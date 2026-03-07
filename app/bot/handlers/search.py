from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.bot.keyboards import main_menu_kb, skip_kb
from app.storage.database import async_session
from app.subscriptions.manager import get_or_create_user, search_and_store

router = Router()


class SearchForm(StatesGroup):
    keywords = State()
    authors = State()


@router.message(Command("search"))
@router.message(F.text == "🔍 Поиск статей")
async def start_search(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchForm.keywords)
    await message.answer(
        "🔍 Введи ключевые слова для поиска (через запятую):\n\n"
        "Например: <i>теория игр, game theory, Nash equilibrium</i>",
        parse_mode="HTML",
    )


@router.message(SearchForm.keywords)
async def search_keywords(message: Message, state: FSMContext) -> None:
    keywords = [k.strip() for k in message.text.split(",") if k.strip()]
    if not keywords:
        await message.answer("⚠️ Укажи хотя бы одно ключевое слово.")
        return
    await state.update_data(keywords=keywords)
    await state.set_state(SearchForm.authors)
    await message.answer("👤 Укажи авторов (через запятую), или пропусти:", reply_markup=skip_kb())


@router.callback_query(SearchForm.authors, F.data == "skip")
async def skip_authors_search(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(authors=[])
    await _do_search(callback.message, state, callback.from_user.id)
    await callback.answer()


@router.message(SearchForm.authors)
async def search_authors(message: Message, state: FSMContext) -> None:
    authors = [a.strip() for a in message.text.split(",") if a.strip()]
    await state.update_data(authors=authors)
    await _do_search(message, state, message.from_user.id)


# Need to import CallbackQuery for the skip handler
from aiogram.types import CallbackQuery  # noqa: E402


async def _do_search(message: Message, state: FSMContext, user_id: int) -> None:
    data = await state.get_data()
    await state.clear()

    await message.answer("🔄 Ищу статьи… Это может занять некоторое время.")

    async with async_session() as session:
        await get_or_create_user(session, user_id)
        results = await search_and_store(
            session,
            keywords=data["keywords"],
            authors=data.get("authors", []) or None,
        )

    if not results:
        await message.answer(
            "😕 Ничего не найдено. Попробуй другие ключевые слова.",
            reply_markup=main_menu_kb(),
        )
        return

    header = f"📚 Найдено статей: {len(results)}\n\n"
    chunks: list[str] = [header]
    for i, (article, annotation) in enumerate(results, 1):
        url = article.url if article.url.startswith(("http://", "https://")) else ""
        entry = f"{i}. <b>{escape(article.title)}</b>\n" f"   📝 {escape(annotation.text_ru)}\n"
        if url:
            entry += f'   🔗 <a href="{escape(url)}">Источник</a> ({escape(article.source)})\n\n'
        else:
            entry += f"   📎 {escape(article.source)}\n\n"

        if len("".join(chunks)) + len(entry) > 4000:
            await message.answer(
                "".join(chunks), parse_mode="HTML", disable_web_page_preview=True
            )
            chunks = ["📚 Продолжение:\n\n"]
        chunks.append(entry)

    if chunks:
        await message.answer(
            "".join(chunks),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=main_menu_kb(),
        )
