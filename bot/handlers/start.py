"""Handlers for start and help commands."""

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.constants import MSG_WELCOME, MSG_HELP
from bot.keyboards.reply import get_main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    """Handle /start command."""
    await message.answer(
        MSG_WELCOME,
        reply_markup=get_main_menu_keyboard()
    )


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    """Handle /help command."""
    await message.answer(MSG_HELP, parse_mode="HTML")