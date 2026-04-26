from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

def main_menu():
    kb = [
        [KeyboardButton(text="записаться")],
        [KeyboardButton(text="связь с ОСЧ")],
        [KeyboardButton(text="анон сообщение мастеру")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def pricing_menu():
    buttons = [
        [InlineKeyboardButton(text="Мини-тату (4к)", callback_data="price_mini")],
        [InlineKeyboardButton(text="Сеанс (20к)", callback_data="price_session")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_instruction_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Вызвать команду DATA", callback_data="run_data")],
        [InlineKeyboardButton(text="Вызвать команду HISTORY", callback_data="run_history")]
    ])

def admin_action_kb(user_id, date, time, service):
    data = f"{user_id}|{date}|{time}|{service}"
    buttons = [
        [InlineKeyboardButton(text="Подтвердить", callback_data=f"adm_confirm|{data}")],
        [InlineKeyboardButton(text="Отклонить", callback_data=f"adm_reject|{data}")],
        [InlineKeyboardButton(text="Связаться", url=f"tg://user?id={user_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_manage_kb(user_id, date, time):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Закрыть запись (выполнено)", callback_data=f"close_app|{user_id}|{date}|{time}")],
        [InlineKeyboardButton(text="Отменить запись (удалить)", callback_data=f"delete_app|{user_id}|{date}|{time}")],
        [InlineKeyboardButton(text="Связаться", url=f"tg://user?id={user_id}")]
    ])

def history_kb(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Связаться", url=f"tg://user?id={user_id}")]
    ])

def get_available_time_slots(booked_slots, is_today=False):
    all_slots = ["14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00", "23:00", "00:00"]
    if any(s[1] == "Сеанс" for s in booked_slots): return None
    now = datetime.now()
    available = []
    for slot in all_slots:
        slot_dt = datetime.strptime(slot, "%H:%M")
        if is_today:
            current_time_dt = datetime.strptime(now.strftime("%H:%M"), "%H:%M")
            if slot_dt <= current_time_dt: continue
        is_blocked = False
        for b_time, b_type in booked_slots:
            if b_time == slot: is_blocked = True; break
        if not is_blocked: available.append(slot)
    if not available: return None
    buttons = []
    for i in range(0, len(available), 2):
        row = [InlineKeyboardButton(text=available[i], callback_data=f"time_{available[i]}")]
        if i + 1 < len(available):
            row.append(InlineKeyboardButton(text=available[i+1], callback_data=f"time_{available[i+1]}"))
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)
