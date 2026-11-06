from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl

from config import TOKEN, WEBAPP_AUTH_MAX_AGE, ensure_required_settings


@dataclass(slots=True)
class TelegramMiniAppUser:
    id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str | None
    is_premium: bool = False
    start_param: str | None = None


class MiniAppAuthError(ValueError):
    pass



def validate_init_data(init_data: str) -> TelegramMiniAppUser:
    ensure_required_settings()
    if not init_data:
        raise MiniAppAuthError('Пустой initData')

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop('hash', None)
    if not received_hash:
        raise MiniAppAuthError('В initData нет hash')

    data_check_string = '\n'.join(f'{key}={value}' for key, value in sorted(pairs.items()))
    # Telegram Mini App validation uses HMAC-SHA256 with constant key WebAppData.
    secret_key = hmac.new(b'WebAppData', TOKEN.encode('utf-8'), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(received_hash, expected_hash):
        raise MiniAppAuthError('Невалидный initData')

    auth_date_raw = pairs.get('auth_date')
    try:
        auth_date = int(auth_date_raw or 0)
    except Exception as exc:
        raise MiniAppAuthError('Некорректный auth_date') from exc

    if auth_date <= 0:
        raise MiniAppAuthError('В initData отсутствует корректный auth_date')

    now = int(time.time())
    if auth_date > now + 60:
        raise MiniAppAuthError('auth_date из будущего')
    if WEBAPP_AUTH_MAX_AGE > 0 and (now - auth_date) > WEBAPP_AUTH_MAX_AGE:
        raise MiniAppAuthError('initData устарел')

    user_raw = pairs.get('user')
    if not user_raw:
        raise MiniAppAuthError('В initData нет user')

    try:
        user_data: dict[str, Any] = json.loads(user_raw)
    except Exception as exc:
        raise MiniAppAuthError('Не удалось разобрать user из initData') from exc

    return TelegramMiniAppUser(
        id=int(user_data['id']),
        username=user_data.get('username'),
        first_name=user_data.get('first_name'),
        last_name=user_data.get('last_name'),
        language_code=user_data.get('language_code'),
        is_premium=bool(user_data.get('is_premium', False)),
        start_param=pairs.get('start_param'),
    )
