from __future__ import annotations

import logging
from html import escape

import httpx

from app.config import config
from app.storage.models import Annotation, Article

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


async def send_email_notification(
    to_email: str,
    subscription_name: str,
    articles: list[tuple[Article, Annotation]],
) -> bool:
    """Send article digest via Resend HTTP API. Returns True on success."""
    if not articles or not to_email or not config.RESEND_API_KEY:
        return False

    rows: list[str] = []
    for article, annotation in articles:
        url = article.url if article.url.startswith(("http://", "https://")) else ""
        link = f'<a href="{escape(url)}">Перейти к статье</a>' if url else ""
        rows.append(
            f"<div style='margin-bottom:15px;'>"
            f"<b>{escape(article.title)}</b><br>"
            f"<em>{escape(annotation.text_ru)}</em><br>"
            f"{link}"
            f"</div>"
        )

    html = (
        f"<h2>Новые статьи по подписке «{escape(subscription_name)}»</h2>"
        + "\n".join(rows)
    )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                RESEND_URL,
                headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"},
                json={
                    "from": config.EMAIL_FROM,
                    "to": [to_email],
                    "subject": f"Новые статьи по подписке «{subscription_name}»",
                    "html": html,
                },
                timeout=15,
            )
            if resp.status_code in (200, 201):
                logger.info("Email sent to %s via Resend", to_email)
                return True
            logger.error("Resend API error %s: %s", resp.status_code, resp.text)
            return False
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False
