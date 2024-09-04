import asyncio
from aiogram import Bot, Dispatcher
import logging
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from tortoise import Tortoise, run_async
from config import TOKEN, TORTOISE_ORM
import os
import handlers
from middlewares import UsernameCheckMiddleware
from aiogram.fsm.storage.memory import MemoryStorage


load_dotenv()

bot = Bot(TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
dp.message.middleware(UsernameCheckMiddleware())
dp.callback_query.middleware(UsernameCheckMiddleware())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


logger.info("Бот запущен и работает...")

async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()

async def main():
    await init_db()
    dp.include_routers(
        handlers.rt
    )
    await dp.start_polling(bot)

if __name__ == "__main__":
    run_async(main())
