from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    MENU_BUTTON_TEXTS,
    cancel_kb,
    email_manage_kb,
    main_menu_kb,
)
from app.storage.database import async_session
from app.subscriptions.manager import (
    delete_user_email,
    get_or_create_user,
    get_user_email,
    set_user_email,
)

router = Router()


# ── /start ──────────────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session() as session:
        await get_or_create_user(session, message.from_user.id)

    await message.answer(
        "👋 Привет! Я бот для мониторинга научных публикаций.\n\n"
        "Я могу:\n"
        "• Искать статьи по ключевым словам, авторам и журналам\n"
        "• Генерировать краткие аннотации на русском языке\n"
        "• Присылать уведомления о новых статьях (Telegram + email)\n\n"
        "Используй кнопки ниже или /help",
        reply_markup=main_menu_kb(),
    )


# ── /cancel — universal FSM reset ──────────────────────────────────
@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    await state.clear()
    if current:
        await message.answer("❌ Действие отменено.", reply_markup=main_menu_kb())
    else:
        await message.answer("Нечего отменять.", reply_markup=main_menu_kb())


# ── /help ───────────────────────────────────────────────────────────
@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "<b>Команды:</b>\n"
        "/search — разовый поиск статей\n"
        "/subscribe — создать подписку на обновления\n"
        "/subscriptions — мои подписки\n"
        "/setemail — настроить email-уведомления\n"
        "/cancel — отменить текущее действие\n"
        "/help — помощь\n\n"
        "<b>Как работает:</b>\n"
        "1. Используй «Поиск статей» для разового поиска\n"
        "2. Создай подписку, чтобы получать уведомления о новых статьях\n"
        "3. Бот ищет на arXiv, Semantic Scholar, CrossRef и CyberLeninka\n"
        "4. Для каждой статьи генерируется аннотация на русском",
        parse_mode="HTML",
    )


# ── Email management ────────────────────────────────────────────────
class EmailForm(StatesGroup):
    waiting_email = State()


@router.message(Command("setemail"))
@router.message(F.text == "📧 Настроить email")
async def cmd_email(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session() as session:
        email = await get_user_email(session, message.from_user.id)

    if email:
        await message.answer(
            f"📧 Текущий email: <b>{email}</b>",
            parse_mode="HTML",
            reply_markup=email_manage_kb(),
        )
    else:
        await state.set_state(EmailForm.waiting_email)
        await message.answer(
            "📧 Email не задан. Отправь свой email-адрес:\n"
            "(или /cancel для отмены)",
            reply_markup=cancel_kb(),
        )


@router.callback_query(F.data == "email:change")
async def cb_email_change(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(EmailForm.waiting_email)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "📧 Отправь новый email-адрес:\n(или /cancel для отмены)",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "email:delete")
async def cb_email_delete(callback: CallbackQuery) -> None:
    async with async_session() as session:
        await delete_user_email(session, callback.from_user.id)
    await callback.message.edit_text(
        "✅ Email удалён. Уведомления будут приходить только в Telegram."
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("❌ Отменено.", reply_markup=main_menu_kb())
    await callback.answer()


# ── Email FSM: cancel on menu-button / command press ────────────────
@router.message(EmailForm.waiting_email, F.text.in_(MENU_BUTTON_TEXTS))
async def cancel_email_on_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("📧 Настройка email отменена.", reply_markup=main_menu_kb())


@router.message(EmailForm.waiting_email, F.text.startswith("/"))
async def cancel_email_on_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("📧 Настройка email отменена.", reply_markup=main_menu_kb())


@router.message(EmailForm.waiting_email)
async def process_email(message: Message, state: FSMContext) -> None:
    email = message.text.strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        await message.answer("⚠️ Неверный формат email. Попробуй ещё раз (или /cancel):")
        return

    async with async_session() as session:
        await set_user_email(session, message.from_user.id, email)

    await state.clear()
    await message.answer(
        f"✅ Email сохранён: {email}\nТеперь уведомления будут приходить и на почту.",
        reply_markup=main_menu_kb(),
    )
