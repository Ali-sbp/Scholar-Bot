from __future__ import annotations

import logging
from datetime import datetime, timedelta

from aiogram import Bot
from sqlalchemy import select

from app.notifications.email_notify import send_email_notification
from app.notifications.telegram_notify import send_article_notification
from app.storage.database import async_session
from app.storage.models import Subscription, User
from app.subscriptions.manager import get_unnotified_articles, search_and_store

logger = logging.getLogger(__name__)


async def check_subscriptions(bot: Bot) -> None:
    """Periodic job: check every active subscription that is due for an update."""
    async with async_session() as session:
        now = datetime.utcnow()
        result = await session.execute(
            select(Subscription).where(Subscription.is_active == True)  # noqa: E712
        )
        subscriptions = result.scalars().all()

        for sub in subscriptions:
            # Skip if not yet due
            if sub.last_checked_at:
                next_check = sub.last_checked_at + timedelta(hours=sub.check_interval_hrs)
                if now < next_check:
                    continue

            try:
                # Search for new articles
                await search_and_store(session, sub)

                # Collect unnotified articles
                new_items = await get_unnotified_articles(session, sub)

                if not new_items:
                    continue

                pairs = [(article, ann) for article, ann, _sa in new_items]

                # Telegram notification
                await send_article_notification(bot, sub.user_id, sub.name, pairs)

                # Email notification
                user_result = await session.execute(
                    select(User).where(User.id == sub.user_id)
                )
                user = user_result.scalar_one_or_none()
                email_sent = False
                if user and user.email:
                    email_sent = await send_email_notification(user.email, sub.name, pairs)

                # Mark as notified
                for _article, _ann, sa in new_items:
                    sa.notified_telegram = True
                    sa.notified_email = email_sent

                await session.commit()

            except Exception as e:
                logger.error("Error checking subscription %s: %s", sub.id, e)
