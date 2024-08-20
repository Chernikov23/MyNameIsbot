import datetime
import re
import qrcode
from io import BytesIO
from aiogram import Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ContentType, BufferedInputFile, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from tortoise.exceptions import IntegrityError
from aiogram.types.reply_keyboard_remove import ReplyKeyboardRemove
from models import User
from aiogram.fsm.context import FSMContext
from states import Form

rt = Router()

rmk = ReplyKeyboardRemove()

choose = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Да"),
            KeyboardButton(text='Нет')
        ]
    ]
)

gen_qr = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text='Сгенерировать QR-код', callback_data='qrcode')
        ]
    ]
)


@rt.message(Command('start'))
async def start_command(message: Message):
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        user_id = int(args[1])
        user = await User.get_or_none(user_id=user_id)
        if user:
            await send_user_profile(message, user)
        else:
            await message.answer("Анкета не найдена.")
    else:
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        
        user, created = await User.get_or_create(
            user_id=user_id,
            defaults={
                'username': username,
                'first_name': first_name,
            }
        )
        
        response_text = (
            "Привет! Я бот для создания анкет.\n"
            "Вы можете использовать следующие команды:\n"
            "/start - Информация о командах\n"
            "/myself - Создать свою анкету\n"
            "/myprofile - Получить вашу анкету\n"
            "/profile_link - Получить ссылку на вашу анкету с QR-кодом"
        )
        await message.answer(response_text)


@rt.message(Command('myself'))
async def myself_command(message: Message, state: FSMContext):
    user = await User.get_or_none(user_id=message.from_user.id)
    if user:
        await message.answer("Введите ваше имя и фамилию:")
        await state.set_state(Form.awaiting_full_name)
    else:
        await message.answer("Ваша анкета не найдена. Пожалуйста, создайте её с помощью команды /start.")


@rt.message(Form.awaiting_full_name)
async def full_name_handler(message: Message, state: FSMContext):
    full_name = message.text
    user = await User.get_or_none(user_id=message.from_user.id)
    if user:
        user.full_name = full_name
        await user.save()
        await message.answer("Введите дату рождения (ДД.ММ.ГГГГ):")
        await state.set_state(Form.awaiting_birth_date)
    else:
        await message.answer("Ваша анкета не найдена. Пожалуйста, создайте её с помощью команды /start.")


@rt.message(Form.awaiting_birth_date)
async def birth_date_handler(message: Message, state: FSMContext):
    try:
        birth_date = datetime.datetime.strptime(message.text, "%d.%m.%Y").date()
        user = await User.get_or_none(user_id=message.from_user.id)
        if user:
            user.birth_date = birth_date
            await user.save()
            await message.answer(f"Ваш возраст: {user.age} ({user.birth_date.strftime('%d.%m.%Y')}). Опишите себя:")
            await state.set_state(Form.awaiting_description)
        else:
            await message.answer("Ваша анкета не найдена. Пожалуйста, создайте её с помощью команды /start.")
    except ValueError:
        await message.answer("Некорректный формат даты. Попробуйте еще раз.")


@rt.message(Form.awaiting_description)
async def description_handler(message: Message, state: FSMContext):
    description = message.text
    user = await User.get_or_none(user_id=message.from_user.id)
    if user:
        user.description = description
        user.main_username = user.username
        await user.save()
        await message.answer("Хотите добавить фотографию?", reply_markup=choose)
        await state.set_state(Form.awaiting_add_photo)
    else:
        await message.answer("Ваша анкета не найдена. Пожалуйста, создайте её с помощью команды /start.")


@rt.message(Form.awaiting_add_photo)
async def add_photo_handler(message: Message, state: FSMContext):
    answer = message.text.lower()
    user = await User.get_or_none(user_id=message.from_user.id)

    if user:
        if answer == 'да':
            await message.answer("Отправьте фотографию.", reply_markup=rmk)
            await state.set_state(Form.awaiting_photo)
        elif answer == 'нет':
            await message.answer("Хотите указать ссылку на канал?", reply_markup=choose)
            await state.set_state(Form.awaiting_add_channel)
        else:
            await message.answer("Пожалуйста, ответьте 'да' или 'нет'.")
    else:
        await message.answer("Ваша анкета не найдена. Пожалуйста, создайте её с помощью команды /start.")


@rt.message(Form.awaiting_photo)
async def photo_handler(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    user = await User.get(user_id=message.from_user.id)
    user.photos = [photo_id]
    await user.save()

    await message.answer("Фото добавлено. Хотите указать ссылку на канал?", reply_markup=choose)
    await state.set_state(Form.awaiting_add_channel)

@rt.message(Form.awaiting_add_channel)
async def add_channel_handler(message: Message, state: FSMContext):
    answer = message.text.lower()
    user = await User.get_or_none(user_id=message.from_user.id)

    if user:
        if answer == 'да':
            await message.answer("Введите ссылку на ваш канал (например, @yourchannel):", reply_markup=rmk)
            await state.set_state(Form.awaiting_channel)
        elif answer == 'нет':
            await message.answer("Ваша анкета завершена!", reply_markup=rmk)
            await send_user_profile(message, user)
            await state.clear()
        else:
            await message.answer("Пожалуйста, ответьте 'да' или 'нет'.")
    else:
        await message.answer("Ваша анкета не найдена. Пожалуйста, создайте её с помощью команды /start.")


@rt.message(Form.awaiting_channel)
async def channel_handler(message: Message, state: FSMContext):
    channel = message.text
    user = await User.get_or_none(user_id=message.from_user.id)

    if user:
        user.channel = channel
        await user.save()
        await message.answer("Канал добавлен. Ваша анкета завершена!")
        await send_user_profile(message, user)
    else:
        await message.answer("Ваша анкета не найдена. Пожалуйста, создайте её с помощью команды /start.")
    
    await state.clear()


async def generate_qr(user_id):
    link = f"https://t.me/getmeknow_bot?start={user_id}"
    qr = qrcode.make(link)
    bio = BytesIO()
    qr.save(bio, format="PNG")
    bio.seek(0)
    return BufferedInputFile(bio.read(), filename="qr_code.png")


@rt.callback_query(F.data == 'qrcode')
async def send_qr(call: CallbackQuery):
    user = await User.get_or_none(user_id=call.from_user.id)
    if user:
        qr_code = await generate_qr(user.user_id)
        link = f"https://t.me/getmeknow_bot?start={user.user_id}"

        caption = f"Ссылка на анкету: {link}"
        await call.message.answer_photo(qr_code, caption=caption)
    else:
        await call.message.answer("Ваша анкета не найдена. Пожалуйста, создайте её с помощью команды /start.")


@rt.message(Command("profile_link"))
async def profile_link_command(message: Message):
    user = await User.get_or_none(user_id=message.from_user.id)
    if user:
        qr_code = await generate_qr(user.user_id)
        link = f"https://t.me/getmeknow_bot?start={user.user_id}"

        caption = f"Ссылка на анкету: {link}"
        await message.answer_photo(qr_code, caption=caption)
    else:
        await message.answer("Ваша анкета не найдена. Пожалуйста, создайте её с помощью команды /start.")


async def send_user_profile(message: Message, user: User):
    profile_text = (
        f"Имя: {user.full_name}\n"
        f"Возраст: {user.age} ({user.birth_date.strftime('%d.%m.%Y')})\n"
        f"Описание: {user.description}\n"
        f"Основной никнейм: @{user.main_username}\n"
    )
    if user.channel:
        profile_text += f"Канал пользователя: {user.channel}\n"
    profile_text +=f"\n\nСсылка на анкету: https://t.me/getmeknow_bot?start={user.user_id}\n\nСоздай свою анкету! Просто введи /start"
    
    if user.photos:
        await message.answer_photo(user.photos[0], caption=profile_text, reply_markup=gen_qr)
    else:
        await message.answer(profile_text, reply_markup=gen_qr)


@rt.message(Command('myprofile'))
async def myprofile_command(message: Message):
    user_id = message.from_user.id
    
    user = await User.get_or_none(user_id=user_id)
    if user:
        await send_user_profile(message, user)
    else:
        await message.answer("Ваша анкета не найдена. Пожалуйста, создайте её с помощью команды /myself.")