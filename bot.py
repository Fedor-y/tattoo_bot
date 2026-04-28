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

async def send_admin_history(user_id):
    apps = db.get_history_appointments()
    if not apps:
        await bot.send_message(user_id, "История (архив) пуста.")
        return
    for a in apps:
        client_label = f"@{a[1]}" if a[1] else "Профиль"
        caption = f"АРХИВ\nДата: {a[2]} | Время: {a[3]}\nУслуга: {a[4]}\nКлиент: [{client_label}](tg://user?id={a[0]})"
        if a[5] and a[5] != "None":
            await bot.send_photo(user_id, photo=a[5], caption=caption, parse_mode="Markdown", 
                                 reply_markup=kb.history_kb(a[0]))
        else:
            await bot.send_message(user_id, f"📦 **АРХИВ (БЕЗ ЭСКИЗА)**\n{caption}", parse_mode="Markdown",
                                   reply_markup=kb.history_kb(a[0]))

# --- ОБРАБОТЧИКИ КОМАНД ---
@dp.message(Command("start"))
async def start(message: types.Message):
    db.add_user(message.from_user.id, message.from_user.username)
    if message.from_user.id == ADMIN_ID:
        await message.answer("Админ-панель:", reply_markup=kb.admin_instruction_kb())
    else:
        await message.answer("Здарова! Записываемся на тату?", reply_markup=kb.main_menu())

@dp.message(Command("data"))
async def admin_data_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID: await send_admin_data(message.from_user.id)

@dp.message(Command("history"))
async def admin_history_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID: await send_admin_history(message.from_user.id)

@dp.callback_query(F.data == "run_data")
async def run_admin_data(callback: types.CallbackQuery):
    if callback.from_user.id == ADMIN_ID:
        await send_admin_data(callback.from_user.id)
        await callback.answer()

@dp.callback_query(F.data == "run_history")
async def run_admin_history(callback: types.CallbackQuery):
    if callback.from_user.id == ADMIN_ID:
        await send_admin_history(callback.from_user.id)
        await callback.answer()

# --- ПРОЦЕСС ЗАПИСИ ---
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
    current_month_ru = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"][today.month - 1]
    for row in markup.inline_keyboard:
        for btn in row:
            digits = re.findall(r'\d+', btn.text)
            if digits:
                day_val = int(digits[0])
                if day_val < today.day and current_month_ru in str(markup).lower(): btn.text = "✖"
                else: btn.text = str(day_val)
            elif "Today" in btn.text: btn.text = "Сегодня"
            elif "Cancel" in btn.text: btn.text = "Отмена"
    await callback.message.edit_text(f"Услуга: {service}\nВыбери дату:", reply_markup=markup)
    await state.set_state(Booking.choosing_date)

@dp.callback_query(SimpleCalendarCallback.filter(), Booking.choosing_date)
async def process_date(callback: types.CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    clicked_text = ""
    for row in callback.message.reply_markup.inline_keyboard:
        for btn in row:
            if btn.callback_data == callback.data:
                clicked_text = btn.text
                break
    if clicked_text == "✖":
        await callback.answer("Дата занята или прошла!", show_alert=True)
        return
    calendar = SimpleCalendar(show_alerts=True)
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        if date.date() < datetime.now().date():
            await callback.answer("Дата прошла", show_alert=True)
            return
        formatted_date = date.strftime("%d.%m.%Y")
        booked_slots = db.get_appointments_by_date(formatted_date)
        markup = kb.get_available_time_slots(booked_slots, is_today=(date.date() == datetime.now().date()))
        if not markup:
            await callback.answer("Мест нет", show_alert=True)
            return
        await state.update_data(booked_date=formatted_date)
        await callback.message.edit_text(f"Время на {formatted_date}:", reply_markup=markup)
        await state.set_state(Booking.choosing_time)

@dp.callback_query(F.data.startswith("time_"), Booking.choosing_time)
async def process_time(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(booked_time=callback.data.split("_")[1])
    await callback.message.edit_text("Скинь фото эскиза или нажми кнопку, если его нет:", reply_markup=kb.no_photo_kb())
    await state.set_state(Booking.waiting_for_photo)

@dp.callback_query(F.data == "no_sketch", Booking.waiting_for_photo)
async def process_no_sketch(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = callback.from_user.username or callback.from_user.full_name
    caption = (f"НОВАЯ ЗАЯВКА (БЕЗ ЭСКИЗА)\n\nКлиент: [{client}](tg://user?id={callback.from_user.id})\n"
               f"Услуга: {data['service_type']}\nДата: {data['booked_date']}\nВремя: {data['booked_time']}")
    
    # ПЕРЕДАЕМ "None" В КНОПКУ АДМИНА
    await bot.send_message(ADMIN_ID, text=caption, parse_mode="Markdown",
                           reply_markup=kb.admin_action_kb(callback.from_user.id, data['booked_date'], data['booked_time'], data['service_type'], "None"))
    await callback.message.edit_text("Заявка отправлена без эскиза!")
    await state.clear()

@dp.message(Booking.waiting_for_photo)
async def process_photo(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("Жду фото эскиза или нажми кнопку!")
        return
    
    data = await state.get_data()
    photo_id = message.photo[-1].file_id # Берем ID фото
    client = message.from_user.username or message.from_user.full_name
    caption = (f"НОВАЯ ЗАЯВКА\n\nКлиент: [{client}](tg://user?id={message.from_user.id})\n"
               f"Услуга: {data['service_type']}\nДата: {data['booked_date']}\nВремя: {data['booked_time']}")
    
    # ПЕРЕДАЕМ photo_id В КНОПКУ АДМИНА
    await bot.send_photo(ADMIN_ID, photo=photo_id, caption=caption, parse_mode="Markdown",
                         reply_markup=kb.admin_action_kb(message.from_user.id, data['booked_date'], data['booked_time'], data['service_type'], photo_id))
    
    await message.answer("Заявка у мастера! Ожидай подтверждения.")
    await state.clear()

# --- АДМИН-ДЕЙСТВИЯ ---
@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(callback: types.CallbackQuery):
    parts = callback.data.split("|")
    # action, uid, date, time, service, photo_id
    action, uid, d, t, s, p_id = parts[0], int(parts[1]), parts[2], parts[3], parts[4], parts[5]
    
    if action == "adm_confirm":
        db.add_appointment(uid, d, t, s, p_id)
        await bot.send_message(uid, f"Запись на {d} в {t} подтверждена! ✅")
        res_text = "\n\n✅ ПОДТВЕРЖДЕНО"
    else:
        await bot.send_message(uid, "Мастер отклонил заявку.")
        res_text = "\n\n❌ ОТКЛОНЕНО"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=callback.message.caption + res_text)
    else:
        await callback.message.edit_text(text=callback.message.text + res_text)

@dp.callback_query(F.data.startswith("close_app|"))
async def close_app(callback: types.CallbackQuery):
    _, uid, d, t = callback.data.split("|")
    db.close_appointment(int(uid), d, t)
    await callback.message.delete()

@dp.callback_query(F.data.startswith("delete_app|"))
async def delete_app(callback: types.CallbackQuery):
    _, uid, d, t = callback.data.split("|")
    db.delete_appointment(int(uid), d, t)
    msg = "🗑️ УДАЛЕНО"
    if callback.message.photo: 
        await callback.message.edit_caption(caption=callback.message.caption + f"\n\n{msg}")
    else: 
        await callback.message.edit_text(text=callback.message.text + f"\n\n{msg}")
    await bot.send_message(int(uid), f"Запись на {d} в {t} отменена.")

@dp.message(F.text == "связь с ОСЧ")
async def contact(message: types.Message):
    await message.answer(f"Мастер: {MASTER_LINK}")

@dp.message(F.text == "анон сообщение мастеру")
async def anon(message: types.Message, state: FSMContext):
    await message.answer("Напиши сообщение анонимно:")
    await state.set_state(AnonMessage.waiting_for_content)

@dp.message(AnonMessage.waiting_for_content)
async def anon_done(message: types.Message, state: FSMContext):
    await bot.send_message(ADMIN_ID, "Анонимное сообщение:")
    if message.text: await bot.send_message(ADMIN_ID, message.text)
    if message.photo: await bot.send_photo(ADMIN_ID, message.photo[-1].file_id)
    await message.answer("Передал!")
    await state.clear()

async def main():
    db.init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
