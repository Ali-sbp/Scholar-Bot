from __future__ import annotations

import logging
from datetime import datetime

import aiohttp

from .base import ArticleData, BaseSource

logger = logging.getLogger(__name__)

S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"


class SemanticScholarSource(BaseSource):
    async def search(
        self,
        keywords: list[str],
        authors: list[str] | None = None,
        journals: list[str] | None = None,
        max_results: int = 10,
    ) -> list[ArticleData]:
        query = " ".join(keywords)
        params = {
            "query": query,
            "limit": str(min(max_results, 100)),
            "fields": "title,authors,abstract,url,externalIds,publicationDate,journal",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(S2_API, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        logger.warning("Semantic Scholar returned status %s", resp.status)
                        return []
                    data = await resp.json()
        except Exception as e:
            logger.error("Semantic Scholar request failed: %s", e)
            return []

        articles: list[ArticleData] = []
        for paper in data.get("data", []):
            ext_ids = paper.get("externalIds") or {}
            ext_id = ext_ids.get("DOI") or ext_ids.get("ArXiv") or paper.get("paperId", "")

            pub_date = None
            if paper.get("publicationDate"):
                try:
                    pub_date = datetime.fromisoformat(paper["publicationDate"])
                except (ValueError, TypeError):
                    pass

            journal_name = None
            if paper.get("journal"):
                journal_name = paper["journal"].get("name")

            paper_id = paper.get("paperId", "")
            url = paper.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}"

            articles.append(
                ArticleData(
                    external_id=f"s2:{ext_id}",
                    source="semantic_scholar",
                    title=paper.get("title", ""),
                    url=url,
                    authors=[a.get("name", "") for a in (paper.get("authors") or [])],
                    journal=journal_name,
                    abstract=paper.get("abstract"),
                    published_at=pub_date,
                )
            )

        return articles
