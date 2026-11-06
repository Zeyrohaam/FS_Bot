from datetime import datetime
from uuid import uuid4

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .common import (
    ADMIN_IDS,
    DICE_DUELS,
    DICE_MAX_BET,
    DICE_MIN_BET,
    DICE_QUEUE,
    DICE_ROOMS,
    DICE_SMALL_BANK_COMMISSION,
    DICE_LARGE_BANK_COMMISSION,
    DICE_SMALL_BANK_THRESHOLD,
    GameStates,
    _add_currency_balance,
    _build_dice_duel_info_text,
    _build_dice_invite_link,
    _build_dice_rounds_keyboard,
    _build_dice_waiting_keyboard,
    _build_dice_waiting_text,
    _create_dice_room,
    _currency_choice_keyboard,
    _currency_info,
    _find_waiting_duel_opponent,
    _get_active_game,
    _get_currency_balance,
    _get_user_data,
    _handle_waiting_navigation,
    _is_forwarded_message,
    _parse_game_bet,
    _remove_dice_room,
    _remove_from_dice_queue,
    _required_dice_wins,
    _sub_currency_balance,
    db,
    format_stars,
    menu_with_back,
    router,
    safe_edit_message,
    TON_MIN_BET,
)
from utils.tournaments import record_game_event


@router.callback_query(F.data == "game_dice_duel")
async def start_dice_duel(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    username = callback.from_user.username
    user_data = _get_user_data(user_id, username)

    if _get_active_game(user_data):
        await callback.answer("Сначала завершите текущую игру", show_alert=True)
        return

    await state.clear()
    await state.set_state(GameStates.waiting_dice_currency)

    text = (
        "🎲 Кубы 1v1\n\n"
        "Игра на двоих: каждый ставит одинаковую сумму, потом оба кидают СВОЙ кубик 🎲.\n"
        "Кто выбросил больше — забирает весь банк.\n"
        "Пересланные кубики не засчитываются.\n\n"
    )

    await safe_edit_message(
        callback,
        text,
        reply_markup=_currency_choice_keyboard(user_data, "dice"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dice_currency_"))
async def dice_currency_selected(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.split("_")[-1]

    user_data = _get_user_data(callback.from_user.id, callback.from_user.username)
    balance = _get_currency_balance(user_data, currency)
    symbol, _ = _currency_info(currency)

    await state.update_data(game_currency=currency)
    await state.set_state(GameStates.waiting_dice_rounds)

    text = (
        "🎲 Кубы 1v1\n\n"
        "Выберите формат матча:\n"
    )

    await safe_edit_message(
        callback,
        text,
        reply_markup=_build_dice_rounds_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dice_rounds_"))
async def dice_rounds_selected(callback: CallbackQuery, state: FSMContext):
    rounds_total = int(callback.data.split("_")[-1])

    data = await state.get_data()
    currency = data.get("game_currency", "stars")

    user_data = _get_user_data(callback.from_user.id, callback.from_user.username)
    balance = _get_currency_balance(user_data, currency)
    symbol, label = _currency_info(currency)

    await state.update_data(dice_rounds_total=rounds_total)
    await state.set_state(GameStates.waiting_dice_bet)

    min_bet = TON_MIN_BET if currency == 'ton' else DICE_MIN_BET
    text = (
        "🎲 Кубы 1v1\n\n"
        f"💎 Ваш баланс: {format_stars(balance)} {symbol}\n"
        f"📚 Формат: {rounds_total} раунд(ах)\n"
        f"🎯 Ставка: от {format_stars(min_bet)} до {format_stars(DICE_MAX_BET)} {symbol}\n\n"
        "Найдётся соперник с такой же ставкой.\n"
        "Потом каждый бросает кубик 🎲.\n\n"
        f"Введите ставку в {label}."
    )

    await safe_edit_message(
        callback,
        text,
        reply_markup=menu_with_back(callback.from_user.id in ADMIN_IDS),
    )
    await callback.answer()


@router.message(GameStates.waiting_dice_bet)
async def process_dice_bet(message: Message, state: FSMContext):
    if await _handle_waiting_navigation(message, state, "games"):
        return

    user_id = message.from_user.id
    username = message.from_user.username
    user_data = _get_user_data(user_id, username)

    data = await state.get_data()
    currency = data.get("game_currency", "stars")
    rounds_total = int(data.get("dice_rounds_total", 1) or 1)

    symbol, label = _currency_info(currency)
    balance = _get_currency_balance(user_data, currency)

    try:
        bet = _parse_game_bet(message.text)
    except Exception:
        await message.answer(
            "❌ Введите ставку числом. Можно целое или с одной цифрой после точки, например: 10 или 10.5"
        )
        return

    min_bet = TON_MIN_BET if currency == 'ton' else DICE_MIN_BET
    if bet < min_bet or bet > DICE_MAX_BET:
        await message.answer(
            f"❌ Ставка должна быть от {format_stars(min_bet)} "
            f"до {format_stars(DICE_MAX_BET)} {symbol}"
        )
        return

    if bet > balance:
        await message.answer(
            f"❌ Недостаточно средств на балансе. "
            f"Доступно: {format_stars(balance)} {symbol}"
        )
        return

    _sub_currency_balance(user_data, currency, bet)

    key, opponent_entry = _find_waiting_duel_opponent(
        user_id,
        currency,
        bet,
        rounds_total,
    )

    if opponent_entry is None:
        room_id = _create_dice_room(user_id, currency, bet, rounds_total)

        user_data["current_game"] = {
            "type": "dice_duel",
            "status": "waiting",
            "currency": currency,
            "bet": bet,
            "rounds_total": rounds_total,
            "queue_key": key,
            "room_id": room_id,
            "queued_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        }

        DICE_QUEUE.setdefault(key, []).append(
            {
                "user_id": user_id,
                "currency": currency,
                "bet": bet,
                "rounds_total": rounds_total,
                "room_id": room_id,
            }
        )

        db.save_data()
        await state.clear()

        me = await message.bot.get_me()
        invite_link = _build_dice_invite_link(getattr(me, "username", None), room_id)

        await message.answer(
            _build_dice_waiting_text(bet, symbol, rounds_total, invite_link),
            reply_markup=_build_dice_waiting_keyboard(),
            disable_web_page_preview=True,
        )
        return

    opponent_id = int(opponent_entry["user_id"])
    room_id = opponent_entry.get("room_id")

    _remove_dice_room(room_id)

    duel_id = uuid4().hex
    duel = {
        "duel_id": duel_id,
        "players": [opponent_id, user_id],
        "currency": currency,
        "bet": bet,
        "rounds_total": rounds_total,
        "current_round": 1,
        "scores": {
            str(opponent_id): 0,
            str(user_id): 0,
        },
        "rolls": {},
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }

    DICE_DUELS[duel_id] = duel

    opponent_data = _get_user_data(opponent_id)
    opponent_data["current_game"] = {
        "type": "dice_duel",
        "status": "active",
        "currency": currency,
        "bet": bet,
        "rounds_total": rounds_total,
        "duel_id": duel_id,
    }

    user_data["current_game"] = {
        "type": "dice_duel",
        "status": "active",
        "currency": currency,
        "bet": bet,
        "rounds_total": rounds_total,
        "duel_id": duel_id,
    }

    db.save_data()
    await state.clear()

    await message.answer(
        _build_dice_duel_info_text(duel, user_id),
        reply_markup=menu_with_back(user_id in ADMIN_IDS),
    )

    try:
        await message.bot.send_message(
            opponent_id,
            _build_dice_duel_info_text(duel, opponent_id),
            reply_markup=menu_with_back(opponent_id in ADMIN_IDS),
        )
    except Exception:
        pass


@router.callback_query(F.data == "dice_cancel_search")
async def cancel_dice_search(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username
    user_data = _get_user_data(user_id, username)

    current_game = user_data.pop("current_game", None)
    if (
        not current_game
        or current_game.get("type") != "dice_duel"
        or current_game.get("status") != "waiting"
    ):
        if current_game:
            user_data["current_game"] = current_game
        await callback.answer("Ожидание соперника не найдено", show_alert=True)
        return

    currency = current_game.get("currency", "stars")
    symbol, _ = _currency_info(currency)
    bet = float(current_game.get("bet", 0) or 0)

    removed = _remove_from_dice_queue(user_id)
    _remove_dice_room(current_game.get("room_id") or (removed or {}).get("room_id"))

    _add_currency_balance(user_data, currency, bet)
    db.save_data()

    await safe_edit_message(
        callback,
        f"❌ Поиск соперника отменён.\n\n💰 Ставка возвращена: {format_stars(bet)} {symbol}",
    )
    await callback.answer("Поиск отменён")


@router.message(F.dice)
async def process_duel_dice_roll(message: Message):
    if not message.dice or message.dice.emoji != "🎲":
        return

    user_id = message.from_user.id
    username = message.from_user.username
    user_data = _get_user_data(user_id, username)

    current_game = _get_active_game(user_data)
    if (
        not current_game
        or current_game.get("type") != "dice_duel"
        or current_game.get("status") != "active"
    ):
        return

    if _is_forwarded_message(message):
        await message.answer(
            "❌ Пересланный кубик не засчитывается. "
            "Отправьте новый кубик 🎲 прямо в этот чат."
        )
        return

    duel_id = current_game.get("duel_id")
    duel = DICE_DUELS.get(duel_id)

    if not duel:
        user_data.pop("current_game", None)
        db.save_data()
        await message.answer("❌ Дуэль не найдена. Попробуйте начать заново.")
        return

    uid_key = str(user_id)

    if uid_key in duel.get("rolls", {}):
        await message.answer("🎲 Вы уже бросили кубик. Ждём соперника.")
        return

    duel.setdefault("rolls", {})[uid_key] = int(message.dice.value)

    player_ids = duel.get("players", [])
    if player_ids[0] == user_id and len(player_ids) > 1:
        opponent_id = player_ids[1]
    else:
        opponent_id = player_ids[0]

    await message.answer(
        f"✅ Ваш бросок засчитан: {int(message.dice.value)}\nЖдём соперника."
    )

    if str(opponent_id) not in duel["rolls"]:
        try:
            await message.bot.send_message(
                opponent_id,
                _build_dice_duel_info_text(duel, opponent_id),
                reply_markup=menu_with_back(opponent_id in ADMIN_IDS),
            )
        except Exception:
            pass
        return

    player_a_id = player_ids[0]
    player_b_id = player_ids[1]

    roll_a = int(duel["rolls"].get(str(player_a_id), 0))
    roll_b = int(duel["rolls"].get(str(player_b_id), 0))

    currency = duel.get("currency", "stars")
    symbol, _ = _currency_info(currency)
    bet = float(duel.get("bet", 0) or 0)
    bank = bet * 2

    if roll_a == roll_b:
        duel["rolls"] = {}

        tie_text = (
            "🤝 Ничья!\n\n"
            f"Оба выбросили {roll_a}.\n"
            f"Раунд {int(duel.get('current_round', 1) or 1)} переигрывается.\n"
            "Отправьте новый кубик 🎲.\n"
            "Пересланные кубики не засчитываются."
        )

        for uid in player_ids:
            try:
                await message.bot.send_message(
                    uid,
                    tie_text,
                    reply_markup=menu_with_back(uid in ADMIN_IDS),
                )
            except Exception:
                pass
        return

    winner_id = player_a_id if roll_a > roll_b else player_b_id
    loser_id = player_b_id if winner_id == player_a_id else player_a_id

    winner_roll = duel["rolls"][str(winner_id)]
    loser_roll = duel["rolls"][str(loser_id)]

    duel.setdefault("scores", {})
    duel["scores"][str(winner_id)] = int(duel["scores"].get(str(winner_id), 0) or 0) + 1

    rounds_total = int(duel.get("rounds_total", 1) or 1)
    need_wins = _required_dice_wins(rounds_total)

    winner_score = int(duel["scores"].get(str(winner_id), 0) or 0)
    loser_score = int(duel["scores"].get(str(loser_id), 0) or 0)
    current_round = int(duel.get("current_round", 1) or 1)

    if winner_score < need_wins and current_round < rounds_total:
        duel["current_round"] = current_round + 1
        duel["rolls"] = {}
        db.save_data()

        try:
            await message.bot.send_message(
                winner_id,
                (
                    f"✅ Раунд {current_round} за вами!\n\n"
                    f"🎲 Ваш бросок: {winner_roll}\n"
                    f"🎲 Бросок соперника: {loser_roll}\n"
                    f"📊 Счёт матча: {winner_score}:{loser_score}\n"
                    f"🔜 Следующий раунд: {current_round + 1}/{rounds_total}"
                ),
                reply_markup=menu_with_back(winner_id in ADMIN_IDS),
            )
        except Exception:
            pass

        try:
            await message.bot.send_message(
                loser_id,
                (
                    f"❌ Раунд {current_round} проигран.\n\n"
                    f"🎲 Ваш бросок: {loser_roll}\n"
                    f"🎲 Бросок соперника: {winner_roll}\n"
                    f"📊 Счёт матча: {loser_score}:{winner_score}\n"
                    f"🔜 Следующий раунд: {current_round + 1}/{rounds_total}"
                ),
                reply_markup=menu_with_back(loser_id in ADMIN_IDS),
            )
        except Exception:
            pass

        return

    winner_data = _get_user_data(winner_id)
    loser_data = _get_user_data(loser_id)

    commission_rate = (
        DICE_SMALL_BANK_COMMISSION
        if bank <= DICE_SMALL_BANK_THRESHOLD
        else DICE_LARGE_BANK_COMMISSION
    )

    payout = round(bank * (1 - commission_rate), 1)

    if duel_id not in DICE_DUELS:
        return
    DICE_DUELS.pop(duel_id, None)
    winner_data.pop("current_game", None)
    loser_data.pop("current_game", None)

    _add_currency_balance(winner_data, currency, payout)

    record_game_event(winner_id, "dice", bet, payout, currency)
    record_game_event(loser_id, "dice", bet, 0.0, currency)

    db.save_data()

    try:
        await message.bot.send_message(
            winner_id,
            (
                "🏆 Матч завершён — вы победили!\n\n"
                f"🎲 Бросок соперника: {loser_roll}\n"
                f"📊 Финальный счёт: {winner_score}:{loser_score}\n"
                f"🏦 Общий банк: {format_stars(bank)} {symbol}\n"
                f"💰 Сумма победы: {format_stars(payout)} {symbol}\n"
                f"🏦 Новый баланс: "
                f"{format_stars(_get_currency_balance(winner_data, currency))} {symbol}"
            ),
            reply_markup=menu_with_back(winner_id in ADMIN_IDS),
        )
    except Exception:
        pass

    try:
        await message.bot.send_message(
            loser_id,
            (
                "😔 Матч завершён — вы проиграли.\n\n"
                f"🎲 Бросок соперника: {winner_roll}\n"
                f"📊 Финальный счёт: {loser_score}:{winner_score}\n"
                f"🏦 Общий банк: {format_stars(bank)} {symbol}\n"
                f"💸 Ваша ставка: {format_stars(bet)} {symbol}"
            ),
            reply_markup=menu_with_back(loser_id in ADMIN_IDS),
        )
    except Exception:
        pass


async def join_dice_room_by_link(message: Message, room_id: str):
    room = DICE_ROOMS.get(room_id)

    if not room or room.get("status") != "waiting":
        await message.answer(
            "❌ Эта ссылка на игру недействительна или матч уже начался.",
            reply_markup=menu_with_back(message.from_user.id in ADMIN_IDS),
        )
        return

    owner_id = int(room.get("owner_id", 0) or 0)

    if owner_id == message.from_user.id:
        await message.answer(
            "ℹ️ Это ваша ссылка на матч. Ждите соперника или отмените поиск.",
            reply_markup=_build_dice_waiting_keyboard(),
        )
        return

    user_data = _get_user_data(message.from_user.id, message.from_user.username)

    if _get_active_game(user_data):
        await message.answer(
            "❌ Сначала завершите текущую игру.",
            reply_markup=menu_with_back(message.from_user.id in ADMIN_IDS),
        )
        return

    owner_data = _get_user_data(owner_id)
    owner_game = _get_active_game(owner_data)

    if not owner_game or owner_game.get("status") != "waiting":
        _remove_dice_room(room_id)
        await message.answer(
            "❌ Хозяин комнаты уже не ждёт соперника.",
            reply_markup=menu_with_back(message.from_user.id in ADMIN_IDS),
        )
        return

    currency = room.get("currency", "stars")
    bet = float(room.get("bet", 0) or 0)
    rounds_total = int(room.get("rounds_total", 1) or 1)

    balance = _get_currency_balance(user_data, currency)
    symbol, _ = _currency_info(currency)

    if bet > balance:
        await message.answer(
            f"❌ Недостаточно средств для входа. Нужно {format_stars(bet)} {symbol}.",
            reply_markup=menu_with_back(message.from_user.id in ADMIN_IDS),
        )
        return

    _sub_currency_balance(user_data, currency, bet)
    _remove_from_dice_queue(owner_id)
    _remove_dice_room(room_id)

    duel_id = uuid4().hex
    duel = {
        "duel_id": duel_id,
        "players": [owner_id, message.from_user.id],
        "currency": currency,
        "bet": bet,
        "rounds_total": rounds_total,
        "current_round": 1,
        "scores": {
            str(owner_id): 0,
            str(message.from_user.id): 0,
        },
        "rolls": {},
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }

    DICE_DUELS[duel_id] = duel

    owner_data["current_game"] = {
        "type": "dice_duel",
        "status": "active",
        "currency": currency,
        "bet": bet,
        "rounds_total": rounds_total,
        "duel_id": duel_id,
    }

    user_data["current_game"] = {
        "type": "dice_duel",
        "status": "active",
        "currency": currency,
        "bet": bet,
        "rounds_total": rounds_total,
        "duel_id": duel_id,
    }

    db.save_data()

    await message.answer(
        "✅ Вы вошли в матч по ссылке. Игра начинается!",
        reply_markup=menu_with_back(message.from_user.id in ADMIN_IDS),
    )
    await message.answer(
        _build_dice_duel_info_text(duel, message.from_user.id),
        reply_markup=menu_with_back(message.from_user.id in ADMIN_IDS),
    )

    try:
        await message.bot.send_message(
            owner_id,
            "✅ По вашей ссылке подключился соперник. Игра начинается!",
            reply_markup=menu_with_back(owner_id in ADMIN_IDS),
        )
        await message.bot.send_message(
            owner_id,
            _build_dice_duel_info_text(duel, owner_id),
            reply_markup=menu_with_back(owner_id in ADMIN_IDS),
        )
    except Exception:
        pass