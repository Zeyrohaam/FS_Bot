import json
import os
import tempfile
import threading
from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
_USERS_LOCK = threading.RLock()
_MISSING = object()


def _merge_user_value(base, local, remote, key=None):
    if local == base:
        return _MISSING if remote is _MISSING else deepcopy(remote)
    if remote == base:
        return _MISSING if local is _MISSING else deepcopy(local)

    if isinstance(local, dict) and isinstance(remote, dict):
        base_dict = base if isinstance(base, dict) else {}
        merged = {}
        for item_key in set(base_dict) | set(local) | set(remote):
            merged_value = _merge_user_value(
                base_dict.get(item_key, _MISSING),
                local.get(item_key, _MISSING),
                remote.get(item_key, _MISSING),
                item_key,
            )
            if merged_value is not _MISSING:
                merged[item_key] = merged_value
        return merged

    if key in {"balance_stars", "balance_ton", "total_stars", "referral_earnings_stars"}:
        if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (base, local, remote)):
            return remote + (local - base)

    if local is _MISSING:
        if remote is _MISSING:
            return _MISSING
        return deepcopy(remote)
    if remote is _MISSING:
        return _MISSING
    return deepcopy(local)


class Database:
    def __init__(self):
        self.users: dict[str, dict[str, Any]] = {}
        self.transactions: list[dict[str, Any]] = []
        self.reviews: list[dict[str, Any]] = []
        self.suggestions: list[dict[str, Any]] = []
        self.restricted_users: list[dict[str, Any] | int] = []
        self.sub_logs: list[dict[str, Any]] = []
        self.game_stats: dict[str, Any] = {}
        self.promocodes: list[dict[str, Any]] = []
        self.pricing_settings: dict[str, Any] = {}
        self.tournaments: list[dict[str, Any]] = []
        self.game_events: list[dict[str, Any]] = []
        self.transaction_id_counter: int = 1
        self.suggestion_id_counter: int = 1
        self._users_snapshot: dict[str, dict[str, Any]] = {}
        self.load_data()

    def _load_file(self, name: str, default: Any):
        path = DATA_DIR / name
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def _save_file(self, name: str, data: Any):
        path = DATA_DIR / name
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        # Atomic replace avoids partially written JSON when multiple processes save concurrently.
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=DATA_DIR, delete=False) as tmp:
            tmp.write(payload)
            tmp_path = tmp.name
        os.replace(tmp_path, path)

    @contextmanager
    def _users_file_lock(self):
        lock_path = DATA_DIR / "users_db.lock"
        with _USERS_LOCK:
            with lock_path.open("a+b") as handle:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    if handle.read(1) == b"":
                        handle.write(b"0")
                        handle.flush()
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                    try:
                        yield
                    finally:
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                    try:
                        yield
                    finally:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _save_users_file(self):
        with self._users_file_lock():
            latest = self._load_file("users_db.json", {})
            base = self._users_snapshot if isinstance(self._users_snapshot, dict) else {}
            local = self.users if isinstance(self.users, dict) else {}
            latest = latest if isinstance(latest, dict) else {}
            merged = _merge_user_value(base, local, latest)
            merged = merged if isinstance(merged, dict) else {}
            if isinstance(self.users, dict):
                for k in list(self.users.keys()):
                    if k not in merged:
                        del self.users[k]
                for k, v in merged.items():
                    if k in self.users and isinstance(self.users[k], dict) and isinstance(v, dict):
                        self.users[k].clear()
                        self.users[k].update(v)
                    else:
                        self.users[k] = v
            else:
                self.users = merged
            self._save_file("users_db.json", self.users)
            self._users_snapshot = deepcopy(self.users)

    def refresh(self):
        with _USERS_LOCK:
            if self.users and self.users != getattr(self, "_users_snapshot", None):
                self._save_users_file()
            self.load_data()

    def refresh_pricing_settings(self):
        self.pricing_settings = self._load_file("pricing_db.json", {})

    def load_data(self):
        loaded_users = self._load_file("users_db.json", {})
        if isinstance(self.users, dict) and isinstance(loaded_users, dict):
            for k in list(self.users.keys()):
                if k not in loaded_users:
                    del self.users[k]
            for k, v in loaded_users.items():
                if k in self.users and isinstance(self.users[k], dict) and isinstance(v, dict):
                    self.users[k].clear()
                    self.users[k].update(v)
                else:
                    self.users[k] = v
        else:
            self.users = loaded_users
        self._users_snapshot = deepcopy(self.users) if isinstance(self.users, dict) else {}
        self.transactions = self._load_file("transactions_db.json", [])
        self.reviews = self._load_file("reviews_db.json", [])
        self.suggestions = self._load_file("suggestions_db.json", [])
        self.restricted_users = self._load_file("restricted_db.json", [])
        self.sub_logs = self._load_file("sub_logs.json", [])
        self.game_stats = self._load_file("games_stats.json", {
            "mines": {
                "games_played": 0,
                "wins": 0,
                "losses": 0,
                "total_bet": 0,
                "total_paid_out": 0,
                "net_profit": 0,
            },
            "crash": {
                "games_played": 0,
                "wins": 0,
                "losses": 0,
                "total_bet": 0,
                "total_paid_out": 0,
                "net_profit": 0,
                "last_round_number": 0,
            },
            "roulette": {
                "games_played": 0,
                "wins": 0,
                "losses": 0,
                "total_bet": 0,
                "total_paid_out": 0,
                "net_profit": 0
            }
        })
        self.game_stats.setdefault("mines", {})
        self.game_stats.setdefault("crash", {})
        self.game_stats.setdefault("roulette", {})
        self.game_stats["crash"].setdefault("last_round_number", 0)
        self.promocodes = self._load_file("promocodes_db.json", [])
        self.pricing_settings = self._load_file("pricing_db.json", {})
        self.tournaments = self._load_file("tournaments_db.json", [])
        self.game_events = self._load_file("game_events_db.json", [])
        self.transaction_id_counter = max((int(t.get("id", 0)) for t in self.transactions if str(t.get("id", "")).isdigit()), default=0) + 1
        self.suggestion_id_counter = max((int(s.get("id", 0)) for s in self.suggestions if str(s.get("id", "")).isdigit()), default=0) + 1

    def _save_transactions_file(self):
        with _USERS_LOCK:
            latest = self._load_file("transactions_db.json", [])
            local_by_id = {int(t.get("id", 0)): t for t in self.transactions if str(t.get("id", "")).isdigit()}
            merged = []
            seen_ids = set()
            for t in latest:
                tid = int(t.get("id", 0)) if str(t.get("id", "")).isdigit() else None
                if tid is not None:
                    seen_ids.add(tid)
                    if tid in local_by_id:
                        merged.append(local_by_id[tid])
                    else:
                        merged.append(t)
                else:
                    merged.append(t)
            for tid, t in local_by_id.items():
                if tid not in seen_ids:
                    merged.append(t)
            self.transactions = merged
            self.transaction_id_counter = max((int(t.get("id", 0)) for t in self.transactions if str(t.get("id", "")).isdigit()), default=0) + 1
            self._save_file("transactions_db.json", self.transactions)

    def add_transaction(self, transaction: dict) -> dict:
        with _USERS_LOCK:
            latest = self._load_file("transactions_db.json", [])
            max_id = max((int(t.get("id", 0)) for t in latest if str(t.get("id", "")).isdigit()), default=0)
            cur_id = transaction.get("id")
            if cur_id is None or not str(cur_id).isdigit() or int(cur_id) <= max_id:
                transaction["id"] = max_id + 1
            latest.append(transaction)
            self._save_file("transactions_db.json", latest)
            self.transactions = latest
            self.transaction_id_counter = int(transaction["id"]) + 1
            return transaction

    def save_data(self):
        self._save_users_file()
        self._save_transactions_file()
        self._save_file("reviews_db.json", self.reviews)
        self._save_file("suggestions_db.json", self.suggestions)
        self._save_file("restricted_db.json", self.restricted_users)
        self._save_file("sub_logs.json", self.sub_logs)
        self._save_file("games_stats.json", self.game_stats)
        self._save_file("promocodes_db.json", self.promocodes)
        self._save_file("pricing_db.json", self.pricing_settings)
        self._save_file("tournaments_db.json", self.tournaments)
        self._save_file("game_events_db.json", self.game_events)

    def add_sub_log(self, user_id: int, username: str | None, channel: str, action: str):
        self.sub_logs.append({
            "user_id": user_id,
            "username": username or "unknown",
            "channel": channel,
            "action": action,
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        })
        self.save_data()

    def is_user_banned(self, user_id: int | str) -> bool:
        try:
            uid_int = int(user_id)
        except (ValueError, TypeError):
            uid_int = None
        uid_str = str(user_id)
        for item in self.restricted_users:
            if isinstance(item, dict):
                r_uid = item.get("user_id") or item.get("id")
                if r_uid is not None and (r_uid == uid_int or str(r_uid) == uid_str):
                    return True
            elif (uid_int is not None and item == uid_int) or str(item) == uid_str:
                return True
        return False

    def ban_user(self, user_id: int | str):
        try:
            uid_int = int(user_id)
        except (ValueError, TypeError):
            uid_int = None
        uid = uid_int if uid_int is not None else user_id
        if not self.is_user_banned(uid):
            self.restricted_users.append(uid)
            self.save_data()

    def unban_user(self, user_id: int | str):
        try:
            uid_int = int(user_id)
        except (ValueError, TypeError):
            uid_int = None
        uid_str = str(user_id)
        self.restricted_users = [
            item for item in self.restricted_users
            if not (
                (isinstance(item, dict) and (item.get('user_id') in (uid_int, uid_str) or item.get('id') in (uid_int, uid_str)))
                or (uid_int is not None and item == uid_int)
                or str(item) == uid_str
            )
        ]
        self.save_data()


db = Database()
