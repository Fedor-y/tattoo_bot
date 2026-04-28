from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="записаться")],
        [KeyboardButton(text="связь с ОСЧ"), KeyboardButton(text="анон сообщение мастеру")]
    ], resize_keyboard=True)

def pricing_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Мини-тату (4к)", callback_data="price_mini")],
        [InlineKeyboardButton(text="Сеанс (20к)", callback_data="price_session")]
    ])

def no_photo_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Нет эскиза", callback_data="no_sketch")]
    ])

def admin_instruction_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Активные записи", callback_data="run_data")],
        [InlineKeyboardButton(text="История", callback_data="run_history")]
    ])

def admin_action_kb(uid, d, t):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ОК", callback_data=f"adm_confirm|{uid}|{d}|{t}"),
         InlineKeyboardButton(text="❌ НЕТ", callback_data=f"adm_reject|{uid}|{d}|{t}")],
        [InlineKeyboardButton(text="✉ Профиль", url=f"tg://user?id={uid}")]
    ])

def admin_manage_kb(uid, d, t):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ В архив", callback_data=f"close_app|{uid}|{d}|{t}"),
         InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_app|{uid}|{d}|{t}")]
    ])

def get_available_time_slots(booked, is_today=False):
    # Добавлены все промежутки каждый час
    all_s = [
        "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", 
        "20:00", "21:00", "22:00", "23:00", "00:00"
    ]
    
    if any(b[1] == "Сеанс" for b in booked):
        return None
    
    now = datetime.now().strftime("%H:%M")
    available = [
        s for s in all_s 
        if not (is_today and s <= now) and not any(b[0] == s for b in booked)
    ]
    
    if not available:
        return None
    
    btns = []
    for i in range(0, len(available), 2):
        row = [InlineKeyboardButton(text=available[i], callback_data=f"time_{available[i]}")]
        if i + 1 < len(available):
            row.append(InlineKeyboardButton(text=available[i+1], callback_data=f"time_{available[i+1]}"))
        btns.append(row)
        
    return InlineKeyboardMarkup(inline_keyboard=btns)
