from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram import BaseMiddleware


class UsernameCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
            
            if not user.username:
                if isinstance(event, Message):
                    await event.answer("Пожалуйста, установите username в настройках вашего Telegram. Без username вы не можете пользоваться ботом.")
                elif isinstance(event, CallbackQuery):
                    await event.message.answer("Пожалуйста, установите username в настройках вашего Telegram. Без username вы не можете пользоваться ботом.")
                
                return  
            
        return await handler(event, data)