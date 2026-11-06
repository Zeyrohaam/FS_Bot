from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_CHAT_ID, ADMIN_IDS, MONO, TON, PREMIUM_SELLER_USERNAME
from database import db
from handlers.calculator import get_price, get_price_per_star, show_calculator_menu
from keyboards.reply import main_menu, menu_with_back, purchases_menu, support_category_menu, back_only_keyboard
import html as html_lib
from utils.helpers import (
    add_star_balance,
    add_ton_balance,
    format_stars,
    get_numeric_balance,
    get_numeric_ton_balance,
    register_user_if_needed,
    safe_edit_message,
    sub_star_balance,
    sub_ton_balance,
)
from utils.ton_rate import async_ton_to_uah_buy_price, async_uah_to_ton
# Aliases so the rest of the module keeps the same call-sites
ton_to_uah_buy_price = async_ton_to_uah_buy_price
uah_to_ton = async_uah_to_ton
from utils.pricing import get_premium_prices, get_star_packages
from utils.referrals import reward_referrer_for_purchase

router = Router()


class PaymentStates(StatesGroup):
    waiting_custom_amount = State()
    waiting_stars_target_username = State()
    waiting_premium_username = State()
    waiting_withdraw_amount = State()
    waiting_ton_withdraw_amount = State()
    waiting_payment_proof = State()
    waiting_ton_topup_amount = State()


async def _handle_waiting_navigation(message: Message, state: FSMContext, back_target: str) -> bool:
    text = (message.text or "").strip()
    if not text:
        return False

    if text == "⬅️ Назад":
        await state.clear()
        if back_target == "stars":
            await buy_stars(message)
            return True
        if back_target == "premium":
            await buy_premium(message)
            return True
        if back_target == "ton":
            await start_ton_topup_flow(message, state)
            return True
        if back_target == "purchases":
            await message.answer("🛍️ Покупки\n\nВыберите, что хотите открыть:", reply_markup=purchases_menu(message.from_user.id in ADMIN_IDS))
            return True
        await message.answer("🛍️ Покупки\n\nВыберите, что хотите открыть:", reply_markup=purchases_menu(message.from_user.id in ADMIN_IDS))
        return True

    mapping = {
        "💰 Купить Stars": buy_stars,
        "👑 Купить Premium": buy_premium,
        "💠 Купить TON": lambda m: start_ton_topup_flow(m, state),
    }
    if text in mapping:
        await state.clear()
        await mapping[text](message)
        return True

    if text == "🛍️ Покупки":
        await state.clear()
        await message.answer("🛍️ Покупки\n\nВыберите, что хотите открыть:", reply_markup=purchases_menu(message.from_user.id in ADMIN_IDS))
        return True
    if text == "🆘 Поддержка":
        await state.clear()
        await message.answer("🆘 Раздел поддержки. Выберите действие:", reply_markup=support_category_menu(message.from_user.id in ADMIN_IDS))
        return True
    if text == "🧮 Посчитать":
        await state.clear()
        await show_calculator_menu(message, state)
        return True
    if text == "👤 Профиль":
        await state.clear()
        from handlers.admin import show_profile
        await show_profile(message)
        return True
    if text == "👥 Рефералы":
        await state.clear()
        from handlers.user import referrals_message_handler
        await referrals_message_handler(message)
        return True
    if text == "🎮 Игры":
        await state.clear()
        from handlers.user import games_redirect_handler
        await games_redirect_handler(message)
        return True
    if text == "⚙️ Админ-панель" and message.from_user.id in ADMIN_IDS:
        await state.clear()
        from handlers.admin import admin_panel
        await admin_panel(message)
        return True
    return False


def build_stars_payment_callback(prefix: str, method: str, package: dict | None = None) -> str:
    if not package:
        return f"{prefix}_{method}"
    target_username = package.get("target_username") or ""
    stars = int(package["stars"])
    price = float(package["price"])
    return f"{prefix}_{method}|{stars}|{price:.2f}|{target_username}"


def parse_stars_payment_callback(callback_data: str) -> dict | None:
    if "|" not in callback_data:
        return None
    prefix_method, payload = callback_data.split("|", 1)
    if not prefix_method.startswith("payment_"):
        return None
    parts = payload.split("|", 2)
    if len(parts) < 2:
        return None
    try:
        stars = int(parts[0])
    except ValueError:
        return None
    if stars < 50 or stars > 10000:
        return None
    price = float(get_price(stars))
    target_username = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
    return {
        "stars": stars,
        "price": price,
        "target_username": target_username,
        "purchase_for": "friend" if target_username else "self",
    }


def payment_methods_keyboard(prefix: str, package: dict | None = None, include_ton_balance: bool = True, include_ton_wallet: bool = True, include_card: bool = True) -> InlineKeyboardMarkup:
    rows = []
    if include_card:
        rows.append([InlineKeyboardButton(text="💳 Оплатить картой Mono", callback_data=build_stars_payment_callback(prefix, "mono", package))])
    if include_ton_wallet:
        rows.append([InlineKeyboardButton(text="💠 Оплатить на TON кошелёк", callback_data=build_stars_payment_callback(prefix, "ton_wallet", package))])
    if include_ton_balance:
        rows.append([InlineKeyboardButton(text="💠 С TON баланса", callback_data=build_stars_payment_callback(prefix, "ton_balance", package))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_stars_target_callback(action: str, package: dict | None = None) -> str:
    if not package:
        return action
    target_username = package.get("target_username") or ""
    stars = int(package["stars"])
    price = float(package["price"])
    return f"{action}|{stars}|{price:.2f}|{target_username}"


def parse_stars_target_callback(callback_data: str) -> dict | None:
    if "|" not in callback_data:
        return None
    action, payload = callback_data.split("|", 1)
    if action not in {"stars_target_self", "stars_target_friend"}:
        return None
    parts = payload.split("|", 2)
    if len(parts) < 2:
        return None
    try:
        stars = int(parts[0])
    except ValueError:
        return None
    if stars < 50 or stars > 10000:
        return None
    price = float(get_price(stars))
    target_username = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
    return {
        "stars": stars,
        "price": price,
        "target_username": target_username,
        "purchase_for": "friend" if target_username else "self",
    }


def stars_target_keyboard(package: dict | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🙋 Себе", callback_data=build_stars_target_callback("stars_target_self", package))],
            [InlineKeyboardButton(text="🎁 Другу", callback_data=build_stars_target_callback("stars_target_friend", package))],
        ]
    )


def _resolve_db_username(username: str | None) -> str | None:
    raw = (username or "").strip()
    if not raw:
        return None
    return raw[1:] if raw.startswith("@") else raw


def find_user_id_by_username(username: str | None) -> int | None:
    db.refresh()
    target = _resolve_db_username(username)
    if not target:
        return None
    target = target.lower()
    for user_id, user_data in db.users.items():
        stored = _resolve_db_username(user_data.get("username"))
        if stored and stored.lower() == target:
            try:
                return int(user_id)
            except Exception:
                return None
    return None


async def show_stars_payment_options(message: Message, state: FSMContext):
    data = await state.get_data()
    package = data.get("selected_package")
    if not package:
        await message.answer("❌ Заказ не найден")
        return
    target_username = package.get("target_username")
    target_line = "🙋 Покупка себе" if not target_username else f"🎁 Покупка другу: {target_username}"
    await state.set_state(None)
    await message.answer(
        f"⭐️ {package['stars']} звёзд — {float(package['price']):.2f} грн\n{target_line}\n\nВыберите способ оплаты:",
        reply_markup=payment_methods_keyboard("payment", package=package),
    )


def balance_topup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💠 Пополнить TON", callback_data="ton_topup_start")],
        ]
    )

def withdraw_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💸 Вывести", callback_data="withdraw_start")]])


def admin_payment_keyboard(transaction_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{transaction_id}"), InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{transaction_id}")]])


def admin_withdraw_keyboard(transaction_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить вывод", callback_data=f"withdraw_confirm_{transaction_id}"), InlineKeyboardButton(text="❌ Отклонить вывод", callback_data=f"withdraw_reject_{transaction_id}")]])


def get_user_pending_withdraw(user_id: int, withdraw_type: str | None = None):
    db.refresh()
    allowed = {withdraw_type} if withdraw_type else {"withdraw", "withdraw_ton"}
    return next((t for t in db.transactions if t.get("type") in allowed and int(t.get("user_id", 0)) == int(user_id) and t.get("status") == "pending"), None)


def _is_admin_callback_actor(callback: CallbackQuery) -> bool:
    if callback.from_user and int(callback.from_user.id) in set(int(x) for x in ADMIN_IDS):
        return True
    return False


async def buy_stars(message: Message):
    register_user_if_needed(message.from_user.id, message.from_user.username)
    rows = [[InlineKeyboardButton(text=f"⭐ {stars} — {price:.2f} грн", callback_data=f"package_{stars}")] for stars, price in get_star_packages().items()]
    rows.append([InlineKeyboardButton(text="🔢 Своё количество", callback_data="custom_amount")])
    await message.answer(
        "⭐ <b>Купить Telegram Stars</b>\n\n"
        "Выберите готовый пакет или введите своё количество:\n\n"
        "<i>Звёзды зачисляются моментально на ваш профиль</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


async def buy_premium(message: Message):
    register_user_if_needed(message.from_user.id, message.from_user.username)
    rows = [[InlineKeyboardButton(text=f"👑 {months} мес. — {price:.2f} грн", callback_data=f"premium_{months}")] for months, price in get_premium_prices().items()]
    await message.answer(
        "👑 <b>Купить Telegram Premium</b>\n\n"
        "Premium открывает эксклюзивные возможности Telegram:\n"
        "• Увеличенные лимиты загрузок\n"
        "• Уникальные стикеры и реакции\n"
        "• Приоритет в поиске\n\n"
        "<i>Выберите срок подписки</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


async def show_balance_topup_options(message: Message, state: FSMContext | None = None):
    register_user_if_needed(message.from_user.id, message.from_user.username)
    if state is not None:
        await start_ton_topup_flow(message, state)
        return
    await message.answer(
        "💠 Купить TON\n\nВведите, сколько TON хотите купить.\nНапример: 1.5",
        reply_markup=menu_with_back(message.from_user.id in ADMIN_IDS),
    )


async def start_ton_topup_flow(message: Message, state: FSMContext):
    register_user_if_needed(message.from_user.id, message.from_user.username)
    await state.clear()
    await state.set_state(PaymentStates.waiting_ton_topup_amount)
    await message.answer(
        "💠 <b>Купить TON</b>\n\n"
        "Введите количество TON, которое хотите купить.\n\n"
        "<i>Например: 1.5 или 5</i>",
        parse_mode="HTML",
        reply_markup=back_only_keyboard(),
    )




@router.message(F.text == "💰 Купить Stars")
async def stars_message(message: Message, state: FSMContext):
    await state.clear()
    await buy_stars(message)


@router.message(F.text == "👑 Купить Premium")
async def premium_message(message: Message, state: FSMContext):
    await state.clear()
    await buy_premium(message)


@router.message(F.text == "💠 Купить TON")
async def balance_topup_message(message: Message, state: FSMContext):
    await state.clear()
    await start_ton_topup_flow(message, state)


@router.callback_query(F.data.startswith("package_"))
async def process_package_selection(callback: CallbackQuery, state: FSMContext):
    stars = int(callback.data.split("_")[1])
    price = float(get_star_packages()[stars])
    package = {"stars": stars, "price": price, "target_username": None, "purchase_for": "self"}
    await state.update_data(
        selected_package=package,
        premium_order=None,
        ton_topup_order=None,
    )
    await safe_edit_message(callback, f"⭐️ {stars} звёзд — {price:.2f} грн\n\nКому покупаете?", reply_markup=stars_target_keyboard(package))
    await callback.answer()


@router.callback_query(F.data == "custom_amount")
async def custom_amount(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(PaymentStates.waiting_custom_amount)
    await callback.message.answer(
        "✍️ <b>Введите количество звёзд</b>\n\n"
        f"<i>От 50 до 10 000 штук</i>",
        parse_mode="HTML",
        reply_markup=back_only_keyboard(),
    )
    await callback.answer()


@router.message(PaymentStates.waiting_custom_amount)
async def process_custom_amount(message: Message, state: FSMContext):
    if await _handle_waiting_navigation(message, state, "stars"):
        return
    try:
        stars = int((message.text or "").strip())
    except Exception:
        await message.answer("❌ Введите число")
        return
    price = get_price(stars)
    if price is None:
        await message.answer("❌ Введите от 50 до 10000")
        return
    coef = get_price_per_star(stars)
    package = {"stars": stars, "price": price, "target_username": None, "purchase_for": "self"}
    await state.update_data(
        selected_package=package,
        premium_order=None,
        ton_topup_order=None,
    )
    await state.set_state(None)
    await message.answer(
        f"⭐️ {stars} = {price:.2f} грн\n💱 Курс: {coef}₴ за ⭐\n\nКому покупаете?",
        reply_markup=stars_target_keyboard(package),
    )


@router.callback_query(F.data.startswith("stars_target_self"))
async def stars_target_self(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    package = data.get("selected_package")
    if not package:
        package = parse_stars_target_callback(callback.data)
    if not package:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    package["purchase_for"] = "self"
    package["target_username"] = None
    await state.update_data(selected_package=package)
    await safe_edit_message(
        callback,
        f"⭐️ {package['stars']} звёзд — {float(package['price']):.2f} грн\n🙋 Покупка себе\n\nВыберите способ оплаты:",
        reply_markup=payment_methods_keyboard("payment", package=package),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("stars_target_friend"))
async def stars_target_friend(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    package = data.get("selected_package")
    if not package:
        package = parse_stars_target_callback(callback.data)
    if not package:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    package["purchase_for"] = "friend"
    await state.update_data(selected_package=package)
    await state.set_state(PaymentStates.waiting_stars_target_username)
    await safe_edit_message(callback, "🎁 Покупка звёзд другу\n\nОтправьте @username человека, которому нужно купить звёзды.")
    await callback.message.answer("✍️ Введите @username получателя:", reply_markup=back_only_keyboard())
    await callback.answer()


@router.message(PaymentStates.waiting_stars_target_username)
async def stars_target_username_received(message: Message, state: FSMContext):
    if await _handle_waiting_navigation(message, state, "stars"):
        return
    username = (message.text or "").strip()
    if not username.startswith("@") or len(username) < 2:
        await message.answer("❌ Отправьте корректный @username")
        return
    data = await state.get_data()
    package = data.get("selected_package")
    if not package:
        await state.clear()
        await message.answer("❌ Заказ не найден")
        return
    package["purchase_for"] = "friend"
    package["target_username"] = username
    await state.update_data(selected_package=package)
    await show_stars_payment_options(message, state)


@router.callback_query(F.data.startswith("premium_") & ~F.data.startswith("premium_pay_"))
async def premium_period_selected(callback: CallbackQuery, state: FSMContext):
    months = int(callback.data.split("_")[1])
    price = float(get_premium_prices()[months])
    await state.update_data(selected_package=None, ton_topup_order=None, premium_order={"months": months, "price": price, "payment_method": None, "target_username": None})
    await safe_edit_message(callback, f"👑 Telegram Premium на {months} мес. — {price:.2f} грн\n\nВыберите способ оплаты:", reply_markup=payment_methods_keyboard("premium_pay"))
    await callback.answer()


@router.callback_query(F.data == "balance_topup_start")
async def balance_topup_start_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await start_ton_topup_flow(callback.message, state)


@router.callback_query(F.data == "ton_topup_start")
async def ton_topup_start_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await start_ton_topup_flow(callback.message, state)




@router.message(PaymentStates.waiting_ton_topup_amount)
async def process_ton_topup_amount(message: Message, state: FSMContext):
    if await _handle_waiting_navigation(message, state, "purchases"):
        return
    try:
        ton_amount = float((message.text or "").strip().replace(",", "."))
    except Exception:
        await message.answer("❌ Введите число. Например: 1.5")
        return
    if ton_amount <= 0:
        await message.answer("❌ Количество TON должно быть больше 0")
        return
    pricing = await ton_to_uah_buy_price(ton_amount, markup_percent=0)
    if pricing is None:
        await message.answer("❌ Не удалось получить курс TON. Попробуйте ещё раз через несколько секунд.")
        return
    order = {
        "ton_amount": round(float(pricing["ton_amount"]), 4),
        "base_uah_per_ton": round(float(pricing["base_uah_per_ton"]), 2),
        "base_total_uah": round(float(pricing["base_total_uah"]), 2),
        "uah_per_ton": round(float(pricing["base_uah_per_ton"]), 2),
        "total_uah": round(float(pricing["base_total_uah"]), 2),
        "ton_usdt": round(float(pricing["ton_usdt"]), 6),
        "payment_method": None,
        "fee_percent": 0.0,
    }
    await state.update_data(selected_package=None, premium_order=None, ton_topup_order=order)
    await state.set_state(None)
    await message.answer(
        f"💠 Покупка TON\n\n"
        f"Будет зачислено: {format_stars(order['ton_amount'])} TON\n"
        f"Выберите способ оплаты:",
        reply_markup=payment_methods_keyboard("ton_topup", include_ton_balance=False, include_ton_wallet=True, include_card=True),
    )


@router.callback_query(F.data.startswith("payment_mono"))
async def payment_mono(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    package = data.get("selected_package")
    if not package:
        package = parse_stars_payment_callback(callback.data)
    if not package:
        await callback.answer("❌ Ошибка пакета", show_alert=True)
        return
    await state.update_data(selected_package=package)
    await state.set_state(PaymentStates.waiting_payment_proof)
    target_line = "🙋 Покупка <b>себе</b>" if not package.get("target_username") else f"🎁 Получатель: <b>{package['target_username']}</b>"
    await safe_edit_message(
        callback,
        f"💳 <b>Оплата картой Mono</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"⭐ Звёзд: <b>{package['stars']}</b>\n"
        f"💰 К оплате: <b>{float(package['price']):.2f} грн</b>\n"
        f"{target_line}\n\n"
        f"🏦 Реквизиты: <code>{MONO}</code>\n\n"
        f"📸 <i>После оплаты отправьте скриншот чека сюда</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("payment_ton_balance"))
async def payment_ton_balance(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    package = data.get("selected_package")
    if not package:
        package = parse_stars_payment_callback(callback.data)
    if not package:
        await callback.answer("❌ Ошибка пакета", show_alert=True)
        return
    ton_amount = await uah_to_ton(float(package["price"]))
    if ton_amount is None:
        await callback.answer("Не удалось получить курс TON", show_alert=True)
        return
    user_data = register_user_if_needed(callback.from_user.id, callback.from_user.username)
    if get_numeric_ton_balance(user_data) < ton_amount:
        await callback.answer("Недостаточно TON на балансе", show_alert=True)
        return
    user_data["balance_ton"] = round(get_numeric_ton_balance(user_data) - ton_amount, 4)
    stars_to_add = int(package["stars"])
    target_username = package.get("target_username")
    recipient_id = find_user_id_by_username(target_username) if target_username else callback.from_user.id
    if recipient_id == callback.from_user.id and not target_username:
        user_data["total_stars"] = int(user_data.get("total_stars", 0) or 0) + stars_to_add
        add_star_balance(user_data, stars_to_add)
        reward_referrer_for_purchase(callback.from_user.id, "stars", stars=stars_to_add, bot=callback.bot)
        db.save_data()
        await state.clear()
        await safe_edit_message(
            callback,
            f"✅ <b>Оплачено с TON баланса!</b>\n\n"
            f"⭐ Начислено: <b>{stars_to_add} Stars</b>\n"
            f"💠 Списано: <b>{format_stars(ton_amount)} TON</b>\n"
            f"💎 Баланс Stars: <b>{format_stars(user_data['balance_stars'])} ⭐️</b>",
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # For third-party gifts, route to admin review
    transaction = {
        "id": db.transaction_id_counter,
        "type": "stars",
        "user_id": callback.from_user.id,
        "stars": stars_to_add,
        "amount": float(package["price"]),
        "status": "pending",
        "referral_rewarded": False,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "purchase_for": "friend",
        "target_username": target_username,
        "recipient_user_id": recipient_id,
        "delivered_to_balance": False,
        "payment_method": "ton_balance",
        "source": "bot",
        "ton_debited": ton_amount,
    }
    db.transactions.append(transaction)
    db.transaction_id_counter += 1
    db.save_data()
    await state.clear()
    safe_target = html_lib.escape(f"@{target_username.lstrip('@')}" if target_username else "друга", quote=False)
    await safe_edit_message(
        callback,
        f"⏳ <b>Заказ #{transaction['id']} отправлен на проверку</b>\n\n"
        f"⭐️ Stars: <b>{stars_to_add}</b>\n"
        f"🎁 Получатель: <b>{safe_target}</b>\n"
        f"💠 Списано: <b>{format_stars(ton_amount)} TON</b>\n\n"
        f"<i>Администратор обработает заявку в ближайшее время.</i>",
        parse_mode="HTML"
    )
    try:
        await callback.bot.send_message(
            ADMIN_CHAT_ID,
            f"🆕 <b>Заказ #{transaction['id']} (Оплата с TON баланса)</b>\n\n"
            f"🛒 Товар: <b>Stars</b>\n"
            f"👤 Покупатель: <code>{callback.from_user.id}</code> (@{callback.from_user.username or 'unknown'})\n"
            f"🎁 Получатель: <b>{safe_target}</b>\n"
            f"⭐️ Количество: <b>{stars_to_add}</b>\n"
            f"💠 Списано: <b>{format_stars(ton_amount)} TON</b>\n"
            f"ℹ️ Требуется ручная выдача / подтверждение",
            parse_mode="HTML",
            reply_markup=admin_payment_keyboard(transaction["id"]),
        )
    except Exception:
        pass
    await callback.answer()
    return


@router.callback_query(F.data.startswith("payment_ton_wallet"))
async def payment_ton_wallet(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    package = data.get("selected_package")
    if not package:
        package = parse_stars_payment_callback(callback.data)
    if not package:
        await callback.answer("❌ Ошибка пакета", show_alert=True)
        return
    await state.update_data(selected_package=package)
    ton_amount = await uah_to_ton(float(package["price"]))
    if ton_amount is None:
        await callback.answer("Не удалось получить курс TON", show_alert=True)
        return
    await state.set_state(PaymentStates.waiting_payment_proof)
    safe_target = html_lib.escape(package.get("target_username") or "", quote=False)
    target_line = "🙋 Покупка <b>себе</b>" if not safe_target else f"🎁 Получатель: <b>{safe_target}</b>"
    await safe_edit_message(
        callback,
        f"💠 <b>Оплата на TON кошелёк</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"⭐ Звёзд: <b>{package['stars']}</b>\n"
        f"💰 Стоимость: <b>{float(package['price']):.2f} грн</b>\n"
        f"💠 К оплате: <b>{format_stars(ton_amount)} TON</b>\n"
        f"{target_line}\n\n"
        f"📬 Адрес TON: <code>{TON}</code>\n\n"
        f"📸 <i>После оплаты отправьте скриншот транзакции сюда</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "premium_pay_ton_wallet")
async def premium_pay_ton_wallet(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    premium = data.get("premium_order")
    if not premium:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    ton_amount = await uah_to_ton(float(premium["price"]))
    if ton_amount is None:
        await callback.answer("Не удалось получить курс TON", show_alert=True)
        return
    premium["payment_method"] = "ton_wallet"
    await state.update_data(premium_order=premium)
    text = f"💠 Оплата на TON кошелёк\n\n👑 Telegram Premium на {premium['months']} мес. = {float(premium['price']):.2f} грн\n💠 К оплате: {format_stars(ton_amount)} TON\n💠 TON адрес: {TON}"
    if int(premium["months"]) == 1:
        await state.set_state(PaymentStates.waiting_payment_proof)
        await safe_edit_message(callback, text + "\n\n📩 Пришлите скриншот об оплате.")
    else:
        await state.set_state(PaymentStates.waiting_premium_username)
        await safe_edit_message(callback, text + "\n\n✍️ Отправьте @username человека, которому нужно купить Premium.")
    await callback.answer()


@router.callback_query(F.data == "ton_topup_ton_wallet")
async def ton_topup_ton_wallet(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order = data.get("ton_topup_order")
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    ton_to_pay = float(order.get("ton_amount", 0) or 0)
    order["payment_method"] = "ton_wallet"
    order["fee_percent"] = 0.0
    order["total_uah"] = round(float(order.get("base_total_uah", order.get("total_uah", 0) or 0)), 2)
    await state.update_data(ton_topup_order=order)
    await state.set_state(PaymentStates.waiting_payment_proof)
    await safe_edit_message(
        callback,
        f"💠 Покупка TON\n\nБудет зачислено: {format_stars(order['ton_amount'])} TON\n"
        f"💠 К оплате: {format_stars(ton_to_pay)} TON\n"
        f"💠 TON адрес: {TON}\n\n"
        f"📩 Пришлите скриншот об оплате.",
    )
    await callback.answer()


@router.callback_query(F.data == "premium_pay_mono")
async def premium_pay_mono(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    premium = data.get("premium_order")
    if not premium:
        await callback.answer("❌ Ошибка заказа", show_alert=True)
        return
    premium["payment_method"] = "mono"
    await state.update_data(premium_order=premium)
    if int(premium["months"]) == 1:
        await state.set_state(PaymentStates.waiting_payment_proof)
        await safe_edit_message(callback, f"💳 Оплата картой\n\n👑 Telegram Premium на 1 мес. = {float(premium['price']):.2f} грн\n💳 Реквизиты: {MONO}\n\n📩 Пришлите скриншот об оплате.")
    else:
        await state.set_state(PaymentStates.waiting_premium_username)
        await safe_edit_message(callback, f"💳 Оплата картой\n\n👑 Telegram Premium на {premium['months']} мес. = {float(premium['price']):.2f} грн\n💳 Реквизиты: {MONO}\n\n✍️ Отправьте @username человека, которому нужно купить Premium.")
    await callback.answer()


@router.callback_query(F.data == "premium_pay_ton_balance")
async def premium_pay_ton_balance(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    premium = data.get("premium_order")
    if not premium:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    ton_amount = await uah_to_ton(float(premium["price"]))
    if ton_amount is None:
        await callback.answer("Не удалось получить курс TON", show_alert=True)
        return
    user_data = register_user_if_needed(callback.from_user.id, callback.from_user.username)
    if get_numeric_ton_balance(user_data) < ton_amount:
        await callback.answer("Недостаточно TON на балансе", show_alert=True)
        return
    user_data["balance_ton"] = round(get_numeric_ton_balance(user_data) - ton_amount, 4)
    months = int(premium["months"])
    target_username = premium.get("target_username") or f"@{callback.from_user.username or 'unknown'}"
    transaction = {
        "id": db.transaction_id_counter,
        "type": "premium",
        "user_id": callback.from_user.id,
        "months": months,
        "amount": float(premium["price"]),
        "payment_method": "ton_balance",
        "target_username": target_username,
        "status": "pending",
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "source": "bot",
        "ton_debited": ton_amount,
    }
    db.transactions.append(transaction)
    db.transaction_id_counter += 1
    reward_referrer_for_purchase(callback.from_user.id, "premium", months=months, bot=callback.bot)
    db.save_data()
    await state.clear()
    safe_target = html_lib.escape(target_username, quote=False)
    text = (
        f"✅ <b>Заявка #{transaction['id']} на Telegram Premium ({months} мес.) принята!</b>\n\n"
        f"💠 Списано: <b>{format_stars(ton_amount)} TON</b>\n"
        f"🎯 Получатель: <b>{safe_target}</b>\n\n"
        f"<i>Ожидайте выдачу (обычно до 30 минут).</i>"
    )
    if months == 1 and PREMIUM_SELLER_USERNAME:
        text += f"\n\nСвяжитесь с: {PREMIUM_SELLER_USERNAME}"
    await safe_edit_message(callback, text, parse_mode="HTML")
    try:
        await callback.bot.send_message(
            ADMIN_CHAT_ID,
            f"🆕 <b>Заявка #{transaction['id']}: Telegram Premium {months} мес. (TON баланс)</b>\n\n"
            f"👤 Покупатель: <code>{callback.from_user.id}</code> (@{callback.from_user.username or 'unknown'})\n"
            f"🎯 Получатель: <b>{safe_target}</b>\n"
            f"💠 Списано: <b>{format_stars(ton_amount)} TON</b>",
            parse_mode="HTML",
            reply_markup=admin_payment_keyboard(transaction["id"]),
        )
    except Exception:
        pass
    await callback.answer()


@router.message(PaymentStates.waiting_premium_username)
async def premium_username_received(message: Message, state: FSMContext):
    if await _handle_waiting_navigation(message, state, "premium"):
        return
    username = (message.text or "").strip()
    if not username.startswith("@") or len(username) < 2:
        await message.answer("❌ Отправьте корректный @username")
        return
    data = await state.get_data()
    premium = data.get("premium_order")
    if not premium:
        await state.clear()
        await message.answer("❌ Заказ не найден")
        return
    premium["target_username"] = username
    await state.update_data(premium_order=premium)
    await state.set_state(PaymentStates.waiting_payment_proof)
    await message.answer(f"✅ Username сохранён: {username}\n\n📩 Теперь отправьте сюда скрин оплаты.", reply_markup=back_only_keyboard())


@router.callback_query(F.data == "ton_topup_mono")
async def ton_topup_mono(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order = data.get("ton_topup_order")
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    ton_amount = float(order.get("ton_amount", 0) or 0)
    fee_percent = 10.0 if ton_amount <= 5 else 7.0
    base_uah_per_ton = float(order.get("base_uah_per_ton", order.get("uah_per_ton", 0)) or 0)
    final_uah_per_ton = base_uah_per_ton * (1 + fee_percent / 100)
    final_total_uah = ton_amount * final_uah_per_ton
    order["payment_method"] = "mono"
    order["fee_percent"] = fee_percent
    order["uah_per_ton"] = round(final_uah_per_ton, 2)
    order["total_uah"] = round(final_total_uah, 2)
    await state.update_data(ton_topup_order=order)
    await state.set_state(PaymentStates.waiting_payment_proof)
    await safe_edit_message(
        callback,
        f"💠 Покупка TON\n\n"
        f"Будет зачислено: {format_stars(order['ton_amount'])} TON\n"
        f"💳 К оплате: {float(order['total_uah']):.2f} грн\n"
        f"💳 Реквизиты: {MONO}\n\n"
        f"📩 Пришлите скриншот об оплате.",
    )
    await callback.answer()


@router.callback_query(F.data == "withdraw_start")
async def withdraw_start(callback: CallbackQuery, state: FSMContext):
    user_data = register_user_if_needed(callback.from_user.id, callback.from_user.username)
    balance = get_numeric_balance(user_data)
    pending = get_user_pending_withdraw(callback.from_user.id, "withdraw")
    if pending:
        await callback.answer("⏳ У вас уже есть активная заявка на вывод звёзд.", show_alert=True)
        return
    if balance <= 0:
        await callback.answer("❌ У вас 0 ⭐ на балансе", show_alert=True)
        return
    await state.set_state(PaymentStates.waiting_withdraw_amount)
    await callback.message.answer(
        f"💸 <b>Вывод Stars</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 Ваш баланс: <b>{format_stars(balance)} ⭐️</b>\n\n"
        f"Введите количество звёзд для вывода:\n"
        f"<i>Минимум: 50 | Максимум: 10 000</i>",
        parse_mode="HTML",
        reply_markup=menu_with_back(callback.from_user.id in ADMIN_IDS),
    )
    await callback.answer()


@router.callback_query(F.data == "withdraw_ton_start")
async def withdraw_ton_start(callback: CallbackQuery, state: FSMContext):
    user_data = register_user_if_needed(callback.from_user.id, callback.from_user.username)
    balance = get_numeric_ton_balance(user_data)
    pending = get_user_pending_withdraw(callback.from_user.id, "withdraw_ton")
    if pending:
        await callback.answer("⏳ У вас уже есть активная заявка на вывод TON.", show_alert=True)
        return
    if balance <= 0:
        await callback.answer("❌ У вас 0 TON на балансе", show_alert=True)
        return
    await state.set_state(PaymentStates.waiting_ton_withdraw_amount)
    await callback.message.answer(
        f"💠 <b>Вывод TON</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"💠 Ваш баланс: <b>{format_stars(balance)} TON</b>\n\n"
        f"Введите количество TON для вывода:",
        parse_mode="HTML",
        reply_markup=menu_with_back(callback.from_user.id in ADMIN_IDS),
    )
    await callback.answer()


@router.message(PaymentStates.waiting_withdraw_amount)
async def process_withdraw_amount(message: Message, state: FSMContext):
    if await _handle_waiting_navigation(message, state, "main"):
        return
    user_data = register_user_if_needed(message.from_user.id, message.from_user.username)
    balance = get_numeric_balance(user_data)
    try:
        amount = int((message.text or "").strip())
    except Exception:
        await message.answer("❌ <b>Введите целое число</b>", parse_mode="HTML")
        return
    if amount < 50 or amount > 10000:
        await message.answer(
            "❌ <b>Некорректная сумма</b>\n\n"
            "<i>Сумма вывода должна быть от 50 до 10 000 ⭐️</i>",
            parse_mode="HTML",
        )
        return
    if amount > balance:
        await message.answer(
            f"❌ <b>Недостаточно Stars на балансе</b>\n\n"
            f"Доступно: <b>{format_stars(balance)} ⭐️</b>",
            parse_mode="HTML",
        )
        return
    sub_star_balance(user_data, amount)
    transaction = {
        "type": "withdraw",
        "user_id": message.from_user.id,
        "stars": amount,
        "status": "pending",
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "source": "bot",
        "held_at_creation": True,
    }
    db.add_transaction(transaction)
    db.save_data()
    clean_username = html_lib.escape(message.from_user.username or "unknown", quote=False)
    caption = (
        f"💸 <b>Новая заявка на вывод #{transaction['id']}</b>\n\n"
        f"👤 ID: <code>{message.from_user.id}</code>\n"
        f"👤 @{clean_username}\n"
        f"⭐️ К выводу: <b>{amount}</b>"
    )
    await message.bot.send_message(ADMIN_CHAT_ID, caption, parse_mode="HTML", reply_markup=admin_withdraw_keyboard(transaction["id"]))
    await state.clear()
    await message.answer(
        "✅ <b>Заявка на вывод отправлена!</b>\n\n"
        "Сумма заблокирована до подтверждения администратора.\n"
        "<i>Обычно это занимает несколько минут</i>",
        parse_mode="HTML",
    )


@router.message(PaymentStates.waiting_ton_withdraw_amount)
async def process_ton_withdraw_amount(message: Message, state: FSMContext):
    if await _handle_waiting_navigation(message, state, "main"):
        return
    user_data = register_user_if_needed(message.from_user.id, message.from_user.username)
    balance = get_numeric_ton_balance(user_data)
    try:
        amount = float((message.text or "").strip().replace(",", "."))
    except Exception:
        await message.answer("❌ <b>Введите число</b>", parse_mode="HTML")
        return
    if amount <= 0:
        await message.answer("❌ <b>Сумма должна быть больше 0</b>", parse_mode="HTML")
        return
    if amount > balance:
        await message.answer(
            f"❌ <b>Недостаточно TON на балансе</b>\n\n"
            f"Доступно: <b>{format_stars(balance)} TON</b>",
            parse_mode="HTML",
        )
        return
    sub_ton_balance(user_data, amount)
    transaction = {
        "type": "withdraw_ton",
        "user_id": message.from_user.id,
        "ton_amount": amount,
        "status": "pending",
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "source": "bot",
        "held_at_creation": True,
    }
    db.add_transaction(transaction)
    db.save_data()
    clean_username = html_lib.escape(message.from_user.username or "unknown", quote=False)
    caption = (
        f"💠 <b>Новая заявка на вывод TON #{transaction['id']}</b>\n\n"
        f"👤 ID: <code>{message.from_user.id}</code>\n"
        f"👤 @{clean_username}\n"
        f"💠 К выводу: <b>{format_stars(amount)} TON</b>"
    )
    await message.bot.send_message(ADMIN_CHAT_ID, caption, parse_mode="HTML", reply_markup=admin_withdraw_keyboard(transaction["id"]))
    await state.clear()
    await message.answer(
        "✅ <b>Заявка на вывод TON отправлена!</b>\n\n"
        "Сумма заблокирована до подтверждения администратора.\n"
        "<i>Обычно это занимает несколько минут</i>",
        parse_mode="HTML",
    )


@router.message(PaymentStates.waiting_payment_proof, F.text)
async def waiting_payment_proof_text(message: Message, state: FSMContext):
    data = await state.get_data()
    back_target = "premium"
    if data.get("ton_topup_order"):
        back_target = "ton"
    elif data.get("selected_package"):
        back_target = "stars"
    if await _handle_waiting_navigation(message, state, back_target):
        return
    await message.answer(
        "📸 <b>Отправьте скриншот оплаты</b>\n\n"
        "<i>Или нажмите ⬅️ Назад для отмены</i>",
        parse_mode="HTML",
        reply_markup=back_only_keyboard(),
    )


@router.message(F.photo)
async def handle_payment_proof(message: Message, state: FSMContext):
    data = await state.get_data()
    package = data.get("selected_package")
    premium = data.get("premium_order")
    ton_topup = data.get("ton_topup_order")
    if not package and not premium and not ton_topup:
        return
    sender_name = html_lib.escape(message.from_user.username or "unknown", quote=False)
    if package:
        stars_amount = int(package["stars"])
        if stars_amount < 50 or stars_amount > 10000:
            await message.answer("❌ <b>Некорректный пакет Stars</b>", parse_mode="HTML")
            return
        official_price = float(get_price(stars_amount))
        target_username = package.get("target_username")
        recipient_user_id = find_user_id_by_username(target_username) if target_username else message.from_user.id
        purchase_for = "friend" if target_username else "self"
        transaction = {
            "type": "stars",
            "user_id": message.from_user.id,
            "stars": stars_amount,
            "amount": official_price,
            "status": "pending",
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "purchase_for": purchase_for,
            "target_username": target_username,
            "recipient_user_id": recipient_user_id,
            "delivered_to_balance": False,
            "source": "bot",
        }
        transaction = db.add_transaction(transaction)
        safe_target = html_lib.escape(target_username or ("@" + (message.from_user.username or "unknown")), quote=False)
        caption = (
            f"🆕 <b>Новая заявка на оплату #{transaction['id']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"🛒 Товар: <b>Stars ⭐</b>\n"
            f"👤 Покупатель: <code>{message.from_user.id}</code> (@{sender_name})\n"
            f"🎁 Получатель: <b>{safe_target}</b>\n"
            f"⭐ Количество: <b>{stars_amount} ⭐️</b>\n"
            f"💰 Сумма: <b>{official_price:.2f} грн</b>"
        )
        if target_username and not recipient_user_id:
            caption += "\n\n<i>ℹ️ Получатель не найден в базе — требуется ручная выдача</i>"
        success_text = (
            "✅ <b>Чек отправлен на проверку!</b>\n\n"
            "После подтверждения заказ будет обработан администратором.\n"
            "<i>Обычно это занимает несколько минут</i>"
        ) if target_username else (
            "✅ <b>Чек отправлен на проверку!</b>\n\n"
            "После подтверждения звёзды будут автоматически зачислены на ваш баланс.\n"
            "<i>Обычно это занимает несколько минут</i>"
        )
    elif ton_topup:
        payment_method = ton_topup.get("payment_method") or "mono"
        ton_amount = float(ton_topup.get("ton_amount", 0) or 0)
        if ton_amount <= 0:
            await message.answer("❌ <b>Некорректная сумма TON</b>", parse_mode="HTML")
            return
        amount_uah = float(ton_topup.get("total_uah", 0) or 0)
        transaction = {
            "type": "ton_topup",
            "user_id": message.from_user.id,
            "ton_amount": ton_amount,
            "amount": amount_uah,
            "payment_method": payment_method,
            "fee_percent": float(ton_topup.get("fee_percent", 0) or 0),
            "status": "pending",
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "source": "bot",
        }
        transaction = db.add_transaction(transaction)
        if payment_method == "ton_wallet":
            caption = (
                f"🆕 <b>Новая заявка на пополнение TON #{transaction['id']}</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 Пользователь: <code>{message.from_user.id}</code> (@{sender_name})\n"
                f"💠 К зачислению: <b>{format_stars(ton_amount)} TON</b>\n"
                f"📬 Метод: <b>TON кошелёк</b>"
            )
        else:
            caption = (
                f"🆕 <b>Новая заявка на пополнение TON #{transaction['id']}</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 Пользователь: <code>{message.from_user.id}</code> (@{sender_name})\n"
                f"💠 К зачислению: <b>{format_stars(ton_amount)} TON</b>\n"
                f"💰 К оплате: <b>{amount_uah:.2f} грн</b>\n"
                f"💳 Метод: <b>Mono (карта)</b>"
            )
        success_text = (
            "✅ <b>Чек отправлен на проверку!</b>\n\n"
            "После подтверждения TON будут зачислены на ваш баланс.\n"
            "<i>Обычно это занимает несколько минут</i>"
        )
    else:
        months_val = int(premium.get("months", 0) or 0)
        prem_prices = get_premium_prices()
        if months_val not in prem_prices:
            await message.answer("❌ <b>Некорректный срок Premium</b>", parse_mode="HTML")
            return
        official_prem_price = float(prem_prices[months_val])
        target_username = premium.get("target_username")
        transaction = {
            "type": "premium",
            "user_id": message.from_user.id,
            "months": months_val,
            "amount": official_prem_price,
            "payment_method": premium.get("payment_method"),
            "target_username": target_username,
            "status": "pending",
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "source": "bot",
        }
        transaction = db.add_transaction(transaction)
        who_for = html_lib.escape(target_username or "Себе", quote=False)
        caption = (
            f"🆕 <b>Новая заявка на Premium #{transaction['id']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 Покупатель: <code>{message.from_user.id}</code> (@{sender_name})\n"
            f"👑 Срок: <b>{months_val} мес.</b>\n"
            f"🎯 Получатель: <b>{who_for}</b>\n"
            f"💰 Сумма: <b>{official_prem_price:.2f} грн</b>"
        )
        success_text = (
            "✅ <b>Чек отправлен на проверку!</b>\n\n"
            "Ожидайте, выдача Telegram Premium обычно занимает до 30 минут.\n"
            "<i>Мы пришлём уведомление сразу после активации</i>"
        )
    transaction['proof_file_id'] = message.photo[-1].file_id
    db.save_data()
    await message.bot.send_photo(ADMIN_CHAT_ID, message.photo[-1].file_id, caption=caption, parse_mode="HTML", reply_markup=admin_payment_keyboard(transaction["id"]))
    await message.answer(success_text, parse_mode="HTML")
    await state.clear()


@router.callback_query(F.data.startswith("confirm_"))
async def confirm_transaction(callback: CallbackQuery):
    db.refresh()
    is_admin = _is_admin_callback_actor(callback)
    if not is_admin:
        await callback.answer("Только администратор может подтвердить оплату", show_alert=True)
        return
    try:
        transaction_id = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("Неверный идентификатор транзакции", show_alert=True)
        return
    trans = next((t for t in db.transactions if int(t.get("id", 0)) == transaction_id), None)
    if not trans:
        await callback.answer("Не найдено", show_alert=True)
        return
    if trans.get("status") in {"confirmed", "rejected"}:
        await callback.answer(f"Уже обработано (статус: {trans.get('status')})", show_alert=True)
        return
    trans["status"] = "confirmed"
    notify_user_text: str | None = None
    notify_user_markup = None
    notify_recipient_user_id: int | None = None
    notify_recipient_text: str | None = None
    try:
        user_data = register_user_if_needed(trans["user_id"])
        if trans.get("type") == "stars":
            stars_to_add = int(trans.get("stars", 0) or 0)
            target_username = trans.get("target_username")
            recipient_user_id = trans.get("recipient_user_id")
            if not target_username:
                add_star_balance(user_data, stars_to_add)
                trans["delivered_to_balance"] = True
                if not trans.get("referral_rewarded"):
                    trans["referral_rewarded"] = True
                    reward_referrer_for_purchase(trans["user_id"], "stars", stars=stars_to_add, bot=callback.bot)
                db.save_data()
                notify_user_text = (
                    f"✅ <b>Оплата подтверждена!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n\n"
                    f"⭐ Начислено: <b>{stars_to_add} Stars</b>\n"
                    f"💎 Ваш баланс: <b>{format_stars(user_data['balance_stars'])} ⭐️</b>\n\n"
                    f"<i>Спасибо за покупку в Freaking Stars!</i>"
                )
                notify_user_markup = withdraw_keyboard()
            elif recipient_user_id:
                recipient_data = register_user_if_needed(int(recipient_user_id))
                add_star_balance(recipient_data, stars_to_add)
                trans["delivered_to_balance"] = True
                if not trans.get("referral_rewarded"):
                    trans["referral_rewarded"] = True
                    reward_referrer_for_purchase(trans["user_id"], "stars", stars=stars_to_add, bot=callback.bot)
                db.save_data()
                notify_user_text = (
                    f"✅ <b>Оплата подтверждена!</b>\n\n"
                    f"🎁 Для <b>{target_username}</b> успешно начислено <b>{stars_to_add} ⭐️</b>"
                )
                notify_recipient_user_id = int(recipient_user_id)
                notify_recipient_text = (
                    f"🎁 <b>Вам подарок!</b>\n\n"
                    f"Вам купили <b>{stars_to_add} Stars ⭐️</b>\n"
                    f"Звёзды уже на вашем балансе."
                )
            else:
                trans["delivered_to_balance"] = False
                if not trans.get("referral_rewarded"):
                    trans["referral_rewarded"] = True
                    reward_referrer_for_purchase(trans["user_id"], "stars", stars=stars_to_add, bot=callback.bot)
                db.save_data()
                notify_user_text = (
                    f"✅ <b>Оплата подтверждена!</b>\n\n"
                    f"🎁 Заказ для <b>{target_username}</b> подтверждён администратором.\n"
                    f"<i>Подарок будет отправлен в ближайшее время вручную.</i>"
                )
        elif trans.get("type") == "ton_topup":
            user_data["balance_ton"] = get_numeric_ton_balance(user_data) + float(trans.get("ton_amount", 0) or 0)
            db.save_data()
            notify_user_text = (
                f"✅ <b>Оплата подтверждена!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"💠 Начислено: <b>{format_stars(trans.get('ton_amount', 0))} TON</b>\n"
                f"💎 Новый баланс TON: <b>{format_stars(user_data['balance_ton'])} TON</b>"
            )
        else:
            months = int(trans.get("months", 0) or 0)
            if not trans.get("referral_rewarded"):
                trans["referral_rewarded"] = True
                reward_referrer_for_purchase(trans["user_id"], "premium", months=months, bot=callback.bot)
            db.save_data()
            if months == 1:
                notify_user_text = (
                    f"✅ <b>Оплата подтверждена!</b>\n\n"
                    f"Для активации Telegram Premium на 1 месяц свяжитесь с нашим продавцом:\n"
                    f"👉 @{PREMIUM_SELLER_USERNAME.lstrip('@')}"
                )
            else:
                notify_user_text = (
                    f"✅ <b>Оплата подтверждена!</b>\n\n"
                    f"👑 Telegram Premium на <b>{months} мес.</b> отправлен на активацию.\n"
                    f"<i>Обычно выдача занимает до 30 минут.</i>"
                )
    except Exception:
        pass
    db.save_data()

    if notify_user_text:
        try:
            await callback.bot.send_message(trans["user_id"], notify_user_text, parse_mode="HTML", reply_markup=notify_user_markup)
        except Exception:
            pass
    if notify_recipient_user_id and notify_recipient_text:
        try:
            await callback.bot.send_message(notify_recipient_user_id, notify_recipient_text, parse_mode="HTML")
        except Exception:
            pass
    
    source_header = ""
    if trans.get("source") == "app":
        source_header = "📱 Заказ через Web App\n"
    elif trans.get("source") == "bot":
        source_header = "🤖 Заказ через Telegram Bot\n"

    async def _edit_admin_callback_message(text: str):
        if not callback.message:
            return
        try:
            if callback.message.caption is not None:
                await callback.message.edit_caption(caption=text, reply_markup=None)
            elif callback.message.text is not None:
                await callback.message.edit_text(text, reply_markup=None)
        except Exception:
            try:
                if callback.message.text is not None:
                    await callback.message.edit_text(text, reply_markup=None)
                elif callback.message.caption is not None:
                    await callback.message.edit_caption(caption=text, reply_markup=None)
            except Exception:
                pass

    if callback.message:
        caption = callback.message.caption or callback.message.text or ""
        if source_header and source_header not in caption:
            caption = source_header + caption
        await _edit_admin_callback_message(caption + "\n\n✅ ОПЛАТА ПОДТВЕРЖДЕНА")
    await callback.answer()


@router.callback_query(F.data.startswith("reject_"))
async def reject_transaction(callback: CallbackQuery):
    db.refresh()
    if not _is_admin_callback_actor(callback):
        await callback.answer("Только администратор может отклонить оплату", show_alert=True)
        return
    try:
        transaction_id = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("Неверный идентификатор транзакции", show_alert=True)
        return
    trans = next((t for t in db.transactions if int(t.get("id", 0)) == transaction_id), None)
    if not trans:
        await callback.answer("Не найдено", show_alert=True)
        return
    if trans.get("status") in {"confirmed", "rejected"}:
        await callback.answer(f"Уже обработано (статус: {trans.get('status')})", show_alert=True)
        return
    trans["status"] = "rejected"
    user_id = trans.get("user_id")
    user_data = db.users.get(str(user_id)) if user_id else None
    ton_refunded = 0.0
    if isinstance(user_data, dict):
        ton_to_refund = float(trans.get("ton_debited") or (trans.get("ton_amount") if trans.get("held_at_creation") else 0) or 0)
        if ton_to_refund > 0:
            add_ton_balance(user_data, ton_to_refund)
            trans["ton_debited"] = 0
            trans["held_at_creation"] = False
            ton_refunded = ton_to_refund
    db.save_data()
    try:
        reject_msg = "❌ <b>Оплата отклонена</b>\n\n"
        if ton_refunded > 0:
            reject_msg += f"Средства возвращены на ваш TON баланс (+{format_stars(ton_refunded)} TON).\n\n"
        reject_msg += "Если вы считаете, что произошла ошибка — обратитесь в нашу поддержку."
        await callback.bot.send_message(
            trans["user_id"],
            reject_msg,
            parse_mode="HTML"
        )
    except Exception:
        pass
    async def _edit_admin_callback_message(text: str):
        if not callback.message:
            return
        try:
            if callback.message.caption is not None:
                await callback.message.edit_caption(caption=text, reply_markup=None)
            elif callback.message.text is not None:
                await callback.message.edit_text(text, reply_markup=None)
        except Exception:
            try:
                if callback.message.text is not None:
                    await callback.message.edit_text(text, reply_markup=None)
                elif callback.message.caption is not None:
                    await callback.message.edit_caption(caption=text, reply_markup=None)
            except Exception:
                pass

    if callback.message:
        text = callback.message.caption if callback.message.caption is not None else callback.message.text or ""
        await _edit_admin_callback_message(text + "\n\n❌ ОПЛАТА ОТКЛОНЕНА")
    await callback.answer()


@router.callback_query(F.data.startswith("withdraw_confirm_"))
async def confirm_withdraw(callback: CallbackQuery):
    db.refresh()
    if not _is_admin_callback_actor(callback):
        await callback.answer("Только администратор может подтвердить вывод", show_alert=True)
        return
    try:
        transaction_id = int(callback.data.split("_")[-1])
    except (IndexError, ValueError):
        await callback.answer("Неверный идентификатор транзакции", show_alert=True)
        return
    trans = next((t for t in db.transactions if int(t.get("id", 0)) == transaction_id and t.get("type") in {"withdraw", "withdraw_ton", "gift_withdraw"}), None)
    if not trans:
        await callback.answer("Не найдено", show_alert=True)
        return
    if trans.get("status") in {"confirmed", "rejected"}:
        await callback.answer("Уже обработано", show_alert=True)
        return
    user_data = db.users.get(str(trans["user_id"]))
    if not user_data:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    if trans.get("type") == "withdraw_ton":
        amount = float(trans.get("ton_amount", 0) or 0)
        if not trans.get("held_at_creation"):
            if amount > get_numeric_ton_balance(user_data):
                await callback.answer("Недостаточно TON у пользователя", show_alert=True)
                return
            sub_ton_balance(user_data, amount)
        msg = (
            f"✅ <b>Заявка на вывод подтверждена!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"💠 Выведено: <b>{format_stars(amount)} TON</b>\n"
            f"💎 Остаток баланса: <b>{format_stars(user_data['balance_ton'])} TON</b>"
        )
    elif trans.get("type") == "gift_withdraw":
        gift_id = str(trans.get("gift_id") or "").strip()
        if not trans.get("held_at_creation"):
            inventory = user_data.setdefault("miniapp_inventory", [])
            if isinstance(inventory, list):
                user_data["miniapp_inventory"] = [item for item in inventory if str(item.get("id") or "") != gift_id]
        msg = (
            f"✅ <b>Заявка на вывод подарка подтверждена!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"🎁 Подарок: <b>{html_lib.escape(str(trans.get('gift_label') or 'Подарок'), quote=False)}</b>\n"
            f"⭐ Оценка: <b>{trans.get('stars_value', 0)} Stars</b>"
        )
    else:
        amount = int(trans.get("stars", 0) or 0)
        if not trans.get("held_at_creation"):
            if amount > get_numeric_balance(user_data):
                await callback.answer("Недостаточно баланса у пользователя", show_alert=True)
                return
            sub_star_balance(user_data, amount)
        msg = (
            f"✅ <b>Заявка на вывод подтверждена!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"⭐ Выведено: <b>{amount} Stars</b>\n"
            f"💎 Остаток баланса: <b>{format_stars(user_data['balance_stars'])} ⭐️</b>"
        )
    trans["status"] = "confirmed"
    db.save_data()
    try:
        await callback.bot.send_message(trans["user_id"], msg, parse_mode="HTML")
    except Exception:
        pass
    if callback.message and callback.message.text:
        await callback.message.edit_text(callback.message.text + "\n\n✅ ВЫВОД ПОДТВЕРЖДЕН")
    await callback.answer()


@router.callback_query(F.data.startswith("withdraw_reject_"))
async def reject_withdraw(callback: CallbackQuery):
    db.refresh()
    if not _is_admin_callback_actor(callback):
        await callback.answer("Только администратор может отклонить вывод", show_alert=True)
        return
    try:
        transaction_id = int(callback.data.split("_")[-1])
    except (IndexError, ValueError):
        await callback.answer("Неверный идентификатор транзакции", show_alert=True)
        return
    trans = next((t for t in db.transactions if int(t.get("id", 0)) == transaction_id and t.get("type") in {"withdraw", "withdraw_ton", "gift_withdraw"}), None)
    if not trans:
        await callback.answer("Не найдено", show_alert=True)
        return
    if trans.get("status") in {"confirmed", "rejected"}:
        await callback.answer("Уже обработано", show_alert=True)
        return

    user_data = db.users.get(str(trans.get("user_id")))
    if isinstance(user_data, dict) and trans.get("held_at_creation"):
        if trans.get("type") == "withdraw_ton":
            add_ton_balance(user_data, float(trans.get("ton_amount", 0) or 0))
        elif trans.get("type") == "withdraw":
            add_star_balance(user_data, float(trans.get("stars", 0) or 0))
        elif trans.get("type") == "gift_withdraw":
            gift_data = trans.get("gift_data")
            if isinstance(gift_data, dict):
                user_data.setdefault("miniapp_inventory", []).insert(0, gift_data)

    trans["status"] = "rejected"
    db.save_data()
    try:
        await callback.bot.send_message(
            trans["user_id"],
            "❌ <b>Заявка на вывод отклонена</b>\n\n"
            "Средства возвращены на ваш баланс. По вопросам обратитесь в поддержку.",
            parse_mode="HTML"
        )
    except Exception:
        pass
    if callback.message and callback.message.text:
        await callback.message.edit_text(callback.message.text + "\n\n❌ ВЫВОД ОТКЛОНЕН")
    await callback.answer()