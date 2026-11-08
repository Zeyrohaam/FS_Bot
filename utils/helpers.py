import logging
import math
from datetime import datetime
from typing import Any

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from database import db

logger = logging.getLogger(__name__)


def get_numeric_balance(user_data: dict[str, Any]) -> float:
    return float(user_data.get("balance_stars", user_data.get("total_stars", 0)) or 0)


def get_numeric_ton_balance(user_data: dict[str, Any]) -> float:
    return float(user_data.get("balance_ton", 0) or 0)


def get_numeric_uah_balance(user_data: dict[str, Any]) -> float:
    return float(user_data.get("balance_uah", 0) or 0)


def format_stars(value: Any) -> str:
    amount = float(value or 0)
    rounded = round(amount, 2)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def add_star_balance(user_data: dict[str, Any], amount: Any) -> float:
    amount = float(amount or 0)
    if not math.isfinite(amount) or amount < 0:
        raise ValueError("amount must be a finite non-negative number")
    user_data["balance_stars"] = round(get_numeric_balance(user_data) + amount, 2)
    user_data["total_stars"] = round(float(user_data.get("total_stars", 0) or 0) + amount, 2)
    uid = user_data.get("id") or user_data.get("user_id")
    if uid and str(uid) in db.users and db.users[str(uid)] is not user_data:
        db.users[str(uid)]["balance_stars"] = user_data["balance_stars"]
        db.users[str(uid)]["total_stars"] = user_data["total_stars"]
    return float(user_data["balance_stars"])


def sub_star_balance(user_data: dict[str, Any], amount: Any) -> float:
    amount = float(amount or 0)
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("deduction amount must be a finite positive number")
    current = get_numeric_balance(user_data)
    if amount > current:
        raise ValueError("insufficient balance")
    user_data["balance_stars"] = round(current - amount, 2)
    uid = user_data.get("id") or user_data.get("user_id")
    if uid and str(uid) in db.users and db.users[str(uid)] is not user_data:
        db.users[str(uid)]["balance_stars"] = user_data["balance_stars"]
    return float(user_data["balance_stars"])


def add_ton_balance(user_data: dict[str, Any], amount: Any) -> float:
    amount = float(amount or 0)
    if not math.isfinite(amount) or amount < 0:
        raise ValueError("amount must be a finite non-negative number")
    user_data["balance_ton"] = round(get_numeric_ton_balance(user_data) + amount, 4)
    uid = user_data.get("id") or user_data.get("user_id")
    if uid and str(uid) in db.users and db.users[str(uid)] is not user_data:
        db.users[str(uid)]["balance_ton"] = user_data["balance_ton"]
    return float(user_data["balance_ton"])


def sub_ton_balance(user_data: dict[str, Any], amount: Any) -> float:
    amount = float(amount or 0)
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("deduction amount must be a finite positive number")
    current = get_numeric_ton_balance(user_data)
    if amount > current:
        raise ValueError("insufficient ton balance")
    user_data["balance_ton"] = round(current - amount, 4)
    uid = user_data.get("id") or user_data.get("user_id")
    if uid and str(uid) in db.users and db.users[str(uid)] is not user_data:
        db.users[str(uid)]["balance_ton"] = user_data["balance_ton"]
    return float(user_data["balance_ton"])


def _ensure_user_game_stats(user_data: dict[str, Any]) -> bool:
    changed = False
    if "games" not in user_data or not isinstance(user_data.get("games"), dict):
        user_data["games"] = {}
        changed = True

    defaults = {
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "total_bet": 0,
        "total_won": 0,
        "biggest_win": 0,
    }

    for game_name in ("mines", "crash"):
        if game_name not in user_data["games"] or not isinstance(user_data["games"].get(game_name), dict):
            user_data["games"][game_name] = {}
            changed = True
        stats = user_data["games"][game_name]
        for key, value in defaults.items():
            if key not in stats:
                stats[key] = value
                changed = True
    return changed


def register_user_if_needed(user_id: int, username: str | None = None) -> dict[str, Any]:
    key = str(user_id)
    if key not in db.users:
        db.refresh()
    if key not in db.users:
        db.users[key] = {
            "id": int(user_id),
            "username": username or "Не указан",
            "total_stars": 0,
            "balance_stars": 0,
            "balance_ton": 0,
            "balance_uah": 0,
            "registration_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "has_review": False,
            "last_active": datetime.now().isoformat(),
            "games": {
                "mines": {
                    "games_played": 0,
                    "wins": 0,
                    "losses": 0,
                    "total_bet": 0,
                    "total_won": 0,
                    "biggest_win": 0,
                },
                "crash": {
                    "games_played": 0,
                    "wins": 0,
                    "losses": 0,
                    "total_bet": 0,
                    "total_won": 0,
                    "biggest_win": 0,
                }
            },
        }
        db.save_data()
    else:
        changed = False
        db.users[key]["last_active"] = datetime.now().isoformat()
        if "id" not in db.users[key]:
            db.users[key]["id"] = int(user_id)
            changed = True
        if "balance_stars" not in db.users[key]:
            db.users[key]["balance_stars"] = float(db.users[key].get("total_stars", 0) or 0)
            changed = True
        if "balance_ton" not in db.users[key]:
            db.users[key]["balance_ton"] = 0
            changed = True
        if "balance_uah" not in db.users[key]:
            db.users[key]["balance_uah"] = 0
            changed = True
        if username and db.users[key].get("username") != username:
            db.users[key]["username"] = username
            changed = True
        if _ensure_user_game_stats(db.users[key]):
            changed = True
        if changed:
            db.save_data()
    return db.users[key]


async def safe_edit_message(query: CallbackQuery, text: str, **kwargs):
    try:
        if query.message:
            await query.message.edit_text(text, **kwargs)
    except TelegramBadRequest as e:
        err = str(e).lower()
        if "message is not modified" in err or "there is no text in the message to edit" in err:
            if query.message:
                await query.message.answer(text, **kwargs)
            return
        if query.message:
            await query.message.answer(text, **kwargs)
    except Exception as e:
        logger.exception("safe_edit_message error: %s", e)
        if query.message:
            await query.message.answer(text, **kwargs)


async def safe_answer_message(message: Message, text: str, **kwargs):
    try:
        await message.answer(text, **kwargs)
    except Exception as e:
        logger.exception("safe_answer_message error: %s", e)
