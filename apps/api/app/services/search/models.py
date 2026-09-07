"""Search result data model."""

from dataclasses import dataclass
from typing import Any


@dataclass
class SearchResult:
    """A single web search result."""

    title: str
    url: str
    snippet: str
    published_date: str = ""
    source: str = "web"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "published_date": self.published_date,
            "source": self.source,
        }
