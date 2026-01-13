"""Authentication and authorization middleware."""

from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


class AuthMiddleware(BaseMiddleware):
    """Middleware to check user permissions."""

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        """
        Check user permissions and inject user data.

        Args:
            handler: Handler function
            event: Telegram event
            data: Handler data dictionary

        Returns:
            Handler result
        """
        # Extract user from event
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user:
            data["user_id"] = user.id
            data["username"] = user.username
            data["full_name"] = user.full_name

        return await handler(event, data)