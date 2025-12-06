import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

import config
from handlers import user_handlers, admin_handlers
from database.firebase_handler import initialize_firebase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def health_check_handler(request):
    return web.Response(text="OK")

async def main():
    if not config.BOT_TOKEN:
        logger.critical("BOT_TOKEN environment variable not set. Shutting down.")
        return

    if not initialize_firebase():
        logger.critical("Could not connect to Firebase. Shutting down.")
        return

    port = int(os.environ.get('PORT', 8080))
    app = web.Application()
    app.router.add_get('/', health_check_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    logger.info(f"Starting web server for health checks on port {port}...")
    await site.start()

    storage = MemoryStorage()
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
    dp = Dispatcher(storage=storage)

    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)

    logger.info("Bot is starting polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        await dp.start_polling(bot)
    finally:
        logger.info("Stopping web server...")
        await runner.cleanup()
        logger.info("Bot polling stopped.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user.")
