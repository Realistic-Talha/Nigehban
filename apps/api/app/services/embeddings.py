"""Embedding service — fastembed local vectors + pgvector similarity."""

import asyncio
import logging
import math
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

_embedder = None
_embedder_lock = asyncio.Lock()


async def _get_embedder():
    global _embedder
    if _embedder is not None:
        return _embedder
    async with _embedder_lock:
        if _embedder is None:
            from fastembed import TextEmbedding

            _embedder = TextEmbedding(model_name=settings.EMBEDDING_MODEL)
    return _embedder


class EmbeddingService:
    """Generate embeddings and perform pgvector similarity search."""

    async def generate_embedding(self, text: str) -> list[float]:
        if not text or not text.strip():
            return [0.0] * settings.EMBEDDING_DIM

        try:
            embedder = await _get_embedder()

            def _embed() -> list[float]:
                vectors = list(embedder.embed([text]))
                return list(vectors[0])

            return await asyncio.to_thread(_embed)
        except Exception:
            logger.exception("Embedding generation failed — using hash fallback")
            return self._hash_embedding(text)

    @staticmethod
    def _hash_embedding(text: str) -> list[float]:
        """Deterministic fallback when fastembed unavailable."""
        import hashlib
        import struct

        dim = settings.EMBEDDING_DIM
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        for i in range(dim):
            chunk = digest[i % len(digest): (i % len(digest)) + 4]
            if len(chunk) < 4:
                chunk = (chunk + digest)[:4]
            val = struct.unpack("!I", chunk[:4])[0]
            values.append((val / 2**32) * 2 - 1)
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]

    async def similarity_search(
        self,
        embedding: list[float],
        table_name: str,
        *,
        limit: int = 5,
        threshold: float = 0.82,
    ) -> list[dict[str, Any]]:
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        allowed_tables = {"claims", "scam_patterns", "media_checks"}
        if table_name not in allowed_tables:
            logger.error("Invalid table for similarity search: %s", table_name)
            return []

        sql = text(
            f"""
            SELECT *, 1 - (embedding <=> :embedding::vector) AS similarity
            FROM {table_name}
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
            """
        )

        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    sql,
                    {"embedding": embedding_str, "limit": limit},
                )
                rows = result.mappings().all()
        except Exception:
            # No pgvector extension (common on local Windows Postgres) — skip L2 hits.
            logger.warning("pgvector similarity unavailable — returning no L2 matches")
            return []

        return [
            dict(row)
            for row in rows
            if float(row.get("similarity", 0)) >= threshold
        ]


embedding_service = EmbeddingService()
