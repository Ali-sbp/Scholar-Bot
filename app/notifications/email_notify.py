from __future__ import annotations

import logging
from html import escape

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import config
from app.storage.models import Annotation, Article

logger = logging.getLogger(__name__)


async def send_email_notification(
    to_email: str,
    subscription_name: str,
    articles: list[tuple[Article, Annotation]],
) -> bool:
    """Send article digest over SMTP. Returns True on success."""
    if not articles or not to_email or not config.SMTP_USER:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Новые статьи по подписке «{subscription_name}»"
    msg["From"] = config.EMAIL_FROM
    msg["To"] = to_email

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
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=config.SMTP_HOST,
            port=config.SMTP_PORT,
            username=config.SMTP_USER,
            password=config.SMTP_PASSWORD,
            use_tls=False,
            start_tls=True,
        )
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False
