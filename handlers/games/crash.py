import asyncio
import random
from datetime import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from .common import (
    ADMIN_IDS,
    CRASH_MAX_BET,
    CRASH_MAX_X,
    CRASH_MIN_BET,
    CRASH_MIN_X,
    CRASH_RUNTIME_TASKS,
    CRASH_TARGET_RTP,
    CrashRoundEnded,
    GameStates,
    _add_currency_balance,
    _build_crash_autox_hint,
    _build_crash_mode_keyboard,
    _currency_choice_keyboard,
    _currency_info,
    _get_active_game,
    _get_currency_balance,
    _get_global_crash_stats,
    _get_user_crash_stats,
    _get_user_data,
    _handle_waiting_navigation,
    _normalize_crash_auto_x,
    _parse_game_bet,
    _sub_currency_balance,
    db,
    format_stars,
    menu_with_back,
    router,
    safe_edit_message,
    TON_MIN_BET,
)
from utils.tournaments import record_game_event


def _crash_step(current_x: float) -> float:
    if current_x < 1.45:
        return 0.01
    if current_x < 3.50:
        return 0.02
    return 0.04


def _next_crash_x(current_x: float) -> float:
    return min(CRASH_MAX_X, round(float(current_x) + _crash_step(float(current_x)), 2))


def _crash_tick_delay(current_x: float) -> float:
    if current_x < 1.45:
        return 0.16
    if current_x < 3.50:
        return 0.12
    return 0.09


def _build_crash_keyboard(game: dict, game_over: bool = False) -> InlineKeyboardMarkup:
    if game_over:
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎮 Сыграть ещё", callback_data="game_crash")]])
    payout = round(float(game.get("bet", 0) or 0) * float(game.get("current_x", 1.0) or 1.0), 2)
    symbol, _ = _currency_info(game.get("currency", "stars"))
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"💰 Забрать {format_stars(payout)} {symbol}", callback_data="crash_cashout")],[InlineKeyboardButton(text="ℹ️ Обновить", callback_data="crash_refresh")]])


def _build_crash_progress_bar(current_x: float) -> str:
    total_slots = 20
    progress = max(0.0, min(1.0, (float(current_x) - 1.0) / (CRASH_MAX_X - 1.0)))
    filled = min(total_slots, max(0, int(round(progress * total_slots))))
    return "🟩" * filled + "⬜" * (total_slots - filled)


def _build_crash_history(game: dict) -> str:
    return " • ".join(f"{float(x):.2f}x" for x in game.get("shown_steps", [1.00])[-6:])


def _get_next_crash_round_number() -> int:
    global_stats = _get_global_crash_stats()
    next_number = int(global_stats.get("last_round_number", 0) or 0) + 1
    global_stats["last_round_number"] = next_number
    return next_number


def _pick_crash_point() -> float:
    roll = max(random.random(), 1e-12)
    crash_at = CRASH_TARGET_RTP / roll
    return CRASH_MAX_X if crash_at >= CRASH_MAX_X else round(max(0.0, crash_at), 2)


def _create_crash_game(user_data: dict, bet: float, chat_id: int) -> dict:
    game = {
        "type": "crash",
        "bet": bet,
        "current_x": 1.00,
        "shown_steps": [1.00],
        "round_id": f"{chat_id}_{datetime.now().timestamp()}_{random.randint(1000,9999)}",
        "round_number": _get_next_crash_round_number(),
        "crash_at": _pick_crash_point(),
        "started_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "chat_id": chat_id,
    }
    pending_auto_x = user_data.pop("pending_crash_auto_x", None)
    if pending_auto_x is not None:
        game["auto_cashout_x"] = float(pending_auto_x)
    user_data["current_game"] = game
    return game


def _build_crash_status_text(game: dict, title: str, subtitle: str | None = None) -> str:
    bet = float(game.get("bet", 0) or 0)
    current_x = float(game.get("current_x", 1.0) or 1.0)
    cashout_amount = round(bet * current_x, 2)
    currency = game.get("currency", "stars")
    symbol, _ = _currency_info(currency)
    lines = [title,"",f"🆔 Раунд #{int(game.get('round_number',0) or 0)}",f"🎲 Ставка: {format_stars(bet)} {symbol}",f"📈 Текущий x: {current_x:.2f}x",f"💰 Можно забрать: {format_stars(cashout_amount)} {symbol}",f"🏁 Максимум: {CRASH_MAX_X:.2f}x","",_build_crash_progress_bar(current_x),"",f"🧾 Последние этапы: {_build_crash_history(game)}"]
    if game.get("auto_cashout_x") is not None:
        lines.extend(["", f"⚙️ Автовывод: {float(game['auto_cashout_x']):.2f}x"])
    if subtitle:
        lines.extend(["", subtitle])
    return "\n".join(lines)


async def _edit_crash_message(bot, game: dict, text: str, reply_markup: InlineKeyboardMarkup | None):
    try:
        await bot.edit_message_text(text=text, chat_id=int(game["chat_id"]), message_id=int(game["message_id"]), reply_markup=reply_markup)
    except Exception:
        pass


async def _finalize_crash_loss(bot, user_id: int, game: dict):
    user_data = _get_user_data(user_id)
    current_game = user_data.pop("current_game", None)
    if not current_game or current_game.get("type") != "crash" or current_game.get("round_id") != game.get("round_id"):
        raise CrashRoundEnded
    bet = float(current_game.get("bet", 0) or 0)
    currency = current_game.get("currency", "stars")
    symbol, _ = _currency_info(currency)
    user_stats = _get_user_crash_stats(user_data)
    global_stats = _get_global_crash_stats()
    user_stats["games_played"] += 1; user_stats["losses"] += 1; user_stats["total_bet"] += bet
    global_stats["games_played"] += 1; global_stats["losses"] += 1; global_stats["total_bet"] += bet
    global_stats["net_profit"] = round(float(global_stats["total_bet"]) - float(global_stats["total_paid_out"]), 2)
    record_game_event(user_id, "crash", bet, 0.0, currency)
    db.save_data()
    await _edit_crash_message(bot, game, "💥 Crash!\n\n" f"🆔 Раунд #{int(current_game.get('round_number',0) or 0)}\n" f"🎲 Ставка сгорела: {format_stars(bet)} {symbol}\n" f"📈 Раунд остановился на {float(current_game.get('current_x',1.0) or 1.0):.2f}x\n" "❌ Вы не успели забрать выигрыш", _build_crash_keyboard(game, game_over=True))


async def _finalize_crash_win(bot, user_id: int, game: dict, auto_max: bool = False):
    user_data = _get_user_data(user_id)
    current_game = user_data.pop("current_game", None)
    if not current_game or current_game.get("type") != "crash" or current_game.get("round_id") != game.get("round_id"):
        raise CrashRoundEnded
    bet = float(current_game.get("bet", 0) or 0)
    current_x = float(current_game.get("current_x", 1.0) or 1.0)
    payout = round(bet * current_x, 2)
    currency = current_game.get("currency", "stars")
    symbol, _ = _currency_info(currency)
    _add_currency_balance(user_data, currency, payout)
    user_stats = _get_user_crash_stats(user_data)
    global_stats = _get_global_crash_stats()
    user_stats["games_played"] += 1; user_stats["wins"] += 1; user_stats["total_bet"] += bet; user_stats["total_won"] += payout
    if payout > float(user_stats.get("biggest_win", 0) or 0): user_stats["biggest_win"] = payout
    global_stats["games_played"] += 1; global_stats["wins"] += 1; global_stats["total_bet"] += bet; global_stats["total_paid_out"] += payout
    global_stats["net_profit"] = round(float(global_stats["total_bet"]) - float(global_stats["total_paid_out"]), 2)
    record_game_event(user_id, "crash", bet, payout, currency)
    db.save_data()
    title = "🏆 Максимальный x достигнут!" if auto_max else "✅ Вы забрали выигрыш!"
    body = f"🆔 Раунд #{int(current_game.get('round_number',0) or 0)}\n🎲 Ставка: {format_stars(bet)} {symbol}\n📈 Коэффициент: {current_x:.2f}x\n💰 Выигрыш: {format_stars(payout)} {symbol}\n🏦 Новый баланс: {format_stars(_get_currency_balance(user_data, currency))} {symbol}"
    await _edit_crash_message(bot, game, f"{title}\n\n{body}", _build_crash_keyboard(game, game_over=True))


async def _run_crash_round(bot, user_id: int, round_id: str):
    try:
        await asyncio.sleep(0.7)
        while True:
            user_data = _get_user_data(user_id)
            game = _get_active_game(user_data)
            if not game or game.get("type") != "crash" or game.get("round_id") != round_id:
                return
            current_x = float(game.get("current_x", 1.0) or 1.0)
            if current_x >= CRASH_MAX_X - 1e-9:
                await _finalize_crash_win(bot, user_id, game, auto_max=True)
                return
            await asyncio.sleep(_crash_tick_delay(current_x))
            game = _get_active_game(_get_user_data(user_id))
            if not game or game.get("round_id") != round_id:
                return
            next_x = _next_crash_x(float(game.get("current_x",1.0) or 1.0))
            if float(game.get("crash_at",0.0) or 0.0) < CRASH_MAX_X - 1e-9 and next_x > float(game.get("crash_at",0.0) or 0.0) + 1e-9:
                await _finalize_crash_loss(bot, user_id, game)
                return
            shown_steps = list(game.get("shown_steps", [1.00])); shown_steps.append(next_x)
            game["current_x"] = next_x; game["shown_steps"] = shown_steps[-10:]
            db.save_data()
            await _edit_crash_message(bot, game, _build_crash_status_text(game, "📈 Crash — раунд идёт", "Жми «Забрать», пока раунд не взорвался."), _build_crash_keyboard(game))
            auto_cashout_x = game.get("auto_cashout_x")
            if auto_cashout_x is not None and next_x >= float(auto_cashout_x) - 1e-9:
                await _finalize_crash_win(bot, user_id, game, auto_max=False); return
    except asyncio.CancelledError:
        return
    finally:
        task = CRASH_RUNTIME_TASKS.get(user_id)
        if task is asyncio.current_task():
            CRASH_RUNTIME_TASKS.pop(user_id, None)


def _cancel_crash_task(user_id: int):
    task = CRASH_RUNTIME_TASKS.pop(user_id, None)
    if task and not task.done():
        task.cancel()


@router.callback_query(F.data == "game_crash")
async def start_crash_game(callback: CallbackQuery, state: FSMContext):
    user_data = _get_user_data(callback.from_user.id, callback.from_user.username)
    if _get_active_game(user_data):
        await callback.answer("Сначала завершите текущую игру", show_alert=True); return
    await state.clear(); await state.set_state(GameStates.waiting_crash_currency)
    await safe_edit_message(callback, "📈 Crash\n\n" f"🎯 Ставка: от {format_stars(CRASH_MIN_BET)} до {format_stars(CRASH_MAX_BET)}\n\n" "После старта x будет расти чаще и плавнее.\n" f"Забирать можно практически на любом x от {CRASH_MIN_X:.2f}x до {CRASH_MAX_X:.2f}x.\n\n" "Выберите валюту для игры:", reply_markup=_currency_choice_keyboard(user_data, "crash"))
    await callback.answer()


@router.callback_query(F.data.startswith("crash_currency_"))
async def crash_currency_selected(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.split("_")[-1]
    user_data = _get_user_data(callback.from_user.id, callback.from_user.username)
    balance = _get_currency_balance(user_data, currency)
    symbol, label = _currency_info(currency)
    await state.update_data(game_currency=currency)
    await state.set_state(GameStates.waiting_crash_bet)
    min_bet = TON_MIN_BET if currency == 'ton' else CRASH_MIN_BET
    await safe_edit_message(callback, "📈 Crash\n\n" f"💎 Ваш баланс: {format_stars(balance)} {symbol}\n" f"🎯 Ставка: от {format_stars(min_bet)} до {format_stars(CRASH_MAX_BET)} {symbol}\n\n" "После старта x будет расти чаще и плавнее.\n" f"Забирать можно практически на любом x от {CRASH_MIN_X:.2f}x до {CRASH_MAX_X:.2f}x.\n\n" f"Введите ставку в {label}. Можно 10 или 10.5:", reply_markup=menu_with_back(callback.from_user.id in ADMIN_IDS))
    await callback.answer()


@router.message(GameStates.waiting_crash_bet)
async def process_crash_bet(message: Message, state: FSMContext):
    if await _handle_waiting_navigation(message, state, "games"): return
    user_data = _get_user_data(message.from_user.id, message.from_user.username)
    data = await state.get_data(); currency = data.get("game_currency", "stars")
    symbol, _ = _currency_info(currency); balance = _get_currency_balance(user_data, currency)
    try: bet = _parse_game_bet(message.text)
    except Exception:
        await message.answer("❌ Введите ставку числом. Можно целое или с одной цифрой после точки, например: 10 или 10.5"); return
    min_bet = TON_MIN_BET if currency == 'ton' else CRASH_MIN_BET
    if bet < min_bet or bet > CRASH_MAX_BET:
        await message.answer(f"❌ Ставка должна быть от {format_stars(min_bet)} до {format_stars(CRASH_MAX_BET)} {symbol}"); return
    if bet > balance:
        await message.answer(f"❌ Недостаточно средств на балансе. Доступно: {format_stars(balance)} {symbol}"); return
    await state.update_data(crash_bet=bet)
    await message.answer("📈 Crash\n\n" f"🎲 Ставка: {format_stars(bet)} {symbol}\n" "Выберите режим раунда:\n\n" "• Обычный — сами нажимаете «Забрать»\n" "• Автовывод — бот сам заберёт на выбранном x", reply_markup=_build_crash_mode_keyboard())


@router.callback_query(F.data == "crash_mode_manual")
async def crash_mode_manual(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data(); bet = float(data.get("crash_bet", 0) or 0)
    if bet <= 0: await callback.answer("Сначала введите ставку", show_alert=True); return
    user_data = _get_user_data(callback.from_user.id, callback.from_user.username)
    currency = data.get("game_currency", "stars")
    if bet > _get_currency_balance(user_data, currency):
        await state.clear(); await callback.answer("Недостаточно средств на балансе", show_alert=True); return
    _sub_currency_balance(user_data, currency, bet); user_data.pop("pending_crash_auto_x", None)
    game = _create_crash_game(user_data, bet, callback.message.chat.id); game["currency"] = currency; db.save_data(); await state.clear()
    await safe_edit_message(callback, _build_crash_status_text(game, "🚀 Crash запущен", "Сейчас x начнёт расти. Успей забрать раньше взрыва."), reply_markup=_build_crash_keyboard(game))
    current_game = _get_active_game(user_data)
    if current_game and callback.message:
        current_game["message_id"] = callback.message.message_id; db.save_data(); _cancel_crash_task(callback.from_user.id)
        CRASH_RUNTIME_TASKS[callback.from_user.id] = asyncio.create_task(_run_crash_round(callback.bot, callback.from_user.id, game["round_id"]))
    await callback.answer()


@router.callback_query(F.data == "crash_mode_auto")
async def crash_mode_auto(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data(); bet = float(data.get("crash_bet",0) or 0)
    if bet <= 0: await callback.answer("Сначала введите ставку", show_alert=True); return
    symbol, _ = _currency_info(data.get("game_currency","stars"))
    await state.set_state(GameStates.waiting_crash_auto_x)
    await safe_edit_message(callback, "⚙️ Автовывод для Crash\n\n" f"🎲 Ставка: {format_stars(bet)} {symbol}\n\n" "Введите желаемый x для автовывода.\n" "Например: 1.02, 1.57, 2.35 или 7.92\n\n" "Доступный диапазон: " + _build_crash_autox_hint())
    await callback.answer()


@router.message(GameStates.waiting_crash_auto_x)
async def process_crash_auto_x(message: Message, state: FSMContext):
    if await _handle_waiting_navigation(message, state, "crash_mode"): return
    data = await state.get_data(); bet = float(data.get("crash_bet",0) or 0)
    if bet <= 0: await state.clear(); await message.answer("❌ Сначала начните игру заново"); return
    try: requested_x = float((message.text or "").strip().replace(",", ".").replace("x", "").replace("х", ""))
    except Exception:
        await message.answer("❌ Введите число, например 1.52"); return
    if requested_x < CRASH_MIN_X or requested_x > CRASH_MAX_X:
        await message.answer(f"❌ Автовывод должен быть от {CRASH_MIN_X:.2f}x до {CRASH_MAX_X:.2f}x"); return
    auto_x = _normalize_crash_auto_x(requested_x)
    user_data = _get_user_data(message.from_user.id, message.from_user.username)
    currency = data.get("game_currency", "stars")
    balance = _get_currency_balance(user_data, currency)
    if bet > balance:
        await state.clear(); await message.answer(f"❌ Недостаточно средств на балансе. Доступно: {format_stars(balance)}"); return
    _sub_currency_balance(user_data, currency, bet); user_data["pending_crash_auto_x"] = auto_x
    game = _create_crash_game(user_data, bet, message.chat.id); game["currency"] = currency; db.save_data(); await state.clear()
    sent = await message.answer(_build_crash_status_text(game, "🚀 Crash запущен", f"Автовывод включён на {auto_x:.2f}x. Если x дойдёт до этой точки — бот сам заберёт выигрыш."), reply_markup=_build_crash_keyboard(game))
    current_game = _get_active_game(user_data)
    if current_game:
        current_game["message_id"] = sent.message_id; db.save_data(); _cancel_crash_task(message.from_user.id)
        CRASH_RUNTIME_TASKS[message.from_user.id] = asyncio.create_task(_run_crash_round(message.bot, message.from_user.id, game["round_id"]))


@router.callback_query(F.data == "crash_refresh")
async def crash_refresh(callback: CallbackQuery):
    user_data = _get_user_data(callback.from_user.id, callback.from_user.username)
    game = _get_active_game(user_data)
    if not game or game.get("type") != "crash": await callback.answer("❌ Активная игра не найдена", show_alert=True); return
    await safe_edit_message(callback, _build_crash_status_text(game, "📈 Crash — раунд идёт", "Следите за ростом x и забирайте вовремя."), reply_markup=_build_crash_keyboard(game))
    await callback.answer("Обновлено")


@router.callback_query(F.data == "crash_cashout")
async def crash_cashout(callback: CallbackQuery):
    user_data = _get_user_data(callback.from_user.id, callback.from_user.username)
    game = _get_active_game(user_data)
    if not game or game.get("type") != "crash": await callback.answer("❌ Активная игра не найдена", show_alert=True); return
    _cancel_crash_task(callback.from_user.id)
    await _finalize_crash_win(callback.bot, callback.from_user.id, game, auto_max=False)
    await callback.answer("💰 Забрано")
