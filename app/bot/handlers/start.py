from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.bot.keyboards import main_menu_kb
from app.storage.database import async_session
from app.subscriptions.manager import get_or_create_user, set_user_email

router = Router()


# ── /start ──────────────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
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


# ── /help ───────────────────────────────────────────────────────────
@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>Команды:</b>\n"
        "/subscribe — создать подписку\n"
        "/subscriptions — мои подписки\n"
        "/setemail — настроить email-уведомления\n"
        "/help — помощь\n\n"
        "<b>Как работает:</b>\n"
        "1. Создай подписку с ключевыми словами\n"
        "2. Бот ищет статьи на arXiv, Semantic Scholar, CrossRef и CyberLeninka\n"
        "3. Для каждой статьи генерируется аннотация на русском\n"
        "4. Бот периодически проверяет новые статьи и присылает уведомления",
        parse_mode="HTML",
    )


# ── /setemail ───────────────────────────────────────────────────────
class EmailForm(StatesGroup):
    waiting_email = State()


@router.message(Command("setemail"))
@router.message(F.text == "📧 Настроить email")
async def cmd_setemail(message: Message, state: FSMContext) -> None:
    await state.set_state(EmailForm.waiting_email)
    await message.answer("📧 Отправь свой email-адрес для получения уведомлений:")


@router.message(EmailForm.waiting_email)
async def process_email(message: Message, state: FSMContext) -> None:
    email = message.text.strip()
    # Basic format check
    if "@" not in email or "." not in email.split("@")[-1]:
        await message.answer("⚠️ Неверный формат email. Попробуй ещё раз:")
        return

    async with async_session() as session:
        await set_user_email(session, message.from_user.id, email)

    await state.clear()
    await message.answer(
        f"✅ Email сохранён: {email}\nТеперь уведомления будут приходить и на почту.",
        reply_markup=main_menu_kb(),
    )
