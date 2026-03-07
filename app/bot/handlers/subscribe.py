from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    MENU_BUTTON_TEXTS,
    after_subscribe_kb,
    interval_kb,
    language_kb,
    main_menu_kb,
    results_count_kb,
    skip_kb,
    sort_kb,
)
from app.storage.database import async_session
from app.subscriptions.manager import create_subscription, get_or_create_user, search_and_store

router = Router()


class SubscribeForm(StatesGroup):
    keywords = State()
    authors = State()
    journals = State()
    interval = State()
    language = State()


class SubSearchForm(StatesGroup):
    """Mini-FSM for the 'search now' flow after creating a subscription."""
    count = State()
    sort = State()


# ── step 1: keywords ───────────────────────────────────────────────
@router.message(Command("subscribe"))
@router.message(F.text.contains("Новая подписка"))
async def start_subscribe(message: Message, state: FSMContext) -> None:
    await state.set_state(SubscribeForm.keywords)
    await message.answer(
        "📝 Введи ключевые слова для поиска (через запятую):\n\n"
        "Например: <i>теория игр, game theory, Nash equilibrium</i>",
        parse_mode="HTML",
    )


# ── Cancel on menu-button / command during any SubscribeForm state ──
@router.message(SubscribeForm.keywords, F.text.in_(MENU_BUTTON_TEXTS))
@router.message(SubscribeForm.authors, F.text.in_(MENU_BUTTON_TEXTS))
@router.message(SubscribeForm.journals, F.text.in_(MENU_BUTTON_TEXTS))
async def cancel_sub_on_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("📌 Создание подписки отменено.", reply_markup=main_menu_kb())


@router.message(SubscribeForm.keywords, F.text.startswith("/"))
@router.message(SubscribeForm.authors, F.text.startswith("/"))
@router.message(SubscribeForm.journals, F.text.startswith("/"))
async def cancel_sub_on_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("📌 Создание подписки отменено.", reply_markup=main_menu_kb())


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


# ── step 4: interval → language ─────────────────────────────────────
@router.callback_query(SubscribeForm.interval, F.data.startswith("interval:"))
async def process_interval(callback: CallbackQuery, state: FSMContext) -> None:
    hours = int(callback.data.split(":")[1])
    await state.update_data(interval=hours)
    await state.set_state(SubscribeForm.language)
    await callback.message.answer("🌐 Язык статей для уведомлений?", reply_markup=language_kb())
    await callback.answer()


# ── step 5: language → create subscription ──────────────────────────
@router.callback_query(SubscribeForm.language, F.data.startswith("lang:"))
async def process_language(callback: CallbackQuery, state: FSMContext) -> None:
    lang = callback.data.split(":")[1]
    data = await state.get_data()
    await state.clear()

    await callback.answer()

    hours = data["interval"]

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
            language=lang,
        )

    lang_label = {"any": "Любой", "ru": "Русский", "en": "English"}.get(lang, lang)
    await callback.message.answer(
        f"✅ Подписка «{name}» создана!\n"
        f"⏰ Проверка каждые {hours}ч\n"
        f"🌐 Язык: {lang_label}\n\n"
        "Хочешь сразу найти статьи или просто получать уведомления о новых?",
        reply_markup=after_subscribe_kb(sub.id),
    )


# ── "search now" → prompt count → sort → execute ────────────────────
@router.callback_query(F.data.startswith("searchnow:"))
async def cb_search_now_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    sub_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.update_data(sub_id=sub_id)
    await state.set_state(SubSearchForm.count)
    await callback.message.answer(
        "📊 Сколько результатов на источник?", reply_markup=results_count_kb()
    )
    await callback.answer()


@router.callback_query(SubSearchForm.count, F.data.startswith("count:"))
async def subsearch_count(callback: CallbackQuery, state: FSMContext) -> None:
    count = int(callback.data.split(":")[1])
    await state.update_data(count=count)
    await state.set_state(SubSearchForm.sort)
    await callback.message.answer("📋 Сортировка результатов?", reply_markup=sort_kb())
    await callback.answer()


@router.callback_query(SubSearchForm.sort, F.data.startswith("sort:"))
async def subsearch_sort(callback: CallbackQuery, state: FSMContext) -> None:
    sort_mode = callback.data.split(":")[1]
    data = await state.get_data()
    await state.clear()
    await callback.answer()

    sub_id = data["sub_id"]
    count = data.get("count", 10)

    await callback.message.answer("🔄 Ищу статьи… Это может занять некоторое время.")

    from sqlalchemy import select
    from app.storage.models import Subscription

    async with async_session() as session:
        result = await session.execute(
            select(Subscription).where(
                Subscription.id == sub_id,
                Subscription.user_id == callback.from_user.id,
            )
        )
        sub = result.scalar_one_or_none()
        if not sub:
            await callback.message.answer("⚠️ Подписка не найдена.")
            return

        results = await search_and_store(
            session,
            subscription=sub,
            max_per_source=count,
            sort=sort_mode,
        )

    if not results:
        await callback.message.answer(
            "😕 Статей пока не найдено. Бот проверит позже автоматически.",
            reply_markup=main_menu_kb(),
        )
        return

    sort_label = {"date": "по дате", "cited": "по цитируемости", "relevance": "по релевантности"}.get(sort_mode, "")
    header = f"📚 Найдено статей: {len(results)} ({sort_label})\n\n"
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


# ── "notify only" — just confirm ────────────────────────────────────
@router.callback_query(F.data.startswith("notifyonly:"))
async def cb_notify_only(callback: CallbackQuery) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await callback.message.answer(
        "👍 Отлично! Бот будет проверять новые статьи автоматически и присылать уведомления.",
        reply_markup=main_menu_kb(),
    )
