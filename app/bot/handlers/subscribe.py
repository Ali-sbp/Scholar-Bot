from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import interval_kb, main_menu_kb, skip_kb
from app.storage.database import async_session
from app.subscriptions.manager import create_subscription, get_or_create_user, search_and_store

router = Router()


class SubscribeForm(StatesGroup):
    keywords = State()
    authors = State()
    journals = State()
    interval = State()


# ── step 1: keywords ───────────────────────────────────────────────
@router.message(Command("subscribe"))
@router.message(F.text == "🔍 Новая подписка")
async def start_subscribe(message: Message, state: FSMContext) -> None:
    await state.set_state(SubscribeForm.keywords)
    await message.answer(
        "📝 Введи ключевые слова для поиска (через запятую):\n\n"
        "Например: <i>теория игр, game theory, Nash equilibrium</i>",
        parse_mode="HTML",
    )


@router.message(SubscribeForm.keywords)
async def process_keywords(message: Message, state: FSMContext) -> None:
    keywords = [k.strip() for k in message.text.split(",") if k.strip()]
    if not keywords:
        await message.answer("⚠️ Укажи хотя бы одно ключевое слово.")
        return
    await state.update_data(keywords=keywords)
    await state.set_state(SubscribeForm.authors)
    await message.answer("👤 Укажи авторов (через запятую), или пропусти:", reply_markup=skip_kb())


# ── step 2: authors ────────────────────────────────────────────────
@router.callback_query(SubscribeForm.authors, F.data == "skip")
async def skip_authors(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(authors=[])
    await state.set_state(SubscribeForm.journals)
    await callback.message.answer(
        "📰 Укажи журналы (через запятую), или пропусти:", reply_markup=skip_kb()
    )
    await callback.answer()


@router.message(SubscribeForm.authors)
async def process_authors(message: Message, state: FSMContext) -> None:
    authors = [a.strip() for a in message.text.split(",") if a.strip()]
    await state.update_data(authors=authors)
    await state.set_state(SubscribeForm.journals)
    await message.answer(
        "📰 Укажи журналы (через запятую), или пропусти:", reply_markup=skip_kb()
    )


# ── step 3: journals ───────────────────────────────────────────────
@router.callback_query(SubscribeForm.journals, F.data == "skip")
async def skip_journals(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(journals=[])
    await state.set_state(SubscribeForm.interval)
    await callback.message.answer("⏰ Как часто проверять новые статьи?", reply_markup=interval_kb())
    await callback.answer()


@router.message(SubscribeForm.journals)
async def process_journals(message: Message, state: FSMContext) -> None:
    journals = [j.strip() for j in message.text.split(",") if j.strip()]
    await state.update_data(journals=journals)
    await state.set_state(SubscribeForm.interval)
    await message.answer("⏰ Как часто проверять новые статьи?", reply_markup=interval_kb())


# ── step 4: interval → search → show results ───────────────────────
@router.callback_query(SubscribeForm.interval, F.data.startswith("interval:"))
async def process_interval(callback: CallbackQuery, state: FSMContext) -> None:
    hours = int(callback.data.split(":")[1])
    data = await state.get_data()
    await state.clear()

    await callback.message.answer("🔄 Ищу статьи… Это может занять некоторое время.")
    await callback.answer()

    async with async_session() as session:
        await get_or_create_user(session, callback.from_user.id)

        name = ", ".join(data["keywords"][:3])
        sub = await create_subscription(
            session,
            user_id=callback.from_user.id,
            name=name,
            keywords=data["keywords"],
            authors=data.get("authors", []),
            journals=data.get("journals", []),
            check_interval_hrs=hours,
        )

        results = await search_and_store(session, sub)

    if not results:
        await callback.message.answer(
            "😕 Статей пока не найдено. Подписка создана — бот проверит позже.",
            reply_markup=main_menu_kb(),
        )
        return

    # Build response
    header = (
        f"✅ Подписка создана! Найдено статей: {len(results)}\n"
        f"⏰ Проверка каждые {hours}ч\n\n"
    )
    chunks: list[str] = [header]
    for i, (article, annotation) in enumerate(results, 1):
        url = article.url if article.url.startswith(("http://", "https://")) else ""
        entry = f"{i}. <b>{escape(article.title)}</b>\n" f"   📝 {escape(annotation.text_ru)}\n"
        if url:
            entry += f'   🔗 <a href="{escape(url)}">Источник</a> ({escape(article.source)})\n\n'
        else:
            entry += f"   📎 {escape(article.source)}\n\n"

        if len("".join(chunks)) + len(entry) > 4000:
            await callback.message.answer(
                "".join(chunks), parse_mode="HTML", disable_web_page_preview=True
            )
            chunks = ["📚 Продолжение:\n\n"]
        chunks.append(entry)

    if chunks:
        await callback.message.answer(
            "".join(chunks),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=main_menu_kb(),
        )
