"""Handlers for event management."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.forms import EventForm
from bot.services.event_service import EventService
from bot.services.participant_service import ParticipantService
from bot.keyboards.inline import (
    get_events_keyboard,
    get_event_actions_keyboard,
)
from bot.keyboards.reply import get_cancel_keyboard, get_main_menu_keyboard
from bot.utils.formatters import format_event_info, format_event_list
from bot.utils.constants import Messages, EventStatus

router = Router()


@router.message(Command("new_event"))
@router.message(F.text == "📝 Новое мероприятие")
async def cmd_new_event(message: Message, state: FSMContext):
    """Start event creation."""
    await state.set_state(EventForm.name)
    await message.answer(
        Messages.EVENT_NAME_PROMPT,
        reply_markup=get_cancel_keyboard(),
    )


@router.message(EventForm.name, F.text == "❌ Отмена")
async def cancel_event_creation_from_name(message: Message, state: FSMContext):
    """Cancel event creation from name step."""
    await state.clear()
    await message.answer(
        "❌ Создание мероприятия отменено",
        reply_markup=get_main_menu_keyboard()
    )


@router.message(EventForm.name)
async def process_event_name(message: Message, state: FSMContext):
    """Process event name."""
    await state.update_data(name=message.text)
    await state.set_state(EventForm.description)
    await message.answer(
        Messages.EVENT_DESCRIPTION_PROMPT,
        reply_markup=get_cancel_keyboard(),
    )


@router.message(EventForm.description, F.text == "❌ Отмена")
async def cancel_event_creation_from_description(message: Message, state: FSMContext):
    """Cancel event creation from description step."""
    await state.clear()
    await message.answer(
        "❌ Создание мероприятия отменено",
        reply_markup=get_main_menu_keyboard()
    )


@router.message(EventForm.description)
async def process_event_description(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    """Process event description and create event."""
    data = await state.get_data()
    description = message.text if message.text != "Пропустить" else None

    event_service = EventService(session)
    event = await event_service.create_event(
        creator_id=message.from_user.id,
        name=data["name"],
        description=description,
        chat_id=message.chat.id if message.chat.type != "private" else None,
    )

    await state.clear()

    await message.answer(
        f"✅ Мероприятие создано!\n\n{format_event_info(event, participants_count=0)}",
        reply_markup=get_event_actions_keyboard(event.id),
        parse_mode="HTML"
    )


@router.message(Command("list_events"))
@router.message(F.text == "📋 Мои мероприятия")
async def cmd_list_events(message: Message, session: AsyncSession):
    """List user's events."""
    event_service = EventService(session)
    participant_service = ParticipantService(session)

    events = await event_service.get_user_events(message.from_user.id)

    if not events:
        await message.answer(Messages.NO_EVENTS, parse_mode="HTML")
        return

    events_with_counts = []
    for event in events:
        participants = await participant_service.get_event_participants(event.id)
        events_with_counts.append((event, len(participants)))

    text = format_event_list(events_with_counts)
    events_data = [(e.id, e.name) for e, count in events_with_counts]

    await message.answer(
        text,
        reply_markup=get_events_keyboard(events_data),
        parse_mode="HTML"
    )


@router.message(Command("event_info"))
async def cmd_event_info(message: Message, session: AsyncSession):
    """Show events for info selection."""
    event_service = EventService(session)
    events = await event_service.get_user_events(message.from_user.id)

    if not events:
        await message.answer(Messages.NO_EVENTS, parse_mode="HTML")
        return

    events_data = [(e.id, e.name) for e in events]

    await message.answer(
        "Выберите мероприятие:",
        reply_markup=get_events_keyboard(events_data, action="info"),
    )


@router.callback_query(F.data.startswith("event:info:"))
async def show_event_info(callback: CallbackQuery, session: AsyncSession):
    """Show detailed event information."""
    event_id = int(callback.data.split(":")[2])

    event_service = EventService(session)
    participant_service = ParticipantService(session)

    event = await event_service.get_event(event_id)

    if not event:
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return

    participants = await participant_service.get_event_participants(event_id)

    await callback.message.edit_text(
        format_event_info(event, participants_count=len(participants)),
        reply_markup=get_event_actions_keyboard(event_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(Command("close_event"))
async def cmd_close_event(message: Message, session: AsyncSession):
    """Show events for closing."""
    event_service = EventService(session)
    events = await event_service.get_user_events(
        message.from_user.id,
        status=EventStatus.ACTIVE,
    )

    if not events:
        await message.answer("У вас нет активных мероприятий")
        return

    events_data = [(e.id, e.name) for e in events]

    await message.answer(
        "Выберите мероприятие для закрытия:",
        reply_markup=get_events_keyboard(events_data, action="close"),
    )


@router.callback_query(F.data.startswith("event:close:"))
async def close_event(callback: CallbackQuery, session: AsyncSession):
    """Close an event."""
    event_id = int(callback.data.split(":")[2])

    event_service = EventService(session)
    event = await event_service.close_event(event_id, callback.from_user.id)

    if not event:
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return

    participant_service = ParticipantService(session)
    participants = await participant_service.get_event_participants(event_id)

    await callback.message.edit_text(
        f"✅ Мероприятие закрыто\n\n{format_event_info(event, participants_count=len(participants))}",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Cancel current action."""
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено")
    await callback.answer()