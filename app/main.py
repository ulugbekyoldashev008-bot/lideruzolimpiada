import asyncio
import logging
from aiogram import Bot, Dispatcher
from . import admin, student
from .config import get_settings
from .db import init_db, make_db
from .health import start_health_server
from .scheduler import reminder_loop


async def main():
    logging.basicConfig(level=logging.INFO)
    settings = get_settings(); engine, sessions = make_db(settings.database_url)
    await init_db(engine, sessions)
    bot = Bot(settings.bot_token)
    dp = Dispatcher()
    dp["sessions"] = sessions; dp["settings"] = settings
    dp.include_router(admin.router); dp.include_router(student.router)
    health_runner = await start_health_server()
    reminder_task = asyncio.create_task(reminder_loop(bot, sessions, settings, dp))
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        reminder_task.cancel()
        if health_runner:
            await health_runner.cleanup()
        await bot.session.close(); await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
