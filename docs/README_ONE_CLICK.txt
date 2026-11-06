# One-click запуск

## Как использовать
1. Открой `config.py`
2. Заполни минимум:
   - `BOT_TOKEN`
   - `ADMIN_IDS_RAW`
   - `ADMIN_CHAT_ID`
   - `MONO_CARD`
   - `TON_ADDRESS`
3. Запускай только `START_ALL.bat`

## Что делает START_ALL.bat
- создаёт `.venv`, если его нет
- ставит зависимости из `requirements.txt`
- автоматически скачивает `cloudflared.exe`, если его нет
- запускает backend
- поднимает Cloudflare Quick Tunnel
- автоматически получает `https://*.trycloudflare.com`
- пишет URL в `var/cloudflare_quick_url.txt`
- запускает Telegram-бота

## Остановка
Запусти `STOP_ALL.bat`

## Где смотреть логи
Папка `var/logs/`:
- `backend.log`
- `cloudflared.log`
- `bot.log`

## Важно
- Quick Tunnel бесплатный, но адрес `trycloudflare.com` может меняться после перезапуска.
- Бот сам подхватит новый адрес, потому что `config.py` читает `var/cloudflare_quick_url.txt`.
- Для стабильного красивого домена нужен свой домен в Cloudflare.
- Лучше использовать Python 3.11 или 3.12.
