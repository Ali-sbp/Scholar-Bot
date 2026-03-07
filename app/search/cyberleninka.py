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

        # CyberLeninka uses multiple possible layouts — try all known selectors
        items = soup.select("ul.list li")
        if not items:
            items = soup.select(".search-results .article-item")
        if not items:
            items = soup.select("article")
        if not items:
            # Fallback: find all links pointing to /article/
            items = []
            for a_tag in soup.find_all("a", href=lambda h: h and "/article/" in h):
                parent = a_tag.find_parent(["li", "div", "article"])
                if parent and parent not in items:
                    items.append(parent)

        for item in items:
            link_tag = item.select_one("a[href*='/article/']")
            if not link_tag:
                link_tag = item if item.name == "a" and "/article/" in item.get("href", "") else None
            if not link_tag:
                continue

            href = link_tag.get("href", "")
            full_url = f"https://cyberleninka.ru{href}" if href.startswith("/") else href

            # Title: try multiple selectors
            title = ""
            for sel in ["h2", "h3", ".title", "span"]:
                tag = item.select_one(sel)
                if tag:
                    title = tag.get_text(strip=True)
                    break
            if not title:
                title = link_tag.get_text(strip=True)
            if not title:
                continue

            # Annotation / snippet text
            abstract = None
            for sel in [".abstract", ".annotation", ".descr", "p"]:
                tag = item.select_one(sel)
                if tag and len(tag.get_text(strip=True)) > 20:
                    abstract = tag.get_text(strip=True)
                    break

            # Authors
            author_list: list[str] = []
            for sel in [".author", ".authors", "span.author"]:
                tag = item.select_one(sel)
                if tag:
                    author_list = [a.strip() for a in tag.get_text().split(",") if a.strip()]
                    break

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
