import asyncio
import time
from typing import Any

import requests

_BINANCE_TON_URL = "https://api.binance.com/api/v3/ticker/price?symbol=TONUSDT"
_NBU_USD_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json"
_CACHE_TTL_SECONDS = 30
_cache: dict[str, Any] = {
    "expires_at": 0.0,
    "ton_usdt": None,
    "usd_uah": None,
    "updated_at": 0.0,
}


def _fetch_ton_usdt_from_binance() -> float | None:
    try:
        response = requests.get(_BINANCE_TON_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data["price"])
    except Exception:
        return None


def _fetch_usd_uah_rate() -> float | None:
    try:
        response = requests.get(_NBU_USD_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data:
            return float(data[0]["rate"])
    except Exception:
        return None
    return None


def _refresh_cache() -> None:
    """Fetch fresh rates synchronously and update cache. Safe to run in a thread."""
    ton_usdt = _fetch_ton_usdt_from_binance()
    usd_uah = _fetch_usd_uah_rate()
    now = time.time()
    if ton_usdt is not None and usd_uah is not None:
        _cache.update({
            "expires_at": now + _CACHE_TTL_SECONDS,
            "ton_usdt": ton_usdt,
            "usd_uah": usd_uah,
            "updated_at": now,
        })


# ──────────────────────────────────────────────────────
# Sync API (for miniapp_backend / non-async callers)
# ──────────────────────────────────────────────────────

def get_ton_market_data() -> dict[str, float | None]:
    """Synchronous. Safe to call from non-async context (e.g. FastAPI/miniapp_backend)."""
    now = time.time()
    if _cache["expires_at"] > now and _cache["ton_usdt"] and _cache["usd_uah"]:
        return {
            "ton_usdt": float(_cache["ton_usdt"]),
            "usd_uah": float(_cache["usd_uah"]),
            "updated_at": float(_cache["updated_at"]),
        }
    _refresh_cache()
    return {
        "ton_usdt": _cache["ton_usdt"],
        "usd_uah": _cache["usd_uah"],
        "updated_at": float(_cache.get("updated_at") or now),
    }


def get_ton_uah_rate() -> float | None:
    data = get_ton_market_data()
    ton_usdt = data.get("ton_usdt")
    usd_uah = data.get("usd_uah")
    if ton_usdt is None or usd_uah is None:
        return None
    return float(ton_usdt) * float(usd_uah)


def get_ton_uah_sell_rate(markup_percent: float = 10.0) -> float | None:
    base_rate = get_ton_uah_rate()
    if base_rate is None:
        return None
    return base_rate * (1 + markup_percent / 100)


def uah_to_ton(uah_amount: float) -> float | None:
    rate = get_ton_uah_rate()
    if not rate:
        return None
    return round(float(uah_amount) / rate, 4)


def ton_to_uah_buy_price(ton_amount: float, markup_percent: float = 10.0) -> dict[str, float] | None:
    data = get_ton_market_data()
    ton_usdt = data.get("ton_usdt")
    usd_uah = data.get("usd_uah")
    if ton_usdt is None or usd_uah is None:
        return None

    ton_amount = float(ton_amount)
    base_uah_per_ton = float(ton_usdt) * float(usd_uah)
    final_uah_per_ton = base_uah_per_ton * (1 + markup_percent / 100)
    base_total_uah = ton_amount * base_uah_per_ton
    final_total_uah = ton_amount * final_uah_per_ton
    final_total_usdt = ton_amount * float(ton_usdt) * (1 + markup_percent / 100)

    return {
        "ton_amount": ton_amount,
        "ton_usdt": float(ton_usdt),
        "usd_uah": float(usd_uah),
        "base_uah_per_ton": base_uah_per_ton,
        "final_uah_per_ton": final_uah_per_ton,
        "base_total_uah": base_total_uah,
        "final_total_uah": final_total_uah,
        "final_total_usdt": final_total_usdt,
        "updated_at": float(data.get("updated_at") or time.time()),
        "markup_percent": float(markup_percent),
    }


# ──────────────────────────────────────────────────────
# Async API (for aiogram handlers — never blocks event loop)
# ──────────────────────────────────────────────────────

async def async_get_ton_market_data() -> dict[str, float | None]:
    """Async — runs HTTP fetches in a thread pool so the event loop is never blocked."""
    now = time.time()
    if _cache["expires_at"] > now and _cache["ton_usdt"] and _cache["usd_uah"]:
        return {
            "ton_usdt": float(_cache["ton_usdt"]),
            "usd_uah": float(_cache["usd_uah"]),
            "updated_at": float(_cache["updated_at"]),
        }
    await asyncio.to_thread(_refresh_cache)
    return {
        "ton_usdt": _cache["ton_usdt"],
        "usd_uah": _cache["usd_uah"],
        "updated_at": float(_cache.get("updated_at") or now),
    }


async def async_get_ton_uah_rate() -> float | None:
    data = await async_get_ton_market_data()
    ton_usdt = data.get("ton_usdt")
    usd_uah = data.get("usd_uah")
    if ton_usdt is None or usd_uah is None:
        return None
    return float(ton_usdt) * float(usd_uah)


async def async_uah_to_ton(uah_amount: float) -> float | None:
    rate = await async_get_ton_uah_rate()
    if not rate:
        return None
    return round(float(uah_amount) / rate, 4)


async def async_ton_to_uah_buy_price(ton_amount: float, markup_percent: float = 10.0) -> dict[str, float] | None:
    data = await async_get_ton_market_data()
    ton_usdt = data.get("ton_usdt")
    usd_uah = data.get("usd_uah")
    if ton_usdt is None or usd_uah is None:
        return None

    ton_amount = float(ton_amount)
    base_uah_per_ton = float(ton_usdt) * float(usd_uah)
    final_uah_per_ton = base_uah_per_ton * (1 + markup_percent / 100)
    base_total_uah = ton_amount * base_uah_per_ton
    final_total_uah = ton_amount * final_uah_per_ton
    final_total_usdt = ton_amount * float(ton_usdt) * (1 + markup_percent / 100)

    return {
        "ton_amount": ton_amount,
        "ton_usdt": float(ton_usdt),
        "usd_uah": float(usd_uah),
        "base_uah_per_ton": base_uah_per_ton,
        "final_uah_per_ton": final_uah_per_ton,
        "base_total_uah": base_total_uah,
        "final_total_uah": final_total_uah,
        "final_total_usdt": final_total_usdt,
        "updated_at": float(data.get("updated_at") or time.time()),
        "markup_percent": float(markup_percent),
    }
