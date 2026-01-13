"""Main entry point for the bot."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from bot.config.settings import settings
from bot.database.session import sessionmanager
from bot.middlewares.database import DatabaseMiddleware
from bot.middlewares.auth import AuthMiddleware

# Import handlers (will create these next)
# from bot.handlers import start, event, participant, family, expense, calculation

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Actions to perform on bot startup."""
    logger.info("Bot starting up...")

    # Initialize database
    sessionmanager.init(settings.database_url)
    logger.info("Database session manager initialized")

    # Set bot commands
    from aiogram.types import BotCommand

    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="help", description="Показать справку"),
        BotCommand(command="new_event", description="Создать мероприятие"),
        BotCommand(command="list_events", description="Список мероприятий"),
        BotCommand(command="add_expense", description="Добавить расход"),
        BotCommand(command="calculate", description="Рассчитать долги"),
    ]

    await bot.set_my_commands(commands)
    logger.info("Bot commands set")

    bot_info = await bot.get_me()
    logger.info(f"Bot started: @{bot_info.username}")


async def on_shutdown(bot: Bot):
    """Actions to perform on bot shutdown."""
    logger.info("Bot shutting down...")

    # Close database connections
    await sessionmanager.close()
    logger.info("Database connections closed")


async def main():
    """Main function to run the bot."""

    # Initialize bot
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Initialize storage
    try:
        redis = Redis.from_url(settings.redis_url)
        storage = RedisStorage(redis=redis)
        logger.info("Using Redis storage for FSM")
    except Exception as e:
        logger.warning(f"Could not connect to Redis: {e}. Using memory storage.")
        from aiogram.fsm.storage.memory import MemoryStorage
        storage = MemoryStorage()

    # Initialize dispatcher
    dp = Dispatcher(storage=storage)

    # Register middlewares
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # Register handlers
    from bot.handlers import start, event, participant, family, expense, calculation, admin

    dp.include_router(start.router)
    dp.include_router(admin.router)  # Admin router first for priority
    dp.include_router(event.router)
    dp.include_router(participant.router)
    dp.include_router(family.router)
    dp.include_router(expense.router)
    dp.include_router(calculation.router)

    # Register startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Start polling
    try:
        logger.info("Starting bot polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Error during polling: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")