"""Handlers for family management."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.forms import FamilyForm, GlobalFamilyForm
from bot.services.event_service import EventService
from bot.services.family_service import FamilyService
from bot.services.participant_service import ParticipantService
from bot.utils.validators import validate_participant_name
from bot.utils.formatters import format_families_list
from bot.keyboards.inline import (
    get_events_keyboard,
    get_families_keyboard,
    get_yes_no_keyboard,
    get_participants_keyboard
)
from bot.keyboards.reply import get_cancel_keyboard, get_done_keyboard, get_main_menu_keyboard

router = Router()


@router.message(Command("create_family"))
async def cmd_create_family(
        message: Message,
        state: FSMContext,
        session: AsyncSession,
        user_id: int
):
    """Start creating a family in an event."""
    # Get user's active events
    event_service = EventService(session)
    events = await event_service.get_user_events(user_id, include_closed=False)

    if not events:
        await message.answer(
            "❌ У вас нет активных мероприятий.\n"
            "Создайте новое с помощью /new_event"
        )
        return

    await state.set_state(FamilyForm.select_event)

    events_data = [(e.id, e.name) for e in events]
    keyboard = get_events_keyboard(events_data, action="create_family")

    await message.answer(
        "👨‍👩‍👧‍👦 <b>Создание семьи</b>\n\n"
        "Выберите мероприятие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# Note: Family handlers would be similar to participant handlers
# For brevity, I'll create a simplified version

@router.callback_query(F.data.startswith("family:list:"))
async def callback_list_families(
        callback: CallbackQuery,
        session: AsyncSession
):
    """List all families for an event."""
    from bot.services.family_service import FamilyService
    from bot.utils.formatters import format_families_list

    event_id = int(callback.data.split(":")[2])

    family_service = FamilyService(session)
    families = await family_service.get_event_families(event_id)

    if not families:
        await callback.answer("❌ Нет семей", show_alert=True)
        return

    message = format_families_list(families)

    await callback.answer()
    await callback.message.answer(message, parse_mode="HTML")