"""Periodic trend snapshot job."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.claim import Claim
from app.models.media_check import MediaCheck
from app.models.scam_report import ScamReport
from app.models.trend_snapshot import TrendSnapshot
from app.services.trend_calculator import trend_calculator

logger = logging.getLogger(__name__)


async def run_trend_snapshot_job() -> int:
    """Compute spread scores for recent entities and insert snapshots."""
    count = 0
    async with AsyncSessionLocal() as session:
        # Recent claims with verdicts
        claims = (
            await session.execute(
                select(Claim).where(Claim.verdict.isnot(None)).order_by(Claim.created_at.desc()).limit(50)
            )
        ).scalars().all()

        for claim in claims:
            score = await trend_calculator.compute_spread_score(str(claim.id), "claim")
            snap = TrendSnapshot(
                id=uuid.uuid4(),
                related_entity_id=claim.id,
                entity_type="claim",
                report_volume=1,
                spread_score=score,
                captured_at=datetime.now(timezone.utc),
            )
            session.add(snap)
            claim.trend_score = score
            count += 1

        scams = (
            await session.execute(
                select(ScamReport).where(ScamReport.risk_verdict.isnot(None)).order_by(
                    ScamReport.created_at.desc()
                ).limit(50)
            )
        ).scalars().all()

        for scam in scams:
            score = await trend_calculator.compute_spread_score(str(scam.id), "scam_report")
            session.add(
                TrendSnapshot(
                    id=uuid.uuid4(),
                    related_entity_id=scam.id,
                    entity_type="scam_report",
                    report_volume=1,
                    spread_score=score,
                    captured_at=datetime.now(timezone.utc),
                )
            )
            count += 1

        media = (
            await session.execute(
                select(MediaCheck).where(MediaCheck.verdict.isnot(None)).order_by(
                    MediaCheck.created_at.desc()
                ).limit(30)
            )
        ).scalars().all()

        for m in media:
            score = await trend_calculator.compute_spread_score(str(m.id), "media_check")
            session.add(
                TrendSnapshot(
                    id=uuid.uuid4(),
                    related_entity_id=m.id,
                    entity_type="media_check",
                    report_volume=1,
                    spread_score=score,
                    captured_at=datetime.now(timezone.utc),
                )
            )
            count += 1

        await session.commit()
    logger.info("Trend snapshot job wrote %d snapshots", count)
    return count
