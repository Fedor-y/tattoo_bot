import sqlite3

def init_db():
    conn = sqlite3.connect('tattoo_studio.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS appointments 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date TEXT, time TEXT,
                       service_type TEXT, photo_id TEXT, status TEXT DEFAULT 'confirmed')''')
    conn.commit()
    conn.close()

def add_user(user_id, username):
    conn = sqlite3.connect('tattoo_studio.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

def has_active_appointment(user_id):
    conn = sqlite3.connect('tattoo_studio.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM appointments WHERE user_id = ? AND status = 'confirmed'", (user_id,))
    return cursor.fetchone() is not None

def add_appointment(user_id, date, time, service_type, photo_id):
    conn = sqlite3.connect('tattoo_studio.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO appointments (user_id, date, time, service_type, photo_id) VALUES (?, ?, ?, ?, ?)", 
                   (user_id, date, time, service_type, photo_id))
    conn.commit()
    conn.close()

def delete_appointment(user_id, date, time):
    conn = sqlite3.connect('tattoo_studio.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE user_id = ? AND date = ? AND time = ?", (user_id, date, time))
    conn.commit()
    conn.close()

def close_appointment(user_id, date, time):
    conn = sqlite3.connect('tattoo_studio.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE appointments SET status = 'closed' WHERE user_id = ? AND date = ? AND time = ?", (user_id, date, time))
    conn.commit()
    conn.close()

def get_appointments_by_date(date):
    conn = sqlite3.connect('tattoo_studio.db')
    cursor = conn.cursor()
    cursor.execute("SELECT time, service_type FROM appointments WHERE date = ? AND status IN ('confirmed', 'closed')", (date,))
    data = cursor.fetchall()
    conn.close()
    return data

def get_all_appointments():
    conn = sqlite3.connect('tattoo_studio.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT users.user_id, users.username, appointments.date, appointments.time, 
                             appointments.service_type, appointments.photo_id FROM appointments 
                      JOIN users ON appointments.user_id = users.user_id WHERE appointments.status = 'confirmed' ''')
    data = cursor.fetchall()
    conn.close()
    return data

def get_history_appointments():
    conn = sqlite3.connect('tattoo_studio.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT users.user_id, users.username, appointments.date, appointments.time, 
                             appointments.service_type, appointments.photo_id FROM appointments 
                      JOIN users ON appointments.user_id = users.user_id WHERE appointments.status = 'closed' ''')
    data = cursor.fetchall()
    conn.close()
    return data
