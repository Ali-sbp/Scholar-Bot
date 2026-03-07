from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime

from .arxiv_source import ArxivSource
from .base import ArticleData
from .crossref_source import CrossRefSource
from .cyberleninka import CyberLeninkaSource
from .semantic_scholar import SemanticScholarSource

logger = logging.getLogger(__name__)

_CYRILLIC_RE = re.compile(r"[а-яА-ЯёЁ]")
_LATIN_RE = re.compile(r"[a-zA-Z]")


def _lang_of(text: str) -> str:
    """Rough language detection by script: 'ru', 'en', or 'other'."""
    cyr = len(_CYRILLIC_RE.findall(text))
    lat = len(_LATIN_RE.findall(text))
    if cyr > lat:
        return "ru"
    if lat > 0:
        return "en"
    return "other"


class SearchAggregator:
    """Fans out search to all sources in parallel and deduplicates results."""

    def __init__(self) -> None:
        self.sources = [
            ArxivSource(),
            SemanticScholarSource(),
            CrossRefSource(),
            CyberLeninkaSource(),
        ]

    async def search(
        self,
        keywords: list[str],
        authors: list[str] | None = None,
        journals: list[str] | None = None,
        max_per_source: int = 10,
        language: str = "any",
    ) -> list[ArticleData]:
        tasks = [
            source.search(keywords, authors, journals, max_per_source)
            for source in self.sources
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles: list[ArticleData] = []
        seen_titles: set[str] = set()

        for i, result in enumerate(results):
            source_name = type(self.sources[i]).__name__
            if isinstance(result, Exception):
                logger.error("Source %s search failed: %s", source_name, result)
                continue
            logger.info("Source %s returned %d articles", source_name, len(result))
            for article in result:
                norm_title = article.title.lower().strip()
                if norm_title not in seen_titles:
                    seen_titles.add(norm_title)
                    all_articles.append(article)

        # Language filter
        if language in ("ru", "en"):
            all_articles = [a for a in all_articles if _lang_of(a.title) == language]

        # Sort by date descending (newest first)
        all_articles.sort(
            key=lambda a: a.published_at or datetime.min, reverse=True
        )

        return all_articles
