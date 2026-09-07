"""Multi-layer Redis cache for the verification pipeline."""

import hashlib
import json
import logging
from typing import Any

from app.core.redis import redis_pool
from app.services.embeddings import embedding_service

logger = logging.getLogger(__name__)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class CacheLayer:
    async def get(self, key: str) -> Any | None:
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        raise NotImplementedError


class DeduplicationCache(CacheLayer):
    """L1 — exact text hash → cached verdict."""

    async def get(self, key: str) -> Any | None:
        try:
            client = redis_pool.client
            raw = await client.get(f"dedup:{key}")
            return json.loads(raw) if raw else None
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 86400) -> None:
        try:
            client = redis_pool.client
            await client.setex(f"dedup:{key}", ttl_seconds, json.dumps(value))
        except Exception:
            logger.warning("L1 cache set failed", exc_info=True)


class EmbeddingSimilarityCache(CacheLayer):
    """L2 — near-duplicate via embedding similarity."""

    async def get(self, text: str) -> Any | None:
        try:
            embedding = await embedding_service.generate_embedding(text)
            similar = await embedding_service.similarity_search(
                embedding, "scam_reports", limit=1, threshold=0.92
            )
            if not similar:
                similar = await embedding_service.similarity_search(
                    embedding, "claims", limit=1, threshold=0.92
                )
            if similar:
                row = similar[0]
                verdict = row.get("risk_verdict") or row.get("verdict")
                if verdict:
                    return {
                        "verdict": verdict,
                        "confidence": row.get("confidence_score"),
                        "explanation_en": row.get("explanation_en"),
                        "explanation_ur": row.get("explanation_ur"),
                        "sources": row.get("sources"),
                        "cache_hit": "L2",
                    }
        except Exception:
            logger.warning("L2 cache get failed", exc_info=True)
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 86400) -> None:
        pass  # L2 reads from DB embeddings


class EvidenceCache(CacheLayer):
    """L3 — cached search results for a claim."""

    async def get(self, key: str) -> Any | None:
        try:
            client = redis_pool.client
            raw = await client.get(f"evidence:{key}")
            return json.loads(raw) if raw else None
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 21600) -> None:
        try:
            client = redis_pool.client
            await client.setex(f"evidence:{key}", ttl_seconds, json.dumps(value))
        except Exception:
            logger.warning("L3 cache set failed", exc_info=True)


class ResponseCache(CacheLayer):
    """L4 — full verdict response cache."""

    async def get(self, key: str) -> Any | None:
        try:
            client = redis_pool.client
            raw = await client.get(f"verdict:{key}")
            return json.loads(raw) if raw else None
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        try:
            client = redis_pool.client
            await client.setex(f"verdict:{key}", ttl_seconds, json.dumps(value))
        except Exception:
            logger.warning("L4 cache set failed", exc_info=True)


dedup_cache = DeduplicationCache()
embedding_cache = EmbeddingSimilarityCache()
evidence_cache = EvidenceCache()
response_cache = ResponseCache()
