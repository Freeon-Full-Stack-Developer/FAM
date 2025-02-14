
import os
import sqlite3
import datetime
import telebot
from telebot import types

# Конфигурация
OWNER_ID = int(input("Введите Ваш Telegram ID: "))
TOKEN = input("Введите токен Вашего Telegram бота: ")
BASE_DIR = os.path.dirname(os.path.abspath(''))
DB_PATH = os.path.join(BASE_DIR, 'data', 'data.db')
DATA_DIR = os.path.join(BASE_DIR, 'chats')
Premium = False
# Инициализация бота
bot = telebot.TeleBot(TOKEN)
user_states = {}

# Инициализация БД
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                blocked BOOLEAN DEFAULT FALSE)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                date TIMESTAMP,
                direction TEXT)''')
conn.commit()

@bot.message_handler(commands=['start'])
def start(message):
    """Обработчик команды /start"""
    if message.from_user.id == OWNER_ID:
        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [
            types.InlineKeyboardButton("📨 Чаты", callback_data='chats'),
            types.InlineKeyboardButton("🆕 Новый диалог", callback_data='new_chats'),
            types.InlineKeyboardButton("📬 Рассылки", callback_data='mails'),
            types.InlineKeyboardButton("⚙️ Настройки", callback_data='settings'),
            types.InlineKeyboardButton("⭐️ Получить Premium", callback_data='premium')
        ]
        markup.add(*buttons)
        bot.send_message(
            message.chat.id,
            f"👋 Привет, {message.from_user.username}! Выберите действие:",
            reply_markup=markup
        )
    else:
        bot.send_message(
            message.chat.id,
            "👋 Привет! Напишите ваше сообщение, и я передам его."
        )


def mailer(message):

    try:
            # Добавляем состояние для ожидания ID пользователей
        user_states[message.chat.id] = {'state': 'waiting_mail_ids'}
        bot.send_message(message.chat.id, "🆔 Отправьте ID пользователей через запятую:")
    except Exception as e:
        print(f"Ошибка в mailer: {e}")


# Обработчик для получения ID
@bot.message_handler(func=lambda message: message.chat.id in user_states
                     and user_states[message.chat.id]['state'] == 'waiting_mail_ids')
def get_mail_ids(message):
    try:
        # Сохраняем ID пользователей
        user_states[message.chat.id]['ids'] = message.text.split(',')
        # Переходим к запросу количества повторений
        user_states[message.chat.id]['state'] = 'waiting_mail_repeats'
        bot.send_message(message.chat.id, "🔢 Укажите количество повторений рассылки:")
    except Exception as e:
        print(f"Ошибка получения ID: {e}")

@bot.message_handler(func=lambda message: message.chat.id in user_states
                     and user_states[message.chat.id]['state'] == 'waiting_mail_repeats')
def get_mail_repeats(message):
    try:
        # Проверяем, что введено число
        if message.text.isdigit():
            repeats = int(message.text)
            user_states[message.chat.id]['repeats'] = repeats
            # Переходим к запросу текста рассылки
            user_states[message.chat.id]['state'] = 'waiting_mail_text'
            bot.send_message(message.chat.id, "📝 Отправьте текст рассылки:")
        else:
            bot.send_message(message.chat.id, "❌ Пожалуйста, введите число.")
    except Exception as e:
        print(f"Ошибка получения количества повторений: {e}")
# Обработчик для получения текста рассылки
@bot.message_handler(func=lambda message: message.chat.id in user_states
                                          and user_states[message.chat.id]['state'] == 'waiting_mail_text')
@bot.message_handler(func=lambda message: message.chat.id in user_states
                                          and user_states[message.chat.id]['state'] == 'waiting_mail_text')
def send_mail(message):
    try:
        user_ids = user_states[message.chat.id]['ids']
        text = message.text
        repeats = user_states[message.chat.id]['repeats']

        success = 0
        errors = 0

        for _ in range(repeats):  # Повторяем рассылку указанное количество раз
            for user_id in user_ids:
                try:
                    # Чистим ID от пробелов и преобразуем в int
                    uid = int(user_id.strip())
                    bot.send_message(uid, text)
                    success += 1
                except Exception as e:
                    errors += 1
                    print(f"Ошибка отправки для {user_id}: {e}")
                    bot.send_message(OWNER_ID, f"Ошибка отправки для {user_id}: {e}")

        # Удаляем состояние
        del user_states[message.chat.id]

        # Отчет
        report = f"✅ Успешно: {success}\n❌ Ошибок: {errors}"
        bot.send_message(message.chat.id, report)

    except Exception as e:
        print(f"Ошибка рассылки: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка при рассылке")


def show_chats_list(message):
    """Показывает список активных чатов"""
    try:
        cursor.execute("SELECT DISTINCT user_id FROM messages")
        chats = cursor.fetchall()

        if not chats:
            bot.send_message(message.chat.id, "📭 Нет активных чатов")
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        for chat in chats:
            user_id = chat[0]
            cursor.execute("SELECT username, first_name FROM users WHERE id = ?", (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                username = user_data[0] if user_data[0] else "Unknown"
                name = user_data[1] if user_data[1] else "Пользователь"
                button_text = f"{name} (@{username})" if username else name
            else:
                button_text = f"Пользователь (ID: {user_id})"

            markup.add(types.InlineKeyboardButton(
                text=button_text,
                callback_data=f'chat_{user_id}'
            ))

        bot.send_message(message.chat.id, "📂 Список активных чатов:", reply_markup=markup)

    except Exception as e:
        bot.send_message(message.chat.id, "❌ Ошибка при загрузке списка чатов")
        print(repr(e))


def new_chats(message):
    try:
        bot.send_message(message.chat.id, "🆔 Отправьте ID пользователя:")
        user_states[message.chat.id] = {'state': 'waiting_for_id', 'recipient_id': None}  # Устанавливаем состояние ожидания ID
    except Exception as e:
        bot.answer_callback_query(OWNER_ID, "❌ Произошла ошибка")
        print(repr(e))

@bot.message_handler(func=lambda message: message.chat.id in user_states and user_states[message.chat.id]['state'] == 'waiting_for_id')
def get_recipient_id(message):
    try:
        if message.text.isdigit() and 8 <= len(message.text) <= 12:
            new_id = int(message.text)  # Конвертируем в int
            print(f"Получен ID: {new_id}")
            cursor.execute(f"""CREATE TABLE IF NOT EXISTS user_{new_id} (
                                                        col_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                        id INT,
                                                        text TEXT,
                                                        date TEXT);
                                                    """)
            conn.commit()
            user_states[message.chat.id]['recipient_id'] = new_id
            bot.send_message(message.chat.id, "Отправь мне текст сообщения")
            user_states[message.chat.id]['state'] = 'waiting_for_message'
        else:
            bot.send_message(message.chat.id, "Пожалуйста, отправь корректный ID (8-12 цифр).")
    except Exception as e:
        print("Ошибка в get_recipient_id:", repr(e))  # Детальный вывод ошибки
        bot.send_message(message.chat.id, "❌ Ошибка при отправке сообщения")


@bot.message_handler(func=lambda message: message.chat.id in user_states and user_states[message.chat.id][
    'state'] == 'waiting_for_message')
def get_message_text(message):
    if message.text:
        mess = message.text
        recipient_id = user_states[message.chat.id]['recipient_id']

        # Добавляем получателя в таблицу users
        cursor.execute('''
            INSERT OR IGNORE INTO users (id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (recipient_id, None, "Чат", None))

        # Сохраняем сообщение с user_id получателя и правильным направлением
        cursor.execute('''
            INSERT INTO messages (user_id, message, date, direction)
            VALUES (?, ?, ?, ?)
        ''', (recipient_id, mess, message.date, 'outgoing'))

        conn.commit()

        # Отправляем сообщение
        bot.send_message(recipient_id, mess)
        bot.send_message(message.chat.id, f"Сообщение отправлено пользователю {recipient_id}.")
        save_message_to_history(recipient_id, f"🟢{mess}", 'ИСХОДЯЩЕЕ')

        del user_states[message.chat.id]
    else:
        bot.send_message(message.chat.id, "Пожалуйста, отправь корректное сообщение.")

def premium():
    print("Premium")

def create_chat_folder(user_id):
    """Создает папки для хранения данных чата"""
    chat_dir = os.path.join(DATA_DIR, f'user_{user_id}')
    media_dir = os.path.join(chat_dir, 'media')
    os.makedirs(media_dir, exist_ok=True)
    return chat_dir

def save_message_to_history(user_id, message, direction):
    """Сохраняет сообщение в историю чата"""
    chat_dir = create_chat_folder(user_id)
    history_path = os.path.join(chat_dir, 'history.txt')
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(history_path, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {direction}: {message}\n")

def save_media(user_id, file_id, file_type):
    """Сохраняет медиафайлы в папку пользователя"""
    chat_dir = create_chat_folder(user_id)
    media_dir = os.path.join(chat_dir, 'media')

    try:
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_path = os.path.join(media_dir, file_info.file_path.split('/')[-1])

        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        return file_path
    except Exception as e:
        print(f"Ошибка сохранения медиа: {e}")
        return None



@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Обработчик inline-кнопок"""
    try:
        if call.data == 'chats':
            show_chats_list(call.message)
        elif call.data == 'mails':
            mailer(call.message)
        elif call.data == 'new_chats':
            new_chats(call.message)
        elif call.data == 'settings':
            show_settings(call.message)
        elif call.data.startswith('chat_'):
            handle_chat_selection(call)
        elif call.data.startswith('block_'):
            user_id = int(call.data.split('_')[1])
            cursor.execute("UPDATE users SET blocked = 1 WHERE id = ?", (user_id,))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ Пользователь заблокирован")
        elif call.data.startswith('unblock_'):
            user_id = int(call.data.split('_')[1])
            cursor.execute("UPDATE users SET blocked = 0 WHERE id = ?", (user_id,))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ Пользователь разблокирован")
        elif call.data.startswith('history_'):
            user_id = int(call.data.split('_')[1])
            get_history(user_id, call.message)
        elif call.data.startswith('clear_'):
            user_id = int(call.data.split('_')[1])
            clear_history(user_id, call.message)
        elif call.data.startswith('reply_'):
            user_id = int(call.data.split('_')[1])
            user_states[call.message.chat.id] = {'state': 'waiting_reply', 'recipient_id': user_id}
            bot.send_message(call.message.chat.id, "📝 Введите ответное сообщение:")
        elif call.data.startswith('premium'):
            premium()

    except Exception as e:
        print(f"Ошибка обработки callback: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


def get_history(user_id: int, message: types.Message) -> None:
    """Получает историю переписки"""
    print(user_id)
    chat_dir = create_chat_folder(user_id)
    history_path = os.path.join(chat_dir, 'history.txt')

    if not os.path.exists(history_path):
        bot.send_message(message.chat.id, "История переписки пуста")
        return

    try:
        with open(history_path, 'r', encoding='utf-8') as f:
            history = f.read()
            # Отправляем частями, если история слишком большая
            for i in range(0, len(history), 4000):
                bot.send_message(message.chat.id, history[i:i+4000])
    except Exception as e:
        print(f"Ошибка чтения истории: {e}")

def clear_history(user_id: int, message: types.Message) -> None:
    """Очищает историю переписки"""
    chat_dir = create_chat_folder(user_id)
    history_path = os.path.join(chat_dir, 'history.txt')

    try:
        if os.path.exists(history_path):
            os.remove(history_path)
            bot.send_message(message.chat.id, "✅ История переписки очищена")
        else:
            bot.send_message(message.chat.id, "❌ История переписки уже пуста")
    except Exception as e:
        print(f"Ошибка очистки истории: {e}")
        bot.send_message(message.chat.id, "❌ Ошибка при очистке истории")

def handle_chat_selection(call):
    """Обрабатывает выбор конкретного чата"""
    try:
        user_id = call.data.split('_')[1]
        bot.send_message(call.message.chat.id, f"🔍 Вы выбрали чат с ID: {user_id}")

        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [
            types.InlineKeyboardButton("✅ Разблокировать", callback_data=f'unblock_{user_id}'),
            types.InlineKeyboardButton("❌ Блокировать", callback_data=f'block_{user_id}'),
            types.InlineKeyboardButton("🗄 История", callback_data=f'history_{user_id}'),
            types.InlineKeyboardButton("🗑 Очистить", callback_data=f'clear_{user_id}'),
            types.InlineKeyboardButton("📨 Написать", callback_data=f'reply_{user_id}')

        ]
        markup.add(*buttons)
        bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=markup)
    except Exception as e:
        print(f"Ошибка обработки выбора чата: {e}")

def start_new_chat(message):
    """Начинает новый диалог"""
    bot.send_message(message.chat.id, "🆔 Отправьте ID пользователя:")
    user_states[message.from_user.id] = {'state': 'waiting_id'}

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id]['state'] == 'waiting_id')
def handle_new_id(message):
    """Обрабатывает ввод ID для нового диалога"""
    if message.text.isdigit() and 8 <= len(message.text) <= 12:
        user_id = int(message.text)
        user_states[message.from_user.id] = {
            'state': 'waiting_message',
            'user_id': user_id
        }
        bot.send_message(message.chat.id, "📝 Введите сообщение для отправки:")
    else:
        bot.send_message(message.chat.id, "❌ Некорректный ID. Введите 8-12 цифр.")



def show_settings(message):
    """Показывает настройки бота"""
    settings_text = f"""⚙️ Настройки бота:

ID владельца: {OWNER_ID}
Токен бота: {TOKEN}
Premium: {Premium}
Версия: 2.0
"""
    bot.send_message(message.chat.id, settings_text)


@bot.message_handler(func=lambda message: message.chat.id in user_states
                                          and user_states[message.chat.id]['state'] == 'waiting_reply')
def handle_reply_message(message):
    try:
        recipient_id = user_states[message.chat.id]['recipient_id']
        mess = message.text

        # Сохраняем сообщение
        cursor.execute('''
            INSERT INTO messages (user_id, message, date, direction)
            VALUES (?, ?, ?, ?)
        ''', (recipient_id, mess, message.date, 'outgoing'))
        conn.commit()

        # Отправляем сообщение
        bot.send_message(recipient_id, mess)
        bot.send_message(message.chat.id, f"✉️ Ответ отправлен пользователю {recipient_id}")
        save_message_to_history(recipient_id, f"🟢{mess}", 'ИСХОДЯЩЕЕ')

        del user_states[message.chat.id]

    except Exception as e:
        print(f"Ошибка отправки ответа: {e}")
        bot.send_message(message.chat.id, "❌ Ошибка при отправке ответа")

@bot.message_handler(func=lambda m: m.from_user.id != OWNER_ID and not m.text.startswith('/'))
def handle_user_message(message):
    """Обрабатывает сообщения от пользователей"""
    try:
        user = message.from_user

        # Сохраняем пользователя в БД
        cursor.execute('INSERT OR IGNORE INTO users (id, username, first_name, last_name) VALUES (?,?,?,?)',
                       (user.id, user.username, user.first_name, user.last_name))

        # Определяем текст сообщения
        msg_text = message.text or message.caption or "[Медиа-сообщение]"

        # Сохраняем сообщение
        cursor.execute('INSERT INTO messages (user_id, message, date, direction) VALUES (?,?,?,?)',
                       (user.id, msg_text, message.date, 'incoming'))
        conn.commit()
        save_message_to_history(user.id, f"🔴{msg_text}", 'ВХОДЯЩЕЕ')

        # Сохраняем медиафайлы
        if message.photo:
            save_media(user.id, message.photo[-1].file_id, 'photo')
            bot.send_message(OWNER_ID, f"{user.id}  {message.photo[-1].file_id}")
        elif message.document:
            save_media(user.id, message.document.file_id, 'document')
        elif message.audio:
            save_media(user.id, message.audio.file_id, 'audio')

        # Отправляем уведомление владельцу
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🚫 Блокировать", callback_data=f'block_{user.id}'),
            types.InlineKeyboardButton("📨 Ответить", callback_data=f'reply_{user.id}')
        )

        bot.send_message(
            OWNER_ID,
            f"📩 Новое сообщение от {user.first_name} (@{user.username}):\n\n{msg_text}",
            reply_markup=markup
        )

    except Exception as e:
        print(f"Ошибка обработки сообщения: {e}")

if __name__ == '__main__':
    print("🤖 Бот запущен...")
    bot.polling(none_stop=True)
