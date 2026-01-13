"""Handlers for debt calculation."""

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.forms import CalculateForm
from bot.services.event_service import EventService
from bot.services.calculation_service import CalculationService
from bot.services.participant_service import ParticipantService
from bot.services.notification_service import NotificationService
from bot.utils.formatters import format_debt_calculation
from bot.keyboards.inline import get_events_keyboard, get_yes_no_keyboard

router = Router()


@router.message(Command("calculate"))
async def cmd_calculate(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user_id: int
):
    """Start debt calculation."""
    # Get user's active events
    event_service = EventService(session)
    events = await event_service.get_user_events(user_id, include_closed=False)

    if not events:
        await message.answer(
            "❌ У вас нет активных мероприятий.\n"
            "Создайте новое с помощью /new_event"
        )
        return

    await state.set_state(CalculateForm.select_event)

    events_data = [(e.id, e.name) for e in events]
    keyboard = get_events_keyboard(events_data, action="calculate")

    await message.answer(
        "🧮 <b>Расчет долгов</b>\n\n"
        "Выберите мероприятие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("calculate:start:"))
@router.callback_query(
    CalculateForm.select_event,
    F.data.startswith("event:calculate:")
)
async def callback_calculate_event(
        callback: CallbackQuery,
        state: FSMContext,
        session: AsyncSession,
        user_id: int
):
    """Calculate debts for selected event."""
    # Extract event_id from callback data
    if callback.data.startswith("calculate:start:"):
        event_id = int(callback.data.split(":")[2])
    else:
        event_id = int(callback.data.split(":")[2])

    # Get event
    event_service = EventService(session)
    event = await event_service.get_event(event_id)

    if not event:
        await callback.answer("❌ Мероприятие не найдено", show_alert=True)
        return

    # Check if there are expenses
    if not event.expenses or all(e.is_deleted for e in event.expenses):
        await callback.answer(
            "❌ В мероприятии нет расходов для расчета",
            show_alert=True
        )
        return

    # Perform calculation
    calculation_service = CalculationService(session)
    debts = await calculation_service.calculate_debts(event_id)

    # Save state for notification
    await state.update_data(event_id=event_id, debts=debts)
    await state.set_state(CalculateForm.confirm_send)

    # Format and show results
    message = format_debt_calculation(debts)

    await callback.message.edit_text(
        message,
        parse_mode="HTML"
    )

    # Ask if want to send notifications
    is_creator = await event_service.is_creator(event_id, user_id)

    if is_creator and event.chat_id:
        await callback.message.answer(
            "📨 Отправить уведомления всем участникам?",
            reply_markup=get_yes_no_keyboard("send_notifications", str(event_id))
        )

    await callback.answer("✅ Расчет выполнен")


@router.callback_query(F.data.startswith("send_notifications:yes:"))
async def callback_send_notifications(
        callback: CallbackQuery,
        state: FSMContext,
        session: AsyncSession,
        bot: Bot
):
    """Send notifications to all participants."""
    event_id = int(callback.data.split(":")[2])

    # Get saved calculation data
    data = await state.get_data()
    debts = data.get("debts")

    if not debts:
        await callback.answer("❌ Нет данных расчета", show_alert=True)
        return

    # Get event and participants
    event_service = EventService(session)
    participant_service = ParticipantService(session)

    event = await event_service.get_event(event_id)
    participants_list = await participant_service.get_event_participants(event_id)

    # Build participants dict
    participants = {p.id: p for p in participants_list}

    # Send notifications
    notification_service = NotificationService(bot)
    await notification_service.notify_calculation_complete(
        event,
        debts,
        participants
    )

    await state.clear()

    await callback.message.edit_text(
        "✅ Уведомления отправлены всем участникам!"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("send_notifications:no:"))
async def callback_skip_notifications(
        callback: CallbackQuery,
        state: FSMContext
):
    """Skip sending notifications."""
    await state.clear()
    await callback.message.edit_text(
        "✅ Расчет завершен. Уведомления не отправлены."
    )
    await callback.answer()


@router.message(Command("my_debts"))
async def cmd_my_debts(
        message: Message,
        session: AsyncSession,
        user_id: int
):
    """Show user's debts across all events."""
    event_service = EventService(session)
    calculation_service = CalculationService(session)
    participant_service = ParticipantService(session)

    events = await event_service.get_user_events(user_id, include_closed=False)

    if not events:
        await message.answer(
            "❌ У вас нет активных мероприятий"
        )
        return

    total_message = "<b>💰 Ваши долги по всем мероприятиям:</b>\n\n"
    has_debts = False

    for event in events:
        # Get participant for this event
        participant = await participant_service.get_participant_by_user(
            event.id,
            user_id
        )

        if not participant:
            continue

        # Calculate debts
        debts = await calculation_service.calculate_debts(event.id)

        if participant.id in debts:
            debt_info = debts[participant.id]

            if debt_info["debts"]:
                has_debts = True
                total_message += f"<b>📋 {event.name}</b>\n"

                for debt in debt_info["debts"]:
                    total_message += f"  → {debt['to_name']}: {debt['amount']:.2f} ₽\n"

                total_message += "\n"

    if not has_debts:
        total_message += "✅ У вас нет долгов!"

    await message.answer(total_message, parse_mode="HTML")