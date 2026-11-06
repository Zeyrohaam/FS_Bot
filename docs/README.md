# Freaking Stars + Telegram Mini App

Готовая версия исходного бота с добавленным Mini App и HTTP API.

## Что добавлено

- `miniapp/miniapp_backend.py` — FastAPI-бэкенд для Telegram Mini App.
- `miniapp/webapp/` — фронтенд Mini App.
- `handlers/miniapp.py` — команда `/app` с кнопкой открытия приложения.
- `.env.example` — все секреты и настройки вынесены в переменные окружения.

## Что умеет Mini App

- просмотр профиля, баланса Stars и TON;
- покупка Stars;
- покупка Telegram Premium;
- покупка TON;
- отправка чеков админам прямо из приложения;
- активация промокодов;
- заявки на вывод Stars / TON;
- поддержка и предложения;
- история транзакций.

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Заполните `.env`, затем запустите:

```bash
python main.py
```

и во втором процессе:

```bash
python -m miniapp.miniapp_backend
```

## Настройка Telegram Mini App

1. Разверните бэкенд по HTTPS.
2. Укажите публичный URL в `WEBAPP_URL`.
3. Откройте бота и используйте `/app`.
4. При желании задайте menu button или Main Mini App через BotFather.

## Маршруты

- `GET /` — фронтенд Mini App.
- `GET /api/bootstrap` — загрузка профиля и цен.
- `POST /api/orders/*` — создание и превью заказов.
- `POST /api/proof/upload` — загрузка чека.
- `POST /api/promo/apply` — активация промокода.
- `POST /api/support/create` — поддержка / предложения.
- `POST /api/withdraw/create` — заявка на вывод.

## Важно

- В архив не включены старые токены, реальные карты, кошельки и база пользователей.
- Все данные оплаты и модерации продолжают идти в тот же админ-чат, который вы укажете в `.env`.
- Подтверждение/отклонение заявок работает через существующие callback-кнопки в самом боте.


## Настройка теперь через `config.py`

Основные поля для запуска:
- `BOT_TOKEN`
- `ADMIN_IDS_RAW`
- `ADMIN_CHAT_ID`
- `MONO_CARD`
- `TON_ADDRESS`
- `REVIEWS_CHANNEL`
- `SUPPORT_USERNAME`
- `REQUIRED_CHANNELS_RAW`

### Cloudflare

Есть 2 режима:

1. `CLOUDFLARE_MODE = 'quick'`
   - для бесплатного тестового `trycloudflare.com`
   - сначала запусти backend
   - потом `scripts/start_cloudflare_quick.bat`
   - после запуска cloudflared возьми выданный URL и вставь его в `CLOUDFLARE_QUICK_TUNNEL_URL`

2. `CLOUDFLARE_MODE = 'custom'`
   - для своего домена/субдомена в Cloudflare
   - укажи `CLOUDFLARE_CUSTOM_DOMAIN = 'https://app.example.com'`
   - `WEBAPP_URL` соберётся автоматически как `/webapp`

Если Cloudflare пока не настроен, можно временно использовать локальный URL через `WEBAPP_FALLBACK_URL`.
