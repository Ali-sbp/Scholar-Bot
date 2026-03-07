from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime

import aiohttp

from .base import ArticleData, BaseSource

logger = logging.getLogger(__name__)

ARXIV_API = "https://export.arxiv.org/api/query"


class ArxivSource(BaseSource):
    async def search(
        self,
        keywords: list[str],
        authors: list[str] | None = None,
        journals: list[str] | None = None,
        max_results: int = 10,
    ) -> list[ArticleData]:
        query_parts: list[str] = []
        if keywords:
            for kw in keywords:
                query_parts.append(f"all:{kw}")
        if authors:
            for au in authors:
                query_parts.append(f"au:{au}")

        search_query = " AND ".join(query_parts) if query_parts else "all:science"

        params = {
            "search_query": search_query,
            "start": "0",
            "max_results": str(max_results),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ARXIV_API, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        logger.warning("arXiv returned status %s", resp.status)
                        return []
                    text = await resp.text()
        except Exception as e:
            logger.error("arXiv request failed: %s", e)
            return []

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(text)
        articles: list[ArticleData] = []

        for entry in root.findall("atom:entry", ns):
            id_el = entry.find("atom:id", ns)
            title_el = entry.find("atom:title", ns)
            summary_el = entry.find("atom:summary", ns)
            published_el = entry.find("atom:published", ns)

            if id_el is None or title_el is None:
                continue

            raw_id = id_el.text.strip()
            arxiv_id = raw_id.split("/abs/")[-1]
            title = " ".join(title_el.text.strip().split())
            abstract = " ".join(summary_el.text.strip().split()) if summary_el is not None else None

            pub_dt = None
            if published_el is not None:
                try:
                    dt = datetime.fromisoformat(published_el.text.strip().replace("Z", "+00:00"))
                    # Strip timezone — DB uses naive timestamps
                    pub_dt = dt.replace(tzinfo=None)
                except ValueError:
                    pass

            authors_list = [
                a.find("atom:name", ns).text
                for a in entry.findall("atom:author", ns)
                if a.find("atom:name", ns) is not None
            ]

            articles.append(
                ArticleData(
                    external_id=f"arxiv:{arxiv_id}",
                    source="arxiv",
                    title=title,
                    url=raw_id,
                    authors=authors_list,
                    abstract=abstract,
                    published_at=pub_dt,
                )
            )

        return articles
