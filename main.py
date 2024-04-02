from aiogram import Bot, Dispatcher
from aiogram.types import FSInputFile
import asyncio
import logging
from aiogram.types import Message
from aiogram import types
from aiogram import F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
import config
import json
import re

API_TOKEN = config.TOKEN


class PostState(StatesGroup):
    waiting_state = State()
    choosing_caption = State()
    choosing_image = State()
    btn_input_caption = State()
    btn_input_url = State()
    btn_finish = State()
    btn_edit = State()
    btn_generate = State()
    btn_delete = State()


# main_menu
view_post = 'Просмотреть пост'
edit_post = 'Редактировать пост'

# edit_menu
change_text = 'Описание'
change_photo = 'Фото'
change_buttons = 'Кнопки'
select_mode = 'Выбрать режим'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()


def load_data_jsonfile():
    with open('./core/data/data.json', 'r', encoding='utf-8') as json_file:
        try:
            data = json.load(json_file)
        except:
            return None
    return data


def isDataNone():
    data = load_data_jsonfile()
    if data is None:
        posts = {}
    else:
        posts = data
    return posts


# Словарь для хранения данных о посте
posts = isDataNone()


async def save_data_infile():
    with open('./core/data/data.json', 'w') as json_file:
        json.dump(posts, json_file)


def get_main_keyboard():
    kb_obj = [
        [
            types.KeyboardButton(text=view_post),
            types.KeyboardButton(text=edit_post)
        ],
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb_obj, resize_keyboard=True, )
    return keyboard


def get_editor_keyboard():
    kb_obj = [
        [
            types.KeyboardButton(text=change_text),
            types.KeyboardButton(text=change_photo),
            types.KeyboardButton(text=change_buttons),
            types.KeyboardButton(text=select_mode)
        ],
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb_obj, resize_keyboard=True)
    return keyboard


async def get_dynamic_keyboard(KeyboardButtonList: list):
    keyboard = InlineKeyboardBuilder()
    line_button = []
    for lines_button in KeyboardButtonList:
        line_button.append(len(lines_button))
        for button in lines_button:
            text_button = button['text']
            url_button = button['url']
            callback_button = button['callback_data']
            keyboard.button(text=text_button, url=url_button, callback_data=callback_button)
    keyboard.adjust(*line_button)
    return keyboard


# Команда для начала работы с постом
@dp.message(Command("start"))
async def start_command(message: Message):
    keyboard = get_main_keyboard()
    await message.answer('''Привет! 👋

    🤖 Я бот по созданию карточек товаров любой категории.

    Тут вы можете выбрать режим:''',
                         reply_markup=keyboard)


# Обработка кнопки "Просмотр поста"
@dp.message(F.text.lower() == view_post.lower())
async def view_mode(message: Message):
    user_id = str(message.from_user.id)
    if user_id not in posts:
        await create_default_post(message.chat.id, user_id)
        await save_data_infile()
    await message.answer("Ваш пост выглядит так. Выберите 'Редактирование', чтобы внести изменения.")
    await send_post(message.chat.id, posts[user_id])


# Функция для отправки поста
async def send_post(chat_id, post):
    caption_text = post.get('caption_text', '')
    url_photo = post.get('url_photo', '')
    InlineKeyboardB = post.get('inline_keyboard', [])
    photo = FSInputFile(url_photo)
    keyboard = await get_dynamic_keyboard(InlineKeyboardB)
    await bot.send_photo(chat_id, photo=photo, caption=caption_text, reply_markup=keyboard.as_markup())


# Функция для создания стандартного поста
async def create_default_post(chat_id, user_id):
    posts[user_id] = {"caption_text": "Вау! Это панда!",
                      "url_photo": "./core/resources/default.jpg",
                      "inline_keyboard": [
                          [
                              {
                                  'text': "Panda",
                                  'url': "https://www.youtube.com/watch?v=hAOoMtRstJ8",
                                  'callback_data': "btn0"
                              }
                          ]
                      ]}


@dp.message(F.text.lower() == edit_post.lower())
async def edit_mode(message: Message):
    user_id = str(message.from_user.id)
    keyboard = get_editor_keyboard()
    if user_id in posts:
        await message.answer("Вы можете редактировать свой пост. Используйте кнопки для изменений.",
                             reply_markup=keyboard)
        await send_post(message.chat.id, posts[user_id])
    else:
        await create_default_post(message.chat.id, user_id)
        await message.answer("Вы можете редактировать свой пост. Используйте кнопки для изменений.",
                             reply_markup=keyboard)
        await send_post(message.chat.id, posts[user_id])


@dp.message(F.text.lower() == select_mode.lower())
async def cmd_select_mode(message: types.Message, bot: Bot, state: FSMContext):
    keyboard = get_main_keyboard()
    chat_id_for_send = message.from_user.id
    await bot.send_message(chat_id_for_send, text='Выберите режим', reply_markup=keyboard)
    await state.set_state(None)


@dp.message(StateFilter(None), F.text.lower() == change_photo.lower())
async def start_edit_photo(message: Message, state: FSMContext):
    await message.answer(text=f'Отправьте картинку:')
    # Устанавливаем пользователю состояние "выбирает фото"
    await state.set_state(PostState.choosing_image)


@dp.message(StateFilter(PostState.choosing_image), F.photo)
async def edit_photo(message: Message, state: FSMContext, bot: Bot):
    user_id = str(message.from_user.id)
    image_url = f"./core/resources/{message.photo[-1].file_id}.jpg"
    posts[user_id]['url_photo'] = image_url
    await save_data_infile()
    await bot.download(
        message.photo[-1],
        destination=image_url
    )
    await state.set_state(None)
    await send_post(message.chat.id, posts[user_id])


@dp.message(StateFilter(PostState.choosing_image))
async def err_send_edit_img(message: Message, bot: Bot):
    await bot.send_message(message.from_user.id, text='Вы отправили сообщение неверного формата. Пожалуйста отправьте '
                                                      'картинку.')


@dp.message(StateFilter(None), F.text.lower() == change_text.lower())
async def start_edit_caption(message: Message, state: FSMContext):
    await message.answer(text=f'Введите описание поста:')
    # Устанавливаем пользователю состояние "ввода описания поста"
    await state.set_state(PostState.choosing_caption)


@dp.message(StateFilter(PostState.choosing_caption), F.text)
async def edit_caption(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    caption_text = message.text
    posts[user_id]['caption_text'] = caption_text  # save data
    await save_data_infile()
    await state.set_state(None)
    await send_post(message.chat.id, posts[user_id])


# смайлики принимает как текст
@dp.message(StateFilter(PostState.choosing_caption))
async def err_send_edit_caption(message: Message, bot: Bot):
    await bot.send_message(message.from_user.id,
                           text='Вы отправили сообщение неверного формата. Введите описание в строку ввода')


# edit_btn
add_btn = 'Добавить'
save_btn = 'Сохранить'
del_btn = 'Удалить'


def get_editor_button():
    kb_obj = [
        [
            types.KeyboardButton(text=add_btn),
            types.KeyboardButton(text=save_btn),
            types.KeyboardButton(text=del_btn),
            types.KeyboardButton(text=select_mode)
        ],
    ]

    keyboard = types.ReplyKeyboardMarkup(keyboard=kb_obj, resize_keyboard=True)
    return keyboard


temp_keyboard = {}


@dp.message(StateFilter(None), F.text.lower() == change_buttons.lower())
async def editing_btn(message: types.Message, bot: Bot, state: FSMContext):
    user_id = str(message.from_user.id)
    temp_keyboard[user_id] = posts[user_id]
    keyboard = get_editor_button()
    await bot.send_message(user_id, text='Вы вошли в режим редактирования кнопок, выберите один из пунктов меню ниже',
                           reply_markup=keyboard)
    await state.set_state(PostState.btn_edit)


@dp.message(StateFilter(PostState.btn_edit), F.text.lower() == del_btn.lower())
async def del_btn_f(message: types.Message, bot: Bot, state: FSMContext):
    user_id = str(message.from_user.id)
    old_keyboard = await get_dynamic_keyboard(
        temp_keyboard[user_id]['inline_keyboard'])
    await bot.send_message(user_id, text='Введите название ссылки, которую хотите удалить.\nСейчас ваши ссылки '
                                         'выглядят так:',
                           reply_markup=old_keyboard.as_markup())
    await state.set_state(PostState.btn_delete)


@dp.message(StateFilter(PostState.btn_delete))
async def remove_btn(message: types.Message, bot: Bot, state: FSMContext):
    user_id = str(message.from_user.id)
    text_to_remove = message.text
    for key, value in temp_keyboard.items():
        if 'inline_keyboard' in value:
            for sublist in value['inline_keyboard']:
                for item in sublist:
                    if 'text' in item and item['text'] == text_to_remove:
                        sublist.remove(item)  # Удаляем словарь из списка
                        break  # Выходим из цикла, так как словарь уже удален
                if not sublist:  # Если список пуст, удаляем его
                    value['inline_keyboard'].remove(sublist)
            break  # Выходим из цикла, так как словарь уже обработан

    new_keyboard = await get_dynamic_keyboard(
        temp_keyboard[user_id]['inline_keyboard'])

    is_btn = len(temp_keyboard[user_id]['inline_keyboard'])
    if is_btn == 0:
        await bot.send_message(user_id, text='Вы удалили все ссылки, нажмите на "добавить кнопку"',
                               reply_markup=new_keyboard.as_markup())
    else:
        await bot.send_message(user_id, text='Чтобы сохранить изменения нажмите "Сохранить"\nТеперь ваши '
                                             'ссылки выглядят так:',
                               reply_markup=new_keyboard.as_markup())
    await state.set_state(None)


@dp.message(F.text.lower() == save_btn.lower())
async def save_btn_f(message: types.Message, bot: Bot, state: FSMContext):
    user_id = str(message.from_user.id)
    keyboard = get_editor_button()
    new_keyboard = await get_dynamic_keyboard(
        temp_keyboard[user_id]['inline_keyboard'])
    json_dump = new_keyboard.as_markup().model_dump_json()  # преобразование в json новую клаву
    temp_json_dict = json.loads(json_dump)  # преобразование в словарь новую клаву
    posts[user_id]['inline_keyboard'] = temp_json_dict['inline_keyboard']
    await save_data_infile()
    await bot.send_message(user_id, text='Ваши ссылки успешно сохранены!', reply_markup=keyboard)
    await state.set_state(PostState.btn_edit)


@dp.message(StateFilter(PostState.btn_edit), F.text.lower() == add_btn.lower())
async def add_btn_f(message: types.Message, bot: Bot, state: FSMContext):
    user_id = str(message.from_user.id)
    keyboard = get_editor_button()
    await bot.send_message(user_id, text='Отправьте мне список URL-кнопок в одном сообщении.\nПожалуйста, следуйте '
                                         'этому формату:\n\n'
                                         'Кнопка 1 - http://example1.com\n'
                                         'Кнопка 2 - http://example2.com\n'
                                         '\n\nИспользуйте разделитель |, чтобы добавить несколько кнопок в один ряд.\n'
                                         'Прмер:\n'
                                         'Кнопка 1 - http://example1.com | Кнопка 2 - http://example2.com\n'
                                         'Кнопка 3 - http://example3.com | Кнопка 4 - http://example4.com',
                           reply_markup=keyboard)
    await state.set_state(PostState.btn_generate)


async def parse_string_to_dict(string):
    buttons = []
    # Разделение строки по разделителю '|'
    parts = re.split(r'\s*\|\s*', string)
    for part in parts:
        # Разделение текста и URL по дефису и удаление лишних пробелов
        text, url = [x.strip() for x in part.split('-')]
        buttons.append({'text': text, 'url': url})
    return buttons


@dp.message(StateFilter(PostState.btn_generate))
async def generate_new_keyboard(message: types.Message, bot: Bot, state: FSMContext):
    user_id = str(message.from_user.id)
    input_string = message.text
    new_btn = []
    test_btn = []
    button_list = []
    if '\n' in input_string:
        temp_btn = input_string.split('\n')
        for item in temp_btn:
            new_btn.append(re.split(r'\s*\|\s*', item))
    else:
        new_btn.append(re.split(r'\s*\|\s*', input_string))

    number_lines = len(new_btn)
    is_btn = len(posts[user_id]['inline_keyboard'])
    number_btn_row = []
    number_btn_row.append(is_btn)
    for item in new_btn:
        number_btn_row.append(len(item))
        for it in item:
            test_btn.append(it.replace(' ', '').split('-'))

    for text, url in test_btn:
        button_list.append({'text': text, 'url': url, 'callback_data': 'callback_data'})

    old_keyboard = await get_dynamic_keyboard(
        posts[user_id]['inline_keyboard'])

    for lines_button in button_list:
        text_button = lines_button['text']
        url_button = lines_button['url']
        callback_button = lines_button['callback_data']
        old_keyboard.button(text=text_button, url=url_button, callback_data=callback_button)
    old_keyboard.adjust(*number_btn_row)
    print(number_btn_row)
    json_test = old_keyboard.as_markup().model_dump_json()  # преобразование в json новую клаву
    temp_json_dict = json.loads(json_test)  # преобразование в словарь новую клаву
    temp_keyboard[user_id]['inline_keyboard'] = temp_json_dict['inline_keyboard']
    await state.set_state(PostState.btn_edit)
    await bot.send_message(message.from_user.id, text='Чтобы сохранить изменения нажмите "Сохранить"\nТеперь ваши '
                                                      'ссылки выглядят так:', reply_markup=old_keyboard.as_markup())


async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s'
                                                   '(%(filename)s).%(funcName)s(%(lineno)d) - %(message)s')
    # db.create_tables()
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
