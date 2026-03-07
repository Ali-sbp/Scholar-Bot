import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import config
from app.bot.handlers import start, subscribe, subscriptions
from app.scheduler.tasks import check_subscriptions
from app.storage.database import engine
from app.storage.models import Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")


async def main() -> None:
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers
    dp.include_router(start.router)
    dp.include_router(subscribe.router)
    dp.include_router(subscriptions.router)

    # Periodic subscription checker (every 30 min)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_subscriptions,
        "interval",
        minutes=30,
        args=[bot],
        id="check_subs",
        replace_existing=True,
    )
    scheduler.start()

    await on_startup(bot)

    logger.info("Bot starting…")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
