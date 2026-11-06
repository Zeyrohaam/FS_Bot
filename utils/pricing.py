from __future__ import annotations

from copy import deepcopy

from config import PREMIUM_PRICES, STARS_PRICES
from database import db

DEFAULT_STAR_RATES = [
    {"min": 50, "max": 149, "rate": 0.73},
    {"min": 150, "max": 499, "rate": 0.715},
    {"min": 500, "max": 1499, "rate": 0.692},
    {"min": 1500, "max": 10000, "rate": 0.674},
]
DEFAULT_STAR_PACKAGES = {int(k): float(v) for k, v in STARS_PRICES.items()}
DEFAULT_PREMIUM_PRICES = {int(k): float(v) for k, v in PREMIUM_PRICES.items()}
PACKAGE_SIZES = [50, 100, 150, 200, 250, 500]


def _default_pricing_settings() -> dict:
    return {
        "star_rates": deepcopy(DEFAULT_STAR_RATES),
        "star_packages": deepcopy(DEFAULT_STAR_PACKAGES),
        "premium_prices": deepcopy(DEFAULT_PREMIUM_PRICES),
    }


def ensure_pricing_settings() -> dict:
    db.refresh_pricing_settings()
    settings = getattr(db, "pricing_settings", None)
    if not isinstance(settings, dict):
        db.pricing_settings = _default_pricing_settings()
        db.save_data()
        return db.pricing_settings

    settings.setdefault("star_rates", deepcopy(DEFAULT_STAR_RATES))
    settings.setdefault("star_packages", deepcopy(DEFAULT_STAR_PACKAGES))
    settings.setdefault("premium_prices", deepcopy(DEFAULT_PREMIUM_PRICES))
    db.save_data()
    return settings


def get_star_rates() -> list[tuple[int, int, float]]:
    settings = ensure_pricing_settings()
    rates = []
    for item in settings.get("star_rates", []):
        try:
            rates.append((int(item["min"]), int(item["max"]), float(item["rate"])))
        except Exception:
            continue
    return rates or [(x["min"], x["max"], x["rate"]) for x in DEFAULT_STAR_RATES]


def get_star_packages() -> dict[int, float]:
    settings = ensure_pricing_settings()
    result: dict[int, float] = {}
    for key, value in settings.get("star_packages", {}).items():
        try:
            result[int(key)] = float(value)
        except Exception:
            continue
    return result or deepcopy(DEFAULT_STAR_PACKAGES)


def get_premium_prices() -> dict[int, float]:
    settings = ensure_pricing_settings()
    result: dict[int, float] = {}
    for key, value in settings.get("premium_prices", {}).items():
        try:
            result[int(key)] = float(value)
        except Exception:
            continue
    return result or deepcopy(DEFAULT_PREMIUM_PRICES)


def get_star_rate_for_amount(stars: int) -> float:
    for min_stars, max_stars, rate in get_star_rates():
        if min_stars <= stars <= max_stars:
            return float(rate)
    raise ValueError("Количество звёзд вне допустимого диапазона")


def calculate_dynamic_star_price(stars: int) -> float:
    return round(stars * get_star_rate_for_amount(stars), 2)


def rebuild_star_packages_from_rates() -> dict[int, float]:
    packages = {size: calculate_dynamic_star_price(size) for size in PACKAGE_SIZES}
    ensure_pricing_settings()["star_packages"] = packages
    db.save_data()
    return packages


def update_star_rates(new_rates: list[tuple[int, int, float]]) -> None:
    ensure_pricing_settings()["star_rates"] = [
        {"min": int(min_stars), "max": int(max_stars), "rate": float(rate)}
        for min_stars, max_stars, rate in new_rates
    ]
    # Keep star packages manual. Rates are informational for calculator/admin views only.
    db.save_data()


def update_star_packages(new_packages: dict[int, float]) -> None:
    ensure_pricing_settings()["star_packages"] = {int(k): float(v) for k, v in new_packages.items()}
    db.save_data()


def update_premium_prices(new_prices: dict[int, float]) -> None:
    ensure_pricing_settings()["premium_prices"] = {int(k): float(v) for k, v in new_prices.items()}
    db.save_data()
