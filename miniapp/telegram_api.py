from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

from config import TOKEN, ensure_required_settings

API_BASE = 'https://api.telegram.org'


def _method_url(method: str) -> str:
    ensure_required_settings()
    return f'{API_BASE}/bot{TOKEN}/{method}'



def send_message(chat_id: int | str, text: str, reply_markup: dict[str, Any] | None = None, parse_mode: str | None = 'HTML') -> dict[str, Any]:
    payload: dict[str, Any] = {'chat_id': str(chat_id), 'text': text}
    if parse_mode:
        payload['parse_mode'] = parse_mode
    if reply_markup:
        payload['reply_markup'] = reply_markup
    response = requests.post(_method_url('sendMessage'), json=payload, timeout=20)
    if not response.ok and parse_mode and "can't parse entities" in response.text:
        payload.pop('parse_mode', None)
        response = requests.post(_method_url('sendMessage'), json=payload, timeout=20)
    response.raise_for_status()
    return response.json()


def send_photo_bytes(
    chat_id: int | str,
    photo_bytes: bytes,
    filename: str = 'photo.jpg',
    caption: str = '',
    reply_markup: dict[str, Any] | None = None,
    parse_mode: str | None = 'HTML',
) -> dict[str, Any]:
    import json as json_module

    payload: dict[str, Any] = {'chat_id': str(chat_id), 'caption': (caption or '')[:1024]}
    if parse_mode:
        payload['parse_mode'] = parse_mode
    if reply_markup:
        payload['reply_markup'] = json_module.dumps(reply_markup)

    files = {'photo': (filename or 'photo.jpg', photo_bytes, 'image/jpeg')}
    response = requests.post(
        _method_url('sendPhoto'),
        data=payload,
        files=files,
        timeout=60,
    )
    if not response.ok and parse_mode and "can't parse entities" in response.text:
        payload.pop('parse_mode', None)
        files = {'photo': (filename or 'photo.jpg', photo_bytes, 'image/jpeg')}
        response = requests.post(
            _method_url('sendPhoto'),
            data=payload,
            files=files,
            timeout=60,
        )
    response.raise_for_status()
    return response.json()


def send_photo(chat_id: int | str, photo_path: str | Path, caption: str, reply_markup: dict[str, Any] | None = None) -> dict[str, Any]:
    path_obj = Path(photo_path)
    with path_obj.open('rb') as photo_file:
        return send_photo_bytes(
            chat_id=chat_id,
            photo_bytes=photo_file.read(),
            filename=path_obj.name,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode='HTML',
        )


def send_photo_url(chat_id: int | str, photo_url: str, caption: str, reply_markup: dict[str, Any] | None = None, parse_mode: str | None = 'HTML') -> dict[str, Any]:
    payload: dict[str, Any] = {'chat_id': str(chat_id), 'photo': photo_url, 'caption': (caption or '')[:1024]}
    if parse_mode:
        payload['parse_mode'] = parse_mode
    if reply_markup:
        payload['reply_markup'] = reply_markup

    response = requests.post(_method_url('sendPhoto'), json=payload, timeout=60)
    if not response.ok and parse_mode and "can't parse entities" in response.text:
        payload.pop('parse_mode', None)
        response = requests.post(_method_url('sendPhoto'), json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def download_telegram_file(file_id: str) -> tuple[bytes, str]:
    metadata_response = requests.get(_method_url('getFile'), params={'file_id': file_id}, timeout=20)
    metadata_response.raise_for_status()
    metadata = metadata_response.json()
    file_path = metadata.get('result', {}).get('file_path')
    if not file_path:
        raise ValueError('Telegram не вернул путь файла')

    file_url = f'{API_BASE}/file/bot{TOKEN}/{file_path}'
    file_response = requests.get(file_url, timeout=30)
    file_response.raise_for_status()
    content_type = file_response.headers.get('Content-Type', 'application/octet-stream').split(';', 1)[0]
    return file_response.content, content_type
