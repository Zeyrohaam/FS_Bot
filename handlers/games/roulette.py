import asyncio
import random
from datetime import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from .common import (
    ADMIN_IDS,
    ROULETTE_GREEN_PAYOUT,
    ROULETTE_MIN_BET,
    ROULETTE_MAX_BET,
    GameStates,
    _add_currency_balance,
    _currency_choice_keyboard,
    _currency_info,
    _get_active_game,
    _get_currency_balance,
    _get_global_roulette_stats,
    _get_user_data,
    _get_user_roulette_stats,
    _handle_waiting_navigation,
    _parse_game_bet,
    _sub_currency_balance,
    db,
    format_stars,
    menu_with_back,
    router,
    safe_edit_message,
    TON_MIN_BET,
)

ROULETTE_RED_EMOJI = "🔴"
ROULETTE_WHITE_EMOJI = "⚪️"
ROULETTE_GREEN_EMOJI = "🟢"
ROULETTE_RED_PAYOUT = 2.0
ROULETTE_WHITE_PAYOUT = 2.0


def _roulette_color_label(color: str) -> str:
    return {
        "red": f"{ROULETTE_RED_EMOJI} Красное",
        "white": f"{ROULETTE_WHITE_EMOJI} Белое",
        "green": f"{ROULETTE_GREEN_EMOJI} Зелёное",
    }.get(color, color)


def _roulette_color_emoji(color: str) -> str:
    return {
        "red": ROULETTE_RED_EMOJI,
        "white": ROULETTE_WHITE_EMOJI,
        "green": ROULETTE_GREEN_EMOJI,
    }.get(color, "🎯")


def _roulette_payout_multiplier(color: str) -> float:
    if color == "green":
        return float(ROULETTE_GREEN_PAYOUT)
    return ROULETTE_RED_PAYOUT if color == "red" else ROULETTE_WHITE_PAYOUT


def _build_roulette_color_keyboard(game: dict) -> InlineKeyboardMarkup:
    bet = float(game.get("bet", 0) or 0)
    currency = game.get("currency", "stars")
    symbol, _ = _currency_info(currency)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"{ROULETTE_RED_EMOJI} Красное x{ROULETTE_RED_PAYOUT:.0f}", callback_data="roulette_pick_red"),
                InlineKeyboardButton(text=f"{ROULETTE_WHITE_EMOJI} Белое x{ROULETTE_WHITE_PAYOUT:.0f}", callback_data="roulette_pick_white"),
            ],
            [
                InlineKeyboardButton(
                    text=f"{ROULETTE_GREEN_EMOJI} Зелёное x{ROULETTE_GREEN_PAYOUT:g}",
                    callback_data="roulette_pick_green",
                )
            ],
            [InlineKeyboardButton(text=f"💰 Ставка: {format_stars(bet)} {symbol}", callback_data="roulette_ignore")],
        ]
    )


async def _animate_roulette(callback: CallbackQuery, game: dict, chosen_color: str) -> str:
    frames = [
        ["red", "white", "red", "white", "green"],
        ["white", "red", "white", "red", "green"],
        ["red", "green", "white", "red", "white"],
        ["white", "red", "green", "white", "red"],
    ]
    for frame in frames:
        frame_text = " ".join(_roulette_color_emoji(item) for item in frame)
        await safe_edit_message(
            callback,
            "🎡 Рулетка\n\n"
            f"🎯 Ваша ставка: {format_stars(game.get('bet', 0))} {_currency_info(game.get('currency', 'stars'))[0]}\n"
            f"🧷 Ваш выбор: {_roulette_color_label(chosen_color)}\n\n"
            f"Крутим...\n{frame_text}",
        )
        await asyncio.sleep(0.35)

    roll = random.randint(1, 30)
    if roll == 30:
        return "green"
    return random.choice(["red", "white"])


@router.callback_query(F.data == "game_roulette")
async def start_roulette_game(callback: CallbackQuery, state: FSMContext):
    user_data = _get_user_data(callback.from_user.id, callback.from_user.username)
    current_game = _get_active_game(user_data)
    if current_game:
        await callback.answer("Сначала завершите текущую игру", show_alert=True)
        return

    await state.clear()
    await state.set_state(GameStates.waiting_roulette_currency)
    await safe_edit_message(
        callback,
        "🎡 Рулетка\n\n"
        f"🎯 Ставка: от {format_stars(ROULETTE_MIN_BET)} до {format_stars(ROULETTE_MAX_BET)}\n"
        f"🔴 Красное — x{ROULETTE_RED_PAYOUT:.0f}\n"
        f"⚪️ Белое — x{ROULETTE_WHITE_PAYOUT:.0f}\n"
        f"🟢 Зелёное — x{ROULETTE_GREEN_PAYOUT:g}\n"
        "🟢 Зелёное выпадает примерно 1 раз на 30 спинов.\n\n"
        "Выберите валюту для игры:",
        reply_markup=_currency_choice_keyboard(user_data, "roulette"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("roulette_currency_"))
async def roulette_currency_selected(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.split("_")[-1]
    user_data = _get_user_data(callback.from_user.id, callback.from_user.username)
    balance = _get_currency_balance(user_data, currency)
    symbol, label = _currency_info(currency)
    await state.update_data(game_currency=currency)
    await state.set_state(GameStates.waiting_roulette_bet)
    min_bet = TON_MIN_BET if currency == 'ton' else ROULETTE_MIN_BET
    await safe_edit_message(
        callback,
        "🎡 Рулетка\n\n"
        f"💎 Ваш баланс: {format_stars(balance)} {symbol}\n"
        f"🎯 Ставка: от {format_stars(min_bet)} до {format_stars(ROULETTE_MAX_BET)} {symbol}\n\n"
        f"Введите ставку в {label}:",
        reply_markup=menu_with_back(callback.from_user.id in ADMIN_IDS),
    )
    await callback.answer()


@router.message(GameStates.waiting_roulette_bet)
async def process_roulette_bet(message: Message, state: FSMContext):
    if await _handle_waiting_navigation(message, state, "games"):
        return

    user_data = _get_user_data(message.from_user.id, message.from_user.username)
    data = await state.get_data()
    currency = data.get("game_currency", "stars")
    symbol, _ = _currency_info(currency)
    balance = _get_currency_balance(user_data, currency)

    try:
        bet = _parse_game_bet(message.text)
    except Exception:
        await message.answer("❌ Введите ставку числом. Например: 10 или 10.5")
        return

    min_bet = TON_MIN_BET if currency == 'ton' else ROULETTE_MIN_BET
    if bet < min_bet or bet > ROULETTE_MAX_BET:
        await message.answer(f"❌ Ставка должна быть от {format_stars(min_bet)} до {format_stars(ROULETTE_MAX_BET)} {symbol}")
        return
    if bet > balance:
        await message.answer(f"❌ Недостаточно средств. Доступно: {format_stars(balance)} {symbol}")
        return

    _sub_currency_balance(user_data, currency, bet)
    user_data["current_game"] = {
        "type": "roulette",
        "bet": bet,
        "currency": currency,
        "started_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    db.save_data()
    await state.clear()

    await message.answer(
        "🎡 Рулетка\n\n"
        f"🎯 Ставка принята: {format_stars(bet)} {symbol}\n"
        "Теперь выберите цвет кнопкой ниже:",
        reply_markup=_build_roulette_color_keyboard(user_data["current_game"]),
    )


@router.callback_query(F.data == "roulette_ignore")
async def ignore_roulette_click(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("roulette_pick_"))
async def roulette_pick_color(callback: CallbackQuery):
    user_data = _get_user_data(callback.from_user.id, callback.from_user.username)
    game = user_data.pop("current_game", None)
    if not game or game.get("type") != "roulette":
        await callback.answer("❌ Активная игра не найдена", show_alert=True)
        return

    chosen_color = callback.data.rsplit("_", 1)[-1]
    if chosen_color not in {"red", "white", "green"}:
        user_data["current_game"] = game
        await callback.answer()
        return

    if game.get("picked_color"):
        await callback.answer("Цвет уже выбран", show_alert=True)
        return

    game["picked_color"] = chosen_color
    db.save_data()

    result_color = await _animate_roulette(callback, game, chosen_color)

    currency = game.get("currency", "stars")
    symbol, _ = _currency_info(currency)
    bet = float(game.get("bet", 0) or 0)
    payout_multiplier = _roulette_payout_multiplier(chosen_color)
    won = chosen_color == result_color
    payout = round(bet * payout_multiplier, 1) if won else 0.0

    user_stats = _get_user_roulette_stats(user_data)
    global_stats = _get_global_roulette_stats()
    user_stats["games_played"] += 1
    user_stats["total_bet"] += bet
    global_stats["games_played"] += 1
    global_stats["total_bet"] += bet

    if won:
        _add_currency_balance(user_data, currency, payout)
        user_stats["wins"] += 1
        user_stats["total_won"] += payout
        user_stats["biggest_win"] = max(float(user_stats.get("biggest_win", 0) or 0), payout)
        global_stats["wins"] += 1
        global_stats["total_paid_out"] += payout
        result_title = "🎉 Вы выиграли!"
        result_body = (
            f"🎯 Ваша ставка: {format_stars(bet)} {symbol}\n"
            f"🧷 Ваш цвет: {_roulette_color_label(chosen_color)}\n"
            f"🎡 Выпало: {_roulette_color_label(result_color)}\n"
            f"💰 Выплата: {format_stars(payout)} {symbol}\n"
            f"🏦 Новый баланс: {format_stars(_get_currency_balance(user_data, currency))} {symbol}"
        )
    else:
        user_stats["losses"] += 1
        global_stats["losses"] += 1
        result_title = "😔 Вы проиграли"
        result_body = (
            f"🎯 Ваша ставка: {format_stars(bet)} {symbol}\n"
            f"🧷 Ваш цвет: {_roulette_color_label(chosen_color)}\n"
            f"🎡 Выпало: {_roulette_color_label(result_color)}\n"
            f"💸 Ставка сгорела: {format_stars(bet)} {symbol}"
        )

    global_stats["net_profit"] = round(float(global_stats["total_bet"]) - float(global_stats["total_paid_out"]), 2)
    from utils.tournaments import record_game_event
    record_game_event(callback.from_user.id, "roulette", bet, payout, currency, won=won)

    recent_games = user_data.setdefault("recent_games", [])
    recent_games.append({
        "game": "roulette",
        "result": "win" if won else "loss",
        "bet": bet,
        "payout": payout,
        "x": payout_multiplier if won else 0,
        "picked_color": chosen_color,
        "result_color": result_color,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
    })
    if len(recent_games) > 20:
        del recent_games[:-20]

    user_data.pop("current_game", None)
    db.save_data()

    await safe_edit_message(
        callback,
        f"{result_title}\n\n{result_body}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🎮 Сыграть ещё", callback_data="game_roulette")]]
        ),
    )
    await callback.answer()
