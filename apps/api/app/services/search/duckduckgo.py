"""Web search provider via ddgs metasearch (Bing/Brave/Google/… fallbacks)."""

import asyncio
import logging
import time

from app.services.search.models import SearchResult

logger = logging.getLogger(__name__)

_last_call = 0.0
_MIN_INTERVAL = 1.5  # seconds between calls


async def duckduckgo_search(query: str, num_results: int = 8) -> list[SearchResult]:
    """Run metasearch with simple rate limiting."""
    global _last_call
    now = time.monotonic()
    wait = _MIN_INTERVAL - (now - _last_call)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_call = time.monotonic()

    try:

        def _run() -> list[SearchResult]:
            try:
                from ddgs import DDGS  # type: ignore
            except ImportError:
                from duckduckgo_search import DDGS  # type: ignore

            results: list[SearchResult] = []
            with DDGS() as client:
                try:
                    rows = list(
                        client.text(
                            query,
                            region="pk-en",
                            max_results=num_results,
                            backend="auto",
                        )
                    )
                except TypeError:
                    rows = list(client.text(query, region="pk-en", max_results=num_results))
                for item in rows:
                    results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            url=item.get("href", item.get("link", "")),
                            snippet=item.get("body", item.get("snippet", "")),
                            source="web_search",
                        )
                    )
            return results

        return await asyncio.to_thread(_run)
    except Exception:
        logger.exception("Web search failed for query: %s", query)
        return []
