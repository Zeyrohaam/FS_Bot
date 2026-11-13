from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
CARDS_FILE = DATA_DIR / "cards_db.json"
_CARDS_LOCK = threading.RLock()

DEFAULT_CARD_1 = "4874 0700 5815 3352"
DEFAULT_CARD_2 = ""


def _default_cards_data() -> dict[str, Any]:
    # Try getting initial card from config if available
    card1 = DEFAULT_CARD_1
    try:
        import config
        if getattr(config, "MONO", None):
            card1 = str(config.MONO)
    except Exception:
        pass

    return {
        "card_1": card1,
        "card_2": DEFAULT_CARD_2,
        "active_card": 1,
    }


def load_cards_data() -> dict[str, Any]:
    with _CARDS_LOCK:
        if not CARDS_FILE.exists():
            data = _default_cards_data()
            save_cards_data(data)
            return data
        try:
            content = CARDS_FILE.read_text(encoding="utf-8")
            data = json.loads(content)
            if not isinstance(data, dict):
                data = _default_cards_data()
        except Exception:
            data = _default_cards_data()

        data.setdefault("card_1", DEFAULT_CARD_1)
        data.setdefault("card_2", DEFAULT_CARD_2)
        try:
            data["active_card"] = 2 if int(data.get("active_card", 1)) == 2 else 1
        except Exception:
            data["active_card"] = 1

        return data


def save_cards_data(data: dict[str, Any]) -> None:
    with _CARDS_LOCK:
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=DATA_DIR, delete=False) as tmp:
                tmp.write(payload)
                tmp_path = tmp.name

            replaced = False
            for _ in range(10):
                try:
                    os.replace(tmp_path, CARDS_FILE)
                    replaced = True
                    break
                except (PermissionError, OSError):
                    import time
                    time.sleep(0.05)

            if not replaced:
                with open(CARDS_FILE, "w", encoding="utf-8") as f:
                    f.write(payload)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        # Sync runtime in memory
        _sync_runtime_card(data)


def _sync_runtime_card(data: dict[str, Any]) -> None:
    active_num = get_active_card(data)
    try:
        import config
        config.MONO = active_num
        for mod_name in ("handlers.payments", "handlers.user", "miniapp.miniapp_backend"):
            mod = sys.modules.get(mod_name)
            if mod:
                setattr(mod, "MONO", active_num)
    except Exception:
        pass


def get_active_card(data: dict[str, Any] | None = None) -> str:
    if data is None:
        data = load_cards_data()
    active = data.get("active_card", 1)
    if active == 2:
        return (data.get("card_2") or data.get("card_1") or DEFAULT_CARD_1).strip()
    return (data.get("card_1") or DEFAULT_CARD_1).strip()


def set_active_card(card_index: int) -> dict[str, Any]:
    with _CARDS_LOCK:
        data = load_cards_data()
        data["active_card"] = 2 if int(card_index) == 2 else 1
        save_cards_data(data)
        data["active_card_number"] = get_active_card(data)
        return data


def update_card_number(card_index: int, number: str) -> dict[str, Any]:
    with _CARDS_LOCK:
        data = load_cards_data()
        clean_num = " ".join(str(number).strip().split())
        if int(card_index) == 2:
            data["card_2"] = clean_num
        else:
            data["card_1"] = clean_num
        save_cards_data(data)
        data["active_card_number"] = get_active_card(data)
        return data


def update_all_cards(
    card_1: str | None = None,
    card_2: str | None = None,
    active_card: int | None = None,
) -> dict[str, Any]:
    with _CARDS_LOCK:
        data = load_cards_data()
        if card_1 is not None:
            data["card_1"] = " ".join(str(card_1).strip().split())
        if card_2 is not None:
            data["card_2"] = " ".join(str(card_2).strip().split())
        if active_card is not None:
            data["active_card"] = 2 if int(active_card) == 2 else 1
        save_cards_data(data)
        data["active_card_number"] = get_active_card(data)
        return data
