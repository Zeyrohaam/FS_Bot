from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from database import db

# Default drop tables with deterministic identifiers
CASE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "case150": {
        "label": "Летний кейс (150⭐️)",
        "cost": 150,
        "items": [
            {"id": "stars_25", "kind": "stars", "label": "25 звёзд", "name": "25 звёзд", "model": None, "value": 25, "icon": "⭐", "rarity": "common", "default_chance": 73.86},
            {"id": "lush-bouquet", "kind": "gift", "label": "Lush Bouquet", "name": "Lush Bouquet", "model": "lush-bouquet", "value": 517, "icon": "💐", "rarity": "rare", "default_chance": 4.0},
            {"id": "pool-float", "kind": "gift", "label": "Pool Float", "name": "Pool Float", "model": "pool-float", "value": 375, "icon": "🦒", "rarity": "common", "default_chance": 4.0},
            {"id": "instant-ramen", "kind": "gift", "label": "Instant Ramen", "name": "Instant Ramen", "model": "instant-ramen", "value": 337, "icon": "🍜", "rarity": "common", "default_chance": 5.0},
            {"id": "ice-cream", "kind": "gift", "label": "Ice Cream", "name": "Ice Cream", "model": "ice-cream", "value": 370, "icon": "🍦", "rarity": "common", "default_chance": 5.64},
            {"id": "ufc-box", "kind": "gift", "label": "UFC Strike", "name": "UFC Strike", "model": "ufc-box", "value": 1200, "icon": "🥊", "rarity": "epic", "default_chance": 3.0},
            {"id": "stellar-rocket", "kind": "gift", "label": "Stellar Rocket", "name": "Stellar Rocket", "model": "stellar-rocket", "value": 1100, "icon": "🚀", "rarity": "epic", "default_chance": 2.0},
            {"id": "chester-hat", "kind": "gift", "label": "Jester Hat", "name": "Jester Hat", "model": "chester-hat", "value": 950, "icon": "🎩", "rarity": "rare", "default_chance": 2.5},
        ]
    },
    "case250": {
        "label": "Завоз (250⭐️)",
        "cost": 250,
        "items": [
            {"id": "stars_25", "kind": "stars", "label": "25 звёзд", "name": "25 звёзд", "model": None, "value": 25, "icon": "⭐", "rarity": "common", "default_chance": 43.79},
            {"id": "stars_75", "kind": "stars", "label": "75 звёзд", "name": "75 звёзд", "model": None, "value": 75, "icon": "⭐", "rarity": "common", "default_chance": 43.79},
            {"id": "ice-cream", "kind": "gift", "label": "Ice Cream", "name": "Ice Cream", "model": "ice-cream", "value": 370, "icon": "🍦", "rarity": "common", "default_chance": 2.9},
            {"id": "liberty-figure", "kind": "gift", "label": "Statue of Liberty", "name": "Statue of Liberty", "model": "liberty-figure", "value": 335, "icon": "🗽", "rarity": "common", "default_chance": 2.7},
            {"id": "desk-calendar", "kind": "gift", "label": "Desk Calendar", "name": "Desk Calendar", "model": "desk-calendar", "value": 420, "icon": "📅", "rarity": "common", "default_chance": 2.1},
            {"id": "big-year", "kind": "gift", "label": "Big Year", "name": "Big Year", "model": "big-year", "value": 290, "icon": "🗓️", "rarity": "common", "default_chance": 3.2},
            {"id": "berry-box", "kind": "gift", "label": "Berry Box", "name": "Berry Box", "model": "berry-box", "value": 670, "icon": "🫐", "rarity": "rare", "default_chance": 1.5},
            {"id": "eternal-rose", "kind": "gift", "label": "Eternal Rose", "name": "Eternal Rose", "model": "eternal-rose", "value": 1957, "icon": "🌹", "rarity": "legendary", "default_chance": 0.01},
            {"id": "bonded-rind", "kind": "gift", "label": "Bonded Ring", "name": "Bonded Ring", "model": "bonded-rind", "value": 3768, "icon": "🧩", "rarity": "legendary", "default_chance": 0.01},
        ]
    },
    "case400": {
        "label": "Богатый (400⭐️)",
        "cost": 400,
        "items": [
            {"id": "stars_50", "kind": "stars", "label": "50 звёзд", "name": "50 звёзд", "model": None, "value": 50, "icon": "⭐", "rarity": "common", "default_chance": 25.1},
            {"id": "stars_100", "kind": "stars", "label": "100 звёзд", "name": "100 звёзд", "model": None, "value": 100, "icon": "⭐", "rarity": "common", "default_chance": 25.1},
            {"id": "candy-cane", "kind": "gift", "label": "Candy Cane", "name": "Candy Cane", "model": "candy-cane", "value": 370, "icon": "🍬", "rarity": "common", "default_chance": 14.9},
            {"id": "liberty-figure", "kind": "gift", "label": "Statue of Liberty", "name": "Statue of Liberty", "model": "liberty-figure", "value": 335, "icon": "🗽", "rarity": "common", "default_chance": 16.3},
            {"id": "love-candle", "kind": "gift", "label": "Love Candle", "name": "Love Candle", "model": "love-candle", "value": 731, "icon": "🕯️", "rarity": "rare", "default_chance": 8.2},
            {"id": "crystal-ball", "kind": "gift", "label": "Crystal Ball", "name": "Crystal Ball", "model": "crystal-ball", "value": 1100, "icon": "🔮", "rarity": "epic", "default_chance": 5.3},
            {"id": "flying-broom", "kind": "gift", "label": "Flying Broom", "name": "Flying Broom", "model": "flying-broom", "value": 1057, "icon": "🧹", "rarity": "epic", "default_chance": 4.9},
            {"id": "genie-lamp", "kind": "gift", "label": "Genie Lamp", "name": "Genie Lamp", "model": "genie-lamp", "value": 2200, "icon": "🪔", "rarity": "legendary", "default_chance": 0.2},
            {"id": "loot-bag", "kind": "gift", "label": "Loot Bag", "name": "Loot Bag", "model": "loot-bag", "value": 3768, "icon": "👜", "rarity": "legendary", "default_chance": 0.0},
        ]
    },
    "case600": {
        "label": "Лакшери (600⭐️)",
        "cost": 600,
        "items": [
            {"id": "stars_200", "kind": "stars", "label": "200 звёзд", "name": "200 звёзд", "model": None, "value": 200, "icon": "⭐", "rarity": "common", "default_chance": 33.85},
            {"id": "ginger-cookie", "kind": "gift", "label": "Ginger Cookie", "name": "Ginger Cookie", "model": "ginger-cookie", "value": 370, "icon": "🍪", "rarity": "common", "default_chance": 18.0},
            {"id": "liberty-figure", "kind": "gift", "label": "Statue of Liberty", "name": "Statue of Liberty", "model": "liberty-figure", "value": 335, "icon": "🗽", "rarity": "common", "default_chance": 15.0},
            {"id": "bunny-mafin", "kind": "gift", "label": "Bunny Muffin", "name": "Bunny Muffin", "model": "bunny-mafin", "value": 731, "icon": "🐰", "rarity": "rare", "default_chance": 16.0},
            {"id": "crystal-ball", "kind": "gift", "label": "Crystal Ball", "name": "Crystal Ball", "model": "crystal-ball", "value": 1100, "icon": "🔮", "rarity": "epic", "default_chance": 11.0},
            {"id": "eternal-rose", "kind": "gift", "label": "Eternal Rose", "name": "Eternal Rose", "model": "eternal-rose", "value": 1957, "icon": "🌹", "rarity": "legendary", "default_chance": 6.1},
            {"id": "magic-potion", "kind": "gift", "label": "Magic Potion", "name": "Magic Potion", "model": "magic-potion", "value": 5500, "icon": "🧪", "rarity": "mythic", "default_chance": 0.05},
            {"id": "astral-shard", "kind": "gift", "label": "Astral Shard", "name": "Astral Shard", "model": "astral-shard", "value": 1059, "icon": "✨", "rarity": "epic", "default_chance": 0.0},
        ]
    },
}


def _ensure_pricing_settings_dict() -> dict:
    if not isinstance(db.pricing_settings, dict):
        db.pricing_settings = {}
    return db.pricing_settings


def get_case_chances(tier: str | None = None) -> dict[str, Any]:
    """
    Returns custom chances for a specific case tier, or for all cases.
    Structure per tier: {item_id: float(chance_percent)}
    """
    settings = _ensure_pricing_settings_dict()
    saved = settings.get("case_drop_chances") if isinstance(settings.get("case_drop_chances"), dict) else {}

    result: dict[str, dict[str, float]] = {}
    for case_id, case_def in CASE_DEFINITIONS.items():
        case_saved = saved.get(case_id) if isinstance(saved.get(case_id), dict) else {}
        tier_chances: dict[str, float] = {}
        for item in case_def["items"]:
            item_id = item["id"]
            if item_id in case_saved:
                try:
                    val = float(case_saved[item_id])
                    tier_chances[item_id] = max(0.0, val)
                except (ValueError, TypeError):
                    tier_chances[item_id] = float(item["default_chance"])
            else:
                tier_chances[item_id] = float(item["default_chance"])
        result[case_id] = tier_chances

    if tier:
        return result.get(tier, {})
    return result


def set_case_chances(tier: str, chances: dict[str, float]) -> dict[str, float]:
    """
    Updates and persists custom chances for a specific case tier.
    """
    if tier not in CASE_DEFINITIONS:
        raise ValueError(f"Неизвестный кейс: {tier}")

    settings = _ensure_pricing_settings_dict()
    saved_all = settings.setdefault("case_drop_chances", {})
    if not isinstance(saved_all, dict):
        saved_all = {}
        settings["case_drop_chances"] = saved_all

    tier_chances = saved_all.setdefault(tier, {})
    for item in CASE_DEFINITIONS[tier]["items"]:
        item_id = item["id"]
        # Match by ID or by model or by label
        match_val = chances.get(item_id)
        if match_val is None and item.get("model"):
            match_val = chances.get(item["model"])
        if match_val is None:
            match_val = chances.get(item["label"])

        if match_val is not None:
            try:
                parsed = float(match_val)
                tier_chances[item_id] = max(0.0, parsed)
            except (ValueError, TypeError):
                pass

    db.save_data()
    return get_case_chances(tier)


def get_case_items(tier: str) -> list[dict[str, Any]]:
    """
    Returns the list of items for the given case with effective chances injected.
    """
    if tier not in CASE_DEFINITIONS:
        return []
    case_def = CASE_DEFINITIONS[tier]
    chances = get_case_chances(tier)
    items = []
    for base_item in case_def["items"]:
        item = deepcopy(base_item)
        chance = float(chances.get(item["id"], item["default_chance"]))
        item["chance_percent"] = round(chance, 4)
        item["weight"] = max(1, int(round(chance * 100)))
        items.append(item)
    return items


def format_case_chances_for_admin(tier: str) -> str:
    """
    Formats case prizes and drop chances nicely for Telegram Admin display.
    """
    if tier not in CASE_DEFINITIONS:
        return "❌ Кейс не найден."

    case_def = CASE_DEFINITIONS[tier]
    items = get_case_items(tier)
    total_chance = sum(item["chance_percent"] for item in items)

    lines = [
        f"🎲 <b>Шансы кейса: {case_def['label']}</b>",
        f"💰 Стоимость открытия: <b>{case_def['cost']} ⭐</b>",
        "━━━━━━━━━━━━━━━━━━",
    ]
    for idx, item in enumerate(items, 1):
        rarity_badge = {
            "common": "⚪ Обычный",
            "rare": "🔵 Редкий",
            "epic": "🟣 Эпический",
            "legendary": "🟠 Легендарный",
            "mythic": "🔴 Мифический",
        }.get(item.get("rarity", ""), "")
        val_str = f"({item['value']} ⭐)" if item.get("value") else ""
        lines.append(f"{idx}. {item['icon']} <b>{item['label']}</b> {val_str} — <b>{item['chance_percent']:.2f}%</b> [{rarity_badge}]")

    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append(f"📊 Сумма шансов: <b>{total_chance:.2f}%</b>")
    return "\n".join(lines)


def get_all_cases_summary_for_admin() -> str:
    """
    Formats summary of all cases for the admin menu.
    """
    sections = []
    for tier, cdef in CASE_DEFINITIONS.items():
        items = get_case_items(tier)
        preview_prizes = ", ".join(f"{it['icon']} {it['label']} ({it['chance_percent']:.2f}%)" for it in items[:4])
        if len(items) > 4:
            preview_prizes += f" и ещё {len(items) - 4} призов..."
        sections.append(
            f"📦 <b>{cdef['label']}</b> (цена: {cdef['cost']} ⭐)\n"
            f"Призов: {len(items)} шт. | {preview_prizes}"
        )

    return (
        "🎲 <b>Управление шансами выпадения из кейсов</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        + "\n\n".join(sections)
        + "\n\n<i>Выберите кейс ниже, чтобы просмотреть подробный список или изменить шансы:</i>"
    )
