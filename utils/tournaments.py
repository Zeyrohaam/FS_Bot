from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from database import db
from utils.helpers import add_star_balance, add_ton_balance, format_stars

METRIC_LABELS: dict[str, str] = {
    "max_single_win": "Самый большой разовый выигрыш",
    "total_win": "Сумма всех выигрышей",
    "max_single_purchase": "Самая большая разовая покупка звёзд",
    "total_stars_bought": "Общее количество купленных звёзд",
    "total_bet": "Общий оборот ставок",
    "games_won_count": "Количество побед",
}

GAME_LABELS: dict[str, str] = {
    "mines": "💣 Мины",
    "crash": "🚀 Краш",
    "roulette": "🎡 Рулетка",
    "coin": "🪙 Монетка",
    "cases": "🎁 Кейсы",
    "dice": "🎲 Кости",
    "tower": "🧗 Башня",
    "blackjack": "🃏 Блэкджек",
    "plinko": "🟢 Плинко",
    "upgrade": "⚡ Апгрейд",
}

MAX_STORED_GAME_EVENTS = 30000


def parse_datetime_flexible(value: str | datetime | None) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)

    val_str = str(value).strip()
    # Normalize ISO with 'Z' or timezone offset
    val_str = re.sub(r"([+-]\d{2}):?(\d{2})$", "", val_str)
    val_str = val_str.rstrip("Z")

    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt)
        except ValueError:
            continue
    return None


def record_game_event(
    user_id: int | str,
    game: str,
    bet: float,
    payout: float,
    currency: str = "stars",
    won: bool | None = None,
    timestamp: str | None = None,
    details: dict | None = None,
) -> dict:
    """Record a completed game round into db.game_events for tournament tracking."""
    now = datetime.now()
    now_iso = timestamp or now.isoformat()

    # Normalize bet and payout to Stars equivalent
    # 1 TON is roughly equivalent to ~250 Stars on average in the shop/pricing
    ton_to_stars_rate = 250.0
    if currency == "ton":
        bet_stars = round(float(bet) * ton_to_stars_rate, 1)
        payout_stars = round(float(payout) * ton_to_stars_rate, 1)
    else:
        bet_stars = round(float(bet), 1)
        payout_stars = round(float(payout), 1)

    is_win = (payout > bet) if won is None else bool(won)

    event = {
        "id": f"ge_{int(now.timestamp() * 1000)}_{uuid4().hex[:6]}",
        "user_id": int(user_id) if str(user_id).isdigit() else str(user_id),
        "game": str(game).strip().lower(),
        "bet": float(bet),
        "payout": float(payout),
        "currency": currency,
        "bet_stars": bet_stars,
        "payout_stars": payout_stars,
        "won": is_win,
        "timestamp": now_iso,
        "date": now.strftime("%d.%m.%Y %H:%M"),
        "details": details or {},
    }

    db.game_events.append(event)
    # Prune old events to prevent memory bloat
    if len(db.game_events) > MAX_STORED_GAME_EVENTS:
        db.game_events = db.game_events[-MAX_STORED_GAME_EVENTS:]

    return event


def get_tournament_status(tournament: dict) -> str:
    override = tournament.get("status")
    if override in ("finished", "cancelled"):
        return override

    now = datetime.now()
    start_dt = parse_datetime_flexible(tournament.get("start_time"))
    end_dt = parse_datetime_flexible(tournament.get("end_time"))

    if start_dt and now < start_dt:
        return "upcoming"
    if end_dt and now > end_dt:
        return "finished"
    return "active"


def format_score_value(score: float, metric: str) -> str:
    if metric == "games_won_count":
        return f"{int(score)} побед"
    if metric in ("max_single_purchase", "total_stars_bought", "max_single_win", "total_win", "total_bet"):
        return f"{format_stars(score)} ⭐"
    return f"{format_stars(score)}"


def create_tournament(
    title: str,
    description: str,
    metric: str,
    games: list[str] | None = None,
    start_time: str | datetime | None = None,
    end_time: str | datetime | None = None,
    prize_pool: float | int = 0,
    prizes: list[dict] | None = None,
    min_threshold: float = 0,
) -> dict:
    now = datetime.now()
    t_id = f"t_{int(now.timestamp())}_{uuid4().hex[:4]}"

    start_dt = parse_datetime_flexible(start_time) or now
    end_dt = parse_datetime_flexible(end_time)

    # Clean games list (irrelevant for purchase metrics)
    clean_games = []
    metric_str = str(metric).strip()
    if metric_str not in ("max_single_purchase", "total_stars_bought") and games:
        for g in games:
            g_str = str(g).strip().lower()
            if g_str in GAME_LABELS or g_str == "all":
                clean_games.append(g_str)

    # Standard prize distribution if empty (stars only)
    prizes_list = list(prizes or [])
    if not prizes_list and prize_pool > 0:
        p_val = float(prize_pool)
        prizes_list = [
            {"place": 1, "prize_type": "stars", "reward": round(p_val * 0.5)},
            {"place": 2, "prize_type": "stars", "reward": round(p_val * 0.3)},
            {"place": 3, "prize_type": "stars", "reward": round(p_val * 0.2)},
        ]

    # Normalise legacy prizes that don't have prize_type
    for p in prizes_list:
        if "prize_type" not in p:
            p["prize_type"] = "nft" if p.get("nft_model") else "stars"

    tournament = {
        "id": t_id,
        "title": str(title).strip(),
        "description": str(description).strip(),
        "metric": str(metric).strip(),
        "games": clean_games,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat() if end_dt else None,
        "prize_pool": float(prize_pool),
        "prizes": prizes_list,
        "min_threshold": float(min_threshold or 0),
        "status": "active",
        "prizes_distributed": False,
        "created_at": now.isoformat(),
    }

    db.tournaments.append(tournament)
    db.save_data()
    return tournament


def compute_tournament_leaderboard(tournament_id_or_dict: str | dict, requesting_user_id: int | str | None = None) -> dict:
    if isinstance(tournament_id_or_dict, dict):
        tournament = tournament_id_or_dict
    else:
        tournament = next((t for t in db.tournaments if str(t.get("id")) == str(tournament_id_or_dict)), None)
        if not tournament:
            return {"error": "Турнир не найден"}

    status = get_tournament_status(tournament)
    start_dt = parse_datetime_flexible(tournament.get("start_time"))
    end_dt = parse_datetime_flexible(tournament.get("end_time"))
    metric = tournament.get("metric", "max_single_win")
    allowed_games = set(tournament.get("games") or [])
    all_games_allowed = (not allowed_games) or ("all" in allowed_games)
    min_threshold = float(tournament.get("min_threshold", 0) or 0)

    # Map: user_id -> {"score": float, "best_time": datetime, "count": int}
    user_scores: dict[str, dict[str, Any]] = {}

    if metric in ("max_single_purchase", "total_stars_bought"):
        # Calculate from stars transactions — both confirmed AND pending
        # (pending = user submitted payment, should appear in leaderboard immediately)
        for t in db.transactions:
            if t.get("status") not in ("confirmed", "pending"):
                continue
            # Must be stars purchase with a positive star amount
            t_type = str(t.get("type", "")).lower()
            stars_amt = float(t.get("stars", 0) or 0)
            if t_type not in ("stars", "star") or stars_amt <= 0:
                continue

            # Only enforce date bounds if tournament has explicit start/end times
            if start_dt or end_dt:
                t_date = parse_datetime_flexible(t.get("date"))
                if t_date:
                    # Truncate to minute precision to avoid off-by-one-second issues
                    t_min = t_date.replace(second=0, microsecond=0)
                    if start_dt:
                        start_min = start_dt.replace(second=0, microsecond=0)
                        if t_min < start_min:
                            continue
                    if end_dt:
                        if t_date > end_dt:
                            continue

            if min_threshold > 0 and stars_amt < min_threshold:
                continue

            uid = str(t.get("user_id", ""))
            if not uid:
                continue

            t_date_fallback = parse_datetime_flexible(t.get("date")) or datetime.now()
            entry = user_scores.setdefault(uid, {"score": 0.0, "best_time": t_date_fallback, "count": 0})
            entry["count"] += 1

            if metric == "max_single_purchase":
                if stars_amt > entry["score"]:
                    entry["score"] = stars_amt
                    entry["best_time"] = t_date_fallback
            elif metric == "total_stars_bought":
                entry["score"] += stars_amt
                entry["best_time"] = max(entry["best_time"], t_date_fallback)

    elif metric in ("max_single_win", "total_win", "total_bet", "games_won_count"):
        # Calculate from game events
        for ge in db.game_events:
            ge_time = parse_datetime_flexible(ge.get("timestamp"))
            if not ge_time:
                continue

            # Check tournament time bounds (minute precision)
            if start_dt:
                start_min = start_dt.replace(second=0, microsecond=0)
                ge_min = ge_time.replace(second=0, microsecond=0)
                if ge_min < start_min:
                    continue
            if end_dt and ge_time > end_dt:
                continue

            # Check games filter
            ge_game = str(ge.get("game", "")).strip().lower()
            if not all_games_allowed and ge_game not in allowed_games:
                continue

            uid = str(ge.get("user_id", ""))
            if not uid:
                continue

            bet_val = float(ge.get("bet_stars", ge.get("bet", 0)) or 0)
            payout_val = float(ge.get("payout_stars", ge.get("payout", 0)) or 0)
            is_win = bool(ge.get("won", payout_val > bet_val))

            if min_threshold > 0 and bet_val < min_threshold:
                continue

            entry = user_scores.setdefault(uid, {"score": 0.0, "best_time": ge_time, "count": 0})

            if metric == "max_single_win":
                if payout_val > entry["score"]:
                    entry["score"] = payout_val
                    entry["best_time"] = ge_time
                    entry["count"] += 1
            elif metric == "total_win":
                if payout_val > 0:
                    entry["score"] += payout_val
                    entry["best_time"] = max(entry["best_time"], ge_time)
                    entry["count"] += 1
            elif metric == "total_bet":
                if bet_val > 0:
                    entry["score"] += bet_val
                    entry["best_time"] = max(entry["best_time"], ge_time)
                    entry["count"] += 1
            elif metric == "games_won_count":
                if is_win:
                    entry["score"] += 1.0
                    entry["best_time"] = max(entry["best_time"], ge_time)
                    entry["count"] += 1

    # Filter out entries with 0 score
    valid_entries = []
    for uid, data in user_scores.items():
        if data["score"] > 0:
            valid_entries.append({
                "user_id": uid,
                "score": data["score"],
                "best_time": data["best_time"],
                "count": data["count"],
            })

    # Sort descending by score; if tied, earlier best_time wins
    valid_entries.sort(key=lambda x: (-x["score"], x["best_time"]))

    prizes = tournament.get("prizes", [])

    leaderboard = []
    my_rank_info = None
    req_uid_str = str(requesting_user_id) if requesting_user_id is not None else None

    for rank_idx, item in enumerate(valid_entries, start=1):
        uid = item["user_id"]
        # Lookup user profile
        user_data = db.users.get(str(uid), {})
        first_name = user_data.get("first_name") or user_data.get("name")
        username = user_data.get("username")
        display_name = first_name or (f"@{username}" if username else f"Игрок #{str(uid)[-4:]}")

        # Find prize for this rank — include full prize metadata
        prize_cfg = None
        for p in prizes:
            try:
                if int(p.get("place", 0)) == rank_idx:
                    prize_cfg = p
                    break
            except (ValueError, TypeError):
                pass

        prize_type = str(prize_cfg.get("prize_type", "stars")).lower() if prize_cfg else "stars"
        prize_reward = prize_cfg.get("reward") if prize_cfg else None
        prize_nft_model = prize_cfg.get("nft_model") if prize_cfg else None
        prize_nft_name = prize_cfg.get("nft_name") if prize_cfg else None
        prize_nft_image = prize_cfg.get("nft_image") if prize_cfg else None
        prize_nft_value = prize_cfg.get("nft_value") if prize_cfg else None

        entry = {
            "rank": rank_idx,
            "user_id": uid,
            "display_name": display_name,
            "username": username,
            "score": round(item["score"], 1),
            "formatted_score": format_score_value(item["score"], metric),
            "prize": prize_reward,
            "prize_type": prize_type,
            "prize_nft_model": prize_nft_model,
            "prize_nft_name": prize_nft_name,
            "prize_nft_image": prize_nft_image,
            "prize_nft_value": prize_nft_value,
            "rounds_count": item["count"],
        }

        # Keep top 100 in returned leaderboard
        if rank_idx <= 100:
            leaderboard.append(entry)

        if req_uid_str and uid == req_uid_str:
            my_rank_info = dict(entry)

    if req_uid_str and not my_rank_info:
        my_rank_info = {
            "rank": None,
            "user_id": req_uid_str,
            "score": 0.0,
            "formatted_score": format_score_value(0, metric),
            "prize": None,
            "rounds_count": 0,
        }

    # Format human-friendly rules description
    metric_title = METRIC_LABELS.get(metric, metric)
    if metric in ("max_single_purchase", "total_stars_bought"):
        criteria_summary = metric_title
    elif allowed_games and "all" not in allowed_games:
        games_str = ", ".join(GAME_LABELS.get(g, g) for g in sorted(allowed_games))
        criteria_summary = f"{metric_title} · в играх: {games_str}"
    else:
        criteria_summary = f"{metric_title} · все игры"

    return {
        "ok": True,
        "tournament": {
            **tournament,
            "status": status,
            "metric_title": metric_title,
            "criteria_summary": criteria_summary,
            "total_participants": len(valid_entries),
        },
        "leaderboard": leaderboard,
        "my_rank": my_rank_info,
    }


def get_all_tournaments_summary(requesting_user_id: int | str | None = None) -> list[dict]:
    results = []
    # Sort tournaments: active first, upcoming next, finished last
    order_map = {"active": 0, "upcoming": 1, "finished": 2, "cancelled": 3}

    for t in db.tournaments:
        data = compute_tournament_leaderboard(t, requesting_user_id=requesting_user_id)
        if not data.get("ok"):
            continue
        tourn = data["tournament"]
        tourn["leaderboard_preview"] = data["leaderboard"][:3]
        tourn["my_rank"] = data["my_rank"]
        results.append(tourn)

    results.sort(key=lambda x: (
        order_map.get(x["status"], 9),
        x.get("end_time") or "9999",
    ))
    return results


def end_tournament(tournament_id: str) -> dict:
    t = next((item for item in db.tournaments if str(item.get("id")) == str(tournament_id)), None)
    if not t:
        return {"ok": False, "error": "Турнир не найден"}
    t["status"] = "finished"
    t["end_time"] = datetime.now().isoformat()
    db.save_data()
    return {"ok": True, "tournament": t}


def delete_tournament(tournament_id: str) -> dict:
    initial_len = len(db.tournaments)
    db.tournaments = [item for item in db.tournaments if str(item.get("id")) != str(tournament_id)]
    if len(db.tournaments) < initial_len:
        db.save_data()
        return {"ok": True}
    return {"ok": False, "error": "Турнир не найден"}


def distribute_tournament_prizes(tournament_id: str) -> dict:
    t = next((item for item in db.tournaments if str(item.get("id")) == str(tournament_id)), None)
    if not t:
        return {"ok": False, "error": "Турнир не найден"}

    if t.get("prizes_distributed"):
        return {"ok": False, "error": "Призы за этот турнир уже были начислены"}

    data = compute_tournament_leaderboard(t)
    leaderboard = data.get("leaderboard", [])
    prizes = t.get("prizes", [])

    # Build a lookup: place -> prize dict
    prize_by_place: dict[int, dict] = {}
    for p in prizes:
        try:
            prize_by_place[int(p.get("place", 0))] = p
        except (ValueError, TypeError):
            pass

    distributed = []
    for entry in leaderboard:
        rank = entry.get("rank")
        prize_cfg = prize_by_place.get(int(rank)) if rank else None
        if not prize_cfg:
            continue

        prize_type = str(prize_cfg.get("prize_type", "stars")).lower()
        uid = str(entry["user_id"])
        user_data = db.users.get(uid)
        if not user_data:
            continue

        if prize_type == "nft":
            # ── NFT: add to miniapp_inventory ─────────────────────
            nft_model = str(prize_cfg.get("nft_model", "")).strip()
            if not nft_model:
                continue
            nft_name = str(prize_cfg.get("nft_name") or nft_model.replace("-", " ").title())
            nft_image = str(prize_cfg.get("nft_image", "") or "")
            nft_value = int(prize_cfg.get("nft_value", 0) or 0)
            if nft_value >= 4500:
                rarity = "mythic"
            elif nft_value >= 2000:
                rarity = "legendary"
            elif nft_value >= 1000:
                rarity = "epic"
            elif nft_value >= 500:
                rarity = "rare"
            else:
                rarity = "common"

            nft_item = {
                "id": uuid4().hex,
                "kind": "gift",
                "label": nft_name,
                "name": nft_name,
                "model": nft_model,
                "value": nft_value,
                "icon": "🎁",
                "rarity": rarity,
                "image": nft_image,
                "source": "tournament_prize",
                "tournament_id": str(t.get("id", "")),
                "createdAt": datetime.now().isoformat(),
            }
            user_data.setdefault("miniapp_inventory", []).insert(0, nft_item)
            distributed.append({
                "user_id": uid,
                "rank": rank,
                "prize_type": "nft",
                "nft_model": nft_model,
                "nft_name": nft_name,
                "name": entry["display_name"],
            })

        elif prize_type == "ton":
            # ── TON: add to ton balance ────────────────────────────
            prize_val = prize_cfg.get("reward", entry.get("prize"))
            try:
                ton_award = float(prize_val)
            except (ValueError, TypeError):
                m = re.search(r"[\d.]+", str(prize_val))
                ton_award = float(m.group(0)) if m else 0.0

            if ton_award <= 0:
                continue

            add_ton_balance(user_data, ton_award)
            distributed.append({
                "user_id": uid,
                "rank": rank,
                "prize_type": "ton",
                "ton": ton_award,
                "name": entry["display_name"],
            })

        else:
            # ── Stars (default): add to star balance ───────────────
            prize_val = prize_cfg.get("reward", entry.get("prize"))
            try:
                stars_award = float(prize_val)
            except (ValueError, TypeError):
                m = re.search(r"\d+", str(prize_val))
                stars_award = float(m.group(0)) if m else 0.0

            if stars_award <= 0:
                continue

            add_star_balance(user_data, stars_award)
            distributed.append({
                "user_id": uid,
                "rank": rank,
                "prize_type": "stars",
                "stars": stars_award,
                "name": entry["display_name"],
            })

    t["prizes_distributed"] = True
    t["status"] = "finished"
    db.save_data()

    return {
        "ok": True,
        "distributed_count": len(distributed),
        "winners": distributed,
    }
