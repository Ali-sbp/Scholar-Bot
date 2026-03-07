from __future__ import annotations

import logging
import re

import aiohttp

from .base import ArticleData, BaseSource

logger = logging.getLogger(__name__)

CYBERLENINKA_API = "https://cyberleninka.ru/api/search"

# Strip HTML bold tags that CyberLeninka injects for highlighting
_BOLD_RE = re.compile(r"</?b>")


class CyberLeninkaSource(BaseSource):
    """Fetches CyberLeninka results via its internal JSON API."""

    async def search(
        self,
        keywords: list[str],
        authors: list[str] | None = None,
        journals: list[str] | None = None,
        max_results: int = 10,
    ) -> list[ArticleData]:
        query = " ".join(keywords)
        payload = {
            "mode": "articles",
            "q": query,
            "size": max_results,
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ScholarBot/1.0)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    CYBERLENINKA_API,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        logger.warning("CyberLeninka API returned status %s", resp.status)
                        return []
                    data = await resp.json()
        except Exception as e:
            logger.error("CyberLeninka request failed: %s", e)
            return []

        raw_articles = data.get("articles", [])
        logger.info(
            "CyberLeninka: found=%s, returned %d articles",
            data.get("found", "?"),
            len(raw_articles),
        )

        articles: list[ArticleData] = []
        for item in raw_articles:
            title = _BOLD_RE.sub("", item.get("name", "")).strip()
            if not title:
                continue

            link = item.get("link", "")
            url = f"https://cyberleninka.ru{link}" if link.startswith("/") else link

            annotation = item.get("annotation", "")
            if annotation:
                annotation = _BOLD_RE.sub("", annotation).strip()

            author_list = item.get("authors") or []
            journal_name = item.get("journal")

            slug = link.rstrip("/").split("/")[-1] if link else title[:60]

            articles.append(
                ArticleData(
                    external_id=f"cyberleninka:{slug}",
                    source="cyberleninka",
                    title=title,
                    url=url,
                    authors=author_list,
                    journal=journal_name,
                    abstract=annotation or None,
                )
            )

        return articles
