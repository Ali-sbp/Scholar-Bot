from __future__ import annotations

from html import escape

from aiogram import Bot

from app.storage.models import Annotation, Article


async def send_article_notification(
    bot: Bot,
    chat_id: int,
    subscription_name: str,
    articles: list[tuple[Article, Annotation]],
) -> None:
    """Send new-articles digest as Telegram messages."""
    if not articles:
        return

    header = f"📚 Новые статьи по подписке «{escape(subscription_name)}»:\n\n"
    chunks: list[str] = [header]

    for i, (article, annotation) in enumerate(articles, 1):
        # Validate URL scheme
        url = article.url if article.url.startswith(("http://", "https://")) else ""
        entry = (
            f"{i}. <b>{escape(article.title)}</b>\n"
            f"   📝 {escape(annotation.text_ru)}\n"
        )
        if url:
            entry += f'   🔗 <a href="{escape(url)}">Источник</a> ({escape(article.source)})\n\n'
        else:
            entry += f"   📎 Источник: {escape(article.source)}\n\n"

        if len("".join(chunks)) + len(entry) > 4000:
            await bot.send_message(
                chat_id, "".join(chunks), parse_mode="HTML", disable_web_page_preview=True,
            )
            chunks = [f"📚 Продолжение ({escape(subscription_name)}):\n\n"]
        chunks.append(entry)

    if chunks:
        await bot.send_message(
            chat_id, "".join(chunks), parse_mode="HTML", disable_web_page_preview=True,
        )
