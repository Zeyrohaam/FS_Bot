from __future__ import annotations

import json
import os
import tempfile
import threading
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from config import MONO, TON

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
SHIFTS_FILE = DATA_DIR / "shifts_db.json"
_SHIFTS_LOCK = threading.RLock()


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def _default_shifts_data() -> dict[str, Any]:
    return {
        "current_shift": None,
        "workers": [
            {
                "id": "worker_1",
                "name": "Основной сменщик",
                "telegram_id": None,
                "username": "admin",
                "mono_card": MONO,
                "ton_address": TON,
                "is_active": True,
                "notes": "Основная смена по умолчанию",
            }
        ],
        "shift_history": [],
        "x_reports": [],
    }


def load_shifts_data() -> dict[str, Any]:
    with _SHIFTS_LOCK:
        if not SHIFTS_FILE.exists():
            data = _default_shifts_data()
            save_shifts_data(data)
            return data
        try:
            content = SHIFTS_FILE.read_text(encoding="utf-8")
            data = json.loads(content)
            if not isinstance(data, dict):
                data = _default_shifts_data()
        except Exception:
            data = _default_shifts_data()

        data.setdefault("current_shift", None)
        data.setdefault("workers", [])
        data.setdefault("shift_history", [])
        data.setdefault("x_reports", [])
        if not data["workers"]:
            data["workers"] = _default_shifts_data()["workers"]
        return data


def save_shifts_data(data: dict[str, Any]) -> None:
    with _SHIFTS_LOCK:
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=DATA_DIR, delete=False) as tmp:
            tmp.write(payload)
            tmp_path = tmp.name
        os.replace(tmp_path, SHIFTS_FILE)


def get_workers() -> list[dict[str, Any]]:
    data = load_shifts_data()
    return deepcopy(data.get("workers", []))


def get_worker_by_id(worker_id: str) -> dict[str, Any] | None:
    for worker in get_workers():
        if str(worker.get("id")) == str(worker_id):
            return deepcopy(worker)
    return None


def get_worker_by_tg(telegram_id: int | str | None, username: str | None = None) -> dict[str, Any] | None:
    workers = get_workers()
    clean_tg = str(telegram_id) if telegram_id is not None else None
    clean_user = (username or "").strip().lstrip("@").lower()

    if clean_tg:
        for worker in workers:
            w_tg = worker.get("telegram_id")
            if w_tg is not None and str(w_tg) == clean_tg:
                return deepcopy(worker)

    if clean_user:
        for worker in workers:
            w_user = (worker.get("username") or "").strip().lstrip("@").lower()
            if w_user and w_user == clean_user:
                return deepcopy(worker)

    return None


def add_worker(
    name: str,
    mono_card: str,
    ton_address: str = "",
    telegram_id: int | str | None = None,
    username: str = "",
    notes: str = "",
    is_active: bool = True,
) -> dict[str, Any]:
    with _SHIFTS_LOCK:
        data = load_shifts_data()
        workers = data.setdefault("workers", [])
        worker_id = f"worker_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(workers) + 1}"
        new_worker = {
            "id": worker_id,
            "name": str(name).strip() or "Новый сменщик",
            "telegram_id": int(telegram_id) if str(telegram_id or "").isdigit() else None,
            "username": str(username or "").strip().lstrip("@"),
            "mono_card": str(mono_card or "").strip(),
            "ton_address": str(ton_address or "").strip(),
            "notes": str(notes or "").strip(),
            "is_active": bool(is_active),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        workers.append(new_worker)
        save_shifts_data(data)
        return deepcopy(new_worker)


def update_worker(worker_id: str, **kwargs) -> dict[str, Any] | None:
    with _SHIFTS_LOCK:
        data = load_shifts_data()
        workers = data.setdefault("workers", [])
        target = None
        for w in workers:
            if str(w.get("id")) == str(worker_id):
                target = w
                break
        if not target:
            return None

        for k, v in kwargs.items():
            if k == "telegram_id":
                target["telegram_id"] = int(v) if str(v or "").isdigit() else None
            elif k == "username":
                target["username"] = str(v or "").strip().lstrip("@")
            elif k in {"name", "mono_card", "ton_address", "notes"}:
                target[k] = str(v or "").strip()
            elif k == "is_active":
                target["is_active"] = bool(v)

        target["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # If current shift belongs to this worker, update current_shift snapshot details too
        cur = data.get("current_shift")
        if cur and str(cur.get("worker_id")) == str(worker_id):
            cur["worker_name"] = target["name"]
            cur["mono_card"] = target["mono_card"]
            cur["ton_address"] = target["ton_address"]
            cur["username"] = target["username"]
            cur["telegram_id"] = target["telegram_id"]

        save_shifts_data(data)
        return deepcopy(target)


def delete_worker(worker_id: str) -> bool:
    with _SHIFTS_LOCK:
        data = load_shifts_data()
        workers = data.get("workers", [])
        initial_len = len(workers)
        data["workers"] = [w for w in workers if str(w.get("id")) != str(worker_id)]
        if len(data["workers"]) == initial_len:
            return False

        cur = data.get("current_shift")
        if cur and str(cur.get("worker_id")) == str(worker_id):
            # Worker currently on shift was deleted -> close shift
            data["current_shift"] = None

        save_shifts_data(data)
        return True


def get_current_shift() -> dict[str, Any] | None:
    data = load_shifts_data()
    cur = data.get("current_shift")
    return deepcopy(cur) if cur else None


def get_active_payment_details() -> dict[str, Any]:
    shift = get_current_shift()
    if shift and shift.get("worker_id"):
        card = (shift.get("mono_card") or "").strip() or MONO
        ton_wallet = (shift.get("ton_address") or "").strip() or TON
        return {
            "shift_active": True,
            "shift_id": shift.get("shift_id"),
            "worker_id": shift.get("worker_id"),
            "worker_name": shift.get("worker_name", "Сменщик"),
            "mono_card": card,
            "ton_address": ton_wallet,
            "started_at": shift.get("started_at"),
        }
    return {
        "shift_active": False,
        "shift_id": None,
        "worker_id": None,
        "worker_name": None,
        "mono_card": MONO,
        "ton_address": TON,
        "started_at": None,
    }


def compute_shift_metrics(
    started_at_str: str | None,
    ended_at_str: str | None = None,
    shift_id: str | None = None,
) -> dict[str, Any]:
    from database import db

    start_dt = _parse_dt(started_at_str)
    end_dt = _parse_dt(ended_at_str) or datetime.now()

    effective_start = start_dt.replace(second=0, microsecond=0) if start_dt else None
    effective_end = end_dt.replace(second=59, microsecond=999999) if end_dt else None

    transactions = getattr(db, "transactions", []) or []
    shift_transactions: list[dict[str, Any]] = []

    for t in transactions:
        t_shift_id = t.get("shift_id")
        if shift_id and t_shift_id and str(shift_id) == str(t_shift_id):
            shift_transactions.append(t)
            continue

        t_dt = _parse_dt(t.get("date"))
        if not t_dt:
            continue
        if effective_start and t_dt < effective_start:
            continue
        if effective_end and t_dt > effective_end:
            continue
        shift_transactions.append(t)

    total_orders = len(shift_transactions)
    confirmed_orders = [t for t in shift_transactions if t.get("status") == "confirmed"]
    rejected_orders = [t for t in shift_transactions if t.get("status") == "rejected"]
    pending_orders = [t for t in shift_transactions if t.get("status") in {"pending", "waiting_proof"}]

    revenue_uah = 0.0
    revenue_ton = 0.0
    stars_sold = 0
    payouts_uah = 0.0
    payouts_ton = 0.0

    breakdown = {
        "stars_orders": 0,
        "premium_orders": 0,
        "ton_topup_orders": 0,
        "withdraw_orders": 0,
    }

    for t in confirmed_orders:
        t_type = str(t.get("type", ""))
        amount_uah = float(t.get("amount", 0) or 0)
        ton_amount = float(t.get("ton_amount", 0) or 0)
        stars = int(t.get("stars", 0) or 0)

        if "withdraw" in t_type:
            breakdown["withdraw_orders"] += 1
            if ton_amount > 0:
                payouts_ton += ton_amount
            else:
                payouts_uah += amount_uah
        else:
            if amount_uah > 0:
                revenue_uah += amount_uah
            if ton_amount > 0 and t.get("payment_method") in {"ton_wallet", "ton_balance"}:
                revenue_ton += ton_amount

            if "star" in t_type:
                breakdown["stars_orders"] += 1
                stars_sold += stars
            elif "premium" in t_type:
                breakdown["premium_orders"] += 1
            elif "ton" in t_type:
                breakdown["ton_topup_orders"] += 1

    return {
        "total_orders": total_orders,
        "confirmed_count": len(confirmed_orders),
        "rejected_count": len(rejected_orders),
        "pending_count": len(pending_orders),
        "revenue_uah": round(revenue_uah, 2),
        "revenue_ton": round(revenue_ton, 4),
        "stars_sold": stars_sold,
        "payouts_uah": round(payouts_uah, 2),
        "payouts_ton": round(payouts_ton, 4),
        "net_uah": round(revenue_uah - payouts_uah, 2),
        "net_ton": round(revenue_ton - payouts_ton, 4),
        "breakdown": breakdown,
        "transactions_count": len(shift_transactions),
    }


def start_shift(worker_id: str, actor_name: str = "Admin", actor_tg_id: int | str | None = None) -> dict[str, Any]:
    with _SHIFTS_LOCK:
        data = load_shifts_data()
        worker = None
        for w in data.get("workers", []):
            if str(w.get("id")) == str(worker_id):
                worker = w
                break

        if not worker:
            raise ValueError(f"Worker {worker_id} not found")

        cur = data.get("current_shift")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # If a shift was already open, automatically archive the previous shift and record handover
        if cur:
            metrics = compute_shift_metrics(cur.get("started_at"), now_str)
            cur_archive = deepcopy(cur)
            cur_archive["ended_at"] = now_str
            cur_archive["ended_by"] = actor_name
            cur_archive["close_type"] = "auto_transfer"
            cur_archive["metrics"] = metrics
            data.setdefault("shift_history", []).append(cur_archive)

        shift_id = f"shift_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        new_shift = {
            "shift_id": shift_id,
            "worker_id": str(worker["id"]),
            "worker_name": worker["name"],
            "telegram_id": worker.get("telegram_id"),
            "username": worker.get("username"),
            "mono_card": worker.get("mono_card") or MONO,
            "ton_address": worker.get("ton_address") or TON,
            "started_at": now_str,
            "started_by": actor_name,
            "started_by_tg": actor_tg_id,
            "transferred_from": cur.get("worker_name") if cur else None,
            "last_transferred_at": None,
        }
        data["current_shift"] = new_shift
        save_shifts_data(data)
        return deepcopy(new_shift)


def transfer_shift(
    new_worker_id: str,
    actor_name: str = "Admin",
    actor_tg_id: int | str | None = None,
) -> dict[str, Any]:
    with _SHIFTS_LOCK:
        data = load_shifts_data()
        worker = None
        for w in data.get("workers", []):
            if str(w.get("id")) == str(new_worker_id):
                worker = w
                break

        if not worker:
            raise ValueError(f"Worker {new_worker_id} not found")

        cur = data.get("current_shift")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        old_worker_name = cur.get("worker_name") if cur else "Никого"
        shift_id = cur.get("shift_id") if cur else f"shift_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        started_at = cur.get("started_at") if cur else now_str

        # Snapshot handover event to shift_history
        if cur:
            metrics = compute_shift_metrics(started_at, now_str, shift_id=shift_id)
            handover_log = {
                "shift_id": shift_id,
                "event": "handover",
                "from_worker_id": cur.get("worker_id"),
                "from_worker_name": old_worker_name,
                "to_worker_id": str(worker["id"]),
                "to_worker_name": worker["name"],
                "transferred_at": now_str,
                "transferred_by": actor_name,
                "metrics_until_transfer": metrics,
            }
            data.setdefault("shift_history", []).append(handover_log)

        updated_shift = {
            "shift_id": shift_id,
            "worker_id": str(worker["id"]),
            "worker_name": worker["name"],
            "telegram_id": worker.get("telegram_id"),
            "username": worker.get("username"),
            "mono_card": worker.get("mono_card") or MONO,
            "ton_address": worker.get("ton_address") or TON,
            "started_at": started_at,
            "started_by": cur.get("started_by") if cur else actor_name,
            "last_transferred_at": now_str,
            "transferred_from": old_worker_name,
            "transferred_by": actor_name,
        }
        data["current_shift"] = updated_shift
        save_shifts_data(data)
        return deepcopy(updated_shift)


def end_shift(actor_name: str = "Admin") -> dict[str, Any]:
    with _SHIFTS_LOCK:
        data = load_shifts_data()
        cur = data.get("current_shift")
        if not cur:
            raise ValueError("Нет активной смены для закрытия")

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report = generate_x_report(actor_name=actor_name, is_closing=True)

        shift_archive = deepcopy(cur)
        shift_archive["ended_at"] = now_str
        shift_archive["ended_by"] = actor_name
        shift_archive["close_type"] = "closed"
        shift_archive["final_report_id"] = report.get("report_id")
        shift_archive["metrics"] = report.get("metrics")

        data.setdefault("shift_history", []).append(shift_archive)
        data["current_shift"] = None
        save_shifts_data(data)
        return {
            "closed_shift": shift_archive,
            "z_report": report,
        }


def generate_x_report(actor_name: str = "Admin", is_closing: bool = False) -> dict[str, Any]:
    with _SHIFTS_LOCK:
        data = load_shifts_data()
        cur = data.get("current_shift")

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_type = "Z-ОТЧЕТ (ЗАКРЫТИЕ СМЕНЫ)" if is_closing else "X-ОТЧЕТ (ТЕКУЩИЙ)"
        prefix = "z" if is_closing else "x"
        report_id = f"{prefix}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        started_at = cur.get("started_at") if cur else now_str
        worker_id = cur.get("worker_id") if cur else None
        worker_name = cur.get("worker_name") if cur else "Без смены"
        shift_id = cur.get("shift_id") if cur else "no_shift"

        metrics = compute_shift_metrics(started_at, now_str, shift_id=shift_id)

        report = {
            "report_id": report_id,
            "shift_id": shift_id,
            "report_type": report_type,
            "is_closing": is_closing,
            "worker_id": worker_id,
            "worker_name": worker_name,
            "generated_at": now_str,
            "generated_by": actor_name,
            "period_start": started_at,
            "period_end": now_str,
            "mono_card": cur.get("mono_card") if cur else MONO,
            "ton_address": cur.get("ton_address") if cur else TON,
            "metrics": metrics,
        }

        # Keep last 500 reports logged
        reports = data.setdefault("x_reports", [])
        reports.append(report)
        if len(reports) > 500:
            data["x_reports"] = reports[-500:]

        save_shifts_data(data)
        return deepcopy(report)


def format_shift_status_text(shift: dict[str, Any] | None) -> str:
    if not shift:
        return (
            "⏱ <b>Статус смен: СМЕНА НЕ ОТКРЫТА</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "ℹ️ <i>Сейчас смена не закреплена ни за кем.</i>\n"
            "<i>Платежные реквизиты: стандартные реквизиты бота.</i>\n\n"
            "Нажмите <b>«Взять смену»</b> или выберите сменщика из списка."
        )

    started_at = shift.get("started_at", "—")
    duration_str = "—"
    dt_start = _parse_dt(started_at)
    if dt_start:
        delta = datetime.now() - dt_start
        hours = delta.seconds // 3600 + delta.days * 24
        minutes = (delta.seconds % 3600) // 60
        duration_str = f"{hours} ч {minutes} мин"

    metrics = compute_shift_metrics(started_at, shift_id=shift.get("shift_id"))
    username_str = f"@{shift.get('username')}" if shift.get("username") else "—"

    return (
        f"⏱ <b>Активная смена</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>На смене:</b> {shift.get('worker_name', 'Сменщик')}\n"
        f"📱 <b>Username:</b> {username_str}\n"
        f"💳 <b>Карта Mono:</b> <code>{shift.get('mono_card', MONO)}</code>\n"
        f"💠 <b>TON кошелек:</b> <code>{shift.get('ton_address', TON)}</code>\n\n"
        f"🕒 <b>Начало:</b> {started_at}\n"
        f"⏳ <b>Длительность:</b> {duration_str}\n"
        f"🔄 <b>Передана от:</b> {shift.get('transferred_from') or 'Новая смена'}\n\n"
        f"📊 <b>Показатели с начала смены:</b>\n"
        f"  • Всего заказов: <b>{metrics['total_orders']}</b>\n"
        f"  • Подтверждено: <b>{metrics['confirmed_count']}</b>\n"
        f"  • В ожидании: <b>{metrics['pending_count']}</b>\n"
        f"  • Выручка UAH: <b>{metrics['revenue_uah']:.2f} ₴</b>\n"
        f"  • Выручка TON: <b>{metrics['revenue_ton']:.4f} TON</b>\n"
        f"  • Звезд выдано: <b>{metrics['stars_sold']} ⭐</b>\n"
    )


def format_x_report_text(report: dict[str, Any]) -> str:
    m = report.get("metrics", {})
    bd = m.get("breakdown", {})
    is_closing = report.get("is_closing", False)
    header = "🧾 <b>Z-ОТЧЕТ (ЗАКРЫТИЕ СМЕНЫ)</b>" if is_closing else "📑 <b>X-ОТЧЕТ (ПРОМЕЖУТОЧНЫЙ)</b>"

    return (
        f"{header}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Отчет: <code>{report.get('report_id')}</code>\n"
        f"👤 Сменщик: <b>{report.get('worker_name', '—')}</b>\n"
        f"💳 Карта: <code>{report.get('mono_card', '—')}</code>\n"
        f"💠 TON: <code>{report.get('ton_address', '—')}</code>\n"
        f"🕒 Период: {report.get('period_start')} — {report.get('period_end')}\n"
        f"👨‍💻 Снял отчет: {report.get('generated_by', 'Admin')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>ИТОГИ:</b>\n"
        f"  • Всего заявок: <b>{m.get('total_orders', 0)}</b>\n"
        f"  • Подтверждено: <b>{m.get('confirmed_count', 0)}</b>\n"
        f"  • Отклонено: <b>{m.get('rejected_count', 0)}</b>\n"
        f"  • В обработке: <b>{m.get('pending_count', 0)}</b>\n\n"
        f"💰 <b>ФИНАНСЫ:</b>\n"
        f"  • Выручка (UAH): <b>{m.get('revenue_uah', 0.0):.2f} ₴</b>\n"
        f"  • Выручка (TON): <b>{m.get('revenue_ton', 0.0):.4f} TON</b>\n"
        f"  • Выплаты (UAH): <b>{m.get('payouts_uah', 0.0):.2f} ₴</b>\n"
        f"  • Выплаты (TON): <b>{m.get('payouts_ton', 0.0):.4f} TON</b>\n"
        f"  • Чистый итог UAH: <b>{m.get('net_uah', 0.0):.2f} ₴</b>\n"
        f"  • Чистый итог TON: <b>{m.get('net_ton', 0.0):.4f} TON</b>\n\n"
        f"📦 <b>ПРОДАЖИ:</b>\n"
        f"  • Stars куплено: <b>{m.get('stars_sold', 0)} ⭐</b>\n"
        f"  • Заказов Stars: <b>{bd.get('stars_orders', 0)}</b>\n"
        f"  • Telegram Premium: <b>{bd.get('premium_orders', 0)}</b>\n"
        f"  • Пополнений TON: <b>{bd.get('ton_topup_orders', 0)}</b>\n"
    )
