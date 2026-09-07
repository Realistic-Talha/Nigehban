"""RSS / news feed ingestion worker for automated claim extraction.

Designed to run as a periodic task that:
1. Fetches configured RSS/Atom feeds
2. Parses entries and extracts claim-like statements
3. Deduplicates by content hash
4. Submits new claims to the pipeline for analysis
"""

import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import redis_pool

logger = logging.getLogger(__name__)

# Atom / RSS namespace mappings
_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_CONTENT_HASH_TTL = 7 * 24 * 3600  # 7 days — dedup window


class RSSIngestionWorker:
    """Ingest RSS and Atom feeds, extract claims, and queue them for analysis."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def ingest_rss_feeds(self, feed_urls: list[str]) -> int:
        """Fetch and process a list of RSS/Atom feed URLs.

        Parameters
        ----------
        feed_urls : List of RSS or Atom feed URLs to ingest.

        Returns
        -------
        Count of new (non-duplicate) items ingested.
        """
        new_count = 0

        for url in feed_urls:
            try:
                entries = await self._fetch_feed(url)
                for entry in entries:
                    is_new = await self._process_entry(entry, source_url=url)
                    if is_new:
                        new_count += 1
            except Exception:
                logger.error("Failed to ingest feed: %s", url, exc_info=True)

        logger.info("RSS ingestion complete: %d new items from %d feeds", new_count, len(feed_urls))
        return new_count

    async def check_new_claims(self) -> list[dict[str, Any]]:
        """Check configured news sources for new claims.

        Uses the RSS_FEED_URLS setting from config. Returns a list of
        newly discovered claim dicts suitable for pipeline submission.
        """
        feed_urls = settings.RSS_FEED_URLS
        if not feed_urls:
            logger.debug("No RSS feed URLs configured")
            return []

        new_claims: list[dict[str, Any]] = []

        for url in feed_urls:
            try:
                entries = await self._fetch_feed(url)
                for entry in entries[:20]:  # cap per feed to avoid flooding
                    claim = self._entry_to_claim(entry, url)
                    if claim and not await self._is_duplicate(claim["content_hash"]):
                        await self._mark_seen(claim["content_hash"])
                        new_claims.append(claim)
            except Exception:
                logger.error("Failed to check claims from %s", url, exc_info=True)

        logger.info("Discovered %d new claims from %d feeds", len(new_claims), len(feed_urls))
        return new_claims

    # ------------------------------------------------------------------
    # Feed fetching & parsing
    # ------------------------------------------------------------------

    async def _fetch_feed(self, url: str) -> list[dict[str, Any]]:
        """Fetch an RSS/Atom feed and return parsed entries."""
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Nigehban/0.1 RSS-Ingestor"})
            resp.raise_for_status()
            content = resp.text

        return self._parse_feed_xml(content)

    def _parse_feed_xml(self, xml_content: str) -> list[dict[str, Any]]:
        """Parse RSS 2.0 or Atom feed XML into a list of entry dicts.

        Returns entries with keys: title, summary, link, published, source.
        """
        entries: list[dict[str, Any]] = []

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            logger.warning("Failed to parse feed XML")
            return entries

        # Detect format: RSS 2.0 vs Atom
        # RSS: <rss><channel><item>...
        # Atom: <feed xmlns="..."><entry>...

        # Try RSS 2.0 first
        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item"):
                entries.append({
                    "title": self._text(item, "title"),
                    "summary": self._text(item, "description") or self._text(item, "title"),
                    "link": self._text(item, "link"),
                    "published": self._text(item, "pubDate"),
                    "category": self._text(item, "category"),
                })
            return entries

        # Try Atom
        for entry_el in root.findall(f"{_ATOM_NS}entry"):
            link_el = entry_el.find(f"{_ATOM_NS}link")
            entries.append({
                "title": self._text(entry_el, f"{_ATOM_NS}title"),
                "summary": (
                    self._text(entry_el, f"{_ATOM_NS}summary")
                    or self._text(entry_el, f"{_ATOM_NS}content")
                    or self._text(entry_el, f"{_ATOM_NS}title")
                ),
                "link": link_el.get("href", "") if link_el is not None else "",
                "published": self._text(entry_el, f"{_ATOM_NS}published")
                             or self._text(entry_el, f"{_ATOM_NS}updated"),
                "category": "",
            })

        return entries

    # ------------------------------------------------------------------
    # Entry processing & deduplication
    # ------------------------------------------------------------------

    async def _process_entry(self, entry: dict[str, Any], source_url: str) -> bool:
        """Process a single feed entry: deduplicate and queue for analysis.

        Returns True if the entry is new and was queued.
        """
        claim = self._entry_to_claim(entry, source_url)
        if not claim:
            return False

        if await self._is_duplicate(claim["content_hash"]):
            return False

        await self._mark_seen(claim["content_hash"])

        # Optionally submit to the pipeline immediately
        # For now, just store in Redis as pending claims
        await self._store_pending_claim(claim)

        return True

    def _entry_to_claim(self, entry: dict[str, Any], source_url: str) -> dict[str, Any] | None:
        """Convert a feed entry into a claim dict, or None if not suitable."""
        title = (entry.get("title") or "").strip()
        summary = (entry.get("summary") or "").strip()

        # Skip entries with no meaningful text
        text = summary or title
        if not text or len(text) < 20:
            return None

        # Clean HTML tags from summary
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()

        content_hash = self._content_hash(text)

        return {
            "title": title[:512],
            "body": text[:5000],
            "source_url": entry.get("link", ""),
            "feed_url": source_url,
            "published": entry.get("published"),
            "category": entry.get("category", ""),
            "content_hash": content_hash,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _content_hash(text: str) -> str:
        """Generate a deterministic hash for deduplication."""
        normalized = text.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]

    async def _is_duplicate(self, content_hash: str) -> bool:
        """Check if a content hash has been seen recently."""
        try:
            client = redis_pool.client
            return bool(await client.exists(f"ingest:seen:{content_hash}"))
        except Exception:
            logger.warning("Redis dedup check failed for %s", content_hash, exc_info=True)
            return False

    async def _mark_seen(self, content_hash: str) -> None:
        """Mark a content hash as seen with a TTL."""
        try:
            client = redis_pool.client
            await client.setex(f"ingest:seen:{content_hash}", _CONTENT_HASH_TTL, "1")
        except Exception:
            logger.warning("Failed to mark %s as seen", content_hash, exc_info=True)

    async def _store_pending_claim(self, claim: dict[str, Any]) -> None:
        """Store a pending claim in Redis for batch processing."""
        import json

        try:
            client = redis_pool.client
            await client.rpush("ingest:pending_claims", json.dumps(claim))
            # Cap the queue length to prevent unbounded growth
            await client.ltrim("ingest:pending_claims", -1000, -1)
        except Exception:
            logger.warning("Failed to store pending claim", exc_info=True)

    # ------------------------------------------------------------------
    # XML helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _text(element: ET.Element, tag: str) -> str:
        """Safely extract text content from an XML sub-element."""
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return ""


# ---------------------------------------------------------------------------
# Convenience functions for periodic task scheduling
# ---------------------------------------------------------------------------

async def run_feed_ingestion() -> int:
    """Top-level entry point for periodic RSS feed ingestion.

    Reads feed URLs from settings and ingests all feeds.
    Suitable for calling from a Celery task or asyncio scheduler.
    """
    worker = RSSIngestionWorker()
    return await worker.ingest_rss_feeds(settings.RSS_FEED_URLS)


async def run_claim_check() -> list[dict[str, Any]]:
    """Top-level entry point for checking new claims from feeds.

    Returns list of new claim dicts. Suitable for periodic scheduling.
    """
    worker = RSSIngestionWorker()
    return await worker.check_new_claims()
