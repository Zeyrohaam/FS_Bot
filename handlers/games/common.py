import asyncio
from uuid import uuid4
from datetime import datetime

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_IDS, GAMES_SETTINGS
from database import db
from keyboards.reply import main_menu, menu_with_back, purchases_menu, support_category_menu
from utils.helpers import add_star_balance, add_ton_balance, format_stars, get_numeric_balance, get_numeric_ton_balance, register_user_if_needed, safe_edit_message, sub_star_balance, sub_ton_balance

router = Router()

MINES_SETTINGS = GAMES_SETTINGS["mines"]
CRASH_SETTINGS = GAMES_SETTINGS["crash"]
DICE_SETTINGS = GAMES_SETTINGS["dice"]
ROULETTE_SETTINGS = GAMES_SETTINGS["roulette"]

GRID_SIZE = int(MINES_SETTINGS["grid_size"])
TOTAL_CELLS = GRID_SIZE * GRID_SIZE
MINES_COUNT = int(MINES_SETTINGS["mines_count"])
MIN_BET = float(MINES_SETTINGS["min_bet"])
MAX_BET = float(MINES_SETTINGS["max_bet"])
MINES_MULTIPLIERS = list(MINES_SETTINGS["multipliers"])
MAX_SAFE_CLICKS = len(MINES_MULTIPLIERS)

CRASH_MIN_BET = float(CRASH_SETTINGS["min_bet"])
CRASH_MAX_BET = float(CRASH_SETTINGS["max_bet"])
CRASH_MIN_X = float(CRASH_SETTINGS["min_x"])
CRASH_MAX_X = float(CRASH_SETTINGS["max_x"])
CRASH_TARGET_RTP = float(CRASH_SETTINGS["target_rtp"])

DICE_MIN_BET = float(DICE_SETTINGS["min_bet"])
DICE_MAX_BET = float(DICE_SETTINGS["max_bet"])
DICE_ROUNDS_OPTIONS = list(DICE_SETTINGS["rounds_options"])
DICE_SMALL_BANK_COMMISSION = float(DICE_SETTINGS["small_bank_commission"])
DICE_LARGE_BANK_COMMISSION = float(DICE_SETTINGS["large_bank_commission"])
DICE_SMALL_BANK_THRESHOLD = float(DICE_SETTINGS["small_bank_threshold"])

ROULETTE_MIN_BET = float(ROULETTE_SETTINGS["min_bet"])
ROULETTE_MAX_BET = float(ROULETTE_SETTINGS["max_bet"])
ROULETTE_GREEN_PAYOUT = float(ROULETTE_SETTINGS["green_payout"])
TON_MIN_BET = 0.2

CRASH_RUNTIME_TASKS: dict[int, asyncio.Task] = {}
DICE_QUEUE: dict[str, list[dict]] = {}
DICE_DUELS: dict[str, dict] = {}
DICE_ROOMS: dict[str, dict] = {}


class GameStates(StatesGroup):
    waiting_mines_currency = State()
    waiting_mines_bet = State()
    waiting_crash_currency = State()
    waiting_crash_bet = State()
    waiting_crash_auto_x = State()
    waiting_dice_currency = State()
    waiting_dice_rounds = State()
    waiting_dice_bet = State()
    waiting_roulette_currency = State()
    waiting_roulette_bet = State()


class CrashRoundEnded(Exception):
    pass


def _get_user_data(user_id: int, username: str | None = None):
    return register_user_if_needed(user_id, username)


def _currency_info(currency: str) -> tuple[str, str]:
    mapping = {"stars": ("⭐️", "звёздах"), "ton": ("TON", "TON")}
    return mapping.get(currency, ("⭐️", "звёздах"))


def _get_currency_balance(user_data: dict, currency: str) -> float:
    if currency == "ton":
        return get_numeric_ton_balance(user_data)
    return get_numeric_balance(user_data)


def _add_currency_balance(user_data: dict, currency: str, amount: float):
    if currency == "ton":
        add_ton_balance(user_data, amount)
    else:
        add_star_balance(user_data, amount)


def _sub_currency_balance(user_data: dict, currency: str, amount: float):
    if currency == "ton":
        sub_ton_balance(user_data, amount)
    else:
        sub_star_balance(user_data, amount)


def _parse_game_bet(raw_value: str | None) -> float:
    raw = (raw_value or '').strip().replace(',', '.')
    if not raw:
        raise ValueError('empty')
    if raw.count('.') > 1:
        raise ValueError('format')
    if '.' in raw:
        whole, frac = raw.split('.', 1)
        if not whole.isdigit() or not frac.isdigit() or len(frac) != 1:
            raise ValueError('format')
    elif not raw.isdigit():
        raise ValueError('format')
    return round(float(raw), 1)


def _currency_choice_keyboard(user_data: dict, game_name: str) -> InlineKeyboardMarkup:
    rows = []
    prefix_map = {"mines": "mines", "crash": "crash", "dice": "dice", "roulette": "roulette"}
    prefix = prefix_map.get(game_name, "mines")
    if get_numeric_balance(user_data) > 0:
        rows.append([InlineKeyboardButton(text=f"⭐️ Играть звёздами ({format_stars(get_numeric_balance(user_data))})", callback_data=f"{prefix}_currency_stars")])
    if get_numeric_ton_balance(user_data) > 0:
        rows.append([InlineKeyboardButton(text=f"💠 Играть TON ({format_stars(get_numeric_ton_balance(user_data))})", callback_data=f"{prefix}_currency_ton")])
    return InlineKeyboardMarkup(inline_keyboard=rows or [[InlineKeyboardButton(text="❌ Нет доступного баланса", callback_data="games_no_balance")]])


def _default_user_game_stats() -> dict:
    return {
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "total_bet": 0,
        "total_won": 0,
        "biggest_win": 0,
    }


def _default_global_game_stats(game_type: str | None = None) -> dict:
    stats = {
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "total_bet": 0,
        "total_paid_out": 0,
        "net_profit": 0,
    }
    if game_type == "crash":
        stats["last_round_number"] = 0
    return stats


def _ensure_stats_dict(target: dict | None, defaults: dict) -> dict:
    stats = target if isinstance(target, dict) else {}
    for key, value in defaults.items():
        stats.setdefault(key, value)
    return stats


def _get_user_game_stats(user_data: dict, game_name: str) -> dict:
    games = user_data.setdefault("games", {})
    stats = _ensure_stats_dict(games.get(game_name), _default_user_game_stats())
    games[game_name] = stats
    return stats


def _get_global_game_stats(game_name: str) -> dict:
    stats = _ensure_stats_dict(db.game_stats.get(game_name), _default_global_game_stats(game_name))
    db.game_stats[game_name] = stats
    if game_name == "crash":
        stats.setdefault("last_round_number", 0)
    return stats


def _get_user_mines_stats(user_data: dict) -> dict:
    return _get_user_game_stats(user_data, "mines")


def _get_user_crash_stats(user_data: dict) -> dict:
    return _get_user_game_stats(user_data, "crash")


def _get_global_mines_stats() -> dict:
    return _get_global_game_stats("mines")


def _get_user_roulette_stats(user_data: dict) -> dict:
    return _get_user_game_stats(user_data, "roulette")


def _get_global_roulette_stats() -> dict:
    return _get_global_game_stats("roulette")


def _get_global_crash_stats() -> dict:
    return _get_global_game_stats("crash")


def _get_active_game(user_data: dict) -> dict | None:
    current_game = user_data.get("current_game")
    return current_game if isinstance(current_game, dict) else None


def _build_games_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💣 Мины", callback_data="game_mines")],
            [InlineKeyboardButton(text="📈 Crash", callback_data="game_crash")],
            [InlineKeyboardButton(text="🎲 Кубы 1v1", callback_data="game_dice_duel")],
            [InlineKeyboardButton(text="🎡 Рулетка", callback_data="game_roulette")],
        ]
    )


def _build_crash_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Обычный раунд", callback_data="crash_mode_manual")],
            [InlineKeyboardButton(text="⚙️ Автовывод", callback_data="crash_mode_auto")],
        ]
    )


def _normalize_crash_auto_x(value: float) -> float:
    normalized = round(float(value), 2)
    if normalized < CRASH_MIN_X:
        return CRASH_MIN_X
    if normalized > CRASH_MAX_X:
        return CRASH_MAX_X
    return normalized


def _build_crash_autox_hint() -> str:
    return f"от {CRASH_MIN_X:.2f}x до {CRASH_MAX_X:.2f}x, например 1.25x • 2.73x • 7.92x"


def _build_dice_rounds_keyboard() -> InlineKeyboardMarkup:
    labels = {1: "быстрая", 3: "классика", 5: "марафон"}
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{rounds} — {labels.get(rounds, 'матч')}", callback_data=f"dice_rounds_{rounds}")]
            for rounds in DICE_ROUNDS_OPTIONS
        ]
    )


def _build_dice_waiting_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отменить поиск", callback_data="dice_cancel_search")]])


def _build_dice_duel_info_text(duel: dict, viewer_id: int) -> str:
    player_ids = duel.get("players", [])
    opponent_id = player_ids[1] if player_ids and player_ids[0] == viewer_id and len(player_ids) > 1 else player_ids[0]
    opponent = _get_user_data(opponent_id)
    currency = duel.get("currency", "stars")
    symbol, _ = _currency_info(currency)
    my_roll = duel.get("rolls", {}).get(str(viewer_id))
    opp_roll = duel.get("rolls", {}).get(str(opponent_id))
    rounds_total = int(duel.get("rounds_total", 1) or 1)
    current_round = int(duel.get("current_round", 1) or 1)
    scores = duel.get("scores", {})
    my_score = int(scores.get(str(viewer_id), 0) or 0)
    opp_score = int(scores.get(str(opponent_id), 0) or 0)
    return (
        "🎲 Кубы 1v1\n\n"
        f"🆚 Соперник: @{opponent.get('username', 'unknown')} (ID: {opponent_id})\n"
        f"🎯 Ставка каждого: {format_stars(duel.get('bet', 0))} {symbol}\n"
        f"🏆 Общий банк: {format_stars(float(duel.get('bet', 0)) * 2)} {symbol}\n"
        f"📚 Формат: {rounds_total} раунд(ах)\n"
        f"🔢 Текущий раунд: {current_round}/{rounds_total}\n"
        f"📊 Счёт: {my_score}:{opp_score}\n\n"
        "Отправьте СВОЙ кубик 🎲 прямо в этот чат с ботом.\n"
        "Пересланные кубики не засчитываются.\n\n"
        f"Ваш бросок: {my_roll if my_roll is not None else 'ещё нет'}\n"
        f"Бросок соперника: {opp_roll if opp_roll is not None else 'ещё нет'}"
    )


def _find_waiting_duel_opponent(user_id: int, currency: str, bet: float, rounds_total: int):
    key = f"{currency}:{round(float(bet), 2):.2f}:{int(rounds_total)}"
    queue = DICE_QUEUE.setdefault(key, [])
    for i, entry in enumerate(queue):
        if int(entry.get("user_id", 0)) != user_id:
            return key, queue.pop(i)
    return key, None


def _remove_from_dice_queue(user_id: int):
    for key, queue in list(DICE_QUEUE.items()):
        for i, entry in enumerate(list(queue)):
            if int(entry.get("user_id", 0)) == user_id:
                queue.pop(i)
                if not queue:
                    DICE_QUEUE.pop(key, None)
                return entry
    return None


def _create_dice_room(user_id: int, currency: str, bet: float, rounds_total: int) -> str:
    room_id = uuid4().hex[:10]
    DICE_ROOMS[room_id] = {
        "room_id": room_id,
        "owner_id": user_id,
        "currency": currency,
        "bet": float(bet),
        "rounds_total": int(rounds_total),
        "status": "waiting",
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    return room_id


def _remove_dice_room(room_id: str | None):
    if room_id:
        DICE_ROOMS.pop(room_id, None)


def _required_dice_wins(rounds_total: int) -> int:
    return int(rounds_total // 2) + 1


def _build_dice_invite_link(bot_username: str | None, room_id: str) -> str | None:
    if not bot_username:
        return None
    return f"https://t.me/{bot_username}?start=dice_{room_id}"


def _build_dice_waiting_text(bet: float, symbol: str, rounds_total: int, invite_link: str | None = None) -> str:
    lines = [
        "⏳ Поиск соперника...",
        "",
        f"🎯 Ваша ставка: {format_stars(bet)} {symbol}",
        f"📚 Формат: {rounds_total} раунд(ах)",
        "Как только найдётся второй игрок с такой же ставкой, валютой и форматом матча, бот начнёт матч.",
    ]
    if invite_link:
        lines.extend(["", "🔗 Личная ссылка для входа в игру:", invite_link])
    return "\n".join(lines)


def _is_forwarded_message(message: Message) -> bool:
    return bool(getattr(message, "forward_origin", None) or getattr(message, "forward_date", None))


async def _handle_waiting_navigation(message: Message, state: FSMContext, back_target: str) -> bool:
    text = (message.text or '').strip()
    if not text:
        return False

    async def _go_main_menu():
        await state.clear()
        await message.answer("Выберите действие", reply_markup=main_menu(message.from_user.id in ADMIN_IDS))

    if text == "⬅️ Назад":
        data = await state.get_data()
        await state.clear()
        if back_target == "games":
            from .menu import show_games_menu
            await show_games_menu(message)
            return True
        if back_target == "crash_mode":
            bet = data.get("crash_bet")
            currency = data.get("game_currency", "stars")
            symbol, _ = _currency_info(currency)
            if bet:
                await state.update_data(crash_bet=bet, game_currency=currency)
                await message.answer(
                    "📈 Crash\n\n"
                    f"🎲 Ставка: {format_stars(bet)} {symbol}\n"
                    "Выберите режим раунда:\n\n"
                    "• Обычный — сами нажимаете «Забрать»\n"
                    "• Автовывод — бот сам заберёт на выбранном x",
                    reply_markup=_build_crash_mode_keyboard(),
                )
                return True
        await _go_main_menu()
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
    if text == "🛍️ Покупки":
        await state.clear()
        await message.answer("🛍️ Покупки\n\nВыберите, что хотите открыть:", reply_markup=purchases_menu(message.from_user.id in ADMIN_IDS))
        return True
    if text == "🆘 Поддержка":
        await state.clear()
        await message.answer("🆘 Раздел поддержки. Выберите действие:", reply_markup=support_category_menu(message.from_user.id in ADMIN_IDS))
        return True
    if text == "📣 Отзывы":
        await state.clear()
        from handlers.reviews import show_reviews_menu
        await show_reviews_menu(message)
        return True
    if text == "🧮 Посчитать":
        await state.clear()
        from handlers.calculator import show_calculator_menu
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
    if text == "👥 Рефералы":
        await state.clear()
        from handlers.user import referrals_message_handler
        await referrals_message_handler(message)
        return True
    if text == "🎮 Игры":
        await state.clear()
        from .menu import show_games_menu
        await show_games_menu(message)
        return True
    if text == "⚙️ Админ-панель" and message.from_user.id in ADMIN_IDS:
        await state.clear()
        from handlers.admin import admin_panel
        await admin_panel(message)
        return True

    return False
