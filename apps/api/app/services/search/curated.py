"""Curated reference search from database."""

import logging

from sqlalchemy import or_, select

from app.core.database import AsyncSessionLocal
from app.models.curated_reference import CuratedReference
from app.services.search.models import SearchResult

logger = logging.getLogger(__name__)


async def curated_search(query: str, limit: int = 5) -> list[SearchResult]:
    """Keyword search against curated_references table."""
    q = f"%{query}%"
    try:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(CuratedReference)
                .where(
                    or_(
                        CuratedReference.title.ilike(q),
                        CuratedReference.description_en.ilike(q),
                        CuratedReference.url.ilike(q),
                    )
                )
                .limit(limit)
            )
            rows = (await session.execute(stmt)).scalars().all()
            results: list[SearchResult] = []
            for row in rows:
                # Also match keywords array
                if row.keywords:
                    keywords_lower = [k.lower() for k in row.keywords]
                    if not any(kw in query.lower() for kw in keywords_lower):
                        if not (
                            row.title.lower().find(query.lower()) >= 0
                            or (row.description_en and query.lower() in row.description_en.lower())
                        ):
                            continue
                results.append(
                    SearchResult(
                        title=row.title,
                        url=row.url,
                        snippet=row.description_en or row.title,
                        source="curated",
                    )
                )
            return results
    except Exception:
        logger.exception("Curated search failed")
        return []
