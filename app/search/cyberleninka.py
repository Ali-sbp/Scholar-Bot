from __future__ import annotations

import logging

import aiohttp
from bs4 import BeautifulSoup

from .base import ArticleData, BaseSource

logger = logging.getLogger(__name__)

CYBERLENINKA_SEARCH = "https://cyberleninka.ru/search"


class CyberLeninkaSource(BaseSource):
    """Scrapes CyberLeninka search results (no official API available)."""

    async def search(
        self,
        keywords: list[str],
        authors: list[str] | None = None,
        journals: list[str] | None = None,
        max_results: int = 10,
    ) -> list[ArticleData]:
        query = " ".join(keywords)
        params = {"q": query, "page": "1"}

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    CYBERLENINKA_SEARCH, params=params, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        logger.warning("CyberLeninka returned status %s", resp.status)
                        return []
                    html = await resp.text()
        except Exception as e:
            logger.error("CyberLeninka request failed: %s", e)
            return []

        soup = BeautifulSoup(html, "lxml")
        articles: list[ArticleData] = []

        # CyberLeninka renders search results inside <ul> with <li> items
        for item in soup.select("ul.list li"):
            link_tag = item.select_one("a[href*='/article/']")
            if not link_tag:
                continue

            href = link_tag.get("href", "")
            full_url = f"https://cyberleninka.ru{href}" if href.startswith("/") else href

            # Title is usually inside a span within the link
            title_tag = link_tag.select_one("span") or link_tag
            title = title_tag.get_text(strip=True)
            if not title:
                continue

            # Annotation / snippet text
            snippet_tag = item.select_one(".abstract, .annotation, p")
            abstract = snippet_tag.get_text(strip=True) if snippet_tag else None

            # Authors
            author_tag = item.select_one(".author, .authors")
            author_list: list[str] = []
            if author_tag:
                author_list = [a.strip() for a in author_tag.get_text().split(",") if a.strip()]

            slug = href.rstrip("/").split("/")[-1] if href else title[:60]

            articles.append(
                ArticleData(
                    external_id=f"cyberleninka:{slug}",
                    source="cyberleninka",
                    title=title,
                    url=full_url,
                    authors=author_list,
                    abstract=abstract,
                )
            )

            if len(articles) >= max_results:
                break

        return articles
