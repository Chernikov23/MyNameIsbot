import asyncio
from aiogram import Bot, Dispatcher
import logging
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from tortoise import Tortoise, run_async
from config import TORTOISE_ORM, TOKEN
from handlers import bot_messages, user_commands
import os

load_dotenv()

bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode="MarkDown"))
dp = Dispatcher() 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Бот запущен и работает...")

async def on_startup():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()

async def on_shutdown():
    await Tortoise.close_connections()

async def main():  
    await on_startup()
    dp.include_routers(
        bot_messages.rt,
        user_commands.rt
    )
    await dp.start_polling(bot)
    await on_shutdown()

if __name__ == "__main__":
    run_async(main())
