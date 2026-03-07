from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Новая подписка"), KeyboardButton(text="📋 Мои подписки")],
            [KeyboardButton(text="📧 Настроить email"), KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
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
