# Интеллектуальная система мониторинга научных публикаций

Telegram-бот для автоматического поиска, аннотирования и мониторинга научных статей с использованием LLM.

## Возможности

- **Поиск статей** по ключевым словам, авторам, журналам из 4 источников (arXiv, Semantic Scholar, CrossRef, CyberLeninka)
- **Генерация аннотаций** — краткие описания на русском языке (1–2 предложения) через Groq (Llama 3.1 70B)
- **Подписки** — настраиваемые фильтры с автоматической проверкой по расписанию
- **Уведомления** — в Telegram и на email

## Структура проекта

```
app/
├── main.py                  # Точка входа
├── config.py                # Конфигурация из .env
├── bot/                     # Telegram-бот (aiogram 3)
│   ├── keyboards.py
│   └── handlers/
│       ├── start.py         # /start, /help, /setemail
│       ├── subscribe.py     # /subscribe — пошаговое создание подписки
│       └── subscriptions.py # /subscriptions — управление подписками
├── search/                  # Адаптеры источников статей
│   ├── base.py              # Базовый класс + ArticleData
│   ├── arxiv_source.py
│   ├── semantic_scholar.py
│   ├── crossref_source.py
│   ├── cyberleninka.py
│   └── aggregator.py        # Параллельный поиск + дедупликация
├── llm/
│   └── annotator.py         # Генерация аннотаций через Groq
├── subscriptions/
│   └── manager.py           # CRUD подписок, поиск + сохранение статей
├── scheduler/
│   └── tasks.py             # Периодическая проверка подписок
├── notifications/
│   ├── telegram_notify.py   # Уведомления в Telegram
│   └── email_notify.py      # Email-уведомления
└── storage/
    ├── database.py           # SQLAlchemy async engine + session
    └── models.py             # ORM-модели (User, Subscription, Article, Annotation)
```

## Быстрый старт

### 1. Требования

- Python 3.11+
- PostgreSQL 14+
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))
- Groq API Key (бесплатно: https://console.groq.com)

### 2. Установка

```bash
# Клонировать / перейти в директорию проекта
cd opd

# Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

### 3. Настройка

```bash
cp .env.example .env
# Заполнить .env реальными значениями:
#   BOT_TOKEN, GROQ_API_KEY, DATABASE_URL, SMTP_*
```

### 4. Запуск

```bash
# Локально (PostgreSQL должен быть запущен)
python -m app.main
```

Или через Docker:

```bash
docker compose up --build
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие + главное меню |
| `/subscribe` | Создать подписку (ключевые слова → авторы → журналы → интервал) |
| `/subscriptions` | Список подписок с кнопками «Проверить» / «Удалить» |
| `/setemail` | Указать email для уведомлений |
| `/help` | Справка |

## Как это работает

1. Пользователь создаёт подписку через `/subscribe`
2. Бот **сразу** ищет статьи по всем источникам и показывает результаты с аннотациями
3. Каждые 30 минут планировщик проверяет подписки, ищет новые статьи
4. Новые статьи с аннотациями отправляются в Telegram и на email (если указан)

## Стек

| Компонент | Технология |
|-----------|-----------|
| Язык | Python 3.11+ |
| Бот | aiogram 3 |
| БД | PostgreSQL + SQLAlchemy 2 (async) |
| LLM | Groq (Llama 3.1 70B) — бесплатный тариф |
| Планировщик | APScheduler |
| HTTP | aiohttp |
| Email | aiosmtplib |
