import logging
import asyncio
import json
import pandas as pd
import os
import re
from aiogram import types
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from datetime import datetime, timedelta

# словник для тимчасових блокувань: user_id → час закінчення блокування
temp_bans: dict[int, datetime] = {}


# ❌ Цей імпорт ти повторив двічі — видали зайвий:
# from aiogram.dispatcher import FSMContext

# ✅ Middleware для автоматичного логування повідомлень
from aiogram.dispatcher.middlewares import BaseMiddleware

# === Глобальна змінна для зберігання повідомлень ===
chat_links = {}

class MessageLoggerMiddleware(BaseMiddleware):
    async def on_post_process_message(self, message, results, data):
        if message:
            user_id = message.from_user.id
            chat_links.setdefault(user_id, {}).setdefault("msgs", []).append(message.message_id)

    async def on_post_process_callback_query(self, callback, results, data):
        if callback and callback.message:
            user_id = callback.from_user.id
            chat_links.setdefault(user_id, {}).setdefault("msgs", []).append(callback.message.message_id)


API_TOKEN = "7079057857:AAEtlYk_l1eTczU8_a9LU4tVD1lVmpwdAOE"
ADMIN_IDS = {5138418509}
MIN_TOPUP = 10


bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# ✅ Підключення middleware
dp.middleware.setup(MessageLoggerMiddleware())

# ✅ Логування
logging.basicConfig(level=logging.INFO)


user_balances = {}
chat_logs = {}  # user_id: [msg_id, msg_id, ...]
banned_users = set()
user_ads = {"buy": [], "sell": []}
def banks(*names):
    return list(names)
merchant_deposits = {}


BALANCE_FILE = "balances.json"

# === Глобальні структури для логування повідомлень ===
chat_logs = {}  # {user_id: [msg_id, msg_id, ...]}
sent_chat_ids = set()  # для повідомлення адмінам про нових юзерів

# --- Завантаження балансу ---
def load_balances():
    global user_balances
    if os.path.exists(BALANCE_FILE):
        with open(BALANCE_FILE, "r") as f:
            user_balances = json.load(f)
            user_balances = {int(k): v for k, v in user_balances.items()}
    else:
        user_balances = {}

# --- Збереження балансу ---
def save_balances():
    with open(BALANCE_FILE, "w") as f:
        json.dump(user_balances, f, indent=2)

# Завантаження при запуску
load_balances()

def log_message(user_id, msg):
    if user_id not in chat_logs:
        chat_logs[user_id] = []
    chat_logs[user_id].append(msg.message_id)

def is_temp_banned(user_id: int) -> bool:
    exp = temp_bans.get(user_id)
    if not exp:
        return False
    if datetime.now() >= exp:
        # блокування закінчилося — прибираємо
        temp_bans.pop(user_id, None)
        return False
    return True


def ad(u, r, lim, b, cur="USDT (TRC20)", t="sell", terms="Без дополнительных условий"):
    return {
        "username": u,
        "verified": True,
        "rate": r,
        "limit": lim,
        "banks": b,
        "currency": cur,
        "type": t,
        "terms": terms
    }

user_ads["sell"] = [
    ad("@CryptoBoss",   42.91, "500 – 2000 грн", banks("Monobank", "PrivatBank", "PUMB", "A-Bank", "Sense Bank"), t="sell"),
    ad("@UkrTrader",    42.95, "500 – 2000 грн", banks("Monobank", "Sense Bank", "Ukrsibbank", "Concord Bank"), t="sell"),
    ad("@BestRate24",   42.92, "500 – 2000 грн", banks("PrivatBank", "PUMB", "OTP Bank", "Oschadbank", "Raiffeisen"), t="sell"),
    ad("@FastUSDT",     42.93, "500 – 2000 грн", banks("Monobank", "PUMB", "MTB Bank", "Globus Bank"), t="sell"),
    ad("@TrustExchanger",42.96, "500 – 2000 грн", banks("Raiffeisen", "Sense Bank", "PrivatBank", "Ukrsibbank", "Oschadbank"), t="sell"),
    ad("@VerifedPro",   42.90, "500 – 2000 грн", banks("Monobank", "PrivatBank", "A-Bank", "Credit Agricole"), t="sell"),
    ad("@TetherKing",   42.97, "2000 – 6000 грн", banks("Monobank", "PrivatBank", "PUMB", "Raiffeisen", "Sense Bank", "OTP Bank"), t="sell"),
    ad("@CashToCoin",   43.01, "2000 – 6000 грн", banks("PrivatBank", "PUMB", "Ukrsibbank", "Concord Bank", "Oschadbank"), t="sell"),
    ad("@EasyChange",   42.98, "2000 – 6000 грн", banks("Monobank", "PrivatBank", "PUMB", "MTB Bank"), t="sell"),
    ad("@USDTbanker",   43.05, "2000 – 6000 грн", banks("Raiffeisen", "PrivatBank", "Sense Bank", "Monobank", "Globus Bank", "Tascombank"), t="sell"),
    ad("@ExchangePlus", 43.02, "2000 – 6000 грн", banks("Monobank", "PrivatBank", "PUMB", "Oschadbank", "Ukrsibbank"), t="sell"),
    ad("@BitProfi",     42.94, "2000 – 6000 грн", banks("Monobank", "PrivatBank", "PUMB", "Oschadbank", "OTP Bank", "Credit Agricole"), t="sell"),
    ad("@FiatBridge",   43.00, "2000 – 6000 грн", banks("Monobank", "PrivatBank", "Sense Bank", "Ukrsibbank"), t="sell"),
    ad("@DigitalGate",  43.03, "2000 – 6000 грн", banks("PrivatBank", "PUMB", "Raiffeisen", "Sense Bank", "Oschadbank"), t="sell"),
    ad("@FastMoney",    43.21, "6000 – 40000 грн", banks("Monobank", "PrivatBank", "PUMB", "Raiffeisen", "Sense Bank", "Ukrsibbank", "Concord Bank"), t="sell"),
    ad("@TokenExpress", 43.38, "6000 – 40000 грн", banks("PrivatBank", "PUMB", "Oschadbank", "Ukrsibbank", "Concord Bank", "Globus Bank"), t="sell"),
    ad("@FixRate",      43.45, "6000 – 40000 грн", banks("Monobank", "PrivatBank", "PUMB", "A-Bank", "Sense Bank", "OTP Bank"), t="sell"),
    ad("@UkrUSDT",      43.32, "6000 – 40000 грн", banks("Monobank", "PrivatBank", "PUMB", "Raiffeisen", "Oschadbank"), t="sell"),
    ad("@MonoCrypto",   43.29, "6000 – 40000 грн", banks("PrivatBank", "PUMB", "Oschadbank", "Tascombank", "Credit Agricole", "MTB Bank"), t="sell"),
    ad("@VerifiedX",    43.50, "6000 – 40000 грн", banks("Monobank", "PrivatBank", "PUMB", "Raiffeisen", "Sense Bank", "Ukrsibbank", "Concord Bank", "Globus Bank"), t="sell"),
    ad("@RateMaster",   43.40, "6000 – 40000 грн", banks("PrivatBank", "PUMB", "Oschadbank", "Ukrsibbank", "OTP Bank", "Credit Agricole"), t="sell"),
]
# Проставляємо заставу для фейкових
fake_usernames = [ad["username"] for ad in user_ads["sell"] + user_ads["buy"]]
for name in fake_usernames:
    if name.startswith("@"):
        # Просто дамо їм 500/500 заставу
        merchant_deposits[name] = {
            "amount": 500,
            "target": 500,
            "verified": True
        }

user_ads["buy"] = [
    ad("@CryptoBoss",   43.1, "500 – 2000 грн", banks("Monobank", "PrivatBank", "PUMB", "A-Bank", "Sense Bank"), t="buy"),
    ad("@UkrTrader",    43.6, "500 – 2000 грн", banks("Monobank", "Sense Bank", "Ukrsibbank", "Concord Bank"), t="buy"),
    ad("@BestRate24",   41.78, "500 – 2000 грн", banks("PrivatBank", "PUMB", "OTP Bank", "Oschadbank", "Raiffeisen"), t="buy"),
    ad("@FastUSDT",     43.48, "500 – 2000 грн", banks("Monobank", "PUMB", "MTB Bank", "Globus Bank"), t="buy"),
    ad("@TrustExchanger",43.29, "500 – 2000 грн", banks("Raiffeisen", "Sense Bank", "PrivatBank", "Ukrsibbank", "Oschadbank"), t="buy"),
    ad("@VerifedPro",   43.76, "500 – 2000 грн", banks("Monobank", "PrivatBank", "A-Bank", "Credit Agricole"), t="buy"),
    ad("@TetherKing",   43.68, "500 – 2000 грн", banks("Monobank", "PrivatBank", "PUMB", "Raiffeisen"), t="buy"),
    ad("@CashToCoin",   43.92, "500 – 2000 грн", banks("PrivatBank", "PUMB", "Ukrsibbank", "Concord Bank"), t="buy"),
    ad("@EasyChange",   43.63, "500 – 2000 грн", banks("Monobank", "PrivatBank", "PUMB", "MTB Bank"), t="buy"),
    ad("@USDTbanker",   43.45, "2000 – 6000 грн", banks("Raiffeisen", "PrivatBank", "Sense Bank", "Monobank", "Globus Bank", "Tascombank"), t="buy"),
    ad("@ExchangePlus", 43.15, "2000 – 6000 грн", banks("Monobank", "PrivatBank", "PUMB", "Oschadbank", "Ukrsibbank"), t="buy"),
    ad("@BitProfi",     43.38, "2000 – 6000 грн", banks("Monobank", "PrivatBank", "PUMB", "Oschadbank", "OTP Bank", "Credit Agricole"), t="buy"),
    ad("@FiatBridge",   43.40, "2000 – 6000 грн", banks("Monobank", "PrivatBank", "Sense Bank", "Ukrsibbank"), t="buy"),
    ad("@DigitalGate",  41.89, "2000 – 6000 грн", banks("PrivatBank", "PUMB", "Raiffeisen", "Sense Bank", "Oschadbank"), t="buy"),
    ad("@FastMoney",    43.29, "2000 – 6000 грн", banks("Monobank", "PrivatBank", "PUMB", "Raiffeisen", "Sense Bank"), t="buy"),
    ad("@TokenExpress", 42.26, "2000 – 6000 грн", banks("PrivatBank", "PUMB", "Oschadbank", "Ukrsibbank", "Concord Bank", "Globus Bank"), t="buy"),
    ad("@FixRate",      42.33, "2000 – 6000 грн", banks("Monobank", "PrivatBank", "PUMB", "A-Bank", "Sense Bank", "OTP Bank"), t="buy"),
    ad("@UkrUSDT",      43.27, "2000 – 6000 грн", banks("Monobank", "PrivatBank", "PUMB", "Raiffeisen", "Oschadbank"), t="buy"),
    ad("@MonoCrypto",   43.61, "6000 – 40000 грн", banks("PrivatBank", "PUMB", "Oschadbank", "Tascombank", "Credit Agricole", "MTB Bank"), t="buy"),
    ad("@VerifiedX",    43.68, "6000 – 40000 грн", banks("Monobank", "PrivatBank", "PUMB", "Raiffeisen", "Sense Bank", "Ukrsibbank", "Concord Bank", "Globus Bank"), t="buy"),
    ad("@RateMaster",   42.70, "6000 – 40000 грн", banks("PrivatBank", "PUMB", "Oschadbank", "Ukrsibbank", "OTP Bank", "Credit Agricole"), t="buy"),
    ad("@FixSpread",    43.62, "6000 – 40000 грн", banks("Monobank", "PrivatBank", "PUMB", "Raiffeisen", "Sense Bank"), t="buy"),
    ad("@UAChanger",    42.66, "6000 – 40000 грн", banks("Monobank", "PrivatBank", "PUMB", "Ukrsibbank", "Concord Bank"), t="buy"),
    ad("@DeepRate",     43.69, "6000 – 40000 грн", banks("PrivatBank", "PUMB", "Oschadbank", "Ukrsibbank", "Concord Bank", "Globus Bank"), t="buy"),
    ad("@NightTrader",  43.64, "6000 – 40000 грн", banks("Monobank", "PrivatBank", "PUMB", "Raiffeisen", "Oschadbank"), t="buy"),
]


chat_links = {}
await_screenshot = set()
active_orders = {}


wallets = {
    "USDT (TRC20)": "TDM4K4kcNEi8YnmMFB7MS2ewUQHcxdxpNR",
    "USDT (TON)":
"UQAuDLXxftnBmsx_QObMjsFhEIbqzH_HnWYdgXS03h-8csHm",
    "BTC": "bc1q5h9vnytxjfy5xnagmhfyta8sqedprklxtdk7pn",
    "ETH (ERC20)": "0xCeD44c75151aFf58BA5C949c8f81e2A45bE5a32C",
    "BNB (BEP20)": "0xa95260531eb4ad8aD83011BcA46d1a0f703e354E",
    "TRX": "TDM4K4kcNEi8YnmMFB7MS2ewUQHcxdxpNR"
}

ADMIN_IDS = {5138418509}  # ← заміни на свій Telegram ID

def get_main_kb(user_id=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🟢 Покупка USDT"), KeyboardButton("🔴 Продажа USDT"))
    kb.add(KeyboardButton("📥 Пополнить баланс"), KeyboardButton("👛 Кошелёк"))
    kb.add(KeyboardButton("📋 Объявления"), KeyboardButton("➕ Добавить объявление"))
    kb.add(KeyboardButton("🔻 Вывести USDT"), KeyboardButton("🗂 Мои ордера"))

    if user_id in ADMIN_IDS:
        kb.add(KeyboardButton("🗨️ Чаты"))

    return kb




def get_range_kb(prefix):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("500–2000 ₴", callback_data=f"{prefix}:500-2000"),
        InlineKeyboardButton("2000–6000 ₴", callback_data=f"{prefix}:2000-6000"),
        InlineKeyboardButton("6000–40000 ₴", callback_data=f"{prefix}:6000-40000")
    )
    return kb

def parse_limit(limit_str):
    # Прибираємо валюту, пробіли, тире
    clean = limit_str.replace("₴", "").replace("грн", "").replace(" ", "").replace(",", "")
    # Уніфікуємо тире
    clean = clean.replace("–", "-")

    if "-" not in clean:
        raise ValueError("Неверный формат диапазона")

    a, b = clean.split("-")
    return int(a), int(b)



def fmt_ad(ad, idx):
    # Отримати ID продавця, якщо це User_<id>
    pledge_str = "—"
    if ad["username"].startswith("User_"):
        uid = int(ad["username"].replace("User_", ""))
        pledge_str = get_pledge_string(uid)
    else:
        # Фейкові — даємо кастомну заставу, наприклад 500/500
        pledge_str = "500/500$"

    return (
        f"<b>#{idx+1} | {ad['type'].upper()}</b>\n"
        f"✅ Верифицировано • <code>{ad['username']}</code>\n"
        f"Курс: <b>{ad['rate']}</b> ₴\n"
        f"Объём: <b>{ad['limit']}</b>\n"
        f"Банки: <i>{', '.join(ad['banks'])}</i>\n"
        f"Залог: <b>{pledge_str}</b>\n"
        f"Время оплаты: 15 мин\n"
        f"Условия: {ad.get('terms', '—')}"
    )
def get_admin_delete_kb(idx, ad_type):
    return InlineKeyboardMarkup().add(
        InlineKeyboardButton("🗑 Удалить (админом)", callback_data=f"admin_del:{ad_type}:{idx}")
    )

def ensure_balance(user_id):
    if user_id not in user_balances:
        user_balances[user_id] = {k: 0 for k in wallets}

def get_wallets_text():
    return "\n".join([f"<b>{k}</b>: <code>{v}</code>" for k, v in wallets.items()])

class AdForm(StatesGroup):
    type = State()
    amount = State()
    rate = State()
    banks = State()

class OrderForm(StatesGroup):
    amount_rub = State()

def is_banned(user_id):
    return user_id in banned_users

from functools import wraps

def ban_check(func):
    @wraps(func)
    async def wrapper(message_or_call, *args, **kwargs):
        user_id = message_or_call.from_user.id
        if is_banned(user_id):
            await message_or_call.answer("🚫 Вы были заблокированы и не можете пользоваться ботом.")
            return
        return await func(message_or_call, *args, **kwargs)
    return wrapper

def log_message(user_id, msg):
    if user_id not in chat_logs:
        chat_logs[user_id] = []
    chat_logs[user_id].append(msg.message_id)

@dp.message_handler(commands=["start"])
@ban_check
async def start(message: types.Message):
    ensure_balance(message.from_user.id)
    
    # 🟡 Відправка повідомлення
    msg = await message.answer(
        "👋 Добро пожаловать!",
        reply_markup=get_main_kb(message.from_user.id)
    )
    chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(msg.message_id)

    # ✅ КРОК 1: Зберігаємо message_id
    user_id = message.from_user.id
    chat_links.setdefault(user_id, {}).setdefault("msgs", []).append(msg.message_id)

@dp.message_handler(
    lambda m: m.from_user.id in ADMIN_IDS 
              and isinstance(m.text, str) 
              and re.match(r'^\d+\s+', m.text),
    content_types=types.ContentType.TEXT
)
async def admin_send_direct(message: types.Message):
    """
    Адмін пише: "<user_id> Привіт, як справи?"
    Бот відправить "Привіт, як справи?" користувачу з цим ID
    """
    user_id_str, text = message.text.strip().split(' ', 1)
    try:
        user_id = int(user_id_str)
    except ValueError:
        return await message.reply("❗ Першим має бути цілим числом user_id.")
    
    try:
        sent = await bot.send_message(user_id, text)
        # логування в chat_links, якщо потрібно
        chat_links.setdefault(user_id, {}).setdefault("msgs", []).append(sent.message_id)

        await message.reply("✅ Повідомлення надіслано!")
    except Exception as e:
        await message.reply(f"❌ Не вдалося відправити повідомлення: {e}")


@dp.message_handler(commands=["addusdt"])
async def add_usdt_handler(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Команда доступна только администраторам.")

    try:
        text = message.text.replace("\n", " ").strip()
        parts = text.split()

        if len(parts) != 3:
            reply_msg = await message.answer(
                "❗ Неверный формат команды.\n\n"
                "Пример:\n<code>/addusdt 123456789 10</code>"
            )
            chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(reply_msg.message_id)
            return

        user_id = int(parts[1])
        amount = float(parts[2])

        ensure_balance(user_id)
        user_balances[user_id]["USDT (TRC20)"] += amount
        save_balances()

        confirm_msg = await message.answer(
            f"✅ Пользователю <code>{user_id}</code> зачислено {amount} USDT (TRC20)."
        )
        chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(confirm_msg.message_id)

        try:
            user_msg = await bot.send_message(
                user_id,
                f"💰 Вам зачислено <b>{amount} USDT (TRC20)</b> на баланс."
            )
            chat_links.setdefault(user_id, {}).setdefault("msgs", []).append(user_msg.message_id)
        except:
            error_msg = await message.answer("Не удалось отправить сообщение пользователю.")
            chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(error_msg.message_id)

    except Exception as e:
        error_msg = await message.answer(f"❗ Ошибка: {e}")
        chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(error_msg.message_id)


@dp.message_handler(commands=['removeusdt'])
async def remove_usdt(message: types.Message):
    try:
        parts = message.text.strip().split()
        if len(parts) != 3:
            reply_msg = await message.reply(
                "❗ Напишите ID пользователя и сумму через пробел.\n"
                "Пример:\n<code>/removeusdt 5138418509 10</code>"
            )
            chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(reply_msg.message_id)
            return

        user_id = int(parts[1])
        amount = float(parts[2])

        ensure_balance(user_id)

        if user_balances[user_id]["USDT (TRC20)"] < amount:
            warn_msg = await message.reply("❗ Недостаточно средств на балансе.")
            chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(warn_msg.message_id)
            return

        user_balances[user_id]["USDT (TRC20)"] -= amount
        save_balances()

        success_msg = await message.reply(
            f"✅ С пользователя <code>{user_id}</code> снято <b>{amount} USDT (TRC20)</b>."
        )
        chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(success_msg.message_id)

        try:
            notify_msg = await bot.send_message(
                user_id,
                f"❌ С вашего баланса снято <b>{amount} USDT (TRC20)</b>."
            )
            chat_links.setdefault(user_id, {}).setdefault("msgs", []).append(notify_msg.message_id)
        except Exception as e:
            err_msg = await message.answer(f"Не удалось отправить сообщение пользователю.\n{e}")
            chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(err_msg.message_id)

    except Exception as e:
        error_msg = await message.reply(f"⚠️ Ошибка: {e}")
        chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(error_msg.message_id)




@dp.message_handler(commands=["backup"])
async def send_backup_file(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        warn = await message.answer("⛔ Команда доступна только администраторам.")
        chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(warn.message_id)
        return

    try:
        with open(BALANCE_FILE, "rb") as f:
            sent = await bot.send_document(message.chat.id, f, caption="📂 Резервная копия баланса")
            chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(sent.message_id)
    except FileNotFoundError:
        err = await message.answer("⚠️ Файл баланса ещё не создан.")
        chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(err.message_id)


@dp.message_handler(lambda m: m.text == "📥 Пополнить баланс")
@ban_check
async def handle_top_up(message: types.Message):
    txt = (
        f"💳 Отправьте USDT на адрес ниже:\n\n{get_wallets_text()}\n\n"
        f"⚠️ Мин. сумма пополнения — <b>{MIN_TOPUP}$</b>.\n"
        f"После оплаты нажмите кнопку ниже."
    )
    msg = await message.answer(
        txt,
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Я оплатил", callback_data="topup_done")
        )
    )
    chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(msg.message_id)

    # 💬 Зберігаємо message_id для подальшої очистки або історії
    chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(msg.message_id)

@dp.callback_query_handler(lambda c: c.data == "topup_done")
async def confirm_topup(call: types.CallbackQuery):
    user_id = call.from_user.id

    # Відповідь користувачу
    msg = await call.message.answer("⌛ Спасибо! Средства будут зачислены в течение 10 минут.")
    log_message(user_id, msg)

    # Сповіщення адміну
    for admin_id in ADMIN_IDS:
        try:
            admin_msg = await bot.send_message(
                admin_id,
                f"📩 Пользователь <code>{user_id}</code> нажал «Я оплатил».\n"
                f"Проверьте пополнение и вручную зачислите средства через /addusdt."
            )
            log_message(admin_id, admin_msg)
        except Exception as e:
            print(f"[⚠] Ошибка отправки сообщения админу: {e}")

@dp.callback_query_handler(lambda c: c.data == "pledge_sent")
async def pledge_confirmation(call: types.CallbackQuery):
    user_id = call.from_user.id

    # Відповідь користувачу
    await call.message.answer("⌛ Спасибо! Ожидайте от 10 до 30 минут...")
    # можеш додати:
    chat_links.setdefault(call.from_user.id, {}).setdefault("msgs", []).append(call.message.message_id)

    # Сповіщення всім адміністраторам
    for admin_id in ADMIN_IDS:
        try:
            pledge_msg = await bot.send_message(
                admin_id,
                f"🔔 Пользователь <code>{user_id}</code> нажал <b>«Я внес залог»</b>.\n"
                f"Проверьте поступление и подтвердите вручную."
            )
            # ✅ Зберігаємо ID повідомлення
            chat_links.setdefault(user_id, {}).setdefault("msgs", []).append(pledge_msg.message_id)

        except Exception as e:
            print(f"[⚠] Ошибка при отправке админу: {e}")

@dp.callback_query_handler(lambda c: c.data == "payment_received")
async def payment_received(call: types.CallbackQuery):
    await call.message.answer("✅ Ордер успешно исполнен.")
    await call.message.answer("❌ Диалог закрыт.", reply_markup=get_main_kb(call.from_user.id))

    target_username = chat_links.get(call.from_user.id, {}).get("with")
    target_id = None
    for uid, data in chat_links.items():
        if data.get("ad", {}).get("username") == target_username:
            target_id = uid
            break

    if target_id:
        completed_msg = await bot.send_message(target_id, "✅ Ордер завершен продавцом.")
        chat_links.setdefault(target_id, {}).setdefault("msgs", []).append(completed_msg.message_id)
        chat_links.pop(target_id, None)


@dp.callback_query_handler(lambda c: c.data.startswith("admin_del:"))
async def admin_delete_ad(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("⛔ Недостаточно прав.")

    _, ad_type, idx = call.data.split(":")
    idx = int(idx)

    if 0 <= idx < len(user_ads[ad_type]):
        removed = user_ads[ad_type].pop(idx)

        # також видалити з user_orders якщо є
        for uid, ads in user_balances.get("user_orders", {}).items():
            if removed in ads:
                ads.remove(removed)

        await call.message.edit_text("🗑 Объявление удалено администратором.")
    else:
        await call.answer("⚠️ Ошибка удаления.")

@dp.callback_query_handler(lambda c: c.data.startswith("delad:"))
@ban_check
async def delete_user_ad(call: types.CallbackQuery):
    idx = int(call.data.split(":")[1])
    user_id = call.from_user.id
    orders = user_balances.get("user_orders", {}).get(user_id, [])

    if 0 <= idx < len(orders):
        ad = orders.pop(idx)
        user_ads[ad["type"]].remove(ad)
        await call.message.edit_text("✅ Объявление удалено.")
    else:
        await call.message.answer("⚠️ Ошибка при удалении.")

@dp.message_handler(lambda m: m.text == "👛 Кошелёк")
@ban_check
async def wallet_view(message: types.Message):
    ensure_balance(message.from_user.id)
    bal = user_balances[message.from_user.id]
    txt = "👛 Ваш баланс:\n"
    for k, v in bal.items():
        txt += f"• {k}: <b>{v:.2f}</b>\n"
    msg = await message.answer(txt)
    chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(msg.message_id)

@dp.message_handler(lambda m: m.text == "🔻 Вывести USDT")
async def handle_withdraw(message: types.Message):
    ensure_balance(message.from_user.id)
    usdt_balance = user_balances[message.from_user.id]["USDT (TRC20)"]

    if usdt_balance < 1:
        msg = await message.answer("❌ Недостаточно средств для вывода. Минимум 10 USDT.")
        chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(msg.message_id)
        return

    msg = await message.answer(
        f"💸 Вы можете вывести USDT (TRC20).\n\n"
        f"Пожалуйста, отправьте адрес TRC20-кошелька, куда перевести <b>{usdt_balance:.2f} USDT</b>.\n\n"
        f"Или напишите админу с ID: <code>{message.from_user.id}</code>."
    )
    chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(msg.message_id)


@dp.message_handler(lambda m: m.text == "📋 Объявления")
@ban_check
async def show_ad_options(message: types.Message):
    msg = await message.answer(
        f"📊 Объявлений:\n"
        f"🔴 Продажа: {len(user_ads['sell'])}\n"
        f"🟢 Покупка: {len(user_ads['buy'])}"
    )
    chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(msg.message_id)


@dp.message_handler(lambda m: m.text == "🗂 Мои ордера")
@ban_check
async def show_my_orders(message: types.Message):
    user_id = message.from_user.id
    orders = user_balances.get("user_orders", {}).get(user_id, [])

    if not orders:
        msg = await message.answer("❌ У вас нет активных ордеров.")
        chat_links.setdefault(user_id, {}).setdefault("msgs", []).append(msg.message_id)
        return

    pledge_str = get_pledge_string(user_id)
    for idx, ad in enumerate(orders):
        text = (
            f"<b>#{idx + 1}</b> | Тип: <b>{ad['type']}</b>\n"
            f"Курс: {ad['rate']}₴\n"
            f"Объём: {ad['limit']}\n"
            f"Банки: {', '.join(ad['banks'])}\n"
            f"Залог: <b>{pledge_str}</b>\n"
            f"Условия: {ad.get('terms', '—')}"
        )
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("❌ Удалить", callback_data=f"delad:{idx}")
        )
        msg = await message.answer(text, reply_markup=kb)
        chat_links.setdefault(user_id, {}).setdefault("msgs", []).append(msg.message_id)


from datetime import datetime

@dp.message_handler(lambda m: m.text == "🟢 Покупка USDT")
@ban_check
async def handle_buy(message: types.Message):
    user_id = message.from_user.id

    # 1) Проверка временной блокировки
    if is_temp_banned(user_id):
        remaining = temp_bans[user_id] - datetime.now()
        mins = int(remaining.total_seconds() // 60)
        secs = int(remaining.total_seconds() % 60)
        return await message.answer(
            f"❌ Вы временно заблокированы от открытия ордеров за обман пользователей и неуплату.\n"
            f"Разблокировка через {mins} мин {secs} сек."
        )

    # 2) Обычная логика «Покупка»
    msg = await message.answer(
        "💰 Выберите диапазон:",
        reply_markup=get_range_kb("buy")
    )
    chat_links.setdefault(user_id, {}).setdefault("msgs", []).append(msg.message_id)


@dp.message_handler(lambda m: m.text == "🔴 Продажа USDT")
@ban_check
async def handle_sell(message: types.Message):
    user_id = message.from_user.id

    # 1) Проверка временной блокировки
    if is_temp_banned(user_id):
        remaining = temp_bans[user_id] - datetime.now()
        mins = int(remaining.total_seconds() // 60)
        secs = int(remaining.total_seconds() % 60)
        return await message.answer(
            f"❌ Вы временно заблокированы от открытия ордеров за обман пользователей и неуплату.\n"
            f"Разблокировка через {mins} мин {secs} сек."
        )

    # 2) Проверка баланса и остальная логика «Продажа»
    ensure_balance(user_id)
    if user_balances[user_id]["USDT (TRC20)"] < 10:
        msg = await message.answer("❌ Недостаточно средств на балансе.")
        chat_links.setdefault(user_id, {}).setdefault("msgs", []).append(msg.message_id)
        return

    msg = await message.answer(
        "💸 Выберите диапазон:",
        reply_markup=get_range_kb("sell")
    )
    chat_links.setdefault(user_id, {}).setdefault("msgs", []).append(msg.message_id)

@dp.message_handler(commands=["clear_chat"], user_id=ADMIN_IDS)
async def admin_clear_chat(message: types.Message):
    args = message.text.strip().split()
    if len(args) != 2:
        return await message.answer("⚠️ Введи команду так:\n<code>/clear_chat USER_ID</code>")

    try:
        target_id = int(args[1])

        # Отримуємо список збережених message_id
        msgs = chat_links.get(target_id, {}).get("msgs", [])
        if not msgs:
            return await message.answer("ℹ️ У пользователя нет сохранённых сообщений.")

        deleted_count = 0

        for msg_id in msgs:
            if not isinstance(msg_id, int):
                continue
            try:
                await bot.delete_message(chat_id=target_id, message_id=msg_id)
                deleted_count += 1
            except Exception as e:
                logging.warning(f"[DEL] Не вдалося видалити msg_id={msg_id}: {e}")

        # Очищаємо лог
        chat_links[target_id]["msgs"] = []
        await message.answer(f"✅ Удалено {deleted_count} сообщений у пользователя <code>{target_id}</code>")

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message_handler(lambda m: m.text == "🗨️ Чаты")
async def admin_chat_list(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("❌ У вас нет доступа к этой функции.")

    if not chat_links:
        return await message.answer("📭 Нет активных чатов.")

    for user_id, data in chat_links.items():
        ad = data.get("ad", {})
        buyer_id = data.get("buyer_id", user_id)
        seller_username = ad.get("username", "—")
        ad_type = ad.get("type", "—")

        text = (
            f"🔄 Чат:\n"
            f"👤 Покупатель: <code>{buyer_id}</code>\n"
            f"👤 Продавец: <code>{seller_username}</code>\n"
            f"📦 Ордер: <b>{ad_type.upper()}</b>\n"
        )
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("💬 Открыть чат", callback_data=f"adminchat:{buyer_id}")
        )
        await message.answer(text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "close_order", state="*")
async def close_order(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id

    # Отримуємо дані з state
    data = await state.get_data()
    # otype = data.get("order_type")  # Якщо не потрібен — можеш видалити

    # Видалення повідомлення з кнопкою
    try:
        await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    except Exception as e:
        print(f"❗ Помилка видалення кнопок: {e}")

    # Надсилаємо підтвердження
    await call.message.answer("✅ Ордер закрыт.", reply_markup=get_main_kb(user_id))

    # Видаляємо ордер із активних
    pair_id = active_orders.pop(user_id, None)
    if pair_id:
        active_orders.pop(pair_id, None)

    # Завершуємо стан
    await state.finish()
    await call.answer()
@dp.callback_query_handler(lambda c: c.data.startswith("buy:") or c.data.startswith("sell:"))
@ban_check
async def show_filtered_ads(call: types.CallbackQuery):
    prefix, rng = call.data.split(":")
    min_sum, max_sum = map(int, rng.split("-"))
    ads = user_ads[prefix]

    def limit_in_range(ad_limit, sel_min, sel_max):
        try:
            ad_min, ad_max = parse_limit(ad_limit)
            return sel_min <= ad_min and ad_max <= sel_max
        except:
            return False

    # собираем пары (оригинальный индекс, ad)
    filtered_pairs = [
        (orig_idx, ad)
        for orig_idx, ad in enumerate(ads)
        if limit_in_range(ad["limit"], min_sum, max_sum)
    ]

    if not filtered_pairs:
        msg = await call.message.answer("🔍 Объявлений не найдено.")
        log_message(call.from_user.id, msg)
        return

    msg_ids = []
    for display_idx, (orig_idx, ad) in enumerate(filtered_pairs, start=1):
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(
                "📩 Открыть ордер",
                callback_data=f"open:{prefix}:{orig_idx}"
            )
        )
        if call.from_user.id in ADMIN_IDS:
            kb.add(InlineKeyboardButton(
                "🗑 Удалить (админом)",
                callback_data=f"admin_del:{prefix}:{orig_idx}"
            ))

        msg = await call.message.answer(fmt_ad(ad, display_idx), reply_markup=kb)
        log_message(call.from_user.id, msg)
        msg_ids.append(msg.message_id)

    # Правильно добавляем все msg_id в chat_links без NameError
    links = chat_links.setdefault(call.from_user.id, {})
    links.setdefault("msgs", []).extend(msg_ids)
    links["admins"] = ADMIN_IDS.copy()


@dp.callback_query_handler(lambda c: c.data.startswith("open:"), state="*")
@ban_check
async def open_order(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id

    # 1) Проверка временной блокировки
    if is_temp_banned(user_id):
        return await call.answer(
            "❌ Вы временно заблокированы от открытия ордеров за обман пользователей и неуплату.\n"
            "Попробуйте позже.",
            show_alert=True
        )

    # 2) Дальнейшая логика открытия ордера
    _, otype, idx = call.data.split(":")
    idx = int(idx)

    ad = user_ads[otype][idx]
    buyer_id = user_id
    seller_username = ad["username"]

    if buyer_id not in chat_links:
        chat_links[buyer_id] = {}
    chat_links[buyer_id]["with"] = seller_username
    chat_links[buyer_id]["ad"] = ad

    if seller_username.startswith("User_"):
        seller_id = int(seller_username.replace("User_", ""))
        active_orders[buyer_id] = seller_id
        active_orders[seller_id] = buyer_id

        chat_links[seller_id] = {
            "with": buyer_id,
            "ad": ad
        }

        await state.update_data(
            order_type=otype,
            order_idx=idx,
            target_user=seller_id,
            ad_data=ad,
            buyer_id=buyer_id
        )

        msg = await bot.send_message(
            seller_id,
            f"📩 Ваше объявление открыто!\nСумма по объявлению: {ad['limit']} ₴"
        )
        chat_links.setdefault(seller_id, {}).setdefault("msgs", []).append(msg.message_id)
        log_message(seller_id, msg)

    else:
        await state.update_data(
            order_type=otype,
            order_idx=idx,
            ad_data=ad,
            buyer_id=buyer_id
        )

    # === ПРОДАЖ — реквизиты
    if otype == "sell":
        seller_id = int(ad["username"].replace("User_", "")) if ad["username"].startswith("User_") else None

        if seller_id and user_balances.get(seller_id, {}).get("USDT (TRC20)", 0) < 12:
            msg = await call.message.answer("❌ Недостаточно средств на балансе для открытия ордера. Минимум: 12 USDT.")
            log_message(buyer_id, msg)
            return

        await state.update_data(waiting_payment_details=True)

        msg = await call.message.answer("✍ Укажите реквизиты для оплаты (номер карты, банк и т.д.):")
        log_message(buyer_id, msg)
        return

    # === ПОКУПКА — спрашиваем сумму
    await OrderForm.amount_rub.set()
    msg = await call.message.answer("💰 Введите сумму в UAH, которую хотите обменять:")
    log_message(buyer_id, msg)

    # Удаление старых сообщений
    if buyer_id in chat_links:
        for msg_id in chat_links[buyer_id].get("msgs", []):
            if msg_id != call.message.message_id:
                try:
                    await bot.delete_message(call.message.chat.id, msg_id)
                except:
                    pass

    chat_links[buyer_id] = {"admins": ADMIN_IDS.copy()}

    for admin_id in ADMIN_IDS:
        admin_msg = await bot.send_message(
            admin_id,
            f"📥 Новый ордер ({otype.upper()})\n"
            f"Пользователь: <code>{buyer_id}</code>\n"
            f"Ожидается сообщение для передачи реквизитов."
        )
        chat_links.setdefault(buyer_id, {}).setdefault("msgs", []).append(admin_msg.message_id)

    chat_links[buyer_id]["admins"] = ADMIN_IDS.copy()

    msg = await call.message.answer(
        "💬 Ордер открыт. Вы можете переписываться здесь.\n\n"
        "Когда закончите — нажмите кнопку ниже.",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("❌ Завершить диалог", callback_data="end_chat")
        )
    )
    log_message(buyer_id, msg)

    # Задержка 3 минуты
    await asyncio.sleep(180)

    if chat_links.get(buyer_id, {}).get("confirm_sent"):
        return
    chat_links[buyer_id]["confirm_sent"] = True

    confirm_btn = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Я оплатил", callback_data=f"confirm:{otype}:{idx}")
    )
    msg = await bot.send_message(
        buyer_id,
        "Если вы произвели оплату, нажмите ниже:",
        reply_markup=confirm_btn
    )
    chat_links.setdefault(buyer_id, {}).setdefault("msgs", []).append(msg.message_id)
    log_message(buyer_id, msg)

@dp.callback_query_handler(lambda c: c.data.startswith("confirm:"))
async def confirm_payment(call: types.CallbackQuery):
    await call.answer()

    # Додаємо користувача до списку очікування скріншота
    await_screenshot.add(call.from_user.id)

    msg = await call.message.answer("📸 Отправьте, пожалуйста, скриншот оплаты.")
    log_message(call.from_user.id, msg)

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    if message.from_user.id in await_screenshot:
        await_screenshot.remove(message.from_user.id)

        for admin_id in ADMIN_IDS:
            msg = await bot.send_photo(
                admin_id,
                message.photo[-1].file_id,
                caption=f"📤 Скрин от <code>{message.from_user.id}</code>"
            )
            log_message(admin_id, msg)

        msg = await message.answer("✅ Скрин получен. USDT будут начислены в течение 10 минут.")
        log_message(message.from_user.id, msg)


@dp.message_handler(commands=["sendbalances"])
async def send_balances_excel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        # Завантаження балансу
        with open("balances.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        # Перетворення в DataFrame
        df = pd.DataFrame.from_dict(data, orient='index').reset_index()
        df.columns = ['User ID'] + list(df.columns[1:])

        # Збереження як Excel
        file_path = "balances.xlsx"
        df.to_excel(file_path, index=False)

        # Надсилання файлу
        doc_msg = await bot.send_document(message.chat.id, open(file_path, "rb"), caption="📊 Таблица баланса пользователей")
        log_message(message.from_user.id, doc_msg)

    except Exception as e:
        error_msg = await message.reply(f"⚠️ Ошибка при создании файла: {e}")
        log_message(message.from_user.id, error_msg)


banned_users = set()  # переконайся, що є ця змінна

@dp.message_handler(commands=["ban"], user_id=ADMIN_IDS)
async def ban_user(message: types.Message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.reply("❗ Использование: /ban <user_id>")
            return

        user_id = int(parts[1])
        banned_users.add(user_id)
        await message.reply(f"✅ Пользователь <code>{user_id}</code> заблокирован.")
    except Exception as e:
        await message.reply(f"⚠️ Ошибка: {e}")


@dp.message_handler(lambda m: m.text == "➕ Добавить объявление")
@ban_check
async def add_ad_start(message: types.Message):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🔴 Продажа", callback_data="adtype:sell"),
        InlineKeyboardButton("🟢 Покупка", callback_data="adtype:buy")
    )
    msg = await message.answer("🔄 Вы хотите купить или продать USDT?", reply_markup=kb)
    log_message(message.from_user.id, msg)

@dp.callback_query_handler(lambda c: c.data.startswith("adtype:"))
async def ad_choose_type(call: types.CallbackQuery, state: FSMContext):
    # Шаг 1: удаляем исходное сообщение с кнопками "Вы хотите купить или продать"
    await bot.delete_message(call.message.chat.id, call.message.message_id)

    _, adtype = call.data.split(":")
    user_id = call.from_user.id
    ensure_balance(user_id)

    # 🛑 Если это продажа — проверяем баланс
    if adtype == "sell" and user_balances[user_id]["USDT (TRC20)"] < 10:
        msg = await call.message.answer("❌ Недостаточно средств для создания объявления о продаже. Минимум: 10 USDT.")
        log_message(user_id, msg)
        return

    # 🛑 Проверка залога
    pledge = merchant_deposits.get(user_id)
    if not pledge or pledge.get("amount", 0) < 200:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Я внес залог", callback_data="pledge_sent")
        )
        msg = await call.message.answer(
            "🔒 Только верифицированные мерчанты могут размещать объявления.\n\n"
            "💰 Внесите залог от <b>200</b> до <b>500 USDT</b> на адрес:\n\n"
            "<code>TQz9gQCkYpARgjhZ3LkgvjBPXP3CbHLs4j</code>\n\n"
            "После оплаты нажмите кнопку ниже.",
            reply_markup=kb
        )
        log_message(user_id, msg)
        return

    await state.update_data(adtype=adtype)
    await AdForm.amount.set()
    msg = await call.message.answer("💵 Введите диапазон суммы (например: 500–2000 ₴):")
    log_message(user_id, msg)


    await state.update_data(adtype=adtype)
    await AdForm.amount.set()
    msg = await call.message.answer("💵 Введите диапазон суммы (например: 500–2000 ₴):")
    log_message(user_id, msg)


@dp.message_handler(commands=['unban'])
async def unban_user(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("❌ У вас нет прав на эту команду.")

    try:
        parts = message.text.split()
        if len(parts) < 2:
            return await message.answer("⚠️ Используйте формат: <code>/unban user_id</code>")

        user_id = int(parts[1])
        banned_users.discard(user_id)  # розблокує, якщо є

        await message.answer(f"✅ Пользователь <code>{user_id}</code> разблокирован.")
    except Exception as e:
        await message.answer(f"❗ Ошибка: {e}")


@dp.message_handler(commands=["closeorder"], user_id=ADMIN_IDS)
async def admin_close_order(message: types.Message):
    """
    Використання: /closeorder <user_id>
    Закриває активний ордер і блокує доступ на 30 хв через несплату.
    """
    parts = message.text.strip().split()
    if len(parts) != 2:
        return await message.reply("❗ Використання: /closeorder <user_id>")
    try:
        target = int(parts[1])
    except ValueError:
        return await message.reply("❗ <user_id> має бути числом")
    if target not in active_orders:
        return await message.reply(f"⚠️ У користувача {target} немає активного ордеру.")
    partner = active_orders.pop(target)
    active_orders.pop(partner, None)

    # Повідомляємо обидві сторони
    await bot.send_message(
        target,
        "❌ Ваш ордер закритий адміністратором через несплату."
    )
    await bot.send_message(
        partner,
        f"❌ Ордер користувача {target} закритий адміністратором."
    )

    # Ставимо блокування на 30 хв
    temp_bans[target] = datetime.now() + timedelta(minutes=30)

    await message.reply(
        f"✅ Ордер користувача {target} закрито.\n"
        f"Блокування створення ордерів на 30 хв."
    )



@dp.callback_query_handler(lambda c: c.data == "delmsg")
async def handle_delete_message(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("⛔ У вас нет прав.", show_alert=True)
    try:
        await bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        await call.answer(f"⚠️ Ошибка удаления.")

@dp.callback_query_handler(lambda c: c.data.startswith("adminchat:"))
async def open_admin_chat(call: types.CallbackQuery):
    buyer_id = int(call.data.split(":")[1])
    admin_id = call.from_user.id

    if buyer_id not in chat_links:
        msg = await call.message.answer("❌ Чат не найден.")
        log_message(admin_id, msg)
        return

    chat_links[admin_id] = {"with": buyer_id, "is_admin": True}
    msg = await call.message.answer("💬 Вы подключены к чату. Напишите сообщение.")
    log_message(admin_id, msg)

@dp.message_handler(state=AdForm.amount)
@ban_check
async def ad_set_amount(message: types.Message, state: FSMContext):
    text = message.text.strip()

    # Якщо немає значка "₴", додаємо автоматично
    if "₽" not in text:
        text += " ₽"

    await state.update_data(amount=text)
    await AdForm.rate.set()
    await message.answer("💰 Введите курс в ₴ (например: 43.12):")


@dp.message_handler(state=AdForm.rate)
@ban_check
async def ad_set_rate(message: types.Message, state: FSMContext):
    await state.update_data(rate=message.text)
    await AdForm.banks.set()
    msg = await message.answer("🏦 Укажите банки через запятую (например: MonoBank,PrivatBank,ПУМБ):")
    log_message(message.from_user.id, msg)

@dp.message_handler(state=AdForm.banks)
@ban_check
async def ad_finish(message: types.Message, state: FSMContext):
    await state.update_data(banks=[b.strip() for b in message.text.split(",")])
    data = await state.get_data()

    user_id = message.from_user.id
    rate = float(data["rate"])
    ad_type = data["adtype"]
    limit_str = data["amount"]

    # 🔒 Перевірка застави
    pledge = merchant_deposits.get(user_id)
    if not pledge or pledge.get("amount", 0) < 200:
        msg = await message.answer(
            "⛔ Объявление может создать только проверенный мерчант, внесите залог от 200 до 500 USDT."
        )
        log_message(user_id, msg)
        return

    # ✅ Якщо це ПРОДАЖ — перевіряємо баланс
    if ad_type == "sell":
        try:
            min_limit, _ = parse_limit(limit_str)
            required_usdt = round(min_limit / rate, 2)

            current_usdt = user_balances.get(user_id, {}).get("USDT (TRC20)", 0)
            if current_usdt < required_usdt:
                msg = await message.answer(
                    f"❌ Недостаточно USDT на балансе для создания объявления.\n"
                    f"Минимум нужно: <b>{required_usdt} USDT</b>, у вас: <b>{current_usdt} USDT</b>."
                )
                log_message(user_id, msg)
                return
        except Exception as e:
            msg = await message.answer(f"⚠️ Ошибка диапазона: {e}")
            log_message(user_id, msg)
            return

    # === Створення оголошення
    ad = {
        "username": f"User_{user_id}",
        "rate": rate,
        "limit": limit_str,
        "banks": data["banks"],
        "terms": "Без дополнительных условий",
        "type": ad_type
    }

    print("=== AD TYPE ===", data["adtype"])
    print("=== AD OBJECT ===", ad)

    # ➕ Додаємо в глобальний список
    user_ads[ad_type].append(ad)

    # ➕ Додаємо в особистий список
    if "user_orders" not in user_balances:
        user_balances["user_orders"] = {}
    if user_id not in user_balances["user_orders"]:
        user_balances["user_orders"][user_id] = []
    user_balances["user_orders"][user_id].append(ad)

    msg = await message.answer("✅ Объявление добавлено.", reply_markup=get_main_kb(user_id))
    log_message(user_id, msg)
    await state.finish()

@dp.message_handler(commands=["confirm_pledge"])
async def confirm_pledge(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply("⛔ Команда доступна только администраторам.")

    try:
        parts = message.text.strip().split()
        if len(parts) != 3:
            return await message.reply("❗ Формат: /confirm_pledge <user_id> <сумма>")

        user_id = int(parts[1])
        amount = float(parts[2])

        merchant_deposits[user_id] = {
            "amount": amount,
            "target": MERCHANT_TARGET,
            "verified": True
        }

        save_merchant_deposits()

        await message.reply(f"✅ Залог {amount} USDT подтверждён для пользователя {user_id}.")

        msg = await bot.send_message(
            user_id,
            "✅ Ваш залог подтверждён! Теперь вы можете размещать объявления."
        )
        chat_links.setdefault(user_id, {}).setdefault("msgs", []).append(msg.message_id)

    except Exception as e:
        await message.reply(f"❗ Ошибка: {e}")


@dp.message_handler(state=OrderForm.amount_rub)
async def order_enter_amount(message: types.Message, state: FSMContext):
    amount_text = message.text.strip()
    buyer_id = message.from_user.id

    # проверяем, что ввели число
    if not amount_text.replace(".", "").isdigit():
        msg = await message.answer("⚠️ Введите число в ₴ (например: 1500).")
        log_message(buyer_id, msg)
        return

    amount_rub = float(amount_text)
    data = await state.get_data()
    ad = data["ad_data"]
    order_type = data["order_type"]
    order_idx  = data["order_idx"]

    # парсим диапазон объявления
    try:
        min_limit, max_limit = parse_limit(ad["limit"])
    except Exception as e:
        msg = await message.answer(f"⚠️ Невозможно определить диапазон объявления: {e}")
        log_message(buyer_id, msg)
        return

    # проверяем, что сумма в пределах
    if amount_rub < min_limit or amount_rub > max_limit:
        msg = await message.answer(
            f"❌ Сумма вне диапазона объявления ({min_limit}–{max_limit} ₴).\n"
            f"Пожалуйста, введите сумму в пределах этого диапазона."
        )
        log_message(buyer_id, msg)
        return

    # если это продажа — проверяем баланс продавца
    seller_id = None
    if ad["username"].startswith("User_"):
        seller_id = int(ad["username"].split("_", 1)[1])
    if order_type == "sell" and seller_id:
        usdt_balance = user_balances.get(seller_id, {}).get("USDT (TRC20)", 0)
        required_usdt = round(amount_rub / ad["rate"], 2)
        if usdt_balance < required_usdt:
            msg = await message.answer(
                f"❌ Недостаточно USDT на балансе продавца.\n"
                f"Нужно: {required_usdt} USDT, есть: {usdt_balance} USDT."
            )
            log_message(buyer_id, msg)
            return
        # списываем
        user_balances[seller_id]["USDT (TRC20)"] -= required_usdt
        save_balances()

    # устанавливаем связь в chat_links
    chat_links[buyer_id] = {"target": seller_id, "admins": ADMIN_IDS.copy()}
    if seller_id:
        chat_links[seller_id] = {"target": buyer_id, "admins": ADMIN_IDS.copy()}

    # уведомляем покупателя
    msg1 = await message.answer(
        f"📩 Ордер открыт!\nСумма: <b>{amount_rub} ₴</b>\nОжидайте реквизиты.",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("❌ Закрыть ордер", callback_data="close_order")
        )
    )
    log_message(buyer_id, msg1)

    # уведомляем продавца, если это пользователь
    if seller_id:
        msg2 = await bot.send_message(
            seller_id,
            f"📥 Ваш ордер открыли на сумму <b>{amount_rub} ₴</b>!\n"
            "Вы можете переписываться с покупателем прямо здесь."
        )
        log_message(seller_id, msg2)

    # даем 3 минуты на оплату, потом присылаем кнопку подтвердить
    await asyncio.sleep(180)
    if not chat_links.get(buyer_id, {}).get("confirm_button_sent"):
        chat_links[buyer_id]["confirm_button_sent"] = True
        msg3 = await bot.send_message(
            buyer_id,
            "Если вы произвели оплату, нажмите ниже:",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("✅ Я оплатил", callback_data=f"confirm:{order_type}:{order_idx}")
            )
        )
        log_message(buyer_id, msg3)

    await state.finish()

@dp.message_handler(state="*", content_types=types.ContentType.TEXT)
async def handle_payment_details(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data.get("waiting_payment_details"):
        buyer_id = data.get("buyer_id")
        if not buyer_id:
            msg = await message.answer("⚠️ Ошибка: ID покупателя не найден.")
            log_message(message.from_user.id, msg)
            return

        # Надсилаємо реквізити покупцю
        msg1 = await bot.send_message(buyer_id, f"💳 Реквизиты продавца:\n<code>{message.text}</code>")
        chat_links.setdefault(buyer_id, {}).setdefault("msgs", []).append(msg1.message_id)

        # Підтвердження продавцю
        msg2 = await message.answer("✅ Реквизиты отправлены покупателю.")
        log_message(message.from_user.id, msg2)
        chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(msg2.message_id)

        # Кнопка "Средства получены"
        msg3 = await message.answer(
            "🟢 Когда получите оплату, нажмите кнопку ниже:",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("✅ Средства получены", callback_data="payment_received")
            )
        )
        chat_links.setdefault(message.from_user.id, {}).setdefault("msgs", []).append(msg3.message_id)
        log_message(message.from_user.id, msg3)

        await state.finish()
# === Прокладка: адмін бачить повідомлення користувача
@dp.message_handler(lambda m: m.from_user.id in ADMIN_IDS)
async def admin_to_user(message: types.Message):
    text = message.text.strip()

    try:
        uid_str, msg = text.split(" ", 1)
        uid = int(uid_str)

        # Кнопка "Удалить"
        reply_markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton("🗑 Удалить", callback_data="delmsg")
        )

        # Надсилання повідомлення користувачу
        sent = await bot.send_message(uid, msg, reply_markup=reply_markup)

        # Зберігання ID повідомлення
        chat_links.setdefault(uid, {}).setdefault("msgs", []).append(sent.message_id)

        await message.answer("✅ Сообщение отправлено.")

    except Exception as e:
        await message.answer(
            "❗ Напишите ID пользователя, а затем через пробел сообщение.\n"
            "Пример:\n<code>5138418509 Привет</code>\n"
            f"Ошибка: {e}"
        )

# === Прокладка: адмін відповідає користувачу
@dp.message_handler(lambda m: m.from_user.id in ADMIN_IDS and m.reply_to_message and m.reply_to_message.text)
async def admin_reply_handler(message: types.Message):
    lines = message.reply_to_message.text.split("\n")
    for line in lines:
        if "от" in line and "Сообщение" in line:
            uid = int(line.split("от")[1].split(":")[0].strip())
            reply_markup = InlineKeyboardMarkup().add(
                InlineKeyboardButton("🗑 Удалить", callback_data="delmsg")
            )
            await bot.send_message(uid, message.text, reply_markup=reply_markup)
            break

@dp.message_handler(lambda m: m.from_user.id in active_orders, content_types=types.ContentType.TEXT)
async def relay_message_between_users(message: types.Message):
    sender_id = message.from_user.id
    recipient_id = active_orders.get(sender_id)
    if not recipient_id:
        return

    sender_name = f"@{message.from_user.username}" if message.from_user.username else f"User {sender_id}"
    text = f"💬 Сообщение от {sender_name}:\n{message.text}"

    # ➕ Надсилаємо співрозмовнику
    msg1 = await bot.send_message(recipient_id, text)
    log_message(recipient_id, msg1)  # логування

    # ➕ Надсилаємо копію адмінам
    for admin in ADMIN_IDS:
        msg2 = await bot.send_message(admin, f"📩 [{sender_id} ➝ {recipient_id}]: {message.text}")
        log_message(admin, msg2)  # логування

# --- 2. Обробка повідомлень ---
@dp.message_handler()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "—"

    if user_id not in sent_chat_ids:
        sent_chat_ids.add(user_id)
        for admin_id in ADMIN_IDS:
            await bot.send_message(
                admin_id,
                f"📩 Новий користувач!\n"
                f"👤 ID: <code>{user_id}</code>\n"
                f"🔗 Username: @{username}"
            )

    # Тут можеш залишити або обробляти інші повідомлення
    # await message.answer("✅ Повідомлення отримано.")

# --- 3. Обробка будь-якої кнопки ---
@dp.message_handler(content_types=types.ContentTypes.ANY)
async def forward_message(message: types.Message):
    user_id = message.from_user.id
    sender_name = message.from_user.username or f"User_{user_id}"

    # отримуємо ID співрозмовника
    link = chat_links.get(user_id)
    if not link:
        await message.reply("❗ Диалог не найден.")
        return

    recipient_id = link.get("target")
    target_id = recipient_id  # для дублювання в кінець

    # === Текст ===
    if message.text:
        text = f"💬 Сообщение от {sender_name}:\n{message.text}"
        msg = await bot.send_message(recipient_id, text)
        chat_links.setdefault(recipient_id, {}).setdefault("msgs", []).append(msg.message_id)

        for admin in ADMIN_IDS:
            msg = await bot.send_message(admin, f"📩 [{user_id} ➝ {recipient_id}]: {message.text}")
            chat_links.setdefault(admin, {}).setdefault("msgs", []).append(msg.message_id)

    # === Фото ===
    elif message.photo:
        file = message.photo[-1].file_id
        caption = f"📷 Фото от {sender_name}"
        msg = await bot.send_photo(recipient_id, file, caption=caption)
        chat_links.setdefault(recipient_id, {}).setdefault("msgs", []).append(msg.message_id)

        for admin in ADMIN_IDS:
            msg = await bot.send_photo(admin, file, caption=f"📥 [{user_id} ➝ {recipient_id}] Фото")
            chat_links.setdefault(admin, {}).setdefault("msgs", []).append(msg.message_id)

    # === Документ ===
    elif message.document:
        file = message.document.file_id
        msg = await bot.send_document(recipient_id, file, caption=f"📎 Файл от {sender_name}")
        chat_links.setdefault(recipient_id, {}).setdefault("msgs", []).append(msg.message_id)

        for admin in ADMIN_IDS:
            msg = await bot.send_document(admin, file, caption=f"📥 [{user_id} ➝ {recipient_id}] Документ")
            chat_links.setdefault(admin, {}).setdefault("msgs", []).append(msg.message_id)

    # === Видео ===
    elif message.video:
        file = message.video.file_id
        msg = await bot.send_video(recipient_id, file, caption=f"🎥 Видео от {sender_name}")
        chat_links.setdefault(recipient_id, {}).setdefault("msgs", []).append(msg.message_id)

        for admin in ADMIN_IDS:
            msg = await bot.send_video(admin, file, caption=f"📥 [{user_id} ➝ {recipient_id}] Видео")
            chat_links.setdefault(admin, {}).setdefault("msgs", []).append(msg.message_id)

    # === Голосове ===
    elif message.voice:
        file = message.voice.file_id
        msg = await bot.send_voice(recipient_id, file, caption=f"🎤 Голосовое сообщение от {sender_name}")
        chat_links.setdefault(recipient_id, {}).setdefault("msgs", []).append(msg.message_id)

        for admin in ADMIN_IDS:
            msg = await bot.send_voice(admin, file, caption=f"📥 [{user_id} ➝ {recipient_id}] Voice")
            chat_links.setdefault(admin, {}).setdefault("msgs", []).append(msg.message_id)

    # === Unsupported
    else:
        await message.reply("⚠️ Тип повідомлення не підтримується.")
        return

    # === Додаткове дублювання співрозмовнику і адмінам
    if message.text:
        msg = await bot.send_message(target_id, f"💬 Сообщение от @{sender_name}:\n{message.text}")
        chat_links.setdefault(target_id, {}).setdefault("msgs", []).append(msg.message_id)

        for admin in ADMIN_IDS:
            msg = await bot.send_message(admin, f"📩 [Диалог] {user_id} ➝ {target_id}:\n{message.text}")
            chat_links.setdefault(admin, {}).setdefault("msgs", []).append(msg.message_id)

@dp.message_handler(content_types=[types.ContentType.PHOTO, types.ContentType.DOCUMENT, types.ContentType.VIDEO])
async def user_media_relay(message: types.Message):
    user_id = message.from_user.id

    if user_id not in chat_links or "with" not in chat_links[user_id]:
        return  # немає активного чату

    target_username = chat_links[user_id]["with"]

    # знайти ID співрозмовника по username
    target_id = None
    for uid, data in chat_links.items():
        if data.get("ad", {}).get("username") == target_username:
            target_id = uid
            break

    if not target_id:
        return await message.answer("⚠️ Пользователь недоступен.")

    caption = f"📎 От @{message.from_user.username or 'user'}"
    admins_caption = f"📥 Медиа: {user_id} ➝ {target_id}"

    # --- Логування функція ---
    def log(msg_obj, uid):
        if uid not in chat_logs:
            chat_logs[uid] = []
        chat_logs[uid].append(msg_obj.message_id)

    # === Фото ===
    if message.photo:
        msg1 = await bot.send_photo(target_id, message.photo[-1].file_id, caption=caption)
        log(msg1, target_id)

        for admin in ADMIN_IDS:
            msg2 = await bot.send_photo(admin, message.photo[-1].file_id, caption=admins_caption)
            log(msg2, admin)

    # === Документ ===
    elif message.document:
        msg1 = await bot.send_document(target_id, message.document.file_id, caption=caption)
        log(msg1, target_id)

        for admin in ADMIN_IDS:
            msg2 = await bot.send_document(admin, message.document.file_id, caption=admins_caption)
            log(msg2, admin)

    # === Відео ===
    elif message.video:
        msg1 = await bot.send_video(target_id, message.video.file_id, caption=caption)
        log(msg1, target_id)

        for admin in ADMIN_IDS:
            msg2 = await bot.send_video(admin, message.video.file_id, caption=admins_caption)
            log(msg2, admin)

@dp.callback_query_handler(lambda c: c.data == "end_chat")
async def end_chat(call: types.CallbackQuery):
    user_id = call.from_user.id

    if user_id not in chat_links or "with" not in chat_links[user_id]:
        return await call.message.answer("⚠️ У вас нет активного диалога.")

    # повідомити обох
    target_username = chat_links[user_id]["with"]
    target_id = None

    for uid, data in chat_links.items():
        if data.get("ad", {}).get("username") == target_username:
            target_id = uid
            break

    if target_id:
        msg = await bot.send_message(target_id, "❌ Диалог завершен другой стороной.")
        chat_links.setdefault(target_id, {}).setdefault("msgs", []).append(msg.message_id)
        chat_links.pop(target_id, None)

    msg = await call.message.answer("✅ Диалог завершен.")
    chat_links.setdefault(user_id, {}).setdefault("msgs", []).append(msg.message_id)
    chat_links.pop(user_id, None)


@dp.message_handler(content_types=types.ContentTypes.ANY)
async def relay_messages(message: types.Message):
    sender_id = message.from_user.id

    if sender_id in active_orders:
        recipient_id = active_orders[sender_id]

        if message.content_type == "text":
            # Текст
            msg = await bot.send_message(recipient_id, f"💬 {message.text}")
            chat_links.setdefault(recipient_id, {}).setdefault("msgs", []).append(msg.message_id)

        elif message.content_type in ["photo", "document", "video", "voice"]:
            # Медіа
            msg = await bot.copy_message(recipient_id, sender_id, message.message_id)
            chat_links.setdefault(recipient_id, {}).setdefault("msgs", []).append(msg.message_id)

# === Запуск
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

