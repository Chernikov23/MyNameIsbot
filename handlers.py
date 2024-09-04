import datetime
import qrcode
from io import BytesIO
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, TelegramObject
from aiogram.types.reply_keyboard_remove import ReplyKeyboardRemove
from models import User, UserInteraction, Match, InteractionType, Rating
from aiogram.fsm.context import FSMContext
from states import Form
from bot import bot

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


def create_rating_keyboard(user_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text=f"{i}", callback_data=f"rate_{user_id}_{i}")
            for i in range(6)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@rt.message(Command('start'))
async def start_command(message: Message):
    args = message.text.split()
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
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id != user_id:  
            referrer = await User.get_or_none(user_id=referrer_id)
            if referrer:
                referrer.referral_count += 1
                await referrer.save()
                await show_profile_with_actions(message, referrer)
                return  
    response_text = (
        "Привет! Я бот для создания анкет.\n"
        "Вы можете использовать следующие команды:\n"
        "/start - Информация о командах\n"
        "/create - Создать свою анкету\n"
        "/myprofile - Получить вашу анкету\n"
        "/profile_link - Получить ссылку на вашу анкету с QR-кодом\n"
        "/view_profiles - Просмотр анкет других пользователей\n"
        "/top_ratings - Топ пользователей по рейтингу\n"
        "/top_referrals - Топ пользователей по рефералам"
    )
    await message.answer(response_text)




@rt.message(Command('create'))
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
            await message.answer(f"Ваш возраст: {user.age} ({user.birth_date.strftime('%d.%m.%Y')}). Расскажите о себе:")
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


async def show_profile_with_actions(message: Message, user: User):
    profile_text = (
        f"Имя: {user.full_name}\n"
        f"Возраст: {user.age} ({user.birth_date.strftime('%d.%m.%Y')})\n"
        f"О себе: {user.description}\n"
        f"Рейтинг: {user.rating:.2f} (на основе {user.rating_count} оценок)\n"
        f"Основной никнейм: @{user.main_username}\n"
    )
    if user.channel:
        profile_text += f"Канал пользователя: {user.channel}\n"
    profile_text += f"\n\nСсылка на анкету: https://t.me/getmeknow_bot?start={user.user_id}"

    action_buttons = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 Лайк", callback_data=f"like_{user.id}"),
                InlineKeyboardButton(text="👎 Дизлайк", callback_data=f"skip_{user.id}")
            ],
            [InlineKeyboardButton(text=f"{i} ⭐", callback_data=f"rate_{user.id}_{i}") for i in range(1, 6)]
        ]
    )

    if user.photos:
        await message.answer_photo(user.photos[0], caption=profile_text, reply_markup=action_buttons)
    else:
        await message.answer(profile_text, reply_markup=action_buttons)



async def send_user_profile(message: Message, user: User):
    profile_text = (
        f"Имя: {user.full_name}\n"
        f"Возраст: {user.age} ({user.birth_date.strftime('%d.%м.%Y')})\n"
        f"О себе: {user.description}\n"
        f"Рейтинг: {user.rating:.2f} (на основе {user.rating_count} оценок)\n"
        f"Основной никнейм: @{user.main_username}\n"
    )
    if user.channel:
        profile_text += f"Канал пользователя: {user.channel}\n"
    profile_text += f"\n\nСсылка на анкету: https://t.me/getmeknow_bot?start={user.user_id}\n\nСоздай свою анкету! Просто введи /start"
    
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



async def check_match(user: User, target_user: User):
    """Проверяет, есть ли мэч между пользователями."""
    interaction = await UserInteraction.get_or_none(user=target_user, target_user=user, interaction_type=InteractionType.LIKE)
    if interaction:
        await Match.create(user1=user, user2=target_user)
        match_message = (
            f"У вас мэч с @{target_user.username}! "
            f"Можете перейти в чат по ссылке: https://t.me/{target_user.username}"
        )
        await bot.send_message(user.user_id, match_message)
        await bot.send_message(target_user.user_id, match_message)
        return True
    return False


@rt.callback_query(lambda call: call.data.startswith("like_"))
async def like_handler(call: CallbackQuery):
    target_user_id = int(call.data.split("_")[1])
    target_user = await User.get_or_none(id=target_user_id)
    current_user = await User.get_or_none(user_id=call.from_user.id)

    if target_user:
        existing_interaction = await UserInteraction.get_or_none(
            user=current_user, 
            target_user=target_user, 
            interaction_type=InteractionType.LIKE
        )

        if not existing_interaction:
            await UserInteraction.create(user=current_user, target_user=target_user, interaction_type=InteractionType.LIKE)

            if await check_match(current_user, target_user):
                await call.message.answer("У вас мэч! Теперь вы можете общаться.")
                match_message = (
                    f"У вас мэч с @{current_user.username}! "
                    f"Можете перейти в чат по ссылке: https://t.me/{current_user.username}"
                )
                await call.bot.send_message(target_user.user_id, match_message)
            else:
                notification_message = (
                    f"Пользователь @{current_user.username} оценил вашу анкету!\n"
                    f"Можете перейти в чат по ссылке: https://t.me/{current_user.username}"
                )
                buttons = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(text="👍 Лайк", callback_data=f"like_{current_user.id}"),
                            InlineKeyboardButton(text="👎 Пропустить", callback_data=f"skip_{current_user.id}")
                        ]
                    ]
                )
                await call.bot.send_message(target_user.user_id, notification_message, reply_markup=buttons)

        await call.message.answer("Вы лайкнули анкету.")
        await show_next_profile(call.message)
    else:
        await call.message.answer("Пользователь не найден.")


@rt.callback_query(lambda call: call.data.startswith("skip_"))
async def skip_handler(call: CallbackQuery):
    target_user_id = int(call.data.split("_")[1])
    target_user = await User.get_or_none(id=target_user_id)
    current_user = await User.get_or_none(user_id=call.from_user.id)

    if target_user:
        await UserInteraction.create(user=current_user, target_user=target_user, interaction_type=InteractionType.SKIP)
        await call.message.answer("Вы пропустили анкету.")
        await show_next_profile(call.message)
    else:
        await call.message.answer("Пользователь не найден.")


@rt.callback_query(lambda call: call.data.startswith("rate_"))
async def rate_handler(call: CallbackQuery):
    data = call.data.split("_")
    target_user_id = int(data[1])
    rating = int(data[2])

    target_user = await User.get_or_none(id=target_user_id)
    current_user = await User.get_or_none(user_id=call.from_user.id)

    if target_user and 1 <= rating <= 5:
        existing_rating = await Rating.get_or_none(user=target_user, rated_by=current_user)

        if not existing_rating:
            await Rating.create(user=target_user, rated_by=current_user, score=rating)
            target_user.rating_sum += rating
            target_user.rating_count += 1
            await target_user.save()

            await call.message.answer(f"Вы поставили оценку {rating} пользователю @{target_user.username}.")
        else:
            await call.message.answer("Вы уже ставили оценку этому пользователю.")
    else:
        await call.message.answer("Некорректный запрос.")


async def show_profile(user: User, message: Message):
    profile_text = (
        f"Имя: {user.full_name}\n"
        f"Возраст: {user.age}\n"
        f"О себе: {user.description}\n"
        f"Рейтинг: {user.rating:.2f} (на основе {user.rating_count} оценок)\n"
        f"Никнейм: @{user.main_username}"
    )
    buttons = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 Лайк", callback_data=f"like_{user.id}"),
                InlineKeyboardButton(text="👎 Пропустить", callback_data=f"skip_{user.id}")
            ]
        ]
    )
    if user.photos:
        await message.answer_photo(user.photos[0], caption=profile_text, reply_markup=buttons)
    else:
        await message.answer(profile_text, reply_markup=buttons)


async def show_next_profile(message: Message):
    current_user = await User.get_or_none(user_id=message.from_user.id)

    if current_user:
        interacted_users = await UserInteraction.filter(user=current_user).values_list("target_user_id", flat=True)
        next_user = await User.filter().exclude(id__in=interacted_users).exclude(id=current_user.id).first()

        if next_user:
            await show_profile(next_user, message)
        else:
            await message.answer("Анкеты закончились. Попробуйте позже.")
    else:
        await message.answer("Сначала создайте свою анкету с помощью команды /myself.")
        


@rt.message(Command("view_profiles"))
async def view_profiles_command(message: Message):
    user = await User.get_or_none(user_id=message.from_user.id)
    if user:
        await show_next_profile(message)
    else:
        await message.answer("Сначала создайте свою анкету с помощью команды /myself.")
        
        
@rt.message(Command("top_ratings"))
async def top_ratings_command(message: Message):
    top_users = await User.all().order_by('-rating_sum', '-rating_count').limit(10)
    
    if top_users:
        text = "Топ 10 пользователей по рейтингу:\n"
        for i, user in enumerate(top_users, start=1):
            if user.rating_count > 0:
                rating = user.rating_sum / user.rating_count
            else:
                rating = 0
            text += f"{i}. @{user.username} - Рейтинг: {rating:.2f} ({user.rating_count} оценок)\n"
        await message.answer(text)
    else:
        await message.answer("Пока нет пользователей с рейтингами.")
        
        
@rt.message(Command("top_referrals"))
async def top_referrals_command(message: Message):
    top_users = await User.all().order_by('-referral_count').limit(10)
    current_user = await User.get_or_none(user_id=message.from_user.id)

    if top_users:
        text = "Топ 10 пользователей по рефералам:\n"
        for i, user in enumerate(top_users, start=1):
            text += f"{i}. @{user.username} - Рефералов: {user.referral_count}\n"
        if current_user:
            total_users = await User.filter(referral_count__gt=current_user.referral_count).count()
            rank = total_users + 1

            if rank > 10:
                text += f"\nВы на {rank} месте."
        
        await message.answer(text)
    else:
        await message.answer("Пока нет данных по рефералам.")
