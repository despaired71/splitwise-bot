"""Handlers for expense management."""

from decimal import Decimal
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.forms import ExpenseForm
from bot.services.event_service import EventService
from bot.services.expense_service import ExpenseService
from bot.services.participant_service import ParticipantService
from bot.utils.validators import validate_amount, validate_description
from bot.utils.formatters import format_expenses_list, format_expense_detail, format_expense_summary
from bot.utils.constants import SplitType
from bot.keyboards.inline import (
    get_events_keyboard,
    get_split_type_keyboard,
    get_participants_keyboard,
    get_expenses_keyboard
)
from bot.keyboards.reply import get_cancel_keyboard, get_skip_keyboard, get_main_menu_keyboard

router = Router()


@router.message(Command("add_expense"))
@router.message(F.text == "💰 Добавить расход")
async def cmd_add_expense(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user_id: int
):
    """Start adding an expense."""
    # Get user's active events
    event_service = EventService(session)
    events = await event_service.get_user_events(user_id, include_closed=False)

    if not events:
        await message.answer(
            "❌ У вас нет активных мероприятий.\n"
            "Создайте новое с помощью /new_event"
        )
        return

    await state.set_state(ExpenseForm.select_event)

    events_data = [(e.id, e.name) for e in events]
    keyboard = get_events_keyboard(events_data, action="add_expense")

    await message.answer(
        "💰 <b>Добавление расхода</b>\n\n"
        "Выберите мероприятие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(
    ExpenseForm.select_event,
    F.data.startswith("event:add_expense:")
)
async def callback_select_event_for_expense(
        callback: CallbackQuery,
        state: FSMContext
):
    """Event selected, ask for amount."""
    event_id = int(callback.data.split(":")[2])
    await state.update_data(event_id=event_id)
    await state.set_state(ExpenseForm.amount)

    await callback.message.edit_text(
        "💵 <b>Сумма расхода</b>\n\n"
        "Введите сумму (например: 500 или 1250.50):",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Введите сумму:",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(ExpenseForm.amount)
async def process_expense_amount(
        message: Message,
        state: FSMContext
):
    """Process expense amount."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Добавление расхода отменено",
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Validate amount
    is_valid, amount, error = validate_amount(message.text)
    if not is_valid:
        await message.answer(error)
        return

    await state.update_data(amount=amount)
    await state.set_state(ExpenseForm.description)

    await message.answer(
        "📝 <b>Описание расхода</b>\n\n"
        "На что потрачены деньги? (например: 'Ужин в ресторане')",
        parse_mode="HTML"
    )


@router.message(ExpenseForm.description)
async def process_expense_description(
        message: Message,
        state: FSMContext
):
    """Process expense description."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Добавление расхода отменено",
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Validate description
    is_valid, error = validate_description(message.text)
    if not is_valid:
        await message.answer(error)
        return

    await state.update_data(description=message.text.strip())
    await state.set_state(ExpenseForm.category)

    await message.answer(
        "🏷 <b>Категория</b> (необязательно)\n\n"
        "Введите категорию расхода (например: 'Еда', 'Транспорт', 'Развлечения')\n"
        "или нажмите 'Пропустить':",
        reply_markup=get_skip_keyboard(),
        parse_mode="HTML"
    )


@router.message(ExpenseForm.category)
async def process_expense_category(
        message: Message,
        state: FSMContext
):
    """Process expense category."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Добавление расхода отменено",
            reply_markup=get_main_menu_keyboard()
        )
        return

    category = None if message.text == "⏭ Пропустить" else message.text.strip()
    await state.update_data(category=category)
    await state.set_state(ExpenseForm.split_type)

    await message.answer(
        "⚖️ <b>Как разделить расход?</b>",
        reply_markup=get_split_type_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(
    ExpenseForm.split_type,
    F.data.startswith("expense:split:")
)
async def callback_select_split_type(
        callback: CallbackQuery,
        state: FSMContext,
        session: AsyncSession
):
    """Split type selected."""
    split_type = callback.data.split(":")[2]
    await state.update_data(split_type=split_type)

    data = await state.get_data()
    event_id = data["event_id"]

    if split_type == "equal":
        # For equal split, ask who to split among
        await state.set_state(ExpenseForm.select_participants)

        # Get all participants
        participant_service = ParticipantService(session)
        participants = await participant_service.get_event_participants(event_id)

        if not participants:
            await callback.answer("❌ Нет участников в мероприятии", show_alert=True)
            return

        participants_data = [(p.id, p.display_name) for p in participants]
        keyboard = get_participants_keyboard(participants_data, action="split_select")

        await callback.message.edit_text(
            "👥 <b>Выберите участников</b>\n\n"
            "Между кем разделить расход?\n"
            "(Можно выбрать несколько, после выбора нажмите 'Готово')",
            parse_mode="HTML"
        )
        await callback.message.answer(
            "Выберите участников:",
            reply_markup=keyboard
        )

    else:
        # For custom/specific splits, we need more complex handling
        # For now, let's simplify and create with equal split
        await callback.answer(
            "⚠️ Пока поддерживается только равное разделение.\n"
            "Эта функция будет добавлена в следующей версии.",
            show_alert=True
        )
        await state.set_state(ExpenseForm.split_type)
        return

    await callback.answer()


@router.callback_query(
    ExpenseForm.select_participants,
    F.data.startswith("participant:split_select:")
)
async def callback_select_participant_for_split(
        callback: CallbackQuery,
        state: FSMContext
):
    """Participant selected for split."""
    participant_id = int(callback.data.split(":")[2])

    # Get current selections
    data = await state.get_data()
    selected = data.get("selected_participants", [])

    # Toggle selection
    if participant_id in selected:
        selected.remove(participant_id)
    else:
        selected.append(participant_id)

    await state.update_data(selected_participants=selected)
    await callback.answer(f"✅ Выбрано: {len(selected)}")


@router.message(ExpenseForm.select_participants, F.text == "✅ Готово")
async def process_participants_selection(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user_id: int
):
    """Finalize participant selection and create expense."""
    data = await state.get_data()

    selected_participants = data.get("selected_participants", [])
    if not selected_participants:
        await message.answer("❌ Выберите хотя бы одного участника")
        return

    # Get participant to use as payer
    participant_service = ParticipantService(session)
    payer = await participant_service.get_participant_by_user(
        data["event_id"],
        user_id
    )

    if not payer:
        # Add current user as participant
        payer = await participant_service.add_participant(
            event_id=data["event_id"],
            added_by=user_id,
            display_name=message.from_user.full_name,
            participant_type="telegram_chat",
            user_id=user_id,
            username=message.from_user.username
        )

    # Create expense
    expense_service = ExpenseService(session)

    splits = [{"participant_id": pid} for pid in selected_participants]

    expense = await expense_service.create_expense(
        event_id=data["event_id"],
        payer_id=payer.id,
        amount=data["amount"],
        description=data["description"],
        split_type=SplitType.EQUAL,
        splits=splits,
        category=data.get("category")
    )

    await state.clear()

    await message.answer(
        f"✅ Расход добавлен!\n\n"
        f"{format_expense_detail(expense)}",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )


@router.message(Command("my_expenses"))
async def cmd_my_expenses(
        message: Message,
        session: AsyncSession,
        user_id: int
):
    """Show user's expenses."""
    # Get user's participants across all events
    participant_service = ParticipantService(session)
    expense_service = ExpenseService(session)

    # This is simplified - in production you'd want to aggregate properly
    await message.answer(
        "📊 <b>Ваши расходы</b>\n\n"
        "Используйте /list_events чтобы посмотреть расходы по мероприятию",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("expense:list:"))
async def callback_list_expenses(
        callback: CallbackQuery,
        session: AsyncSession,
        user_id: int
):
    """List all expenses for an event."""
    event_id = int(callback.data.split(":")[2])

    expense_service = ExpenseService(session)
    event_service = EventService(session)

    expenses = await expense_service.get_event_expenses(event_id)
    is_creator = await event_service.is_creator(event_id, user_id)

    if not expenses:
        await callback.answer("❌ Нет расходов", show_alert=True)
        return

    # Get summary
    summary = await expense_service.get_expense_summary(event_id)

    message = format_expense_summary(summary)
    message += "\n\n" + format_expenses_list(expenses)

    await callback.answer()
    await callback.message.answer(message, parse_mode="HTML")