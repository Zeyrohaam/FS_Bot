from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import REQUIRED_CHANNELS, ADMIN_IDS
from database import db


async def get_subscription_status(bot: Bot, user_id: int, username: str | None = None):
    if user_id in ADMIN_IDS:
        return []

    missing: list[str] = []
    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in {"left", "kicked"}:
                missing.append(channel)
                db.add_sub_log(user_id, username, channel, "UNSUBSCRIBED")
        except Exception:
            missing.append(channel)
    return missing


def subscription_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for idx, channel in enumerate(REQUIRED_CHANNELS, start=1):
        rows.append(
            [InlineKeyboardButton(text=f"📢 Канал {idx}", url=f"https://t.me/{channel.lstrip('@')}")]
        )
    rows.append(
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subscriptions")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)