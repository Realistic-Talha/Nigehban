"""Fact-check endpoints — submit claims and browse the feed."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.stream import create_sse_response
from app.core.database import get_db
from app.models.claim import Claim
from app.schemas.requests import FactCheckSubmission
from app.schemas.responses import FeedItem
from app.workers.redis_queue import enqueue_pipeline

router = APIRouter(prefix="/factcheck")


@router.post("/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_fact_check(
    body: FactCheckSubmission,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Accept a claim for fact-checking and enqueue processing."""
    claim = Claim(
        title=body.text[:512],
        body=body.text,
        language=body.language,
    )
    db.add(claim)
    await db.flush()

    check_id = str(claim.id)
    input_data = {
        "text": body.text,
        "source_url": body.url,
        "language": body.language,
    }
    await enqueue_pipeline(check_id, "claim", input_data)

    return {"id": check_id, "status": "processing"}


@router.get("/feed", response_model=list[FeedItem])
async def get_feed(
    cursor: str | None = Query(
        None,
        description="Cursor for keyset pagination (previous item's created_at ISO string)",
    ),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    category: str | None = Query(None, description="Filter by category"),
    q: str | None = Query(None, description="Full-text search query"),
    db: AsyncSession = Depends(get_db),
) -> list[Claim]:
    """Return a paginated feed of fact-checked claims, newest first."""
    stmt = select(Claim).where(Claim.verdict.isnot(None))

    if category:
        stmt = stmt.where(Claim.category == category)

    if q:
        stmt = stmt.where(Claim.title.ilike(f"%{q}%") | Claim.body.ilike(f"%{q}%"))

    if cursor:
        stmt = stmt.where(Claim.created_at < cursor)

    stmt = stmt.order_by(Claim.created_at.desc()).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/feed/stream")
async def get_feed_stream():
    """SSE endpoint — streams new feed items as they are processed."""
    return create_sse_response("feed:updates", timeout=300.0)
