"""Database middleware for injecting session into handlers."""

from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.session import sessionmanager


class DatabaseMiddleware(BaseMiddleware):
    """Middleware to provide database session to handlers."""

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        """
        Inject database session into handler data.

        Args:
            handler: Handler function
            event: Telegram event
            data: Handler data dictionary

        Returns:
            Handler result
        """
        async with sessionmanager.session() as session:
            data["session"] = session
            return await handler(event, data)