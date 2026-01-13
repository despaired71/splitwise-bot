"""Inline keyboards for the bot."""

from typing import List, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.constants import CB_EVENT, CB_PARTICIPANT, CB_FAMILY, CB_EXPENSE, CB_CALCULATE, CB_CONFIRM, CB_CANCEL


def get_events_keyboard(events: List[tuple], action: str = "select") -> InlineKeyboardMarkup:
    """
    Create keyboard with list of events.

    Args:
        events: List of (event_id, event_name) tuples
        action: Action prefix for callback data
    """
    builder = InlineKeyboardBuilder()

    for event_id, event_name in events:
        builder.button(
            text=event_name,
            callback_data=f"{CB_EVENT}:{action}:{event_id}"
        )

    builder.adjust(1)  # One button per row
    return builder.as_markup()


def get_event_actions_keyboard(event_id: int, is_creator: bool = False) -> InlineKeyboardMarkup:
    """
    Create keyboard with event actions.

    Args:
        event_id: Event ID
        is_creator: Whether user is event creator (has more permissions)
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="ℹ️ Информация",
        callback_data=f"{CB_EVENT}:info:{event_id}"
    )
    builder.button(
        text="👥 Участники",
        callback_data=f"{CB_PARTICIPANT}:list:{event_id}"
    )
    builder.button(
        text="👨‍👩‍👧‍👦 Семьи",
        callback_data=f"{CB_FAMILY}:list:{event_id}"
    )
    builder.button(
        text="💰 Расходы",
        callback_data=f"{CB_EXPENSE}:list:{event_id}"
    )
    builder.button(
        text="🧮 Рассчитать",
        callback_data=f"{CB_CALCULATE}:start:{event_id}"
    )

    if is_creator:
        builder.button(
            text="✏️ Редактировать",
            callback_data=f"{CB_EVENT}:edit:{event_id}"
        )
        builder.button(
            text="🔒 Закрыть",
            callback_data=f"{CB_EVENT}:close:{event_id}"
        )

    builder.adjust(2)  # Two buttons per row
    return builder.as_markup()


def get_participants_keyboard(
        participants: List[tuple],
        action: str = "select",
        event_id: Optional[int] = None
) -> InlineKeyboardMarkup:
    """
    Create keyboard with list of participants.

    Args:
        participants: List of (participant_id, display_name) tuples
        action: Action prefix for callback data
        event_id: Event ID (if needed for callback)
    """
    builder = InlineKeyboardBuilder()

    for participant_id, display_name in participants:
        callback_data = f"{CB_PARTICIPANT}:{action}:{participant_id}"
        if event_id:
            callback_data += f":{event_id}"

        builder.button(
            text=display_name,
            callback_data=callback_data
        )

    builder.adjust(2)  # Two buttons per row
    return builder.as_markup()


def get_families_keyboard(families: List[tuple], action: str = "select") -> InlineKeyboardMarkup:
    """
    Create keyboard with list of families.

    Args:
        families: List of (family_id, family_name) tuples
        action: Action prefix for callback data
    """
    builder = InlineKeyboardBuilder()

    for family_id, family_name in families:
        builder.button(
            text=family_name,
            callback_data=f"{CB_FAMILY}:{action}:{family_id}"
        )

    builder.adjust(1)
    return builder.as_markup()


def get_split_type_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for selecting expense split type."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="⚖️ Поровну на всех",
        callback_data=f"{CB_EXPENSE}:split:equal"
    )
    builder.button(
        text="🎯 На конкретных людей",
        callback_data=f"{CB_EXPENSE}:split:specific"
    )
    builder.button(
        text="📊 Свои доли",
        callback_data=f"{CB_EXPENSE}:split:custom"
    )

    builder.adjust(1)
    return builder.as_markup()


def get_participant_type_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for selecting participant type."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="👤 Пользователь Telegram",
        callback_data=f"{CB_PARTICIPANT}:type:telegram"
    )
    builder.button(
        text="📝 По имени",
        callback_data=f"{CB_PARTICIPANT}:type:external"
    )

    builder.adjust(1)
    return builder.as_markup()


def get_yes_no_keyboard(action: str, data: str = "") -> InlineKeyboardMarkup:
    """
    Create Yes/No keyboard.

    Args:
        action: Action prefix for callback data
        data: Additional data to include in callback
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="✅ Да",
        callback_data=f"{action}:yes:{data}" if data else f"{action}:yes"
    )
    builder.button(
        text="❌ Нет",
        callback_data=f"{action}:no:{data}" if data else f"{action}:no"
    )

    builder.adjust(2)
    return builder.as_markup()


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Create admin menu keyboard."""
    builder = InlineKeyboardBuilder()

    builder.button(text="📊 Статистика", callback_data="admin:stats")
    builder.button(text="📋 Все мероприятия", callback_data="admin:events")
    builder.button(text="🏆 Топ по расходам", callback_data="admin:top")
    builder.button(text="📝 Активность", callback_data="admin:activity")
    builder.button(text="❓ Помощь", callback_data="admin:help")

    builder.adjust(1)  # All buttons in separate rows
    return builder.as_markup()


def get_admin_back_keyboard() -> InlineKeyboardMarkup:
    """Create back to admin menu keyboard."""
    builder = InlineKeyboardBuilder()

    builder.button(text="◀️ Назад в меню", callback_data="admin:menu")

    return builder.as_markup()


def get_confirmation_keyboard(action: str, item_id: int) -> InlineKeyboardMarkup:
    """
    Create confirmation keyboard.

    Args:
        action: Action prefix (e.g., 'expense', 'event')
        item_id: ID of item to confirm action for
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="✅ Подтвердить",
        callback_data=f"{CB_CONFIRM}:{action}:{item_id}"
    )
    builder.button(
        text="❌ Отмена",
        callback_data=f"{CB_CANCEL}:{action}:{item_id}"
    )

    builder.adjust(2)
    return builder.as_markup()


def get_back_button(action: str, item_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """
    Create keyboard with back button.

    Args:
        action: Where to go back (e.g., 'event', 'menu')
        item_id: Optional ID for context
    """
    builder = InlineKeyboardBuilder()

    callback_data = f"back:{action}:{item_id}" if item_id else f"back:{action}"
    builder.button(
        text="◀️ Назад",
        callback_data=callback_data
    )

    return builder.as_markup()


def get_expenses_keyboard(
        expenses: List[tuple],
        can_edit: bool = False
) -> InlineKeyboardMarkup:
    """
    Create keyboard with list of expenses.

    Args:
        expenses: List of (expense_id, description, amount) tuples
        can_edit: Whether to show edit buttons
    """
    builder = InlineKeyboardBuilder()

    for expense_id, description, amount in expenses:
        text = f"{description} - {amount}₽"
        builder.button(
            text=text,
            callback_data=f"{CB_EXPENSE}:view:{expense_id}"
        )

        if can_edit:
            builder.button(
                text="✏️",
                callback_data=f"{CB_EXPENSE}:edit:{expense_id}"
            )
            builder.button(
                text="🗑",
                callback_data=f"{CB_EXPENSE}:delete:{expense_id}"
            )

    # Adjust layout: expense on first column, edit/delete on same row if can_edit
    builder.adjust(3 if can_edit else 1)
    return builder.as_markup()


def get_pagination_keyboard(
        current_page: int,
        total_pages: int,
        action: str,
        item_id: Optional[int] = None
) -> InlineKeyboardMarkup:
    """
    Create pagination keyboard.

    Args:
        current_page: Current page number (0-indexed)
        total_pages: Total number of pages
        action: Action prefix for callback
        item_id: Optional context ID
    """
    builder = InlineKeyboardBuilder()

    # Previous button
    if current_page > 0:
        callback_data = f"page:{action}:{current_page - 1}"
        if item_id:
            callback_data += f":{item_id}"
        builder.button(text="◀️", callback_data=callback_data)

    # Page indicator
    builder.button(
        text=f"{current_page + 1}/{total_pages}",
        callback_data="page:ignore"
    )

    # Next button
    if current_page < total_pages - 1:
        callback_data = f"page:{action}:{current_page + 1}"
        if item_id:
            callback_data += f":{item_id}"
        builder.button(text="▶️", callback_data=callback_data)

    builder.adjust(3)
    return builder.as_markup()