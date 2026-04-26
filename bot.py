import asyncio
import os
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

async def send_admin_data(user_id):
    apps = db.get_all_appointments()
    if not apps:
        await bot.send_message(user_id, "Журнал пуст (активных записей нет)")
        return
    for a in apps:
        client_label = f"@{a[1]}" if a[1] else "Профиль клиента"
        caption = (f"Дата: {a[2]} | Время: {a[3]}\nУслуга: {a[4]}\nКлиент: [{client_label}](tg://user?id={a[0]})")
        await bot.send_photo(user_id, photo=a[5], caption=caption, parse_mode="Markdown", 
                             reply_markup=kb.admin_manage_kb(a[0], a[2], a[3]))

async def send_admin_history(user_id):
    apps = db.get_history_appointments()
    if not apps:
        await bot.send_message(user_id, "История пуста")
        return
    await bot.send_message(user_id, "АРХИВ ЗАВЕРШЕННЫХ СЕАНСОВ:")
    for a in apps:
        client_label = f"@{a[1]}" if a[1] else "Профиль клиента"
        caption = (f"ЗАКРЫТО\nДата: {a[2]} | Время: {a[3]}\nУслуга: {a[4]}\nКлиент: [{client_label}](tg://user?id={a[0]})")
        await bot.send_photo(user_id, photo=a[5], caption=caption, parse_mode="Markdown", 
                             reply_markup=kb.history_kb(a[0]))

@dp.message(Command("data"))
async def admin_data_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await send_admin_data(message.from_user.id)

@dp.message(Command("history"))
async def admin_history_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await send_admin_history(message.from_user.id)

@dp.message(Command("start"))
async def start(message: types.Message):
    db.add_user(message.from_user.id, message.from_user.username)
    if message.from_user.id == ADMIN_ID:
        instruction = (
            "инструкция для ебланов:\n\n"
            "Команда /data — текущие записи.\n"
            "Команда /history — архив.\n"
            "Кнопки ниже для быстрого доступа:"
        )
        await message.answer(instruction, reply_markup=kb.admin_instruction_kb(), parse_mode="Markdown")
    else:
        await message.answer("здарова, будем на татуху записываться?", reply_markup=kb.main_menu(), parse_mode="Markdown")

@dp.callback_query(F.data == "run_data")
async def callback_run_data(callback: types.CallbackQuery):
    if callback.from_user.id == ADMIN_ID:
        await send_admin_data(callback.from_user.id)
        await callback.answer()

@dp.callback_query(F.data == "run_history")
async def callback_run_history(callback: types.CallbackQuery):
    if callback.from_user.id == ADMIN_ID:
        await send_admin_history(callback.from_user.id)
        await callback.answer()

@dp.message(F.text == "связь с ОСЧ")
async def show_master(message: types.Message):
    await message.answer(f"Мастер: {MASTER_LINK}")

@dp.message(F.text == "записаться")
async def show_prices(message: types.Message):
    # ПРОВЕРКА НА АКТИВНУЮ ЗАПИСЬ
    if db.has_active_appointment(message.from_user.id):
        await message.answer("У тебя уже есть активная запись. Сначала разберись с ней (дождись сеанса или отмены), потом лезь за новой.")
        return
    await message.answer("ВЫБЕРИ ТИП РАБОТЫ:", reply_markup=kb.pricing_menu(), parse_mode="Markdown")

@dp.message(F.text == "анон сообщение мастеру")
async def anon_start(message: types.Message, state: FSMContext):
    await message.answer("можешь написать че угодно, и я отправлю это ОСЧ анонимно, ну ка скинь ему какую-нибудь хуйню чтобы не втыкал ))) \nследующим сообщением кидай фотку или текст (одним сообщением) и я скину это ОСЧ")
    await state.set_state(AnonMessage.waiting_for_content)

@dp.message(AnonMessage.waiting_for_content)
async def anon_process(message: types.Message, state: FSMContext):
    await bot.send_message(ADMIN_ID, "ПРИШЛО АНОН СООБЩЕНИЕ:")
    if message.photo:
        await bot.send_photo(ADMIN_ID, photo=message.photo[-1].file_id, caption=message.caption if message.caption else "")
    elif message.text:
        await bot.send_message(ADMIN_ID, message.text)
    await message.answer("Отправлено анонимно. Мастер оценит.")
    await state.clear()

@dp.callback_query(F.data.startswith("price_"))
async def price_booking(callback: types.CallbackQuery, state: FSMContext):
    service = "Мини-тату" if callback.data == "price_mini" else "Сеанс"
    info_text = (
        "мини тату не должна превышать размеры (\"добавим потом\") \nпожалуйста выберите время" 
        if service == "Мини-тату" else 
        "сеанс длится не более 12 часов, в это время можете делать с мастером что хотите, хоть бейте татуху хоть бухайте хоть в жопу с ним ебитесь, пожалуйста выберите время"
    )
    await state.update_data(service_type=service)
    calendar = SimpleCalendar(show_alerts=True, locale='ru_RU')
    today = datetime.now()
    calendar.set_dates_range(today, datetime(today.year + 1, 12, 31)) 
    await callback.message.edit_text(f"Услуга: {service}\n\n{info_text}\n\nВЫБЕРИ ДАТУ:", 
                                     reply_markup=await calendar.start_calendar())
    await state.set_state(Booking.choosing_date)

@dp.callback_query(SimpleCalendarCallback.filter(), Booking.choosing_date)
async def process_date(callback: types.CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    calendar = SimpleCalendar(show_alerts=True, locale='ru_RU')
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        if date.date() < datetime.now().date():
            await callback.answer("Нельзя выбрать прошедшую дату", show_alert=True)
            return
        formatted_date = date.strftime("%d.%m.%Y")
        booked_slots = db.get_appointments_by_date(formatted_date)
        markup = kb.get_available_time_slots(booked_slots, is_today=(date.date() == datetime.now().date()))
        if markup is None:
            await callback.answer("На эту дату мест нет", show_alert=True)
            return
        await state.update_data(booked_date=formatted_date)
        await callback.message.edit_text(f"Свободное время на {formatted_date}:", reply_markup=markup)
        await state.set_state(Booking.choosing_time)

@dp.callback_query(F.data.startswith("time_"), Booking.choosing_time)
async def process_time(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(booked_time=callback.data.split("_")[1])
    await callback.message.edit_text("скидывай фотку эскиза ( просьба не кидать всякую хуйню и мемы )")
    await state.set_state(Booking.waiting_for_photo)

@dp.message(Booking.waiting_for_photo)
async def process_photo_or_trash(message: types.Message, state: FSMContext):
    if message.photo:
        photo_id = message.photo[-1].file_id
        data = await state.get_data()
        await message.answer("Красавчик, ОСЧ скоро свяжется по поводу твоей заявки")
        client_label = message.from_user.username if message.from_user.username else message.from_user.full_name
        caption = (f"НОВАЯ ЗАЯВКА\n\nКлиент: [{client_label}](tg://user?id={message.from_user.id})\nУслуга: {data['service_type']}\nДата: {data['booked_date']}\nВремя: {data['booked_time']}")
        await bot.send_photo(ADMIN_ID, photo=photo_id, caption=caption, parse_mode="Markdown",
                             reply_markup=kb.admin_action_kb(message.from_user.id, data['booked_date'], data['booked_time'], data['service_type']))
        await state.clear()
    else:
        type_names = {"text": "текст", "sticker": "стикер", "video": "видео", "voice": "голосовуху", "document": "документ", "video_note": "кружочек"}
        name = type_names.get(message.content_type, "непонятную хуйню")
        await message.answer(f"фотку бля а не {name}")

@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(callback: types.CallbackQuery):
    action, user_id, date, time, service = callback.data.split("|")
    user_id = int(user_id)
    if action == "adm_confirm":
        db.add_appointment(user_id, date, time, service, callback.message.photo[-1].file_id)
        await bot.send_message(user_id, f"ЗАПИСЬ ПОДТВЕРЖДЕНА\n\nДата: {date}\nВремя: {time}")
        await callback.message.edit_caption(caption=callback.message.caption + "\n\nСТАТУС: ПОДТВЕРЖДЕНО", parse_mode="Markdown")
    elif action == "adm_reject":
        await bot.send_message(user_id, "ЗАЯВКА ОТКЛОНЕНА\n\nПопробуйте выбрать другое время или дату.")
        await callback.message.edit_caption(caption=callback.message.caption + "\n\nСТАТУС: ОТКЛОНЕНО", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("close_app|"))
async def process_close_app(callback: types.CallbackQuery):
    _, user_id, date, time = callback.data.split("|")
    db.close_appointment(int(user_id), date, time)
    await callback.message.delete()
    await bot.send_message(ADMIN_ID, f"Запись {date} в {time} закрыта и перенесена в историю.")

@dp.callback_query(F.data.startswith("delete_app|"))
async def process_delete_app(callback: types.CallbackQuery):
    _, user_id, date, time = callback.data.split("|")
    db.delete_appointment(int(user_id), date, time)
    await callback.message.edit_caption(caption=callback.message.caption + "\n\nСТАТУС: ЗАПИСЬ УДАЛЕНА", parse_mode="Markdown")
    await bot.send_message(int(user_id), f"Ваша запись на {date} в {time} была отменена мастером.")

async def main():
    db.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
