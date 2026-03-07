from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ArticleData:
    """Unified article representation returned by every source adapter."""

    external_id: str
    source: str
    title: str
    url: str
    authors: list[str] = field(default_factory=list)
    journal: str | None = None
    abstract: str | None = None
    published_at: datetime | None = None
    citation_count: int | None = None


class BaseSource(ABC):
    @abstractmethod
    async def search(
        self,
        keywords: list[str],
        authors: list[str] | None = None,
        journals: list[str] | None = None,
        max_results: int = 10,
    ) -> list[ArticleData]: ...
