from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

from config import BOT_USERNAME
from database import db
from utils.helpers import add_star_balance, format_stars, register_user_if_needed

logger = logging.getLogger(__name__)

PREMIUM_REWARDS: dict[int, int] = {
    1: 15,
    3: 25,
    6: 30,
    12: 60,
}

STARS_COMMISSION_PERCENT: float = 0.05  # 5%


def get_clean_bot_username(fallback: str = "FreakingStars_Bot") -> str:
    raw = (BOT_USERNAME or "").strip()
    clean = raw.lstrip("@").strip()
    return clean or fallback


def build_referral_link(bot_username: str | None, user_id: int) -> str:
    clean_username = (bot_username or get_clean_bot_username()).lstrip("@").strip()
    return f"https://t.me/{clean_username}?start=ref_{user_id}"


def build_referral_share_link(bot_username: str | None, user_id: int) -> str:
    invite_link = build_referral_link(bot_username, user_id)
    share_text = "⭐️ Заходи в Freaking Stars! Покупай Stars и Telegram Premium по лучшим ценам, крути кейсы и выигрывай!"
    return f"https://t.me/share/url?url={quote_plus(invite_link)}&text={quote_plus(share_text)}"


def bind_referral(user_id: int, referrer_id: int, username: str | None = None, bot: Any = None) -> bool:
    """
    Привязывает пользователя user_id к рефереру referrer_id.
    Возвращает True, если реферал успешно привязан впервые.
    """
    try:
        user_id = int(user_id)
        referrer_id = int(referrer_id)
    except (TypeError, ValueError):
        return False

    if user_id == referrer_id:
        return False

    referrer_str = str(referrer_id)
    if referrer_str not in db.users:
        # Реферер не найден в базе
        return False

    user_data = register_user_if_needed(user_id, username)
    existing_referrer = user_data.get("invited_by")
    if existing_referrer:
        # Пользователь уже чей-то реферал
        return False

    # Проверка на цикличность (A -> B -> A)
    curr_id = referrer_id
    visited = set()
    while curr_id:
        if curr_id == user_id:
            return False
        if curr_id in visited:
            break
        visited.add(curr_id)
        parent_user = db.users.get(str(curr_id))
        if not isinstance(parent_user, dict):
            break
        curr_id = parent_user.get("invited_by")
        try:
            curr_id = int(curr_id) if curr_id is not None else None
        except (TypeError, ValueError):
            curr_id = None

    user_data["invited_by"] = referrer_id
    referrer_data = db.users[referrer_str]
    refs = referrer_data.setdefault("referrals", [])
    if user_id not in refs:
        refs.append(user_id)
    referrer_data["referral_count"] = len(refs)

    db.save_data()

    clean_user = (username or "").strip().lstrip("@")
    user_display = f"@{clean_user}" if clean_user and clean_user != "Не указан" else f"ID: {user_id}"
    notify_text = (
        f"🎉 У вас новый реферал!\n\n"
        f"Пользователь {user_display} перешёл и зарегистрировался по вашей ссылке.\n\n"
        f"💰 Вы будете получать:\n"
        f"• ⭐️ 5% от всех его покупок Stars\n"
        f"• 👑 За покупки Telegram Premium: 15 ⭐ (1 мес), 25 ⭐ (3 мес), 30 ⭐ (6 мес), 60 ⭐ (12 мес)"
    )

    _send_referral_notification(referrer_id, notify_text, bot=bot)
    return True


def reward_referrer_for_purchase(
    user_id: int,
    purchase_type: str,
    stars: int = 0,
    months: int = 0,
    bot: Any = None,
) -> float:
    """
    Начисляет вознаграждение рефереру за покупку реферала.
    purchase_type: 'stars' или 'premium'
    Возвращает сумму начисленных звёзд.
    """
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return 0.0

    user_str = str(user_id)
    user_data = db.users.get(user_str)
    if not isinstance(user_data, dict):
        return 0.0

    referrer_id = user_data.get("invited_by")
    if not referrer_id:
        return 0.0

    try:
        referrer_id = int(referrer_id)
    except (TypeError, ValueError):
        return 0.0

    referrer_str = str(referrer_id)
    referrer_data = db.users.get(referrer_str)
    if not isinstance(referrer_data, dict):
        return 0.0

    bonus_stars = 0.0
    reason_desc = ""

    if purchase_type == "stars":
        stars_amount = int(stars or 0)
        if stars_amount <= 0:
            return 0.0
        bonus_stars = round(stars_amount * STARS_COMMISSION_PERCENT, 2)
        reason_desc = f"5% от покупки {stars_amount} ⭐️ рефералом"
    elif purchase_type == "premium":
        months_val = int(months or 0)
        bonus_stars = float(PREMIUM_REWARDS.get(months_val, 15))
        reason_desc = f"покупку Telegram Premium на {months_val} мес. рефералом"
    else:
        return 0.0

    if bonus_stars <= 0:
        return 0.0

    add_star_balance(referrer_data, bonus_stars)
    prev_earnings = float(referrer_data.get("referral_earnings_stars", 0) or 0)
    referrer_data["referral_earnings_stars"] = round(prev_earnings + bonus_stars, 2)

    history = referrer_data.setdefault("referral_rewards", [])
    history.append({
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "from_user_id": user_id,
        "type": purchase_type,
        "bonus_stars": bonus_stars,
        "description": reason_desc,
    })

    db.save_data()

    buyer_name = user_data.get("username")
    buyer_display = f"@{buyer_name}" if buyer_name and buyer_name != "Не указан" else f"ID: {user_id}"
    notify_text = (
        f"🎁 Реферальное вознаграждение!\n\n"
        f"Вам начислено +{format_stars(bonus_stars)} ⭐️ за {reason_desc} ({buyer_display})!\n"
        f"💎 Ваш текущий баланс: {format_stars(referrer_data['balance_stars'])} ⭐️"
    )

    _send_referral_notification(referrer_id, notify_text, bot=bot)
    return bonus_stars


def _send_referral_notification(user_id: int, text: str, bot: Any = None):
    """
    Отправляет уведомление пользователю через aiogram Bot (если передан)
    или синхронный Telegram API (если вызов из FastAPI).
    """
    if bot:
        try:
            import asyncio
            coro = bot.send_message(chat_id=user_id, text=text)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro)
                return
            except RuntimeError:
                asyncio.run(coro)
                return
        except Exception as e:
            logger.warning("Failed to send referral notification via bot: %s", e)

    try:
        from miniapp.telegram_api import send_message as tg_send_message
        tg_send_message(chat_id=user_id, text=text)
    except Exception as e:
        logger.warning("Failed to send referral notification via telegram_api: %s", e)


def get_user_referral_summary(user_id: int, bot_username: str | None = None) -> dict[str, Any]:
    db.refresh()
    user_str = str(user_id)
    user_data = db.users.get(user_str, {})
    referrals_list = user_data.get("referrals", [])
    if not isinstance(referrals_list, list):
        referrals_list = []

    referrals_details = []
    for r_id in reversed(referrals_list[-20:]):
        r_user = db.users.get(str(r_id), {})
        referrals_details.append({
            "user_id": r_id,
            "username": r_user.get("username") or "Пользователь",
            "date": r_user.get("registration_date") or "—",
        })

    return {
        "invite_link": build_referral_link(bot_username, user_id),
        "share_link": build_referral_share_link(bot_username, user_id),
        "referral_count": len(referrals_list),
        "referral_earnings_stars": round(float(user_data.get("referral_earnings_stars", 0) or 0), 2),
        "invited_by": user_data.get("invited_by"),
        "stars_percent": 5,
        "premium_rewards": PREMIUM_REWARDS,
        "referrals": referrals_details,
    }
