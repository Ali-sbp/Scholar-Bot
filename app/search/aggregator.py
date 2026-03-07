from __future__ import annotations

import asyncio
import logging

from .arxiv_source import ArxivSource
from .base import ArticleData
from .crossref_source import CrossRefSource
from .cyberleninka import CyberLeninkaSource
from .semantic_scholar import SemanticScholarSource

logger = logging.getLogger(__name__)


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
        max_per_source: int = 5,
    ) -> list[ArticleData]:
        tasks = [
            source.search(keywords, authors, journals, max_per_source)
            for source in self.sources
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles: list[ArticleData] = []
        seen_titles: set[str] = set()

        for result in results:
            if isinstance(result, Exception):
                logger.error("Source search failed: %s", result)
                continue
            for article in result:
                norm_title = article.title.lower().strip()
                if norm_title not in seen_titles:
                    seen_titles.add(norm_title)
                    all_articles.append(article)

        return all_articles
