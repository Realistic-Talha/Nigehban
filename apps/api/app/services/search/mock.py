"""Mock search for CI."""

from app.services.search.models import SearchResult


def mock_search(query: str, num_results: int = 5) -> list[SearchResult]:
    return [
        SearchResult(
            title=f"Mock fact-check: {query[:50]}",
            url="https://www.sbp.org.pk/",
            snippet="Mock search result for testing.",
            source="mock",
        )
    ][:num_results]
