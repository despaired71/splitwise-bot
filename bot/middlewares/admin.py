"""Admin middleware for checking admin permissions."""

from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.config.settings import settings


class AdminMiddleware(BaseMiddleware):
    """Middleware to check if user is admin."""

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        """Check admin status and add to data."""
        user_id = data.get("user_id")

        # Check if user is admin
        is_admin = settings.is_admin(user_id) if user_id else False
        data["is_admin"] = is_admin

        return await handler(event, data)