"""Dashboard endpoints — trending items and aggregate statistics."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func as sa_func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.claim import Claim
from app.models.media_check import MediaCheck
from app.models.scam_report import ScamReport
from app.models.trend_snapshot import TrendSnapshot

router = APIRouter(prefix="/dashboard")


@router.get("/trending")
async def get_trending(
    window: str = Query("24h", description="Time window: 24h, 7d, or 30d"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return the top trending items ranked by spread score within the given window."""
    now = datetime.now(timezone.utc)
    window_map = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    since = now - window_map.get(window, timedelta(hours=24))

    stmt = (
        select(TrendSnapshot)
        .where(TrendSnapshot.captured_at >= since)
        .order_by(desc(TrendSnapshot.spread_score))
        .limit(limit)
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    enriched: list[dict] = []
    for s in snapshots:
        item = {
            "id": str(s.id),
            "related_entity_id": str(s.related_entity_id),
            "entity_type": s.entity_type,
            "report_volume": s.report_volume,
            "spread_score": s.spread_score,
            "captured_at": s.captured_at.isoformat(),
            "title": None,
            "verdict": None,
        }
        if s.entity_type == "claim":
            claim = await db.get(Claim, s.related_entity_id)
            if claim:
                item["title"] = claim.title
                item["verdict"] = claim.verdict
        elif s.entity_type == "scam_report":
            scam = await db.get(ScamReport, s.related_entity_id)
            if scam:
                item["title"] = (scam.submitted_text or scam.extracted_text or "")[:128]
                item["verdict"] = scam.risk_verdict
        elif s.entity_type == "media_check":
            media = await db.get(MediaCheck, s.related_entity_id)
            if media:
                item["title"] = f"Media check ({media.media_type})"
                item["verdict"] = media.verdict
        enriched.append(item)

    return enriched


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return aggregate counts across all check tables."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    claims_count = (await db.execute(select(sa_func.count(Claim.id)))).scalar() or 0
    scams_count = (await db.execute(select(sa_func.count(ScamReport.id)))).scalar() or 0
    media_count = (await db.execute(select(sa_func.count(MediaCheck.id)))).scalar() or 0

    claims_today = (
        await db.execute(
            select(sa_func.count(Claim.id)).where(Claim.created_at >= today_start)
        )
    ).scalar() or 0
    scams_today = (
        await db.execute(
            select(sa_func.count(ScamReport.id)).where(ScamReport.created_at >= today_start)
        )
    ).scalar() or 0
    media_today = (
        await db.execute(
            select(sa_func.count(MediaCheck.id)).where(MediaCheck.created_at >= today_start)
        )
    ).scalar() or 0

    return {
        "total_claims": claims_count,
        "total_scams": scams_count,
        "total_media_checks": media_count,
        "checks_today": claims_today + scams_today + media_today,
    }
