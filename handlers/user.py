from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from config import ADMIN_IDS, MONO, WEBAPP_URL, get_current_webapp_url
from database import db
from handlers.admin import admin_panel, show_profile
from handlers.calculator import show_calculator_menu
from handlers.payments import buy_stars, buy_premium, start_ton_topup_flow
from handlers.reviews import show_reviews_menu
from handlers.support import support_menu, suggestion_menu, SupportStates
from keyboards.reply import main_menu, menu_with_back, purchases_menu, support_category_menu
from utils.helpers import add_star_balance, format_stars, get_numeric_balance, register_user_if_needed
from utils.referrals import bind_referral, get_user_referral_summary
from utils.subscription import get_subscription_status, subscription_keyboard
from handlers.miniapp import build_open_app_keyboard

router = Router()


class PromoStates(StatesGroup):
    waiting_promo_code = State()


def _normalize_promocode(value: str) -> str:
    return (value or "").strip().upper()


def _build_referrals_view(summary: dict) -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "👥 <b>Реферальная программа</b>\n\n"
        "Приглашайте друзей в Freaking Stars и зарабатывайте ⭐️ звёзды с каждой их покупки!\n\n"
        "💰 <b>Награды за покупки рефералов:</b>\n"
        "• ⭐️ <b>5%</b> от любой покупки Stars\n"
        "• 👑 <b>За покупку Telegram Premium:</b>\n"
        "  — 1 месяц: <b>+15 ⭐️</b>\n"
        "  — 3 месяца: <b>+25 ⭐️</b>\n"
        "  — 6 месяцев: <b>+30 ⭐️</b>\n"
        "  — 12 месяцев: <b>+60 ⭐️</b>\n\n"
        "📊 <b>Ваша статистика:</b>\n"
        f"• Приглашено друзей: <b>{summary['referral_count']}</b>\n"
        f"• Заработано звёзд: <b>{format_stars(summary['referral_earnings_stars'])} ⭐️</b>\n\n"
        "🔗 <b>Ваша реферальная ссылка:</b>\n"
        f"<code>{summary['invite_link']}</code>"
    )
    inline_rows = [
        [
            InlineKeyboardButton(
                text="🚀 Пригласить друга",
                url=summary["share_link"],
            )
        ]
    ]
    current_webapp = get_current_webapp_url()
    if current_webapp:
        inline_rows.append([
            InlineKeyboardButton(
                text="📱 Открыть Mini App",
                web_app=WebAppInfo(url=current_webapp),
            )
        ])
    return text, InlineKeyboardMarkup(inline_keyboard=inline_rows)


@router.message(Command("start"))
async def start(message: Message):
    user = message.from_user
    register_user_if_needed(user.id, user.username)

    parts = (message.text or '').split(maxsplit=1)
    start_arg = parts[1].strip() if len(parts) > 1 else ''

    ref_bound = False
    if start_arg.startswith('ref_'):
        try:
            referrer_id = int(start_arg[4:])
            ref_bound = bind_referral(user.id, referrer_id, user.username, message.bot)
        except Exception:
            pass

    missing = await get_subscription_status(message.bot, user.id, user.username)
    if missing:
        await message.answer(
            "🔒 Для использования бота подпишитесь на обязательные каналы, затем нажмите кнопку проверки.",
            reply_markup=subscription_keyboard(),
        )
        return

    if start_arg.startswith('dice_'):
        await message.answer(
            "🎮 <b>Все игры перенесены в наше веб-приложение!</b>\n\n"
            "Откройте Mini App, чтобы сыграть:",
            parse_mode="HTML",
            reply_markup=build_open_app_keyboard(),
        )
        return

    if ref_bound:
        welcome_text = (
            "🌟 <b>Добро пожаловать в Freaking Stars!</b>\n\n"
            "✅ Вы успешно зарегистрировались по реферальной ссылке — "
            "ваш пригласитель уже получил бонус!\n\n"
            "<i>Исследуйте магазин, играйте в игры и зарабатывайте ⭐️</i>"
        )
    else:
        welcome_text = (
            "🌟 <b>Добро пожаловать в Freaking Stars!</b>\n\n"
            "⭐ Покупайте звёзды и Premium\n"
            "🎮 Играйте в игры и открывайте кейсы\n"
            "👥 Приглашайте друзей и зарабатывайте\n\n"
            "<i>Выберите раздел в меню ниже</i>"
        )

    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=main_menu(user.id in ADMIN_IDS),
    )
    await message.answer(
        "🚀 <b>Открыть Mini App</b>\n<i>Полный магазин и игры в одном приложении</i>",
        parse_mode="HTML",
        reply_markup=build_open_app_keyboard(),
    )


@router.callback_query(F.data == "check_subscriptions")
async def check_subscriptions(callback: CallbackQuery):
    user = callback.from_user
    missing = await get_subscription_status(callback.bot, user.id, user.username)
    if missing:
        await callback.message.answer(
            "❌ <b>Подписка не подтверждена</b>\n\n"
            "Подпишитесь на все обязательные каналы и попробуйте снова.",
            parse_mode="HTML",
            reply_markup=subscription_keyboard(),
        )
    else:
        await callback.message.answer(
            "✅ <b>Подписка подтверждена!</b>\n\n"
            "<i>Добро пожаловать в Freaking Stars</i> 🌟",
            parse_mode="HTML",
            reply_markup=main_menu(user.id in ADMIN_IDS),
        )
    await callback.answer()


@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer("Помощь")


@router.message(Command("mono"))
async def mono_info(message: Message):
    await message.answer(f"💳 Реквизиты Mono:\n{MONO}")




@router.message(F.text == "🛍️ Покупки")
async def purchases_category_message(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🛍️ <b>Магазин Freaking Stars</b>\n\n"
        "💰 Купить Stars — для профиля и игр\n"
        "👑 Купить Premium — подписка Telegram\n"
        "💠 Купить TON — криптовалюта\n"
        "🧮 Посчитать — калькулятор стоимости\n\n"
        "<i>Выберите нужный раздел</i>",
        parse_mode="HTML",
        reply_markup=purchases_menu(message.from_user.id in ADMIN_IDS),
    )


@router.message(F.text == "🆘 Поддержка")
async def support_category_message(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "💬 <b>Раздел поддержки</b>\n\n"
        "🛠️ Поддержка — связаться с командой\n"
        "💡 Предложения — идеи по магазину\n"
        "📣 Отзывы — смотреть и оставлять отзывы\n\n"
        "<i>Выберите нужный раздел</i>",
        parse_mode="HTML",
        reply_markup=support_category_menu(message.from_user.id in ADMIN_IDS),
    )


@router.message(F.text == "🛠️ Поддержка")
async def support_button_message(message: Message, state: FSMContext):
    await state.clear()
    await support_menu(message)


@router.message(F.text == "💡 Предложения")
async def suggestion_button_message(message: Message, state: FSMContext):
    await state.clear()
    await suggestion_menu(message, state)


@router.message(F.text == "📣 Отзывы")
async def reviews_button_message(message: Message, state: FSMContext):
    await state.clear()
    await show_reviews_menu(message)


@router.message(F.text == "👤 Профиль")
async def profile_message(message: Message, state: FSMContext):
    await state.clear()
    await show_profile(message)


@router.message(F.text == "👥 Рефералы")
@router.message(Command("ref", "referral", "referrals"))
async def referrals_message_handler(message: Message, state: FSMContext | None = None):
    if state:
        await state.clear()
    user = message.from_user
    register_user_if_needed(user.id, user.username)
    bot_info = await message.bot.get_me()
    summary = get_user_referral_summary(user.id, getattr(bot_info, "username", None))
    text, reply_markup = _build_referrals_view(summary)
    await message.answer(text, parse_mode="HTML", reply_markup=reply_markup)


@router.callback_query(F.data == "referrals_menu")
async def referrals_callback_handler(callback: CallbackQuery):
    user = callback.from_user
    register_user_if_needed(user.id, user.username)
    bot_info = await callback.bot.get_me()
    summary = get_user_referral_summary(user.id, getattr(bot_info, "username", None))
    text, reply_markup = _build_referrals_view(summary)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=reply_markup)
    await callback.answer()


@router.message(F.text == "🎮 Игры")
@router.message(Command("games", "game"))
async def games_redirect_handler(message: Message, state: FSMContext | None = None):
    if state:
        await state.clear()
    await message.answer(
        "🎮 <b>Игры Freaking Stars</b>\n\n"
        "📈 Crash — ракета улетает, успей забрать множитель!\n"
        "🪙 Монетка — орёл, решка или ребро?\n"
        "🔴 Plinko — шарики и множители до 100x+\n"
        "🏰 Tower — поднимайся и умножай ставку\n"
        "🃏 Blackjack — 21 очко против дилера\n"
        "⚡ Апгрейды — обменяй NFT на топовый приз\n"
        "🎁 Кейсы — открывай и выигрывай\n\n"
        "<i>Все игры доступны в Mini App</i>",
        parse_mode="HTML",
        reply_markup=build_open_app_keyboard(),
    )


@router.message(F.text == "🎁 Промокод")
async def promo_message(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(PromoStates.waiting_promo_code)
    await message.answer(
        "🎁 <b>Активация промокода</b>\n\n"
        "Введите кодовое слово для получения бонусных ⭐️\n\n"
        "<i>Промокоды выдаются в акциях и розыгрышах</i>",
        parse_mode="HTML",
        reply_markup=menu_with_back(message.from_user.id in ADMIN_IDS),
    )


@router.message(PromoStates.waiting_promo_code)
async def promo_code_input(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "⬅️ Назад":
        await state.clear()
        await message.answer(
            "🏠 <b>Главное меню</b>",
            parse_mode="HTML",
            reply_markup=main_menu(message.from_user.id in ADMIN_IDS),
        )
        return

    user_data = register_user_if_needed(message.from_user.id, message.from_user.username)
    code = _normalize_promocode(message.text or "")

    if not code:
        await message.answer(
            "❌ <b>Промокод не может быть пустым</b>\n\n"
            "<i>Введите кодовое слово ещё раз</i>",
            parse_mode="HTML",
        )
        return

    promo = next(
        (
            p for p in db.promocodes
            if _normalize_promocode(p.get("code", "")) == code and p.get("active", True)
        ),
        None,
    )
    if not promo:
        await state.clear()
        await message.answer(
            "❌ <b>Промокод не найден</b>\n\n"
            "<i>Промокод не существует или уже недоступен</i>",
            parse_mode="HTML",
        )
        return

    used_by = promo.setdefault("used_by", [])
    max_uses = int(promo.get("max_uses", 0) or 0)
    amount = int(promo.get("amount_stars", 0) or 0)

    if message.from_user.id in used_by:
        await state.clear()
        await message.answer(
            "❌ <b>Промокод уже использован</b>\n\n"
            "<i>Вы уже активировали этот промокод ранее</i>",
            parse_mode="HTML",
        )
        return

    if int(promo.get("used_count", 0) or 0) >= max_uses:
        promo["active"] = False
        db.save_data()
        await state.clear()
        await message.answer(
            "❌ <b>Промокод недействителен</b>\n\n"
            "<i>У этого промокода закончились активации</i>",
            parse_mode="HTML",
        )
        return

    used_by.append(message.from_user.id)
    promo["used_count"] = int(promo.get("used_count", 0) or 0) + 1
    if int(promo["used_count"]) >= max_uses:
        promo["active"] = False
    add_star_balance(user_data, amount)
    db.save_data()

    await state.clear()
    await message.answer(
        f"✅ <b>Промокод активирован!</b>\n\n"
        f"🎁 Начислено: <b>{amount} ⭐️</b>\n"
        f"💎 Новый баланс: <b>{format_stars(user_data.get('balance_stars', 0))} ⭐️</b>",
        parse_mode="HTML",
    )



@router.message(F.text == "⚙️ Админ-панель")
async def admin_panel_message(message: Message, state: FSMContext):
    await state.clear()
    await admin_panel(message)




@router.message(F.text == "⬅️ Назад")
async def back_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🏠 <b>Главное меню</b>",
        parse_mode="HTML",
        reply_markup=main_menu(message.from_user.id in ADMIN_IDS),
    )


@router.message()
async def text_router(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == SupportStates.waiting_suggestion.state:
        return
    if current_state:
        return

    await message.answer(
        "🏠 <b>Главное меню</b>",
        parse_mode="HTML",
        reply_markup=main_menu(message.from_user.id in ADMIN_IDS),
    )
