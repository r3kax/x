import os
import json
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor

# ================== Настройки ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
FILES_DIR = "files"  # папка с файлами/аккаунтами
DATA_FILE = "data.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ================== Инициализация базы ==================
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"users": {}, "promocodes": {}}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

os.makedirs(FILES_DIR, exist_ok=True)

# ================== Кнопки ==================
def main_menu():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("📊 Профиль", callback_data="profile"),
        InlineKeyboardButton("🛒 Товары", callback_data="products")
    )
    kb.add(InlineKeyboardButton("🎁 Промокод", callback_data="promo"))
    return kb

# ================== /start ==================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    data = load_data()
    if user_id not in data["users"]:
        data["users"][user_id] = {"balance": 0, "purchases": 0}
        save_data(data)
    await message.answer("Добро пожаловать в магазин!\nВыберите действие:", reply_markup=main_menu())

# ================== Кнопки ==================
@dp.callback_query_handler(lambda c: True)
async def callbacks(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    data = load_data()

    if call.data == "profile":
        u = data["users"][user_id]
        await call.message.answer(f"Ваш профиль:\nБаланс: {u['balance']}\nВсего покупок: {u['purchases']}")
    
    elif call.data == "products":
        files = os.listdir(FILES_DIR)
        if not files:
            await call.message.answer("Пока нет товаров.")
            return
        text = "Список товаров:\n\n"
        for i, f in enumerate(files, 1):
            text += f"{i}. {f}\n"
        text += "\nЧтобы купить, напишите /buy <номер товара> <кол-во (1-30)>"
        await call.message.answer(text)
    
    elif call.data == "promo":
        await call.message.answer("Введите промокод:")

# ================== Покупка ==================
@dp.message_handler(commands=["buy"])
async def buy(message: types.Message):
    data = load_data()
    user_id = str(message.from_user.id)

    try:
        _, item_number, amount = message.text.split()
        item_number = int(item_number) - 1
        amount = int(amount)
        assert 1 <= amount <= 30
    except:
        await message.answer("Использование: /buy <номер товара> <кол-во 1-30>")
        return

    files = os.listdir(FILES_DIR)
    if item_number < 0 or item_number >= len(files):
        await message.answer("Такого товара нет.")
        return

    chosen_file = files[item_number]

    # выдача файлов
    for _ in range(amount):
        path = os.path.join(FILES_DIR, chosen_file)
        if os.path.isfile(path):
            await message.answer_document(open(path, "rb"))
        else:
            with open(path, "r", encoding="utf-8") as f:
                await message.answer(f.read())

    data["users"][user_id]["purchases"] += amount
    save_data(data)

# ================== Промокод ==================
@dp.message_handler(lambda m: True)
async def promo_handler(message: types.Message):
    data = load_data()
    user_id = str(message.from_user.id)
    code = message.text.strip()

    if code in data["promocodes"]:
        data["users"][user_id]["balance"] += data["promocodes"][code]
        await message.answer(f"Промокод принят! Баланс +{data['promocodes'][code]}")
        del data["promocodes"][code]
        save_data(data)
    else:
        return

# ================== Админка ==================
@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID, commands=["addpromo"])
async def add_promo(message: types.Message):
    try:
        _, code, amount = message.text.split()
        data = load_data()
        data["promocodes"][code] = int(amount)
        save_data(data)
        await message.answer(f"Промокод {code} на {amount} добавлен.")
    except:
        await message.answer("Использование: /addpromo PROMO 50")

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID, commands=["addfile"])
async def add_file(message: types.Message):
    # админ может добавить файл вручную через папку, так проще
    await message.answer("Файл добавляется через папку 'files'. Просто загрузи туда файл.")

# ================== Старт ==================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)