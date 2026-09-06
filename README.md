# Ai VPN — Telegram Bot

Асинхронный Telegram-бот на **aiogram 3.x** для сервиса Ai VPN.
Хранилище — SQLite (через `aiosqlite`), FSM — `aiogram.fsm` со стандартным `MemoryStorage`
(можно заменить на `RedisStorage` в проде).

## Структура проекта

```
vpn/
├── assets/                     # баннеры разделов
│   ├── start_profile.jpg       # /start — "Профиль"
│   ├── support.jpg             # "Поддержка" + /support
│   ├── about.jpg                # "О сервисе"
│   ├── balance.jpg              # "Пополнить баланс"
│   └── subscription.jpg         # "Купить подписку"
├── bot/
│   ├── config.py                 # чтение .env
│   ├── database.py               # инициализация БД + все SQL-запросы (Database class)
│   ├── states.py                  # FSM состояния
│   ├── keyboards/
│   │   ├── main_menu.py
│   │   ├── free_trial.py
│   │   ├── subscription.py
│   │   ├── payment.py
│   │   ├── balance.py
│   │   ├── referral.py
│   │   └── support.py
│   ├── utils/
│   │   └── texts.py               # все текстовые константы
│   ├── handlers/
│   │   ├── start.py                # /start, главное меню, "О сервисе"
│   │   ├── free_trial.py           # бесплатный час + проверка подписки на канал
│   │   ├── subscription.py         # тарифы, скидка 30%, подарить VPN, оплата (скелет)
│   │   ├── balance.py              # пополнение баланса (FSM), история операций
│   │   ├── referral.py             # реферальная система целиком
│   │   └── support.py              # тикеты (FSM), /support
│   └── main.py                     # точка входа, Dispatcher, регистрация роутеров
├── requirements.txt
├── .env.example
└── README.md
```

## Установка

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # заполнить своими значениями
python -m bot.main
```

## Что нужно подготовить для .env

| Переменная | Откуда взять | Зачем |
|---|---|---|
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) | токен самого бота |
| `CHANNEL_ID` | `@username` или числовой id канала | канал, на который проверяется подписка для бесплатного часа |
| `CHANNEL_URL` | ссылка вида `https://t.me/MyAiVPN` | кнопка "Подписаться" |
| `ADMIN_IDS` | твой Telegram user_id (через запятую, если несколько) | уведомления о новых тикетах/платежах |
| `CRYPTOBOT_API_TOKEN` | [@CryptoBot](https://t.me/CryptoBot) → Crypto Pay App → Create App | оплата криптовалютой (Crypto Pay API) |
| `YOOKASSA_SHOP_ID` | Личный кабинет ЮKassa → Настройки → API | приём карт и СБП через ЮKassa |
| `YOOKASSA_SECRET_KEY` | Личный кабинет ЮKassa → Настройки → API | секретный ключ ЮKassa |
| `SBERPAY_TERMINAL_KEY` / `SBERPAY_SECRET_KEY` | Личный кабинет Сбербанк Эквайринг | если СБП/карты проводятся не через ЮKassa, а напрямую через Сбер |
| `TELEGRAM_PROVIDER_TOKEN_STARS` | не нужен отдельно — Stars встроены в Bot API (`XTR`) через `send_invoice` | оплата Telegram Stars |
| `DATABASE_PATH` | локальный путь, например `bot.db` | файл SQLite |

Реальные значения токенов я не подставляю в код — впиши их только в свой `.env`,
который не должен попадать в git (см. `.gitignore`).

## Важное про оплату

В коде оставлены **рабочие точки интеграции** (`bot/handlers/subscription.py`,
`bot/handlers/balance.py`) с понятной структурой, куда подключаются реальные вызовы
CryptoBot API / YooKassa API / Bot API `send_invoice` (для Stars и СБП через ЮKassa-провайдера).
Полная реализация вебхуков платёжных систем требует поднятого HTTPS-эндпоинта
(aiohttp/FastAPI) — это отдельный сервис, вынесенный за рамки основного бота,
чтобы не блокировать polling. Если нужно — могу дописать отдельный `payments/webhook_server.py`.
