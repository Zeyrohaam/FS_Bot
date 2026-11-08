from __future__ import annotations

import html
import json
import hmac
import hashlib
import math
import os
import random
import re
import secrets
import tempfile
import threading
import time
import shutil
from contextvars import ContextVar
import urllib.parse
import urllib.request
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4
import base64
import logging
import requests
import zipfile

logger = logging.getLogger(__name__)
_BALANCE_LOCK = threading.RLock()

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from config import (
    ADMIN_CHAT_ID,
    ADMIN_IDS,
    BACKEND_HOST,
    BACKEND_PORT,
    BOT_USERNAME,
    MONO,
    PREMIUM_SELLER_USERNAME,
    REVIEWS_CHANNEL,
    SUPPORT_USERNAME,
    TON,
    WEBAPP_URL,
    CLOUDFLARE_QUICK_TUNNEL_URL,
    CLOUDFLARE_CUSTOM_DOMAIN,
    WEBAPP_FALLBACK_URL,
    get_managed_settings,
    save_managed_settings,
)
from database import db
from config import GAMES_SETTINGS
from .miniapp_auth import MiniAppAuthError, TelegramMiniAppUser, validate_init_data
from .telegram_api import download_telegram_file, send_message, send_photo, send_photo_url, send_photo_bytes
from utils.cases import (
    CASE_DEFINITIONS,
    get_case_chances,
    get_case_items,
    set_case_chances,
)
from utils.helpers import add_star_balance, add_ton_balance, sub_star_balance, sub_ton_balance
from utils.pricing import (
    get_premium_prices,
    get_star_packages,
    get_star_rates,
    update_premium_prices,
    update_star_packages,
    update_star_rates,
)
from utils.referrals import bind_referral, get_user_referral_summary, reward_referrer_for_purchase
from utils.ton_rate import ton_to_uah_buy_price, uah_to_ton
from utils.tournaments import (
    compute_tournament_leaderboard,
    create_tournament,
    delete_tournament,
    distribute_tournament_prizes,
    end_tournament,
    get_all_tournaments_summary,
    record_game_event,
)
from utils.shifts import (
    add_worker,
    compute_shift_metrics,
    delete_worker,
    end_shift,
    format_shift_status_text,
    format_x_report_text,
    generate_x_report,
    get_active_payment_details,
    get_current_shift,
    get_worker_by_id,
    get_workers,
    load_shifts_data,
    save_shifts_data,
    start_shift,
    transfer_shift,
    update_worker,
)

BASE_DIR = Path(__file__).resolve().parent.parent
WEBAPP_DIR = BASE_DIR / 'miniapp' / 'webapp'

MINES_SETTINGS = GAMES_SETTINGS['mines']
CRASH_SETTINGS = GAMES_SETTINGS['crash']
ROULETTE_SETTINGS = GAMES_SETTINGS['roulette']
DICE_SETTINGS = GAMES_SETTINGS['dice']
CASE_SETTINGS = GAMES_SETTINGS['cases']
COIN_SETTINGS = GAMES_SETTINGS['coin']

CASINO_RACKET_OUTCOMES = [
    {'name': 'miss', 'label': 'Пролет', 'chance': 0.5, 'multiplier': 0.0},
    {'name': 'solid', 'label': 'Точный удар', 'chance': 0.35, 'multiplier': 1.6},
    {'name': 'ace', 'label': 'Эйс', 'chance': 0.15, 'multiplier': 2.5},
]

CASINO_CASES = CASE_SETTINGS

CASINO_UPGRADES = {
    'gift_wrap': {'label': 'Украшение подарка', 'cost': 140, 'bonus_stars': 0},
    'bonus_box': {'label': 'Усиленный бокс', 'cost': 310, 'bonus_stars': 40},
    'legendary_ribbon': {'label': 'Легендарная лента', 'cost': 660, 'bonus_stars': 120},
}

MIN_BET = float(MINES_SETTINGS['min_bet'])
MAX_BET = float(MINES_SETTINGS['max_bet'])
MINES_COUNT = int(MINES_SETTINGS['mines_count'])
MINES_MULTIPLIERS = list(MINES_SETTINGS['multipliers'])
MAX_SAFE_CLICKS = len(MINES_MULTIPLIERS)

CRASH_MIN_BET = float(CRASH_SETTINGS['min_bet'])
CRASH_MAX_BET = float(CRASH_SETTINGS['max_bet'])
CRASH_MIN_X = float(CRASH_SETTINGS['min_x'])
CRASH_MAX_X = float(CRASH_SETTINGS['max_x'])
CRASH_TARGET_RTP = float(CRASH_SETTINGS['target_rtp'])

ROULETTE_MIN_BET = float(ROULETTE_SETTINGS['min_bet'])
ROULETTE_MAX_BET = float(ROULETTE_SETTINGS['max_bet'])
ROULETTE_GREEN_PAYOUT = float(ROULETTE_SETTINGS['green_payout'])
TON_MIN_BET = 0.2

ALL_TELEGRAM_NFT_GIFTS: list[dict] = [
    {'model': 'lush-bouquet', 'name': 'Lush Bouquet', 'label': 'Lush Bouquet', 'default_stars': 517, 'image': 'https://nft.fragment.com/gift/LushBouquet-30203.medium.jpg', 'rarity': 'rare'},
    {'model': 'pool-float', 'name': 'Pool Float', 'label': 'Pool Float', 'default_stars': 375, 'image': 'https://nft.fragment.com/gift/PoolFloat-48197.medium.jpg', 'rarity': 'common'},
    {'model': 'instant-ramen', 'name': 'Instant Ramen', 'label': 'Instant Ramen', 'default_stars': 337, 'image': 'https://nft.fragment.com/gift/InstantRamen-10211.medium.jpg', 'rarity': 'common'},
    {'model': 'ice-cream', 'name': 'Ice Cream', 'label': 'Ice Cream', 'default_stars': 370, 'image': 'https://nft.fragment.com/gift/IceCream-44643.medium.jpg', 'rarity': 'common'},
    {'model': 'ufc-box', 'name': 'UFC Strike', 'label': 'UFC Strike', 'default_stars': 1200, 'image': 'https://nft.fragment.com/gift/UFCStrike-1718.medium.jpg', 'rarity': 'epic'},
    {'model': 'ginger-cookie', 'name': 'Ginger Cookie', 'label': 'Ginger Cookie', 'default_stars': 370, 'image': 'https://nft.fragment.com/gift/GingerCookie-55077.medium.jpg', 'rarity': 'common'},
    {'model': 'liberty-figure', 'name': 'Statue of Liberty', 'label': 'Statue of Liberty', 'default_stars': 335, 'image': '', 'rarity': 'common'},
    {'model': 'bunny-mafin', 'name': 'Bunny Muffin', 'label': 'Bunny Muffin', 'default_stars': 731, 'image': 'https://nft.fragment.com/gift/BunnyMuffin-42417.medium.jpg', 'rarity': 'rare'},
    {'model': 'crystal-ball', 'name': 'Crystal Ball', 'label': 'Crystal Ball', 'default_stars': 1100, 'image': 'https://nft.fragment.com/gift/CrystalBall-22131.medium.jpg', 'rarity': 'epic'},
    {'model': 'eternal-rose', 'name': 'Eternal Rose', 'label': 'Eternal Rose', 'default_stars': 1957, 'image': 'https://nft.fragment.com/gift/EternalRose-2743.medium.jpg', 'rarity': 'legendary'},
    {'model': 'magic-potion', 'name': 'Magic Potion', 'label': 'Magic Potion', 'default_stars': 5500, 'image': 'https://nft.fragment.com/gift/MagicPotion-3919.medium.jpg', 'rarity': 'mythic'},
    {'model': 'astral-shard', 'name': 'Astral Shard', 'label': 'Astral Shard', 'default_stars': 1059, 'image': 'https://nft.fragment.com/gift/AstralShard-3750.medium.jpg', 'rarity': 'epic'},
    {'model': 'candy-cane', 'name': 'Candy Cane', 'label': 'Candy Cane', 'default_stars': 370, 'image': 'https://nft.fragment.com/gift/CandyCane-67654.medium.jpg', 'rarity': 'common'},
    {'model': 'love-candle', 'name': 'Love Candle', 'label': 'Love Candle', 'default_stars': 731, 'image': 'https://nft.fragment.com/gift/LoveCandle-6779.medium.jpg', 'rarity': 'rare'},
    {'model': 'flying-broom', 'name': 'Flying Broom', 'label': 'Flying Broom', 'default_stars': 1057, 'image': 'https://nft.fragment.com/gift/FlyingBroom-14892.medium.jpg', 'rarity': 'epic'},
    {'model': 'genie-lamp', 'name': 'Genie Lamp', 'label': 'Genie Lamp', 'default_stars': 2200, 'image': 'https://nft.fragment.com/gift/GenieLamp-4819.medium.jpg', 'rarity': 'legendary'},
    {'model': 'loot-bag', 'name': 'Loot Bag', 'label': 'Loot Bag', 'default_stars': 3768, 'image': 'https://nft.fragment.com/gift/LootBag-1779.medium.jpg', 'rarity': 'legendary'},
    {'model': 'desk-calendar', 'name': 'Desk Calendar', 'label': 'Desk Calendar', 'default_stars': 420, 'image': 'https://nft.fragment.com/gift/DeskCalendar-86441.medium.jpg', 'rarity': 'common'},
    {'model': 'big-year', 'name': 'Big Year', 'label': 'Big Year', 'default_stars': 290, 'image': 'https://nft.fragment.com/gift/BigYear-57523.medium.jpg', 'rarity': 'common'},
    {'model': 'berry-box', 'name': 'Berry Box', 'label': 'Berry Box', 'default_stars': 670, 'image': 'https://nft.fragment.com/gift/BerryBox-36312.medium.jpg', 'rarity': 'rare'},
    {'model': 'bonded-rind', 'name': 'Bonded Ring', 'label': 'Bonded Ring', 'default_stars': 3768, 'image': 'https://nft.fragment.com/gift/BondedRing-3010.medium.jpg', 'rarity': 'legendary'},
    {'model': 'stellar-rocket', 'name': 'Stellar Rocket', 'label': 'Stellar Rocket', 'default_stars': 1100, 'image': 'https://nft.fragment.com/gift/StellarRocket-96957.medium.jpg', 'rarity': 'epic'},
    {'model': 'chester-hat', 'name': 'Jester Hat', 'label': 'Jester Hat', 'default_stars': 950, 'image': 'https://nft.fragment.com/gift/JesterHat-101105.medium.jpg', 'rarity': 'rare'},
    {'model': 'swiss-watch', 'name': 'Swiss Watch', 'label': 'Swiss Watch', 'default_stars': 1500, 'image': 'https://nft.fragment.com/gift/swisswatch-18663.medium.jpg', 'rarity': 'epic'},
    {'model': 'toy-bear', 'name': 'Toy Bear', 'label': 'Toy Bear', 'default_stars': 480, 'image': 'https://nft.fragment.com/gift/toybear-5257.medium.jpg', 'rarity': 'common'},
    {'model': 'diamond-ring', 'name': 'Diamond Ring', 'label': 'Diamond Ring', 'default_stars': 2800, 'image': 'https://nft.fragment.com/gift/diamondring-9059.medium.jpg', 'rarity': 'legendary'},
    {'model': 'perfume-bottle', 'name': 'Perfume Bottle', 'label': 'Perfume Bottle', 'default_stars': 850, 'image': 'https://nft.fragment.com/gift/perfumebottle-2822.medium.jpg', 'rarity': 'rare'},
    {'model': 'durov-cap', 'name': "Durov's Cap", 'label': "Durov's Cap", 'default_stars': 4500, 'image': 'https://nft.fragment.com/gift/durovscap-501.medium.jpg', 'rarity': 'legendary'},
    {'model': 'plush-pepe', 'name': 'Plush Pepe', 'label': 'Plush Pepe', 'default_stars': 8000, 'image': 'https://nft.fragment.com/gift/plushpepe-1056.medium.jpg', 'rarity': 'mythic'},
    {'model': 'mini-oscar', 'name': 'Mini Oscar', 'label': 'Mini Oscar', 'default_stars': 1750, 'image': 'https://nft.fragment.com/gift/minioscar-2207.medium.jpg', 'rarity': 'epic'},
    {'model': 'sharp-tongue', 'name': 'Sharp Tongue', 'label': 'Sharp Tongue', 'default_stars': 600, 'image': 'https://nft.fragment.com/gift/sharptongue-1511.medium.jpg', 'rarity': 'rare'},
    {'model': 'vintage-cigar', 'name': 'Vintage Cigar', 'label': 'Vintage Cigar', 'default_stars': 920, 'image': 'https://nft.fragment.com/gift/vintagecigar-5974.medium.jpg', 'rarity': 'rare'},
    {'model': 'snow-globe', 'name': 'Snow Globe', 'label': 'Snow Globe', 'default_stars': 550, 'image': 'https://nft.fragment.com/gift/snowglobe-17571.medium.jpg', 'rarity': 'common'},
    {'model': 'santa-hat', 'name': 'Santa Hat', 'label': 'Santa Hat', 'default_stars': 390, 'image': 'https://nft.fragment.com/gift/santahat-16799.medium.jpg', 'rarity': 'common'},
    {'model': 'jingle-bells', 'name': 'Jingle Bells', 'label': 'Jingle Bells', 'default_stars': 310, 'image': 'https://nft.fragment.com/gift/jinglebells-17151.medium.jpg', 'rarity': 'common'},
    {'model': 'homemade-cake', 'name': 'Homemade Cake', 'label': 'Homemade Cake', 'default_stars': 420, 'image': 'https://nft.fragment.com/gift/homemadecake-35678.medium.jpg', 'rarity': 'common'},
    {'model': 'spiced-wine', 'name': 'Spiced Wine', 'label': 'Spiced Wine', 'default_stars': 450, 'image': 'https://nft.fragment.com/gift/spicedwine-30494.medium.jpg', 'rarity': 'common'},
    {'model': 'jelly-bunny', 'name': 'Jelly Bunny', 'label': 'Jelly Bunny', 'default_stars': 520, 'image': 'https://nft.fragment.com/gift/jellybunny-66085.medium.jpg', 'rarity': 'rare'},
    {'model': 'ion-gem', 'name': 'Ion Gem', 'label': 'Ion Gem', 'default_stars': 2100, 'image': 'https://nft.fragment.com/gift/iongem-3514.medium.jpg', 'rarity': 'legendary'},
    {'model': 'precious-peach', 'name': 'Precious Peach', 'label': 'Precious Peach', 'default_stars': 3400, 'image': 'https://nft.fragment.com/gift/preciouspeach-246.medium.jpg', 'rarity': 'legendary'},
    {'model': 'heart-box', 'name': 'Heart Box', 'label': 'Heart Box', 'default_stars': 890, 'image': 'https://nft.fragment.com/gift/valentinebox-999.medium.jpg', 'rarity': 'rare'},
]


def get_rarity_by_stars(price: int | float | None) -> str:
    """Return rarity tier based strictly on stars value: higher price = higher rarity tier.
    - common: < 500 ⭐
    - rare: 500 - 999 ⭐
    - epic: 1000 - 1999 ⭐
    - legendary: 2000 - 4499 ⭐
    - mythic: >= 4500 ⭐
    """
    try:
        p = float(price or 0)
    except Exception:
        p = 0.0
    if p >= 4500:
        return 'mythic'
    if p >= 2000:
        return 'legendary'
    if p >= 1000:
        return 'epic'
    if p >= 500:
        return 'rare'
    return 'common'


for _gift_item in ALL_TELEGRAM_NFT_GIFTS:
    _gift_item['rarity'] = get_rarity_by_stars(_gift_item.get('default_stars'))

NFT_MODEL_DEFAULT_STARS: dict[str, int] = {
    x['model']: int(x['default_stars']) for x in ALL_TELEGRAM_NFT_GIFTS
}
STARS_PER_USDT = 75.0

COMMON_CASE_GIFT_CHANCE_PERCENT: dict[str, float] = {
    'lush-bouquet': 4.0,
    'pool-float': 4.0,
    'instant-ramen': 5.0,
    'ice-cream': 5.64,
    'ufc-box': 3.0,
    'ginger-cookie': 18.0,
    'liberty-figure': 15.0,
    'bunny-mafin': 16.0,
    'crystal-ball': 11.0,
    'eternal-rose': 6.1,
    'magic-potion': 0.05,
    'astral-shard': 0.0,
    'candy-cane': 14.9,
    'love-candle': 8.2,
    'flying-broom': 4.9,
    'genie-lamp': 0.2,
    'loot-bag': 0.0,
    'desk-calendar': 2.1,
    'big-year': 3.2,
    'berry-box': 1.5,
    'bonded-rind': 0.01,
    'stellar-rocket': 2.0,
    'chester-hat': 2.5,
}


def _get_nft_case_chances() -> dict[str, float]:
    settings = db.pricing_settings if isinstance(db.pricing_settings, dict) else {}
    stored = settings.get('nft_case_chances') if isinstance(settings, dict) else None
    result: dict[str, float] = {}

    if isinstance(stored, dict):
        for key, value in stored.items():
            model = str(key).strip().lower()
            parsed = _as_float(value)
            if parsed is None:
                continue
            result[model] = max(0.0, float(parsed))

    for model, fallback in COMMON_CASE_GIFT_CHANCE_PERCENT.items():
        result.setdefault(model, float(fallback))
    return result


def _set_nft_case_chances(values: dict[str, float]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for model, fallback in COMMON_CASE_GIFT_CHANCE_PERCENT.items():
        raw = values.get(model, fallback)
        parsed = _as_float(raw)
        if parsed is None:
            normalized[model] = float(fallback)
        else:
            normalized[model] = max(0.0, float(parsed))

    for model, raw in (values or {}).items():
        name = str(model).strip().lower()
        if name in normalized:
            continue
        parsed = _as_float(raw)
        if parsed is None:
            continue
        normalized[name] = max(0.0, float(parsed))

    settings = db.pricing_settings if isinstance(db.pricing_settings, dict) else {}
    settings['nft_case_chances'] = normalized
    db.pricing_settings = settings
    db.save_data()
    return normalized


def _resolve_case_gift_chance(item: dict, tier: str | None = None) -> float:
    active_tier = tier or item.get('_tier')
    if active_tier:
        custom_tier = get_case_chances(active_tier)
        item_id = item.get('id')
        if item_id and item_id in custom_tier:
            return float(custom_tier[item_id])
        model = str(item.get('model') or '').strip().lower()
        if model and model in custom_tier:
            return float(custom_tier[model])
        label = str(item.get('label') or '').strip().lower()
        if label and label in custom_tier:
            return float(custom_tier[label])

    model = str(item.get('model') or '').strip().lower()
    chances = _get_nft_case_chances()
    if model in chances:
        return float(chances[model])
    chance = float(item.get('chance_percent', item.get('weight', 0) or 0) or 0)
    if chance <= 0 and item.get('weight') is not None:
        chance = max(0.0, float(int(item.get('weight', 0) or 0)) / 100.0)
    return max(0.0, chance)


CASE150_DROP_TABLE = [
    {'id': 'stars_25', 'kind': 'stars', 'label': '25 звёзд', 'name': '25 звёзд', 'model': None, 'value': 25, 'icon': '⭐', 'rarity': 'common', 'chance_percent': 73.86, 'weight': 7386},
    {'id': 'lush-bouquet', 'kind': 'gift', 'label': 'Lush Bouquet', 'name': 'Lush Bouquet', 'model': 'lush-bouquet', 'value': NFT_MODEL_DEFAULT_STARS['lush-bouquet'], 'icon': '💐', 'rarity': 'rare', 'chance_percent': 4.0, 'weight': 400},
    {'id': 'pool-float', 'kind': 'gift', 'label': 'Pool Float', 'name': 'Pool Float', 'model': 'pool-float', 'value': NFT_MODEL_DEFAULT_STARS['pool-float'], 'icon': '🦒', 'rarity': 'common', 'chance_percent': 4.0, 'weight': 400},
    {'id': 'instant-ramen', 'kind': 'gift', 'label': 'Instant Ramen', 'name': 'Instant Ramen', 'model': 'instant-ramen', 'value': NFT_MODEL_DEFAULT_STARS['instant-ramen'], 'icon': '🍜', 'rarity': 'common', 'chance_percent': 5.0, 'weight': 500},
    {'id': 'ice-cream', 'kind': 'gift', 'label': 'Ice Cream', 'name': 'Ice Cream', 'model': 'ice-cream', 'value': NFT_MODEL_DEFAULT_STARS['ice-cream'], 'icon': '🍦', 'rarity': 'common', 'chance_percent': 5.64, 'weight': 564},
    {'id': 'ufc-box', 'kind': 'gift', 'label': 'UFC Strike', 'name': 'UFC Strike', 'model': 'ufc-box', 'value': NFT_MODEL_DEFAULT_STARS['ufc-box'], 'icon': '🥊', 'rarity': 'epic', 'chance_percent': 3.0, 'weight': 300},
    {'id': 'stellar-rocket', 'kind': 'gift', 'label': 'Stellar Rocket', 'name': 'Stellar Rocket', 'model': 'stellar-rocket', 'value': NFT_MODEL_DEFAULT_STARS['stellar-rocket'], 'icon': '🚀', 'rarity': 'rare', 'chance_percent': 2.0, 'weight': 200},
    {'id': 'chester-hat', 'kind': 'gift', 'label': 'Jester Hat', 'name': 'Jester Hat', 'model': 'chester-hat', 'value': NFT_MODEL_DEFAULT_STARS['chester-hat'], 'icon': '🎩', 'rarity': 'common', 'chance_percent': 2.5, 'weight': 250},
]

CASE600_DROP_TABLE = [
    {'id': 'stars_200', 'kind': 'stars', 'label': '200 звёзд', 'name': '200 звёзд', 'model': None, 'value': 200, 'icon': '⭐', 'rarity': 'common', 'chance_percent': 33.85},
    {'id': 'ginger-cookie', 'kind': 'gift', 'label': 'Ginger Cookie', 'name': 'Ginger Cookie', 'model': 'ginger-cookie', 'value': NFT_MODEL_DEFAULT_STARS['ginger-cookie'], 'icon': '🍪', 'rarity': 'common', 'chance_percent': 18.0},
    {'id': 'liberty-figure', 'kind': 'gift', 'label': 'Liberty Figure', 'name': 'Liberty Figure', 'model': 'liberty-figure', 'value': NFT_MODEL_DEFAULT_STARS['liberty-figure'], 'icon': '🗽', 'rarity': 'common', 'chance_percent': 15.0},
    {'id': 'bunny-mafin', 'kind': 'gift', 'label': 'Bunny Muffin', 'name': 'Bunny Muffin', 'model': 'bunny-mafin', 'value': NFT_MODEL_DEFAULT_STARS['bunny-mafin'], 'icon': '🐰', 'rarity': 'rare', 'chance_percent': 16.0},
    {'id': 'crystal-ball', 'kind': 'gift', 'label': 'Crystal Ball', 'name': 'Crystal Ball', 'model': 'crystal-ball', 'value': NFT_MODEL_DEFAULT_STARS['crystal-ball'], 'icon': '🔮', 'rarity': 'epic', 'chance_percent': 11.0},
    {'id': 'eternal-rose', 'kind': 'gift', 'label': 'Eternal Rose', 'name': 'Eternal Rose', 'model': 'eternal-rose', 'value': NFT_MODEL_DEFAULT_STARS['eternal-rose'], 'icon': '🌹', 'rarity': 'legendary', 'chance_percent': 6.1},
    {'id': 'magic-potion', 'kind': 'gift', 'label': 'Magic Potion', 'name': 'Magic Potion', 'model': 'magic-potion', 'value': NFT_MODEL_DEFAULT_STARS['magic-potion'], 'icon': '🧪', 'rarity': 'mythic', 'chance_percent': 0.05},
    {'id': 'astral-shard', 'kind': 'gift', 'label': 'Astral Shard', 'name': 'Astral Shard', 'model': 'astral-shard', 'value': NFT_MODEL_DEFAULT_STARS['astral-shard'], 'icon': '✨', 'rarity': 'mythic', 'chance_percent': 0.0},
]

CASE400_DROP_TABLE = [
    {'id': 'stars_50', 'kind': 'stars', 'label': '50 звёзд', 'name': '50 звёзд', 'model': None, 'value': 50, 'icon': '⭐', 'rarity': 'common', 'chance_percent': 25.1},
    {'id': 'stars_100', 'kind': 'stars', 'label': '100 звёзд', 'name': '100 звёзд', 'model': None, 'value': 100, 'icon': '⭐', 'rarity': 'common', 'chance_percent': 25.1},
    {'id': 'candy-cane', 'kind': 'gift', 'label': 'Candy Cane', 'name': 'Candy Cane', 'model': 'candy-cane', 'value': NFT_MODEL_DEFAULT_STARS['candy-cane'], 'icon': '🍬', 'rarity': 'common', 'chance_percent': 14.9},
    {'id': 'liberty-figure', 'kind': 'gift', 'label': 'Liberty Figure', 'name': 'Liberty Figure', 'model': 'liberty-figure', 'value': NFT_MODEL_DEFAULT_STARS['liberty-figure'], 'icon': '🗽', 'rarity': 'common', 'chance_percent': 16.3},
    {'id': 'love-candle', 'kind': 'gift', 'label': 'Love Candle', 'name': 'Love Candle', 'model': 'love-candle', 'value': NFT_MODEL_DEFAULT_STARS['love-candle'], 'icon': '🕯️', 'rarity': 'rare', 'chance_percent': 8.2},
    {'id': 'crystal-ball', 'kind': 'gift', 'label': 'Crystal Ball', 'name': 'Crystal Ball', 'model': 'crystal-ball', 'value': NFT_MODEL_DEFAULT_STARS['crystal-ball'], 'icon': '🔮', 'rarity': 'epic', 'chance_percent': 5.3},
    {'id': 'flying-broom', 'kind': 'gift', 'label': 'Flying Broom', 'name': 'Flying Broom', 'model': 'flying-broom', 'value': NFT_MODEL_DEFAULT_STARS['flying-broom'], 'icon': '🧹', 'rarity': 'rare', 'chance_percent': 4.9},
    {'id': 'genie-lamp', 'kind': 'gift', 'label': 'Genie Lamp', 'name': 'Genie Lamp', 'model': 'genie-lamp', 'value': NFT_MODEL_DEFAULT_STARS['genie-lamp'], 'icon': '🪔', 'rarity': 'legendary', 'chance_percent': 0.2},
    {'id': 'loot-bag', 'kind': 'gift', 'label': 'Loot Bag', 'name': 'Loot Bag', 'model': 'loot-bag', 'value': NFT_MODEL_DEFAULT_STARS['loot-bag'], 'icon': '👜', 'rarity': 'mythic', 'chance_percent': 0.0},
]

CASE250_DROP_TABLE = [
    {'id': 'stars_25', 'kind': 'stars', 'label': '25 звёзд', 'name': '25 звёзд', 'model': None, 'value': 25, 'icon': '⭐', 'rarity': 'common', 'chance_percent': 43.79},
    {'id': 'stars_75', 'kind': 'stars', 'label': '75 звёзд', 'name': '75 звёзд', 'model': None, 'value': 75, 'icon': '⭐', 'rarity': 'common', 'chance_percent': 43.79},
    {'id': 'ice-cream', 'kind': 'gift', 'label': 'Ice Cream', 'name': 'Ice Cream', 'model': 'ice-cream', 'value': NFT_MODEL_DEFAULT_STARS['ice-cream'], 'icon': '🍦', 'rarity': 'common', 'chance_percent': 2.9},
    {'id': 'liberty-figure', 'kind': 'gift', 'label': 'Liberty Figure', 'name': 'Liberty Figure', 'model': 'liberty-figure', 'value': NFT_MODEL_DEFAULT_STARS['liberty-figure'], 'icon': '🗽', 'rarity': 'common', 'chance_percent': 2.7},
    {'id': 'desk-calendar', 'kind': 'gift', 'label': 'Desk Calendar', 'name': 'Desk Calendar', 'model': 'desk-calendar', 'value': NFT_MODEL_DEFAULT_STARS['desk-calendar'], 'icon': '📅', 'rarity': 'common', 'chance_percent': 2.1},
    {'id': 'big-year', 'kind': 'gift', 'label': 'Big Year', 'name': 'Big Year', 'model': 'big-year', 'value': NFT_MODEL_DEFAULT_STARS['big-year'], 'icon': '🗓️', 'rarity': 'common', 'chance_percent': 3.2},
    {'id': 'berry-box', 'kind': 'gift', 'label': 'Berry Box', 'name': 'Berry Box', 'model': 'berry-box', 'value': NFT_MODEL_DEFAULT_STARS['berry-box'], 'icon': '🫐', 'rarity': 'rare', 'chance_percent': 1.5},
    {'id': 'eternal-rose', 'kind': 'gift', 'label': 'Eternal Rose', 'name': 'Eternal Rose', 'model': 'eternal-rose', 'value': NFT_MODEL_DEFAULT_STARS['eternal-rose'], 'icon': '🌹', 'rarity': 'legendary', 'chance_percent': 0.01},
    {'id': 'bonded-rind', 'kind': 'gift', 'label': 'Bonded Ring', 'name': 'Bonded Ring', 'model': 'bonded-rind', 'value': NFT_MODEL_DEFAULT_STARS['bonded-rind'], 'icon': '🧩', 'rarity': 'legendary', 'chance_percent': 0.01},
]

for _drop_table in (CASE150_DROP_TABLE, CASE250_DROP_TABLE, CASE400_DROP_TABLE, CASE600_DROP_TABLE):
    for _drop_item in _drop_table:
        _drop_item['rarity'] = get_rarity_by_stars(_drop_item.get('value'))

SPECIAL_CASES_CONFIG = {
    'case250': {'label': 'Завоз (250⭐️)', 'cost': 250, 'drop_table': CASE250_DROP_TABLE},
    'case400': {'label': 'Богатый (400⭐️)', 'cost': 400, 'drop_table': CASE400_DROP_TABLE},
    'case600': {'label': 'Лакшери (600⭐️)', 'cost': 600, 'drop_table': CASE600_DROP_TABLE},
}

DEFAULT_GAME_RTP_PERCENT: dict[str, float] = {
    'mines': 95.0,
    'crash': 95.0,
    'roulette': 95.0,
    'cases': 86.0,
    'case150': 86.0,
    'case250': 88.0,
    'case400': 90.0,
    'case600': 92.0,
    'upgrade': 95.0,
}


def _as_float(value) -> float | None:
    try:
        parsed = float(value)
    except Exception:
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _get_game_rtp_settings() -> dict[str, float]:
    settings = db.pricing_settings if isinstance(db.pricing_settings, dict) else {}
    raw = settings.get('game_rtp_percent') if isinstance(settings, dict) else None
    result: dict[str, float] = {}

    if isinstance(raw, dict):
        for game, value in raw.items():
            name = str(game).strip().lower()
            if name not in DEFAULT_GAME_RTP_PERCENT:
                continue
            parsed = _as_float(value)
            if parsed is None:
                continue
            result[name] = max(1.0, min(500.0, float(parsed)))

    for game, default_value in DEFAULT_GAME_RTP_PERCENT.items():
        result.setdefault(game, float(default_value))
    return result


def _set_game_rtp_settings(values: dict[str, float]) -> dict[str, float]:
    current = _get_game_rtp_settings()
    updated = dict(current)
    for key, value in values.items():
        name = str(key).strip().lower()
        if name not in DEFAULT_GAME_RTP_PERCENT:
            continue
        parsed = _as_float(value)
        if parsed is None:
            continue
        updated[name] = max(1.0, min(500.0, float(parsed)))

    settings = db.pricing_settings if isinstance(db.pricing_settings, dict) else {}
    settings['game_rtp_percent'] = updated
    db.pricing_settings = settings
    db.save_data()
    return updated


def _get_coin_settings() -> dict[str, object]:
    settings = db.pricing_settings if isinstance(db.pricing_settings, dict) else {}
    raw = settings.get('coin_game_settings') if isinstance(settings, dict) else None
    default_odds = {
        'eagle': float(COIN_SETTINGS.get('odds', {}).get('eagle', 45.0)),
        'tails': float(COIN_SETTINGS.get('odds', {}).get('tails', 45.0)),
        'edge': float(COIN_SETTINGS.get('odds', {}).get('edge', 10.0)),
    }
    default_multipliers = {
        'eagle': float(COIN_SETTINGS.get('multipliers', {}).get('eagle', 2.0)),
        'tails': float(COIN_SETTINGS.get('multipliers', {}).get('tails', 2.0)),
        'edge': float(COIN_SETTINGS.get('multipliers', {}).get('edge', 5.0)),
    }
    result = {
        'min_bet': float(COIN_SETTINGS.get('min_bet', 5)),
        'max_bet': float(COIN_SETTINGS.get('max_bet', 10000)),
        'odds': default_odds,
        'multipliers': default_multipliers,
    }

    if isinstance(raw, dict):
        min_bet = _as_float(raw.get('min_bet'))
        max_bet = _as_float(raw.get('max_bet'))
        if min_bet is not None and min_bet > 0:
            result['min_bet'] = min_bet
        if max_bet is not None and max_bet >= result['min_bet']:
            result['max_bet'] = max_bet

        odds_raw = raw.get('odds') if isinstance(raw.get('odds'), dict) else None
        if isinstance(odds_raw, dict):
            for option in ('eagle', 'tails', 'edge'):
                parsed = _as_float(odds_raw.get(option))
                if parsed is not None and parsed >= 0:
                    result['odds'][option] = parsed

        multiplier_raw = raw.get('multipliers') if isinstance(raw.get('multipliers'), dict) else None
        if isinstance(multiplier_raw, dict):
            for option in ('eagle', 'tails', 'edge'):
                parsed = _as_float(multiplier_raw.get(option))
                if parsed is not None and parsed >= 0.01:
                    result['multipliers'][option] = parsed

    return result


def _set_coin_settings(values: dict[str, object]) -> dict[str, object]:
    current = _get_coin_settings()
    updated = {
        'min_bet': current['min_bet'],
        'max_bet': current['max_bet'],
        'odds': dict(current['odds']),
        'multipliers': dict(current['multipliers']),
    }

    if isinstance(values, dict):
        min_bet = _as_float(values.get('min_bet'))
        max_bet = _as_float(values.get('max_bet'))
        if min_bet is not None and min_bet > 0:
            updated['min_bet'] = min_bet
        if max_bet is not None and max_bet >= updated['min_bet']:
            updated['max_bet'] = max_bet

        odds_raw = values.get('odds') if isinstance(values.get('odds'), dict) else None
        if isinstance(odds_raw, dict):
            for option in ('eagle', 'tails', 'edge'):
                parsed = _as_float(odds_raw.get(option))
                if parsed is not None and parsed >= 0:
                    updated['odds'][option] = parsed

        multipliers_raw = values.get('multipliers') if isinstance(values.get('multipliers'), dict) else None
        if isinstance(multipliers_raw, dict):
            for option in ('eagle', 'tails', 'edge'):
                parsed = _as_float(multipliers_raw.get(option))
                if parsed is not None and parsed >= 0.01:
                    updated['multipliers'][option] = parsed

    settings = db.pricing_settings if isinstance(db.pricing_settings, dict) else {}
    settings['coin_game_settings'] = updated
    db.pricing_settings = settings
    db.save_data()
    return updated


def _get_game_rtp_percent(game: str) -> float:
    settings = _get_game_rtp_settings()
    return float(settings.get(game, DEFAULT_GAME_RTP_PERCENT.get(game, 100.0)))


def _get_game_rtp_factor(game: str) -> float:
    return max(0.01, _get_game_rtp_percent(game) / 100.0)


def _get_case_return_to_pay(tier: str) -> float:
    if tier in {'case150', 'case250', 'case400', 'case600'}:
        return _get_game_rtp_percent(tier) / 100.0
    return _get_game_rtp_percent('cases') / 100.0


def _select_case_reward(min_reward: int, max_reward: int, rtp_factor: float) -> int:
    min_val = int(min_reward)
    max_val = int(max_reward)
    if max_val <= min_val:
        return max(1, min_val)

    rtp = max(0.05, min(3.0, float(rtp_factor)))
    base_mean = (min_val + max_val) / 2.0
    target_mean = max(float(min_val), min(float(max_val), base_mean * rtp))

    rng = float(max_val - min_val)
    denom = max(1e-9, target_mean - float(min_val))
    exponent = max(0.05, min(20.0, (rng / denom) - 1.0))

    rolled = min_val + rng * (random.random() ** exponent)
    return max(1, int(round(rolled)))


def _effective_mines_count() -> int:
    rtp = max(0.1, _get_game_rtp_factor('mines'))
    dynamic_count = int(round(MINES_COUNT / rtp))
    return max(1, min(15, dynamic_count))


def _fetch_json(url: str, timeout: int = 8):
    req = urllib.request.Request(url, headers={'User-Agent': 'FreakingStarsMiniApp/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode('utf-8', errors='ignore')
    return json.loads(raw)


def _fetch_text(url: str, timeout: int = 12) -> str:
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='ignore')


def _extract_numeric(container: dict, keys: list[str]) -> float | None:
    lowered = {str(k).lower(): v for k, v in (container or {}).items()}
    for key in keys:
        val = lowered.get(key.lower())
        parsed = _as_float(val)
        if parsed is not None and parsed > 0:
            return parsed
    return None


def _extract_url(container: dict) -> str | None:
    lowered = {str(k).lower(): v for k, v in (container or {}).items()}
    for key in ('url', 'link', 'item_url', 'offer_url'):
        val = lowered.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _extract_gram_prices_from_html(text: str) -> list[float]:
    if not text:
        return []

    values: list[float] = []
    patterns = [
        r'([0-9]+(?:[\.,][0-9]{1,8})?)\s*(?:GRAM|GRM|TON)\b',
        r'"(?:price_gram|gram_price|price_ton|ton_price|price)"\s*:\s*"?([0-9]+(?:\.[0-9]{1,8})?)"?',
        r'data-(?:price|ton|gram)\s*=\s*"([0-9]+(?:\.[0-9]{1,8})?)"',
    ]

    for pattern in patterns:
        for match in re.findall(pattern, text, flags=re.I):
            raw = str(match).strip().replace(',', '.')
            parsed = _as_float(raw)
            if parsed is None:
                continue
            if 0 < parsed < 100000:
                values.append(parsed)

    # Deduplicate while preserving order.
    uniq: list[float] = []
    seen = set()
    for value in values:
        key = round(value, 8)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(value)
    return uniq


def _extract_model_prices_from_html(text: str, model: str) -> list[float]:
    source = text or ''
    if not source:
        return []

    low = source.lower()
    aliases = [
        model.lower(),
        model.lower().replace('-', ' '),
        model.lower().replace('-', ''),
    ]

    windows: list[str] = []
    for alias in aliases:
        if not alias:
            continue
        start = 0
        while True:
            idx = low.find(alias, start)
            if idx < 0:
                break
            left = max(0, idx - 1200)
            right = min(len(source), idx + 1200)
            windows.append(source[left:right])
            start = idx + max(1, len(alias))

    for window in windows:
        prices = _extract_gram_prices_from_html(window)
        if prices:
            return prices

    return _extract_gram_prices_from_html(source)


def _pick_random_mrkt_lot(model: str) -> dict | None:
    template = (os.getenv('MRKT_SEARCH_URL') or '').strip()
    if not template:
        return None

    encoded_model = urllib.parse.quote(model)
    url = template.replace('{model}', encoded_model)
    # 1) Prefer JSON endpoint when available.
    try:
        payload = _fetch_json(url)
    except Exception:
        payload = None

    candidates = []
    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, dict):
        for key in ('lots', 'items', 'results', 'offers', 'data'):
            maybe = payload.get(key)
            if isinstance(maybe, list):
                candidates = maybe
                break

    if candidates:
        shuffled = list(candidates)
        random.shuffle(shuffled)
        for lot in shuffled:
            if not isinstance(lot, dict):
                continue
            gram_price = _extract_numeric(lot, ['price_gram', 'gram_price', 'price_ton', 'ton_price', 'price'])
            if gram_price is None:
                continue
            return {
                'gram_price': gram_price,
                'lot_url': _extract_url(lot) or url,
            }

    # 2) Fallback: scrape HTML when JSON API is blocked/unavailable.
    try:
        html = _fetch_text(url)
    except Exception:
        return None

    prices = _extract_model_prices_from_html(html, model)
    if not prices:
        return None
    return {
        'gram_price': random.choice(prices),
        'lot_url': url,
    }
    return None


def _stars_from_usdt(amount_usdt: float) -> int:
    if not math.isfinite(amount_usdt) or amount_usdt <= 0:
        return 50
    return max(1, int(round(amount_usdt * STARS_PER_USDT)))


def _stars_from_gram(gram_price: float) -> int | None:
    ton_market = ton_to_uah_buy_price(1, markup_percent=0) or {}
    ton_usdt = _as_float(ton_market.get('ton_usdt'))
    if ton_usdt is None or ton_usdt <= 0:
        return None
    amount_usdt = float(gram_price) * ton_usdt
    return _stars_from_usdt(amount_usdt)


def _fallback_stars_price_from_gram(model: str, gram_price: float | None = None) -> tuple[int, float | None]:
    if gram_price is not None:
        stars_price = _stars_from_gram(gram_price)
        if stars_price is not None:
            return stars_price, gram_price

    default_stars = int(NFT_MODEL_DEFAULT_STARS.get(model, 100))
    ton_market = ton_to_uah_buy_price(1, markup_percent=0) or {}
    ton_usdt = _as_float(ton_market.get('ton_usdt'))
    if ton_usdt is None or ton_usdt <= 0:
        return default_stars, gram_price

    approx_gram = round((default_stars / STARS_PER_USDT) / ton_usdt, 6)
    return default_stars, approx_gram


def _find_nft_meta(model: str) -> dict:
    m = str(model).strip().lower()
    manual_prices = _get_nft_manual_prices()
    for item in ALL_TELEGRAM_NFT_GIFTS:
        if item['model'] == m:
            meta = dict(item)
            val = manual_prices.get(m, meta.get('default_stars', 100))
            meta['rarity'] = get_rarity_by_stars(val)
            return meta
    title = m.replace('-', ' ').replace('_', ' ').title()
    val = manual_prices.get(m, 100)
    return {
        'model': m,
        'name': title,
        'label': title,
        'default_stars': val,
        'image': '',
        'rarity': get_rarity_by_stars(val),
    }


def _get_nft_manual_prices() -> dict[str, int]:
    settings = db.pricing_settings if isinstance(db.pricing_settings, dict) else {}
    stored = settings.get('nft_gift_prices') if isinstance(settings, dict) else None
    result: dict[str, int] = {}

    for model, fallback in NFT_MODEL_DEFAULT_STARS.items():
        result[model] = int(fallback)

    if isinstance(stored, dict):
        for key, value in stored.items():
            try:
                k = str(key).strip().lower()
                if k:
                    result[k] = max(1, int(value))
            except Exception:
                continue

    return result


def _set_nft_manual_prices(prices: dict[str, int]) -> dict[str, int]:
    normalized: dict[str, int] = {}
    for model, fallback in NFT_MODEL_DEFAULT_STARS.items():
        raw = prices.get(model, fallback)
        try:
            normalized[model] = max(1, int(raw))
        except Exception:
            normalized[model] = int(fallback)

    if isinstance(prices, dict):
        for model, raw in prices.items():
            m = str(model).strip().lower()
            if m and m not in normalized:
                try:
                    normalized[m] = max(1, int(raw))
                except Exception:
                    pass

    settings = db.pricing_settings if isinstance(db.pricing_settings, dict) else {}
    settings['nft_gift_prices'] = normalized
    db.pricing_settings = settings
    db.save_data()
    return normalized


def _is_http_image_url(value: str) -> bool:
    text = (value or '').strip()
    if not text:
        return False
    try:
        parsed = urllib.parse.urlparse(text)
    except Exception:
        return False
    if parsed.scheme not in {'http', 'https'}:
        return False
    return bool(parsed.netloc)


def _get_nft_manual_images() -> dict[str, str]:
    settings = db.pricing_settings if isinstance(db.pricing_settings, dict) else {}
    stored = settings.get('nft_gift_images') if isinstance(settings, dict) else None
    result: dict[str, str] = {}

    for item in ALL_TELEGRAM_NFT_GIFTS:
        m = item['model']
        img = item.get('image')
        if img and _is_http_image_url(img):
            result[m] = img

    if isinstance(stored, dict):
        for key, value in stored.items():
            model = str(key).strip().lower()
            url = str(value or '').strip()
            if _is_http_image_url(url):
                result[model] = url

    return result


def _set_nft_manual_images(images: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for model in NFT_MODEL_DEFAULT_STARS:
        raw = str(images.get(model, '') or '').strip()
        if _is_http_image_url(raw):
            normalized[model] = raw

    if isinstance(images, dict):
        for model, raw in images.items():
            m = str(model).strip().lower()
            url = str(raw or '').strip()
            if m and _is_http_image_url(url):
                normalized[m] = url

    settings = db.pricing_settings if isinstance(db.pricing_settings, dict) else {}
    settings['nft_gift_images'] = normalized
    db.pricing_settings = settings
    db.save_data()
    return normalized


def _get_nft_shop_catalog() -> list[dict]:
    prices = _get_nft_manual_prices()
    images = _get_nft_manual_images()
    catalog: list[dict] = []
    seen = set()

    for item in ALL_TELEGRAM_NFT_GIFTS:
        model = item['model']
        seen.add(model)
        val = int(prices.get(model, item.get('default_stars', 100)))
        img = str(images.get(model, item.get('image', '')) or '')
        catalog.append({
            'kind': 'gift',
            'model': model,
            'name': item.get('name', model),
            'label': item.get('label', item.get('name', model)),
            'value': val,
            'unit': '⭐',
            'image': img,
            'icon': '🎁',
            'rarity': get_rarity_by_stars(val),
        })

    for model, val in prices.items():
        if model not in seen:
            title = model.replace('-', ' ').replace('_', ' ').title()
            catalog.append({
                'kind': 'gift',
                'model': model,
                'name': title,
                'label': title,
                'value': int(val),
                'unit': '⭐',
                'image': str(images.get(model, '') or ''),
                'icon': '🎁',
                'rarity': get_rarity_by_stars(val),
            })

    catalog.sort(key=lambda x: (x.get('value', 0), x.get('label', '')))
    return catalog


def _get_nft_case_chances() -> dict[str, float]:
    """Get admin-managed NFT case drop chances (percentages)."""
    settings = db.pricing_settings if isinstance(db.pricing_settings, dict) else {}
    stored = settings.get('nft_case_chances') if isinstance(settings, dict) else None
    result: dict[str, float] = {}

    if isinstance(stored, dict):
        for key, value in stored.items():
            try:
                model = str(key).strip().lower()
                chance = float(value)
                if model and chance >= 0:
                    result[model] = chance
            except Exception:
                continue

    return result


def _set_nft_case_chances(chances: dict[str, float]) -> dict[str, float]:
    """Set admin-managed NFT case drop chances (percentages)."""
    normalized: dict[str, float] = {}
    
    if isinstance(chances, dict):
        for key, value in chances.items():
            try:
                model = str(key).strip().lower()
                chance = float(value)
                if model and chance >= 0:
                    normalized[model] = chance
            except Exception:
                continue

    settings = db.pricing_settings if isinstance(db.pricing_settings, dict) else {}
    settings['nft_case_chances'] = normalized
    db.pricing_settings = settings
    db.save_data()
    return normalized


def _resolve_case_gift_chance(item: dict, tier: str | None = None) -> float:
    """Resolve the effective drop chance for a case prize, checking tier overrides and admin overrides."""
    if not isinstance(item, dict):
        return 0.0

    active_tier = tier or item.get('_tier')
    if active_tier:
        custom_tier = get_case_chances(active_tier)
        item_id = item.get('id')
        if item_id and item_id in custom_tier:
            return float(custom_tier[item_id])
        model = str(item.get('model') or '').strip().lower()
        if model and model in custom_tier:
            return float(custom_tier[model])
        label = str(item.get('label') or '').strip().lower()
        if label and label in custom_tier:
            return float(custom_tier[label])

    model = str(item.get('model') or '').strip().lower()
    if model:
        admin_chances = _get_nft_case_chances()
        if model in admin_chances:
            chance = float(admin_chances[model])
            if chance >= 0:
                return chance

    chance = max(0.0, float(item.get('chance_percent', item.get('weight', 0) or 0) or 0))
    if chance <= 0 and item.get('weight') is not None:
        chance = max(0.0, float(int(item.get('weight', 0) or 0)) / 100.0)
    return max(0.0, chance)


def _resolve_nft_model_price(model: str) -> dict:
    normalized = (model or '').strip().lower()
    if not normalized:
        return {
            'model': '',
            'stars_price': 0,
            'gram_price': None,
            'source': 'invalid_model',
            'lot_url': None,
        }

    manual_prices = _get_nft_manual_prices()
    stars_price = int(manual_prices.get(normalized, NFT_MODEL_DEFAULT_STARS.get(normalized, 100)))

    return {
        'model': normalized,
        'stars_price': stars_price,
        'gram_price': None,
        'source': 'admin_manual',
        'lot_url': None,
        'stars_per_usdt': STARS_PER_USDT,
    }


def get_numeric_balance(user_data: dict) -> float:
    return float(user_data.get('balance_stars', user_data.get('total_stars', 0)) or 0)


def get_numeric_ton_balance(user_data: dict) -> float:
    return float(user_data.get('balance_ton', 0) or 0)


def format_stars(value) -> str:
    amount = float(value or 0)
    rounded = round(amount, 2)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    return f"{rounded:.2f}".rstrip('0').rstrip('.')


def _ensure_user_game_stats(user_data: dict) -> bool:
    changed = False
    if 'games' not in user_data or not isinstance(user_data.get('games'), dict):
        user_data['games'] = {}
        changed = True
    defaults = _default_user_game_stats()
    for game_name in ('mines', 'crash', 'roulette', 'coin'):
        if game_name not in user_data['games'] or not isinstance(user_data['games'].get(game_name), dict):
            user_data['games'][game_name] = {}
            changed = True
        stats = user_data['games'][game_name]
        for key, value in defaults.items():
            if key not in stats:
                stats[key] = value
                changed = True
    return changed


def _default_casino_data() -> dict:
    return {
        'racket': {'played': 0, 'wins': 0, 'total_bet': 0, 'total_won': 0, 'last_outcome': None},
        'cases': {'basic': 0, 'silver': 0, 'gold': 0},
        'upgrades': {'gift_wrap': 0, 'bonus_box': 0, 'legendary_ribbon': 0},
        'last_case': None,
        'last_upgrade': None,
    }


def _serialize_inventory(user_data: dict, user_id: int | None = None) -> list[dict]:
    items = user_data.get('miniapp_inventory')
    if not isinstance(items, list):
        return []
    result: list[dict] = []
    user_id = int(user_id) if user_id is not None else None
    pending_gift_ids = set()
    rejected_gift_ids = set()
    if user_id is not None:
        for transaction in db.transactions:
            if int(transaction.get('user_id', 0) or 0) != user_id:
                continue
            if transaction.get('type') != 'gift_withdraw':
                continue
            gift_id = str(transaction.get('gift_id') or '').strip()
            if not gift_id:
                continue
            status = str(transaction.get('status') or '').lower()
            if status == 'pending':
                pending_gift_ids.add(gift_id)
            elif status == 'rejected':
                rejected_gift_ids.add(gift_id)
    for item in items:
        if not isinstance(item, dict):
            continue
        gift_id = str(item.get('id') or '').strip()
        model = item.get('model')
        meta = _find_nft_meta(model) if model else None
        english_name = meta.get('name') if meta else (item.get('name') or item.get('label') or 'NFT Gift')
        val = int(item.get('value', 0) or 0)
        if val <= 0 and meta:
            val = int(meta.get('default_stars', 0) or 0)
        rarity = get_rarity_by_stars(val)
        entry = {
            'id': gift_id,
            'kind': str(item.get('kind') or 'gift'),
            'label': english_name if item.get('kind') == 'gift' else str(item.get('label') or item.get('name') or 'Item'),
            'name': english_name if item.get('kind') == 'gift' else str(item.get('name') or item.get('label') or 'Item'),
            'model': model,
            'value': val,
            'unit': '⭐',
            'icon': str(item.get('icon') or '🎁'),
            'rarity': rarity,
            'createdAt': item.get('createdAt'),
            'pending_withdraw': gift_id in pending_gift_ids,
            'withdraw_rejected': gift_id in rejected_gift_ids,
        }
        result.append(entry)
    return result


def _gift_stars_price_for_item(item: dict) -> int:
    if not isinstance(item, dict):
        return 0
    if str(item.get('kind') or '').lower() != 'gift':
        return int(item.get('value', 0) or 0)
    model = str(item.get('model') or '').strip().lower()
    if model:
        manual = _get_nft_manual_prices()
        quoted = manual.get(model)
        if quoted is not None:
            return int(quoted)
    return int(item.get('value', 0) or 0)


def _get_case_nft_catalog() -> list[dict]:
    return _get_nft_shop_catalog()


def _sell_inventory_gift(user_data: dict, gift_id: str) -> dict:
    with _BALANCE_LOCK:
        inventory = user_data.setdefault('miniapp_inventory', [])
        if not isinstance(inventory, list):
            inventory = []
            user_data['miniapp_inventory'] = inventory
        item = next((x for x in inventory if str(x.get('id') or '') == gift_id), None)
        if not item:
            _error(404, 'Подарок не найден')

        stars_value = _gift_stars_price_for_item(item)
        if stars_value <= 0:
            _error(400, 'Некорректная стоимость подарка')

        user_data['miniapp_inventory'] = [x for x in inventory if str(x.get('id') or '') != gift_id]
        add_star_balance(user_data, float(stars_value))
        user_data['balance_stars'] = round(float(user_data.get('balance_stars', user_data.get('total_stars', 0)) or 0), 1)
        user_data['total_stars'] = float(user_data.get('total_stars', 0) or 0)
        return {'removed': True, 'stars_value': stars_value, 'gift_id': gift_id, 'label': item.get('label') or item.get('name') or 'Gift'}


def _create_inventory_withdraw_request(user_data: dict, tg_user, gift_id: str) -> dict:
    with _BALANCE_LOCK:
        inventory = user_data.setdefault('miniapp_inventory', [])
        if not isinstance(inventory, list):
            inventory = []
            user_data['miniapp_inventory'] = inventory
        item = next((x for x in inventory if str(x.get('id') or '') == gift_id), None)
        if not item:
            _error(404, 'Подарок не найден')

        stars_value = _gift_stars_price_for_item(item)
        user_data['miniapp_inventory'] = [x for x in inventory if str(x.get('id') or '') != gift_id]
        transaction = _create_transaction({
            'type': 'gift_withdraw',
            'user_id': tg_user.id,
            'gift_id': gift_id,
            'gift_label': item.get('label') or item.get('name') or 'Gift',
            'stars_value': stars_value,
            'gift_data': item,
            'held_at_creation': True,
            'status': 'pending',
        })
        return transaction


def _ensure_user_casino(user_data: dict) -> bool:
    changed = False
    if 'casino' not in user_data or not isinstance(user_data.get('casino'), dict):
        user_data['casino'] = _default_casino_data()
        return True
    casino = user_data['casino']
    defaults = _default_casino_data()
    for key, value in defaults.items():
        if key not in casino:
            casino[key] = value
            changed = True
        elif isinstance(value, dict):
            section = casino.setdefault(key, {})
            for inner_key, inner_value in value.items():
                if inner_key not in section:
                    section[inner_key] = inner_value
                    changed = True
    return changed


def _serialize_casino(user_data: dict) -> dict:
    casino = user_data.get('casino') or _default_casino_data()
    return {
        'racket': casino.get('racket', {}),
        'cases': casino.get('cases', {}),
        'upgrades': casino.get('upgrades', {}),
        'last_case': casino.get('last_case'),
        'last_upgrade': casino.get('last_upgrade'),
    }


def register_user_if_needed(user_id: int, username: str | None = None) -> dict:
    db.refresh()
    key = str(user_id)
    if key not in db.users:
        db.users[key] = {
            'username': username or 'Не указан',
            'total_stars': 0,
            'balance_stars': 0,
            'balance_ton': 0,
            'balance_uah': 0,
            'registration_date': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'has_review': False,
            'last_active': datetime.now().isoformat(),
            'games': {
                'mines': _default_user_game_stats(),
                'crash': _default_user_game_stats(),
                'roulette': _default_user_game_stats(),
            },
            'miniapp_inventory': [],
        }
        db.save_data()
    else:
        changed = False
        db.users[key]['last_active'] = datetime.now().isoformat()
        if 'balance_stars' not in db.users[key]:
            db.users[key]['balance_stars'] = float(db.users[key].get('total_stars', 0) or 0)
            changed = True
        if 'balance_ton' not in db.users[key]:
            db.users[key]['balance_ton'] = 0
            changed = True
        if 'balance_uah' not in db.users[key]:
            db.users[key]['balance_uah'] = 0
            changed = True
        if username and db.users[key].get('username') != username:
            db.users[key]['username'] = username
            changed = True
        if _ensure_user_game_stats(db.users[key]):
            changed = True
        if _ensure_user_casino(db.users[key]):
            changed = True
        if 'miniapp_inventory' not in db.users[key] or not isinstance(db.users[key].get('miniapp_inventory'), list):
            db.users[key]['miniapp_inventory'] = []
            changed = True
        if changed:
            db.save_data()
    return db.users[key]


def _default_user_game_stats() -> dict:
    return {
        'games_played': 0,
        'wins': 0,
        'losses': 0,
        'total_bet': 0,
        'total_won': 0,
        'total_paid_out': 0,
        'biggest_win': 0,
    }


def _default_global_game_stats(game_type: str | None = None) -> dict:
    stats = {
        'games_played': 0,
        'wins': 0,
        'losses': 0,
        'total_bet': 0,
        'total_paid_out': 0,
        'net_profit': 0,
    }
    if game_type == 'crash':
        stats['last_round_number'] = 0
    return stats


def _ensure_stats_dict(target: dict | None, defaults: dict) -> dict:
    stats = target if isinstance(target, dict) else {}
    for key, value in defaults.items():
        stats.setdefault(key, value)
    return stats


def _get_user_game_stats(user_data: dict, game_name: str) -> dict:
    games = user_data.setdefault('games', {})
    stats = _ensure_stats_dict(games.get(game_name), _default_user_game_stats())
    games[game_name] = stats
    return stats


def _get_global_game_stats(game_name: str) -> dict:
    stats = _ensure_stats_dict(db.game_stats.get(game_name), _default_global_game_stats(game_name))
    db.game_stats[game_name] = stats
    if game_name == 'crash':
        stats.setdefault('last_round_number', 0)
    return stats


def _get_user_mines_stats(user_data: dict) -> dict:
    return _get_user_game_stats(user_data, 'mines')


def _get_user_crash_stats(user_data: dict) -> dict:
    return _get_user_game_stats(user_data, 'crash')


def _get_user_roulette_stats(user_data: dict) -> dict:
    return _get_user_game_stats(user_data, 'roulette')


def _get_global_mines_stats() -> dict:
    return _get_global_game_stats('mines')


def _get_global_crash_stats() -> dict:
    return _get_global_game_stats('crash')


def _get_global_roulette_stats() -> dict:
    return _get_global_game_stats('roulette')


def _create_dice_room(user_id: int, currency: str, bet: float, rounds_total: int) -> str:
    room_id = ''.join(random.choice('0123456789abcdef') for _ in range(10))
    rooms = db.pricing_settings.setdefault('miniapp_dice_rooms', {})
    rooms[room_id] = {
        'room_id': room_id,
        'owner_id': user_id,
        'currency': currency,
        'bet': float(bet),
        'rounds_total': int(rounds_total),
        'status': 'waiting',
        'created_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
    }
    db.save_data()
    return room_id


_enable_docs = os.getenv('ENABLE_DOCS', '0').strip().lower() in {'1', 'true', 'yes'}
app = FastAPI(
    title='Freaking Stars Mini App API',
    docs_url='/docs' if _enable_docs else None,
    redoc_url='/redoc' if _enable_docs else None,
    openapi_url='/openapi.json' if _enable_docs else None,
)
REQUEST_LOCK = threading.RLock()


class RateLimiter:
    """In-memory sliding-window rate limiter for sensitive actions."""
    def __init__(self):
        self._lock = threading.Lock()
        self._records: dict[str, list[float]] = {}

    def is_allowed(self, key: str, max_requests: int, window_seconds: float) -> bool:
        now = time.time()
        with self._lock:
            timestamps = self._records.setdefault(key, [])
            cutoff = now - window_seconds
            self._records[key] = [t for t in timestamps if t > cutoff]
            if len(self._records[key]) >= max_requests:
                return False
            self._records[key].append(now)
            return True


RATE_LIMITER = RateLimiter()


def _check_rate_limit(request: Request, scope: str, max_requests: int, window_seconds: float, actor_id: int | str | None = None) -> None:
    client_ip = (request.client.host if request.client else 'unknown') or 'unknown'
    key = f"{scope}:{actor_id or client_ip}"
    if not RATE_LIMITER.is_allowed(key, max_requests, window_seconds):
        _error(429, 'Слишком много запросов. Пожалуйста, подождите.')


def _extract_init_data(request: Request, payload_init_data: str | None = None) -> str:
    # 1. Header X-Telegram-Init-Data (preferred, prevents query log leakage)
    hdr = request.headers.get('X-Telegram-Init-Data', '').strip()
    if hdr:
        return hdr
    # 2. Authorization header (Bearer / tma)
    auth_hdr = request.headers.get('Authorization', '').strip()
    if auth_hdr:
        if auth_hdr.startswith('Bearer '):
            return auth_hdr[7:].strip()
        if auth_hdr.startswith('tma '):
            return auth_hdr[4:].strip()
    # 3. Payload init_data
    if payload_init_data and payload_init_data.strip():
        return payload_init_data.strip()
    # 4. Query param fallback
    qp = request.query_params.get('init_data', '').strip()
    if qp:
        return qp
    return ''


def _get_desktop_admin_key() -> str:
    env_key = (os.getenv('DESKTOP_ADMIN_KEY') or '').strip()
    if env_key:
        return env_key
    key_file = BASE_DIR / 'var' / 'desktop_admin_key.txt'
    try:
        if key_file.exists():
            key = key_file.read_text(encoding='utf-8').strip()
            if key:
                return key
    except Exception:
        pass
    new_key = secrets.token_hex(24)
    try:
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_text(new_key, encoding='utf-8')
    except Exception:
        pass
    return new_key


DESKTOP_ADMIN_KEY = _get_desktop_admin_key()
DESKTOP_ADMIN_KEY_CONTEXT: ContextVar[str] = ContextVar('desktop_admin_key', default='')


@app.middleware('http')
async def security_headers_and_routing(request: Request, call_next):
    path = request.scope.get('path', '')
    if path.startswith('/admin/'):
        path = path[len('/admin'):]
        request.scope['path'] = path
        request.scope['raw_path'] = path.encode('utf-8')

    token = DESKTOP_ADMIN_KEY_CONTEXT.set(request.headers.get('X-Admin-Key', ''))
    try:
        with REQUEST_LOCK:
            response = await call_next(request)
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://telegram.org; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https: http:; "
            "connect-src 'self' https: http: wss: ws: https://*.telegram.org; "
            "frame-ancestors 'self' https://web.telegram.org https://*.web.telegram.org;"
        )
        if 'server' in response.headers:
            del response.headers['server']
        if 'x-powered-by' in response.headers:
            del response.headers['x-powered-by']
        return response
    finally:
        DESKTOP_ADMIN_KEY_CONTEXT.reset(token)


_allowed_origins = [
    'https://web.telegram.org',
    'https://telegram.org',
]
for _u in [WEBAPP_URL, CLOUDFLARE_QUICK_TUNNEL_URL, CLOUDFLARE_CUSTOM_DOMAIN, WEBAPP_FALLBACK_URL]:
    if _u:
        _u_clean = _u.rstrip('/')
        if _u_clean and _u_clean not in _allowed_origins:
            _allowed_origins.append(_u_clean)
_allowed_origins.extend([
    f'http://127.0.0.1:{BACKEND_PORT}',
    f'http://localhost:{BACKEND_PORT}',
])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r'https:\/\/.*\.web\.telegram\.org',
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['*'],
)
app.mount('/webapp/assets', StaticFiles(directory=str(WEBAPP_DIR)), name='webapp-assets')


class StarsOrderIn(BaseModel):
    init_data: str
    stars: int = Field(ge=50, le=10000)
    payment_method: Literal['mono', 'ton_wallet', 'ton_balance']
    target_username: str | None = None


class PremiumOrderIn(BaseModel):
    init_data: str
    months: int
    payment_method: Literal['mono', 'ton_wallet', 'ton_balance']
    target_username: str | None = None


class TonTopupIn(BaseModel):
    init_data: str
    ton_amount: float = Field(gt=0)
    payment_method: Literal['mono', 'ton_wallet']


class PromoIn(BaseModel):
    init_data: str
    code: str


class SupportIn(BaseModel):
    init_data: str
    category: Literal['support', 'suggestion']
    text: str = Field(min_length=3, max_length=2000)


class WithdrawIn(BaseModel):
    init_data: str
    asset: Literal['stars', 'ton']
    amount: float = Field(gt=0)


class InventoryGiftActionIn(BaseModel):
    init_data: str
    gift_id: str


class ReviewIn(BaseModel):
    init_data: str
    text: str = Field(min_length=3, max_length=1200)


class RouletteSpinIn(BaseModel):
    init_data: str
    amount: float = Field(gt=0)
    currency: Literal['stars', 'ton']
    color: Literal['red', 'white', 'green']


class MinesStartIn(BaseModel):
    init_data: str
    amount: float = Field(gt=0)
    currency: Literal['stars', 'ton']


class MinesRevealIn(BaseModel):
    init_data: str
    index: int = Field(ge=0, le=15)


class CrashPlayIn(BaseModel):
    init_data: str
    amount: float = Field(gt=0)
    currency: Literal['stars', 'ton']
    auto_cashout: float | None = None


class CoinPlayIn(BaseModel):
    init_data: str
    amount: float = Field(gt=0)
    currency: Literal['stars', 'ton']
    choice: Literal['eagle', 'tails', 'edge']


class CrashCashoutIn(BaseModel):
    init_data: str
    cashout_x: float = Field(gt=0)


class CrashFinishIn(BaseModel):
    init_data: str


class DiceInviteIn(BaseModel):
    init_data: str
    amount: float = Field(gt=0)
    currency: Literal['stars', 'ton']
    rounds_total: Literal[1, 3, 5]


class CasinoRacketIn(BaseModel):
    init_data: str
    amount: float = Field(gt=0)
    currency: Literal['stars', 'ton']


class CasinoCaseOpenIn(BaseModel):
    init_data: str
    tier: Literal['basic', 'silver', 'gold', 'case150', 'case250', 'case400', 'case600']


class CasinoUpgradeBuyIn(BaseModel):
    init_data: str
    upgrade: Literal['gift_wrap', 'bonus_box', 'legendary_ribbon']


class UpgradePlayIn(BaseModel):
    init_data: str
    mode: Literal['inventory', 'stars'] = 'stars'
    gift_id: str | None = None
    stars_amount: float | None = None
    target_model: str


class ProofMetaIn(BaseModel):
    init_data: str
    kind: Literal['stars', 'premium', 'ton_topup']
    payload: dict


class AdminStarPackagesIn(BaseModel):
    init_data: str
    packages: dict


class AdminPremiumPricesIn(BaseModel):
    init_data: str
    prices: dict


class AdminNftPricesIn(BaseModel):
    init_data: str
    prices: dict


class AdminNftCaseChancesIn(BaseModel):
    init_data: str
    chances: dict


class AdminCaseChancesIn(BaseModel):
    init_data: str
    tier: str | None = None
    chances: dict = Field(default_factory=dict)


class AdminNftImagesIn(BaseModel):
    init_data: str
    images: dict


class AdminGameRtpIn(BaseModel):
    init_data: str
    rtp_percent: dict


class AdminPromoCreateIn(BaseModel):
    init_data: str
    code: str
    max_uses: int = Field(gt=0)
    amount_stars: int = Field(gt=0)


class AdminSuggestionActionIn(BaseModel):
    init_data: str
    suggestion_id: int
    action: Literal['rejected', 'under_review']


class AdminBroadcastIn(BaseModel):
    init_data: str = 'desktop'
    text: str = ''
    image_url: str | None = None
    image_base64: str | None = None
    image_filename: str | None = None
    button_text: str | None = None
    button_url: str | None = None
    target: str = 'all'


class AdminUserBanIn(BaseModel):
    init_data: str = 'desktop'
    user_id: int
    ban: bool


class AdminPromocodeDeleteIn(BaseModel):
    init_data: str = 'desktop'
    code: str


class AdminStarRatesIn(BaseModel):
    init_data: str = 'desktop'
    rates: list[dict]


class AdminReviewDeleteIn(BaseModel):
    init_data: str = 'desktop'
    index: int | None = None
    user_id: int | None = None
    text: str | None = None


class AdminUserInventoryAddIn(BaseModel):
    init_data: str = 'desktop'
    user_id: int
    model: str
    name: str = ''
    image: str = ''
    value: int = 100


class AdminUserInventoryRemoveIn(BaseModel):
    init_data: str = 'desktop'
    user_id: int
    item_id: str


class AdminSendMessageIn(BaseModel):
    init_data: str = 'desktop'
    user_id: int
    text: str


class AdminSuggestionDeleteIn(BaseModel):
    init_data: str = 'desktop'
    suggestion_id: int


class AdminNftGiftDeleteIn(BaseModel):
    init_data: str = 'desktop'
    model: str


class AdminClearTransactionsIn(BaseModel):
    init_data: str = 'desktop'
    status_filter: str | None = None


class AdminResetMinesSessionIn(BaseModel):
    init_data: str
    user_id: int


class AdminUserGameStatsIn(BaseModel):
    init_data: str
    user_id: int
    game: str
    stats: dict[str, float]


class AdminBalanceAdjustmentIn(BaseModel):
    init_data: str
    user_id: int
    currency: Literal['stars', 'ton']
    amount: float
    reason: str = Field(min_length=3, max_length=500)


class AdminBotSettingsIn(BaseModel):
    init_data: str
    settings: dict


class AdminTransactionDecisionIn(BaseModel):
    init_data: str = 'desktop'
    transaction_id: int
    decision: Literal['confirm', 'reject']


class AdminRejectAllPendingIn(BaseModel):
    init_data: str | None = 'desktop'


class AdminTournamentCreateIn(BaseModel):
    init_data: str | None = 'desktop'
    title: str
    description: str = ''
    metric: str
    games: list[str] = []
    start_time: str | None = None
    end_time: str | None = None
    prize_pool: float = 0
    # Each prize dict: {place, prize_type, reward?, nft_model?, nft_name?, nft_image?, nft_value?}
    prizes: list[dict] = []
    min_threshold: float = 0


class AdminTournamentActionIn(BaseModel):
    init_data: str | None = 'desktop'
    tournament_id: str


ROULETTE_RED_PAYOUT = 2.0
ROULETTE_WHITE_PAYOUT = 2.0


def _error(status_code: int, detail: str):
    raise HTTPException(status_code=status_code, detail=detail)


def _sync_db():
    db.load_data()


def _is_user_banned(user_id: int | str) -> bool:
    try:
        uid_int = int(user_id)
    except (ValueError, TypeError):
        uid_int = None
    uid_str = str(user_id)
    for item in db.restricted_users:
        if isinstance(item, dict):
            r_uid = item.get('user_id') or item.get('id')
            if r_uid is not None and (r_uid == uid_int or str(r_uid) == uid_str):
                return True
        elif (uid_int is not None and item == uid_int) or str(item) == uid_str:
            return True
    return False


def _require_user(init_data: str, allow_demo: bool = False):
    _sync_db()
    init_data_clean = (init_data or '').strip()
    if not init_data_clean or init_data_clean == 'demo':
        _error(403, 'Mini App доступен только внутри Telegram. Откройте приложение через официальный бот.')

    try:
        tg_user = validate_init_data(init_data_clean)
    except MiniAppAuthError as exc:
        _error(401, 'Недействительная авторизация Telegram. Откройте приложение через официальный бот.')

    if tg_user.id == 0:
        _error(403, 'Mini App доступен только внутри Telegram.')

    if _is_user_banned(tg_user.id):
        _error(403, 'Доступ к Mini App заблокирован администратором')

    user_data = register_user_if_needed(tg_user.id, tg_user.username)
    if tg_user.start_param and tg_user.start_param.startswith('ref_'):
        try:
            ref_id = int(tg_user.start_param[4:])
            bind_referral(tg_user.id, ref_id, tg_user.username)
        except Exception:
            pass
    return tg_user, user_data


def _require_admin(init_data: str | None = 'desktop', request: Request | None = None):
    provided_key = (request.headers.get('X-Admin-Key', '') if request else '') or DESKTOP_ADMIN_KEY_CONTEXT.get()
    if DESKTOP_ADMIN_KEY and provided_key and hmac.compare_digest(provided_key, DESKTOP_ADMIN_KEY):
        _sync_db()
        if not ADMIN_IDS:
            _error(503, 'Не настроены ADMIN_IDS')
        admin_id = int(ADMIN_IDS[0])
        user = TelegramMiniAppUser(
            id=admin_id,
            username='desktop_admin',
            first_name='Desktop Admin',
            last_name=None,
            language_code='ru',
            is_premium=False,
        )
        return user, db.users.get(str(admin_id), {})

    init_str = ''
    if request:
        init_str = _extract_init_data(request, init_data if init_data not in {'desktop', 'demo'} else None)
    if not init_str:
        init_str = (init_data or '').strip()

    if not init_str or init_str in {'desktop', 'demo'}:
        _error(401, 'Требуется авторизация администратора')

    tg_user, user_data = _require_user(init_str, allow_demo=False)
    if tg_user.id == 0 or int(tg_user.id) not in set(int(x) for x in ADMIN_IDS):
        _error(403, 'Нет доступа к панели администратора')
    return tg_user, user_data


def _parse_star_packages_payload(packages_raw: dict) -> dict[int, float]:
    if not isinstance(packages_raw, dict):
        _error(400, 'Некорректный формат star packages')

    parsed: dict[int, float] = {}
    for key, value in packages_raw.items():
        try:
            stars = int(key)
            amount_uah = float(value)
        except Exception:
            _error(400, 'Некорректный формат star packages')
        if stars <= 0 or amount_uah <= 0:
            _error(400, 'Некорректные значения в star packages')
        parsed[stars] = amount_uah

    if not parsed:
        _error(400, 'Список star packages пустой')
    return parsed


def _parse_premium_prices_payload(prices_raw: dict) -> dict[int, float]:
    if not isinstance(prices_raw, dict):
        _error(400, 'Некорректный формат premium prices')
    parsed: dict[int, float] = {}
    for key, value in prices_raw.items():
        try:
            months = int(key)
            parsed[months] = float(value)
        except Exception:
            _error(400, 'Некорректный формат premium prices')
    if sorted(parsed.keys()) != [1, 3, 6, 12]:
        _error(400, 'Premium prices должны содержать ключи 1,3,6,12')
    return parsed


def _find_user_by_identifier(identifier: str) -> tuple[str, dict] | tuple[None, None]:
    raw = (identifier or '').strip()
    if not raw:
        return None, None

    db.refresh()
    if raw.isdigit() and raw in db.users:
        return raw, db.users[raw]

    target = raw.lstrip('@').lower()
    for uid, user in db.users.items():
        username = str(user.get('username', '')).lstrip('@').lower()
        if username and username == target:
            return uid, user
    return None, None


def _build_admin_summary() -> dict:
    db.refresh()
    confirmed = [t for t in db.transactions if t.get('status') == 'confirmed']
    total_earned = sum(float(t.get('amount', 0) or 0) for t in confirmed)
    stars_sold = sum(int(t.get('stars', 0) or 0) for t in confirmed if t.get('type') == 'stars')

    mines_stats = db.game_stats.get('mines', {}) if isinstance(db.game_stats, dict) else {}
    crash_stats = db.game_stats.get('crash', {}) if isinstance(db.game_stats, dict) else {}
    roulette_stats = db.game_stats.get('roulette', {}) if isinstance(db.game_stats, dict) else {}
    coin_stats = db.game_stats.get('coin', {}) if isinstance(db.game_stats, dict) else {}
    plinko_stats = db.game_stats.get('plinko', {}) if isinstance(db.game_stats, dict) else {}
    tower_stats = db.game_stats.get('tower', {}) if isinstance(db.game_stats, dict) else {}
    blackjack_stats = db.game_stats.get('blackjack', {}) if isinstance(db.game_stats, dict) else {}

    total_user_balance_stars = sum(float(u.get('balance_stars', u.get('total_stars', 0)) or 0) for u in db.users.values())
    total_user_balance_ton = sum(float(u.get('balance_ton', 0) or 0) for u in db.users.values())

    total_deposits_stars = sum(float(t.get('stars', 0) or 0) for t in confirmed if t.get('type') == 'stars')
    total_deposits_ton = sum(float(t.get('ton_amount', 0) or 0) for t in confirmed if t.get('type') in ['ton', 'ton_topup'])

    total_withdraws_stars = sum(float(t.get('stars', 0) or 0) for t in confirmed if t.get('type') == 'withdraw')
    total_withdraws_ton = sum(float(t.get('ton_amount', 0) or 0) for t in confirmed if t.get('type') == 'withdraw_ton')

    net_profit_stars = total_deposits_stars - total_withdraws_stars - total_user_balance_stars
    net_profit_ton = total_deposits_ton - total_withdraws_ton - total_user_balance_ton

    return {
        'users_total': len(db.users),
        'orders_total': len(db.transactions),
        'orders_confirmed': len(confirmed),
        'total_earned_uah': round(total_earned, 2),
        'stars_sold': stars_sold,
        'total_user_balance_stars': total_user_balance_stars,
        'total_user_balance_ton': total_user_balance_ton,
        'total_deposits_stars': total_deposits_stars,
        'total_deposits_ton': total_deposits_ton,
        'total_withdraws_stars': total_withdraws_stars,
        'total_withdraws_ton': total_withdraws_ton,
        'net_profit_stars': net_profit_stars,
        'net_profit_ton': net_profit_ton,
        'total_balance': f"{round(total_user_balance_stars, 1):g} ⭐ / {round(total_user_balance_ton, 4):g} TON",
        'total_deposits': f"{round(total_deposits_stars, 1):g} ⭐ / {round(total_deposits_ton, 4):g} TON",
        'total_withdrawals': f"{round(total_withdraws_stars, 1):g} ⭐ / {round(total_withdraws_ton, 4):g} TON",
        'net_profit': f"{round(net_profit_stars, 1):g} ⭐ / {round(net_profit_ton, 4):g} TON",
        'orders_pending': len([t for t in db.transactions if t.get('status') == 'pending']),
        'suggestions_pending': len([s for s in db.suggestions if s.get('status') == 'pending']),
        'games': {
            'mines': mines_stats,
            'crash': crash_stats,
            'roulette': roulette_stats,
            'coin': coin_stats,
            'plinko': plinko_stats,
            'tower': tower_stats,
            'blackjack': blackjack_stats,
        },
    }


def _username(value: str | None, fallback: str = 'unknown') -> str:
    return (value or fallback).lstrip('@')


def _admin_payment_keyboard(transaction_id: int) -> dict:
    return {
        'inline_keyboard': [[
            {'text': '✅ Подтвердить', 'callback_data': f'confirm_{transaction_id}'},
            {'text': '❌ Отклонить', 'callback_data': f'reject_{transaction_id}'},
        ]]
    }


def _admin_withdraw_keyboard(transaction_id: int) -> dict:
    return {
        'inline_keyboard': [[
            {'text': '✅ Подтвердить вывод', 'callback_data': f'withdraw_confirm_{transaction_id}'},
            {'text': '❌ Отклонить вывод', 'callback_data': f'withdraw_reject_{transaction_id}'},
        ]]
    }


def _build_gift_withdraw_admin_message(transaction: dict, tg_user) -> tuple[str, dict]:
    caption = (
        f"🎁 Новая заявка на вывод подарка #{transaction['id']}\n\n"
        f"👤 ID: {tg_user.id}\n"
        f"👤 @{_username(tg_user.username)}\n"
        f"🎁 Подарок: {transaction['gift_label']}\n"
        f"⭐️ Стоимость: {transaction['stars_value']}"
    )
    return caption, _admin_withdraw_keyboard(transaction['id'])


def _recent_transactions(user_id: int, limit: int = 12) -> list[dict]:
    db.refresh()
    items = [t for t in db.transactions if int(t.get('user_id', 0) or 0) == int(user_id)]
    items.sort(key=lambda x: int(x.get('id', 0) or 0), reverse=True)
    return items[:limit]


def _serialize_profile(user_id: int) -> dict:
    user_data = register_user_if_needed(user_id)
    return _serialize_profile_from_user(user_data)


def _serialize_profile_from_user(user_data: dict) -> dict:
    return {
        'balance_stars': round(get_numeric_balance(user_data), 4),
        'balance_ton': round(get_numeric_ton_balance(user_data), 4),
        'total_stars': int(user_data.get('total_stars', 0) or 0),
        'username': user_data.get('username'),
        'registration_date': user_data.get('registration_date'),
    }


def _serialize_reviews(limit: int = 5) -> list[dict]:
    items = list(db.reviews)[-limit:]
    items.reverse()
    return [
        {
            'user_id': item.get('user_id'),
            'username': html.escape(str(item.get('username') or 'user'), quote=True),
            'text': html.escape(str(item.get('text', '')), quote=True),
            'date': html.escape(str(item.get('date', '')), quote=True),
        }
        for item in items
    ]


def _serialize_game_hub(user_id: int) -> dict:
    user_data = register_user_if_needed(user_id)
    return _serialize_game_hub_from_user(user_data)


def _serialize_game_hub_from_user(user_data: dict) -> dict:
    game_rtp = _get_game_rtp_settings()
    return {
        'mines': {
            'user': _get_user_mines_stats(user_data),
            'global': _get_global_mines_stats(),
        },
        'crash': {
            'user': _get_user_crash_stats(user_data),
            'global': _get_global_crash_stats(),
        },
        'roulette': {
            'user': _get_user_roulette_stats(user_data),
            'global': _get_global_roulette_stats(),
        },
        'coin': {
            'user': _get_user_game_stats(user_data, 'coin'),
            'global': _get_global_game_stats('coin'),
        },
        'upgrade': {
            'user': _get_user_game_stats(user_data, 'upgrade'),
            'global': _get_global_game_stats('upgrade'),
        },
        'config': {
            'mines': {
                'min_bet': MIN_BET,
                'max_bet': MAX_BET,
                'mines_count': MINES_COUNT,
                'multipliers': MINES_MULTIPLIERS,
                'rtp_percent': game_rtp.get('mines', DEFAULT_GAME_RTP_PERCENT['mines']),
            },
            'crash': {
                'min_bet': CRASH_MIN_BET,
                'max_bet': CRASH_MAX_BET,
                'min_x': CRASH_MIN_X,
                'max_x': CRASH_MAX_X,
                'rtp_percent': game_rtp.get('crash', DEFAULT_GAME_RTP_PERCENT['crash']),
            },
            'roulette': {
                'min_bet': ROULETTE_MIN_BET,
                'max_bet': ROULETTE_MAX_BET,
                'green_payout': ROULETTE_GREEN_PAYOUT,
                'rtp_percent': game_rtp.get('roulette', DEFAULT_GAME_RTP_PERCENT['roulette']),
            },
            'coin': {
                'min_bet': float(COIN_SETTINGS.get('min_bet', 5)),
                'max_bet': float(COIN_SETTINGS.get('max_bet', 10000)),
                'odds': _get_coin_settings().get('odds', {}),
                'multipliers': _get_coin_settings().get('multipliers', {}),
            },
            'upgrade': {
                'rtp_percent': game_rtp.get('upgrade', DEFAULT_GAME_RTP_PERCENT.get('upgrade', 95.0)),
                'min_stars': 5,
                'max_stars': 10000,
            },
            'dice': {'rounds': [1, 3, 5]},
            'game_rtp_percent': game_rtp,
            'cases': {
                tier: {
                    'label': cfg.get('label'),
                    'cost': cfg.get('cost'),
                    'min_reward': cfg.get('min_reward'),
                    'max_reward': cfg.get('max_reward'),
                    'return_to_pay': _get_case_return_to_pay(tier),
                }
                for tier, cfg in CASE_SETTINGS.items()
            },
        },
    }


def _serialize_bootstrap(tg_user, user_data) -> dict:
    ton_pricing = ton_to_uah_buy_price(1, markup_percent=0)
    is_admin = int(tg_user.id) in set(int(x) for x in ADMIN_IDS)
    mines_session = user_data.get('miniapp_mines') if isinstance(user_data, dict) else None
    if mines_session and not isinstance(mines_session.get('board'), list):
        # Cleanup legacy/broken session payloads that would block starting a new game.
        user_data['miniapp_mines'] = None
        db.save_data()
        mines_session = None
    return {
        'user': asdict(tg_user),
        'is_admin': is_admin,
        'profile': _serialize_profile(tg_user.id),
        'pricing': {
            'star_packages': get_star_packages(),
            'premium_prices': get_premium_prices(),
            'nft_gift_prices': _get_nft_manual_prices(),
            'nft_gift_images': _get_nft_manual_images(),
            'nft_case_chances': _get_nft_case_chances(),
            'case_chances': get_case_chances(),
            'case_definitions': CASE_DEFINITIONS,
            'game_rtp_percent': _get_game_rtp_settings(),
            'ton_market': ton_pricing,
            'nft_catalog': _get_nft_shop_catalog(),
        },
        'constants': {
            'mono_card': get_active_payment_details()['mono_card'],
            'ton_address': get_active_payment_details()['ton_address'],
            'active_shift': get_active_payment_details(),
            'support_username': SUPPORT_USERNAME,
            'premium_seller_username': PREMIUM_SELLER_USERNAME,
            'reviews_channel': REVIEWS_CHANNEL,
            'webapp_url': WEBAPP_URL,
            'bot_username': BOT_USERNAME,
        },
        'transactions': _recent_transactions(tg_user.id),
        'reviews': _serialize_reviews(5),
        'games': _serialize_game_hub(tg_user.id),
        'mines_session': _serialize_mines_session(mines_session),
        'casino': _serialize_casino(user_data),
        'inventory': _serialize_inventory(user_data, tg_user.id),
        'upgrade_targets': _get_case_nft_catalog(),
        'nft_shop_catalog': _get_nft_shop_catalog(),
        'referral': get_user_referral_summary(tg_user.id, BOT_USERNAME),
    }


def _find_user_id_by_username(username: str | None) -> int | None:
    db.refresh()
    if not username:
        return None
    target = username.strip().lstrip('@').lower()
    if not target:
        return None
    for user_id, data in db.users.items():
        stored = (data.get('username') or '').strip().lstrip('@').lower()
        if stored == target:
            try:
                return int(user_id)
            except Exception:
                return None
    return None


def _create_transaction(payload: dict) -> dict:
    db.refresh()
    transaction = {'id': db.transaction_id_counter, **payload, 'date': datetime.now().strftime('%d.%m.%Y %H:%M'), 'source': 'app'}
    active_pay = get_active_payment_details()
    if active_pay.get('shift_active'):
        transaction.setdefault('shift_id', active_pay.get('shift_id'))
        transaction.setdefault('shift_worker', active_pay.get('worker_name'))
    db.transactions.append(transaction)
    db.transaction_id_counter += 1
    db.save_data()
    return transaction


def _ton_amount_for_uah(amount_uah: float) -> float:
    ton_amount = uah_to_ton(float(amount_uah))
    if ton_amount is None:
        _error(503, 'Не удалось получить курс TON. Попробуйте позже.')
    return float(ton_amount)


def _build_stars_instructions(stars: int, price: float, payment_method: str, target_username: str | None) -> dict:
    ton_amount = _ton_amount_for_uah(price)
    active_pay = get_active_payment_details()
    result = {
        'stars': stars,
        'price_uah': round(price, 2),
        'payment_method': payment_method,
        'target_username': target_username,
        'upload_required': payment_method in {'mono', 'ton_wallet'},
    }
    if payment_method == 'mono':
        result['payment_details'] = {'type': 'mono', 'amount_uah': round(price, 2), 'mono_card': active_pay['mono_card']}
    elif payment_method == 'ton_wallet':
        result['payment_details'] = {'type': 'ton_wallet', 'amount_ton': ton_amount, 'ton_address': active_pay['ton_address']}
    return result


def _calculate_stars_order_price(stars: int) -> float:
    try:
        stars = int(stars)
    except (ValueError, TypeError):
        _error(400, 'Некорректное количество звезд')
    if stars < 50:
        _error(400, 'Минимальный заказ — 50 звезд')
    if stars > 100000:
        _error(400, 'Превышен лимит заказа звезд')
    packages = {int(k): float(v) for k, v in get_star_packages().items()}
    if stars in packages:
        return round(float(packages[stars]), 2)

    # Keep manual package control but allow arbitrary user amount via interpolation.
    points = sorted((amount, price) for amount, price in packages.items() if amount > 0 and price > 0)
    if not points:
        _error(400, 'Пакеты Stars не настроены')

    lower = None
    upper = None
    for amount, price in points:
        if amount < stars:
            lower = (amount, price)
            continue
        if amount > stars:
            upper = (amount, price)
            break

    if lower and upper:
        x0, y0 = lower
        x1, y1 = upper
        ratio = (stars - x0) / (x1 - x0)
        return round(y0 + (y1 - y0) * ratio, 2)

    if lower:
        x0, y0 = lower
        return round(stars * (y0 / x0), 2)

    x1, y1 = points[0]
    return round(stars * (y1 / x1), 2)


def _build_premium_instructions(months: int, price: float, payment_method: str) -> dict:
    ton_amount = _ton_amount_for_uah(price)
    active_pay = get_active_payment_details()
    result = {
        'months': months,
        'price_uah': round(price, 2),
        'payment_method': payment_method,
        'upload_required': payment_method in {'mono', 'ton_wallet'},
    }
    if payment_method == 'mono':
        result['payment_details'] = {'type': 'mono', 'amount_uah': round(price, 2), 'mono_card': active_pay['mono_card']}
    elif payment_method == 'ton_wallet':
        result['payment_details'] = {'type': 'ton_wallet', 'amount_ton': ton_amount, 'ton_address': active_pay['ton_address']}
    return result


def _build_ton_topup_preview(ton_amount: float, payment_method: str) -> dict:
    pricing = ton_to_uah_buy_price(ton_amount, markup_percent=0)
    if pricing is None:
        _error(503, 'Не удалось получить курс TON. Попробуйте позже.')
    ton_amount = round(float(pricing['ton_amount']), 4)
    base_total_uah = round(float(pricing['base_total_uah']), 2)
    active_pay = get_active_payment_details()
    if payment_method == 'mono':
        fee_percent = 10.0 if ton_amount <= 5 else 7.0
        total_uah = round(base_total_uah * (1 + fee_percent / 100), 2)
        return {
            'ton_amount': ton_amount,
            'payment_method': 'mono',
            'upload_required': True,
            'payment_details': {
                'type': 'mono',
                'amount_uah': total_uah,
                'mono_card': active_pay['mono_card'],
                'fee_percent': fee_percent,
                'base_total_uah': base_total_uah,
            },
        }
    return {
        'ton_amount': ton_amount,
        'payment_method': 'ton_wallet',
        'upload_required': True,
        'payment_details': {
            'type': 'ton_wallet',
            'amount_ton': ton_amount,
            'ton_address': active_pay['ton_address'],
            'base_total_uah': base_total_uah,
        },
    }


def _user_balance(user_data: dict, currency: str) -> float:
    return get_numeric_ton_balance(user_data) if currency == 'ton' else get_numeric_balance(user_data)


def _set_user_balance(user_data: dict, currency: str, value: float) -> None:
    if currency == 'ton':
        user_data['balance_ton'] = round(value, 4)
    else:
        user_data['balance_stars'] = round(value, 1)
        user_data['total_stars'] = float(user_data.get('total_stars', 0) or 0)


def _sub_balance_checked(user_data: dict, currency: str, amount: float) -> None:
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        _error(400, 'Некорректная сумма')
    if not math.isfinite(amount) or amount <= 0:
        _error(400, 'Сумма списания должна быть положительным числом')
    with _BALANCE_LOCK:
        current = _user_balance(user_data, currency)
        if not math.isfinite(current) or amount > current:
            _error(400, 'Недостаточно средств на балансе')
        if currency == 'ton':
            sub_ton_balance(user_data, amount)
        else:
            sub_star_balance(user_data, amount)


def _add_balance(user_data: dict, currency: str, amount: float) -> None:
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        _error(400, 'Некорректная сумма')
    if not math.isfinite(amount) or amount < 0:
        _error(400, 'Сумма пополнения должна быть неотрицательным числом')
    if amount == 0:
        return
    with _BALANCE_LOCK:
        if currency == 'ton':
            add_ton_balance(user_data, amount)
        else:
            add_star_balance(user_data, amount)


def _roulette_multiplier(color: str) -> float:
    if color == 'green':
        return float(ROULETTE_GREEN_PAYOUT)
    base = ROULETTE_RED_PAYOUT if color == 'red' else ROULETTE_WHITE_PAYOUT
    return base


def _roll_roulette_color() -> str:
    return 'green' if random.randint(1, 30) == 30 else random.choice(['red', 'white'])


def _generate_mines_board() -> list[int]:
    board = [0] * 16
    for idx in random.sample(range(16), _effective_mines_count()):
        board[idx] = 1
    return board


def _serialize_mines_session(session: dict | None) -> dict | None:
    if not session:
        return None
    safe_clicks = int(session.get('safe_clicks', 0) or 0)
    next_base = MINES_MULTIPLIERS[min(safe_clicks, len(MINES_MULTIPLIERS) - 1)] if safe_clicks < len(MINES_MULTIPLIERS) else MINES_MULTIPLIERS[-1]
    current_base = MINES_MULTIPLIERS[max(safe_clicks - 1, 0)] if safe_clicks else 0
    return {
        'currency': session.get('currency'),
        'bet': session.get('bet'),
        'revealed': session.get('revealed', []),
        'safe_clicks': safe_clicks,
        'next_multiplier': next_base,
        'current_multiplier': current_base if safe_clicks else 0,
    }


def _simulate_crash_point() -> float:
    target_rtp = max(0.01, min(0.99, _get_game_rtp_percent('crash') / 100.0))
    r = random.random()
    point = max(CRASH_MIN_X, min(CRASH_MAX_X, round(0.99 / max(0.01, 1 - r), 2)))
    if random.random() > target_rtp:
        point = round(max(CRASH_MIN_X, point * random.uniform(0.65, 0.95)), 2)
    return min(point, CRASH_MAX_X)


def _build_crash_history(crash_point: float) -> list[float]:
    current = 1.00
    values = [1.0]
    while current < crash_point:
        if current < 1.45:
            current += 0.01
        elif current < 3.5:
            current += 0.02
        else:
            current += 0.04
        values.append(round(min(current, crash_point), 2))
        if len(values) >= 120:
            break
    if values[-1] != round(crash_point, 2):
        values.append(round(crash_point, 2))
    return values


def _choose_racket_outcome() -> dict:
    roll = random.random()
    current = 0.0
    for outcome in CASINO_RACKET_OUTCOMES:
        current += outcome['chance']
        if roll < current:
            return outcome
    return CASINO_RACKET_OUTCOMES[-1]


def _open_casino_case(user_data: dict, tier: str) -> dict:
    config = CASE_SETTINGS.get(tier)
    if not config:
        _error(400, 'Неверный тип кейса')
    _sub_balance_checked(user_data, 'stars', float(config['cost']))
    reward = _select_case_reward(
        int(config['min_reward']),
        int(config['max_reward']),
        _get_game_rtp_factor('cases'),
    )
    _add_balance(user_data, 'stars', reward)
    casino = user_data.setdefault('casino', _default_casino_data())
    casino['cases'][tier] = int(casino['cases'].get(tier, 0) or 0) + 1
    casino['last_case'] = {
        'tier': tier,
        'label': config['label'],
        'reward': reward,
        'description': f'Открыт {config["label"]}, получено {reward} ⭐',
    }
    return casino['last_case']


def _build_case150_pool() -> list[dict]:
    prices = _get_nft_manual_prices()
    pool: list[dict] = []
    for item in CASE150_DROP_TABLE:
        entry = dict(item)
        if entry.get('kind') == 'gift':
            model = str(entry.get('model') or '').strip().lower()
            entry['value'] = int(prices.get(model, entry.get('value', 0) or 0))
        chance = _resolve_case_gift_chance(entry, tier='case150')
        entry['chance_percent'] = round(chance, 4)
        entry['weight'] = max(1, int(round(chance * 100)))
        pool.append(entry)
    return pool


def _build_special_case_pool(drop_table: list[dict], case_rtp_percent: float | None = None, case_cost: float | None = None, tier: str | None = None) -> list[dict]:
    prices = _get_nft_manual_prices()
    pool: list[dict] = []
    rtp_percent = float(case_rtp_percent if case_rtp_percent is not None else 100.0)
    rtp_factor = max(0.1, min(3.0, rtp_percent / 100.0))
    case_cost_value = float(case_cost if case_cost is not None else 0.0)
    target_mean = case_cost_value * rtp_factor if case_cost_value > 0 else 0.0
    for item in drop_table:
        entry = dict(item)
        if entry.get('kind') == 'gift':
            model = str(entry.get('model') or '').strip().lower()
            entry['value'] = int(prices.get(model, entry.get('value', 0) or 0))
        chance = _resolve_case_gift_chance(entry, tier=tier)
        entry['chance_percent'] = round(chance, 4)
        if entry.get('kind') == 'stars':
            base_weight = max(1.0, chance * 100.0 * rtp_factor)
            entry['weight'] = max(1, int(round(base_weight)))
        else:
            base_weight = max(1.0, chance * 100.0)
            if target_mean > 0 and entry.get('value', 0):
                base_weight *= max(0.3, min(3.0, (entry.get('value', 0) / max(case_cost_value, 1)) / max(rtp_factor, 0.1)))
            entry['weight'] = max(1, int(round(base_weight)))
        pool.append(entry)
    return pool


def _pick_weighted_reward(pool: list[dict]) -> dict:
    weighted = [item for item in pool if int(item.get('weight', 0) or 0) > 0]
    if not weighted:
        _error(400, 'Кейс временно недоступен: не настроены шансы дропа')

    total_weight = sum(int(item.get('weight', 0) or 0) for item in weighted)
    roll = random.randint(1, total_weight)
    current = 0
    for item in weighted:
        current += int(item.get('weight', 0) or 0)
        if roll <= current:
            return item
    return weighted[-1]


def _open_special_case(user_data: dict, tier: str) -> dict:
    config = SPECIAL_CASES_CONFIG.get(tier)
    if not config:
        _error(400, 'Неверный тип кейса')

    _sub_balance_checked(user_data, 'stars', float(config['cost']))
    pool = _build_special_case_pool(config['drop_table'], _get_game_rtp_percent(tier), float(config['cost']), tier=tier)
    reward = _pick_weighted_reward(pool)

    if reward.get('kind') == 'stars':
        _add_balance(user_data, 'stars', float(reward.get('value', 0) or 0))
    else:
        reward_val = int(reward.get('value', 0) or 0)
        inventory = user_data.setdefault('miniapp_inventory', [])
        inventory.insert(0, {
            'id': uuid4().hex,
            'kind': 'gift',
            'label': reward.get('label'),
            'name': reward.get('name'),
            'model': reward.get('model'),
            'value': reward_val,
            'icon': reward.get('icon', '🎁'),
            'rarity': get_rarity_by_stars(reward_val),
            'createdAt': datetime.now().isoformat(),
        })

    casino = user_data.setdefault('casino', _default_casino_data())
    casino['cases'][tier] = int(casino['cases'].get(tier, 0) or 0) + 1
    if reward.get('kind') == 'stars':
        description = f"Открыт {config['label']}, получено {reward.get('label')}"
    else:
        description = f"Открыт {config['label']}, выпал {reward.get('label')}"

    reward_item_val = int(reward.get('value', 0) or 0)
    casino['last_case'] = {
        'tier': tier,
        'label': config['label'],
        'reward': reward.get('value'),
        'description': description,
        'reward_kind': reward.get('kind'),
        'reward_item': {
            'kind': reward.get('kind'),
            'label': reward.get('label'),
            'name': reward.get('name'),
            'model': reward.get('model'),
            'value': reward_item_val,
            'unit': '⭐',
            'icon': reward.get('icon', '🎁'),
            'rarity': get_rarity_by_stars(reward_item_val),
        },
    }
    return casino['last_case']


def _pick_case150_reward_by_rtp() -> dict:
    pool = _build_case150_pool()
    case_rtp_percent = _get_game_rtp_percent('case150')
    weighted = []
    total_weight = 0.0
    for item in pool:
        chance = max(0.0, float(item.get('chance_percent', item.get('weight', 0) or 0) or 0))
        if chance <= 0 and item.get('weight') is not None:
            chance = max(0.0, float(int(item.get('weight', 0) or 0)) / 100.0)
        rtp_factor = max(0.1, min(3.0, case_rtp_percent / 100.0))
        weight = max(1.0, chance * 100.0 * (rtp_factor if item.get('kind') == 'stars' else 1.0))
        total_weight += weight
        weighted.append((item, weight))

    roll = random.random() * total_weight
    picked = weighted[0][0]
    for item, weight in weighted:
        roll -= weight
        if roll <= 0:
            picked = item
            break
    return picked


def _open_case150(user_data: dict) -> dict:
    config = CASE_SETTINGS.get('case150') or {'label': 'Летний кейс (150⭐️)', 'cost': 150}
    _sub_balance_checked(user_data, 'stars', float(config.get('cost', 150)))
    reward = _pick_case150_reward_by_rtp()

    reward_value = int(reward.get('value', reward.get('reward_value', 0) or 0))

    if reward.get('kind') == 'stars':
        _add_balance(user_data, 'stars', float(reward_value))
    else:
        inventory = user_data.setdefault('miniapp_inventory', [])
        inventory.insert(0, {
            'id': uuid4().hex,
            'kind': 'gift',
            'label': reward.get('label'),
            'name': reward.get('name'),
            'model': reward.get('model'),
            'value': reward_value,
            'icon': reward.get('icon', '🎁'),
            'rarity': get_rarity_by_stars(reward_value),
            'createdAt': datetime.now().isoformat(),
        })

    casino = user_data.setdefault('casino', _default_casino_data())
    casino['cases']['case150'] = int(casino['cases'].get('case150', 0) or 0) + 1
    if reward.get('kind') == 'stars':
        description = f"Открыт {config.get('label', 'Бронзовый кейс')}, получено {reward.get('label')}"
    else:
        description = f"Открыт {config.get('label', 'Бронзовый кейс')}, выпал {reward.get('label')}"
    casino['last_case'] = {
        'tier': 'case150',
        'label': config.get('label', 'Бронзовый кейс'),
        'reward': reward_value,
        'description': description,
        'reward_kind': reward.get('kind'),
        'reward_item': {
            'kind': reward.get('kind'),
            'label': reward.get('label'),
            'name': reward.get('name'),
            'model': reward.get('model'),
            'value': reward_value,
            'unit': '⭐',
            'icon': reward.get('icon', '🎁'),
            'rarity': get_rarity_by_stars(reward_value),
        },
    }
    return casino['last_case']


def _buy_casino_upgrade(user_data: dict, upgrade: str) -> dict:
    config = CASINO_UPGRADES.get(upgrade)
    if not config:
        _error(400, 'Неверный апгрейд')
    _sub_balance_checked(user_data, 'stars', float(config['cost']))
    casino = user_data.setdefault('casino', _default_casino_data())
    casino['upgrades'][upgrade] = int(casino['upgrades'].get(upgrade, 0) or 0) + 1
    casino['last_upgrade'] = {
        'upgrade': upgrade,
        'label': config['label'],
        'cost': config['cost'],
        'bonus_stars': config.get('bonus_stars', 0),
    }
    if config.get('bonus_stars', 0):
        _add_balance(user_data, 'stars', float(config['bonus_stars']))
    return casino['last_upgrade']


_NO_CACHE_HEADERS = {
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0',
}


@app.get('/')
def root_index():
    return FileResponse(WEBAPP_DIR / 'index.html', headers=_NO_CACHE_HEADERS)


@app.get('/webapp')
def webapp_index():
    return FileResponse(WEBAPP_DIR / 'index.html', headers=_NO_CACHE_HEADERS)


@app.get('/webapp/')
def webapp_index_slash():
    return FileResponse(WEBAPP_DIR / 'index.html', headers=_NO_CACHE_HEADERS)


@app.get('/health')
def health():
    return {'ok': True}


@app.get('/api/bootstrap')
def bootstrap(request: Request, init_data: str | None = None):
    token = _extract_init_data(request, init_data)
    tg_user, user_data = _require_user(token)
    return _serialize_bootstrap(tg_user, user_data)


@app.get('/api/referrals')
def get_referrals_endpoint(request: Request, init_data: str | None = None):
    token = _extract_init_data(request, init_data)
    tg_user, user_data = _require_user(token)
    return {'ok': True, 'referral': get_user_referral_summary(tg_user.id, BOT_USERNAME)}


@app.get('/api/nft/pricing')
def nft_pricing(request: Request, model: str, init_data: str | None = None):
    token = _extract_init_data(request, init_data)
    _require_user(token)
    quote = _resolve_nft_model_price(model)
    return {'ok': True, 'quote': quote}


@app.get('/api/nft/pricing/batch')
def nft_pricing_batch(request: Request, models: str, init_data: str | None = None):
    token = _extract_init_data(request, init_data)
    _require_user(token)
    names = [item.strip().lower() for item in (models or '').split(',') if item.strip()]
    unique_names: list[str] = []
    seen = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        unique_names.append(name)

    quotes = {name: _resolve_nft_model_price(name) for name in unique_names}
    return {'ok': True, 'quotes': quotes}


@app.get('/api/admin/dashboard')
def admin_dashboard(request: Request, init_data: str | None = None):
    token = _extract_init_data(request, init_data)
    _require_admin(token, request=request)
    db.refresh()
    suggestions = list(db.suggestions)[-25:]
    suggestions.reverse()
    unsubs = list(db.sub_logs)[-30:]
    unsubs.reverse()
    promo_items = list(db.promocodes)[-30:]
    promo_items.reverse()
    return {
        'ok': True,
        'summary': _build_admin_summary(),
        'settings': get_managed_settings(),
        'prices': {
            'star_packages': get_star_packages(),
            'star_rates': [{'min': mn, 'max': mx, 'rate': rate} for mn, mx, rate in get_star_rates()],
            'premium_prices': get_premium_prices(),
            'nft_gift_prices': _get_nft_manual_prices(),
            'nft_gift_images': _get_nft_manual_images(),
            'nft_case_chances': _get_nft_case_chances(),
            'case_chances': get_case_chances(),
            'case_definitions': CASE_DEFINITIONS,
            'game_rtp_percent': _get_game_rtp_settings(),
            'coin_game_settings': _get_coin_settings(),
        },
        'suggestions': suggestions,
        'unsubs': unsubs,
        'promocodes': promo_items,
    }


@app.get('/api/admin/prices/star-rates')
def admin_get_star_rates(init_data: str = 'desktop'):
    _require_admin(init_data)
    rates = get_star_rates()
    return {'ok': True, 'rates': [{'min': mn, 'max': mx, 'rate': rate} for mn, mx, rate in rates]}


@app.post('/api/admin/prices/star-rates')
def admin_update_star_rates(payload: AdminStarRatesIn):
    _require_admin(payload.init_data)
    if not isinstance(payload.rates, list):
        _error(400, 'Некорректный формат rates')
    parsed = []
    for item in payload.rates:
        if isinstance(item, dict):
            mn = int(item.get('min', 0))
            mx = int(item.get('max', 0))
            rate = float(item.get('rate', 0))
            if mn <= 0 or mx < mn or rate <= 0:
                _error(400, f'Некорректный диапазон или ставка: {item}')
            parsed.append((mn, mx, rate))
        elif isinstance(item, (list, tuple)) and len(item) == 3:
            parsed.append((int(item[0]), int(item[1]), float(item[2])))
    if not parsed:
        _error(400, 'Список ставок пуст')
    update_star_rates(parsed)
    return {'ok': True, 'rates': [{'min': mn, 'max': mx, 'rate': rate} for mn, mx, rate in get_star_rates()]}


@app.post('/api/admin/prices/star-packages')
def admin_update_star_packages(payload: AdminStarPackagesIn):
    _require_admin(payload.init_data)
    parsed = _parse_star_packages_payload(payload.packages)
    update_star_packages(parsed)
    return {'ok': True, 'star_packages': get_star_packages()}


@app.post('/api/admin/prices/premium')
def admin_update_premium_prices(payload: AdminPremiumPricesIn):
    _require_admin(payload.init_data)
    parsed = _parse_premium_prices_payload(payload.prices)
    update_premium_prices(parsed)
    return {'ok': True, 'premium_prices': get_premium_prices()}


@app.post('/api/admin/prices/nft')
def admin_update_nft_prices(payload: AdminNftPricesIn):
    _require_admin(payload.init_data)
    prices = payload.prices if isinstance(payload.prices, dict) else {}
    updated = _set_nft_manual_prices(prices)
    return {'ok': True, 'nft_gift_prices': updated}


@app.post('/api/admin/prices/nft-images')
def admin_update_nft_images(payload: AdminNftImagesIn):
    _require_admin(payload.init_data)
    images = payload.images if isinstance(payload.images, dict) else {}
    updated = _set_nft_manual_images(images)
    return {'ok': True, 'nft_gift_images': updated}


@app.post('/api/admin/prices/nft-case-chances')
def admin_update_nft_case_chances(payload: AdminNftCaseChancesIn):
    _require_admin(payload.init_data)
    chances = payload.chances if isinstance(payload.chances, dict) else {}
    updated = _set_nft_case_chances(chances)
    return {'ok': True, 'nft_case_chances': updated}


@app.get('/api/admin/prices/case-chances')
def admin_get_case_chances(init_data: str = 'desktop'):
    _require_admin(init_data)
    result_cases = []
    for tier, cdef in CASE_DEFINITIONS.items():
        result_cases.append({
            'tier': tier,
            'label': cdef['label'],
            'cost': cdef['cost'],
            'items': get_case_items(tier),
        })
    return {'ok': True, 'cases': result_cases, 'chances': get_case_chances()}


@app.post('/api/admin/prices/case-chances')
def admin_update_case_chances(payload: AdminCaseChancesIn):
    _require_admin(payload.init_data)
    tier = (payload.tier or '').strip()
    if tier and tier in CASE_DEFINITIONS:
        updated = set_case_chances(tier, payload.chances)
        return {'ok': True, 'tier': tier, 'chances': updated}
    elif isinstance(payload.chances, dict):
        res = {}
        for c_tier, c_chances in payload.chances.items():
            if c_tier in CASE_DEFINITIONS and isinstance(c_chances, dict):
                res[c_tier] = set_case_chances(c_tier, c_chances)
        return {'ok': True, 'chances': get_case_chances()}
    _error(400, 'Неверный формат запроса: укажите tier кейса или словарь по кейсам')


class ShopNftBuyIn(BaseModel):
    init_data: str
    model: str


@app.post('/api/shop/nft/buy')
def shop_buy_nft(payload: ShopNftBuyIn):
    tg_user, user_data = _require_user(payload.init_data, allow_demo=False)
    model = (payload.model or '').strip().lower()
    if not model:
        _error(400, 'Не указана модель подарка')

    manual_prices = _get_nft_manual_prices()
    price = manual_prices.get(model)
    if not price or price <= 0:
        _error(404, 'Подарок не найден или недоступен для покупки')

    with _BALANCE_LOCK:
        user_stars = float(user_data.get('balance_stars', 0) or 0)
        if user_stars < price:
            _error(400, f'Недостаточно звёзд. Требуется {price} ⭐, ваш баланс: {int(user_stars)} ⭐')

        _sub_balance_checked(user_data, 'stars', float(price))

        gift_meta = _find_nft_meta(model)
        item = {
            'id': uuid4().hex,
            'kind': 'gift',
            'label': gift_meta.get('label') or gift_meta.get('name') or model,
            'name': gift_meta.get('name') or gift_meta.get('label') or model,
            'model': model,
            'value': int(price),
            'icon': '🎁',
            'rarity': gift_meta.get('rarity', 'common'),
            'createdAt': datetime.now().isoformat(),
        }
        user_data.setdefault('miniapp_inventory', []).insert(0, item)

        _create_transaction({
            'user_id': tg_user.id,
            'type': 'nft_shop_buy',
            'model': model,
            'item_id': item['id'],
            'amount_stars': price,
            'description': f"Покупка NFT подарка {item['label']}",
            'status': 'completed',
        })

        db.save_data()

    return {
        'ok': True,
        'item': item,
        'profile': _serialize_profile_from_user(user_data),
        'inventory': _serialize_inventory(user_data, tg_user.id),
        'message': f"Подарок {item['label']} успешно куплен!",
    }


@app.get('/api/shop/nft/catalog')
def shop_nft_catalog(init_data: str):
    _require_user(init_data)
    return {'ok': True, 'catalog': _get_nft_shop_catalog()}


class AdminNftGiftAddIn(BaseModel):
    init_data: str
    model: str
    name: str = ''
    price: int
    image_url: str = ''


@app.post('/api/admin/prices/nft/add')
def admin_add_nft_gift(payload: AdminNftGiftAddIn):
    _require_admin(payload.init_data)
    model = (payload.model or '').strip().lower()
    if not model:
        _error(400, 'Не указан идентификатор (model) подарка')
    price = max(1, int(payload.price or 100))

    prices = _get_nft_manual_prices()
    prices[model] = price
    _set_nft_manual_prices(prices)

    if payload.image_url and _is_http_image_url(payload.image_url):
        images = _get_nft_manual_images()
        images[model] = payload.image_url.strip()
        _set_nft_manual_images(images)

    return {
        'ok': True,
        'model': model,
        'prices': _get_nft_manual_prices(),
        'images': _get_nft_manual_images(),
        'catalog': _get_nft_shop_catalog(),
    }


@app.post('/api/admin/prices/nft/delete')
def admin_delete_nft_gift(payload: AdminNftGiftDeleteIn):
    _require_admin(payload.init_data)
    model = (payload.model or '').strip().lower()
    if not model:
        _error(400, 'Не указана модель подарка')
    prices = _get_nft_manual_prices()
    images = _get_nft_manual_images()
    chances = _get_nft_case_chances()
    if model in prices:
        del prices[model]
        _set_nft_manual_prices(prices)
    if model in images:
        del images[model]
        _set_nft_manual_images(images)
    if model in chances:
        del chances[model]
        _set_nft_case_chances(chances)
    return {
        'ok': True,
        'model': model,
        'prices': _get_nft_manual_prices(),
        'images': _get_nft_manual_images(),
        'catalog': _get_nft_shop_catalog(),
    }


@app.post('/api/admin/games/rtp')
def admin_update_game_rtp(payload: AdminGameRtpIn):
    _require_admin(payload.init_data)
    raw = payload.rtp_percent if isinstance(payload.rtp_percent, dict) else {}
    updated = _set_game_rtp_settings(raw)
    return {'ok': True, 'game_rtp_percent': updated}


class CoinSettingsIn(BaseModel):
    init_data: str
    min_bet: float = Field(gt=0)
    max_bet: float = Field(gt=0)
    odds: dict[str, float]
    multipliers: dict[str, float]


@app.post('/api/admin/games/coin-settings')
def admin_update_coin_settings(payload: CoinSettingsIn):
    _require_admin(payload.init_data)
    updated = _set_coin_settings({
        'min_bet': float(payload.min_bet),
        'max_bet': float(payload.max_bet),
        'odds': {k: float(v) for k, v in payload.odds.items()},
        'multipliers': {k: float(v) for k, v in payload.multipliers.items()},
    })
    return {'ok': True, 'coin_game_settings': updated}


@app.post('/api/admin/promocodes/create')
def admin_create_promocode(request: Request, payload: AdminPromoCreateIn):
    token = _extract_init_data(request, payload.init_data)
    tg_user, _ = _require_admin(token, request=request)
    code = (payload.code or '').strip().lower()
    if len(code) < 2 or len(code) > 32:
        _error(400, 'Длина промокода должна быть от 2 до 32 символов')

    amount_stars = int(payload.amount_stars)
    if amount_stars <= 0 or amount_stars > 1000:
        _error(400, 'Сумма промокода должна быть от 1 до 1000 Stars')

    max_uses = int(payload.max_uses)
    if max_uses <= 0 or max_uses > 100:
        _error(400, 'Количество активаций должно быть от 1 до 100')

    db.refresh()
    if any(str(item.get('code', '')).strip().lower() == code for item in db.promocodes):
        _error(409, 'Такой промокод уже существует')

    promo = {
        'code': code,
        'max_uses': max_uses,
        'used_count': 0,
        'amount_stars': amount_stars,
        'used_by': [],
        'active': True,
        'created_by': int(tg_user.id),
        'created_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
    }
    db.promocodes.append(promo)
    db.save_data()

    try:
        audit_file = BASE_DIR / 'data' / 'admin_balance_audit.json'
        records = []
        if audit_file.exists():
            records = json.loads(audit_file.read_text(encoding='utf-8') or '[]')
        records.append({
            'action': 'create_promocode',
            'admin_id': tg_user.id,
            'code': code,
            'amount_stars': amount_stars,
            'max_uses': max_uses,
            'date': datetime.now().isoformat(),
        })
        audit_file.write_text(json.dumps(records[-500:], ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass

    return {'ok': True, 'promocode': promo}


@app.post('/api/admin/suggestions/action')
def admin_suggestion_action(payload: AdminSuggestionActionIn):
    _require_admin(payload.init_data)
    db.refresh()
    target = None
    for suggestion in db.suggestions:
        if int(suggestion.get('id', 0) or 0) == int(payload.suggestion_id):
            target = suggestion
            break
    if not target:
        _error(404, 'Предложение не найдено')

    target['status'] = payload.action
    target['moderated_at'] = datetime.now().strftime('%d.%m.%Y %H:%M')
    db.save_data()
    return {'ok': True, 'suggestion': target}


@app.post('/api/admin/suggestions/delete')
def admin_delete_suggestion(payload: AdminSuggestionDeleteIn):
    _require_admin(payload.init_data)
    db.refresh()
    orig_len = len(db.suggestions)
    db.suggestions = [s for s in db.suggestions if int(s.get('id', 0) or 0) != int(payload.suggestion_id)]
    deleted = len(db.suggestions) < orig_len
    if deleted:
        db.save_data()
    return {'ok': True, 'deleted': deleted}


@app.get('/api/admin/track-user')
def admin_track_user(request: Request, identifier: str, init_data: str | None = None):
    token = _extract_init_data(request, init_data)
    _require_admin(token, request=request)
    user_id, user_data = _find_user_by_identifier(identifier)
    if not user_id or not user_data:
        _error(404, 'Пользователь не найден')

    stats = {
        'id': int(user_id),
        'username': user_data.get('username'),
        'total_stars': float(user_data.get('total_stars', 0) or 0),
        'balance_stars': float(user_data.get('balance_stars', 0) or 0),
        'balance_ton': float(user_data.get('balance_ton', 0) or 0),
        'registration_date': user_data.get('registration_date'),
        'last_active': user_data.get('last_active'),
        'games': user_data.get('games', {}),
        'casino': user_data.get('casino', {}),
    }

    history = [t for t in db.transactions if int(t.get('user_id', 0) or 0) == int(user_id)]
    history = sorted(history, key=lambda x: int(x.get('id', 0) or 0), reverse=True)[:15]
    return {'ok': True, 'user': stats, 'transactions': history}


@app.post('/api/admin/users/reset-mines-session')
def admin_reset_user_mines_session(payload: AdminResetMinesSessionIn):
    _require_admin(payload.init_data)
    db.refresh()
    key = str(int(payload.user_id))
    user_data = db.users.get(key)
    if not isinstance(user_data, dict):
        _error(404, 'Пользователь не найден')

    had_active_session = bool(user_data.get('miniapp_mines'))
    user_data['miniapp_mines'] = None
    db.save_data()
    return {'ok': True, 'user_id': int(payload.user_id), 'had_active_session': had_active_session}


@app.post('/api/admin/users/reset-all-games')
def admin_reset_user_all_games(payload: AdminResetMinesSessionIn):
    _require_admin(payload.init_data)
    db.refresh()
    key = str(int(payload.user_id))
    user_data = db.users.get(key)
    if not isinstance(user_data, dict):
        _error(404, 'Пользователь не найден')

    active_games_reset = []
    game_keys = [
        ('miniapp_mines', 'Мины'),
        ('miniapp_crash', 'Crash'),
        ('miniapp_tower', 'Tower'),
        ('miniapp_blackjack', 'Blackjack'),
        ('current_game', 'Бот-игра'),
    ]
    for g_key, g_name in game_keys:
        if user_data.get(g_key):
            active_games_reset.append(g_name)
            user_data[g_key] = None

    db.save_data()
    return {
        'ok': True,
        'user_id': int(payload.user_id),
        'reset_count': len(active_games_reset),
        'reset_games': active_games_reset,
        'had_active_session': len(active_games_reset) > 0,
    }


@app.post('/api/admin/users/game-stats')
def admin_update_user_game_stats(payload: AdminUserGameStatsIn):
    _require_admin(payload.init_data)
    db.refresh()
    user_data = db.users.get(str(int(payload.user_id)))
    if not isinstance(user_data, dict):
        _error(404, 'Пользователь не найден')

    allowed_fields = {'games_played', 'wins', 'losses', 'total_bet', 'total_won', 'biggest_win'}
    unknown_fields = set(payload.stats) - allowed_fields
    if unknown_fields:
        _error(400, 'Переданы неизвестные показатели игры')

    games = user_data.setdefault('games', {})
    if not isinstance(games, dict):
        games = {}
        user_data['games'] = games
    stats = games.get(payload.game)
    if not isinstance(stats, dict):
        stats = {}
        games[payload.game] = stats

    updated = dict(stats)
    integer_fields = {'games_played', 'wins', 'losses'}
    for field, raw_value in payload.stats.items():
        value = _as_float(raw_value)
        if value is None or value < 0:
            _error(400, 'Показатели должны быть неотрицательными числами')
        if field in integer_fields and not value.is_integer():
            _error(400, 'Количество игр и исходов должно быть целым числом')
        updated[field] = int(value) if field in integer_fields else value

    games_played = int(updated.get('games_played', 0) or 0)
    wins = int(updated.get('wins', 0) or 0)
    losses = int(updated.get('losses', 0) or 0)
    if wins + losses > games_played:
        _error(400, 'Побед и поражений не может быть больше, чем сыграно игр')

    games[payload.game] = updated
    db.save_data()
    return {'ok': True, 'user_id': int(payload.user_id), 'game': payload.game, 'stats': updated}


@app.post('/api/admin/users/balance-adjustment')
def admin_adjust_user_balance(payload: AdminBalanceAdjustmentIn):
    admin_user, _ = _require_admin(payload.init_data)
    db.refresh()
    user_data = db.users.get(str(int(payload.user_id)))
    if not isinstance(user_data, dict):
        _error(404, 'Пользователь не найден')

    amount = _as_float(payload.amount)
    if amount is None or amount == 0 or round(amount, 4) != amount:
        _error(400, 'Введите ненулевую сумму не более чем с четырьмя знаками после запятой')
    field = 'balance_stars' if payload.currency == 'stars' else 'balance_ton'
    with _BALANCE_LOCK:
        before = _as_float(user_data.get(field, 0)) or 0.0
        after = round(before + amount, 4)
        if after < 0:
            _error(400, 'На балансе недостаточно средств для такого списания')

        user_data[field] = after
        db.save_data()
    after = float(db.users[str(int(payload.user_id))].get(field, 0) or 0)
    audit_path = BASE_DIR / 'data' / 'admin_balance_audit.json'
    try:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        entries = json.loads(audit_path.read_text(encoding='utf-8')) if audit_path.exists() else []
        desktop_actor = bool(DESKTOP_ADMIN_KEY_CONTEXT.get())
        entries.append({
            'user_id': int(payload.user_id),
            'actor_id': None if desktop_actor else int(admin_user.id),
            'actor': 'desktop_admin_key' if desktop_actor else 'telegram_admin',
            'currency': payload.currency,
            'amount': amount,
            'before': before,
            'after': after,
            'reason': payload.reason.strip(),
            'created_at': datetime.now().isoformat(timespec='seconds'),
        })
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=audit_path.parent, delete=False) as tmp:
            json.dump(entries[-5000:], tmp, ensure_ascii=False, indent=2)
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, audit_path)
    except OSError as exc:
        _error(500, f'Баланс обновлён, но не удалось записать журнал: {exc}')
    return {'ok': True, 'user_id': int(payload.user_id), 'currency': payload.currency, 'before': before, 'after': after}


@app.post('/api/admin/settings')
def admin_update_bot_settings(payload: AdminBotSettingsIn):
    _require_admin(payload.init_data)
    try:
        settings = save_managed_settings(payload.settings)
    except ValueError as exc:
        _error(400, str(exc))
    return {'ok': True, 'settings': settings, 'applied': 'runtime'}


@app.post('/api/admin/broadcast/upload-image')
async def admin_broadcast_upload_image(
    image: UploadFile = File(...),
    init_data: str = Form('desktop'),
):
    _require_admin(init_data)
    contents = await image.read()
    if not contents:
        _error(400, 'Файл пустой')

    filename = image.filename or 'broadcast.jpg'
    file_id = None
    if ADMIN_IDS:
        try:
            admin_id = int(ADMIN_IDS[0])
            res = send_photo_bytes(admin_id, contents, filename, caption='[Тест загрузки фото для рассылки]')
            photos = res.get('result', {}).get('photo', [])
            if photos:
                file_id = photos[-1].get('file_id')
        except Exception as exc:
            logger.warning(f"Failed to obtain file_id for uploaded photo: {exc}")

    return {
        'ok': True,
        'file_id': file_id,
        'filename': filename,
        'size': len(contents),
    }


def _resolve_image_bytes_from_url(url: str) -> tuple[bytes | None, str]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    }
    try:
        r = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
        if not r.ok:
            return None, 'broadcast.jpg'

        content_type = r.headers.get('Content-Type', '').lower()

        # If it is an HTML webpage (e.g. Pinterest pin, Imgur, Telegra.ph), extract the real image URL!
        if 'text/html' in content_type or (len(r.text) > 500 and ('<html' in r.text.lower() or '<meta' in r.text.lower())):
            html_text = r.text
            # 1. Search for Pinterest direct originals / 736x image
            pinimg_matches = re.findall(r'https://i\.pinimg\.com/(?:originals|736x|564x|474x)/[a-zA-Z0-9/_.\-]+', html_text)
            if pinimg_matches:
                origs = [x for x in pinimg_matches if 'originals' in x or '736x' in x]
                target_img_url = origs[0] if origs else pinimg_matches[0]
                img_r = requests.get(target_img_url, headers={'User-Agent': headers['User-Agent']}, timeout=10)
                if img_r.ok and len(img_r.content) > 100:
                    ext = '.png' if '.png' in target_img_url.lower() else '.jpg'
                    return img_r.content, f'photo{ext}'

            # 2. General OpenGraph or Twitter Card image
            og_match = re.search(r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
            if not og_match:
                og_match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\']', html_text, re.IGNORECASE)
            if og_match:
                real_img_url = og_match.group(1).replace('&amp;', '&')
                img_r = requests.get(real_img_url, headers={'User-Agent': headers['User-Agent']}, timeout=10)
                if img_r.ok and len(img_r.content) > 100:
                    ct = img_r.headers.get('Content-Type', '').lower()
                    ext = '.png' if 'png' in ct else ('.webp' if 'webp' in ct else '.jpg')
                    return img_r.content, f'photo{ext}'

            return None, 'broadcast.jpg'

        # If it is direct image bytes:
        if 'image' in content_type or r.content.startswith(b'\xff\xd8') or r.content.startswith(b'\x89PNG') or r.content.startswith(b'RIFF'):
            ext = '.png' if 'png' in content_type else ('.webp' if 'webp' in content_type else '.jpg')
            return r.content, f'photo{ext}'

    except Exception as exc:
        logger.warning(f"Error resolving image from URL {url}: {exc}")

    return None, 'broadcast.jpg'


@app.post('/api/admin/broadcast')
def admin_broadcast(payload: AdminBroadcastIn):
    _require_admin(payload.init_data)
    text = (payload.text or '').strip()
    has_image = bool(payload.image_url or payload.image_base64)
    if len(text) < 1 and not has_image:
        _error(400, 'Текст рассылки слишком короткий')

    db.refresh()
    sent = 0
    failed = 0

    reply_markup = None
    btn_url = (payload.button_url or '').strip()
    btn_text = (payload.button_text or '').strip()
    if btn_url:
        if not btn_text:
            btn_text = 'Перейти'
        if not (btn_url.startswith('https://') or btn_url.startswith('http://') or btn_url.startswith('tg://')):
            btn_url = f'https://{btn_url}'
        reply_markup = {
            "inline_keyboard": [
                [{"text": btn_text, "url": btn_url}]
            ]
        }

    # Prepare photo source
    photo_bytes: bytes | None = None
    photo_filename: str = payload.image_filename or 'broadcast.jpg'
    telegram_file_id: str | None = None
    fallback_url: str | None = None

    if payload.image_base64:
        try:
            raw_b64 = payload.image_base64.strip()
            if ',' in raw_b64:
                raw_b64 = raw_b64.split(',', 1)[1]
            photo_bytes = base64.b64decode(raw_b64)
        except Exception as exc:
            logger.warning(f"Failed to decode broadcast image_base64: {exc}")

    elif payload.image_url:
        img_val = payload.image_url.strip()
        if img_val.startswith('data:image'):
            try:
                raw_b64 = img_val.split(',', 1)[1] if ',' in img_val else img_val
                photo_bytes = base64.b64decode(raw_b64)
            except Exception as exc:
                logger.warning(f"Failed to decode data URL: {exc}")
        elif os.path.isfile(img_val):
            try:
                with open(img_val, 'rb') as f:
                    photo_bytes = f.read()
                photo_filename = os.path.basename(img_val)
            except Exception as exc:
                logger.warning(f"Failed to read local file {img_val}: {exc}")
        elif img_val.startswith('http://') or img_val.startswith('https://'):
            fallback_url = img_val
            resolved_bytes, resolved_name = _resolve_image_bytes_from_url(img_val)
            if resolved_bytes:
                photo_bytes = resolved_bytes
                photo_filename = resolved_name
        else:
            # Assumed to be Telegram file_id
            telegram_file_id = img_val

    # Determine target recipients
    recipients: list[int] = []
    if payload.target == "test":
        for a in ADMIN_IDS:
            try:
                recipients.append(int(a))
            except Exception:
                pass
    else:
        for uid_str, user_data in db.users.items():
            if payload.target == "depositors":
                if float(user_data.get('total_stars', 0)) <= 0 and float(user_data.get('total_ton', 0)) <= 0:
                    continue
            try:
                recipients.append(int(uid_str))
            except Exception:
                pass

    if not recipients:
        return {'ok': True, 'sent': 0, 'failed': 0, 'message': 'Нет получателей для рассылки'}

    for uid in recipients:
        try:
            if photo_bytes or telegram_file_id or fallback_url:
                # 1. If we already have a cached Telegram file_id, use it
                if telegram_file_id:
                    try:
                        send_photo_url(uid, telegram_file_id, text, reply_markup)
                        sent += 1
                        time.sleep(0.04)
                        continue
                    except Exception as exc:
                        logger.warning(f"send_photo_url with file_id failed for {uid}: {exc}")

                # 2. If we have photo_bytes and need to get file_id from the first send
                if photo_bytes:
                    try:
                        res = send_photo_bytes(uid, photo_bytes, photo_filename, text, reply_markup)
                        photos = res.get('result', {}).get('photo', [])
                        if photos:
                            telegram_file_id = photos[-1].get('file_id')
                        sent += 1
                        time.sleep(0.04)
                        continue
                    except Exception as exc:
                        logger.warning(f"send_photo_bytes failed for {uid}: {exc}")

                # 3. If we have fallback_url
                if fallback_url:
                    try:
                        res = send_photo_url(uid, fallback_url, text, reply_markup)
                        photos = res.get('result', {}).get('photo', [])
                        if photos:
                            telegram_file_id = photos[-1].get('file_id')
                        sent += 1
                        time.sleep(0.04)
                        continue
                    except Exception as exc:
                        logger.warning(f"send_photo_url with url failed for {uid}: {exc}")

                # 4. Fallback to text message if photo sending failed
                send_message(uid, text, reply_markup)
                sent += 1
            else:
                send_message(uid, text, reply_markup)
                sent += 1
            time.sleep(0.04)
        except Exception as exc:
            logger.warning(f"Broadcast completely failed for user {uid}: {exc}")
            failed += 1

    return {'ok': True, 'sent': sent, 'failed': failed}


@app.get('/api/admin/users')
def admin_get_users(init_data: str = 'desktop'):
    _require_admin(init_data)
    db.refresh()
    users_list = []
    for uid_str, user_data in db.users.items():
        uid = int(uid_str)
        is_user_banned = _is_user_banned(uid)
        users_list.append({
            'id': uid,
            'user_id': uid,
            'username': user_data.get('username', 'unknown'),
            'balance_stars': float(user_data.get('balance_stars', user_data.get('total_stars', 0)) or 0),
            'balance_ton': float(user_data.get('balance_ton', 0) or 0),
            'total_deposited': float(user_data.get('total_stars', 0) or 0),
            'total_stars': float(user_data.get('total_stars', 0) or 0),
            'inventory_size': len(user_data.get('miniapp_inventory', [])),
            'is_banned': is_user_banned,
            'banned': is_user_banned,
        })
    return {'ok': True, 'users': users_list}


@app.get('/api/admin/transactions')
def admin_get_transactions(init_data: str = 'desktop', status: str = 'pending'):
    _require_admin(init_data)
    db.refresh()
    allowed_statuses = {'pending', 'confirmed', 'rejected', 'all'}
    if status not in allowed_statuses:
        _error(400, 'Недопустимый статус транзакций')

    transactions = db.transactions if status == 'all' else [
        item for item in db.transactions if item.get('status') == status
    ]
    safe_fields = {
        'id', 'type', 'user_id', 'status', 'date', 'source', 'stars', 'ton_amount',
        'amount', 'months', 'payment_method', 'target_username', 'recipient_user_id',
        'gift_id', 'gift_label', 'stars_value', 'fee_percent', 'delivered_to_balance',
    }
    return {
        'ok': True,
        'transactions': [
            {
                **{key: value for key, value in item.items() if key in safe_fields},
                'has_proof': bool(item.get('proof_file_id')),
            }
            for item in reversed(transactions[-500:])
        ],
    }


@app.get('/api/admin/transactions/{transaction_id}/proof')
def admin_get_transaction_proof(transaction_id: int, init_data: str = 'desktop'):
    _require_admin(init_data)
    db.refresh()
    transaction = next(
        (item for item in db.transactions if int(item.get('id', 0) or 0) == transaction_id),
        None,
    )
    if not transaction:
        _error(404, 'Транзакция не найдена')
    file_id = transaction.get('proof_file_id')
    if not file_id:
        _error(404, 'Для этой заявки чек не сохранён')
    try:
        content, content_type = download_telegram_file(str(file_id))
    except Exception:
        _error(502, 'Не удалось загрузить чек из Telegram')
    if not content_type.startswith('image/'):
        _error(415, 'Telegram вернул файл, который не является изображением')
    return Response(
        content=content,
        media_type=content_type,
        headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'},
    )


def _refund_held_transaction(transaction: dict, user_data: dict | None = None) -> None:
    if not transaction.get('held_at_creation'):
        return
    user_id = int(transaction.get('user_id', 0) or 0)
    if user_data is None:
        user_data = db.users.get(str(user_id))
    if not isinstance(user_data, dict):
        return
    ttype = transaction.get('type')
    if ttype == 'withdraw':
        stars = int(transaction.get('stars', 0) or 0)
        if stars > 0:
            add_star_balance(user_data, stars)
    elif ttype == 'withdraw_ton':
        ton_amount = float(transaction.get('ton_amount', 0) or 0)
        if ton_amount > 0:
            add_ton_balance(user_data, ton_amount)
    elif ttype == 'gift_withdraw':
        gift_data = transaction.get('gift_data')
        if isinstance(gift_data, dict):
            inv = user_data.setdefault('miniapp_inventory', [])
            if not isinstance(inv, list):
                inv = []
                user_data['miniapp_inventory'] = inv
            gid = str(gift_data.get('id') or '')
            if not any(str(x.get('id') or '') == gid for x in inv if isinstance(x, dict)):
                inv.insert(0, gift_data)
    transaction['held_at_creation'] = False


@app.post('/api/admin/transactions/decision')
def admin_decide_transaction(payload: AdminTransactionDecisionIn):
    _require_admin(payload.init_data)
    db.refresh()
    transaction = next(
        (item for item in db.transactions if int(item.get('id', 0) or 0) == payload.transaction_id),
        None,
    )
    if not transaction:
        _error(404, 'Транзакция не найдена')
    if transaction.get('status') != 'pending':
        _error(409, 'Эта транзакция уже обработана')

    user_id = int(transaction.get('user_id', 0) or 0)
    user_data = db.users.get(str(user_id))
    transaction_type = transaction.get('type')
    notification = None

    if payload.decision == 'reject':
        transaction['status'] = 'rejected'
        _refund_held_transaction(transaction, user_data)
        notification = '❌ Заявка отклонена администратором. Если это ошибка, обратитесь в поддержку.'
    elif transaction_type in {'withdraw', 'withdraw_ton', 'gift_withdraw'}:
        if not isinstance(user_data, dict):
            _error(404, 'Пользователь не найден')
        if transaction_type == 'withdraw_ton':
            amount = float(transaction.get('ton_amount', 0) or 0)
            if not transaction.get('held_at_creation'):
                balance = get_numeric_ton_balance(user_data)
                if amount <= 0 or amount > balance:
                    _error(400, 'Недостаточно TON у пользователя для подтверждения вывода')
                sub_ton_balance(user_data, amount)
            notification = f'✅ Вывод подтверждён. Списано {format_stars(amount)} TON.'
        elif transaction_type == 'withdraw':
            amount = int(transaction.get('stars', 0) or 0)
            if not transaction.get('held_at_creation'):
                if amount <= 0 or amount > get_numeric_balance(user_data):
                    _error(400, 'Недостаточно Stars у пользователя для подтверждения вывода')
                sub_star_balance(user_data, amount)
            notification = f'✅ Вывод подтверждён. Списано {amount} ⭐.'
        else:
            if not transaction.get('held_at_creation'):
                gift_id = str(transaction.get('gift_id') or '')
                inventory = user_data.setdefault('miniapp_inventory', [])
                if not gift_id or not isinstance(inventory, list) or not any(
                    str(item.get('id') or '') == gift_id for item in inventory if isinstance(item, dict)
                ):
                    _error(404, 'Подарок для вывода не найден в инвентаре')
                user_data['miniapp_inventory'] = [
                    item for item in inventory
                    if not isinstance(item, dict) or str(item.get('id') or '') != gift_id
                ]
            notification = f"✅ Вывод подарка подтверждён: {transaction.get('gift_label') or 'подарок'}."
        transaction['status'] = 'confirmed'
    elif transaction_type in {'stars', 'ton_topup', 'premium'}:
        if not isinstance(user_data, dict):
            _error(404, 'Пользователь не найден')
        if transaction_type == 'stars':
            stars = int(transaction.get('stars', 0) or 0)
            if stars <= 0:
                _error(400, 'В заказе указано некорректное количество Stars')
            target_username = transaction.get('target_username')
            recipient_id = transaction.get('recipient_user_id')
            if not target_username:
                add_star_balance(user_data, stars)
                transaction['delivered_to_balance'] = True
                db.save_data()
                notification = f'✅ Оплата подтверждена. Начислено {stars} ⭐.'
            elif recipient_id:
                recipient_data = register_user_if_needed(int(recipient_id))
                add_star_balance(recipient_data, stars)
                transaction['delivered_to_balance'] = True
                db.save_data()
                notification = f'✅ Оплата подтверждена. Для {target_username} начислено {stars} ⭐.'
                try:
                    send_message(int(recipient_id), f'🎁 Вам купили {stars} ⭐.')
                except Exception:
                    pass
            else:
                transaction['delivered_to_balance'] = False
                db.save_data()
                notification = f'✅ Оплата подтверждена. Заказ для {target_username} требует ручной выдачи.'
            if not transaction.get('referral_rewarded'):
                transaction['referral_rewarded'] = True
                reward_referrer_for_purchase(transaction['user_id'], 'stars', stars=stars)
                db.save_data()
        elif transaction_type == 'ton_topup':
            amount = float(transaction.get('ton_amount', 0) or 0)
            if amount <= 0:
                _error(400, 'В заявке указано некорректное количество TON')
            user_data['balance_ton'] = get_numeric_ton_balance(user_data) + amount
            db.save_data()
            notification = f'✅ Оплата подтверждена. Начислено {format_stars(amount)} TON.'
        else:
            months = int(transaction.get('months', 0) or 0)
            db.save_data()
            if not transaction.get('referral_rewarded'):
                transaction['referral_rewarded'] = True
                reward_referrer_for_purchase(transaction['user_id'], 'premium', months=months)
                db.save_data()
            notification = (
                f'✅ Premium на {months} мес. подтверждён. Свяжитесь с {PREMIUM_SELLER_USERNAME}.'
                if months == 1 else '✅ Оплата Premium подтверждена. Ожидайте выдачу подписки.'
            )
        transaction['status'] = 'confirmed'
    else:
        _error(400, 'Этот тип транзакции нельзя обработать из desktop-админки')

    db.save_data()
    if notification:
        try:
            send_message(user_id, notification)
        except Exception:
            pass
    return {'ok': True, 'transaction': transaction}


@app.post('/api/admin/transactions/reject-all-pending')
def admin_reject_all_pending_transactions(request: Request, payload: AdminRejectAllPendingIn | None = None, init_data: str | None = None):
    token = _extract_init_data(request, (payload.init_data if payload else None) or init_data)
    _require_admin(token, request=request)
    db.refresh()
    pending_transactions = [
        item for item in db.transactions
        if item.get('status') == 'pending'
    ]
    rejected_count = 0
    for transaction in pending_transactions:
        transaction['status'] = 'rejected'
        was_held = bool(transaction.get('held_at_creation'))
        _refund_held_transaction(transaction)
        rejected_count += 1
        user_id = int(transaction.get('user_id', 0) or 0)
        if user_id:
            try:
                if was_held:
                    msg = '❌ Ваша заявка на вывод отклонена администратором. Средства возвращены на ваш баланс.'
                else:
                    msg = '❌ Ваша заявка отклонена администратором. Если вы считаете, что произошла ошибка — обратитесь в поддержку.'
                send_message(
                    user_id,
                    msg,
                )
            except Exception:
                pass

    if rejected_count > 0:
        db.save_data()

    return {
        'ok': True,
        'rejected_count': rejected_count,
        'message': f'Отклонено заявок: {rejected_count}',
    }


@app.post('/api/admin/users/ban')
def admin_ban_user(payload: AdminUserBanIn, init_data: str | None = None):
    _require_admin(payload.init_data or init_data)
    db.refresh()
    uid = payload.user_id
    if payload.ban:
        if not _is_user_banned(uid):
            db.restricted_users.append(uid)
    else:
        db.restricted_users = [
            item for item in db.restricted_users
            if not (
                (isinstance(item, dict) and (item.get('user_id') == uid or str(item.get('user_id')) == str(uid)))
                or item == uid
                or str(item) == str(uid)
            )
        ]
    db.save_data()
    return {'ok': True}


@app.get('/api/admin/users/{user_id}/inventory')
def admin_get_user_inventory(user_id: int, init_data: str = 'desktop'):
    _require_admin(init_data)
    db.refresh()
    user_data = db.users.get(str(user_id), {})
    return {'ok': True, 'inventory': user_data.get('miniapp_inventory', [])}


@app.post('/api/admin/users/inventory/add')
def admin_add_user_inventory(payload: AdminUserInventoryAddIn):
    _require_admin(payload.init_data)
    db.refresh()
    user_data = db.users.get(str(int(payload.user_id)))
    if not isinstance(user_data, dict):
        _error(404, 'Пользователь не найден')
    inv = user_data.setdefault('miniapp_inventory', [])
    if not isinstance(inv, list):
        inv = []
        user_data['miniapp_inventory'] = inv
    item = {
        'id': str(uuid4()),
        'model': payload.model.strip(),
        'name': payload.name.strip() or payload.model.strip(),
        'image': payload.image.strip() if payload.image else '',
        'value': max(1, int(payload.value)),
        'date': datetime.now().strftime('%d.%m.%Y %H:%M'),
    }
    inv.append(item)
    db.save_data()
    return {'ok': True, 'item': item, 'inventory': inv}


@app.post('/api/admin/users/inventory/remove')
def admin_remove_user_inventory(payload: AdminUserInventoryRemoveIn):
    _require_admin(payload.init_data)
    db.refresh()
    user_data = db.users.get(str(int(payload.user_id)))
    if not isinstance(user_data, dict):
        _error(404, 'Пользователь не найден')
    inv = user_data.get('miniapp_inventory', [])
    if isinstance(inv, list):
        user_data['miniapp_inventory'] = [
            x for x in inv if str(x.get('id') or '') != str(payload.item_id)
        ]
        db.save_data()
    return {'ok': True, 'inventory': user_data.get('miniapp_inventory', [])}


@app.post('/api/admin/users/send-message')
def admin_send_message_to_user(payload: AdminSendMessageIn):
    _require_admin(payload.init_data)
    text = (payload.text or '').strip()
    if not text:
        _error(400, 'Текст сообщения не может быть пустым')
    try:
        send_message(payload.user_id, text)
    except Exception as exc:
        _error(500, f'Не удалось отправить сообщение: {exc}')
    return {'ok': True, 'message': 'Сообщение успешно отправлено'}


@app.post('/api/admin/promocodes/delete')
def admin_delete_promocode(payload: AdminPromocodeDeleteIn, init_data: str | None = None):
    _require_admin(payload.init_data or init_data)
    db.refresh()
    initial_len = len(db.promocodes)
    db.promocodes = [p for p in db.promocodes if p.get('code') != payload.code]
    if len(db.promocodes) < initial_len:
        db.save_data()
    return {'ok': True}


@app.get('/api/admin/audit-logs')
def admin_audit_logs(init_data: str = 'desktop'):
    _require_admin(init_data)
    audit_file = Path(BASE_DIR) / 'data' / 'admin_balance_audit.json'
    if audit_file.exists():
        try:
            return {'ok': True, 'logs': json.loads(audit_file.read_text(encoding='utf-8'))}
        except Exception:
            pass
    return {'ok': True, 'logs': []}


@app.get('/api/admin/backup')
def admin_backup(init_data: str = 'desktop'):
    _require_admin(init_data)
    data_dir = Path(BASE_DIR) / 'data'
    temp_dir = tempfile.mkdtemp()
    zip_base = Path(temp_dir) / f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    archive_path = shutil.make_archive(str(zip_base), 'zip', data_dir)
    return FileResponse(archive_path, media_type='application/zip', filename=Path(archive_path).name)


@app.post('/api/admin/clear-game-stats')
def admin_clear_game_stats(request: Request, init_data: str | None = None):
    token = _extract_init_data(request, init_data)
    _require_admin(token, request=request)
    db.refresh()
    db.game_stats = {
        'mines': {'games_played': 0, 'wins': 0, 'losses': 0, 'total_bet': 0, 'total_paid_out': 0, 'net_profit': 0},
        'crash': {'games_played': 0, 'wins': 0, 'losses': 0, 'total_bet': 0, 'total_paid_out': 0, 'net_profit': 0, 'last_round_number': 0},
        'roulette': {'games_played': 0, 'wins': 0, 'losses': 0, 'total_bet': 0, 'total_paid_out': 0, 'net_profit': 0},
        'coin': {'games_played': 0, 'wins': 0, 'losses': 0, 'total_bet': 0, 'total_paid_out': 0, 'net_profit': 0},
        'plinko': {'games_played': 0, 'wins': 0, 'losses': 0, 'total_bet': 0, 'total_paid_out': 0, 'net_profit': 0},
        'tower': {'games_played': 0, 'wins': 0, 'losses': 0, 'total_bet': 0, 'total_paid_out': 0, 'net_profit': 0},
        'blackjack': {'games_played': 0, 'wins': 0, 'losses': 0, 'total_bet': 0, 'total_paid_out': 0, 'net_profit': 0},
    }
    db.save_data()
    return {'ok': True, 'summary': _build_admin_summary()}


@app.get('/api/reviews/recent')
def recent_reviews(request: Request, init_data: str | None = None, limit: int = 5):
    token = _extract_init_data(request, init_data)
    _require_user(token)
    return {'ok': True, 'reviews': _serialize_reviews(limit)}


@app.post('/api/reviews/create')
def create_review(request: Request, payload: ReviewIn):
    token = _extract_init_data(request, payload.init_data)
    tg_user, user_data = _require_user(token, allow_demo=False)
    if tg_user.id == 0:
        _error(403, 'Действие недоступно в демо-режиме')
    _check_rate_limit(request, 'reviews_create', max_requests=3, window_seconds=60, actor_id=tg_user.id)
    if int(user_data.get('total_stars', 0) or 0) <= 0 and tg_user.id not in ADMIN_IDS:
        _error(403, 'Оставлять отзывы могут пользователи с покупками')

    # Strict sanitization against Stored XSS: strip HTML tags and escape HTML entities
    cleaned_text = re.sub(r'<[^>]*>', '', payload.text).strip()
    safe_text = html.escape(cleaned_text, quote=True)
    if len(safe_text) < 3:
        _error(400, 'Текст отзыва слишком короткий')
    if len(safe_text) > 500:
        safe_text = safe_text[:500]

    entry = {
        'user_id': tg_user.id,
        'username': html.escape(str(tg_user.username or 'unknown'), quote=True),
        'text': safe_text,
        'date': datetime.now().strftime('%d.%m.%Y'),
    }
    db.reviews.append(entry)
    if str(tg_user.id) in db.users:
        db.users[str(tg_user.id)]['has_review'] = True
    db.save_data()
    try:
        safe_name = html.escape(tg_user.first_name or 'Пользователь', quote=False)
        send_message(REVIEWS_CHANNEL, f"💬 Новый отзыв:\n\n{safe_text}\n\n👤 {safe_name}")
    except Exception:
        pass
    return {'ok': True, 'message': 'Спасибо за отзыв', 'reviews': _serialize_reviews(5)}


@app.get('/api/admin/reviews')
def admin_get_reviews(request: Request, init_data: str | None = 'desktop'):
    token = _extract_init_data(request, init_data)
    _require_admin(token, request=request)
    db.refresh()
    items = []
    for idx, r in enumerate(db.reviews):
        item = dict(r)
        item['id'] = idx
        items.append(item)
    return {'ok': True, 'reviews': items}


@app.post('/api/admin/reviews/delete')
def admin_delete_review(payload: AdminReviewDeleteIn):
    _require_admin(payload.init_data)
    db.refresh()
    deleted = False
    if payload.index is not None and 0 <= payload.index < len(db.reviews):
        db.reviews.pop(payload.index)
        deleted = True
    elif payload.text:
        orig_len = len(db.reviews)
        db.reviews = [r for r in db.reviews if r.get('text') != payload.text]
        deleted = len(db.reviews) < orig_len
    elif payload.user_id:
        orig_len = len(db.reviews)
        db.reviews = [r for r in db.reviews if int(r.get('user_id', 0) or 0) != int(payload.user_id)]
        deleted = len(db.reviews) < orig_len
    if deleted:
        db.save_data()
    return {'ok': True, 'deleted': deleted}


@app.post('/api/admin/clear-transactions')
def admin_clear_transactions(payload: AdminClearTransactionsIn):
    _require_admin(payload.init_data)
    db.refresh()
    filter_val = (payload.status_filter or '').strip().lower()
    if filter_val == 'all':
        db.transactions = []
        db.transaction_id_counter = 1
    elif filter_val in {'confirmed', 'rejected'}:
        db.transactions = [t for t in db.transactions if t.get('status') != filter_val]
    else:
        db.transactions = [t for t in db.transactions if t.get('status') == 'pending']
    db.save_data()
    return {'ok': True, 'remaining_count': len(db.transactions)}


@app.post('/api/admin/restore-backup')
async def admin_restore_backup(
    request: Request,
    file: UploadFile = File(...),
    init_data: str = Form('desktop')
):
    token = _extract_init_data(request, init_data)
    _require_admin(token, request=request)
    if not (file.filename and file.filename.lower().endswith('.zip')):
        _error(400, 'Файл должен быть ZIP архивом')
    data_dir = (BASE_DIR / 'data').resolve()
    temp_dir = tempfile.mkdtemp()
    zip_path = Path(temp_dir) / 'restore.zip'
    try:
        content = await file.read()
        with open(zip_path, 'wb') as f:
            f.write(content)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.namelist():
                # Strictly prevent path traversal (including Windows drive letters and backslashes)
                if '\\' in member or member.startswith('/') or '..' in member:
                    _error(400, 'Недопустимый архив (traversal detected)')
                target_path = (data_dir / member).resolve()
                if not (target_path == data_dir or data_dir in target_path.parents):
                    _error(400, 'Недопустимый путь файла в архиве')
            zip_ref.extractall(data_dir)
    except HTTPException:
        raise
    except Exception as exc:
        _error(400, f'Ошибка при распаковке архива: {exc}')
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    db.load_data()
    return {'ok': True, 'message': 'База данных успешно восстановлена'}


@app.get('/api/admin/system-status')
def admin_system_status(init_data: str = 'desktop'):
    _require_admin(init_data)
    db.refresh()
    data_dir = BASE_DIR / 'data'
    db_files = {}
    if data_dir.exists():
        for p in data_dir.glob('*.json'):
            try:
                db_files[p.name] = round(p.stat().st_size / 1024, 2)
            except Exception:
                pass
    return {
        'ok': True,
        'status': 'online',
        'server_time': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
        'bot_username': BOT_USERNAME,
        'total_users': len(db.users),
        'total_transactions': len(db.transactions),
        'pending_transactions': len([t for t in db.transactions if t.get('status') == 'pending']),
        'total_reviews': len(db.reviews),
        'total_suggestions': len(db.suggestions),
        'total_promocodes': len(db.promocodes),
        'total_banned': len(db.restricted_users),
        'total_tournaments': len(getattr(db, 'tournaments', [])),
        'db_files_kb': db_files,
    }


# ─────────────────────────────────────────────────────────────
# Tournaments Endpoints
# ─────────────────────────────────────────────────────────────

@app.get('/api/tournaments')
def get_tournaments_endpoint(request: Request, init_data: str | None = None):
    db.refresh()
    user_id = None
    token = _extract_init_data(request, init_data) or 'demo'
    try:
        tg_user, _ = _require_user(token)
        user_id = tg_user.id
    except Exception:
        pass
    tournaments = get_all_tournaments_summary(requesting_user_id=user_id)
    return {'ok': True, 'tournaments': tournaments}


@app.get('/api/tournaments/{tournament_id}')
def get_tournament_details_endpoint(request: Request, tournament_id: str, init_data: str | None = None):
    db.refresh()
    user_id = None
    token = _extract_init_data(request, init_data) or 'demo'
    try:
        tg_user, _ = _require_user(token)
        user_id = tg_user.id
    except Exception:
        pass
    result = compute_tournament_leaderboard(tournament_id, requesting_user_id=user_id)
    if not result.get('ok'):
        _error(404, result.get('error', 'Турнир не найден'))
    return result


@app.get('/api/admin/tournaments')
def admin_get_tournaments_endpoint(request: Request, init_data: str | None = None):
    token = _extract_init_data(request, init_data)
    _require_admin(token, request=request)
    db.refresh()
    tournaments = get_all_tournaments_summary()
    return {'ok': True, 'tournaments': tournaments}


@app.get('/api/admin/tournaments/nft-catalog')
def admin_tournament_nft_catalog(init_data: str = 'desktop'):
    try:
        _require_admin(init_data)
    except Exception:
        pass
    catalog = _get_nft_shop_catalog()
    return {'ok': True, 'catalog': catalog}


@app.post('/api/admin/tournaments/create')
def admin_create_tournament_endpoint(payload: AdminTournamentCreateIn):
    _require_admin(payload.init_data)
    if not payload.title.strip():
        _error(400, 'Название турнира не может быть пустым')
    tournament = create_tournament(
        title=payload.title,
        description=payload.description,
        metric=payload.metric,
        games=payload.games,
        start_time=payload.start_time,
        end_time=payload.end_time,
        prize_pool=payload.prize_pool,
        prizes=payload.prizes,
        min_threshold=payload.min_threshold,
    )
    return {'ok': True, 'tournament': tournament}


@app.post('/api/admin/tournaments/end')
def admin_end_tournament_endpoint(payload: AdminTournamentActionIn):
    _require_admin(payload.init_data)
    res = end_tournament(payload.tournament_id)
    if not res.get('ok'):
        _error(404, res.get('error', 'Не удалось завершить турнир'))
    return res


@app.post('/api/admin/tournaments/distribute-prizes')
def admin_distribute_prizes_endpoint(payload: AdminTournamentActionIn):
    _require_admin(payload.init_data)
    res = distribute_tournament_prizes(payload.tournament_id)
    if not res.get('ok'):
        _error(400, res.get('error', 'Ошибка при начислении призов'))
    return res


@app.post('/api/admin/tournaments/delete')
def admin_delete_tournament_endpoint(payload: AdminTournamentActionIn):
    _require_admin(payload.init_data)
    res = delete_tournament(payload.tournament_id)
    if not res.get('ok'):
        _error(404, res.get('error', 'Не удалось удалить турнир'))
    return res


class ShiftBaseModel(BaseModel):
    @model_validator(mode='before')
    @classmethod
    def _parse_raw_if_string(cls, data):
        if isinstance(data, (str, bytes)):
            try:
                return json.loads(data)
            except Exception:
                pass
        return data


class AdminShiftStartIn(ShiftBaseModel):
    init_data: str = 'desktop'
    worker_id: str
    actor_name: str | None = None


class AdminShiftTransferIn(ShiftBaseModel):
    init_data: str = 'desktop'
    worker_id: str
    actor_name: str | None = None


class AdminShiftActionIn(ShiftBaseModel):
    init_data: str = 'desktop'
    actor_name: str | None = None


class AdminWorkerIn(ShiftBaseModel):
    init_data: str = 'desktop'
    id: str | None = None
    name: str
    telegram_id: int | str | None = None
    username: str = ''
    mono_card: str = ''
    ton_address: str = ''
    notes: str = ''
    is_active: bool = True


class AdminWorkerDeleteIn(ShiftBaseModel):
    init_data: str = 'desktop'
    worker_id: str


@app.get('/api/admin/shifts/state')
def admin_shifts_state(request: Request, init_data: str | None = 'desktop'):
    _require_admin(init_data, request=request)
    shifts_data = load_shifts_data()
    cur = shifts_data.get('current_shift')
    cur_metrics = compute_shift_metrics(cur.get('started_at')) if cur else None
    return {
        'ok': True,
        'current_shift': cur,
        'current_metrics': cur_metrics,
        'active_payment_details': get_active_payment_details(),
        'workers': shifts_data.get('workers', []),
        'recent_x_reports': shifts_data.get('x_reports', [])[-20:],
        'recent_history': shifts_data.get('shift_history', [])[-20:],
    }


@app.post('/api/admin/shifts/start')
def admin_shifts_start(request: Request, payload: AdminShiftStartIn):
    _require_admin(payload.init_data, request=request)
    try:
        shift = start_shift(payload.worker_id, actor_name=payload.actor_name or 'Admin')
        return {'ok': True, 'shift': shift}
    except Exception as e:
        _error(400, str(e))


@app.post('/api/admin/shifts/take')
def admin_shifts_take(request: Request, payload: AdminShiftStartIn):
    _require_admin(payload.init_data, request=request)
    try:
        shift = start_shift(payload.worker_id, actor_name=payload.actor_name or 'Admin')
        return {'ok': True, 'shift': shift}
    except Exception as e:
        _error(400, str(e))


@app.post('/api/admin/shifts/transfer')
def admin_shifts_transfer(request: Request, payload: AdminShiftTransferIn):
    _require_admin(payload.init_data, request=request)
    try:
        shift = transfer_shift(payload.worker_id, actor_name=payload.actor_name or 'Admin')
        return {'ok': True, 'shift': shift}
    except Exception as e:
        _error(400, str(e))


@app.post('/api/admin/shifts/end')
def admin_shifts_end(request: Request, payload: AdminShiftActionIn):
    _require_admin(payload.init_data, request=request)
    try:
        res = end_shift(actor_name=payload.actor_name or 'Admin')
        return {'ok': True, **res}
    except Exception as e:
        _error(400, str(e))


@app.post('/api/admin/shifts/x-report')
def admin_shifts_x_report(request: Request, payload: AdminShiftActionIn):
    _require_admin(payload.init_data, request=request)
    try:
        report = generate_x_report(actor_name=payload.actor_name or 'Admin', is_closing=False)
        return {'ok': True, 'report': report}
    except Exception as e:
        _error(400, str(e))


@app.get('/api/admin/shifts/history')
def admin_shifts_history(request: Request, init_data: str | None = 'desktop'):
    _require_admin(init_data, request=request)
    shifts_data = load_shifts_data()
    return {
        'ok': True,
        'x_reports': shifts_data.get('x_reports', []),
        'shift_history': shifts_data.get('shift_history', []),
    }


@app.post('/api/admin/shifts/workers/add')
def admin_shifts_add_worker(request: Request, payload: AdminWorkerIn):
    _require_admin(payload.init_data, request=request)
    w = add_worker(
        name=payload.name,
        mono_card=payload.mono_card,
        ton_address=payload.ton_address,
        telegram_id=payload.telegram_id,
        username=payload.username,
        notes=payload.notes,
        is_active=payload.is_active,
    )
    return {'ok': True, 'worker': w, 'workers': get_workers()}


@app.post('/api/admin/shifts/workers/update')
def admin_shifts_update_worker(request: Request, payload: AdminWorkerIn):
    _require_admin(payload.init_data, request=request)
    if not payload.id:
        _error(400, 'Не указан ID сменщика')
    w = update_worker(
        payload.id,
        name=payload.name,
        mono_card=payload.mono_card,
        ton_address=payload.ton_address,
        telegram_id=payload.telegram_id,
        username=payload.username,
        notes=payload.notes,
        is_active=payload.is_active,
    )
    if not w:
        _error(404, 'Сменщик не найден')
    return {'ok': True, 'worker': w, 'workers': get_workers()}


@app.post('/api/admin/shifts/workers/delete')
def admin_shifts_delete_worker(request: Request, payload: AdminWorkerDeleteIn):
    _require_admin(payload.init_data, request=request)
    ok = delete_worker(payload.worker_id)
    if not ok:
        _error(404, 'Сменщик не найден')
    return {'ok': True, 'workers': get_workers()}


@app.post('/api/games/roulette/play')
def play_roulette(payload: RouletteSpinIn):
    tg_user, user_data = _require_user(payload.init_data)
    amount = round(float(payload.amount), 1 if payload.currency == 'stars' else 4)
    limit_min = ROULETTE_MIN_BET
    limit_max = ROULETTE_MAX_BET
    if amount < limit_min or amount > limit_max:
        _error(400, f'Ставка должна быть от {format_stars(limit_min)} до {format_stars(limit_max)}')
    _sub_balance_checked(user_data, payload.currency, amount)

    result = _roll_roulette_color()
    win = payload.color == result
    if win and random.random() > _get_game_rtp_factor('roulette'):
        alternatives = ['red', 'white', 'green']
        alternatives = [c for c in alternatives if c != payload.color]
        result = random.choice(alternatives)
        win = False
    payout = round(amount * _roulette_multiplier(payload.color), 4 if payload.currency == 'ton' else 1) if win else 0
    if payout:
        _add_balance(user_data, payload.currency, payout)

    user_stats = _get_user_roulette_stats(user_data)
    global_stats = _get_global_roulette_stats()
    user_stats['games_played'] += 1
    user_stats['total_bet'] += amount
    global_stats['games_played'] += 1
    global_stats['total_bet'] += amount
    if win:
        user_stats['wins'] += 1
        user_stats['total_won'] += payout
        user_stats['biggest_win'] = max(float(user_stats.get('biggest_win', 0) or 0), payout)
        global_stats['wins'] += 1
        global_stats['total_paid_out'] += payout
    else:
        user_stats['losses'] += 1
        global_stats['losses'] += 1
    global_stats['net_profit'] = round(float(global_stats['total_bet']) - float(global_stats['total_paid_out']), 2)
    record_game_event(tg_user.id, 'roulette', amount, payout, payload.currency, won=win)
    db.save_data()
    return {
        'ok': True,
        'win': win,
        'result_color': result,
        'payout': payout,
        'profile': _serialize_profile(tg_user.id),
        'games': _serialize_game_hub(tg_user.id),
    }


@app.post('/api/games/mines/start')
def start_mines(payload: MinesStartIn):
    tg_user, user_data = _require_user(payload.init_data)
    amount = round(float(payload.amount), 1 if payload.currency == 'stars' else 4)
    min_bet = TON_MIN_BET if payload.currency == 'ton' else MIN_BET
    if amount < min_bet or amount > MAX_BET:
        _error(400, f'Ставка должна быть от {format_stars(min_bet)} до {format_stars(MAX_BET)}')
    if user_data.get('miniapp_mines'):
        _error(409, 'У вас уже есть активная игра в мины')
    _sub_balance_checked(user_data, payload.currency, amount)
    user_data['miniapp_mines'] = {
        'board': _generate_mines_board(),
        'bet': amount,
        'currency': payload.currency,
        'revealed': [],
        'safe_clicks': 0,
        'started_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
    }
    db.save_data()
    return {'ok': True, 'session': _serialize_mines_session(user_data['miniapp_mines']), 'profile': _serialize_profile(tg_user.id)}


@app.post('/api/games/mines/reveal')
def reveal_mines(payload: MinesRevealIn):
    tg_user, user_data = _require_user(payload.init_data)
    session = user_data.get('miniapp_mines')
    if not session:
        _error(404, 'Нет активной игры в мины')
    idx = int(payload.index)
    board = session['board']
    if idx < 0 or idx >= len(board):
        _error(400, 'Некорректная клетка')
    if idx in session.get('revealed', []):
        _error(409, 'Эта клетка уже открыта')

    session['revealed'].append(idx)
    user_stats = _get_user_mines_stats(user_data)
    global_stats = _get_global_mines_stats()

    if board[idx] == 1:
        user_stats['games_played'] += 1
        user_stats['losses'] += 1
        user_stats['total_bet'] += float(session['bet'])
        global_stats['games_played'] += 1
        global_stats['losses'] += 1
        global_stats['total_bet'] += float(session['bet'])
        global_stats['net_profit'] = round(float(global_stats['total_bet']) - float(global_stats['total_paid_out']), 2)
        mines_positions = [i for i, value in enumerate(board) if value == 1]
        user_data['miniapp_mines'] = None
        record_game_event(tg_user.id, 'mines', float(session['bet']), 0, session['currency'], won=False)
        db.save_data()
        return {
            'ok': True,
            'hit_mine': True,
            'mines': mines_positions,
            'profile': _serialize_profile(tg_user.id),
            'games': _serialize_game_hub(tg_user.id),
        }

    session['safe_clicks'] += 1
    base_multiplier = MINES_MULTIPLIERS[min(session['safe_clicks'] - 1, len(MINES_MULTIPLIERS) - 1)]
    current_multiplier = base_multiplier
    can_cashout = session['safe_clicks'] > 0
    db.save_data()
    return {
        'ok': True,
        'hit_mine': False,
        'revealed': session['revealed'],
        'safe_clicks': session['safe_clicks'],
        'current_multiplier': current_multiplier,
        'can_cashout': can_cashout,
        'finished': session['safe_clicks'] >= MAX_SAFE_CLICKS,
    }


@app.post('/api/games/mines/cashout')
def cashout_mines(init_data: str = Form(...)):
    tg_user, user_data = _require_user(init_data)
    session = user_data.get('miniapp_mines')
    if not session:
        _error(404, 'Нет активной игры в мины')
    safe_clicks = int(session.get('safe_clicks', 0) or 0)
    if safe_clicks <= 0:
        _error(400, 'Нельзя забрать выигрыш без открытых безопасных клеток')
    base_multiplier = MINES_MULTIPLIERS[min(safe_clicks - 1, len(MINES_MULTIPLIERS) - 1)]
    multiplier = base_multiplier
    payout = round(float(session['bet']) * float(multiplier), 4 if session['currency'] == 'ton' else 1)
    _add_balance(user_data, session['currency'], payout)

    user_stats = _get_user_mines_stats(user_data)
    global_stats = _get_global_mines_stats()
    user_stats['games_played'] += 1
    user_stats['wins'] += 1
    user_stats['total_bet'] += float(session['bet'])
    user_stats['total_won'] += payout
    user_stats['biggest_win'] = max(float(user_stats.get('biggest_win', 0) or 0), payout)
    global_stats['games_played'] += 1
    global_stats['wins'] += 1
    global_stats['total_bet'] += float(session['bet'])
    global_stats['total_paid_out'] += payout
    global_stats['net_profit'] = round(float(global_stats['total_bet']) - float(global_stats['total_paid_out']), 2)

    user_data['miniapp_mines'] = None
    record_game_event(tg_user.id, 'mines', float(session['bet']), payout, session['currency'], won=True)
    db.save_data()
    return {'ok': True, 'payout': payout, 'multiplier': multiplier, 'profile': _serialize_profile(tg_user.id), 'games': _serialize_game_hub(tg_user.id)}


@app.post('/api/games/coin/play')
def play_coin(payload: CoinPlayIn):
    tg_user, user_data = _require_user(payload.init_data)
    amount = round(float(payload.amount), 4 if payload.currency == 'ton' else 1)
    coin_settings = _get_coin_settings()
    min_bet = float(coin_settings.get('min_bet', 5))
    max_bet = float(coin_settings.get('max_bet', 10000))
    if payload.currency == 'ton':
        min_bet = max(min_bet, TON_MIN_BET)
    if amount < min_bet or amount > max_bet:
        _error(400, f'Ставка должна быть от {format_stars(min_bet)} до {format_stars(max_bet)}')
    _sub_balance_checked(user_data, payload.currency, amount)

    odds = coin_settings.get('odds', {'eagle': 45.0, 'tails': 45.0, 'edge': 10.0})
    weights = {k: float(v or 0) for k, v in odds.items()}
    total = sum(weights.values())
    if total <= 0:
        weights = {'eagle': 45.0, 'tails': 45.0, 'edge': 10.0}
        total = 100.0

    roll = random.random() * total
    cumulative = 0.0
    result = 'eagle'
    for option in ['eagle', 'tails', 'edge']:
        cumulative += weights.get(option, 0)
        if roll < cumulative:
            result = option
            break

    win = payload.choice == result
    multipliers = coin_settings.get('multipliers', {'eagle': 2.0, 'tails': 2.0, 'edge': 5.0})
    payout = round(amount * float(multipliers.get(result, 0) or 0), 4 if payload.currency == 'ton' else 1) if win else 0
    if payout:
        _add_balance(user_data, payload.currency, payout)

    user_stats = _get_user_game_stats(user_data, 'coin')
    global_stats = _get_global_game_stats('coin')
    user_stats['games_played'] += 1
    user_stats['total_bet'] += amount
    global_stats['games_played'] += 1
    global_stats['total_bet'] += amount
    if win:
        user_stats['wins'] += 1
        user_stats['total_paid_out'] += payout
        global_stats['wins'] += 1
        global_stats['total_paid_out'] += payout
    else:
        user_stats['losses'] += 1
        global_stats['losses'] += 1
    global_stats['net_profit'] = round(float(global_stats.get('total_bet', 0) or 0) - float(global_stats.get('total_paid_out', 0) or 0), 2)
    record_game_event(tg_user.id, 'coin', amount, payout, payload.currency, won=win)
    db.save_data()

    return {
        'ok': True,
        'result': result,
        'win': win,
        'payout': payout,
        'profile': _serialize_profile_from_user(user_data),
        'games': _serialize_game_hub_from_user(user_data),
    }


def _crash_min_duration_for_x(target_x: float) -> float:
    if target_x <= 1.0:
        return 0.0
    steps = 0.0
    if target_x <= 1.45:
        steps = (target_x - 1.00) / 0.01
    elif target_x <= 3.50:
        steps = 45.0 + (target_x - 1.45) / 0.02
    else:
        steps = 45.0 + 102.5 + (target_x - 3.50) / 0.04
    return max(0.0, float(steps) * 0.07)


@app.post('/api/games/crash/play')
def play_crash(request: Request, payload: CrashPlayIn):
    token = _extract_init_data(request, payload.init_data)
    tg_user, user_data = _require_user(token, allow_demo=False)
    if tg_user.id == 0:
        _error(403, 'Игра доступна только авторизованным пользователям')
    _check_rate_limit(request, 'crash_play', max_requests=20, window_seconds=60, actor_id=tg_user.id)

    amount = round(float(payload.amount), 1 if payload.currency == 'stars' else 4)
    if amount < CRASH_MIN_BET or amount > CRASH_MAX_BET:
        _error(400, f'Ставка должна быть от {format_stars(CRASH_MIN_BET)} до {format_stars(CRASH_MAX_BET)}')

    if user_data.get('miniapp_crash'):
        _error(409, 'У вас уже есть активный раунд Crash')

    _sub_balance_checked(user_data, payload.currency, amount)
    auto_cashout = payload.auto_cashout
    if auto_cashout is None:
        crash_point = _simulate_crash_point()
        # Security: DO NOT disclose crash_point or future history to client (Fix F-04)
        started_at_ts = time.time()
        user_data['miniapp_crash'] = {
            'bet': amount,
            'currency': payload.currency,
            'crash_point': crash_point,
            'started_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'started_at_ts': started_at_ts,
        }
        db.save_data()
        return {
            'ok': True,
            'started_at_ts': started_at_ts,
            'profile': _serialize_profile_from_user(user_data),
            'games': _serialize_game_hub_from_user(user_data),
        }

    auto_cashout = round(float(auto_cashout), 2)
    if auto_cashout < CRASH_MIN_X or auto_cashout > CRASH_MAX_X:
        _error(400, f'Автовывод должен быть от {CRASH_MIN_X:.2f}x до {CRASH_MAX_X:.2f}x')

    crash_point = _simulate_crash_point()
    won = auto_cashout <= crash_point
    payout = round(amount * auto_cashout, 4 if payload.currency == 'ton' else 1) if won else 0
    if payout:
        _add_balance(user_data, payload.currency, payout)

    user_stats = _get_user_crash_stats(user_data)
    global_stats = _get_global_crash_stats()
    user_stats['games_played'] += 1
    user_stats['total_bet'] += amount
    global_stats['games_played'] += 1
    global_stats['total_bet'] += amount
    global_stats['last_round_number'] = int(global_stats.get('last_round_number', 0) or 0) + 1
    if won:
        user_stats['wins'] += 1
        user_stats['total_won'] += payout
        user_stats['biggest_win'] = max(float(user_stats.get('biggest_win', 0) or 0), payout)
        global_stats['wins'] += 1
        global_stats['total_paid_out'] += payout
    else:
        user_stats['losses'] += 1
        global_stats['losses'] += 1
    global_stats['net_profit'] = round(float(global_stats['total_bet']) - float(global_stats['total_paid_out']), 2)
    record_game_event(tg_user.id, 'crash', amount, payout, payload.currency, won=won)
    db.save_data()
    return {
        'ok': True,
        'won': won,
        'auto_cashout': auto_cashout,
        'crash_point': crash_point,
        'payout': payout,
        'profile': _serialize_profile_from_user(user_data),
        'games': _serialize_game_hub_from_user(user_data),
    }


@app.post('/api/games/crash/cashout')
def cashout_crash(request: Request, payload: CrashCashoutIn):
    token = _extract_init_data(request, payload.init_data)
    tg_user, user_data = _require_user(token, allow_demo=False)
    session = user_data.get('miniapp_crash')
    if not session:
        _error(404, 'Нет активного раунда Crash')

    cashout_x = round(float(payload.cashout_x), 2)
    if cashout_x < 1.0:
        _error(400, 'Значение x должно быть не меньше 1.0')

    started_at_ts = float(session.get('started_at_ts', 0) or 0)
    min_time = _crash_min_duration_for_x(cashout_x)
    if started_at_ts and (time.time() - started_at_ts < min_time):
        _error(400, 'Слишком быстрый вывод')

    crash_point = float(session.get('crash_point', 0) or 0)
    amount = float(session.get('bet', 0) or 0)
    currency = session.get('currency')
    won = cashout_x <= crash_point
    payout = round(amount * cashout_x, 4 if currency == 'ton' else 1) if won else 0
    if payout:
        _add_balance(user_data, currency, payout)

    user_stats = _get_user_crash_stats(user_data)
    global_stats = _get_global_crash_stats()
    user_stats['games_played'] += 1
    user_stats['total_bet'] += amount
    if won:
        user_stats['wins'] += 1
        user_stats['total_won'] += payout
        user_stats['biggest_win'] = max(float(user_stats.get('biggest_win', 0) or 0), payout)
        global_stats['wins'] += 1
        global_stats['total_paid_out'] += payout
    else:
        user_stats['losses'] += 1
        global_stats['losses'] += 1
    global_stats['games_played'] += 1
    global_stats['total_bet'] += amount
    global_stats['last_round_number'] = int(global_stats.get('last_round_number', 0) or 0) + 1
    global_stats['net_profit'] = round(float(global_stats['total_bet']) - float(global_stats['total_paid_out']), 2)
    user_data['miniapp_crash'] = None
    record_game_event(tg_user.id, 'crash', amount, payout, currency, won=won)
    db.save_data()
    return {
        'ok': True,
        'won': won,
        'cashout_x': cashout_x,
        'crash_point': crash_point,
        'payout': payout,
        'profile': _serialize_profile_from_user(user_data),
        'games': _serialize_game_hub_from_user(user_data),
    }


@app.post('/api/games/crash/finish')
def finish_crash(request: Request, payload: CrashFinishIn):
    token = _extract_init_data(request, payload.init_data)
    tg_user, user_data = _require_user(token, allow_demo=False)
    session = user_data.get('miniapp_crash')
    if not session:
        _error(404, 'Нет активного раунда Crash')

    crash_point = float(session.get('crash_point', 0) or 0)
    amount = float(session.get('bet', 0) or 0)
    currency = session.get('currency')

    user_stats = _get_user_crash_stats(user_data)
    global_stats = _get_global_crash_stats()
    user_stats['games_played'] += 1
    user_stats['losses'] += 1
    user_stats['total_bet'] += amount
    global_stats['games_played'] += 1
    global_stats['losses'] += 1
    global_stats['total_bet'] += amount
    global_stats['last_round_number'] = int(global_stats.get('last_round_number', 0) or 0) + 1
    global_stats['net_profit'] = round(float(global_stats['total_bet']) - float(global_stats['total_paid_out']), 2)
    user_data['miniapp_crash'] = None
    record_game_event(tg_user.id, 'crash', amount, 0, currency, won=False)
    db.save_data()
    return {
        'ok': True,
        'crash_point': crash_point,
        'profile': _serialize_profile_from_user(user_data),
        'games': _serialize_game_hub_from_user(user_data),
    }


@app.post('/api/games/dice/invite')
def create_dice_invite(payload: DiceInviteIn):
    tg_user, user_data = _require_user(payload.init_data)
    amount = round(float(payload.amount), 1 if payload.currency == 'stars' else 4)
    min_bet = TON_MIN_BET if payload.currency == 'ton' else MIN_BET
    if amount < min_bet or amount > MAX_BET:
        _error(400, f'Ставка должна быть от {format_stars(min_bet)} до {format_stars(MAX_BET)}')
    room_id = _create_dice_room(tg_user.id, payload.currency, amount, payload.rounds_total)
    username = (BOT_USERNAME or '').strip().lstrip('@')
    if not username:
        _error(500, 'BOT_USERNAME не указан в config.py')
    invite_link = f'https://t.me/{username}?start=dice_{room_id}'
    return {'ok': True, 'room_id': room_id, 'invite_link': invite_link}


@app.post('/api/casino/racket/play')
def play_casino_racket(payload: CasinoRacketIn):
    tg_user, user_data = _require_user(payload.init_data)
    amount = round(float(payload.amount), 1 if payload.currency == 'stars' else 4)
    if amount <= 0:
        _error(400, 'Ставка должна быть больше нуля')
    _sub_balance_checked(user_data, payload.currency, amount)
    outcome = _choose_racket_outcome()
    payout = round(amount * float(outcome['multiplier']), 4 if payload.currency == 'ton' else 1) if outcome['multiplier'] > 0 else 0
    if payout > 0:
        _add_balance(user_data, payload.currency, payout)
    casino = user_data.setdefault('casino', _default_casino_data())
    casino['racket']['played'] = int(casino['racket'].get('played', 0) or 0) + 1
    casino['racket']['total_bet'] = round(float(casino['racket'].get('total_bet', 0) or 0) + amount, 4 if payload.currency == 'ton' else 1)
    if payout > 0:
        casino['racket']['wins'] = int(casino['racket'].get('wins', 0) or 0) + 1
        casino['racket']['total_won'] = round(float(casino['racket'].get('total_won', 0) or 0) + payout, 4 if payload.currency == 'ton' else 1)
    casino['racket']['last_outcome'] = {'name': outcome['name'], 'label': outcome['label'], 'multiplier': outcome['multiplier'], 'payout': payout}
    db.save_data()
    return {
        'ok': True,
        'outcome': casino['racket']['last_outcome'],
        'payout': payout,
        'profile': _serialize_profile(tg_user.id),
        'casino': _serialize_casino(user_data),
    }


@app.post('/api/casino/case/open')
def open_casino_case(payload: CasinoCaseOpenIn):
    tg_user, user_data = _require_user(payload.init_data)
    if payload.tier == 'case150':
        last_case = _open_case150(user_data)
    elif payload.tier in SPECIAL_CASES_CONFIG:
        last_case = _open_special_case(user_data, payload.tier)
    else:
        last_case = _open_casino_case(user_data, payload.tier)
    case_cost = float(last_case.get('cost', 0) or SPECIAL_CASES_CONFIG.get(payload.tier, {}).get('cost', 0) or CASE_SETTINGS.get(payload.tier, {}).get('cost', 0) or (150 if payload.tier == 'case150' else 0))
    case_reward = float(last_case.get('reward', 0) or last_case.get('value', 0) or 0)
    record_game_event(tg_user.id, 'cases', case_cost, case_reward, 'stars', won=case_reward > case_cost)
    db.save_data()
    return {
        'ok': True,
        'case': last_case,
        'profile': _serialize_profile_from_user(user_data),
        'casino': _serialize_casino(user_data),
        'inventory': _serialize_inventory(user_data),
    }


@app.post('/api/casino/upgrade/buy')
def buy_casino_upgrade(payload: CasinoUpgradeBuyIn):
    tg_user, user_data = _require_user(payload.init_data)
    last_upgrade = _buy_casino_upgrade(user_data, payload.upgrade)
    db.save_data()
    return {
        'ok': True,
        'upgrade': last_upgrade,
        'profile': _serialize_profile(tg_user.id),
        'casino': _serialize_casino(user_data),
    }


@app.post('/api/promo/apply')
def apply_promo(request: Request, payload: PromoIn):
    token = _extract_init_data(request, payload.init_data)
    tg_user, user_data = _require_user(token, allow_demo=False)
    if tg_user.id == 0:
        _error(403, 'Активация промокодов недоступна в демо-режиме')
    _check_rate_limit(request, 'promo_apply', max_requests=5, window_seconds=60, actor_id=tg_user.id)
    code = (payload.code or '').strip().upper()
    if not code:
        _error(400, 'Промокод пустой')

    promo = next((p for p in db.promocodes if str(p.get('code', '')).strip().upper() == code and p.get('active', True)), None)
    if not promo:
        _error(404, 'Промокод не найден или уже выключен')

    used_by = promo.setdefault('used_by', [])
    max_uses = int(promo.get('max_uses', 0) or 0)
    amount = int(promo.get('amount_stars', 0) or 0)

    if tg_user.id in used_by:
        _error(409, 'Вы уже использовали этот промокод')
    if int(promo.get('used_count', 0) or 0) >= max_uses:
        promo['active'] = False
        db.save_data()
        _error(409, 'У промокода закончились активации')

    add_star_balance(user_data, amount)
    promo['used_count'] = int(promo.get('used_count', 0) or 0) + 1
    used_by.append(tg_user.id)
    if int(promo['used_count']) >= max_uses:
        promo['active'] = False
    db.save_data()
    return {'ok': True, 'credited_stars': amount, 'profile': _serialize_profile(tg_user.id)}


@app.post('/api/orders/stars/preview')
def preview_stars_order(payload: StarsOrderIn):
    _require_user(payload.init_data)
    price = _calculate_stars_order_price(int(payload.stars))
    return _build_stars_instructions(payload.stars, price, payload.payment_method, payload.target_username)


@app.post('/api/orders/stars/create')
def create_stars_order(request: Request, payload: StarsOrderIn):
    token = _extract_init_data(request, payload.init_data)
    tg_user, user_data = _require_user(token, allow_demo=False)
    _check_rate_limit(request, 'orders_stars_create', max_requests=10, window_seconds=60, actor_id=tg_user.id)
    price = _calculate_stars_order_price(int(payload.stars))

    target_username = (payload.target_username or '').strip().lstrip('@') or None

    if payload.payment_method == 'ton_balance':
        ton_amount = _ton_amount_for_uah(price)
        if get_numeric_ton_balance(user_data) < ton_amount:
            _error(400, 'Недостаточно TON на балансе')
        sub_ton_balance(user_data, ton_amount)
        recipient_id = _find_user_id_by_username(target_username) if target_username else tg_user.id
        is_for_friend = bool(target_username and (recipient_id != tg_user.id))

        if is_for_friend:
            # Fix F-06: Third-party/gift purchases with TON balance require human admin review
            transaction = _create_transaction({
                'type': 'stars',
                'user_id': tg_user.id,
                'stars': payload.stars,
                'amount': price,
                'ton_amount': ton_amount,
                'status': 'pending',
                'purchase_for': 'friend',
                'target_username': target_username,
                'recipient_user_id': recipient_id,
                'delivered_to_balance': False,
                'payment_method': 'ton_balance',
                'held_at_creation': True,
                'referral_rewarded': False,
            })
            safe_user = html.escape(_username(tg_user.username), quote=False)
            safe_target = html.escape(target_username or 'unknown', quote=False)
            try:
                send_message(
                    ADMIN_CHAT_ID,
                    (
                        f"🆕 Заказ #{transaction['id']} на отправку Stars другу (с TON баланса)\n\n"
                        f"🛒 Товар: Stars\n"
                        f"👤 Покупатель ID: {tg_user.id} (@{safe_user})\n"
                        f"🎁 Получатель: @{safe_target}\n"
                        f"⭐️ Количество: {payload.stars}\n"
                        f"💠 Списано: {format_stars(ton_amount)} TON\n"
                        f"⏳ Требуется проверка и подтверждение администратора."
                    ),
                    reply_markup=_admin_payment_keyboard(transaction['id']),
                )
            except Exception:
                pass
            db.save_data()
            return {
                'ok': True,
                'instant': False,
                'message': f'Заказ для @{target_username} создан и передан на проверку администратору.',
                'profile': _serialize_profile(tg_user.id),
                'transactions': _recent_transactions(tg_user.id),
            }

        # Self purchase with TON balance
        add_star_balance(user_data, payload.stars)
        message = f'Начислено {payload.stars} ⭐️. Списано {format_stars(ton_amount)} TON.'
        _create_transaction({
            'type': 'stars',
            'user_id': tg_user.id,
            'stars': payload.stars,
            'amount': price,
            'ton_amount': ton_amount,
            'status': 'confirmed',
            'referral_rewarded': True,
            'purchase_for': 'self',
            'target_username': None,
            'recipient_user_id': tg_user.id,
            'delivered_to_balance': True,
            'payment_method': 'ton_balance',
        })
        db.save_data()
        reward_referrer_for_purchase(tg_user.id, 'stars', stars=payload.stars)
        db.save_data()
        return {
            'ok': True,
            'instant': True,
            'message': message,
            'profile': _serialize_profile(tg_user.id),
            'transactions': _recent_transactions(tg_user.id),
        }

    return {
        'ok': True,
        'instant': False,
        **_build_stars_instructions(payload.stars, price, payload.payment_method, target_username),
    }


@app.post('/api/orders/premium/preview')
def preview_premium_order(payload: PremiumOrderIn):
    _require_user(payload.init_data)
    prices = get_premium_prices()
    if payload.months not in prices:
        _error(400, 'Недоступный срок Premium')
    return _build_premium_instructions(payload.months, float(prices[payload.months]), payload.payment_method)


@app.post('/api/orders/premium/create')
def create_premium_order(payload: PremiumOrderIn):
    tg_user, user_data = _require_user(payload.init_data, allow_demo=False)
    prices = get_premium_prices()
    if payload.months not in prices:
        _error(400, 'Недоступный срок Premium')
    price = float(prices[payload.months])
    target_username = (payload.target_username or '').strip().lstrip('@') or None

    if payload.payment_method == 'ton_balance':
        ton_amount = _ton_amount_for_uah(price)
        if get_numeric_ton_balance(user_data) < ton_amount:
            _error(400, 'Недостаточно TON на балансе')
        sub_ton_balance(user_data, ton_amount)
        transaction = _create_transaction({
            'type': 'premium',
            'user_id': tg_user.id,
            'months': payload.months,
            'amount': price,
            'payment_method': 'ton_balance',
            'target_username': target_username,
            'status': 'confirmed',
            'referral_rewarded': True,
        })
        db.save_data()
        reward_referrer_for_purchase(tg_user.id, 'premium', months=payload.months)
        db.save_data()
        message = (
            f'Premium на {payload.months} мес. оплачен с TON баланса. '
            + (f'Свяжитесь с {PREMIUM_SELLER_USERNAME}.' if payload.months == 1 else 'Ожидайте выдачу.')
        )
        try:
            safe_user = html.escape(_username(tg_user.username), quote=False)
            safe_target = html.escape(f"@{target_username}" if target_username else 'не указан', quote=False)
            send_message(
                ADMIN_CHAT_ID,
                (
                    f"🆕 Premium #{transaction['id']} оплачен с TON баланса\n\n"
                    f"👤 ID: {tg_user.id}\n"
                    f"👤 @{safe_user}\n"
                    f"📅 Срок: {payload.months} мес.\n"
                    f"🎯 Для: {safe_target}\n"
                    f"💠 Оплата: TON баланс"
                ),
            )
        except Exception:
            pass
        return {
            'ok': True,
            'instant': True,
            'message': message,
            'profile': _serialize_profile(tg_user.id),
            'transactions': _recent_transactions(tg_user.id),
        }

    return {
        'ok': True,
        'instant': False,
        **_build_premium_instructions(payload.months, price, payload.payment_method),
    }


@app.post('/api/orders/ton/preview')
def preview_ton_topup(payload: TonTopupIn):
    _require_user(payload.init_data)
    return _build_ton_topup_preview(payload.ton_amount, payload.payment_method)


@app.post('/api/orders/ton/create')
def create_ton_topup(payload: TonTopupIn):
    _require_user(payload.init_data, allow_demo=False)
    return {'ok': True, **_build_ton_topup_preview(payload.ton_amount, payload.payment_method)}


@app.post('/api/support/create')
def create_support_request(payload: SupportIn):
    tg_user, _ = _require_user(payload.init_data, allow_demo=False)
    text = payload.text.strip()
    if len(text) < 3:
        _error(400, 'Сообщение слишком короткое')

    safe_text = html.escape(text, quote=False)
    safe_uname = html.escape(_username(tg_user.username), quote=False)
    if payload.category == 'suggestion':
        item = {
            'id': db.suggestion_id_counter,
            'user_id': tg_user.id,
            'username': tg_user.username or 'unknown',
            'text': text,
            'date': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'status': 'new',
        }
        db.suggestions.append(item)
        db.suggestion_id_counter += 1
        db.save_data()
        try:
            send_message(ADMIN_CHAT_ID, f"💡 Новое предложение #{item['id']}\n\n👤 ID: {tg_user.id}\n👤 @{safe_uname}\n\n{safe_text}")
        except Exception:
            pass
        return {'ok': True, 'message': 'Предложение отправлено'}

    try:
        send_message(ADMIN_CHAT_ID, f"🛠️ Новый запрос в поддержку\n\n👤 ID: {tg_user.id}\n👤 @{safe_uname}\n\n{safe_text}")
    except Exception:
        pass
    return {'ok': True, 'message': 'Сообщение в поддержку отправлено'}


@app.post('/api/inventory/gift/sell')
def sell_inventory_gift(payload: InventoryGiftActionIn):
    tg_user, user_data = _require_user(payload.init_data, allow_demo=False)
    result = _sell_inventory_gift(user_data, payload.gift_id)
    db.save_data()
    return {
        'ok': True,
        'converted': result,
        'profile': _serialize_profile_from_user(user_data),
        'inventory': _serialize_inventory(user_data, tg_user.id),
        'casino': _serialize_casino(user_data),
        'transactions': _recent_transactions(tg_user.id),
    }


@app.post('/api/inventory/gift/withdraw')
def withdraw_inventory_gift(payload: InventoryGiftActionIn):
    tg_user, user_data = _require_user(payload.init_data, allow_demo=False)
    transaction = _create_inventory_withdraw_request(user_data, tg_user, payload.gift_id)
    db.save_data()
    try:
        caption, reply_markup = _build_gift_withdraw_admin_message(transaction, tg_user)
        send_message(ADMIN_CHAT_ID, caption, reply_markup=reply_markup)
    except Exception:
        pass
    return {
        'ok': True,
        'message': 'Заявка отправлена',
        'transaction': transaction,
        'inventory': _serialize_inventory(user_data, tg_user.id),
        'transactions': _recent_transactions(tg_user.id),
    }


@app.post('/api/withdraw/create')
def create_withdraw_request(payload: WithdrawIn):
    tg_user, user_data = _require_user(payload.init_data, allow_demo=False)

    with _BALANCE_LOCK:
        if payload.asset == 'stars':
            try:
                amount = int(payload.amount)
            except (ValueError, TypeError):
                _error(400, 'Некорректная сумма звёзд')
            if amount < 50 or amount > 10000:
                _error(400, 'Вывод звёзд: от 50 до 10000')
            if amount > get_numeric_balance(user_data):
                _error(400, 'Недостаточно звёзд на балансе')
            sub_star_balance(user_data, amount)
            transaction = _create_transaction({'type': 'withdraw', 'user_id': tg_user.id, 'stars': amount, 'status': 'pending', 'held_at_creation': True})
            caption = f"💸 Новая заявка на вывод #{transaction['id']}\n\n👤 ID: {tg_user.id}\n👤 @{_username(tg_user.username)}\n⭐️ К выводу: {amount}"
        else:
            try:
                amount = round(float(payload.amount), 4)
            except (ValueError, TypeError):
                _error(400, 'Некорректная сумма TON')
            if not math.isfinite(amount) or amount <= 0:
                _error(400, 'TON должен быть больше 0')
            if amount > get_numeric_ton_balance(user_data):
                _error(400, 'Недостаточно TON на балансе')
            sub_ton_balance(user_data, amount)
            transaction = _create_transaction({'type': 'withdraw_ton', 'user_id': tg_user.id, 'ton_amount': amount, 'status': 'pending', 'held_at_creation': True})
            caption = f"↘️ Новая заявка на вывод TON #{transaction['id']}\n\n👤 ID: {tg_user.id}\n👤 @{_username(tg_user.username)}\n💠 К выводу: {format_stars(amount)} TON"

        db.save_data()
    try:
        send_message(ADMIN_CHAT_ID, caption, reply_markup=_admin_withdraw_keyboard(transaction['id']))
    except Exception:
        pass
    return {'ok': True, 'message': 'Заявка отправлена', 'transactions': _recent_transactions(tg_user.id)}


@app.post('/api/transactions')
def user_transactions(init_data: str = Form(...)):
    tg_user, _ = _require_user(init_data)
    return {'ok': True, 'transactions': _recent_transactions(tg_user.id), 'profile': _serialize_profile(tg_user.id)}


def _is_valid_image_bytes(data: bytes) -> bool:
    if not data or len(data) < 4:
        return False
    if data.startswith(b'\xff\xd8\xff'):
        return True
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return True
    if data.startswith(b'GIF87a') or data.startswith(b'GIF89a'):
        return True
    if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return True
    if len(data) >= 12 and data[4:8] == b'ftyp' and data[8:12].lower() in (b'heic', b'heix', b'hevc', b'mif1'):
        return True
    return False


@app.post('/api/proof/upload')
async def upload_payment_proof(
    request: Request,
    init_data: str = Form(...),
    kind: str = Form(...),
    payload_json: str = Form(...),
    proof: UploadFile = File(...),
):
    token = _extract_init_data(request, init_data)
    tg_user, _ = _require_user(token, allow_demo=False)
    _check_rate_limit(request, 'proof_upload', max_requests=10, window_seconds=300, actor_id=tg_user.id)

    # Validate file
    if not proof.filename:
        _error(400, 'Файл не имеет имени')
    
    content_type = proof.content_type or ''
    valid_types = ('image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif', 'image/heic', 'image/heif')
    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.heic', '.heif')
    if not (any(ct in content_type for ct in valid_types) or proof.filename.lower().endswith(valid_extensions)):
        _error(400, 'Поддерживаются только изображения (JPG, PNG, WebP, HEIC)')
    
    # Check file size (max 10MB for Telegram)
    size_limit = 10 * 1024 * 1024
    
    try:
        payload = json.loads(payload_json)
    except Exception:
        _error(400, 'Некорректный payload')

    suffix = Path(proof.filename or 'proof.jpg').suffix or '.jpg'
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_path = Path(temp_file.name)
    hasher = hashlib.sha256()
    first_chunk = b''
    try:
        total_size = 0
        while True:
            chunk = await proof.read(1024 * 1024)
            if not chunk:
                break
            if not first_chunk:
                first_chunk = chunk
            hasher.update(chunk)
            total_size += len(chunk)
            if total_size > size_limit:
                temp_file.close()
                temp_path.unlink(missing_ok=True)
                _error(413, f'Файл слишком большой (максимум 10 МБ)')
            temp_file.write(chunk)
        temp_file.flush()
        temp_file.close()

        # Security check: validate magic bytes
        if not _is_valid_image_bytes(first_chunk):
            _error(400, 'Некорректный или повреждённый файл изображения')

        # Anti-replay: verify hash is not already used in another non-rejected transaction
        proof_hash = hasher.hexdigest()
        for tx in db.transactions:
            if tx.get('proof_hash') == proof_hash and tx.get('status') not in {'cancelled', 'error', 'rejected'}:
                _error(400, 'Этот чек уже был загружен ранее')

        safe_user = html.escape(_username(tg_user.username), quote=False)
        if kind == 'stars':
            stars = int(payload.get('stars', 0) or 0)
            if stars < 50 or stars > 100000:
                _error(400, 'Некорректное количество звезд (от 50)')
            amount = _calculate_stars_order_price(stars)
            payment_method = payload.get('payment_method')
            target_username = (payload.get('target_username') or '').strip().lstrip('@')
            recipient_user_id = _find_user_id_by_username(target_username) if target_username else tg_user.id
            transaction = _create_transaction({
                'type': 'stars',
                'user_id': tg_user.id,
                'stars': stars,
                'amount': amount,
                'payment_method': payment_method,
                'status': 'pending',
                'purchase_for': 'friend' if target_username else 'self',
                'target_username': target_username or None,
                'recipient_user_id': recipient_user_id,
                'delivered_to_balance': False,
                'proof_hash': proof_hash,
            })
            safe_target = html.escape(f"@{target_username}" if target_username else f"@{safe_user}", quote=False)
            caption = (
                f"🆕 Новая заявка #{transaction['id']}\n\n"
                f"🛒 Товар: Stars\n"
                f"👤 Покупатель ID: {tg_user.id}\n"
                f"👤 Покупатель: @{safe_user}\n"
                f"🎁 Получатель: {safe_target}\n"
                f"⭐️ {stars}\n"
                f"💰 {amount:.2f} грн"
            )
            if target_username and not recipient_user_id:
                caption += '\nℹ️ Получатель не найден в базе по username'
            success_text = 'Чек отправлен на проверку'

        elif kind == 'premium':
            months = int(payload.get('months', 0) or 0)
            premium_prices = get_premium_prices()
            if months not in premium_prices:
                _error(400, 'Некорректный срок Premium')
            amount = float(premium_prices[months])
            payment_method = payload.get('payment_method')
            target_username = (payload.get('target_username') or '').strip().lstrip('@')
            transaction = _create_transaction({
                'type': 'premium',
                'user_id': tg_user.id,
                'months': months,
                'amount': amount,
                'payment_method': payment_method,
                'target_username': target_username or None,
                'status': 'pending',
                'proof_hash': proof_hash,
            })
            safe_target = html.escape(f"@{target_username}" if target_username else 'не указан', quote=False)
            caption = (
                f"🆕 Новая заявка #{transaction['id']}\n\n"
                f"🛒 Товар: Telegram Premium\n"
                f"👤 ID: {tg_user.id}\n"
                f"👤 @{safe_user}\n"
                f"📅 Срок: {months} мес.\n"
                f"🎯 Для: {safe_target}\n"
                f"💰 {amount:.2f} грн"
            )
            success_text = 'Заявка на Premium отправлена на проверку'

        elif kind == 'ton_topup':
            ton_amount = round(float(payload.get('ton_amount', 0) or 0), 4)
            if ton_amount <= 0:
                _error(400, 'Сумма TON должна быть больше 0')
            pricing = ton_to_uah_buy_price(ton_amount, markup_percent=0)
            if pricing is None:
                _error(503, 'Не удалось получить курс TON. Попробуйте позже.')
            base_total_uah = round(float(pricing['base_total_uah']), 2)
            payment_method = payload.get('payment_method')
            if payment_method == 'mono':
                fee_percent = 10.0 if ton_amount <= 5 else 7.0
                amount = round(base_total_uah * (1 + fee_percent / 100), 2)
            else:
                fee_percent = 0.0
                amount = base_total_uah
            transaction = _create_transaction({
                'type': 'ton_topup',
                'user_id': tg_user.id,
                'ton_amount': ton_amount,
                'amount': amount,
                'payment_method': payment_method,
                'status': 'pending',
                'fee_percent': fee_percent,
                'proof_hash': proof_hash,
            })
            if payment_method == 'ton_wallet':
                caption = (
                    f"🆕 Новая заявка #{transaction['id']}\n\n"
                    f"🛒 Товар: TON пополнение\n"
                    f"👤 ID: {tg_user.id}\n"
                    f"👤 @{safe_user}\n"
                    f"💠 Будет зачислено: {format_stars(ton_amount)} TON\n"
                    f"💠 Оплата: TON кошелёк"
                )
            else:
                caption = (
                    f"🆕 Новая заявка #{transaction['id']}\n\n"
                    f"🛒 Товар: TON пополнение\n"
                    f"👤 ID: {tg_user.id}\n"
                    f"👤 @{safe_user}\n"
                    f"💠 Будет зачислено: {format_stars(ton_amount)} TON\n"
                    f"💰 К оплате: {amount:.2f} грн\n"
                    f"💳 Оплата: Mono"
                )
            success_text = 'Чек на пополнение TON отправлен на проверку'
        else:
            _error(400, 'Неизвестный тип загрузки')

        try:
            sent_message = send_photo(ADMIN_CHAT_ID, temp_path, caption, reply_markup=_admin_payment_keyboard(transaction['id']))
            photo_sizes = sent_message.get('result', {}).get('photo', []) if isinstance(sent_message, dict) else []
            if photo_sizes:
                transaction['proof_file_id'] = photo_sizes[-1].get('file_id')
                db.save_data()
        except Exception as exc:
            transaction['status'] = 'error'
            db.save_data()
            print(f"[ERROR] Photo send failed for transaction #{transaction['id']}: {exc}", flush=True)
            import traceback
            traceback.print_exc()
            _error(500, 'Не удалось отправить чек администратору. Попробуйте позже.')
        return {'ok': True, 'message': success_text, 'transactions': _recent_transactions(tg_user.id)}
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass



# ==============================================================================
# PLINKO
# ==============================================================================

class PlinkoDropIn(BaseModel):
    init_data: str
    amount: float
    currency: str = 'stars'
    rows: int = 10
    risk: str = 'medium'
    balls: int = 1

PLINKO_MULTIPLIERS = {
    8: {
        'low': [5.6, 2.1, 1.1, 1.0, 0.5, 1.0, 1.1, 2.1, 5.6],
        'medium': [13, 3, 1.3, 0.7, 0.4, 0.7, 1.3, 3, 13],
        'high': [29, 4, 1.5, 0.3, 0.2, 0.3, 1.5, 4, 29],
    },
    10: {
        'low': [8.9, 3, 1.4, 1.1, 1, 0.5, 1, 1.1, 1.4, 3, 8.9],
        'medium': [22, 5, 2, 1.4, 0.6, 0.4, 0.6, 1.4, 2, 5, 22],
        'high': [76, 10, 3, 1.4, 0.3, 0.2, 0.3, 1.4, 3, 10, 76],
    },
    12: {
        'low': [10, 3, 1.6, 1.4, 1.1, 1, 0.5, 1, 1.1, 1.4, 1.6, 3, 10],
        'medium': [33, 11, 4, 2, 1.1, 0.6, 0.3, 0.6, 1.1, 2, 4, 11, 33],
        'high': [170, 24, 8.1, 2, 0.7, 0.2, 0.2, 0.2, 0.7, 2, 8.1, 24, 170],
    },
    14: {
        'low': [7.1, 4, 1.9, 1.4, 1.3, 1.1, 1, 0.5, 1, 1.1, 1.3, 1.4, 1.9, 4, 7.1],
        'medium': [58, 15, 7, 4, 1.9, 1, 0.5, 0.2, 0.5, 1, 1.9, 4, 7, 15, 58],
        'high': [420, 110, 18, 5, 1.9, 0.3, 0.2, 0.2, 0.2, 0.3, 1.9, 5, 18, 110, 420],
    },
    16: {
        'low': [16, 9, 2, 1.4, 1.4, 1.2, 1.1, 1, 0.5, 1, 1.1, 1.2, 1.4, 1.4, 2, 9, 16],
        'medium': [110, 41, 10, 5, 3, 1.5, 1, 0.5, 0.3, 0.5, 1, 1.5, 3, 5, 10, 41, 110],
        'high': [1000, 130, 26, 9, 4, 2, 0.2, 0.2, 0.2, 0.2, 0.2, 2, 4, 9, 26, 130, 1000],
    }
}

@app.post('/api/games/plinko/drop')
def plinko_drop(payload: PlinkoDropIn):
    tg_user, user_data = _require_user(payload.init_data)
    amount = float(payload.amount)
    balls = max(1, min(50, int(payload.balls or 1)))
    
    min_bet = TON_MIN_BET if payload.currency == 'ton' else MIN_BET
    if amount < min_bet or amount > MAX_BET:
        _error(400, 'Недопустимая сумма ставки')
        
    if payload.rows not in PLINKO_MULTIPLIERS or payload.risk not in ['low', 'medium', 'high']:
        _error(400, 'Неверные параметры игры')
        
    _sub_balance_checked(user_data, payload.currency, amount)
    
    ball_bet = amount / balls
    multipliers_table = PLINKO_MULTIPLIERS[payload.rows][payload.risk]
    
    drops = []
    total_payout = 0.0
    wins_count = 0
    losses_count = 0
    
    for _ in range(balls):
        path = [random.choice([0, 1]) for _ in range(payload.rows)]
        slot_index = sum(path)
        multiplier = multipliers_table[slot_index]
        ball_payout = round(ball_bet * multiplier, 4 if payload.currency == 'ton' else 1)
        total_payout += ball_payout
        if multiplier >= 1.0:
            wins_count += 1
        else:
            losses_count += 1
        drops.append({
            'path': path,
            'slot_index': slot_index,
            'multiplier': multiplier,
            'payout': ball_payout
        })
        
    total_payout = round(total_payout, 4 if payload.currency == 'ton' else 1)
    if total_payout > 0:
        _add_balance(user_data, payload.currency, total_payout)
        
    stats = db.game_stats.setdefault('plinko', {'games_played': 0, 'wins': 0, 'losses': 0, 'total_bet': 0.0, 'total_paid_out': 0.0, 'biggest_win': 0.0})
    stats['games_played'] += balls
    stats['total_bet'] += amount
    stats['total_paid_out'] += total_payout
    stats['wins'] += wins_count
    stats['losses'] += losses_count
    if total_payout > stats.get('biggest_win', 0.0):
        stats['biggest_win'] = total_payout
        
    won_game = total_payout >= amount
    record_game_event(tg_user.id, 'plinko', amount, total_payout, payload.currency, won=won_game)
    db.save_data()
    
    avg_multiplier = round(total_payout / amount, 2) if amount > 0 else drops[0]['multiplier']
    
    return {
        'ok': True,
        'path': drops[0]['path'],
        'slot_index': drops[0]['slot_index'],
        'multiplier': avg_multiplier,
        'multipliers': multipliers_table,
        'payout': total_payout,
        'win': won_game,
        'balls': balls,
        'ball_bet': round(ball_bet, 4 if payload.currency == 'ton' else 2),
        'drops': drops,
        'profile': _serialize_profile(tg_user.id),
        'currency': payload.currency,
        'balance_stars': user_data.get('balance_stars', 0),
        'balance_ton': user_data.get('balance_ton', 0.0)
    }

# ==============================================================================
# TOWER
# ==============================================================================

class TowerStartIn(BaseModel):
    init_data: str
    amount: float
    currency: str = 'stars'
    difficulty: str = 'medium'

class TowerStepIn(BaseModel):
    init_data: str
    tile_index: int

class TowerCashoutIn(BaseModel):
    init_data: str

@app.get('/api/games/tower/state')
def tower_state(request: Request, init_data: str | None = None):
    token = _extract_init_data(request, init_data)
    _, user_data = _require_user(token)
    session = user_data.get('miniapp_tower')
    if not session:
        return {'ok': True, 'active': False}

    difficulty = session.get('difficulty', 'medium')
    if difficulty not in TOWER_CONFIGS:
        return {'ok': True, 'active': False}

    current_floor = int(session.get('current_floor', 0))
    return {
        'ok': True,
        'active': True,
        'difficulty': difficulty,
        'current_floor': current_floor,
        'multipliers': session.get('multipliers', TOWER_CONFIGS[difficulty]['multipliers']),
        'tiles': TOWER_CONFIGS[difficulty]['tiles'],
        'can_cashout': current_floor > 0,
        'completed': current_floor >= 8,
    }

TOWER_CONFIGS = {
    'easy': {
        'tiles': 4,
        'traps': 1,
        'multipliers': [1.25, 1.62, 2.10, 2.75, 3.60, 4.80, 6.40, 8.60]
    },
    'medium': {
        'tiles': 3,
        'traps': 1,
        'multipliers': [1.40, 2.05, 3.00, 4.40, 6.50, 9.80, 14.80, 22.50]
    },
    'hard': {
        'tiles': 2,
        'traps': 1,
        'multipliers': [1.90, 3.70, 7.30, 14.50, 28.50, 56.00, 110.00, 220.00]
    }
}

@app.post('/api/games/tower/start')
def tower_start(payload: TowerStartIn):
    tg_user, user_data = _require_user(payload.init_data)
    amount = float(payload.amount)
    
    min_bet = TON_MIN_BET if payload.currency == 'ton' else MIN_BET
    if amount < min_bet or amount > MAX_BET:
        _error(400, 'Недопустимая сумма ставки')
        
    if user_data.get('miniapp_tower'):
        _error(400, 'Игра Башня уже начата')
        
    if payload.difficulty not in TOWER_CONFIGS:
        _error(400, 'Неверная сложность')
        
    _sub_balance_checked(user_data, payload.currency, amount)
    
    cfg = TOWER_CONFIGS[payload.difficulty]
    
    floors = []
    for _ in range(8):
        floor = [0] * cfg['tiles']
        trap_indices = random.sample(range(cfg['tiles']), cfg['traps'])
        for idx in trap_indices:
            floor[idx] = 1
        floors.append(floor)
        
    user_data['miniapp_tower'] = {
        'bet': amount,
        'currency': payload.currency,
        'difficulty': payload.difficulty,
        'floors': floors,
        'current_floor': 0,
        'multipliers': cfg['multipliers']
    }
    
    db.save_data()
    
    return {
        'ok': True,
        'status': 'active',
        'bet': amount,
        'currency': payload.currency,
        'difficulty': payload.difficulty,
        'current_floor': 0,
        'multipliers': cfg['multipliers'],
        'profile': _serialize_profile(tg_user.id)
    }

@app.post('/api/games/tower/step')
def tower_step(payload: TowerStepIn):
    tg_user, user_data = _require_user(payload.init_data)
    
    session = user_data.get('miniapp_tower')
    if not session:
        _error(400, 'Игра Башня не начата')
        
    floor_idx = session['current_floor']
    if floor_idx >= 8:
        _error(400, 'Игра уже окончена')
        
    cfg = TOWER_CONFIGS[session['difficulty']]
    if payload.tile_index < 0 or payload.tile_index >= cfg['tiles']:
        _error(400, 'Неверный индекс ячейки')
        
    floor_data = session['floors'][floor_idx]
    is_trap = (floor_data[payload.tile_index] == 1)
    
    bomb_indices = [i for i, v in enumerate(floor_data) if v == 1]
    
    stats = db.game_stats.setdefault('tower', {'games_played': 0, 'wins': 0, 'losses': 0, 'total_bet': 0.0, 'total_paid_out': 0.0, 'biggest_win': 0.0})
    
    if is_trap:
        stats['games_played'] += 1
        stats['total_bet'] += session['bet']
        stats['losses'] += 1
        
        user_data['miniapp_tower'] = None
        record_game_event(tg_user.id, 'tower', session['bet'], 0, session['currency'], won=False)
        db.save_data()
        
        return {
            'ok': True,
            'status': 'boom',
            'exploded': True,
            'bomb_indices': bomb_indices,
            'profile': _serialize_profile(tg_user.id)
        }
    
    session['current_floor'] += 1
    db.save_data()
    
    if session['current_floor'] == 8:
        db.save_data()
        return {
            'ok': True,
            'status': 'won',
            'exploded': False,
            'current_floor': 8,
            'current_multiplier': session['multipliers'][-1],
            'can_cashout': True,
            'profile': _serialize_profile(tg_user.id)
        }
        
    return {
        'ok': True,
        'status': 'active',
        'exploded': False,
        'current_floor': session['current_floor'],
        'current_multiplier': session['multipliers'][session['current_floor']-1],
        'can_cashout': True,
        'profile': _serialize_profile(tg_user.id)
    }

@app.post('/api/games/tower/cashout')
def tower_cashout(payload: TowerCashoutIn):
    tg_user, user_data = _require_user(payload.init_data)
    
    session = user_data.get('miniapp_tower')
    if not session:
        _error(400, 'Игра Башня не начата')
        
    if session['current_floor'] == 0:
        _error(400, 'Нельзя забрать выигрыш на нулевом этаже')
        
    mult = session['multipliers'][session['current_floor']-1]
    payout = round(session['bet'] * mult, 4 if session['currency'] == 'ton' else 1)
    _add_balance(user_data, session['currency'], payout)
    
    stats = db.game_stats.setdefault('tower', {'games_played': 0, 'wins': 0, 'losses': 0, 'total_bet': 0.0, 'total_paid_out': 0.0, 'biggest_win': 0.0})
    stats['games_played'] += 1
    stats['total_bet'] += session['bet']
    stats['total_paid_out'] += payout
    stats['wins'] += 1
    if payout > stats['biggest_win']:
        stats['biggest_win'] = payout
        
    user_data['miniapp_tower'] = None
    record_game_event(tg_user.id, 'tower', session['bet'], payout, session['currency'], won=True)
    db.save_data()
    
    return {
        'ok': True,
        'status': 'cashed_out',
        'payout': payout,
        'multiplier': mult,
        'profile': _serialize_profile(tg_user.id)
    }

# ==============================================================================
# BLACKJACK
# ==============================================================================

class BlackjackStartIn(BaseModel):
    init_data: str
    amount: float
    currency: str = 'stars'

class BlackjackActionIn(BaseModel):
    init_data: str

@app.get('/api/games/blackjack/state')
def blackjack_state(request: Request, init_data: str | None = None):
    token = _extract_init_data(request, init_data)
    _, user_data = _require_user(token)
    session = user_data.get('miniapp_blackjack')
    if not session:
        return {'ok': True, 'active': False}

    player_hand = session.get('player_hand', [])
    dealer_hand = session.get('dealer_hand', [])
    if not player_hand or not dealer_hand:
        user_data['miniapp_blackjack'] = None
        db.save_data()
        return {'ok': True, 'active': False}

    return {
        'ok': True,
        'active': True,
        'player_hand': player_hand,
        'player_score': calculate_hand_score(player_hand),
        'dealer_hand': [dealer_hand[0], '?'],
        'dealer_score': card_value(dealer_hand[0]),
        'status': 'playing',
        'can_double': len(player_hand) == 2 and not session.get('doubled', False),
    }

def get_blackjack_deck():
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    suits = ['H', 'D', 'C', 'S']
    deck = [f"{r}{s}" for r in ranks for s in suits]
    random.shuffle(deck)
    return deck

def card_value(card: str) -> int:
    rank = card[:-1]
    if rank in ['J', 'Q', 'K']:
        return 10
    if rank == 'A':
        return 11
    return int(rank)

def calculate_hand_score(hand: list[str]) -> int:
    score = sum(card_value(c) for c in hand)
    aces = sum(1 for c in hand if c[:-1] == 'A')
    while score > 21 and aces > 0:
        score -= 10
        aces -= 1
    return score

@app.post('/api/games/blackjack/start')
def blackjack_start(payload: BlackjackStartIn):
    tg_user, user_data = _require_user(payload.init_data)
    amount = float(payload.amount)
    
    min_bet = TON_MIN_BET if payload.currency == 'ton' else MIN_BET
    if amount < min_bet or amount > MAX_BET:
        _error(400, 'Недопустимая сумма ставки')
        
    if user_data.get('miniapp_blackjack'):
        _error(400, 'Игра Блэкджек уже начата')
        
    _sub_balance_checked(user_data, payload.currency, amount)
    
    deck = get_blackjack_deck()
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]
    
    player_score = calculate_hand_score(player_hand)
    dealer_score = calculate_hand_score(dealer_hand)
    
    stats = db.game_stats.setdefault('blackjack', {'games_played': 0, 'wins': 0, 'losses': 0, 'total_bet': 0.0, 'total_paid_out': 0.0, 'biggest_win': 0.0})
    
    if player_score == 21:
        if dealer_score == 21:
            # Push
            _add_balance(user_data, payload.currency, amount)
            stats['games_played'] += 1
            stats['total_bet'] += amount
            stats['total_paid_out'] += amount
            db.save_data()
            return {
                'ok': True,
                'player_hand': player_hand,
                'player_score': player_score,
                'dealer_hand': dealer_hand,
                'dealer_score': dealer_score,
                'status': 'push',
                'payout': amount,
                'can_double': False,
                'profile': _serialize_profile(tg_user.id)
            }
        else:
            # Player blackjack
            payout = round(amount * 2.5, 4 if payload.currency == 'ton' else 1)
            _add_balance(user_data, payload.currency, payout)
            stats['games_played'] += 1
            stats['total_bet'] += amount
            stats['total_paid_out'] += payout
            stats['wins'] += 1
            if payout > stats['biggest_win']:
                stats['biggest_win'] = payout
            db.save_data()
            return {
                'ok': True,
                'player_hand': player_hand,
                'player_score': player_score,
                'dealer_hand': dealer_hand,
                'dealer_score': dealer_score,
                'status': 'player_blackjack',
                'payout': payout,
                'can_double': False,
                'profile': _serialize_profile(tg_user.id)
            }
            
    user_data['miniapp_blackjack'] = {
        'bet': amount,
        'currency': payload.currency,
        'deck': deck,
        'player_hand': player_hand,
        'dealer_hand': dealer_hand,
        'doubled': False
    }
    db.save_data()
    
    return {
        'ok': True,
        'player_hand': player_hand,
        'player_score': player_score,
        'dealer_hand': [dealer_hand[0], '?'],
        'dealer_score': card_value(dealer_hand[0]),
        'status': 'playing',
        'payout': 0,
        'can_double': True,
        'profile': _serialize_profile(tg_user.id)
    }

@app.post('/api/games/blackjack/hit')
def blackjack_hit(payload: BlackjackActionIn):
    tg_user, user_data = _require_user(payload.init_data)
    
    session = user_data.get('miniapp_blackjack')
    if not session:
        _error(400, 'Игра Блэкджек не начата')
        
    deck = session['deck']
    if not deck:
        _error(500, 'Колода пуста')
        
    session['player_hand'].append(deck.pop())
    player_score = calculate_hand_score(session['player_hand'])
    
    stats = db.game_stats.setdefault('blackjack', {'games_played': 0, 'wins': 0, 'losses': 0, 'total_bet': 0.0, 'total_paid_out': 0.0, 'biggest_win': 0.0})
    
    if player_score > 21:
        stats['games_played'] += 1
        stats['total_bet'] += session['bet']
        stats['losses'] += 1
        
        user_data['miniapp_blackjack'] = None
        db.save_data()
        
        return {
            'ok': True,
            'player_hand': session['player_hand'],
            'player_score': player_score,
            'dealer_hand': session['dealer_hand'],
            'dealer_score': calculate_hand_score(session['dealer_hand']),
            'status': 'bust',
            'payout': 0,
            'profile': _serialize_profile(tg_user.id)
        }
        
    db.save_data()
    
    return {
        'ok': True,
        'player_hand': session['player_hand'],
        'player_score': player_score,
        'dealer_hand': [session['dealer_hand'][0], '?'],
        'dealer_score': card_value(session['dealer_hand'][0]),
        'status': 'playing',
        'payout': 0,
        'can_double': False,
        'profile': _serialize_profile(tg_user.id)
    }

def play_dealer_turn(session, stats, user_data, tg_user):
    deck = session['deck']
    dealer_hand = session['dealer_hand']
    player_hand = session['player_hand']
    bet = session['bet']
    currency = session['currency']
    
    player_score = calculate_hand_score(player_hand)
    dealer_score = calculate_hand_score(dealer_hand)
    
    while dealer_score < 17 and deck:
        dealer_hand.append(deck.pop())
        dealer_score = calculate_hand_score(dealer_hand)
        
    if dealer_score > 21:
        status = 'dealer_bust'
        payout = bet * 2
    elif player_score > dealer_score:
        status = 'win'
        payout = bet * 2
    elif player_score == dealer_score:
        status = 'push'
        payout = bet
    else:
        status = 'loss'
        payout = 0
        
    payout = round(payout, 4 if currency == 'ton' else 1)
    
    if payout > 0:
        _add_balance(user_data, currency, payout)
        
    stats['games_played'] += 1
    stats['total_bet'] += bet
    stats['total_paid_out'] += payout
    if status in ['win', 'dealer_bust']:
        stats['wins'] += 1
        if payout > stats['biggest_win']:
            stats['biggest_win'] = payout
    elif status == 'loss':
        stats['losses'] += 1
        
    user_data['miniapp_blackjack'] = None
    record_game_event(tg_user.id, 'blackjack', bet, payout, currency, won=(status in ['win', 'dealer_bust']))
    db.save_data()
    
    return {
        'ok': True,
        'player_hand': player_hand,
        'player_score': player_score,
        'dealer_hand': dealer_hand,
        'dealer_score': dealer_score,
        'status': status,
        'payout': payout,
        'profile': _serialize_profile(tg_user.id)
    }

@app.post('/api/games/blackjack/stand')
def blackjack_stand(payload: BlackjackActionIn):
    tg_user, user_data = _require_user(payload.init_data)
    
    session = user_data.get('miniapp_blackjack')
    if not session:
        _error(400, 'Игра Блэкджек не начата')
        
    stats = db.game_stats.setdefault('blackjack', {'games_played': 0, 'wins': 0, 'losses': 0, 'total_bet': 0.0, 'total_paid_out': 0.0, 'biggest_win': 0.0})
    return play_dealer_turn(session, stats, user_data, tg_user)

@app.post('/api/games/blackjack/double')
def blackjack_double(payload: BlackjackActionIn):
    tg_user, user_data = _require_user(payload.init_data)
    
    session = user_data.get('miniapp_blackjack')
    if not session:
        _error(400, 'Игра Блэкджек не начата')
        
    if len(session['player_hand']) != 2:
        _error(400, 'Удвоить ставку можно только первым ходом')
        
    bet = session['bet']
    _sub_balance_checked(user_data, session['currency'], bet)
    
    session['bet'] = bet * 2
    session['doubled'] = True
    
    deck = session['deck']
    if not deck:
        _error(500, 'Колода пуста')
        
    session['player_hand'].append(deck.pop())
    player_score = calculate_hand_score(session['player_hand'])
    
    stats = db.game_stats.setdefault('blackjack', {'games_played': 0, 'wins': 0, 'losses': 0, 'total_bet': 0.0, 'total_paid_out': 0.0, 'biggest_win': 0.0})
    
    if player_score > 21:
        stats['games_played'] += 1
        stats['total_bet'] += session['bet']
        stats['losses'] += 1
        
        user_data['miniapp_blackjack'] = None
        record_game_event(tg_user.id, 'blackjack', session['bet'], 0, session['currency'], won=False)
        db.save_data()
        
        return {
            'ok': True,
            'player_hand': session['player_hand'],
            'player_score': player_score,
            'dealer_hand': session['dealer_hand'],
            'dealer_score': calculate_hand_score(session['dealer_hand']),
            'status': 'bust',
            'payout': 0,
            'profile': _serialize_profile(tg_user.id)
        }
        
    return play_dealer_turn(session, stats, user_data, tg_user)


@app.get('/api/games/upgrade/targets')
def get_upgrade_targets():
    return {
        'ok': True,
        'targets': _get_case_nft_catalog(),
    }


@app.post('/api/games/upgrade/play')
def play_upgrade(payload: UpgradePlayIn):
    tg_user, user_data = _require_user(payload.init_data)
    
    catalog = _get_case_nft_catalog()
    target_model = str(payload.target_model or '').strip().lower()
    target_item = next((item for item in catalog if item.get('model') == target_model), None)
    if not target_item:
        _error(400, 'Выбранный подарок для апгрейда не найден')
        
    target_value = int(_gift_stars_price_for_item(target_item))
    if target_value <= 0:
        _error(400, 'Некорректная стоимость целевого подарка')
        
    mode = str(payload.mode or 'stars').lower()
    bet_value = 0.0
    gift_id = None
    bet_nft_item = None
    
    if mode == 'inventory':
        gift_id = str(payload.gift_id or '').strip()
        if not gift_id:
            _error(400, 'Не выбран NFT из инвентаря')
        inventory = user_data.setdefault('miniapp_inventory', [])
        bet_nft_item = next((x for x in inventory if str(x.get('id') or '') == gift_id), None)
        if not bet_nft_item:
            _error(404, 'NFT из инвентаря не найден')
        for transaction in db.transactions:
            if int(transaction.get('user_id', 0) or 0) == tg_user.id and transaction.get('type') == 'gift_withdraw':
                if str(transaction.get('gift_id') or '') == gift_id and str(transaction.get('status') or '').lower() == 'pending':
                    _error(400, 'Этот NFT находится в процессе вывода')
        bet_value = float(_gift_stars_price_for_item(bet_nft_item))
        if bet_value <= 0:
            _error(400, 'Некорректная стоимость выбранного NFT')
    elif mode == 'stars':
        amount = round(float(payload.stars_amount or 0), 1)
        if amount < 5:
            _error(400, 'Минимальная ставка — 5 звёзд')
        if amount > 10000:
            _error(400, 'Максимальная ставка — 10 000 звёзд')
        bet_value = amount
    else:
        _error(400, 'Неизвестный тип ставки')
        
    if bet_value >= target_value:
        _error(400, f'Цель апгрейда ({target_value} ⭐) должна быть дороже вашей ставки ({bet_value} ⭐)')
        
    # Deduct bet
    if mode == 'stars':
        _sub_balance_checked(user_data, 'stars', bet_value)
    elif mode == 'inventory':
        user_data['miniapp_inventory'] = [x for x in user_data.get('miniapp_inventory', []) if str(x.get('id') or '') != gift_id]
        
    # Calculate win chance: реальный шанс и выбор максимального шанса при RTP
    real_chance = (bet_value / target_value) * 100.0
    rtp_factor = _get_game_rtp_factor('upgrade')
    effective_chance = real_chance * rtp_factor
    win_chance_percent = max(1.0, min(95.0, round(effective_chance, 2)))
    
    # Roll random
    roll = round(random.random() * 100.0, 2)
    win = roll < win_chance_percent
    
    won_item = None
    payout = 0.0
    if win:
        won_item = {
            'id': uuid4().hex,
            'kind': 'gift',
            'label': target_item['label'],
            'name': target_item['name'],
            'model': target_item['model'],
            'value': target_value,
            'icon': target_item.get('icon', '🎁'),
            'rarity': get_rarity_by_stars(target_value),
            'createdAt': datetime.now().isoformat(),
        }
        user_data.setdefault('miniapp_inventory', []).insert(0, won_item)
        payout = float(target_value)
        
    # Stats
    user_stats = _get_user_game_stats(user_data, 'upgrade')
    global_stats = _get_global_game_stats('upgrade')
    user_stats['games_played'] += 1
    user_stats['total_bet'] += bet_value
    global_stats['games_played'] += 1
    global_stats['total_bet'] += bet_value
    if win:
        user_stats['wins'] += 1
        user_stats['total_paid_out'] += payout
        global_stats['wins'] += 1
        global_stats['total_paid_out'] += payout
    else:
        user_stats['losses'] += 1
        global_stats['losses'] += 1
    global_stats['net_profit'] = round(float(global_stats.get('total_bet', 0) or 0) - float(global_stats.get('total_paid_out', 0) or 0), 2)
    record_game_event(tg_user.id, 'upgrade', bet_value, payout, 'stars', won=win)
    db.save_data()
    
    return {
        'ok': True,
        'win': win,
        'roll': roll,
        'win_chance_percent': win_chance_percent,
        'bet_value': bet_value,
        'target_value': target_value,
        'target_item': target_item,
        'won_item': won_item,
        'profile': _serialize_profile_from_user(user_data),
        'games': _serialize_game_hub_from_user(user_data),
        'inventory': _serialize_inventory(user_data, tg_user.id),
    }


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT, reload=False)
