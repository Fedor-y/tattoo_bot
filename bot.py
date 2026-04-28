import asyncio
import os
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
from dotenv import load_dotenv

import database as db
import keyboards as kb

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MASTER_LINK = "@hoboto"

class Booking(StatesGroup):
    choosing_date = State()
    choosing_time = State()
    waiting_for_photo = State()

class AnonMessage(StatesGroup):
    waiting_for_content = State()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ АДМИНА ---
async def send_admin_data(user_id):
    apps = db.get_all_appointments()
    if not apps:
        await bot.send_message(user_id, "Журнал активных записей пуст.")
        return
    for a in apps:
        client_label = f"@{a[1]}" if a[1] else "Профиль"
        caption = f"Дата: {a[2]} | Время: {a[3]}\nУслуга: {a[4]}\nКлиент: [{client_label}](tg://user?id={a[0]})"
        if a[5] and a[5] != "None":
            await bot.send_photo(user_id, photo=a[5], caption=caption, parse_mode="Markdown", 
                                 reply_markup=kb.admin_manage_kb(a[0], a[2], a[3]))
        else:
            await bot.send_message(user_id, f"📝 **БЕЗ ЭСКИЗА**\n{caption}", parse_mode="Markdown",
                                   reply_markup=kb.admin_manage_kb(a[0], a[2], a[3]))

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    db.add_user(message.from_user.id, message.from_user.username)
    if message.from_user.id == ADMIN_ID:
        await message.answer("Админ-панель:", reply_markup=kb.admin_instruction_kb())
    else:
        await message.answer("Здарова! Записываемся на тату?", reply_markup=kb.main_menu())

@dp.message(F.text == "записаться")
async def show_prices(message: types.Message):
    if db.has_active_appointment(message.from_user.id):
        await message.answer("У тебя уже есть активная запись.")
        return
    await message.answer("Выбери услугу:", reply_markup=kb.pricing_menu())

@dp.callback_query(F.data.startswith("price_"))
async def price_booking(callback: types.CallbackQuery, state: FSMContext):
    service = "Мини-тату" if callback.data == "price_mini" else "Сеанс"
    await state.update_data(service_type=service)
    calendar = SimpleCalendar(show_alerts=True)
    today = datetime.now()
    markup = await calendar.start_calendar()
    
    # Логика календаря: помечаем прошедшие дни месяца
    current_month_ru = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"][today.month - 1]
    for row in markup.inline_keyboard:
        for btn in row:
            digits = re.findall(r'\d+', btn.text)
            if digits:
                day_val = int(digits[0])
                if day_val < today.day and current_month_ru in str(markup).lower():
                    btn.text = "✖"
    
    await callback.message.edit_text(f"Услуга: {service}\nВыбери дату:", reply_markup=markup)
    await state.set_state(Booking.choosing_date)

@dp.callback_query(SimpleCalendarCallback.filter(), Booking.choosing_date)
async def process_date(callback: types.CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    # Проверка на "крестик"
    for row in callback.message.reply_markup.inline_keyboard:
        for btn in row:
            if btn.callback_data == callback.data and btn.text == "✖":
                await callback.answer("Эта дата уже прошла!", show_alert=True)
                return

    calendar = SimpleCalendar(show_alerts=True)
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        if date.date() < datetime.now().date():
            await callback.answer("Нельзя выбрать прошедшую дату", show_alert=True)
            return
        
        formatted_date = date.strftime("%d.%m.%Y")
        booked_slots = db.get_appointments_by_date(formatted_date)
        markup = kb.get_available_time_slots(booked_slots, is_today=(date.date() == datetime.now().date()))
        
        if not markup:
            await callback.answer("На этот день мест нет", show_alert=True)
            return
            
        await state.update_data(booked_date=formatted_date)
        await callback.message.edit_text(f"Выбрана дата: {formatted_date}\nВыбери время:", reply_markup=markup)
        await state.set_state(Booking.choosing_time)

@dp.callback_query(F.data.startswith("time_"), Booking.choosing_time)
async def process_time(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(booked_time=callback.data.split("_")[1])
    await callback.message.edit_text("Пришли фото эскиза или нажми кнопку, если его нет:", reply_markup=kb.no_photo_kb())
    await state.set_state(Booking.waiting_for_photo)

@dp.callback_query(F.data == "no_sketch", Booking.waiting_for_photo)
async def process_no_sketch(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = callback.from_user.username or callback.from_user.full_name
    db.add_appointment(callback.from_user.id, data['booked_date'], data['booked_time'], data['service_type'], "None")
    
    await bot.send_message(ADMIN_ID, f"НОВАЯ ЗАЯВКА (БЕЗ ЭСКИЗА)\n\nКлиент: [{client}](tg://user?id={callback.from_user.id})\n"
                                     f"Услуга: {data['service_type']}\nДата: {data['booked_date']}\nВремя: {data['booked_time']}", 
                           parse_mode="Markdown", reply_markup=kb.admin_action_kb(callback.from_user.id, data['booked_date'], data['booked_time']))
    await callback.message.edit_text("Заявка отправлена!")
    await state.clear()

@dp.message(Booking.waiting_for_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id
    client = message.from_user.username or message.from_user.full_name
    db.add_appointment(message.from_user.id, data['booked_date'], data['booked_time'], data['service_type'], photo_id)
    
    await bot.send_photo(ADMIN_ID, photo=photo_id, caption=f"НОВАЯ ЗАЯВКА\n\nКлиент: [{client}](tg://user?id={message.from_user.id})\n"
                                                          f"Услуга: {data['service_type']}\nДата: {data['booked_date']}\nВремя: {data['booked_time']}",
                         parse_mode="Markdown", reply_markup=kb.admin_action_kb(message.from_user.id, data['booked_date'], data['booked_time']))
    await message.answer("Заявка у мастера! Ожидай подтверждения.")
    await state.clear()

@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(callback: types.CallbackQuery):
    action, uid, d, t = callback.data.split("|")
    if action == "adm_confirm":
        await bot.send_message(int(uid), f"Запись на {d} в {t} подтверждена! ✅")
        res = "✅ ПОДТВЕРЖДЕНО"
    else:
        db.delete_appointment(int(uid), d, t)
        await bot.send_message(int(uid), "Мастер отклонил заявку.")
        res = "❌ ОТКЛОНЕНО"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=callback.message.caption + f"\n\n{res}")
    else:
        await callback.message.edit_text(text=callback.message.text + f"\n\n{res}")

async def main():
    db.init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
