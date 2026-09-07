"""Unified web search service."""

import logging

from app.core.config import settings
from app.services.search.curated import curated_search
from app.services.search.duckduckgo import duckduckgo_search
from app.services.search.mock import mock_search
from app.services.search.models import SearchResult

logger = logging.getLogger(__name__)


class WebSearchService:
    """Merge DuckDuckGo, curated references, and optional mock."""

    async def search(self, query: str, num_results: int = 8) -> list[SearchResult]:
        if settings.SEARCH_PROVIDER == "mock":
            return mock_search(query, num_results)

        curated = await curated_search(query, limit=3)
        web = await duckduckgo_search(query, num_results=num_results)

        seen_urls: set[str] = set()
        merged: list[SearchResult] = []

        for result in curated + web:
            url = result.url.strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            merged.append(result)

        return merged[:num_results]


search_service = WebSearchService()
