import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import ContentType, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from transformers import pipeline
from PIL import Image
from config import *
import io
from base import *
from state import *
from aplha import  *
import redis





# Настройка логирования
logging.basicConfig(level=logging.INFO)
state_bot = True
# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())
MAX_FILE_SIZE_MB = 5
# Инициализация модели
pipe = pipeline("image-segmentation", model="briaai/RMBG-1.4", trust_remote_code=True)


create_users_table()
activity_today()
create_time_delay()
users_per_page = 3  # Установка количества пользователей на странице

original_photo_storage = {}
processed_photo_storage = {}

@dp.message_handler(content_types=[ContentType.PHOTO, ContentType.DOCUMENT])
async def handle_docs_photo(message: types.Message):
    unique_key = f"{message.chat.id}:{message.message_id}"
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    original_photo_storage[unique_key] = file_id  # Store the original file_id
    keyboard = InlineKeyboardMarkup(row_width=2)
    button_add_alpha = InlineKeyboardButton("👆Расширить фон", callback_data=f"add_alpha:{unique_key}")
    button_add_alpha_new = InlineKeyboardButton("🆕 Расширить фон", callback_data=f"new_add_alpha:{unique_key}")
    keyboard.add(button_add_alpha,button_add_alpha_new)


    if state_bot:
        user_id = message.from_user.id
        status = get_status_user(user_id)
        unlimited = get_unlimited_person(user_id)
        role = get_role_user(user_id)

        if status[0] != 'join':
            await message.reply('Отказано в доступе')
            return

        if unlimited[0] != 'ON' and role[0] != 'admin':
            last_activity = get_last_activity(user_id)
            if last_activity:
                last_activity_time = datetime.datetime.strptime(last_activity, '%Y-%m-%d %H:%M:%S')
                current_time = datetime.datetime.now()
                time_diff = (current_time - last_activity_time).total_seconds()
                time_msg = get_time_msg()  # получаем требуемый интервал

                if time_diff < time_msg[0]:
                    await message.reply(
                        f"Пожалуйста, подождите {time_msg[0] - time_diff:.0f} секунд перед отправкой следующего фото.")
                    return

        # Получаем информацию о файле и загружаем его
        response = await message.reply(f"⌛️")
        file_info = await bot.get_file(file_id)
        photo_bytes = io.BytesIO()
        await bot.download_file(file_info.file_path, destination=photo_bytes)
        photo_bytes.seek(0)
        file_size_mb = photo_bytes.getbuffer().nbytes / (1024 * 1024)

        if file_size_mb > MAX_FILE_SIZE_MB:
            await message.reply(
                f"Размер файла превышает {MAX_FILE_SIZE_MB} МБ. Пожалуйста, загрузите изображение меньшего размера.")
            return

        # Обработка изображения
        pil_image = Image.open(photo_bytes)
        pillow_image = pipe(pil_image)  # применение маски
        pillow_image = process_image_with_alpha_border(pillow_image)  # добавление альфа-границы

        # Сохранение обработанного изображения
        output = io.BytesIO()
        pillow_image.save(output, format='PNG')
        output.name = "ZeroBG_bot_@nmntzh.png"
        output.seek(0)
        await response.delete()
        processed_file_info = await bot.send_document(message.chat.id, document=output, reply_markup=keyboard)
        processed_file_id = processed_file_info.document.file_id
        processed_photo_storage[unique_key] = processed_file_id  # Store processed image file_id

        insert_or_update_user(user_id)
    else:
        await message.reply(SORRY)







@dp.callback_query_handler(lambda c: c.data.startswith('add_alpha'))
async def process_add_alpha(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    unique_key = callback_query.data.split(':')[1] + ':' + callback_query.data.split(':')[2]
    processed_file_id = processed_photo_storage.get(unique_key)

    if not processed_file_id:
        await callback_query.message.reply("Обработанное фото не найдено.")
        return

    # Processed image retrieval and further processing for expanding the background
    file_info = await bot.get_file(processed_file_id)
    photo_bytes = io.BytesIO()
    await bot.download_file(file_info.file_path, destination=photo_bytes)
    photo_bytes.seek(0)

    # Open and process image using Pillow for adding alpha border
    image = Image.open(photo_bytes)
    processed_image = process_image_with_alpha_border_second(image)

    # Save the expanded image and send it back
    output = io.BytesIO()
    processed_image.save(output, format='PNG')
    output.name = "ZeroBG_bot_@nmntzh.png"
    output.seek(0)
    await bot.send_document(callback_query.message.chat.id, document=output)
    output.close()


@dp.message_handler(commands=['add_alpha'],state='*')
async def prompt_command_for_photo(message: types.Message, state: FSMContext):
    await Form.waiting_for_new_photo.set()
    await message.reply("Пожалуйста, отправьте новое фото для расширения фона.")




@dp.callback_query_handler(lambda c: c.data.startswith('new_add_alpha'))
async def prompt_for_photo(callback_query: types.CallbackQuery, state: FSMContext):
    await Form.waiting_for_new_photo.set()
    await callback_query.message.reply("Пожалуйста, отправьте новое фото для расширения фона.")



@dp.message_handler(content_types=[ContentType.PHOTO, ContentType.DOCUMENT], state=Form.waiting_for_new_photo)
async def handle_new_photo(message: types.Message, state: FSMContext):
    await state.finish()
    photo_bytes = io.BytesIO()

    # Check if the incoming message is a photo or a document
    if message.photo:
        await message.photo[-1].download(destination_file=photo_bytes)
    elif message.document and message.document.mime_type.startswith('image/'):
        await message.document.download(destination_file=photo_bytes)
    else:
        await message.reply("Пожалуйста, отправьте изображение.")
        return

    photo_bytes.seek(0)
    image = Image.open(photo_bytes)

    # Process and expand the background using your custom function
    processed_image = process_image_with_alpha_border_second(image)

    # Save the processed image and send it back
    output = io.BytesIO()
    processed_image.save(output, format='PNG')
    output.name = "ZeroBG_bot_@nmntzh.png"
    output.seek(0)
    await bot.send_document(message.chat.id, document=output)
    output.close()
#
# @dp.message_handler(content_types=[ContentType.PHOTO, ContentType.DOCUMENT])
# async def handle_docs_photo(message: types.Message):
#     if state_bot:
#         photo_bytes = io.BytesIO()
#         user_id = message.from_user.id
#         status = get_status_user(user_id)
#         unlimited = get_unlimited_person(user_id)
#         role = get_role_user(user_id)
#         if status[0] == 'join':
#             if unlimited[0] == 'ON' or role[0] == 'admin':
#                 if message.content_type == ContentType.PHOTO:
#                     response = await message.reply(f"⌛️ ")
#                     message_id = response.message_id
#                     photo = message.photo[-1]
#                     await photo.download(destination_file=photo_bytes)
#                 elif message.content_type == ContentType.DOCUMENT:
#                     if message.document.mime_type.startswith('image/') or message.document.mime_type.startswith('application/octet-stream'):
#                         response = await message.reply(f"⌛️ ")
#                         message_id = response.message_id
#                         await message.document.download(destination_file=photo_bytes)
#                     else:
#                         await message.reply("Пожалуйста, отправьте файл изображения.")
#                         return
#                 else:
#                     await message.reply("Не поддерживаемый тип файла.")
#                     return
#
#                 photo_bytes.seek(0)
#                 file_size_mb = photo_bytes.getbuffer().nbytes / (1024 * 1024)
#                 if file_size_mb > MAX_FILE_SIZE_MB:
#                     await message.reply(
#                         f"Размер файла превышает {MAX_FILE_SIZE_MB} МБ. Пожалуйста, загрузите изображение меньшего размера.")
#                     return
#
#                 pil_image = Image.open(photo_bytes)
#                 pillow_image = pipe(pil_image)  # применение маски
#                 pillow_image = process_image_with_alpha_border(pillow_image)  # добавление альфа-границы
#
#                 # Сохранение результата в буфер
#                 output = io.BytesIO()
#                 pillow_image.save(output, format='PNG')
#                 output.name = "processed_image.png"  # задаем имя файла
#                 output.seek(0)
#
#                 await bot.send_document(message.chat.id, document=output)
#                 await response.delete()
#
#                 insert_or_update_user(user_id)
#             elif unlimited[0] != 'ON':
#                 last_activity = get_last_activity(user_id)
#                 print('время - ', last_activity)
#                 if last_activity:
#                     last_activity_time = datetime.datetime.strptime(last_activity, '%Y-%m-%d %H:%M:%S')
#                     current_time = datetime.datetime.now()
#                     time_diff = (current_time - last_activity_time).total_seconds()
#                     time_msg = get_time_msg()  # получаем требуемый интервал
#
#                     if time_diff < time_msg[0]:
#                         await message.reply(
#                             f"Пожалуйста, подождите {time_msg[0] - time_diff:.0f} секунд перед отправкой следующего фото.")
#                         return
#
#                     if message.content_type == ContentType.PHOTO:
#                         response = await message.reply(f"⌛️ ")
#                         message_id = response.message_id
#                         photo = message.photo[-1]
#                         await photo.download(destination_file=photo_bytes)
#                     elif message.content_type == ContentType.DOCUMENT:
#                         if message.document.mime_type.startswith('image/') or message.document.mime_type.startswith('application/octet-stream'):
#                             response = await message.reply(f"⌛️ ")
#                             message_id = response.message_id
#                             await message.document.download(destination_file=photo_bytes)
#                         else:
#                             await message.reply("Пожалуйста, отправьте файл изображения.")
#                             return
#                     else:
#                         await message.reply("Не поддерживаемый тип файла.")
#                         return
#
#                     photo_bytes.seek(0)
#                     file_size_mb = photo_bytes.getbuffer().nbytes / (1024 * 1024)
#                     if file_size_mb > MAX_FILE_SIZE_MB:
#                         await message.reply(
#                             f"Размер файла превышает {MAX_FILE_SIZE_MB} МБ. Пожалуйста, загрузите изображение меньшего размера.")
#                         return
#
#                     pil_image = Image.open(photo_bytes)
#                     pillow_image = pipe(pil_image)  # применение маски
#                     pillow_image = process_image_with_alpha_border(pillow_image)  # добавление альфа-границы
#
#                     # Сохранение результата в буфер
#                     output = io.BytesIO()
#                     pillow_image.save(output, format='PNG')
#                     output.name = "processed_image.png"  # задаем имя файла
#                     output.seek(0)
#
#                     await bot.send_document(message.chat.id, document=output)
#                     await response.delete()
#
#                     insert_or_update_user(user_id)
#                 else:
#                     if message.content_type == ContentType.PHOTO:
#                         response = await message.reply(f"⌛️ ")
#                         message_id = response.message_id
#                         await message.reply(f"⌛️ ")
#                         photo = message.photo[-1]
#                         await photo.download(destination_file=photo_bytes)
#                     elif message.content_type == ContentType.DOCUMENT:
#                         if message.document.mime_type.startswith('image/'):
#                             response = await message.reply(f"⌛️")
#                             message_id = response.message_id
#                             await message.document.download(destination_file=photo_bytes)
#                         else:
#                             await message.reply("Пожалуйста, отправьте файл изображения.")
#                             return
#                     else:
#                         await message.reply("Не поддерживаемый тип файла.")
#                         return
#
#                     photo_bytes.seek(0)
#                     file_size_mb = photo_bytes.getbuffer().nbytes / (1024 * 1024)
#                     if file_size_mb > MAX_FILE_SIZE_MB:
#                         await message.reply(
#                             f"Размер файла превышает {MAX_FILE_SIZE_MB} МБ. Пожалуйста, загрузите изображение меньшего размера.")
#                         return
#
#                     pil_image = Image.open(photo_bytes)
#                     pillow_image = pipe(pil_image)  # применение маски
#                     pillow_image = process_image_with_alpha_border(pillow_image)  # добавление альфа-границы
#
#                     # Сохранение результата в буфер
#                     output = io.BytesIO()
#                     pillow_image.save(output, format='PNG')
#                     output.name = "processed_image.png"  # задаем имя файла
#                     output.seek(0)
#
#                     await bot.send_document(message.chat.id, document=output)
#                     await response.delete()
#
#                     insert_or_update_user(user_id)
#         else:
#             await bot.send_message(message.chat.id, text='Отказано в доступе', parse_mode='HTML')
#     else:
#         await bot.send_message(message.chat.id, text=SORRY, parse_mode='HTML')
#
#
#




@dp.message_handler(commands=['start'],state="*")
async def handle_docs_photo(message: types.Message, state: FSMContext):
    await state.finish()
    count = get_delay_time()
    delay_time = count[0] if count is not None else 15


    if message.from_user.username == None:
        add_user(message.from_user.id, message.from_user.first_name,
                 datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), delay_time,  'OFF', 'join', 'user')
    else:
        add_user(message.from_user.id, message.from_user.username,
                 datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), delay_time,  'OFF', 'join', 'user')

    await bot.send_message(message.chat.id, 'Отправь картинку у которой ты хочешь удалить фон.')

#Admin panel ---------------


@dp.message_handler(commands=['admin'],state='*')
async def handle_admin(message: types.Message, state: FSMContext ):
    await state.finish()
    # Проверяем, является ли отправитель сообщения администратором
    admin = get_admin_user(message.chat.id)

    if message.chat.id not in admin_ids and not admin == 'admin':
        await message.reply("У вас нет доступа к админ-панели.")
        return

    # Создание клавиатуры админ-панели
    keyboard = types.InlineKeyboardMarkup(row_width=1, resize_keyboard=True)
    keyboard.add(types.InlineKeyboardButton(text="Состояние бота 🤖", callback_data='status'),
                 types.InlineKeyboardButton(text="Рассылка 📝", callback_data='newsletter'),
                 types.InlineKeyboardButton(text="Аналитика 📊", callback_data='analytics'))

    await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=keyboard)


#------------------------------



@dp.callback_query_handler(lambda call: call.data == "delay_day", state="*")
async def handle_day_bonus(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.message.chat.id, 'Введите новую зарержку между запросами в секундах')
    await BonusDayState.bonus.set()

@dp.message_handler(state=BonusDayState.bonus)
async def bon_state(message: types.Message, state: FSMContext):
    print('Попал')
    try:
        new_bonus_count = int(message.text)
        if new_bonus_count < 0:
            await message.reply("Количество секунд не может быть отрицательным")
            return
        update_bonus(new_bonus_count)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='analytics'))
        await message.reply(f'Задержка между запросами обновлена на: {new_bonus_count}', reply_markup=keyboard)
        await state.finish()  # завершаем состояние FSM после обработки сообщения
    except ValueError:
        await message.reply("Пожалуйста, введите число.")


@dp.callback_query_handler(lambda call: call.data == "analytics", state="*")
async def handle_bot_analitycs(callback_query: types.CallbackQuery):
    global state_bot
    chat_id = callback_query.from_user.id
    message_id = callback_query.message.message_id
    keyboard = types.InlineKeyboardMarkup(row_width=1, resize_keyboard=True)
    keyboard.add(types.InlineKeyboardButton(text="Найти пользователя 🔎", callback_data='search_user'))
    keyboard.add(types.InlineKeyboardButton(text='Задержка между запросами ⌛️', callback_data='delay_day'))
    keyboard.add(types.InlineKeyboardButton(text="Назад ⏪", callback_data='back_menu'))
    text = 'Статистика 📊'
    count = count_total_users()
    this_month = count_new_users_this_month()
    last_month = count_new_users_last_month()
    today_activity = count_active_users_today()
    text += f'\n\n🔢 Общее'
    text += f'\n└ Кол-во пользователей = {count}'
    text += f'\n└ Кол-во новых пользователей за этот месяц = {this_month}'
    text += f'\n└ Кол-во пользователей за прошлый месяц = {last_month}'
    text += f'\n└ Заблокировали бота = {count_blocked_users()}'
    text += f'\n└ Активные пользователи сегодня = {today_activity}'
    text += f'\n└ Кол-во владельцев = {len(admin_ids)}'
    text += f'\n└ Кол-во администраторов = {get_all_admin_from_bd()}'

    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=keyboard)

@dp.callback_query_handler(lambda call: call.data == "search_user", state="*")
async def handle_bot_search_user(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)

    users = get_all_users()
    global users_per_page  # Установка количества пользователей на странице
    current_page = 0

    async def send_users_page(chat_id, message_id, page):
        start_index = page * users_per_page
        end_index = min((page + 1) * users_per_page, len(users))
        user_names = users[start_index:end_index]

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for i in range(0, len(user_names)):
            user_id, user_name = user_names[i]  # Распаковываем tuple
            keyboard.add(types.InlineKeyboardButton(text=user_name, callback_data=f'select_user_{user_id}_{user_name}'))

        if page > 0:
            keyboard.row(types.InlineKeyboardButton(text="Назад ⏪", callback_data='back'))
        if end_index < len(users):
            keyboard.row(types.InlineKeyboardButton(text="Дальше ⏩", callback_data='next'))

        keyboard.row(
            types.InlineKeyboardButton(text="Поиск по логину 🔍", callback_data='search_by_username'),
            types.InlineKeyboardButton(text='Назад в меню', callback_data='analytics')
        )

        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Выберите пользователя:", reply_markup=keyboard)

    await send_users_page(callback_query.message.chat.id, callback_query.message.message_id, current_page)


# Обработчик нажатия на кнопку "Поиск по логину"
@dp.callback_query_handler(lambda call: call.data == "search_by_username", state="*")
async def handle_search_by_username(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Отмена и назад в меню',callback_data='search_user'))
    await bot.send_message(callback_query.from_user.id, "Введите логин пользователя:",reply_markup=keyboard)
    await SearchUserState.InputUsername.set()


# Обработчик текстового сообщения с логином пользователя
@dp.message_handler(state=SearchUserState.InputUsername, content_types=types.ContentTypes.TEXT)
async def handle_username_input(message: types.Message, state: FSMContext):
    username = message.text
    users = get_all_users()

    found_users = [(user_id, user_name) for user_id, user_name in users if username.lower() in user_name.lower()]

    if found_users:
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for user_id, user_name in found_users:
            keyboard.add(types.InlineKeyboardButton(text=user_name, callback_data=f'select_user_{user_id}_{user_name}'))

        await message.reply("Найдены пользователи:", reply_markup=keyboard)
    else:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text='Назад в меню', callback_data='search_user'))
        await message.reply("Пользователи с таким логином не найдены.", reply_markup=keyboard)

    await state.finish()  # Завершаем состояние после обработки запроса поиска



# Обработчик нажатия на кнопку "Дальше" или "Назад"
@dp.callback_query_handler(lambda call: call.data in ['next', 'back'], state="*")
async def handle_pagination(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)

    users = get_all_users()
    global users_per_page # Установка количества пользователей на странице
    current_page = await state.get_state() or 0

    current_page = int(current_page)  # Преобразуем текущую страницу в целое число

    if callback_query.data == 'next':
        current_page += 1
    elif callback_query.data == 'back':
        current_page -= 1

    await state.set_state(current_page)

    await send_users_page(callback_query.message.chat.id, callback_query.message.message_id, current_page)



async def send_users_page(chat_id, message_id, page):
    global users_per_page
    users = get_all_users()
    start_index = page * users_per_page
    end_index = min((page + 1) * users_per_page, len(users))
    user_names = users[start_index:end_index]

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for i in range(0, len(user_names)):
        user_id, user_name = user_names[i]  # Распаковываем tuple
        user_name = str(user_name)  # Преобразуем в строку, если необходимо
        keyboard.add(types.InlineKeyboardButton(text=user_name, callback_data=f'select_user_{user_id}_{user_name}'))

    if page > 0:
        keyboard.row(types.InlineKeyboardButton(text="Назад ⏪", callback_data='back'))
    if end_index < len(users):
        keyboard.row(types.InlineKeyboardButton(text="Дальше ⏩", callback_data='next'))

    keyboard.row(
        types.InlineKeyboardButton(text="Поиск по логину 🔍", callback_data='search_by_username'),
        types.InlineKeyboardButton(text='Назад в меню', callback_data='analytics')
    )

    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Выберите пользователя:", reply_markup=keyboard)



@dp.callback_query_handler(lambda call: call.data.startswith('select_user_'), state="*")
async def handle_select_user(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)

    user_name = callback_query.data.split('_')[-1]
    user_id = callback_query.data.split('_')[-2]
    chat_id = callback_query.from_user.id
    message_id = callback_query.message.message_id
    unlimited = get_unlimited_person(user_id)
    role = get_role_user(user_id)
    status = get_status_user(user_id)
    keyboard = types.InlineKeyboardMarkup()
    unl_btn = ''
    role_btn = ''
    status_btn = ''
    text = f'ID: <b>{user_id}</b>'
    text += f'\nЛогин: <b> @{user_name}</b>'


    if unlimited[0] == 'ON':
        text += '\nБезлимит: <b>включен</b>'
        unl_btn = types.InlineKeyboardButton(text='Отключить безлимит',
                                             callback_data=f'off_unlimited_{user_id}_{user_name}')
    else:
        text += '\nБезлимит: <b>отключен</b>'
        unl_btn = types.InlineKeyboardButton(text='Включить безлимит',
                                             callback_data=f'on_unlimited_{user_id}_{user_name}')

    if role[0] == 'user':
        text += f'\n\nРоль: <b>пользователь</b>'
        role_btn = types.InlineKeyboardButton(text=f'Назначить администратором',
                                              callback_data=f'appoint_admin_{user_id}_{user_name}')
    else:
        text += f'\n\nРоль: <b>администратор</b>'
        role_btn = types.InlineKeyboardButton(text=f'Назначить пользователем',
                                              callback_data=f'appoint_user_{user_id}_{user_name}')

    if status[0] == 'join':
        status_btn = types.InlineKeyboardButton(text=f'Заблокировать',
                                                callback_data=f'block_user_{user_id}_{user_name}')
    else:
        status_btn = types.InlineKeyboardButton(text=f'Разблокировать',
                                                callback_data=f'unblock_user_{user_id}_{user_name}')

    keyboard.add(role_btn)
    keyboard.add(status_btn)

    keyboard.add(unl_btn)
    keyboard.add(types.InlineKeyboardButton(text="Назад ⏪", callback_data='search_user'))
    await bot.edit_message_text(chat_id=callback_query.message.chat.id, message_id=message_id, text=text,
                                reply_markup=keyboard, parse_mode='html')


# Заблокировать пользователя
@dp.callback_query_handler(lambda call: call.data.startswith('block_user_'), state="*")
async def handle_block_user(callback_query: types.CallbackQuery, state: FSMContext):
    user_name = callback_query.data.split('_')[-1]
    user_id = callback_query.data.split('_')[-2]
    chat_id = callback_query.from_user.id
    message_id = callback_query.message.message_id

    update_status_kick(user_id)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Назад ⏪", callback_data=f'select_user_{user_id}_{user_name}'))
    await bot.edit_message_text(chat_id=callback_query.message.chat.id, message_id=message_id,
                                text='Пользователь заблокирован', reply_markup=keyboard, parse_mode='html')
    await bot.answer_callback_query(callback_query_id=callback_query.id)

@dp.callback_query_handler(lambda call: call.data.startswith('unblock_user_'), state="*")
async def handle_unblock_user(callback_query: types.CallbackQuery, state: FSMContext):
    user_name = callback_query.data.split('_')[-1]
    user_id = callback_query.data.split('_')[-2]
    chat_id = callback_query.from_user.id
    message_id = callback_query.message.message_id
    update_status_join(user_id)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Назад ⏪", callback_data=f'select_user_{user_id}_{user_name}'))
    await bot.edit_message_text(chat_id=callback_query.message.chat.id, message_id=message_id,
                                text='Пользователь разблокирован', reply_markup=keyboard, parse_mode='html')
    await bot.answer_callback_query(callback_query_id=callback_query.id)


# Назначить администратором

@dp.callback_query_handler(lambda call: call.data.startswith('appoint_admin_'), state="*")
async def handle_appoint_admin(callback_query: types.CallbackQuery, state: FSMContext):
    user_name = callback_query.data.split('_')[-1]
    user_id = callback_query.data.split('_')[-2]
    chat_id = callback_query.from_user.id
    message_id = callback_query.message.message_id
    update_role_user_admin(user_id)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Назад ⏪", callback_data=f'select_user_{user_id}_{user_name}'))
    await bot.edit_message_text(chat_id=callback_query.message.chat.id, message_id=message_id,
                                text='Пользователь назначен администратором', reply_markup=keyboard, parse_mode='html')
    await bot.answer_callback_query(callback_query_id=callback_query.id)


# Разблокировать пользователя

@dp.callback_query_handler(lambda call: call.data.startswith('appoint_user_'), state="*")
async def handle_appoint_user(callback_query: types.CallbackQuery, state: FSMContext):
    user_name = callback_query.data.split('_')[-1]
    user_id = callback_query.data.split('_')[-2]
    chat_id = callback_query.from_user.id
    message_id = callback_query.message.message_id
    update_role_user_person(user_id)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Назад ⏪", callback_data=f'select_user_{user_id}_{user_name}'))
    await bot.edit_message_text(chat_id=callback_query.message.chat.id, message_id=message_id,
                                text='Пользователь удален из списка администраторов', reply_markup=keyboard,
                                parse_mode='html')
    await bot.answer_callback_query(callback_query_id=callback_query.id)


# Включить безлмит


@dp.callback_query_handler(lambda call: call.data.startswith('off_unlimited_'), state="*")
async def handle_off_unlimited(callback_query: types.CallbackQuery, state: FSMContext):
    user_name = callback_query.data.split('_')[-1]
    user_id = callback_query.data.split('_')[-2]
    chat_id = callback_query.from_user.id
    message_id = callback_query.message.message_id
    update_unlimited_off(user_id)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Назад ⏪", callback_data=f'select_user_{user_id}_{user_name}'))
    await bot.edit_message_text(chat_id=callback_query.message.chat.id, message_id=message_id, text='Безлмит отключен',
                                reply_markup=keyboard, parse_mode='html')
    await bot.answer_callback_query(callback_query_id=callback_query.id)


# Выключить безлмит


@dp.callback_query_handler(lambda call: call.data.startswith('on_unlimited_'), state="*")
async def handle_off_unlimited(callback_query: types.CallbackQuery, state: FSMContext):
    user_name = callback_query.data.split('_')[-1]
    user_id = callback_query.data.split('_')[-2]
    chat_id = callback_query.from_user.id
    message_id = callback_query.message.message_id
    update_unlimited_on(user_id)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Назад ⏪", callback_data=f'select_user_{user_id}_{user_name}'))
    await bot.edit_message_text(chat_id=callback_query.message.chat.id, message_id=message_id, text='Безлмит включен',
                                reply_markup=keyboard, parse_mode='html')
    await bot.answer_callback_query(callback_query_id=callback_query.id)


@dp.callback_query_handler(lambda call: call.data == "newsletter", state="*")
async def handle_bot_newsletter(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query_id=callback_query.id)  # Отмечаем кнопку как обработанную
    await NewsletterText.text.set()
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Отмена и возврат в меню',callback_data='back_menu'))
    await bot.send_message(callback_query.from_user.id, "Введите текст для отправки:",reply_markup=keyboard)

@dp.message_handler(content_types=[types.ContentType.TEXT,types.ContentType.PHOTO], state=NewsletterText.text)
async def process_mixed_content(message: types.Message, state: FSMContext):
    # Initialize variables to store text and photo
    text = ""
    photo = None
    # Check if the message contains both text and photo
    if message.caption:
        text = message.caption
    if message.text:
        text = message.text
    if message.photo:
        photo = message.photo[-1].file_id

    # Get all user IDs from the database
    all_user_ids = get_all_user_ids()

    # Send the mixed content to each user individually
    for user_id in all_user_ids:
        try:
            if text and photo:
                # If both text and photo are present, send them together
                await bot.send_photo(user_id[0], photo, caption=text)
            elif text:
                # If only text is present, send the text
                await bot.send_message(user_id[0], text)
            elif photo:
                # If only photo is present, send the photo
                await bot.send_photo(user_id[0], photo)
        except Exception as e:
            print(f"Failed to send mixed content newsletter to user {user_id}: {e}")

    await state.finish()
    await message.answer("Сообщение успешно отправлен всем пользователям.")
    keyboard = types.InlineKeyboardMarkup(row_width=1, resize_keyboard=True)
    keyboard.add(types.InlineKeyboardButton(text="Состояние бота 🤖",callback_data='status'), types.InlineKeyboardButton(text="Рассылка 📝",callback_data='newsletter'),
                 types.InlineKeyboardButton(text="Аналитика 📊",callback_data='analytics'))

    await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data == "status", state="*")
async def handle_bot_state(callback_query: types.CallbackQuery):
    global state_bot
    chat_id = callback_query.from_user.id
    message_id = callback_query.message.message_id

    if state_bot:
        keyboard = types.InlineKeyboardMarkup()

        keyboard.add(types.InlineKeyboardButton(text="Выключить бота 🔴", callback_data='toggle_off'))
        keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='back_menu'))
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Бот успешно включен 🟢",
                                    reply_markup=keyboard)
    else:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Включить бота 🟢", callback_data='toggle_on'))
        keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='back_menu'))

        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Бот выключен 🔴",
                                    reply_markup=keyboard)


@dp.callback_query_handler(lambda call: call.data.startswith("toggle_"), state="*")
async def toggle_bot(callback_query: types.CallbackQuery):
    global state_bot
    message = callback_query.message
    chat_id = message.chat.id
    message_id = message.message_id

    if callback_query.data == "toggle_on":
        state_bot = True
        await handle_bot_state(callback_query)
    elif callback_query.data == "toggle_off":
        state_bot = False
        await handle_bot_state(callback_query)


@dp.callback_query_handler(lambda call: call.data == "back_menu", state="*")
async def handle_bot_back(callback_query: types.CallbackQuery):
    global state_bot
    chat_id = callback_query.from_user.id
    message_id = callback_query.message.message_id
    keyboard = types.InlineKeyboardMarkup(row_width=1, resize_keyboard=True)
    keyboard.add(types.InlineKeyboardButton(text="Состояние бота 🤖", callback_data='status'),
                 types.InlineKeyboardButton(text="Рассылка 📝", callback_data='newsletter'),
                 types.InlineKeyboardButton(text="Аналитика 📊", callback_data='analytics'))

    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Выберите опцию", reply_markup=keyboard)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
