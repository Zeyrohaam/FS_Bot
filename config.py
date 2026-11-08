from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / '.env'



def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(ENV_PATH)


# ==============================
# ТЕСТОВАЯ АРХИТЕКТУРА
# ==============================
TEST = {
    'bot_token': os.getenv('TEST_TOKEN', os.getenv('TEST_BOT_TOKEN', '')),
    'admin_ids': [1374629431, 1037149255],
    'admin_chat_id': -5230075957,
    'bot_username': '@grbrbfsbsBot',
    'reviews_channel': '@OTZ_test',
    'support_username': '@Zeyrohaam_da',
    'required_channels': ['@FreakingStarsChannel'],
    'premium_seller_username': '@Zeyrohaam_da',
    'mono_card': '4874 0700 5815 3352',
    'ton_address': 'UQCnwslHYMscJhQL5C2rDLXESCR9-O_6FkXksNWJkRaTDtqG',
}

# ==============================
# ПРОДОВАЯ АРХИТЕКТУРА
# ==============================
PROD = {
    'bot_token': os.getenv('BOT_TOKEN', os.getenv('PROD_BOT_TOKEN', '')),
    'admin_ids': [1374629431, 1037149255],
    'admin_chat_id': -1003735271617,
    'bot_username': '@FreakingStars_Bot',
    'reviews_channel': '@FreakingStarsOtz',
    'support_username': '@Zeyrohaam_da',
    'required_channels': ['@FreakingStarsChannel'],
    'premium_seller_username': '@Zeyrohaam_da',
    'mono_card': '4874 0700 5815 3352',
    'ton_address': 'UQCnwslHYMscJhQL5C2rDLXESCR9-O_6FkXksNWJkRaTDtqG',
}

MODE_DEFAULTS = {
    'test': TEST,
    'prod': PROD,
}
#Режим роботы
APP_MODE = 'test'

# Mini App / backend
BACKEND_HOST = os.getenv('BACKEND_HOST', '0.0.0.0')
BACKEND_PORT = 8080
WEBAPP_AUTH_MAX_AGE = 3600

# Cloudflare режимы:
# none   -> Mini App открывается по WEBAPP_FALLBACK_URL
# quick  -> бесплатный тестовый trycloudflare.com, URL выдаёт cloudflared; вставь его в CLOUDFLARE_QUICK_TUNNEL_URL
# custom -> свой домен/субдомен в Cloudflare, например app.example.com
CLOUDFLARE_MODE = 'quick'  # 'none', 'quick', 'custom'
CLOUDFLARE_QUICK_TUNNEL_URL = ''
CLOUDFLARE_CUSTOM_DOMAIN = ''
_fallback_host = '127.0.0.1' if BACKEND_HOST in {'0.0.0.0', '::', ''} else BACKEND_HOST
WEBAPP_FALLBACK_URL = f'http://{_fallback_host}:{BACKEND_PORT}/webapp'

# START_ALL.bat сам получает quick tunnel URL и пишет его в этот файл.
# Обычно сюда ничего руками вписывать не нужно.
CLOUDFLARE_QUICK_TUNNEL_FILE = BASE_DIR / 'var' / 'cloudflare_quick_url.txt'

# Цены
STARS_PRICES = {
    50: 36.5,
    100: 73,
    150: 107,
    200: 143,
    250: 179,
    500: 346,
}
PREMIUM_PRICES = {
    1: 140,
    3: 610,
    6: 780,
    12: 1370,
}
PREMIUM_COST_PRICES = {
    1: 115,
    3: 530,
    6: 708,
    12: 1285,
}

GAMES_SETTINGS = {
    'mines': {
        'grid_size': 4,
        'mines_count': 5,
        'min_bet': 5,
        'max_bet': 10000,
        'multipliers': [1.09, 1.24, 1.39, 1.58, 1.84, 2.04, 2.32, 2.89, 3.54, 4.26, 5.11],
    },
    'crash': {
        'min_bet': 5,
        'max_bet': 10000,
        'min_x': 1.01,
        'max_x': 9.88,
        'target_rtp': 0.90,
    },
    'dice': {
        'min_bet': 5,
        'max_bet': 10000,
        'rounds_options': [1, 3, 5],
        'small_bank_commission': 0.05,
        'large_bank_commission': 0.01,
        'small_bank_threshold': 99,
    },
    'roulette': {
        'min_bet': 5,
        'max_bet': 10000,
        'green_payout': 14,
    },
    'coin': {
        'min_bet': 5,
        'max_bet': 10000,
        'odds': {
            'eagle': 45.0,
            'tails': 45.0,
            'edge': 10.0,
        },
        'multipliers': {
            'eagle': 2.0,
            'tails': 2.0,
            'edge': 5.0,
        },
    },
    'cases': {
        'basic': {
            'label': 'Деревянный кейс',
            'cost': 100,
            'min_reward': 20,
            'max_reward': 150,
            'return_to_pay': 0.76,
        },
        'silver': {
            'label': 'Серебряный кейс',
            'cost': 280,
            'min_reward': 70,
            'max_reward': 320,
            'return_to_pay': 0.71,
        },
        'gold': {
            'label': 'Алмазный кейс',
            'cost': 720,
            'min_reward': 200,
            'max_reward': 780,
            'return_to_pay': 0.64,
        },
    },
}




def _parse_int_list(value, default: list[int] | None = None) -> list[int]:
    if isinstance(value, list):
        result: list[int] = []
        for item in value:
            try:
                result.append(int(item))
            except Exception:
                continue
        return result or list(default or [])
    if not value:
        return list(default or [])
    result: list[int] = []
    for item in str(value).split(','):
        item = item.strip()
        if not item:
            continue
        try:
            result.append(int(item))
        except ValueError:
            continue
    return result or list(default or [])



def _parse_str_list(value, default: list[str] | None = None) -> list[str]:
    if isinstance(value, list):
        result = [str(item).strip() for item in value if str(item).strip()]
        return result or list(default or [])
    if not value:
        return list(default or [])
    return [item.strip() for item in str(value).split(',') if item.strip()] or list(default or [])



def _parse_json(value, default):
    if not value:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _parse_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}



def _normalize_base_url(value: str) -> str:
    value = (value or '').strip().rstrip('/')
    if not value:
        return ''
    if value.startswith('http://') or value.startswith('https://'):
        return value
    return f'https://{value}'



def _read_quick_tunnel_url_from_file(path: Path) -> str:
    try:
        value = path.read_text(encoding='utf-8').strip()
        url = _normalize_base_url(value)
        if 'api.trycloudflare.com' in url.lower():
            return ''
        return url
    except Exception:
        return ''


APP_MODE = (os.getenv('APP_MODE') or APP_MODE).strip().lower()
if APP_MODE not in {'test', 'prod'}:
    APP_MODE = 'test'
TEST = APP_MODE == 'test'


def _resolve_mode_value(mode: str, key: str, default):
    env_key = f'{mode.upper()}_{key.upper()}'
    raw_value = os.getenv(env_key)
    if raw_value is None or raw_value == '':
        return default

    if key == 'admin_ids':
        return _parse_int_list(raw_value, list(default or []))
    if key == 'required_channels':
        return _parse_str_list(raw_value, list(default or []))
    if key == 'admin_chat_id':
        return int(raw_value)
    return str(raw_value)


MODE_SETTINGS = {}
for mode in ('test', 'prod'):
    defaults = MODE_DEFAULTS[mode]
    MODE_SETTINGS[mode] = {
        'bot_token': _resolve_mode_value(mode, 'bot_token', defaults['bot_token']),
        'admin_ids': _resolve_mode_value(mode, 'admin_ids', defaults['admin_ids']),
        'admin_chat_id': _resolve_mode_value(mode, 'admin_chat_id', defaults['admin_chat_id']),
        'bot_username': _resolve_mode_value(mode, 'bot_username', defaults['bot_username']),
        'reviews_channel': _resolve_mode_value(mode, 'reviews_channel', defaults['reviews_channel']),
        'support_username': _resolve_mode_value(mode, 'support_username', defaults['support_username']),
        'required_channels': _resolve_mode_value(mode, 'required_channels', defaults['required_channels']),
        'premium_seller_username': _resolve_mode_value(mode, 'premium_seller_username', defaults['premium_seller_username']),
        'mono_card': _resolve_mode_value(mode, 'mono_card', defaults['mono_card']),
        'ton_address': _resolve_mode_value(mode, 'ton_address', defaults['ton_address']),
    }

ACTIVE_MODE = 'test' if TEST else 'prod'
ACTIVE_SETTINGS = MODE_SETTINGS[ACTIVE_MODE]

BOT_TOKEN = ACTIVE_SETTINGS['bot_token']
TEST_TOKEN = MODE_SETTINGS['test']['bot_token']
TOKEN = BOT_TOKEN if not TEST else TEST_TOKEN
ADMIN_IDS = list(ACTIVE_SETTINGS['admin_ids'])
ADMIN_CHAT_ID = int(ACTIVE_SETTINGS['admin_chat_id'])
BOT_USERNAME = ACTIVE_SETTINGS['bot_username']
REVIEWS_CHANNEL = ACTIVE_SETTINGS['reviews_channel']
SUPPORT_USERNAME = ACTIVE_SETTINGS['support_username']
REQUIRED_CHANNELS = list(ACTIVE_SETTINGS['required_channels'])
PREMIUM_SELLER_USERNAME = ACTIVE_SETTINGS['premium_seller_username']
MONO = ACTIVE_SETTINGS['mono_card']
TON = ACTIVE_SETTINGS['ton_address']

BACKEND_HOST = str(os.getenv('BACKEND_HOST') or BACKEND_HOST or '0.0.0.0')
BACKEND_PORT = int(BACKEND_PORT or os.getenv('BACKEND_PORT', '8090') or 8090)
WEBAPP_AUTH_MAX_AGE = int(WEBAPP_AUTH_MAX_AGE or os.getenv('WEBAPP_AUTH_MAX_AGE', '3600') or 3600)
CLOUDFLARE_MODE = str(CLOUDFLARE_MODE or os.getenv('CLOUDFLARE_MODE', 'none')).strip().lower()
CLOUDFLARE_QUICK_TUNNEL_URL = _normalize_base_url(CLOUDFLARE_QUICK_TUNNEL_URL or os.getenv('CLOUDFLARE_QUICK_TUNNEL_URL', ''))
CLOUDFLARE_CUSTOM_DOMAIN = _normalize_base_url(CLOUDFLARE_CUSTOM_DOMAIN or os.getenv('CLOUDFLARE_CUSTOM_DOMAIN', ''))
_runtime_fallback_host = '127.0.0.1' if BACKEND_HOST in {'0.0.0.0', '::', ''} else BACKEND_HOST
WEBAPP_FALLBACK_URL = _normalize_base_url(WEBAPP_FALLBACK_URL or os.getenv('WEBAPP_FALLBACK_URL', f'http://{_runtime_fallback_host}:{BACKEND_PORT}/webapp'))

if not CLOUDFLARE_QUICK_TUNNEL_URL and CLOUDFLARE_QUICK_TUNNEL_FILE:
    CLOUDFLARE_QUICK_TUNNEL_URL = _read_quick_tunnel_url_from_file(Path(CLOUDFLARE_QUICK_TUNNEL_FILE))

if CLOUDFLARE_MODE == 'custom' and CLOUDFLARE_CUSTOM_DOMAIN:
    WEBAPP_URL = CLOUDFLARE_CUSTOM_DOMAIN.rstrip('/') + '/webapp'
elif CLOUDFLARE_MODE == 'quick' and CLOUDFLARE_QUICK_TUNNEL_URL:
    WEBAPP_URL = CLOUDFLARE_QUICK_TUNNEL_URL.rstrip('/') + '/webapp'
else:
    WEBAPP_URL = WEBAPP_FALLBACK_URL.rstrip('/')


def get_current_webapp_url() -> str:
    global WEBAPP_URL, CLOUDFLARE_QUICK_TUNNEL_URL
    if CLOUDFLARE_MODE == 'quick' and CLOUDFLARE_QUICK_TUNNEL_FILE:
        file_url = _read_quick_tunnel_url_from_file(Path(CLOUDFLARE_QUICK_TUNNEL_FILE))
        if file_url:
            CLOUDFLARE_QUICK_TUNNEL_URL = file_url
            WEBAPP_URL = CLOUDFLARE_QUICK_TUNNEL_URL.rstrip('/') + '/webapp'
    return WEBAPP_URL

STARS_PRICES = _parse_json(STARS_PRICES or os.getenv('STARS_PRICES_JSON', ''), STARS_PRICES)
PREMIUM_PRICES = _parse_json(PREMIUM_PRICES or os.getenv('PREMIUM_PRICES_JSON', ''), PREMIUM_PRICES)
PREMIUM_COST_PRICES = _parse_json(PREMIUM_COST_PRICES or os.getenv('PREMIUM_COST_PRICES_JSON', ''), PREMIUM_COST_PRICES)
GAMES_SETTINGS = _parse_json(GAMES_SETTINGS or os.getenv('GAMES_SETTINGS_JSON', ''), GAMES_SETTINGS)



def ensure_required_settings() -> None:
    if not TOKEN:
        missing_key = 'TEST_TOKEN' if TEST else 'BOT_TOKEN'
        raise RuntimeError(f'{missing_key} не задан. Открой config.py и заполни {missing_key}.')


RUNTIME_SETTINGS_PATH = BASE_DIR / 'data' / 'bot_runtime_settings.json'
RUNTIME_SETTING_KEYS = {
    'admin_ids', 'admin_chat_id', 'bot_username', 'reviews_channel', 'support_username',
    'required_channels', 'premium_seller_username', 'mono_card', 'ton_address',
}
RUNTIME_MODULE_TARGETS = {
    'handlers.payments': {
        'ADMIN_CHAT_ID': 'admin_chat_id', 'REVIEWS_CHANNEL': 'reviews_channel',
        'SUPPORT_USERNAME': 'support_username', 'PREMIUM_SELLER_USERNAME': 'premium_seller_username',
        'MONO': 'mono_card', 'TON': 'ton_address',
    },
    'handlers.reviews': {'REVIEWS_CHANNEL': 'reviews_channel'},
    'handlers.support': {'SUPPORT_USERNAME': 'support_username'},
    'handlers.user': {'MONO': 'mono_card'},
    'miniapp.miniapp_backend': {
        'ADMIN_CHAT_ID': 'admin_chat_id', 'BOT_USERNAME': 'bot_username',
        'REVIEWS_CHANNEL': 'reviews_channel', 'SUPPORT_USERNAME': 'support_username',
        'PREMIUM_SELLER_USERNAME': 'premium_seller_username', 'MONO': 'mono_card', 'TON': 'ton_address',
    },
}


def get_managed_settings() -> dict:
    return {
        'mode': APP_MODE,
        'admin_ids': list(ADMIN_IDS),
        'admin_chat_id': int(ADMIN_CHAT_ID),
        'bot_username': str(BOT_USERNAME),
        'reviews_channel': str(REVIEWS_CHANNEL),
        'support_username': str(SUPPORT_USERNAME),
        'required_channels': list(REQUIRED_CHANNELS),
        'premium_seller_username': str(PREMIUM_SELLER_USERNAME),
        'mono_card': str(MONO),
        'ton_address': str(TON),
        'token_change_requires_restart': True,
    }


def normalize_managed_settings(values: dict) -> dict:
    if not isinstance(values, dict) or set(values) - RUNTIME_SETTING_KEYS:
        raise ValueError('Переданы неподдерживаемые настройки')

    normalized = {}
    if 'admin_ids' in values:
        if not isinstance(values['admin_ids'], list):
            raise ValueError('Список администраторов задан неверно')
        try:
            admin_ids = list(dict.fromkeys(int(value) for value in values['admin_ids']))
        except (TypeError, ValueError):
            raise ValueError('ID администраторов должны быть целыми числами') from None
        if not admin_ids or any(value <= 0 for value in admin_ids):
            raise ValueError('Нужен хотя бы один положительный ID администратора')
        normalized['admin_ids'] = admin_ids

    if 'admin_chat_id' in values:
        try:
            chat_id = int(values['admin_chat_id'])
        except (TypeError, ValueError):
            raise ValueError('ID чата должен быть целым числом') from None
        if chat_id == 0:
            raise ValueError('ID чата не может быть равен нулю')
        normalized['admin_chat_id'] = chat_id

    if 'required_channels' in values:
        if not isinstance(values['required_channels'], list):
            raise ValueError('Список обязательных каналов задан неверно')
        channels = [str(value).strip() for value in values['required_channels'] if str(value).strip()]
        normalized['required_channels'] = list(dict.fromkeys(
            channel if channel.startswith('@') else f'@{channel}' for channel in channels
        ))

    string_fields = RUNTIME_SETTING_KEYS - {'admin_ids', 'admin_chat_id', 'required_channels'}
    for field in string_fields & values.keys():
        value = str(values[field]).strip()
        if len(value) > 500:
            raise ValueError('Слишком длинное значение настройки')
        if field in {'bot_username', 'reviews_channel', 'support_username', 'premium_seller_username'} and value and not value.startswith('@'):
            value = f'@{value}'
        normalized[field] = value
    return normalized


def apply_managed_settings(values: dict) -> dict:
    normalized = normalize_managed_settings(values)
    for key, value in normalized.items():
        if key == 'admin_ids':
            ADMIN_IDS[:] = value
        elif key == 'required_channels':
            REQUIRED_CHANNELS[:] = value
        elif key == 'admin_chat_id':
            globals()['ADMIN_CHAT_ID'] = value
        elif key == 'bot_username':
            globals()['BOT_USERNAME'] = value
        elif key == 'reviews_channel':
            globals()['REVIEWS_CHANNEL'] = value
        elif key == 'support_username':
            globals()['SUPPORT_USERNAME'] = value
        elif key == 'premium_seller_username':
            globals()['PREMIUM_SELLER_USERNAME'] = value
        elif key == 'mono_card':
            globals()['MONO'] = value
        elif key == 'ton_address':
            globals()['TON'] = value

    current = get_managed_settings()
    for module_name, attributes in RUNTIME_MODULE_TARGETS.items():
        module = sys.modules.get(module_name)
        if module is not None:
            for attribute, key in attributes.items():
                setattr(module, attribute, current[key])
    return current


def load_managed_settings() -> dict:
    try:
        saved = json.loads(RUNTIME_SETTINGS_PATH.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return get_managed_settings()
    if not isinstance(saved, dict):
        return get_managed_settings()
    try:
        return apply_managed_settings(saved)
    except ValueError:
        return get_managed_settings()


def save_managed_settings(values: dict) -> dict:
    normalized = normalize_managed_settings(values)
    current = get_managed_settings()
    current.update(normalized)
    RUNTIME_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=RUNTIME_SETTINGS_PATH.parent, delete=False) as tmp:
        json.dump({key: current[key] for key in RUNTIME_SETTING_KEYS}, tmp, ensure_ascii=False, indent=2)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, RUNTIME_SETTINGS_PATH)
    return apply_managed_settings(normalized)


load_managed_settings()
