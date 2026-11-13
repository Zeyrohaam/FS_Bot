from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_IDS, PREMIUM_COST_PRICES
from database import db
from utils.helpers import (
    add_star_balance,
    add_ton_balance,
    format_stars,
    get_numeric_balance,
    get_numeric_ton_balance,
    register_user_if_needed,
    safe_edit_message,
)
from utils.cases import (
    CASE_DEFINITIONS,
    format_case_chances_for_admin,
    get_all_cases_summary_for_admin,
    get_case_chances,
    get_case_items,
    set_case_chances,
)
from utils.pricing import (
    get_premium_prices,
    get_star_packages,
    get_star_rates,
    update_premium_prices,
    update_star_rates,
)
from utils.cards import get_active_card, load_cards_data, set_active_card, update_card_number

router = Router()


import html as html_lib


class BroadcastAdminStates(StatesGroup):
    waiting_broadcast_text = State()


class PromoAdminStates(StatesGroup):
    waiting_max_uses = State()
    waiting_amount_stars = State()
    waiting_code_word = State()


class TrackUserStates(StatesGroup):
    waiting_user_identifier = State()


class PricingAdminStates(StatesGroup):
    waiting_star_rates = State()
    waiting_premium_prices = State()


class CaseChancesAdminStates(StatesGroup):
    waiting_chances_input = State()


class CardAdminStates(StatesGroup):
    editing_card_1 = State()
    editing_card_2 = State()



def _normalize_promocode(value: str) -> str:
    return (value or "").strip().upper()


COST_PRICE_PER_STAR = 0.66


def _parse_transaction_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    for fmt in ("%d.%m.%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _get_confirmed_transactions():
    return [t for t in db.transactions if t.get("status") == "confirmed"]


def _get_today_confirmed_transactions():
    now = datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    today_transactions = []
    for transaction in _get_confirmed_transactions():
        transaction_dt = _parse_transaction_datetime(transaction.get("date"))
        if transaction_dt and transaction_dt >= start_of_day:
            today_transactions.append(transaction)
    return today_transactions


def _default_global_game_stats() -> dict:
    return {
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "total_bet": 0,
        "total_paid_out": 0,
        "net_profit": 0,
    }


def _get_global_mines_stats() -> dict:
    return db.game_stats.setdefault("mines", _default_global_game_stats().copy())


def _get_global_crash_stats() -> dict:
    return db.game_stats.setdefault("crash", _default_global_game_stats().copy())


def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📣 Рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="💡 Предложения", callback_data="admin_suggestions")],
            [InlineKeyboardButton(text="🎁 Промокоды", callback_data="admin_promocode")],
            [InlineKeyboardButton(text="🔎 Отследить", callback_data="admin_track_user")],
            [InlineKeyboardButton(text="💸 Цены", callback_data="admin_prices")],
            [InlineKeyboardButton(text="🎲 Шансы кейсов", callback_data="admin_cases")],
            [InlineKeyboardButton(text="💳 Карты Mono", callback_data="admin_cards")],
            [InlineKeyboardButton(text="🚫 Кто отписался", callback_data="admin_unsubs")],
            [InlineKeyboardButton(text="❌ Отклонить все заявки", callback_data="admin_reject_all_pending_prompt")],
        ]
    )


async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ <b>Нет доступа</b>", parse_mode="HTML")
        return

    await message.answer(
        "⚙️ <b>Панель администратора</b>\n\n"
        "<i>Выберите раздел управления</i>",
        parse_mode="HTML",
        reply_markup=get_admin_panel_keyboard(),
    )


async def show_profile(message: Message):
    user_data = register_user_if_needed(message.from_user.id, message.from_user.username)
    balance = get_numeric_balance(user_data)
    ton_balance = get_numeric_ton_balance(user_data)
    total_bought = int(user_data.get("total_stars", 0) or 0)

    ref_count = len(user_data.get("referrals", [])) if isinstance(user_data.get("referrals"), list) else 0
    ref_earnings = float(user_data.get("referral_earnings_stars", 0) or 0)

    text = (
        f"👤 <b>Профиль</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"👤 Username: @{user_data.get('username', 'unknown')}\n\n"
        f"⭐ <b>Баланс Stars:</b> {format_stars(balance)} ⭐️\n"
        f"💠 <b>Баланс TON:</b> {format_stars(ton_balance)} TON\n"
        f"🛒 <b>Куплено всего:</b> {total_bought} ⭐️\n\n"
        f"👥 <b>Рефералов:</b> {ref_count}\n"
        f"💰 <b>Заработано с рефералов:</b> {format_stars(ref_earnings)} ⭐️"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💠 Купить TON", callback_data="balance_topup_start")],
            [
                InlineKeyboardButton(text="💸 Вывести ⭐", callback_data="withdraw_start"),
                InlineKeyboardButton(text="↘️ Вывести TON", callback_data="withdraw_ton_start"),
            ],
            [
                InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals_menu"),
                InlineKeyboardButton(text="📊 Статистика Игр", callback_data="game_stats"),
            ]
        ]
    )
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@router.callback_query(F.data == "game_stats")

async def game_stats(callback: CallbackQuery):
    user_data = register_user_if_needed(callback.from_user.id, callback.from_user.username)

    mines_stats = user_data.get("games", {}).get("mines", {})
    mines_wins = int(mines_stats.get("wins", 0) or 0)
    mines_losses = int(mines_stats.get("losses", 0) or 0)
    mines_games_played = int(mines_stats.get("games_played", mines_wins + mines_losses) or 0)
    mines_total_bet = float(mines_stats.get("total_bet", 0) or 0)
    mines_total_won = float(mines_stats.get("total_won", 0) or 0)
    mines_biggest_win = float(mines_stats.get("biggest_win", 0) or 0)
    mines_winrate = round((mines_wins / mines_games_played) * 100, 2) if mines_games_played > 0 else 0

    crash_stats = user_data.get("games", {}).get("crash", {})
    crash_wins = int(crash_stats.get("wins", 0) or 0)
    crash_losses = int(crash_stats.get("losses", 0) or 0)
    crash_games_played = int(crash_stats.get("games_played", crash_wins + crash_losses) or 0)
    crash_total_bet = float(crash_stats.get("total_bet", 0) or 0)
    crash_total_won = float(crash_stats.get("total_won", 0) or 0)
    crash_biggest_win = float(crash_stats.get("biggest_win", 0) or 0)
    crash_winrate = round((crash_wins / crash_games_played) * 100, 2) if crash_games_played > 0 else 0

    roulette_stats = user_data.get("games", {}).get("roulette", {})
    roulette_wins = int(roulette_stats.get("wins", 0) or 0)
    roulette_losses = int(roulette_stats.get("losses", 0) or 0)
    roulette_games_played = int(roulette_stats.get("games_played", roulette_wins + roulette_losses) or 0)
    roulette_total_bet = float(roulette_stats.get("total_bet", 0) or 0)
    roulette_total_won = float(roulette_stats.get("total_won", 0) or 0)
    roulette_biggest_win = float(roulette_stats.get("biggest_win", 0) or 0)
    roulette_winrate = round((roulette_wins / roulette_games_played) * 100, 2) if roulette_games_played > 0 else 0

    text = (
        f"🎮 <b>Статистика игр</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"💣 <b>Мины</b>\n"
        f"• Игр сыграно: <b>{mines_games_played}</b>\n"
        f"• Побед: <b>{mines_wins}</b> | Поражений: <b>{mines_losses}</b>\n"
        f"• Винрейт: <b>{mines_winrate}%</b>\n"
        f"• Ставок: <b>{format_stars(mines_total_bet)} ⭐️</b>\n"
        f"• Выиграно: <b>{format_stars(mines_total_won)} ⭐️</b>\n"
        f"• Рекорд: <b>{format_stars(mines_biggest_win)} ⭐️</b>\n\n"
        f"📈 <b>Crash</b>\n"
        f"• Игр сыграно: <b>{crash_games_played}</b>\n"
        f"• Побед: <b>{crash_wins}</b> | Поражений: <b>{crash_losses}</b>\n"
        f"• Винрейт: <b>{crash_winrate}%</b>\n"
        f"• Ставок: <b>{format_stars(crash_total_bet)} ⭐️</b>\n"
        f"• Выиграно: <b>{format_stars(crash_total_won)} ⭐️</b>\n"
        f"• Рекорд: <b>{format_stars(crash_biggest_win)} ⭐️</b>\n\n"
        f"🎡 <b>Рулетка</b>\n"
        f"• Игр сыграно: <b>{roulette_games_played}</b>\n"
        f"• Побед: <b>{roulette_wins}</b> | Поражений: <b>{roulette_losses}</b>\n"
        f"• Винрейт: <b>{roulette_winrate}%</b>\n"
        f"• Ставок: <b>{format_stars(roulette_total_bet)} ⭐️</b>\n"
        f"• Выиграно: <b>{format_stars(roulette_total_won)} ⭐️</b>\n"
        f"• Рекорд: <b>{format_stars(roulette_biggest_win)} ⭐️</b>"
    )

    back_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад в профиль", callback_data="profile_back")]
        ]
    )

    await safe_edit_message(callback, text, reply_markup=back_keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "profile_back")
async def profile_back(callback: CallbackQuery):
    user_data = register_user_if_needed(callback.from_user.id, callback.from_user.username)
    balance = get_numeric_balance(user_data)
    ton_balance = get_numeric_ton_balance(user_data)
    total_bought = int(user_data.get("total_stars", 0) or 0)

    text = (
        f"👤 Профиль\n\n"
        f"🆔 ID: {callback.from_user.id}\n"
        f"👤 Username: @{user_data.get('username', 'unknown')}\n"
        f"💎 Баланс: {format_stars(balance)} ⭐️\n"
        f"💠 TON баланс: {format_stars(ton_balance)} TON\n"
        f"🛒 Всего куплено: {total_bought} ⭐️"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💠 Купить TON", callback_data="balance_topup_start")],
            [
                InlineKeyboardButton(text="💸 Вывести ⭐", callback_data="withdraw_start"),
                InlineKeyboardButton(text="↘️ Вывести TON", callback_data="withdraw_ton_start"),
            ],
            [InlineKeyboardButton(text="🎮 Статистика игр", callback_data="game_stats")],
        ]
    )

    await safe_edit_message(callback, text, reply_markup=keyboard)
    await callback.answer()


def get_pending_suggestions():
    return [s for s in db.suggestions if s.get("status") == "pending"]


def build_suggestion_keyboard(index: int, total: int, suggestion_id: int) -> InlineKeyboardMarkup:
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"suggest_prev_{index}"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton(text="➡️ Дальше", callback_data=f"suggest_next_{index}"))

    rows = []
    if nav_row:
        rows.append(nav_row)
    rows.append(
        [
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"suggest_reject_{suggestion_id}_{index}"),
            InlineKeyboardButton(text="🕐 На рассмотрение", callback_data=f"suggest_review_{suggestion_id}_{index}"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_suggestion_page(callback: CallbackQuery, index: int):
    pending = get_pending_suggestions()
    if not pending:
        await safe_edit_message(callback, "💡 Активных предложений нет")
        return

    if index < 0:
        index = 0
    if index >= len(pending):
        index = len(pending) - 1

    suggestion = pending[index]
    text = (
        f"💡 Предложения ({index + 1}/{len(pending)})\n\n"
        f"🆔 #{suggestion['id']}\n"
        f"👤 ID: {suggestion['user_id']}\n"
        f"👤 @{suggestion.get('username', 'unknown')}\n"
        f"📅 {suggestion.get('date', '-')}\n\n"
        f"📝 {suggestion.get('text', '')}"
    )
    await safe_edit_message(
        callback,
        text,
        reply_markup=build_suggestion_keyboard(index, len(pending), int(suggestion["id"])),
    )




def _find_user_by_identifier(raw_value: str):
    value = (raw_value or "").strip()
    if not value:
        return None, None

    if value.isdigit() and value in db.users:
        return value, db.users[value]

    username = value.lstrip("@").lower()
    for uid, user_data in db.users.items():
        current_username = str(user_data.get("username", "")).lstrip("@").lower()
        if username and current_username == username:
            return uid, user_data

    return None, None


def _format_recent_games(user_data: dict) -> str:
    recent_games = list(user_data.get("recent_games", []))[-5:]
    if not recent_games:
        return "— Нет завершённых игр"

    lines = []
    for item in reversed(recent_games):
        if item.get("game") == "crash":
            game_name = "Crash"
        elif item.get("game") == "roulette":
            game_name = "Рулетка"
        else:
            game_name = "Мины"
        result_icon = "✅" if item.get("result") == "win" else "❌"
        bet = format_stars(item.get("bet", 0))
        payout = format_stars(item.get("payout", 0))
        x_value = float(item.get("x", 0) or 0)
        extra = ""
        if item.get("game") == "mines":
            extra = f" | клеток: {int(item.get('safe_clicks', 0) or 0)}"
        elif item.get("round_number"):
            extra = f" | раунд #{int(item.get('round_number', 0) or 0)}"
        elif item.get("game") == "roulette":
            extra = f" | выбор: {item.get('picked_color', '-')} | выпало: {item.get('result_color', '-')}"

        lines.append(
            f"{result_icon} {game_name} | ставка: {bet}⭐ | выплата: {payout}⭐ | x: {x_value:.2f}{extra} | {item.get('date', '-') }"
        )
    return "\n".join(lines)


def _build_tracked_user_text(user_id: int, user_data: dict) -> str:
    balance = get_numeric_balance(user_data)
    username = html_lib.escape(str(user_data.get("username", "unknown")), quote=False)
    registration_date = user_data.get("registration_date", "-")
    last_active = user_data.get("last_active", "-")
    total_bought = format_stars(user_data.get("total_stars", 0))

    mines_stats = user_data.get("games", {}).get("mines", {})
    crash_stats = user_data.get("games", {}).get("crash", {})
    roulette_stats = user_data.get("games", {}).get("roulette", {})

    mines_played = int(mines_stats.get("games_played", 0) or 0)
    mines_wins = int(mines_stats.get("wins", 0) or 0)
    mines_losses = int(mines_stats.get("losses", 0) or 0)
    mines_winrate = round((mines_wins / mines_played) * 100, 2) if mines_played else 0

    crash_played = int(crash_stats.get("games_played", 0) or 0)
    crash_wins = int(crash_stats.get("wins", 0) or 0)
    crash_losses = int(crash_stats.get("losses", 0) or 0)
    crash_winrate = round((crash_wins / crash_played) * 100, 2) if crash_played else 0

    roulette_played = int(roulette_stats.get("games_played", 0) or 0)
    roulette_wins = int(roulette_stats.get("wins", 0) or 0)
    roulette_losses = int(roulette_stats.get("losses", 0) or 0)
    roulette_winrate = round((roulette_wins / roulette_played) * 100, 2) if roulette_played else 0

    total_games = mines_played + crash_played + roulette_played
    total_wins = mines_wins + crash_wins + roulette_wins
    total_losses = mines_losses + crash_losses + roulette_losses
    total_winrate = round((total_wins / total_games) * 100, 2) if total_games else 0

    user_transactions = [t for t in db.transactions if int(t.get("user_id", 0) or 0) == int(user_id)]
    confirmed_transactions = [t for t in user_transactions if t.get("status") == "confirmed"]
    total_paid = sum(float(t.get("amount", 0) or 0) for t in confirmed_transactions)
    pending_transactions = [t for t in user_transactions if t.get("status") == "pending"]

    current_game = user_data.get("current_game") if isinstance(user_data.get("current_game"), dict) else None
    current_game_text = "— Нет"
    if current_game:
        if current_game.get("type") == "crash":
            game_name = "Crash"
        elif current_game.get("type") == "roulette":
            game_name = "Рулетка"
        else:
            game_name = "Мины"
        current_game_text = f"{game_name} | ставка: {format_stars(current_game.get('bet', 0))}⭐"

    return (
        f"🔎 <b>Статистика пользователя</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Username: @{username}\n"
        f"💎 Баланс: <b>{format_stars(balance)} ⭐️</b>\n"
        f"🛒 Куплено звёзд: <b>{total_bought} ⭐️</b>\n"
        f"💳 Оплат: <b>{len(confirmed_transactions)}</b> (на сумму {total_paid:.2f} грн)\n"
        f"⏳ В ожидании: <b>{len(pending_transactions)}</b>\n"
        f"📅 Регистрация: {registration_date}\n"
        f"🕒 Активность: {last_active}\n"
        f"🎮 В игре: <b>{current_game_text}</b>\n\n"
        f"📊 <b>Общие результаты</b>\n"
        f"• Винрейт: <b>{total_winrate}%</b>\n"
        f"• Всего игр: <b>{total_games}</b> (Побед: {total_wins} | Поражений: {total_losses})\n\n"
        f"💣 <b>Мины</b>\n"
        f"• Игр: <b>{mines_played}</b> | Винрейт: <b>{mines_winrate}%</b>\n"
        f"• Ставок: {format_stars(mines_stats.get('total_bet', 0))} ⭐️ | Выигрыш: {format_stars(mines_stats.get('total_won', 0))} ⭐️\n\n"
        f"📈 <b>Crash</b>\n"
        f"• Игр: <b>{crash_played}</b> | Винрейт: <b>{crash_winrate}%</b>\n"
        f"• Ставок: {format_stars(crash_stats.get('total_bet', 0))} ⭐️ | Выигрыш: {format_stars(crash_stats.get('total_won', 0))} ⭐️\n\n"
        f"🧾 <b>Последние игры</b>\n{_format_recent_games(user_data)}"
    )

@router.callback_query(F.data == "admin_suggestions")
async def open_suggestions(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    pending = get_pending_suggestions()
    if not pending:
        await safe_edit_message(callback, "💡 Активных предложений нет")
        await callback.answer()
        return
    await show_suggestion_page(callback, len(pending) - 1)
    await callback.answer()


@router.callback_query(F.data.startswith("suggest_prev_"))
async def suggestion_prev(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    current_index = int(callback.data.split("_")[-1])
    await show_suggestion_page(callback, current_index - 1)
    await callback.answer()


@router.callback_query(F.data.startswith("suggest_next_"))
async def suggestion_next(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    current_index = int(callback.data.split("_")[-1])
    await show_suggestion_page(callback, current_index + 1)
    await callback.answer()


@router.callback_query(F.data.startswith("suggest_reject_"))
async def suggestion_reject(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    parts = callback.data.split("_")
    suggestion_id = int(parts[-2])
    current_index = int(parts[-1])
    suggestion = next((s for s in db.suggestions if int(s.get("id", 0)) == suggestion_id), None)
    if not suggestion:
        await callback.answer("Предложение не найдено", show_alert=True)
        return

    suggestion["status"] = "rejected"
    db.save_data()

    try:
        await callback.bot.send_message(
            suggestion["user_id"],
            "❌ Ваше предложение отклонено\n\n"
            f"Ваше предложение:\n{suggestion.get('text', '')}",
        )
    except Exception:
        pass

    pending = get_pending_suggestions()
    if not pending:
        await safe_edit_message(callback, "💡 Активных предложений больше нет")
    else:
        await show_suggestion_page(callback, min(current_index, len(pending) - 1))
    await callback.answer("Предложение отклонено")


@router.callback_query(F.data.startswith("suggest_review_"))
async def suggestion_review(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    parts = callback.data.split("_")
    suggestion_id = int(parts[-2])
    current_index = int(parts[-1])
    suggestion = next((s for s in db.suggestions if int(s.get("id", 0)) == suggestion_id), None)
    if not suggestion:
        await callback.answer("Предложение не найдено", show_alert=True)
        return

    suggestion["status"] = "under_review"
    db.save_data()

    try:
        await callback.bot.send_message(
            suggestion["user_id"],
            "🕐 Ваше предложение на рассмотрении\n\n"
            f"Ваше предложение:\n{suggestion.get('text', '')}",
        )
    except Exception:
        pass

    pending = get_pending_suggestions()
    if not pending:
        await safe_edit_message(callback, "💡 Активных предложений больше нет")
    else:
        await show_suggestion_page(callback, min(current_index, len(pending) - 1))
    await callback.answer("Отмечено как на рассмотрении")


@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return

    confirmed_transactions = _get_confirmed_transactions()
    mines_stats = _get_global_mines_stats()
    crash_stats = _get_global_crash_stats()

    total_users = len(db.users)
    total_orders = len(db.transactions)
    total_confirmed_orders = len(confirmed_transactions)
    total_earned = sum(float(t.get("amount", 0) or 0) for t in confirmed_transactions)

    total_stars_sold = sum(int(t.get("stars", 0) or 0) for t in confirmed_transactions if t.get("type") == "stars")
    total_stars_revenue = sum(float(t.get("amount", 0) or 0) for t in confirmed_transactions if t.get("type") == "stars")
    total_stars_cost = total_stars_sold * COST_PRICE_PER_STAR

    total_premium_orders = [t for t in confirmed_transactions if t.get("type") == "premium"]
    total_premium_revenue = sum(float(t.get("amount", 0) or 0) for t in total_premium_orders)
    total_premium_cost = sum(float(PREMIUM_COST_PRICES.get(int(t.get("months", 0) or 0), 0)) for t in total_premium_orders)

    total_cost = total_stars_cost + total_premium_cost
    total_net_profit = total_earned - total_cost

    text = (
        f"📊 <b>Статистика магазина</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Пользователей: <b>{total_users}</b>\n"
        f"📦 Заявок всего: <b>{total_orders}</b>\n"
        f"✅ Подтверждено: <b>{total_confirmed_orders}</b>\n\n"
        f"💰 <b>Финансы</b>\n"
        f"• Выручка: <b>{total_earned:.2f} грн</b>\n"
        f"• Себестоимость: <b>{total_cost:.2f} грн</b>\n"
        f"• Чистая прибыль: <b>{total_net_profit:.2f} грн</b>\n\n"
        f"📦 <b>Продажи за всё время</b>\n"
        f"⭐ Stars: <b>{total_stars_sold} шт.</b>\n"
        f"   Выручка: {total_stars_revenue:.2f} грн | Себест.: {total_stars_cost:.2f} грн\n"
        f"👑 Premium: <b>{len(total_premium_orders)} шт.</b>\n"
        f"   Выручка: {total_premium_revenue:.2f} грн | Себест.: {total_premium_cost:.2f} грн\n\n"
        f"🎮 <b>Статистика игр (Мины)</b>\n"
        f"• Игр: <b>{int(mines_stats.get('games_played', 0) or 0)}</b>\n"
        f"• Побед: <b>{int(mines_stats.get('wins', 0) or 0)}</b> | "
        f"Поражений: <b>{int(mines_stats.get('losses', 0) or 0)}</b>\n"
        f"• Ставок: <b>{int(mines_stats.get('total_bet', 0) or 0)} ⭐️</b>\n"
        f"• Выплачено: <b>{int(mines_stats.get('total_paid_out', 0) or 0)} ⭐️</b>\n"
        f"• Прибыль казино: <b>{int(mines_stats.get('net_profit', 0) or 0)} ⭐️</b>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🗑 Очистить статистику", callback_data="clear_stats")]]
    )
    await safe_edit_message(callback, text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "clear_stats")
async def clear_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    db.transactions = []
    db.transaction_id_counter = 1
    db.game_stats = {
        "mines": _default_global_game_stats().copy(),
        "crash": _default_global_game_stats().copy(),
        "roulette": _default_global_game_stats().copy(),
    }
    db.save_data()
    await safe_edit_message(callback, "🗑 Статистика продаж и игр очищена")
    await callback.answer()


@router.callback_query(F.data == "admin_unsubs")
async def show_unsubscribed(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return

    unsub_logs = [log for log in db.sub_logs if log.get("action") == "UNSUBSCRIBED"]
    if not unsub_logs:
        await safe_edit_message(callback, "Никто не отписывался")
        await callback.answer()
        return

    text = "🚫 Последние отписки:\n\n"
    for log in unsub_logs[-10:][::-1]:
        text += (
            f"👤 @{log.get('username', 'unknown')} | {log.get('user_id')}\n"
            f"📢 {log.get('channel')}\n"
            f"📅 {log.get('date')}\n\n"
        )
    await safe_edit_message(callback, text)
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await state.set_state(BroadcastAdminStates.waiting_broadcast_text)
    await callback.message.answer(
        "📣 <b>Массовая рассылка</b>\n\n"
        "Отправьте текст сообщения для рассылки всем пользователям бота:\n\n"
        "<i>Или нажмите ⬅️ Назад для отмены</i>",
        parse_mode="HTML",
        reply_markup=menu_with_back(callback.from_user.id in ADMIN_IDS),
    )
    await callback.answer()


@router.message(BroadcastAdminStates.waiting_broadcast_text)
async def process_broadcast_message(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "⬅️ Назад":
        await state.clear()
        await admin_panel(message)
        return

    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ <b>Нет доступа</b>", parse_mode="HTML")
        await state.clear()
        return

    if not text:
        await message.answer("❌ <b>Текст рассылки не может быть пустым</b>", parse_mode="HTML")
        return

    await state.clear()
    status_msg = await message.answer("⏳ <b>Рассылка запущена...</b>", parse_mode="HTML")
    db.refresh()
    success = 0
    failed = 0
    import asyncio
    for uid in list(db.users.keys()):
        try:
            await message.bot.send_message(int(uid), text)
            success += 1
            await asyncio.sleep(0.04)
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"📣 <b>Рассылка завершена</b>\n\n"
        f"✅ Отправлено: <b>{success}</b>\n"
        f"❌ Ошибки: <b>{failed}</b>",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_promocode")
async def admin_promocode_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await state.set_state(PromoAdminStates.waiting_max_uses)
    await callback.message.answer(
        "🎁 <b>Создание промокода (Шаг 1/3)</b>\n\n"
        "Введите максимальное количество активаций (число):",
        parse_mode="HTML",
        reply_markup=menu_with_back(callback.from_user.id in ADMIN_IDS)
    )
    await callback.answer()


@router.message(PromoAdminStates.waiting_max_uses)
async def admin_promocode_max_uses(message: Message, state: FSMContext):
    if (message.text or "").strip() == "⬅️ Назад":
        await state.clear()
        await admin_panel(message)
        return

    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ <b>Нет доступа</b>", parse_mode="HTML")
        await state.clear()
        return

    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("❌ <b>Введите целое число больше 0</b>", parse_mode="HTML")
        return

    await state.update_data(promocode_max_uses=int(raw))
    await state.set_state(PromoAdminStates.waiting_amount_stars)
    await message.answer(
        "💎 <b>Создание промокода (Шаг 2/3)</b>\n\n"
        "Введите сумму начисления в Stars ⭐ (целое число):",
        parse_mode="HTML",
        reply_markup=menu_with_back(message.from_user.id in ADMIN_IDS)
    )


@router.message(PromoAdminStates.waiting_amount_stars)
async def admin_promocode_amount(message: Message, state: FSMContext):
    if (message.text or "").strip() == "⬅️ Назад":
        await state.clear()
        await admin_panel(message)
        return

    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ <b>Нет доступа</b>", parse_mode="HTML")
        await state.clear()
        return

    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("❌ <b>Введите целое число больше 0</b>", parse_mode="HTML")
        return

    await state.update_data(promocode_amount_stars=int(raw))
    await state.set_state(PromoAdminStates.waiting_code_word)
    await message.answer(
        "🔐 <b>Создание промокода (Шаг 3/3)</b>\n\n"
        "Введите кодовое слово промокода (например: <code>STAR2026</code>):",
        parse_mode="HTML",
        reply_markup=menu_with_back(message.from_user.id in ADMIN_IDS)
    )


@router.message(PromoAdminStates.waiting_code_word)
async def admin_promocode_code(message: Message, state: FSMContext):
    if (message.text or "").strip() == "⬅️ Назад":
        await state.clear()
        await admin_panel(message)
        return

    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ <b>Нет доступа</b>", parse_mode="HTML")
        await state.clear()
        return

    code_word = _normalize_promocode(message.text or "")
    if len(code_word) < 2:
        await message.answer("❌ <b>Кодовое слово слишком короткое</b>", parse_mode="HTML")
        return

    if any(_normalize_promocode(p.get("code", "")) == code_word for p in db.promocodes):
        await message.answer("❌ <b>Такой промокод уже существует</b>. Придумайте другое слово.", parse_mode="HTML")
        return

    data = await state.get_data()
    promo = {
        "code": code_word,
        "max_uses": int(data.get("promocode_max_uses", 0) or 0),
        "used_count": 0,
        "amount_stars": int(data.get("promocode_amount_stars", 0) or 0),
        "used_by": [],
        "active": True,
        "created_by": message.from_user.id,
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    db.promocodes.append(promo)
    db.save_data()
    await state.clear()

    await message.answer(
        f"✅ <b>Промокод успешно создан!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🔐 Код: <code>{promo['code']}</code>\n"
        f"🔁 Активаций: <b>{promo['max_uses']}</b>\n"
        f"⭐ Награда: <b>{promo['amount_stars']} ⭐️</b>",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_track_user")
async def admin_track_user_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await state.set_state(TrackUserStates.waiting_user_identifier)
    await callback.message.answer(
        "🔎 <b>Поиск пользователя</b>\n\n"
        "Отправьте ID пользователя или его @username:",
        parse_mode="HTML",
        reply_markup=menu_with_back(callback.from_user.id in ADMIN_IDS),
    )
    await callback.answer()


@router.message(TrackUserStates.waiting_user_identifier)
async def admin_track_user_lookup(message: Message, state: FSMContext):
    if (message.text or "").strip() == "⬅️ Назад":
        await state.clear()
        await admin_panel(message)
        return

    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ <b>Нет доступа</b>", parse_mode="HTML")
        await state.clear()
        return

    user_id, user_data = _find_user_by_identifier(message.text or "")
    if not user_data:
        await message.answer(
            "❌ <b>Пользователь не найден</b>\nПопробуйте ввести другой ID или @username:",
            parse_mode="HTML",
            reply_markup=menu_with_back(message.from_user.id in ADMIN_IDS),
        )
        return

    await state.clear()
    await message.answer(_build_tracked_user_text(int(user_id), user_data), parse_mode="HTML")


def _build_prices_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Цены Stars", callback_data="admin_prices_stars")],
            [InlineKeyboardButton(text="👑 Цены Premium", callback_data="admin_prices_premium")],
            [InlineKeyboardButton(text="🎲 Шансы кейсов", callback_data="admin_cases")],
        ]
    )


def _format_current_prices() -> str:
    star_rates = get_star_rates()
    packages = get_star_packages()
    premium = get_premium_prices()
    star_lines = [f"• {mn}–{mx} ⭐ = <b>{rate:.3f}</b> грн/⭐" for mn, mx, rate in star_rates]
    package_lines = [f"• {stars} ⭐ = <b>{price:.2f}</b> грн" for stars, price in sorted(packages.items())]
    premium_lines = [f"• {months} мес. = <b>{premium[months]:.2f}</b> грн" for months in sorted(premium.keys())]
    return (
        "💸 <b>Управление ценами</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "⭐ <b>Stars по коэффициентам:</b>\n" + "\n".join(star_lines)
        + "\n\n📦 <b>Пакеты Stars:</b>\n" + "\n".join(package_lines)
        + "\n\n👑 <b>Telegram Premium:</b>\n" + "\n".join(premium_lines)
    )

def _parse_star_rates_text(raw_text: str) -> list[tuple[int, int, float]] | None:
    lines = [line.strip() for line in (raw_text or "").splitlines() if line.strip()]
    if len(lines) != 4:
        return None
    result = []
    for line in lines:
        if "=" not in line or "-" not in line:
            return None
        left, right = [part.strip() for part in line.split("=", 1)]
        min_text, max_text = [part.strip() for part in left.split("-", 1)]
        try:
            result.append((int(min_text), int(max_text), float(right.replace(",", "."))))
        except Exception:
            return None
    return result


def _parse_premium_prices_text(raw_text: str) -> dict[int, float] | None:
    lines = [line.strip() for line in (raw_text or "").splitlines() if line.strip()]
    if len(lines) != 4:
        return None
    result: dict[int, float] = {}
    for line in lines:
        if "=" not in line:
            return None
        left, right = [part.strip() for part in line.split("=", 1)]
        try:
            months = int(left)
            price = float(right.replace(",", "."))
        except Exception:
            return None
        result[months] = price
    if sorted(result.keys()) != [1, 3, 6, 12]:
        return None
    return result


@router.callback_query(F.data == "admin_prices")
async def admin_prices_menu(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await safe_edit_message(callback, _format_current_prices(), reply_markup=_build_prices_menu(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_prices_stars")
async def admin_prices_stars_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await state.set_state(PricingAdminStates.waiting_star_rates)
    current = get_star_rates()
    template = "\n".join(f"{mn}-{mx}={rate:.3f}" for mn, mx, rate in current)
    await callback.message.answer(
        "⭐ <b>Изменение цен Stars</b>\n\n"
        "Отправьте 4 строки в формате:\n"
        "<code>50-149=0.73\n"
        "150-499=0.715\n"
        "500-1499=0.692\n"
        "1500-10000=0.674</code>\n\n"
        f"<b>Текущие значения:</b>\n<code>{template}</code>",
        parse_mode="HTML",
        reply_markup=menu_with_back(callback.from_user.id in ADMIN_IDS),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_prices_premium")
async def admin_prices_premium_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await state.set_state(PricingAdminStates.waiting_premium_prices)
    current = get_premium_prices()
    template = "\n".join(f"{months}={current[months]:.2f}" for months in [1, 3, 6, 12])
    await callback.message.answer(
        "👑 <b>Изменение цен Premium</b>\n\n"
        "Отправьте 4 строки в формате:\n"
        "<code>1=140\n3=610\n6=780\n12=1370</code>\n\n"
        f"<b>Текущие значения:</b>\n<code>{template}</code>",
        parse_mode="HTML",
        reply_markup=menu_with_back(callback.from_user.id in ADMIN_IDS),
    )
    await callback.answer()


@router.message(PricingAdminStates.waiting_star_rates)
async def admin_prices_stars_save(message: Message, state: FSMContext):
    if (message.text or "").strip() == "⬅️ Назад":
        await state.clear()
        await admin_panel(message)
        return
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ <b>Нет доступа</b>", parse_mode="HTML")
        await state.clear()
        return
    parsed = _parse_star_rates_text(message.text or "")
    if not parsed:
        await message.answer(
            "❌ <b>Неверный формат</b>. Пример:\n"
            "<code>50-149=0.73\n"
            "150-499=0.715\n"
            "500-1499=0.692\n"
            "1500-10000=0.674</code>",
            parse_mode="HTML"
        )
        return
    update_star_rates(parsed)
    await state.clear()
    await message.answer("✅ <b>Цены Stars успешно обновлены!</b>\n\n" + _format_current_prices(), parse_mode="HTML")


@router.message(PricingAdminStates.waiting_premium_prices)
async def admin_prices_premium_save(message: Message, state: FSMContext):
    if (message.text or "").strip() == "⬅️ Назад":
        await state.clear()
        await admin_panel(message)
        return
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ <b>Нет доступа</b>", parse_mode="HTML")
        await state.clear()
        return
    parsed = _parse_premium_prices_text(message.text or "")
    if not parsed:
        await message.answer(
            "❌ <b>Неверный формат</b>. Пример:\n"
            "<code>1=140\n3=610\n6=780\n12=1370</code>",
            parse_mode="HTML"
        )
        return
    update_premium_prices(parsed)
    await state.clear()
    await message.answer("✅ <b>Цены Premium успешно обновлены!</b>\n\n" + _format_current_prices(), parse_mode="HTML")


@router.callback_query(F.data == "admin_cases")
async def admin_cases_overview(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    text = get_all_cases_summary_for_admin()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Летний кейс (150⭐️)", callback_data="admin_case_view:case150")],
            [InlineKeyboardButton(text="📦 Завоз (250⭐️)", callback_data="admin_case_view:case250")],
            [InlineKeyboardButton(text="📦 Богатый (400⭐️)", callback_data="admin_case_view:case400")],
            [InlineKeyboardButton(text="📦 Лакшери (600⭐️)", callback_data="admin_case_view:case600")],
            [InlineKeyboardButton(text="⬅️ В админ-панель", callback_data="admin_panel_back")],
        ]
    )
    await safe_edit_message(callback, text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_case_view:"))
async def admin_case_view_tier(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    tier = callback.data.split(":", 1)[1]
    if tier not in CASE_DEFINITIONS:
        await callback.answer("Кейс не найден", show_alert=True)
        return
    text = format_case_chances_for_admin(tier)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить шансы", callback_data=f"admin_case_edit:{tier}")],
            [InlineKeyboardButton(text="🔄 Сбросить к стандартным", callback_data=f"admin_case_reset:{tier}")],
            [InlineKeyboardButton(text="⬅️ Назад к кейсам", callback_data="admin_cases")],
        ]
    )
    await safe_edit_message(callback, text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_case_edit:"))
async def admin_case_edit_tier(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    tier = callback.data.split(":", 1)[1]
    if tier not in CASE_DEFINITIONS:
        await callback.answer("Кейс не найден", show_alert=True)
        return
    await state.set_state(CaseChancesAdminStates.waiting_chances_input)
    await state.update_data(editing_case_tier=tier)

    case_def = CASE_DEFINITIONS[tier]
    items = get_case_items(tier)
    item_lines = [
        f"<b>{i}.</b> {item['icon']} {item['label']} — <code>{item['chance_percent']:.2f}%</code>"
        for i, item in enumerate(items, 1)
    ]

    prompt = (
        f"✏️ <b>Настройка шансов: {case_def['label']}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        + "\n".join(item_lines) + "\n\n"
        "<b>Как изменить шансы:</b>\n"
        "Отправьте сообщение в формате:\n"
        "<code>номер=процент</code> или <code>название=процент</code>\n\n"
        "<i>Можно указать один или несколько призов (каждый с новой строки).</i>\n"
        "Пример:\n"
        "<code>1=70.5\n2=5\n3=4.5</code>\n\n"
        "<i>Или отправьте <b>⬅️ Назад</b> для отмены.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data=f"admin_case_view:{tier}")]
        ]
    )
    await callback.message.answer(prompt, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_case_reset:"))
async def admin_case_reset_tier(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    tier = callback.data.split(":", 1)[1]
    if tier not in CASE_DEFINITIONS:
        await callback.answer("Кейс не найден", show_alert=True)
        return
    defaults = {item["id"]: float(item["default_chance"]) for item in CASE_DEFINITIONS[tier]["items"]}
    set_case_chances(tier, defaults)
    text = "✅ <b>Шансы сброшены к стандартным значениям!</b>\n\n" + format_case_chances_for_admin(tier)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить шансы", callback_data=f"admin_case_edit:{tier}")],
            [InlineKeyboardButton(text="⬅️ Назад к кейсам", callback_data="admin_cases")],
        ]
    )
    await safe_edit_message(callback, text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer("Шансы сброшены")


@router.message(CaseChancesAdminStates.waiting_chances_input)
async def admin_case_save_chances_input(message: Message, state: FSMContext):
    if (message.text or "").strip() == "⬅️ Назад":
        await state.clear()
        await admin_panel(message)
        return

    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ <b>Нет доступа</b>", parse_mode="HTML")
        await state.clear()
        return

    data = await state.get_data()
    tier = data.get("editing_case_tier")
    if not tier or tier not in CASE_DEFINITIONS:
        await state.clear()
        await message.answer("❌ Сессия редактирования устарела.")
        return

    raw_text = (message.text or "").strip()
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    items = CASE_DEFINITIONS[tier]["items"]

    parsed_chances: dict[str, float] = {}
    errors = []

    for line in lines:
        if "=" not in line and ":" not in line:
            errors.append(f"Неверный формат строки: <code>{html_lib.escape(line)}</code>")
            continue
        delimiter = "=" if "=" in line else ":"
        key_part, val_part = [p.strip() for p in line.split(delimiter, 1)]
        try:
            val = float(val_part.replace(",", ".").replace("%", "").strip())
            if val < 0:
                raise ValueError("Chance must be non-negative")
        except ValueError:
            errors.append(f"Некорректное число: <code>{html_lib.escape(val_part)}</code>")
            continue

        matched_item = None
        if key_part.isdigit():
            idx = int(key_part) - 1
            if 0 <= idx < len(items):
                matched_item = items[idx]
            else:
                errors.append(f"Приз под номером {key_part} не существует (всего {len(items)})")
                continue
        else:
            k_low = key_part.lower()
            for item in items:
                if (item["id"].lower() == k_low
                    or item["label"].lower() == k_low
                    or (item.get("model") and item["model"].lower() == k_low)
                    or item["name"].lower() == k_low):
                    matched_item = item
                    break

        if matched_item:
            parsed_chances[matched_item["id"]] = val
        else:
            errors.append(f"Приз «{html_lib.escape(key_part)}» не найден в кейсе")

    if not parsed_chances and errors:
        await message.answer(
            "❌ <b>Ошибки при распознавании:</b>\n" + "\n".join(errors) + "\n\n<i>Попробуйте ещё раз, например:</i> <code>1=50</code>",
            parse_mode="HTML"
        )
        return

    set_case_chances(tier, parsed_chances)
    await state.clear()

    reply_text = "✅ <b>Шансы кейса успешно обновлены!</b>\n\n"
    if errors:
        reply_text += "⚠️ <i>Некоторые строки были пропущены:</i>\n" + "\n".join(errors) + "\n\n"
    reply_text += "━━━━━━━━━━━━━━━━━━\n\n" + format_case_chances_for_admin(tier)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить ещё", callback_data=f"admin_case_edit:{tier}")],
            [InlineKeyboardButton(text="⬅️ Назад к кейсам", callback_data="admin_cases")],
            [InlineKeyboardButton(text="⚙️ В админ-панель", callback_data="admin_panel_back")],
        ]
    )
    await message.answer(reply_text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin_reject_all_pending_prompt")
async def admin_reject_all_pending_prompt(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    db.refresh()
    pending = [t for t in db.transactions if t.get("status") == "pending"]
    if not pending:
        await callback.answer("Висящих заявок нет!", show_alert=True)
        return

    text = (
        f"⚠️ <b>Отклонение всех заявок</b>\n\n"
        f"Найдено висящих заявок: <b>{len(pending)}</b> шт.\n\n"
        f"Вы действительно хотите отклонить ВСЕ висящие заявки?\n"
        f"<i>Средства по заявкам на вывод будут автоматически возвращены пользователям.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, отклонить все", callback_data="admin_reject_all_pending_confirm"),
                InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_panel_back"),
            ]
        ]
    )
    await safe_edit_message(callback, text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_reject_all_pending_confirm")
async def admin_reject_all_pending_confirm(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    db.refresh()
    pending = [t for t in db.transactions if t.get("status") == "pending"]
    if not pending:
        await callback.answer("Висящих заявок нет!", show_alert=True)
        return

    count = 0
    refunded_count = 0
    for t in pending:
        is_withdrawal = False
        t["status"] = "rejected"
        count += 1
        user_id = t.get("user_id")
        user_data = db.users.get(str(user_id)) if user_id else None

        # Return held funds/items if this was a withdrawal
        if isinstance(user_data, dict):
            ton_debited = float(t.get("ton_debited", 0) or 0)
            if ton_debited > 0:
                add_ton_balance(user_data, ton_debited)
                t["ton_debited"] = 0
                refunded_count += 1
                is_withdrawal = True
        if isinstance(user_data, dict) and t.get("held_at_creation"):
            is_withdrawal = True
            ttype = t.get("type")
            if ttype == "withdraw_ton":
                ton_amount = float(t.get("ton_amount", 0) or 0)
                if ton_amount > 0:
                    add_ton_balance(user_data, ton_amount)
                    refunded_count += 1
            elif ttype == "withdraw":
                stars = float(t.get("stars", 0) or 0)
                if stars > 0:
                    add_star_balance(user_data, stars)
                    refunded_count += 1
            elif ttype == "gift_withdraw":
                gift_data = t.get("gift_data")
                if isinstance(gift_data, dict):
                    inv = user_data.setdefault("miniapp_inventory", [])
                    if not isinstance(inv, list):
                        inv = []
                        user_data["miniapp_inventory"] = inv
                    gid = str(gift_data.get("id") or "")
                    if not any(str(x.get("id") or "") == gid for x in inv if isinstance(x, dict)):
                        inv.insert(0, gift_data)
                    refunded_count += 1
            t["held_at_creation"] = False

        if user_id:
            try:
                if is_withdrawal:
                    msg = (
                        "❌ <b>Заявка на вывод отклонена</b>\n\n"
                        "Средства возвращены на ваш баланс. По вопросам обратитесь в поддержку."
                    )
                else:
                    msg = (
                        "❌ <b>Заявка отклонена</b>\n\n"
                        "Ваша заявка отклонена администратором. По всем вопросам обратитесь в поддержку."
                    )
                await callback.bot.send_message(user_id, msg, parse_mode="HTML")
            except Exception:
                pass

    db.save_data()
    back_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ В админ-панель", callback_data="admin_panel_back")]]
    )
    refund_info = f"\n<i>Автоматически возвращено средств по {refunded_count} заявкам.</i>" if refunded_count else ""
    await safe_edit_message(
        callback,
        f"✅ <b>Успешно отклонено висящих заявок: {count} шт.</b>{refund_info}",
        reply_markup=back_keyboard,
        parse_mode="HTML",
    )
    await callback.answer(f"Отклонено: {count}")


@router.callback_query(F.data == "admin_panel_back")
async def admin_panel_back(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await safe_edit_message(
        callback,
        "⚙️ <b>Панель администратора</b>\n\n<i>Выберите раздел управления</i>",
        parse_mode="HTML",
        reply_markup=get_admin_panel_keyboard(),
    )
    await callback.answer()


@router.message(F.text.in_({"/reject_all", "/reject_all_pending", "❌ Отклонить все заявки"}))
async def cmd_reject_all_pending(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    db.refresh()
    pending = [t for t in db.transactions if t.get("status") == "pending"]
    if not pending:
        await message.answer("ℹ️ Висящих заявок нет.")
        return
    text = (
        f"⚠️ <b>Отклонение всех заявок</b>\n\n"
        f"Найдено висящих заявок: <b>{len(pending)}</b> шт.\n\n"
        f"Вы действительно хотите отклонить ВСЕ висящие заявки?\n"
        f"<i>Средства по заявкам на вывод будут автоматически возвращены пользователям.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, отклонить все", callback_data="admin_reject_all_pending_confirm"),
                InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_panel_back"),
            ]
        ]
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin_cards")
async def show_admin_cards(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет прав", show_alert=True)
        return
    data = load_cards_data()
    active = data.get('active_card', 1)
    c1 = data.get('card_1', '') or '(не задана)'
    c2 = data.get('card_2', '') or '(не задана)'
    text = (
        f"💳 <b>Управление картами Mono</b>\n\n"
        f"{'✅' if active == 1 else '⬜'} <b>Карта 1:</b> <code>{c1}</code>\n"
        f"{'✅' if active == 2 else '⬜'} <b>Карта 2:</b> <code>{c2}</code>\n\n"
        f"<i>Активная карта показывается клиентам при оплате.</i>"
    )
    rows = [
        [InlineKeyboardButton(text="🟢 Активировать карту 1", callback_data="admin_card_switch_1")],
        [InlineKeyboardButton(text="🟢 Активировать карту 2", callback_data="admin_card_switch_2")],
        [InlineKeyboardButton(text="✏️ Изменить карту 1", callback_data="admin_card_edit_1")],
        [InlineKeyboardButton(text="✏️ Изменить карту 2", callback_data="admin_card_edit_2")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel_back")],
    ]
    await safe_edit_message(callback, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.in_({"admin_card_switch_1", "admin_card_switch_2"}))
async def admin_card_switch(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет прав", show_alert=True)
        return
    idx = 1 if callback.data == "admin_card_switch_1" else 2
    set_active_card(idx)
    await callback.answer(f"✅ Карта {idx} активирована!", show_alert=True)
    await show_admin_cards(callback, state)


@router.callback_query(F.data.in_({"admin_card_edit_1", "admin_card_edit_2"}))
async def admin_card_edit_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет прав", show_alert=True)
        return
    idx = 1 if callback.data == "admin_card_edit_1" else 2
    await state.update_data(editing_card_index=idx)
    await state.set_state(CardAdminStates.editing_card_1 if idx == 1 else CardAdminStates.editing_card_2)
    await safe_edit_message(
        callback,
        f"✏️ <b>Введите новый номер карты {idx}:</b>\n<i>Например: 4874 0700 1234 5678</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CardAdminStates.editing_card_1)
@router.message(CardAdminStates.editing_card_2)
async def admin_card_edit_save(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    data = await state.get_data()
    idx = data.get('editing_card_index', 1)
    number = (message.text or '').strip()
    update_card_number(idx, number)
    await state.clear()
    await message.answer(
        f"✅ <b>Карта {idx} обновлена!</b>\n<code>{number}</code>",
        parse_mode="HTML",
        reply_markup=get_admin_panel_keyboard(),
    )
