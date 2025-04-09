import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import sqlite3
from aiogram.types import CallbackQuery
from aiogram import Router
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.methods import GetChatMember
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile
from aiogram.types import InputMediaPhoto
from aiogram.fsm.state import State, StatesGroup



from configuration import WELCOME_MESSAGE

API_TOKEN = '7440321214:AAHfytdUiQVj4buqMSHp0dnYvjeoClzsFdQ'
CHANNEL_USERNAME = '@testimshophardy'
CHANNEL_LINK = 'https://t.me/testimshophardy'
YOUTUBE_LINK = 'https://www.youtube.com/@goatyhardy'

# Настройки логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Роутер
router = Router()

async def is_user_subscribed(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "creator", "administrator"]
    except:
        return False


# Функция для получения информации о пользователе из Blacklist
def get_blacklist_info(user_id: int):
    conn = sqlite3.connect('ravito-bot.db')  # Укажи путь к базе данных
    cursor = conn.cursor()
    cursor.execute("SELECT reason, ban_date FROM Blacklist WHERE telegram_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def get_main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Профиль")],
            [KeyboardButton(text="Рынок")],
            [KeyboardButton(text="Настройки профиля")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие 👇"
    )
    return keyboard


# Обработчик команды /start
@router.message(Command("start"))
async def start_messages(message: Message):
    user_id = message.from_user.id

    # Получаем информацию о пользователе из Blacklist
    blacklist_info = get_blacklist_info(user_id)
    
    # Если пользователь в черном списке
    if blacklist_info:
        reason, ban_date = blacklist_info
        await message.answer(f"Увы, вы находитесь в черном списке RAVITO. Дата занесения: {ban_date}. Причина: {reason}")
        return

    # Создаем клавиатуру с кнопкой для подтверждения
    keyboard = InlineKeyboardMarkup(inline_keyboard=[ 
        [InlineKeyboardButton(text="📲 Подтвердить", callback_data="done")]
    ])
    await message.answer(WELCOME_MESSAGE, reply_markup=keyboard, parse_mode="HTML")

# Обработчик нажатия на кнопку Подтвердить
@dp.callback_query(lambda c: c.data == "done")
async def confirm_subscription(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    # Получаем информацию о пользователе из Blacklist
    blacklist_info = get_blacklist_info(user_id)
    
    # Если пользователь в черном списке
    if blacklist_info:
        reason, ban_date = blacklist_info
        await callback_query.answer(f"Увы, вы находитесь в черном списке RAVITO. Дата занесения: {ban_date}. Причина: {reason}")
        return

    # Создаем кнопки для выбора серверов
    buttons = [InlineKeyboardButton(text=str(i), callback_data=f"server_{i}") for i in range(1, 22)]
    
    # Разбиваем кнопки на строки с 7 кнопками в каждой
    inline_keyboard = [buttons[i:i + 7] for i in range(0, len(buttons), 7)]  # Разбиваем на 7 кнопок в ряд

    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    # Отправляем сообщение с клавиатурой
    await callback_query.message.answer(
        "Выберите ваш сервер 🖥️🔑", 
        reply_markup=keyboard
    )

# Обработчик нажатия на сервер
@dp.callback_query(lambda c: c.data.startswith("server_"))
async def handle_server_selection(callback: CallbackQuery):
    server = callback.data.replace("server_", "")
    telegram_id = callback.from_user.id

    # Сохраняем информацию о пользователе в базу данных
    conn = sqlite3.connect('ravito-bot.db')
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO Users (telegram_id, role, server)
            VALUES (?, 'user', ?)
            ON CONFLICT(telegram_id) DO UPDATE SET server=excluded.server;
        """, (telegram_id, server))
        conn.commit()
    finally:
        conn.close()

    # Отправляем сообщение с успешным созданием профиля
    await callback.message.answer(
        f"🎉 Ты успешно создал профиль в моей базе данных! Вот твой профиль:\n"
        f"📱 Номер профиля: {telegram_id}\n"
        f"🖥️ Сервер: {server}\n\n"
        "🚀 Поздравляю на борту\n"
        "Теперь ты можешь начать торговать на выбранном сервере!"

    )
    await callback.answer()
    await callback.message.answer("Меню открыто 👇", reply_markup=get_main_menu())
@router.message(lambda message: message.text == "Профиль")
async def show_profile(message: Message):
    telegram_id = message.from_user.id
    conn = sqlite3.connect('ravito-bot.db')
    cursor = conn.cursor()
    
    # Получаем сервер пользователя
    cursor.execute("SELECT server FROM Users WHERE telegram_id = ?", (telegram_id,))
    result = cursor.fetchone()
    
    # Считаем количество объявлений в таблице Obyavy для данного пользователя
    cursor.execute("SELECT COUNT(*) FROM Obyavy WHERE telegram_id = ?", (telegram_id,))
    ad_count = cursor.fetchone()[0]
    conn.close()

    server = result[0] if result else "не указан"

    profile_text = (
        f"🎉 Вот твой профиль:\n"
        f"📱 Номер профиля: {telegram_id}\n"
        f"🖥️ Сервер: {server}\n\n"
        "🚀 Удачной торговли!"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🚀 Мои Объявления: {ad_count}", callback_data="my_ads")]
    ])

    await message.answer(profile_text, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "my_ads")
async def show_my_ads(callback_query: CallbackQuery):
    telegram_id = callback_query.from_user.id
    conn = sqlite3.connect('ravito-bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, vid, tip_tovara, opisanie, server FROM Obyavy WHERE telegram_id = ?", (telegram_id,))
    ads = cursor.fetchall()
    conn.close()

    if ads:
        text = "📦 Ваши объявления:\n\n"
        for ad in ads:
            text += (f"✉️✉️✉️\n\n🆔 ID: {ad[0]}\n🖥 Сервер: {ad[4]}\n"
                     f"💼 Тип сделки: {ad[1]}\n📦 Тип товара: {ad[2]}\n"
                     f"📝 Описание: {ad[3]}\n\n")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить посты", callback_data="delete_choose")]
        ])
        await callback_query.message.answer(text, reply_markup=keyboard)
    else:
        await callback_query.message.answer("😔 У вас пока нет объявлений.")
    
    await callback_query.answer()


@dp.callback_query(lambda c: c.data == "delete_choose")
async def choose_post_to_delete(callback_query: CallbackQuery):
    telegram_id = callback_query.from_user.id
    conn = sqlite3.connect('ravito-bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Obyavy WHERE telegram_id = ?", (telegram_id,))
    ad_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    if not ad_ids:
        await callback_query.message.answer("😕 У вас нет постов для удаления.")
        return

    # Формируем кнопки: 4 в ряд
    keyboard_rows = []
    row = []
    for i, ad_id in enumerate(ad_ids, start=1):
        row.append(InlineKeyboardButton(text=str(ad_id), callback_data=f"delete_post_{ad_id}"))
        if i % 4 == 0:
            keyboard_rows.append(row)
            row = []
    if row:  # Добавляем остаток
        keyboard_rows.append(row)

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    await callback_query.message.answer("❓ Какой пост желаете удалить?\n👇 Выберите ID поста:", reply_markup=keyboard)
    await callback_query.answer()


@dp.callback_query(lambda c: c.data.startswith("delete_post_"))
async def confirm_delete_post(callback_query: CallbackQuery):
    post_id = int(callback_query.data.split("_")[2])

    conn = sqlite3.connect('ravito-bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT vid, tip_tovara, opisanie, server FROM Obyavy WHERE id = ?", (post_id,))
    post = cursor.fetchone()
    conn.close()

    if not post:
        await callback_query.message.answer("⚠️ Пост не найден.")
        return

    text = (
        f"🔍 Пост для удаления:\n\n"
        f"🆔 ID: {post_id}\n🖥 Сервер: {post[3]}\n"
        f"💼 Тип сделки: {post[0]}\n📦 Тип товара: {post[1]}\n"
        f"📝 Описание: {post[2]}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить удаление", callback_data=f"confirm_delete_{post_id}")]
        ]
    )

    await callback_query.message.answer(text, reply_markup=keyboard)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data.startswith("confirm_delete_"))
async def delete_ad_from_db(callback_query: CallbackQuery):
    post_id = int(callback_query.data.split("_")[2])
    conn = sqlite3.connect('ravito-bot.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Obyavy WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()

    await callback_query.message.answer(f"🗑 Пост с ID {post_id} был успешно удалён!")
    await callback_query.answer()



@router.message(lambda message: message.text == "Настройки профиля")
async def profile_settings(message: Message):
    buttons = [InlineKeyboardButton(text=str(i), callback_data=f"server_{i}") for i in range(1, 22)]
    inline_keyboard = [buttons[i:i + 7] for i in range(0, len(buttons), 7)]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    await message.answer("Выберите ваш сервер 🖥️🔑", reply_markup=keyboard)


@router.message(lambda message: message.text == "Рынок")
async def show_market(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒Купить", callback_data="buy")],
        [InlineKeyboardButton(text="💰Продать", callback_data="sell")]
    ])
    await message.answer("Что желаете купить или продать?", reply_markup=keyboard)

from configuration import MARKET_MESSAGE  # не забудь додати цю змінну в configuration.py

@dp.callback_query(lambda c: c.data in ["buy", "sell"])
async def handle_market_action(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if not await is_user_subscribed(bot, user_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Перейти в Telegram", url=CHANNEL_LINK)],
            [InlineKeyboardButton(text="▶️ YouTube", url=YOUTUBE_LINK)]
        ])
        await callback_query.message.answer(MARKET_MESSAGE, reply_markup=keyboard, parse_mode="HTML")
        await callback_query.answer()
        return

    if callback_query.data == "sell":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚗 Авто", callback_data="sell_auto")],
            [InlineKeyboardButton(text="🎒 Аксессуар", callback_data="sell_accessory")],
            [InlineKeyboardButton(text="🏠 Дом", callback_data="sell_house")],
            [InlineKeyboardButton(text="🏢 Бизнес", callback_data="sell_business")],
        ])
        await callback_query.message.answer("Что желаешь продать?", reply_markup=keyboard)
    elif callback_query.data == "buy":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚗 Авто", callback_data="buy_auto")],
            [InlineKeyboardButton(text="🎒 Аксессуар", callback_data="buy_accessory")],
            [InlineKeyboardButton(text="🏠 Дом", callback_data="buy_house")],
            [InlineKeyboardButton(text="🏢 Бизнес", callback_data="buy_business")]
        ])
        await callback_query.message.answer("Что желаешь купить? 🛍️", reply_markup=keyboard)

class SellAutoStates(StatesGroup):
    waiting_for_form = State()
    confirm_telegram = State()
    waiting_for_photo = State()

@dp.callback_query(lambda c: c.data == "sell_auto")
async def start_sell_auto(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "Хорошо что ты решил продать машину, может она тебе и не нада\n"
        "Запиши пожалуйста по форме ниже:\n"
        "1. Марка твоего чертолета:\n"
        "2. Описание(Стейдж тюнинг, винил, тонировка):\n"
        "3. Цена:\n"
        "4. Как с тобой связатся:\n\n"
        "Пример:\n"
        "1. MBW F90\n"
        "2. ФТ ФБ\n"
        "3. 10.000.000\n"
        "4. в игре 999999"
    )
    await state.set_state(SellAutoStates.waiting_for_form)

@router.message(SellAutoStates.waiting_for_form)
async def receive_form(message: Message, state: FSMContext):
    await state.update_data(form_text=message.text)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="add_telegram_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="add_telegram_no")]
    ])
    await message.answer(
        f"Твоё обьявление\n{message.text}\nЖелаешь добавить свой телеграмм для удобства связи с тобой?",
        reply_markup=keyboard
    )
    await state.set_state(SellAutoStates.confirm_telegram)
@dp.callback_query(lambda c: c.data in ["add_telegram_yes", "add_telegram_no"])
async def handle_telegram_add(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    form_text = data["form_text"]

    telegram_username = callback_query.from_user.username
    if callback_query.data == "add_telegram_yes" and telegram_username:
        form_text += f"\n5. Телеграм продавца: @{telegram_username}"

    await state.update_data(form_text=form_text, telegram_username=telegram_username if callback_query.data == "add_telegram_yes" else None)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="add_photo_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="add_photo_no")]
    ])
    await callback_query.message.answer(
        f"{form_text}\n\nХочешь добавить фото?", reply_markup=keyboard
    )
    await state.set_state(SellAutoStates.waiting_for_photo)

@dp.callback_query(lambda c: c.data in ["add_photo_yes", "add_photo_no"])
async def handle_photo_option(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.data == "add_photo_yes":
        await callback_query.message.answer("Пришли фото 👇")
    else:
        await save_to_database(callback_query, state, photo_url=None)
        await callback_query.message.answer("Объявление успешно сохранено без фото ✅")
        await state.clear()

@router.message(SellAutoStates.waiting_for_photo)
async def receive_photo(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("Пожалуйста, отправь фото.")
        return

    data = await state.get_data()
    photos = data.get("photos", [])

    photo = message.photo[-1]
    photos.append(photo.file_id)
    await state.update_data(photos=photos)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершить", callback_data="finish_uploading_photos")]
    ])
    await message.answer("Фото добавлено. Если хочешь загрузить ещё — пришли их. Когда всё готово, нажми кнопку ниже.", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "finish_uploading_photos")
async def finish_photo_upload(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    photo_urls = ",".join(photos) if photos else None

    await save_to_database(callback_query, state, photo_urls)
    await callback_query.message.answer("Объявление успешно сохранено ✅")
    await state.clear()

class SellAccessoryStates(StatesGroup):
    waiting_for_form = State()
    confirm_telegram = State()
    waiting_for_photo = State()

class AdsBrowsing(StatesGroup):
    ads = State()
    index = State()

@dp.callback_query(lambda c: c.data == "sell_accessory")
async def start_sell_accessory(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "Отлично, что ты решил продать аксессуар!\n"
        "Заполни, пожалуйста, форму:\n"
        "1. Название аксессуара:\n"
        "2. Описание (состояние, размер, особенности):\n"
        "3. Цена:\n"
        "4. Как с тобой связаться:\n\n"
        "Пример:\n"
        "1. Кожаная куртка\n"
        "2. Отличное состояние, размер M\n"
        "3. 5.000\n"
        "4. тел. 123456789"
    )
    await state.set_state(SellAccessoryStates.waiting_for_form)

@router.message(SellAccessoryStates.waiting_for_form)
async def receive_form_accessory(message: Message, state: FSMContext):
    await state.update_data(form_text=message.text)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="add_telegram_yes_accessory")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="add_telegram_no_accessory")]
    ])
    await message.answer(
        f"Твое объявление:\n{message.text}\nДобавить свой Телеграм для удобства связи?",
        reply_markup=keyboard
    )
    await state.set_state(SellAccessoryStates.confirm_telegram)

@dp.callback_query(lambda c: c.data in ["add_telegram_yes_accessory", "add_telegram_no_accessory"])
async def handle_telegram_add_accessory(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    form_text = data["form_text"]
    telegram_username = callback_query.from_user.username
    if callback_query.data == "add_telegram_yes_accessory" and telegram_username:
        form_text += f"\nТелеграм продавца: @{telegram_username}"
    await state.update_data(form_text=form_text,
                            telegram_username=telegram_username if callback_query.data.startswith("add_telegram_yes") else None)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="add_photo_yes_accessory")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="add_photo_no_accessory")]
    ])
    await callback_query.message.answer(f"{form_text}\n\nДобавить фото?", reply_markup=keyboard)
    await state.set_state(SellAccessoryStates.waiting_for_photo)

@dp.callback_query(lambda c: c.data in ["add_photo_yes_accessory", "add_photo_no_accessory"])
async def handle_photo_option_accessory(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.data == "add_photo_yes_accessory":
        await callback_query.message.answer("Пришли фото 👇")
    else:
        await save_to_database(callback_query, state, photo_url=None, tip_tovara="Аксесуар")
        await callback_query.message.answer("Объявление успешно сохранено без фото ✅")
        await state.clear()

@router.message(SellAccessoryStates.waiting_for_photo)
async def receive_photo_accessory(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("Пожалуйста, отправь фото.")
        return
    data = await state.get_data()
    photos = data.get("photos", [])
    photo = message.photo[-1]
    photos.append(photo.file_id)
    await state.update_data(photos=photos)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершить", callback_data="finish_uploading_photos_accessory")]
    ])
    await message.answer("Фото добавлено. Если хочешь добавить еще, отправляй фото. Когда все готово, нажми кнопку ниже.", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "finish_uploading_photos_accessory")
async def finish_photo_upload_accessory(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    photo_urls = ",".join(photos) if photos else None
    await save_to_database(callback_query, state, photo_urls, tip_tovara="Аксесуар")
    await callback_query.message.answer("Объявление успешно сохранено ✅")
    await state.clear()

class SellHouseStates(StatesGroup):
    waiting_for_form = State()
    confirm_telegram = State()
    waiting_for_photo = State()

@dp.callback_query(lambda c: c.data == "sell_house")
async def start_sell_house(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "Отлично, что ты решил продать дом!\n"
        "Заполни, пожалуйста, форму:\n"
        "1. Адрес или район:\n"
        "2. Описание (количество комнат, состояние, площадь):\n"
        "3. Цена:\n"
        "4. Как с тобой связаться:\n\n"
        "Пример:\n"
        "1. ул. Центральная 10\n"
        "2. 3 комнаты, хороший ремонт, 80 кв.м.\n"
        "3. 15.000.000\n"
        "4. тел. 987654321"
    )
    await state.set_state(SellHouseStates.waiting_for_form)

@router.message(SellHouseStates.waiting_for_form)
async def receive_form_house(message: Message, state: FSMContext):
    await state.update_data(form_text=message.text)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="add_telegram_yes_house")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="add_telegram_no_house")]
    ])
    await message.answer(
        f"Твое объявление:\n{message.text}\nДобавить свой Телеграм для связи?",
        reply_markup=keyboard
    )
    await state.set_state(SellHouseStates.confirm_telegram)

@dp.callback_query(lambda c: c.data in ["add_telegram_yes_house", "add_telegram_no_house"])
async def handle_telegram_add_house(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    form_text = data["form_text"]
    telegram_username = callback_query.from_user.username
    if callback_query.data == "add_telegram_yes_house" and telegram_username:
        form_text += f"\nТелеграм продавца: @{telegram_username}"
    await state.update_data(form_text=form_text,
                            telegram_username=telegram_username if callback_query.data.startswith("add_telegram_yes") else None)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="add_photo_yes_house")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="add_photo_no_house")]
    ])
    await callback_query.message.answer(f"{form_text}\n\nДобавить фото?", reply_markup=keyboard)
    await state.set_state(SellHouseStates.waiting_for_photo)

@dp.callback_query(lambda c: c.data in ["add_photo_yes_house", "add_photo_no_house"])
async def handle_photo_option_house(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.data == "add_photo_yes_house":
        await callback_query.message.answer("Пришли фото 👇")
    else:
        await save_to_database(callback_query, state, photo_url=None, tip_tovara="Дом")
        await callback_query.message.answer("Объявление успешно сохранено без фото ✅")
        await state.clear()

@router.message(SellHouseStates.waiting_for_photo)
async def receive_photo_house(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("Пожалуйста, отправь фото.")
        return
    data = await state.get_data()
    photos = data.get("photos", [])
    photo = message.photo[-1]
    photos.append(photo.file_id)
    await state.update_data(photos=photos)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершить", callback_data="finish_uploading_photos_house")]
    ])
    await message.answer("Фото добавлено. Если хочешь добавить еще, отправляй фото. Когда готово, нажми кнопку ниже.", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "finish_uploading_photos_house")
async def finish_photo_upload_house(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    photo_urls = ",".join(photos) if photos else None
    await save_to_database(callback_query, state, photo_urls, tip_tovara="Дом")
    await callback_query.message.answer("Объявление успешно сохранено ✅")
    await state.clear()

class SellBusinessStates(StatesGroup):
    waiting_for_form = State()
    confirm_telegram = State()
    waiting_for_photo = State()

@dp.callback_query(lambda c: c.data == "sell_business")
async def start_sell_business(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "Хорошо, что ты решил продать бизнес!\n"
        "Заполни, пожалуйста, форму:\n"
        "1. Название бизнеса и его отрасль:\n"
        "2. Описание (история, потенциал, состояние бизнеса):\n"
        "3. Цена:\n"
        "4. Как с тобой связаться:\n\n"
        "Пример:\n"
        "1. Кафе \"Солнечный берег\"\n"
        "2. Отличное месторасположение, стабильная клиентура\n"
        "3. 2.500.000\n"
        "4. тел. 5551234"
    )
    await state.set_state(SellBusinessStates.waiting_for_form)

@router.message(SellBusinessStates.waiting_for_form)
async def receive_form_business(message: Message, state: FSMContext):
    await state.update_data(form_text=message.text)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="add_telegram_yes_business")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="add_telegram_no_business")]
    ])
    await message.answer(
        f"Твое объявление:\n{message.text}\nДобавить свой Телеграм для связи?",
        reply_markup=keyboard
    )
    await state.set_state(SellBusinessStates.confirm_telegram)

@dp.callback_query(lambda c: c.data in ["add_telegram_yes_business", "add_telegram_no_business"])
async def handle_telegram_add_business(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    form_text = data["form_text"]
    telegram_username = callback_query.from_user.username
    if callback_query.data == "add_telegram_yes_business" and telegram_username:
        form_text += f"\nТелеграм продавца: @{telegram_username}"
    await state.update_data(form_text=form_text,
                            telegram_username=telegram_username if callback_query.data.startswith("add_telegram_yes") else None)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="add_photo_yes_business")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="add_photo_no_business")]
    ])
    await callback_query.message.answer(f"{form_text}\n\nДобавить фото?", reply_markup=keyboard)
    await state.set_state(SellBusinessStates.waiting_for_photo)

@dp.callback_query(lambda c: c.data in ["add_photo_yes_business", "add_photo_no_business"])
async def handle_photo_option_business(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.data == "add_photo_yes_business":
        await callback_query.message.answer("Пришли фото 👇")
    else:
        await save_to_database(callback_query, state, photo_url=None, tip_tovara="Бизнес")
        await callback_query.message.answer("Объявление успешно сохранено без фото ✅")
        await state.clear()

@router.message(SellBusinessStates.waiting_for_photo)
async def receive_photo_business(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("Пожалуйста, отправь фото.")
        return
    data = await state.get_data()
    photos = data.get("photos", [])
    photo = message.photo[-1]
    photos.append(photo.file_id)
    await state.update_data(photos=photos)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершить", callback_data="finish_uploading_photos_business")]
    ])
    await message.answer("Фото добавлено. Если хочешь добавить еще, отправляй фото. Когда готово, нажми кнопку ниже.", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "finish_uploading_photos_business")
async def finish_photo_upload_business(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    photo_urls = ",".join(photos) if photos else None
    await save_to_database(callback_query, state, photo_urls, tip_tovara="Бизнес")
    await callback_query.message.answer("Объявление успешно сохранено ✅")
    await state.clear()


async def save_to_database(message_or_cb, state: FSMContext, photo_url, tip_tovara="Авто"):
    data = await state.get_data()
    telegram_id = message_or_cb.from_user.id
    conn = sqlite3.connect('ravito-bot.db')
    cursor = conn.cursor()

    cursor.execute("SELECT server FROM Users WHERE telegram_id = ?", (telegram_id,))
    server_row = cursor.fetchone()
    server = server_row[0] if server_row else None

    cursor.execute("""
        INSERT INTO Obyavy (telegram_id, vid, tip_tovara, opisanie, tsena, foto_sylka, telegram_user_name, server)
        VALUES (?, 'Продажа', ?, ?, ?, ?, ?, ?)
    """, (
        telegram_id,
        tip_tovara,
        data['form_text'],
        0.0,  # Если нужно, потом можно распарсить цену
        photo_url or "Фото не прикреплено",
        data.get("telegram_username"),
        server
    ))
    conn.commit()

    cursor.execute("SELECT * FROM Obyavy WHERE telegram_id = ? ORDER BY id DESC LIMIT 1", (telegram_id,))
    last_ad = cursor.fetchone()
    conn.close()

    ad_text = (
        f"📣 Ваше описание:\n\n"
        f"🖥️ Сервер: {last_ad[9]}\n"
        f"🔄 Тип сделки: {last_ad[2]}\n"
        f"📦 Тип товара: {last_ad[3]}\n"
        f"📝 Описание: {last_ad[4]}\n"
    )

    if isinstance(message_or_cb, CallbackQuery):
        msg = message_or_cb.message
    else:
        msg = message_or_cb

    if last_ad[6] and last_ad[6] != "Фото не прикреплено":
        photos = last_ad[6].split(",")
        if len(photos) == 1:
            await msg.answer_photo(photo=photos[0], caption=ad_text)
        else:
            from aiogram.types import InputMediaPhoto
            media = [InputMediaPhoto(media=photos[0], caption=ad_text)]
            media += [InputMediaPhoto(media=photo) for photo in photos[1:]]
            await msg.answer_media_group(media)
    else:
        await msg.answer(f"{ad_text}\n🖼️ Фото не прикреплено")

@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def handle_buy_action(callback_query: CallbackQuery):
    mapping = {
        "buy_auto": "Авто",
        "buy_accessory": "Аксесуар",
        "buy_house": "Дом",
        "buy_business": "Бизнес"
    }
    key = callback_query.data
    if key not in mapping:
        await callback_query.answer("❗ Неверный запрос ❗", show_alert=True)
        return

    selected_tip = mapping[key]
    telegram_id = callback_query.from_user.id

    # Получаем сервер пользователя
    conn = sqlite3.connect('ravito-bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT server FROM Users WHERE telegram_id = ?", (telegram_id,))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        await callback_query.answer("⚠️ Сначала выберите сервер через профиль!", show_alert=True)
        return
    user_server = user_row[0]

    # Ищем объявления с нужным типом и сервером
    cursor.execute(
        "SELECT id, tip_tovara, opisanie, foto_sylka FROM Obyavy WHERE server = ? AND tip_tovara = ?",
        (user_server, selected_tip)
    )
    ads = cursor.fetchall()
    conn.close()

    if not ads:
        await callback_query.message.answer("🙁 На рынке нет предложений для выбранного типа 😢")
        await callback_query.answer()
        return

    for ad in ads:
        ad_id, tip, opisanie, foto_sylka = ad
        text = (
            f"🔔 Предложение на рынке 🔔\n\n"
            f"💼 Тип: {tip}\n"
            f"🖥️ Сервер: {user_server}\n"
            f"📝 Описание: {opisanie}\n"
            f"🆔 ID объявления: {ad_id}\n\n"
            f"🔥 Не упусти свой шанс! 🔥"
        )
        # Формируем клавиатуру с кнопкой "Жалоба"
        complain_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚩 Жалоба", callback_data=f"complain_{ad_id}")]
        ])

        # Если фото прикреплены – отправляем фото с подписью и клавиатурой,
        # иначе отправляем только текст
        if foto_sylka and foto_sylka != "Фото не прикреплено":
            photos = foto_sylka.split(",")
            if len(photos) == 1:
                await callback_query.message.answer_photo(photo=photos[0], caption=text, reply_markup=complain_kb)
            else:
                from aiogram.types import InputMediaPhoto
                media = [InputMediaPhoto(media=photos[0], caption=text)]
                media += [InputMediaPhoto(media=p) for p in photos[1:]]
                # Примечание: к медиагруппе нельзя прикрепить клавиатуру, поэтому отправляем клавиатуру отдельным сообщением
                await callback_query.message.answer_media_group(media)
                await callback_query.message.answer("Нажмите кнопку, если хотите пожаловаться:", reply_markup=complain_kb)
        else:
            await callback_query.message.answer(text, reply_markup=complain_kb)
    await callback_query.answer("✅ Предложения найдены!", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("complain_"))
async def handle_complaint(callback_query: CallbackQuery):
    try:
        ad_id = int(callback_query.data.split("_")[1])
    except (IndexError, ValueError):
        await callback_query.answer("Ошибка! Неверные данные объявления.", show_alert=True)
        return

    conn = sqlite3.connect('ravito-bot.db')
    cursor = conn.cursor()
    # Получаем текущее количество жалоб и описание для данного объявления
    cursor.execute("SELECT zhaloby, opisanie FROM Obyavy WHERE id = ?", (ad_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        await callback_query.answer("Объявление не найдено.", show_alert=True)
        return

    current_zhaloby, opisanie = row
    new_zhaloby = current_zhaloby + 1

    if new_zhaloby >= 5:
        # Если жалоб пять и более – удаляем объявление
        cursor.execute("DELETE FROM Obyavy WHERE id = ?", (ad_id,))
        conn.commit()
        conn.close()
        await callback_query.answer("🚫 Объявление удалено за слишком много жалоб!", show_alert=True)
        try:
            await callback_query.message.edit_text("Это объявление было удалено за слишком много жалоб.")
        except Exception:
            pass
    else:
        # Обновляем описание: можно добавить или обновить часть, где указывается количество жалоб.
        # Здесь мы просто добавляем текст в конец.
        new_opisanie = f"{opisanie} | Жалобы на объявление: {new_zhaloby}"
        cursor.execute("UPDATE Obyavy SET zhaloby = ?, opisanie = ? WHERE id = ?", (new_zhaloby, new_opisanie, ad_id))
        conn.commit()
        conn.close()
        await callback_query.answer(f"🚩 Жалоба принята! Жалоб: {new_zhaloby}", show_alert=True)
        # Можно также обновить сообщение, если нужно (например, через edit_message_caption)


async def main():
    logging.basicConfig(level=logging.INFO)
    dp.include_router(router)
    await dp.start_polling(bot)



if __name__ == "__main__":
    asyncio.run(main())
