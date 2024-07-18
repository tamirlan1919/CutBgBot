import datetime
import sqlite3


def create_users_table():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS my_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        name TEXT,
                        subscription_date TEXT,
                        time_delay INTEGER,
                        unlimited TEXT,
                        status TEXT,
                        role TEXT)
                    ''')
    conn.commit()
    conn.close()


def activity_today():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS activity_today (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        last_activity_date TEXT)
                    ''')
    conn.commit()
    conn.close()



def get_time_msg():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT count FROM time_delay_count')
    time_msg = cursor.fetchone()
    conn.close()
    return  time_msg if time_msg else 15


def create_time_delay():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS time_delay_count (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        count INTEGER)
                    ''')
    conn.commit()
    conn.close()


def get_admin_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM my_users WHERE  user_id = ?", (user_id,))
    existing_user = cursor.fetchone()
    conn.close()
    return existing_user[0]


def get_all_user_ids():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM my_users")
    total_users = cursor.fetchall()
    print(total_users)
    conn.close()

    return total_users

def count_total_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM my_users")
    total_users = cursor.fetchone()[0]
    conn.close()
    return total_users


def count_new_users_this_month():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    current_month = datetime.datetime.now().strftime("%Y-%m")
    cursor.execute("SELECT COUNT(*) FROM my_users WHERE subscription_date LIKE ?", (f"{current_month}%",))
    new_users_this_month = cursor.fetchone()[0]
    conn.close()
    return new_users_this_month


def count_new_users_last_month():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Получаем текущую дату
    current_date = datetime.datetime.now()
    # Получаем первый день текущего месяца
    first_day_current_month = current_date.replace(day=1)
    # Получаем последний день прошлого месяца
    last_day_last_month = first_day_current_month - datetime.timedelta(days=1)
    # Форматируем дату прошлого месяца в формат YYYY-MM
    last_month = last_day_last_month.strftime("%Y-%m")

    # Выполняем запрос к базе данных, чтобы получить количество новых пользователей за прошлый месяц
    cursor.execute("SELECT COUNT(*) FROM my_users WHERE subscription_date LIKE ?", (f"{last_month}%",))
    new_users_last_month = cursor.fetchone()[0]

    conn.close()
    return new_users_last_month
def count_new_users_last_month():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Получаем текущую дату
    current_date = datetime.datetime.now()
    # Получаем первый день текущего месяца
    first_day_current_month = current_date.replace(day=1)
    # Получаем последний день прошлого месяца
    last_day_last_month = first_day_current_month - datetime.timedelta(days=1)
    # Форматируем дату прошлого месяца в формат YYYY-MM
    last_month = last_day_last_month.strftime("%Y-%m")

    # Выполняем запрос к базе данных, чтобы получить количество новых пользователей за прошлый месяц
    cursor.execute("SELECT COUNT(*) FROM my_users WHERE subscription_date LIKE ?", (f"{last_month}%",))
    new_users_last_month = cursor.fetchone()[0]

    conn.close()
    return new_users_last_month


def count_active_users_today():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # Получаем текущую дату
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    print(today)
    cursor.execute("SELECT COUNT(*) FROM activity_today WHERE DATE(last_activity_date) = ?", (today,))
    active_users_count = cursor.fetchone()[0]
    print(active_users_count)
    conn.close()
    return active_users_count


def count_blocked_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Подсчитываем количество заблокированных пользователей
    cursor.execute("SELECT COUNT(*) FROM my_users WHERE status = 'sent'")
    blocked_count = cursor.fetchone()[0]

    conn.close()
    return blocked_count

def get_all_admin_from_bd():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(role) FROM my_users WHERE role = 'admin'")
    existing_user = cursor.fetchone()
    conn.close()
    return existing_user[0]

def get_all_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id,name FROM my_users")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_unlimited_person(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT unlimited FROM my_users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()
    conn.close()
    return existing_user


def get_role_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM my_users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()
    conn.close()
    return existing_user


def get_status_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM my_users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()
    conn.close()
    return existing_user

def update_unlimited_on(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE my_users SET unlimited = 'ON' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_delay_time():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT count FROM time_delay_count")
    time_delay = cursor.fetchone()
    conn.close()
    return time_delay


def update_unlimited_off(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE my_users SET unlimited = 'OFF' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def update_status_join(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE my_users SET status = 'join' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def update_status_kick(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE my_users SET status = 'kick' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def update_role_user_admin(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE my_users SET role = 'admin' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def update_role_user_person(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE my_users SET role = 'user' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()



def update_bonus(count):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE my_users SET time_delay = ?", (count,))
    conn.commit()
    # Проверяем, есть ли записи в таблице time_delay_count
    cursor.execute("SELECT COUNT(*) FROM time_delay_count")
    result = cursor.fetchone()

    if result[0] == 0:
        # Если таблица пуста, вставляем данные
        cursor.execute("INSERT INTO time_delay_count (count) VALUES (?)", (count,))
    else:
        # Если таблица не пуста, обновляем данные
        cursor.execute("UPDATE time_delay_count SET count = ?", (count,))

    conn.commit()
    conn.close()


def insert_or_update_user(username):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Получаем текущую дату и время
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Проверяем, существует ли пользователь с таким именем в базе данных
    cursor.execute("SELECT COUNT(*) FROM activity_today WHERE user_id = ?", (username,))
    user_exists = cursor.fetchone()[0]

    if user_exists:
        # Если пользователь существует, обновляем его последнюю активность
        cursor.execute("UPDATE activity_today SET last_activity_date = ? WHERE user_id = ?", (current_datetime, username))
    else:
        # Если пользователь не существует, вставляем новую запись
        cursor.execute("INSERT INTO activity_today (user_id, last_activity_date) VALUES (?, ?)", (username, current_datetime))

    conn.commit()
    conn.close()



def get_last_activity(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT last_activity_date FROM activity_today WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id,))
    last_activity = cursor.fetchone()
    conn.close()
    return last_activity[0] if last_activity else None

def add_user(user_id, name, subscription_date, time_delay, unlimited, status, role):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    try:
        # Check if the user ID already exists in the database
        cursor.execute("SELECT * FROM my_users WHERE user_id = ?", (user_id,))
        existing_user = cursor.fetchone()
        # If the user already exists, return without inserting
        if existing_user:
            return

        # Insert the new user into the database
        cursor.execute(
            "INSERT INTO my_users (user_id, name, subscription_date, time_delay, unlimited,status,role ) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, name, subscription_date, time_delay , unlimited, status, role))
        conn.commit()
    finally:
        # Close the cursor and connection
        cursor.close()
        conn.close()

