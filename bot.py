import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram. filters import CommandStart, Command
from aiogram. types import Message, FSInputFile
from aiogram. fsm. context import FSMContext
from aiogram. fsm.state import State, StatesGroup
from aiogram. fsm. storage. memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from config import TOKEN
import sqlite3
import aiohttp
import logging
import requests
import random

bot = Bot(token=TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

button_registr = KeyboardButton(text="Регистрация в телеграм боте") #Создаём кнопку регистрации.
button_exchange_rates = KeyboardButton(text="Курс валют") #Создаём кнопку для выдачи курса валют.
button_tips = KeyboardButton(text="Советы по экономии") #Создаём кнопку для выдачи курса валют.
button_finances = KeyboardButton(text="Личные финансы") #Создаём кнопку для учёта расходов.

keyboard = ReplyKeyboardMarkup(keyboard=[
    [button_registr, button_exchange_rates],
    [button_tips, button_finances]
    ], resize_keyboard=True)  #Для работы кнопок нужно создавать клавиатуру. Клавиатура будет
                            # обычная, которая находится снизу. Создаём переменную с помощью
                            # класса ReplyKeyboardMarkup. В круглых скобках указываем список,
                            # внутри которого будут находиться другие списки. Таким образом
                            # настраиваем размещение кнопок.
                            # Кнопки выходят крупными, поэтому настроим изменение размера клавиатуры.

conn = sqlite3.connect('user.db') #Чтобы сохранять данные о пользователях, нам нужно создать
                            # базу данных. Сделаем мы это м помощью SQLite в этом же файле.
                            # Создаём подключение, курсор.
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,         -- ID пользователя
    telegram_id INTEGER UNIQUE,     -- уникальное поле
    name TEXT,                      --  имя пользователя
    category1 TEXT,                 -- будет название категории
    category2 TEXT,
    category3 TEXT,
    expenses1 REAL,
    expenses2 REAL,
    expenses3 REAL
    )
''')   #создаём таблицу. Указываем поля таблицы. Для ID пользователя указываем UNIQUE, потому
       # что идентификатор пользователя не может быть неуникальным. Создаём поля для категорий
       # (в TEXT будут названия категорий) и для расходов по этим категориям (REAL — это дробный тип данных).

conn.commit() #Прописываем сохранение после выполнения этого действия.

class FinancesForm(StatesGroup): #создаем группу со всеми категориями расходов, которые у нас будут
    category1 = State() #категория
    expenses1 = State() #расходы по данной категории
    category2 = State()
    expenses2 = State()
    category3 = State()
    expenses3 = State() #Чтобы запрашивать информацию и ждать ответа, нужно использовать состояния.
        # Создаём класс, в котором будут прописаны эти состояния для каждой категории и каждого значения категории.


@dp.message(Command('start'))
async def send_start(message: Message):
   await message.answer("Привет! Я ваш личный финансовый помощник. Выберите одну из опций в меню:", reply_markup=keyboard)


@dp.message(F.text == "Регистрация в телеграм боте")
async def registration(message: Message):
   telegram_id = message.from_user.id
   name = message.from_user.full_name
   cursor.execute('''SELECT * FROM users WHERE telegram_id = ?''', (telegram_id,))
   user = cursor.fetchone()
   if user:
       await message.answer("Вы уже зарегистрированы!")
   else:
       cursor.execute('''INSERT INTO users (telegram_id, name) VALUES (?, ?)''', (telegram_id, name))
       conn.commit()
       await message.answer("Вы успешно зарегистрированы!")

@dp.message(F.text == "Курс валют")
async def exchange_rates(message: Message):
   url = "https://v6.exchangerate-api.com/v6/09edf8b2bb246e1f801cbfba/latest/USD"
   try:
       response = requests.get(url)
       data = response.json()
       if response.status_code != 200:
           await message.answer("Не удалось получить данные о курсе валют!")
           return
       usd_to_rub = data['conversion_rates']['RUB']
       eur_to_usd = data['conversion_rates']['EUR']

       euro_to_rub = eur_to_usd * usd_to_rub

       await message.answer(f"1 USD - {usd_to_rub:.2f}  RUB\n"
                            f"1 EUR - {euro_to_rub:.2f}  RUB")

   except:
       await message.answer("Произошла ошибка")


@dp.message(F.text == "Советы по экономии")    #Создаём асинхронную функцию для отправки текста.
async def send_tips(message: Message):
   tips = [
       "Совет 1: Ведите бюджет и следите за своими расходами.",   #Создаём список с советами.
       "Совет 2: Откладывайте часть доходов на сбережения.",
       "Совет 3: Покупайте товары по скидкам и распродажам."
   ]
   tip = random.choice(tips)                  #Настраиваем рандомную выдачу советов с помощью переменной.
                                              # Отправляем совет из переменной.
   await message.answer(tip)

@dp.message(F.text == "Личные финансы")         #Создаём асинхронную функцию для работы с личными финансами.
async def finances(message: Message, state: FSMContext):    #Начинаем работу с состояниями. Вводим второй атрибут функции.
   await state.set_state(FinancesForm.category1)            #Устанавливаем новое состояние. В круглых скобках указываем
                                                            # класс и категорию этого состояния.
   await message.reply("Введите первую категорию расходов:") #Отправляем сообщение пользователю.


@dp.message(FinancesForm.category1)             #Создаём декоратор, который сработает не по фразе, а по категории.
async def finances(message: Message, state: FSMContext):
   await state.update_data(category1 = message.text)        #Настраиваем обновление данных. Теперь в category1 будет
                                                            # сохраняться текст сообщения.
   await state.set_state(FinancesForm.expenses1)
   await message.reply("Введите расходы для категории 1:")  #Начинаем использовать новое состояние. Теперь нужно
                                                            # значение денег, которые уходят на эту категорию товаров.


@dp.message(FinancesForm.expenses1)             #Прописываем функцию, которая сработает после получения предыдущего значения.
async def finances(message: Message, state: FSMContext):
   await state.update_data(expenses1 = float(message.text)) #Используем float, чтобы преобразовывать тип данных.
   await state.set_state(FinancesForm.category2)            #Устанавливаем вторую категорию.
   await message.reply("Введите вторую категорию расходов:")#Создаём функцию для расходов по второй категории.

@dp.message(FinancesForm.category2)
async def finances(message: Message, state: FSMContext):
   await state.update_data(category2 = message.text)
   await state.set_state(FinancesForm.expenses2)
   await message.reply("Введите расходы для категории 2:")


@dp.message(FinancesForm.expenses2)
async def finances(message: Message, state: FSMContext):
   await state.update_data(expenses2 = float(message.text))
   await state.set_state(FinancesForm.category3)
   await message.reply("Введите третью категорию расходов:")

@dp.message(FinancesForm.category3)
async def finances(message: Message, state: FSMContext):
   await state.update_data(category3 = message.text)
   await state.set_state(FinancesForm.expenses3)
   await message.reply("Введите расходы для категории 3:")


@dp.message(FinancesForm.expenses3) #Создаём функцию, которая сработает после третьего ответа по расходам.
async def finances(message: Message, state: FSMContext):
   data = await state.get_data()    #Создаём переменную data, в которую сохраним всю информацию по состояниям.
   telegram_id = message.from_user.id   #Сохраняем telegram ID пользователя, чтобы сохранить информацию в
                                        # нужную строчку базы данных.
   cursor.execute('''UPDATE users SET category1 = ?, expenses1 = ?, category2 = ?, expenses2 = ?, category3 = ?, expenses3 = ? WHERE telegram_id = ?''',
                  (data['category1'], data['expenses1'], data['category2'], data['expenses2'], data['category3'], float(message.text), telegram_id))
                                        #Отравляем запрос. Обновляем информацию и устанавливаем значения для
                                        # категорий в базе данных.
   conn.commit()                        #Сохраняем изменения.
   await state.clear()                  #Очищаем состояния. Прописываем сообщение о сохранении категорий и расходов.

   await message.answer("Категории и расходы сохранены!")


async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())