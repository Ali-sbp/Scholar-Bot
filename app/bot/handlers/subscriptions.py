from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.keyboards import main_menu_kb, subscription_actions_kb
from app.storage.database import async_session
from app.storage.models import Subscription
from app.subscriptions.manager import delete_subscription, get_user_subscriptions, search_and_store

router = Router()


# ── list subscriptions ──────────────────────────────────────────────
@router.message(Command("subscriptions"))
@router.message(F.text == "📋 Мои подписки")
async def list_subscriptions(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session() as session:
        subs = await get_user_subscriptions(session, message.from_user.id)

    if not subs:
        await message.answer("У тебя пока нет подписок. Создай через /subscribe")
        return

    for sub in subs:
        kw = escape(", ".join(sub.keywords))
        lang_label = {"any": "Любой", "ru": "Русский", "en": "English"}.get(
            getattr(sub, "language", "any") or "any", "Любой"
        )
        text = (
            f"📌 <b>{escape(sub.name)}</b>\n"
            f"🔑 Ключевые слова: {kw}\n"
            f"⏰ Проверка каждые {sub.check_interval_hrs}ч\n"
            f"🌐 Язык: {lang_label}\n"
        )
        if sub.authors:
            text += f"👤 Авторы: {escape(', '.join(sub.authors))}\n"
        if sub.journals:
            text += f"📰 Журналы: {escape(', '.join(sub.journals))}\n"

        await message.answer(
            text, parse_mode="HTML", reply_markup=subscription_actions_kb(sub.id)
        )


# ── delete subscription ────────────────────────────────────────────
@router.callback_query(F.data.startswith("delete:"))
async def cb_delete(callback: CallbackQuery) -> None:
    sub_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        ok = await delete_subscription(session, sub_id, callback.from_user.id)

    if ok:
        await callback.message.edit_text("✅ Подписка удалена.")
    else:
        await callback.message.edit_text("⚠️ Подписка не найдена.")
    await callback.answer()


# ── manual check now ────────────────────────────────────────────────
@router.callback_query(F.data.startswith("check:"))
async def cb_check_now(callback: CallbackQuery) -> None:
    sub_id = int(callback.data.split(":")[1])
    await callback.message.answer("🔄 Проверяю…")
    await callback.answer()

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

        results = await search_and_store(session, sub)

    if results:
        header = f"📚 Найдено статей: {len(results)}\n\n"
        chunks: list[str] = [header]
        for i, (article, annotation) in enumerate(results[:10], 1):
            url = article.url if article.url.startswith(("http://", "https://")) else ""
            entry = f"{i}. <b>{escape(article.title)}</b>\n   📝 {escape(annotation.text_ru)}\n"
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
    else:
        await callback.message.answer("Новых статей не найдено.", reply_markup=main_menu_kb())
