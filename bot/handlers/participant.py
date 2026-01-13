"""Handlers for participant management."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.forms import ParticipantForm
from bot.services.event_service import EventService
from bot.services.participant_service import ParticipantService
from bot.utils.validators import validate_participant_name, validate_username
from bot.utils.formatters import format_participants_list
from bot.utils.constants import ParticipantType
from bot.keyboards.inline import (
    get_events_keyboard,
    get_participant_type_keyboard,
    get_participants_keyboard
)
from bot.keyboards.reply import get_cancel_keyboard, get_main_menu_keyboard

router = Router()


@router.message(Command("add_participant"))
async def cmd_add_participant(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user_id: int
):
    """Start adding a participant."""
    # Get user's active events
    event_service = EventService(session)
    events = await event_service.get_user_events(user_id, include_closed=False)

    if not events:
        await message.answer(
            "❌ У вас нет активных мероприятий.\n"
            "Создайте новое с помощью /new_event"
        )
        return

    await state.set_state(ParticipantForm.select_event)

    events_data = [(e.id, e.name) for e in events]
    keyboard = get_events_keyboard(events_data, action="add_participant")

    await message.answer(
        "👥 <b>Добавление участника</b>\n\n"
        "Выберите мероприятие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(
    ParticipantForm.select_event,
    F.data.startswith("event:add_participant:")
)
async def callback_select_event_for_participant(
        callback: CallbackQuery,
        state: FSMContext
):
    """Event selected, ask for participant type."""
    event_id = int(callback.data.split(":")[2])
    await state.update_data(event_id=event_id)
    await state.set_state(ParticipantForm.participant_type)

    await callback.message.edit_text(
        "👤 <b>Тип участника</b>\n\n"
        "Как добавить участника?",
        reply_markup=get_participant_type_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(
    ParticipantForm.participant_type,
    F.data.startswith("participant:type:")
)
async def callback_select_participant_type(
        callback: CallbackQuery,
        state: FSMContext
):
    """Participant type selected, ask for details."""
    participant_type = callback.data.split(":")[2]
    await state.update_data(participant_type=participant_type)
    await state.set_state(ParticipantForm.user_input)

    if participant_type == "telegram":
        prompt = (
            "👤 <b>Пользователь Telegram</b>\n\n"
            "Введите username пользователя (например, @username)\n"
            "или перешлите его сообщение:"
        )
    else:
        prompt = (
            "📝 <b>Участник без Telegram</b>\n\n"
            "Введите имя участника:"
        )

    await callback.message.edit_text(prompt, parse_mode="HTML")
    await callback.message.answer(
        "Введите данные:",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(ParticipantForm.user_input)
async def process_participant_input(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user_id: int
):
    """Process participant input and add to event."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Добавление участника отменено",
            reply_markup=get_main_menu_keyboard()
        )
        return

    data = await state.get_data()
    event_id = data["event_id"]
    participant_type = data["participant_type"]

    participant_service = ParticipantService(session)

    if participant_type == "telegram":
        # Try to get user from forwarded message
        if message.forward_from:
            target_user_id = message.forward_from.id
            username = message.forward_from.username
            display_name = message.forward_from.full_name
        else:
            # Parse username
            is_valid, username, error = validate_username(message.text)
            if not is_valid:
                await message.answer(error)
                return

            # Note: We can't get user_id from username directly via Bot API
            # So we'll add with username only
            target_user_id = None
            display_name = f"@{username}"

        participant = await participant_service.add_participant(
            event_id=event_id,
            added_by=user_id,
            display_name=display_name,
            participant_type=ParticipantType.TELEGRAM_EXTERNAL,
            user_id=target_user_id,
            username=username
        )

    else:
        # External participant
        is_valid, error = validate_participant_name(message.text)
        if not is_valid:
            await message.answer(error)
            return

        participant = await participant_service.add_participant(
            event_id=event_id,
            added_by=user_id,
            display_name=message.text.strip(),
            participant_type=ParticipantType.EXTERNAL
        )

    await state.clear()

    await message.answer(
        f"✅ Участник добавлен!\n\n"
        f"👤 {participant.display_name}",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )


@router.message(Command("join_event"))
async def cmd_join_event(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user_id: int
):
    """Join an event (for group chats)."""
    # This command should be used in group chats
    if message.chat.type not in ["group", "supergroup"]:
        await message.answer(
            "❌ Эта команда работает только в групповых чатах.\n"
            "Используйте /add_participant для добавления участников."
        )
        return

    chat_id = message.chat.id

    # Get events for this chat
    event_service = EventService(session)
    events = await event_service.get_chat_events(chat_id)

    if not events:
        await message.answer(
            "❌ В этом чате нет активных мероприятий.\n"
            "Создайте новое с помощью /new_event"
        )
        return

    # If only one event, join directly
    if len(events) == 1:
        event = events[0]
        participant_service = ParticipantService(session)

        participant = await participant_service.add_participant(
            event_id=event.id,
            added_by=user_id,
            display_name=message.from_user.full_name,
            participant_type=ParticipantType.TELEGRAM_CHAT,
            user_id=user_id,
            username=message.from_user.username
        )

        await message.reply(
            f"✅ Вы добавлены к мероприятию: {event.name}"
        )
    else:
        # Multiple events, let user choose
        events_data = [(e.id, e.name) for e in events]
        keyboard = get_events_keyboard(events_data, action="join")

        await message.answer(
            "📋 Выберите мероприятие для присоединения:",
            reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("event:join:"))
async def callback_join_event(
        callback: CallbackQuery,
        session: AsyncSession,
        user_id: int,
        full_name: str,
        username: str
):
    """Join selected event."""
    event_id = int(callback.data.split(":")[2])

    participant_service = ParticipantService(session)
    event_service = EventService(session)

    event = await event_service.get_event(event_id)
    if not event:
        await callback.answer("❌ Мероприятие не найдено", show_alert=True)
        return

    participant = await participant_service.add_participant(
        event_id=event_id,
        added_by=user_id,
        display_name=full_name,
        participant_type=ParticipantType.TELEGRAM_CHAT,
        user_id=user_id,
        username=username
    )

    await callback.message.edit_text(
        f"✅ Вы добавлены к мероприятию: {event.name}"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("participant:list:"))
async def callback_list_participants(
        callback: CallbackQuery,
        session: AsyncSession
):
    """List all participants for an event."""
    event_id = int(callback.data.split(":")[2])

    participant_service = ParticipantService(session)
    participants = await participant_service.get_event_participants(event_id)

    if not participants:
        await callback.answer("❌ Нет участников", show_alert=True)
        return

    message = format_participants_list(participants)

    await callback.answer()
    await callback.message.answer(message, parse_mode="HTML")