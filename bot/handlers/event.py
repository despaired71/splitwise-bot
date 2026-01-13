"""Handlers for event management."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.forms import EventForm
from bot.services.event_service import EventService
from bot.utils.validators import validate_event_name
from bot.utils.formatters import format_event_info
from bot.keyboards.inline import (
    get_events_keyboard,
    get_event_actions_keyboard,
    get_confirmation_keyboard
)
from bot.keyboards.reply import get_cancel_keyboard, get_main_menu_keyboard

router = Router()


@router.message(Command("new_event"))
@router.message(F.text == "📝 Новое мероприятие")
async def cmd_new_event(message: Message, state: FSMContext):
    """Start creating a new event."""
    await state.set_state(EventForm.name)
    await message.answer(
        "📝 <b>Создание нового мероприятия</b>\n\n"
        "Введите название мероприятия:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )


@router.message(EventForm.name)
async def process_event_name(message: Message, state: FSMContext, user_id: int):
    """Process event name input."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Создание мероприятия отменено",
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Validate name
    is_valid, error = validate_event_name(message.text)
    if not is_valid:
        await message.answer(error)
        return

    # Save name and ask for description
    await state.update_data(name=message.text.strip())
    await state.set_state(EventForm.description)

    await message.answer(
        "📄 Введите описание мероприятия (или нажмите 'Пропустить'):",
        reply_markup=get_cancel_keyboard()
    )


@router.message(EventForm.description)
async def process_event_description(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user_id: int
):
    """Process event description and create event."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Создание мероприятия отменено",
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Get saved data
    data = await state.get_data()
    name = data["name"]
    description = message.text.strip() if message.text != "⏭ Пропустить" else None

    # Create event
    event_service = EventService(session)

    # Determine chat_id (if in group chat)
    chat_id = message.chat.id if message.chat.type in ["group", "supergroup"] else None

    event = await event_service.create_event(
        name=name,
        creator_id=user_id,
        description=description,
        chat_id=chat_id
    )

    await state.clear()

    # Show created event
    await message.answer(
        f"✅ Мероприятие создано!\n\n{format_event_info(event)}",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )

    # Show action buttons
    await message.answer(
        "Что хотите сделать?",
        reply_markup=get_event_actions_keyboard(event.id, is_creator=True)
    )


@router.message(Command("list_events"))
@router.message(F.text == "📋 Мои мероприятия")
async def cmd_list_events(
        message: Message,
        session: AsyncSession,
        user_id: int
):
    """List all user's events."""
    event_service = EventService(session)
    events = await event_service.get_user_events(user_id, include_closed=False)

    if not events:
        await message.answer(
            "❌ У вас пока нет активных мероприятий.\n\n"
            "Создайте новое с помощью /new_event"
        )
        return

    # Create keyboard with events
    events_data = [(e.id, e.name) for e in events]
    keyboard = get_events_keyboard(events_data, action="view")

    await message.answer(
        f"📋 <b>Ваши мероприятия ({len(events)}):</b>\n\n"
        "Выберите мероприятие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("event:view:"))
async def callback_view_event(
        callback: CallbackQuery,
        session: AsyncSession,
        user_id: int
):
    """View event details."""
    event_id = int(callback.data.split(":")[2])

    event_service = EventService(session)
    event = await event_service.get_event(event_id)

    if not event:
        await callback.answer("❌ Мероприятие не найдено", show_alert=True)
        return

    is_creator = await event_service.is_creator(event_id, user_id)

    await callback.message.edit_text(
        format_event_info(event),
        reply_markup=get_event_actions_keyboard(event_id, is_creator),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("event:info:"))
async def callback_event_info(
        callback: CallbackQuery,
        session: AsyncSession
):
    """Show detailed event info."""
    event_id = int(callback.data.split(":")[2])

    event_service = EventService(session)
    event = await event_service.get_event(event_id)

    if not event:
        await callback.answer("❌ Мероприятие не найдено", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer(
        format_event_info(event),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("event:close:"))
async def callback_close_event(callback: CallbackQuery):
    """Ask confirmation to close event."""
    event_id = int(callback.data.split(":")[2])

    await callback.message.edit_text(
        "⚠️ <b>Закрытие мероприятия</b>\n\n"
        "После закрытия нельзя будет добавлять новые расходы.\n"
        "Подтвердите действие:",
        reply_markup=get_confirmation_keyboard("close_event", event_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm:close_event:"))
async def callback_confirm_close_event(
        callback: CallbackQuery,
        session: AsyncSession,
        user_id: int
):
    """Confirm and close event."""
    event_id = int(callback.data.split(":")[2])

    event_service = EventService(session)

    # Check permissions
    if not await event_service.is_creator(event_id, user_id):
        await callback.answer("❌ Только создатель может закрыть мероприятие", show_alert=True)
        return

    event = await event_service.close_event(event_id, user_id)

    if not event:
        await callback.answer("❌ Мероприятие не найдено", show_alert=True)
        return

    await callback.message.edit_text(
        f"✅ Мероприятие закрыто!\n\n{format_event_info(event)}",
        parse_mode="HTML"
    )
    await callback.answer("✅ Мероприятие закрыто")


@router.callback_query(F.data.startswith("cancel:close_event:"))
async def callback_cancel_close_event(
        callback: CallbackQuery,
        session: AsyncSession,
        user_id: int
):
    """Cancel event closing."""
    event_id = int(callback.data.split(":")[2])

    event_service = EventService(session)
    event = await event_service.get_event(event_id)
    is_creator = await event_service.is_creator(event_id, user_id)

    await callback.message.edit_text(
        format_event_info(event),
        reply_markup=get_event_actions_keyboard(event_id, is_creator),
        parse_mode="HTML"
    )
    await callback.answer("❌ Отменено")