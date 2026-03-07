from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# Texts on the main reply‑keyboard — used to detect when user presses
# a menu button while inside an FSM flow so we can cancel gracefully.
MENU_BUTTON_TEXTS = frozenset({
    "🔍 Поиск статей",
    "📌 Новая подписка",
    "📋 Мои подписки",
    "📧 Настроить email",
    "ℹ️ Помощь",
})


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Поиск статей"), KeyboardButton(text="📌 Новая подписка")],
            [KeyboardButton(text="📋 Мои подписки"), KeyboardButton(text="📧 Настроить email")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]]
    )


def email_manage_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить email", callback_data="email:change")],
            [InlineKeyboardButton(text="🗑 Удалить email", callback_data="email:delete")],
        ]
    )


def results_count_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="5", callback_data="count:5"),
                InlineKeyboardButton(text="10", callback_data="count:10"),
                InlineKeyboardButton(text="20", callback_data="count:20"),
            ]
        ]
    )


def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🌐 Любой", callback_data="lang:any"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
            ]
        ]
    )


def sort_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Новые", callback_data="sort:date"),
                InlineKeyboardButton(text="📊 Цитируемые", callback_data="sort:cited"),
                InlineKeyboardButton(text="🎯 Релевантные", callback_data="sort:relevance"),
            ]
        ]
    )


def skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip")]]
    )


def interval_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="6ч", callback_data="interval:6"),
                InlineKeyboardButton(text="12ч", callback_data="interval:12"),
                InlineKeyboardButton(text="24ч", callback_data="interval:24"),
            ]
        ]
    )


def subscription_actions_kb(sub_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Проверить сейчас", callback_data=f"check:{sub_id}"),
                InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete:{sub_id}"),
            ]
        ]
    )


def after_subscribe_kb(sub_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Искать сейчас", callback_data=f"searchnow:{sub_id}"),
                InlineKeyboardButton(text="⏭ Только уведомлять", callback_data=f"notifyonly:{sub_id}"),
            ]
        ]
    )
