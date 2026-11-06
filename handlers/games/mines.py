import random
from datetime import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from .common import (
    ADMIN_IDS,
    GRID_SIZE,
    MAX_BET,
    MAX_SAFE_CLICKS,
    MINES_COUNT,
    MINES_MULTIPLIERS,
    MIN_BET,
    TON_MIN_BET,
    TOTAL_CELLS,
    GameStates,
    _add_currency_balance,
    _currency_choice_keyboard,
    _currency_info,
    _get_active_game,
    _get_currency_balance,
    _get_global_mines_stats,
    _get_user_data,
    _get_user_mines_stats,
    _handle_waiting_navigation,
    _parse_game_bet,
    _sub_currency_balance,
    db,
    format_stars,
    menu_with_back,
    router,
    safe_edit_message,
)


def _format_amount_by_step(bet: float, safe_clicks: int) -> int:
    if safe_clicks <= 0:
        return int(round(bet))
    multiplier = MINES_MULTIPLIERS[min(safe_clicks, MAX_SAFE_CLICKS) - 1]
    return int(round(bet * multiplier))


def _current_multiplier(game: dict) -> float:
    safe_clicks = int(game.get("safe_clicks", 0) or 0)
    if safe_clicks <= 0:
        return 1.0
    return float(MINES_MULTIPLIERS[min(safe_clicks, MAX_SAFE_CLICKS) - 1])


def _next_multiplier(game: dict) -> float | None:
    safe_clicks = int(game.get("safe_clicks", 0) or 0)
    if safe_clicks >= MAX_SAFE_CLICKS:
        return None
    return float(MINES_MULTIPLIERS[safe_clicks])


def _build_mines_keyboard(game: dict, game_over: bool = False, exploded_idx: int | None = None) -> InlineKeyboardMarkup:
    rows = []
    opened = set(game.get("opened_cells", []))
    mines = set(game.get("mines", []))

    for row in range(GRID_SIZE):
        current_row = []
        for col in range(GRID_SIZE):
            idx = row * GRID_SIZE + col
            if exploded_idx is not None and idx == exploded_idx:
                text = "💥"
                callback_data = "mines_ignore"
            elif idx in opened:
                text = "✅"
                callback_data = "mines_ignore"
            elif game_over and idx in mines:
                text = "💣"
                callback_data = "mines_ignore"
            elif game_over:
                text = "▫️"
                callback_data = "mines_ignore"
            else:
                text = "🟦"
                callback_data = f"mines_open_{idx}"
            current_row.append(InlineKeyboardButton(text=text, callback_data=callback_data))
        rows.append(current_row)

    symbol, _ = _currency_info(game.get("currency", "stars"))
    if not game_over and int(game.get("safe_clicks", 0) or 0) < MAX_SAFE_CLICKS:
        payout = float(game.get("current_amount", 0) or 0)
        multiplier = _current_multiplier(game)
        rows.append([InlineKeyboardButton(text=f"💰 Забрать {format_stars(payout)} {symbol} ({multiplier:.2f}x)", callback_data="mines_cashout")])
    elif not game_over:
        payout = float(game.get("current_amount", 0) or 0)
        rows.append([InlineKeyboardButton(text=f"🏆 Максимум: забрать {format_stars(payout)} {symbol}", callback_data="mines_cashout")])
    else:
        rows.append([InlineKeyboardButton(text="🎮 Сыграть ещё", callback_data="game_mines")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_progress_line(game: dict) -> str:
    safe_clicks = int(game.get("safe_clicks", 0) or 0)
    parts = []
    for i, mult in enumerate(MINES_MULTIPLIERS, start=1):
        if i < safe_clicks:
            parts.append(f"✅ {mult:.2f}x")
        elif i == safe_clicks and safe_clicks > 0:
            parts.append(f"🔷 {mult:.2f}x")
        else:
            parts.append(f"▫️ {mult:.2f}x")
    return "\n".join(parts)


def _build_mines_status_text(game: dict, title: str, subtitle: str | None = None) -> str:
    bet = float(game.get("bet", 0) or 0)
    payout = float(game.get("current_amount", 0) or 0)
    safe_clicks = int(game.get("safe_clicks", 0) or 0)
    current_multiplier = _current_multiplier(game)
    next_multiplier = _next_multiplier(game)
    next_text = f"{next_multiplier:.2f}x" if next_multiplier is not None else "максимальный этап"
    symbol, _ = _currency_info(game.get("currency", "stars"))

    lines = [
        title,
        "",
        f"🎲 Ставка: {format_stars(bet)} {symbol}",
        f"📈 Текущий множитель: {current_multiplier:.2f}x",
        f"💎 Можно забрать: {format_stars(payout)} {symbol}",
        f"🟩 Безопасных клеток открыто: {safe_clicks}/{MAX_SAFE_CLICKS}",
        f"⏭ Следующий этап: {next_text}",
    ]
    if subtitle:
        lines.extend(["", subtitle])
    lines.extend(["Нажимай на синюю клетку или забирай выигрыш."])
    return "\n".join(lines)


@router.callback_query(F.data == "game_mines")
async def start_mines_game(callback: CallbackQuery, state: FSMContext):
    user_data = _get_user_data(callback.from_user.id, callback.from_user.username)
    current_game = _get_active_game(user_data)
    if current_game:
        await callback.answer("Сначала завершите текущую игру", show_alert=True)
        return

    await state.clear()
    await state.set_state(GameStates.waiting_mines_currency)
    await safe_edit_message(
        callback,
        "💣 Мины\n\n"
        f"🧨 Поле: {GRID_SIZE}x{GRID_SIZE}\n"
        f"💣 Мин на поле: {MINES_COUNT}\n"
        f"🎯 Ставка: от {format_stars(MIN_BET)} до {format_stars(MAX_BET)}\n\n"
        "📈 Иксы по этапам:\n"
        + " → ".join(f"{x:.2f}x" for x in MINES_MULTIPLIERS)
        + "\n\nВыберите валюту для игры:",
        reply_markup=_currency_choice_keyboard(user_data, "mines"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mines_currency_"))
async def mines_currency_selected(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.split("_")[-1]
    user_data = _get_user_data(callback.from_user.id, callback.from_user.username)
    balance = _get_currency_balance(user_data, currency)
    symbol, label = _currency_info(currency)
    await state.update_data(game_currency=currency)
    await state.set_state(GameStates.waiting_mines_bet)
    min_bet = TON_MIN_BET if currency == 'ton' else MIN_BET
    await safe_edit_message(
        callback,
        "💣 Мины\n\n"
        f"💎 Ваш баланс: {format_stars(balance)} {symbol}\n"
        f"🎯 Ставка: от {format_stars(min_bet)} до {format_stars(MAX_BET)} {symbol}\n\n"
        + f"\n\nВведите ставку в {label}:",
        reply_markup=menu_with_back(callback.from_user.id in ADMIN_IDS),
    )
    await callback.answer()


@router.message(GameStates.waiting_mines_bet)
async def process_mines_bet(message: Message, state: FSMContext):
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
        await message.answer("❌ Введите ставку числом. Можно целое или с одной цифрой после точки, например: 10 или 10.5")
        return

    min_bet = TON_MIN_BET if currency == 'ton' else MIN_BET
    if bet < min_bet or bet > MAX_BET:
        await message.answer(f"❌ Ставка должна быть от {format_stars(min_bet)} до {format_stars(MAX_BET)} {symbol}")
        return
    if bet > balance:
        await message.answer(f"❌ Недостаточно средств на балансе. Доступно: {format_stars(balance)} {symbol}")
        return

    mines = sorted(random.sample(range(TOTAL_CELLS), MINES_COUNT))
    _sub_currency_balance(user_data, currency, bet)
    user_data["current_game"] = {
        "type": "mines",
        "bet": bet,
        "current_amount": bet,
        "mines": mines,
        "opened_cells": [],
        "safe_clicks": 0,
        "started_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "currency": currency,
    }
    db.save_data()
    await state.clear()

    game = user_data["current_game"]
    await message.answer(_build_mines_status_text(game, "💣 Игра началась", "Выбери первую клетку. Один неудачный клик — и ставка сгорит."), reply_markup=_build_mines_keyboard(game))


@router.callback_query(F.data == "mines_ignore")
async def ignore_mines_click(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("mines_open_"))
async def open_mines_cell(callback: CallbackQuery):
    user_data = _get_user_data(callback.from_user.id, callback.from_user.username)
    game = _get_active_game(user_data)
    if not game or game.get("type") != "mines":
        await callback.answer("❌ Активная игра не найдена", show_alert=True)
        return

    idx = int(callback.data.split("_")[-1])
    opened = set(game.get("opened_cells", []))
    mines = set(game.get("mines", []))

    if idx in opened:
        await callback.answer()
        return

    if idx in mines:
        bet = float(game.get("bet", 0) or 0)
        payout = float(game.get("current_amount", 0) or 0)
        currency = game.get("currency", "stars")
        symbol, _ = _currency_info(currency)
        user_stats = _get_user_mines_stats(user_data)
        global_stats = _get_global_mines_stats()
        user_stats["games_played"] += 1
        user_stats["losses"] += 1
        user_stats["total_bet"] += bet
        global_stats["games_played"] += 1
        global_stats["losses"] += 1
        global_stats["total_bet"] += bet
        global_stats["net_profit"] = round(float(global_stats["total_bet"]) - float(global_stats["total_paid_out"]), 2)
        user_data.pop("current_game", None)
        from utils.tournaments import record_game_event
        record_game_event(callback.from_user.id, "mines", bet, 0, currency, won=False)
        db.save_data()
        await safe_edit_message(callback, "💥 Вы попали на мину!\n\n" f"🎲 Ставка сгорела: {format_stars(bet)} {symbol}\n" f"📈 Последний достигнутый множитель: {_current_multiplier(game):.2f}x\n" f"💎 Потенциальный выигрыш на момент проигрыша: {format_stars(payout)} {symbol}", reply_markup=_build_mines_keyboard(game, game_over=True, exploded_idx=idx))
        await callback.answer("💥 Мина!")
        return

    opened.add(idx)
    safe_clicks = int(game.get("safe_clicks", 0) or 0) + 1
    new_amount = _format_amount_by_step(float(game.get("bet", 0) or 0), safe_clicks)
    game["opened_cells"] = sorted(opened)
    game["safe_clicks"] = safe_clicks
    game["current_amount"] = new_amount
    db.save_data()

    symbol, _ = _currency_info(game.get("currency", "stars"))
    if safe_clicks >= MAX_SAFE_CLICKS:
        await safe_edit_message(callback, _build_mines_status_text(game, "🏆 Максимальный этап достигнут", f"Ты дошёл до {MAX_SAFE_CLICKS} безопасных открытий. Теперь можно только забрать {format_stars(new_amount)} {symbol}."), reply_markup=_build_mines_keyboard(game))
        await callback.answer("🏆 Максимальный x достигнут")
        return

    await safe_edit_message(callback, _build_mines_status_text(game, "✅ Безопасная клетка", f"Новый выигрыш: {format_stars(new_amount)} {symbol} • текущий x: {_current_multiplier(game):.2f}x"), reply_markup=_build_mines_keyboard(game))
    await callback.answer(f"✅ {_current_multiplier(game):.2f}x")


@router.callback_query(F.data == "mines_cashout")
async def cashout_mines(callback: CallbackQuery):
    user_data = _get_user_data(callback.from_user.id, callback.from_user.username)
    game = user_data.pop("current_game", None)
    if not game or game.get("type") != "mines":
        await callback.answer("❌ Активная игра не найдена", show_alert=True)
        return

    bet = float(game.get("bet", 0) or 0)
    payout = float(game.get("current_amount", 0) or 0)
    currency = game.get("currency", "stars")
    symbol, _ = _currency_info(currency)
    _add_currency_balance(user_data, currency, payout)

    user_stats = _get_user_mines_stats(user_data)
    global_stats = _get_global_mines_stats()
    user_stats["games_played"] += 1
    user_stats["wins"] += 1
    user_stats["total_bet"] += bet
    user_stats["total_won"] += payout
    if payout > float(user_stats.get("biggest_win", 0) or 0):
        user_stats["biggest_win"] = payout
    global_stats["games_played"] += 1
    global_stats["wins"] += 1
    global_stats["total_bet"] += bet
    global_stats["total_paid_out"] += payout
    global_stats["net_profit"] = round(float(global_stats["total_bet"]) - float(global_stats["total_paid_out"]), 2)

    from utils.tournaments import record_game_event
    record_game_event(callback.from_user.id, "mines", bet, payout, currency, won=True)
    db.save_data()
    await safe_edit_message(callback, "💰 Вы забрали выигрыш\n\n" f"🎲 Ставка: {format_stars(bet)} {symbol}\n" f"📈 Итоговый множитель: {_current_multiplier(game):.2f}x\n" f"💵 Начислено: {format_stars(payout)} {symbol}\n" f"🏦 Новый баланс: {format_stars(_get_currency_balance(user_data, currency))} {symbol}", reply_markup=_build_mines_keyboard(game, game_over=True))
    await callback.answer("💰 Забрано")
