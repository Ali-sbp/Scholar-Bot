# Интеллектуальная система мониторинга научных публикаций

Telegram-бот для поиска научных статей, генерации кратких аннотаций на русском языке и отслеживания новых публикаций по подпискам.

## Что умеет

- Ищет статьи по ключевым словам, авторам и журналам.
- Работает с `arXiv`, `Semantic Scholar`, `CrossRef` и `CyberLeninka`.
- Генерирует краткие аннотации на русском языке через Groq.
- Поддерживает разовый поиск и постоянные подписки.
- Отправляет уведомления в Telegram и по email.

## Команды бота

| Команда | Описание |
| --- | --- |
| `/start` | Регистрация пользователя и главное меню |
| `/search` | Разовый поиск статей |
| `/subscribe` | Создание подписки на новые публикации |
| `/subscriptions` | Просмотр, ручная проверка и удаление подписок |
| `/setemail` | Настройка email-уведомлений |
| `/cancel` | Отмена текущего действия |
| `/help` | Справка |

## Требования

- Python `3.11+`
- PostgreSQL `14+` для локального запуска
- Telegram Bot Token от [@BotFather](https://t.me/BotFather)
- Groq API key от [console.groq.com](https://console.groq.com)
- Опционально: Resend API key для email-уведомлений

## Переменные окружения

Пример находится в `.env.example`.

| Переменная | Обязательна | Назначение |
| --- | --- | --- |
| `BOT_TOKEN` | Да | Токен Telegram-бота |
| `GROQ_API_KEY` | Да | Ключ для генерации аннотаций |
| `DATABASE_URL` | Да | Подключение к PostgreSQL |
| `RESEND_API_KEY` | Нет | Ключ Resend для email-уведомлений |
| `EMAIL_FROM` | Нет | Адрес отправителя для Resend |

Если `RESEND_API_KEY` не задан, бот продолжит работать, но email-уведомления будут отключены.

Пример `DATABASE_URL` для локального запуска:

```env
DATABASE_URL=postgresql+asyncpg://scholar:scholar@localhost:5432/scholar_bot
```

## Локальный запуск

1. Перейдите в директорию проекта.
2. Создайте виртуальное окружение.
3. Установите зависимости.
4. Настройте `.env`.
5. Запустите приложение.

Перед запуском локально PostgreSQL должен быть уже доступен по `DATABASE_URL`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

При старте приложение автоматически создаёт таблицы в базе данных через SQLAlchemy.

## Запуск через Docker

`docker-compose.yml` поднимает PostgreSQL и контейнер с ботом. Для запуска достаточно заполнить `.env` и выполнить:

```bash
docker compose up --build
```

По умолчанию контейнер базы данных создаётся с параметрами:

- База данных: `scholar_bot`
- Пользователь: `scholar`
- Пароль: `scholar`

## Как это работает

1. Пользователь запускает бота и при необходимости указывает email.
2. Команда `/search` выполняет разовый поиск по выбранным фильтрам.
3. Команда `/subscribe` создаёт подписку с ключевыми словами, авторами, журналами, интервалом и языком.
4. Планировщик проверяет активные подписки каждые 30 минут и запускает поиск только для тех, у которых подошло время следующей проверки.
5. Найденные статьи сохраняются в PostgreSQL, для них создаются аннотации, после чего бот отправляет уведомления.

## Структура проекта

```text
app/
├── main.py                  # Точка входа и запуск scheduler
├── config.py                # Загрузка конфигурации из .env
├── bot/
│   ├── keyboards.py         # Клавиатуры и кнопки
│   └── handlers/            # Telegram handlers
├── search/                  # Источники и агрегатор поиска
├── llm/                     # Генерация аннотаций
├── subscriptions/           # Логика подписок и сохранения статей
├── scheduler/               # Фоновая проверка подписок
├── notifications/           # Telegram и email-уведомления
└── storage/                 # SQLAlchemy engine, session и ORM-модели
```

## База данных

Проект использует PostgreSQL. Схема описана ORM-моделями в `app/storage/models.py`.

Основные таблицы:

- `users`
- `subscriptions`
- `articles`
- `annotations`
- `subscription_articles`

## Стек

- `Python 3.11`
- `aiogram 3`
- `SQLAlchemy 2` + `asyncpg`
- `PostgreSQL`
- `APScheduler`
- `aiohttp` / `httpx`
- `Groq` (`llama-3.3-70b-versatile`)
- `Resend` для email-уведомлений
