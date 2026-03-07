from __future__ import annotations

import logging
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup

from .base import ArticleData, BaseSource

logger = logging.getLogger(__name__)

CROSSREF_API = "https://api.crossref.org/works"


class CrossRefSource(BaseSource):
    async def search(
        self,
        keywords: list[str],
        authors: list[str] | None = None,
        journals: list[str] | None = None,
        max_results: int = 10,
    ) -> list[ArticleData]:
        # Use quoted phrases for multi-word keywords
        parts = []
        for kw in keywords:
            parts.append(f'"{kw}"' if " " in kw else kw)
        query = " ".join(parts)
        params: dict[str, str] = {
            "query": query,
            "rows": str(max_results),
            "sort": "deposited",
            "order": "desc",
        }
        if authors:
            params["query.author"] = " ".join(authors)

        headers = {"User-Agent": "ScholarBot/1.0 (mailto:scholar@example.com)"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    CROSSREF_API, params=params, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        logger.warning("CrossRef returned status %s", resp.status)
                        return []
                    data = await resp.json()
        except Exception as e:
            logger.error("CrossRef request failed: %s", e)
            return []

        articles: list[ArticleData] = []
        for item in data.get("message", {}).get("items", []):
            doi = item.get("DOI", "")
            title = (item.get("title") or [""])[0]

            abstract = item.get("abstract", "")
            if abstract:
                abstract = BeautifulSoup(abstract, "lxml").get_text()

            authors_list: list[str] = []
            for author in item.get("author", []):
                name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                if name:
                    authors_list.append(name)

            pub_date = None
            date_parts = item.get("published", {}).get("date-parts", [[]])
            if date_parts and date_parts[0]:
                parts = date_parts[0]
                try:
                    pub_date = datetime(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)
                except (ValueError, IndexError, TypeError):
                    pass

            journal_name = (item.get("container-title") or [None])[0]
            url = f"https://doi.org/{doi}" if doi else item.get("URL", "")

            if not doi:
                continue

            articles.append(
                ArticleData(
                    external_id=f"crossref:{doi}",
                    source="crossref",
                    title=title,
                    url=url,
                    authors=authors_list,
                    journal=journal_name,
                    abstract=abstract or None,
                    published_at=pub_date,
                )
            )

        return articles
