"""Middlewares package."""

from bot.middlewares.database import DatabaseMiddleware
from bot.middlewares.auth import AuthMiddleware
from bot.middlewares.admin import AdminMiddleware

__all__ = ["DatabaseMiddleware", "AuthMiddleware", "AdminMiddleware"]