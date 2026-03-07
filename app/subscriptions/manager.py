from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.annotator import generate_annotation
from app.search.aggregator import SearchAggregator
from app.storage.models import (
    Annotation,
    Article,
    Subscription,
    SubscriptionArticle,
    User,
)

logger = logging.getLogger(__name__)
_aggregator = SearchAggregator()


async def get_or_create_user(session: AsyncSession, telegram_id: int) -> User:
    result = await session.execute(select(User).where(User.id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(id=telegram_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def create_subscription(
    session: AsyncSession,
    user_id: int,
    name: str,
    keywords: list[str],
    authors: list[str] | None = None,
    journals: list[str] | None = None,
    check_interval_hrs: int = 24,
) -> Subscription:
    sub = Subscription(
        user_id=user_id,
        name=name,
        keywords=keywords,
        authors=authors or [],
        journals=journals or [],
        check_interval_hrs=check_interval_hrs,
    )
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return sub


async def search_and_store(
    session: AsyncSession,
    subscription: Subscription | None = None,
    keywords: list[str] | None = None,
    authors: list[str] | None = None,
    journals: list[str] | None = None,
    max_per_source: int = 10,
    language: str = "any",
) -> list[tuple[Article, Annotation]]:
    """Search, store articles, generate missing annotations, optionally link to subscription."""
    kw = keywords or (subscription.keywords if subscription else [])
    au = authors or (subscription.authors if subscription else None) or None
    jn = journals or (subscription.journals if subscription else None) or None

    raw_articles = await _aggregator.search(
        keywords=kw,
        authors=au,
        journals=jn,
        max_per_source=max_per_source,
        language=language,
    )

    results: list[tuple[Article, Annotation]] = []

    for article_data in raw_articles:
        try:
            # Strip timezone if present (DB uses naive timestamps)
            pub_at = article_data.published_at
            if pub_at and pub_at.tzinfo is not None:
                pub_at = pub_at.replace(tzinfo=None)

            # Upsert article
            existing = await session.execute(
                select(Article).where(Article.external_id == article_data.external_id)
            )
            article = existing.scalar_one_or_none()

            if not article:
                article = Article(
                    external_id=article_data.external_id,
                    source=article_data.source,
                    title=article_data.title,
                    url=article_data.url,
                    authors=article_data.authors,
                    journal=article_data.journal,
                    abstract=article_data.abstract,
                    published_at=pub_at,
                )
                session.add(article)
                await session.flush()

            # Ensure annotation exists
            ann_result = await session.execute(
                select(Annotation).where(Annotation.article_id == article.id)
            )
            annotation = ann_result.scalar_one_or_none()

            if not annotation:
                text_ru, model_used = await generate_annotation(article.title, article.abstract)
                annotation = Annotation(
                    article_id=article.id,
                    text_ru=text_ru,
                    model_used=model_used,
                )
                session.add(annotation)
                await session.flush()

            # Link article ↔ subscription if provided
            if subscription:
                link_result = await session.execute(
                    select(SubscriptionArticle).where(
                        SubscriptionArticle.subscription_id == subscription.id,
                        SubscriptionArticle.article_id == article.id,
                    )
                )
                if not link_result.scalar_one_or_none():
                    session.add(
                        SubscriptionArticle(
                            subscription_id=subscription.id,
                            article_id=article.id,
                        )
                    )

            results.append((article, annotation))

        except Exception as e:
            logger.error("Error processing article %s: %s", article_data.external_id, e)
            await session.rollback()
            continue

    if subscription:
        subscription.last_checked_at = datetime.utcnow()
    await session.commit()

    return results


async def get_user_subscriptions(session: AsyncSession, user_id: int) -> list[Subscription]:
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.is_active == True)  # noqa: E712
        .order_by(Subscription.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_subscription(session: AsyncSession, subscription_id: int, user_id: int) -> bool:
    result = await session.execute(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.user_id == user_id,
        )
    )
    sub = result.scalar_one_or_none()
    if sub:
        await session.delete(sub)
        await session.commit()
        return True
    return False


async def set_user_email(session: AsyncSession, user_id: int, email: str) -> None:
    user = await get_or_create_user(session, user_id)
    user.email = email
    await session.commit()


async def get_user_email(session: AsyncSession, user_id: int) -> str | None:
    user = await get_or_create_user(session, user_id)
    return user.email


async def delete_user_email(session: AsyncSession, user_id: int) -> None:
    user = await get_or_create_user(session, user_id)
    user.email = None
    await session.commit()


async def get_unnotified_articles(
    session: AsyncSession, subscription: Subscription
) -> list[tuple[Article, Annotation, SubscriptionArticle]]:
    """Articles linked to a subscription that haven't been notified yet."""
    result = await session.execute(
        select(SubscriptionArticle, Article, Annotation)
        .join(Article, SubscriptionArticle.article_id == Article.id)
        .join(Annotation, Annotation.article_id == Article.id)
        .where(
            SubscriptionArticle.subscription_id == subscription.id,
            SubscriptionArticle.notified_telegram == False,  # noqa: E712
        )
    )
    return [(row.Article, row.Annotation, row.SubscriptionArticle) for row in result.all()]
