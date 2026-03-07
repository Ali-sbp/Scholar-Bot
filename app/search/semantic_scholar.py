from __future__ import annotations

import asyncio
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
            "fields": "title,authors,abstract,url,externalIds,publicationDate,journal,citationCount",
        }

        data = None
        for attempt in range(3):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        S2_API, params=params, timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        if resp.status == 429:
                            wait = 3 ** attempt + 1  # 2s, 4s, 10s
                            logger.warning(
                                "S2 rate-limited (attempt %d), retrying in %ds", attempt + 1, wait,
                            )
                            await asyncio.sleep(wait)
                            continue
                        if resp.status != 200:
                            body = await resp.text()
                            logger.warning(
                                "S2 returned status %s: %.200s", resp.status, body,
                            )
                            return []
                        data = await resp.json()
                        break
            except Exception as e:
                logger.error("S2 request failed (attempt %d): %s", attempt + 1, e)
                if attempt < 2:
                    await asyncio.sleep(2)
                    continue
                return []

        if data is None:
            logger.warning("S2: all retries exhausted")
            return []

        papers = data.get("data", [])
        logger.info("S2: received %d papers for query '%s'", len(papers), query)

        articles: list[ArticleData] = []
        for paper in papers:
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

            title = paper.get("title", "")
            if not title:
                continue

            articles.append(
                ArticleData(
                    external_id=f"s2:{ext_id}",
                    source="semantic_scholar",
                    title=title,
                    url=url,
                    authors=[a.get("name", "") for a in (paper.get("authors") or [])],
                    journal=journal_name,
                    abstract=paper.get("abstract"),
                    published_at=pub_date,
                    citation_count=paper.get("citationCount"),
                )
            )

        return articles
