from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_IDS
from keyboards.reply import main_menu, menu_with_back, purchases_menu, support_category_menu
from utils.pricing import get_star_rates

router = Router()


class CalculatorStates(StatesGroup):
    waiting_for_stars = State()
    waiting_for_amount = State()


MIN_STARS = 50
MAX_STARS = 10000

def get_calculator_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ → грн", callback_data="calc_stars_to_uah")],
            [InlineKeyboardButton(text="грн → ⭐", callback_data="calc_uah_to_stars")],
        ]
    )


def get_star_rate(stars: int) -> float:
    for min_stars, max_stars, rate in get_star_rates():
        if min_stars <= stars <= max_stars:
            return float(rate)
    raise ValueError(f"Количество звёзд должно быть от {MIN_STARS} до {MAX_STARS}")


def get_price_per_star(stars: int) -> float:
    return get_star_rate(stars)


def calculate_price_from_stars(stars: int) -> float:
    rate = get_star_rate(stars)
    return round(stars * rate, 2)


def get_price(stars: int) -> float:
    return calculate_price_from_stars(stars)




async def _handle_waiting_navigation(message: Message, state: FSMContext) -> bool:
    text = (message.text or '').strip()
    if not text:
        return False

    if text == "⬅️ Назад":
        await state.clear()
        await message.answer("🛍️ Покупки\n\nВыберите, что хотите открыть:", reply_markup=purchases_menu(message.from_user.id in ADMIN_IDS))
        return True

    if text == "🛍️ Покупки":
        await state.clear()
        await message.answer("🛍️ Покупки\n\nВыберите, что хотите открыть:", reply_markup=purchases_menu(message.from_user.id in ADMIN_IDS))
        return True
    if text == "🆘 Поддержка":
        await state.clear()
        await message.answer("🆘 Раздел поддержки. Выберите действие:", reply_markup=support_category_menu(message.from_user.id in ADMIN_IDS))
        return True
    if text == "💰 Купить Stars":
        await state.clear()
        from handlers.payments import buy_stars
        await buy_stars(message)
        return True
    if text == "👑 Купить Premium":
        await state.clear()
        from handlers.payments import buy_premium
        await buy_premium(message)
        return True
    if text == "📣 Отзывы":
        await state.clear()
        from handlers.reviews import show_reviews_menu
        await show_reviews_menu(message)
        return True
    if text == "🧮 Посчитать":
        await state.clear()
        await show_calculator_menu(message, state)
        return True
    if text == "💡 Предложения":
        await state.clear()
        from handlers.support import suggestion_menu
        await suggestion_menu(message, state)
        return True
    if text == "🛠️ Поддержка":
        await state.clear()
        from handlers.support import support_menu
        await support_menu(message)
        return True
    if text == "🎮 Игры":
        await state.clear()
        from handlers.user import games_redirect_handler
        await games_redirect_handler(message)
        return True
    if text == "👥 Рефералы":
        await state.clear()
        from handlers.user import referrals_message_handler
        await referrals_message_handler(message)
        return True
    if text == "🎁 Промокод":
        await state.clear()
        from handlers.user import PromoStates
        await state.set_state(PromoStates.waiting_promo_code)
        await message.answer("🎁 Введите кодовое слово промокода", reply_markup=menu_with_back(message.from_user.id in ADMIN_IDS))
        return True
    if text == "👤 Профиль":
        await state.clear()
        from handlers.admin import show_profile
        await show_profile(message)
        return True
    if text == "⚙️ Админ-панель" and message.from_user.id in ADMIN_IDS:
        await state.clear()
        from handlers.admin import admin_panel
        await admin_panel(message)
        return True

    return False


def calculate_stars_from_amount(amount: float) -> int:
    best_stars = MIN_STARS

    for stars in range(MIN_STARS, MAX_STARS + 1):
        price = calculate_price_from_stars(stars)
        if price <= amount:
            best_stars = stars
        else:
            break

    return best_stars


@router.message(F.text == "🧮 Посчитать")
async def open_calculator_from_message(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🧮 <b>Калькулятор стоимости</b>\n\n"
        "Рассчитайте цену звёзд до оформления заказа:\n\n"
        "⭐ → грн — сколько стоит N звёзд\n"
        "грн → ⭐ — сколько звёзд за сумму\n\n"
        "<i>Актуальный курс применяется автоматически</i>",
        parse_mode="HTML",
        reply_markup=get_calculator_keyboard(),
    )


@router.callback_query(F.data == "open_calculator")
async def open_calculator_from_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "🧮 <b>Калькулятор стоимости</b>\n\n"
        "Рассчитайте цену звёзд до оформления заказа:\n\n"
        "⭐ → грн — сколько стоит N звёзд\n"
        "грн → ⭐ — сколько звёзд за сумму\n\n"
        "<i>Актуальный курс применяется автоматически</i>",
        parse_mode="HTML",
        reply_markup=get_calculator_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "calc_stars_to_uah")
async def calculator_stars_to_uah(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CalculatorStates.waiting_for_stars)
    await callback.message.answer(
        f"⭐ <b>Расчёт: Звёзды → Гривны</b>\n\n"
        f"Введите количество звёзд от {MIN_STARS} до {MAX_STARS}:\n\n"
        f"<i>Например: 100 или 500</i>",
        parse_mode="HTML",
        reply_markup=menu_with_back(callback.from_user.id in ADMIN_IDS),
    )
    await callback.answer()


@router.callback_query(F.data == "calc_uah_to_stars")
async def calculator_uah_to_stars(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CalculatorStates.waiting_for_amount)
    await callback.message.answer(
        "💰 <b>Расчёт: Гривны → Звёзды</b>\n\n"
        "Введите сумму в гривнах:\n\n"
        "<i>Например: 73 или 200.50</i>",
        parse_mode="HTML",
        reply_markup=menu_with_back(callback.from_user.id in ADMIN_IDS),
    )
    await callback.answer()


@router.message(CalculatorStates.waiting_for_stars)
async def process_stars_to_uah(message: Message, state: FSMContext):
    if await _handle_waiting_navigation(message, state):
        return
    text = (message.text or "").replace(" ", "").replace(",", ".")

    if not text.isdigit():
        await message.answer(
            "❌ <b>Введите целое число</b>\n\n"
            "<i>Например: 100 или 500</i>",
            parse_mode="HTML",
        )
        return

    stars = int(text)

    if stars < MIN_STARS or stars > MAX_STARS:
        await message.answer(
            f"❌ <b>Некорректное количество</b>\n\n"
            f"<i>Введите от {MIN_STARS} до {MAX_STARS} звёзд</i>",
            parse_mode="HTML",
        )
        return

    try:
        rate = get_star_rate(stars)
        price = calculate_price_from_stars(stars)
    except ValueError as e:
        await message.answer(f"❌ <b>Ошибка:</b> {e}", parse_mode="HTML")
        return

    await state.clear()

    await message.answer(
        f"✅ <b>Результат расчёта</b>\n\n"
        f"⭐ <b>{stars} Stars</b> = <b>{price:.2f} грн</b>\n"
        f"💱 Курс: <b>{rate:.3f} грн</b> за ⭐",
        parse_mode="HTML",
    )

    await message.answer(
        "🧮 <b>Калькулятор стоимости</b>\n\n"
        "Рассчитайте цену звёзд до оформления заказа:\n\n"
        "<i>Выберите направление расчёта</i>",
        parse_mode="HTML",
        reply_markup=get_calculator_keyboard(),
    )


@router.message(CalculatorStates.waiting_for_amount)
async def process_uah_to_stars(message: Message, state: FSMContext):
    if await _handle_waiting_navigation(message, state):
        return
    raw_text = (message.text or "").replace(" ", "").replace(",", ".")

    try:
        amount = float(raw_text)
    except ValueError:
        await message.answer(
            "❌ <b>Некорректная сумма</b>\n\n"
            "<i>Введите число, например: 73 или 73.50</i>",
            parse_mode="HTML",
        )
        return

    if amount <= 0:
        await message.answer(
            "❌ <b>Сумма должна быть больше нуля</b>",
            parse_mode="HTML",
        )
        return

    min_price = calculate_price_from_stars(MIN_STARS)
    if amount < min_price:
        await message.answer(
            f"❌ <b>Сумма слишком маленькая</b>\n\n"
            f"Минимум: <b>{min_price:.2f} грн</b> (это {MIN_STARS} ⭐)",
            parse_mode="HTML",
        )
        return

    stars = calculate_stars_from_amount(amount)
    price = calculate_price_from_stars(stars)
    rate = get_star_rate(stars)

    await state.clear()

    await message.answer(
        f"✅ <b>Результат расчёта</b>\n\n"
        f"💰 <b>{amount:.2f} грн</b> ≈ <b>{stars} ⭐</b>\n"
        f"📌 Точная стоимость: <b>{price:.2f} грн</b>\n"
        f"💱 Курс: <b>{rate:.3f} грн</b> за ⭐",
        parse_mode="HTML",
    )

async def show_calculator_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🧮 <b>Калькулятор стоимости</b>\n\n"
        "<i>Выберите направление расчёта</i>",
        parse_mode="HTML",
        reply_markup=get_calculator_keyboard(),
    )