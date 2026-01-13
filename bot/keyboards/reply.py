"""Reply keyboards for the bot."""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Create main menu keyboard."""
    builder = ReplyKeyboardBuilder()

    builder.button(text="📝 Новое мероприятие")
    builder.button(text="📋 Мои мероприятия")
    builder.button(text="💰 Добавить расход")
    builder.button(text="👨‍👩‍👧‍👦 Мои семьи")
    builder.button(text="ℹ️ Помощь")

    builder.adjust(2, 2, 1)  # 2-2-1 layout
    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Create keyboard with cancel button."""
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    return builder.as_markup(resize_keyboard=True)


def get_skip_keyboard() -> ReplyKeyboardMarkup:
    """Create keyboard with skip button."""
    builder = ReplyKeyboardBuilder()
    builder.button(text="⏭ Пропустить")
    builder.button(text="❌ Отмена")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_done_keyboard() -> ReplyKeyboardMarkup:
    """Create keyboard with done button."""
    builder = ReplyKeyboardBuilder()
    builder.button(text="✅ Готово")
    builder.button(text="❌ Отмена")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def remove_keyboard() -> ReplyKeyboardMarkup:
    """Remove keyboard."""
    from aiogram.types import ReplyKeyboardRemove
    return ReplyKeyboardRemove()