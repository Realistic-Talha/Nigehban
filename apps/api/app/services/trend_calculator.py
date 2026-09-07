"""Trend and spread-score computation for claims, scams, and media checks."""

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.core.redis import redis_pool

logger = logging.getLogger(__name__)

# Weight factors for spread-score computation
_WEIGHTS = {
    "report_volume": 0.30,      # Total number of reports
    "velocity": 0.25,           # Reports per hour (acceleration)
    "unique_reporters": 0.25,   # Distinct reporters (avoids spam counting)
    "geographic_spread": 0.20,  # Diversity of reporter locations
}


class TrendCalculator:
    """Compute spread/trending scores for entities and surface trending items.

    The spread score (0–100) is a weighted composite of:
      - Report volume (raw count)
      - Velocity (reports per hour over the time window)
      - Unique reporters (distinct users who reported the same entity)
      - Geographic spread (distinct regions / area codes)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def compute_spread_score(
        self,
        entity_id: str,
        entity_type: str,
    ) -> float:
        """Compute a 0–100 spread score for a given entity.

        Parameters
        ----------
        entity_id   : UUID of the claim / scam_report / media_check.
        entity_type : One of "claim", "scam_report", "media_check".

        Returns
        -------
        Normalized spread score in [0, 100].
        """
        metrics = await self._gather_metrics(entity_id, entity_type)

        # Normalize each factor to 0–1 range using log-scaled capping
        volume_norm = self._log_normalize(metrics["report_volume"], cap=500)
        velocity_norm = self._log_normalize(metrics["velocity"], cap=50)
        reporters_norm = self._log_normalize(metrics["unique_reporters"], cap=100)
        geo_norm = min(metrics["geographic_spread"] / 10.0, 1.0)  # cap at 10 regions

        score = (
            _WEIGHTS["report_volume"] * volume_norm
            + _WEIGHTS["velocity"] * velocity_norm
            + _WEIGHTS["unique_reporters"] * reporters_norm
            + _WEIGHTS["geographic_spread"] * geo_norm
        ) * 100.0

        score = round(max(0.0, min(100.0, score)), 2)

        # Cache in Redis for quick access
        await self._cache_score(entity_id, score)

        logger.info(
            "Spread score for %s/%s = %.2f (vol=%d vel=%.1f rep=%d geo=%d)",
            entity_type, entity_id, score,
            metrics["report_volume"], metrics["velocity"],
            metrics["unique_reporters"], metrics["geographic_spread"],
        )
        return score

    async def get_trending_items(
        self,
        limit: int = 10,
        time_window_hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Return the top trending entities across all types.

        Parameters
        ----------
        limit              : Max number of items to return.
        time_window_hours  : Look-back window in hours.

        Returns
        -------
        List of dicts with entity_id, entity_type, spread_score, and metadata.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
        results: list[dict[str, Any]] = []

        async with AsyncSessionLocal() as session:
            # Query TrendSnapshot for recent high-scoring entries
            from app.models.trend_snapshot import TrendSnapshot

            stmt = (
                select(TrendSnapshot)
                .where(TrendSnapshot.captured_at >= cutoff)
                .order_by(TrendSnapshot.spread_score.desc())
                .limit(limit)
            )
            rows = (await session.execute(stmt)).scalars().all()

            for row in rows:
                results.append({
                    "entity_id": str(row.related_entity_id),
                    "entity_type": row.entity_type,
                    "spread_score": row.spread_score,
                    "report_volume": row.report_volume,
                    "captured_at": row.captured_at.isoformat(),
                })

        # If no snapshots exist, compute on-the-fly from claims/scam_reports
        if not results:
            results = await self._compute_live_trending(cutoff, limit)

        return results

    # ------------------------------------------------------------------
    # Metric gathering
    # ------------------------------------------------------------------

    async def _gather_metrics(
        self,
        entity_id: str,
        entity_type: str,
    ) -> dict[str, float]:
        """Gather raw metrics for an entity from the database and Redis."""
        now = datetime.now(timezone.utc)
        window_24h = now - timedelta(hours=24)

        report_volume = 0
        unique_reporters = 0
        geographic_spread = 0
        recent_count = 0

        async with AsyncSessionLocal() as session:
            if entity_type == "claim":
                from app.models.claim import Claim
                stmt = select(func.count()).select_from(Claim).where(Claim.id == entity_id)
                report_volume = (await session.execute(stmt)).scalar() or 0
                unique_reporters = min(report_volume, report_volume)  # placeholder
            elif entity_type == "scam_report":
                from app.models.scam_report import ScamReport
                stmt = select(func.count()).select_from(ScamReport).where(
                    ScamReport.id == entity_id
                )
                report_volume = (await session.execute(stmt)).scalar() or 0
                # Count unique senders
                sender_stmt = select(func.count(func.distinct(ScamReport.sender_identifier))).where(
                    ScamReport.id == entity_id
                )
                unique_reporters = (await session.execute(sender_stmt)).scalar() or 0

        # Try to get velocity from Redis time-series keys
        redis_key = f"reports:{entity_type}:{entity_id}"
        try:
            client = redis_pool.client
            recent_count = await client.llen(redis_key)
        except Exception:
            recent_count = report_volume

        velocity = recent_count / 24.0 if recent_count > 0 else 0.0

        return {
            "report_volume": report_volume,
            "velocity": velocity,
            "unique_reporters": unique_reporters,
            "geographic_spread": geographic_spread,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _log_normalize(value: float, cap: float) -> float:
        """Log-scale normalization: maps [0, cap] → [0, 1] with diminishing returns."""
        if value <= 0:
            return 0.0
        return math.log(1 + value) / math.log(1 + cap)

    async def _cache_score(self, entity_id: str, score: float) -> None:
        """Cache the spread score in Redis with a 1-hour TTL."""
        try:
            client = redis_pool.client
            await client.setex(f"spread:{entity_id}", 3600, str(score))
        except Exception:
            logger.warning("Failed to cache spread score for %s", entity_id, exc_info=True)

    async def _compute_live_trending(
        self,
        cutoff: datetime,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fallback: compute trending items from raw tables when no snapshots exist."""
        results: list[dict[str, Any]] = []

        async with AsyncSessionLocal() as session:
            # Recent claims
            from app.models.claim import Claim
            stmt = (
                select(Claim.id, Claim.title, Claim.verdict, Claim.created_at)
                .where(Claim.created_at >= cutoff)
                .order_by(Claim.created_at.desc())
                .limit(limit)
            )
            rows = (await session.execute(stmt)).all()
            for row in rows:
                results.append({
                    "entity_id": str(row.id),
                    "entity_type": "claim",
                    "spread_score": 50.0,  # placeholder until computed
                    "report_volume": 1,
                    "captured_at": row.created_at.isoformat(),
                })

            # Recent scam reports
            from app.models.scam_report import ScamReport
            stmt = (
                select(ScamReport.id, ScamReport.risk_verdict, ScamReport.created_at)
                .where(ScamReport.created_at >= cutoff)
                .order_by(ScamReport.created_at.desc())
                .limit(limit)
            )
            rows = (await session.execute(stmt)).all()
            for row in rows:
                results.append({
                    "entity_id": str(row.id),
                    "entity_type": "scam_report",
                    "spread_score": 50.0,
                    "report_volume": 1,
                    "captured_at": row.created_at.isoformat(),
                })

        # Sort by score descending and trim
        results.sort(key=lambda r: r["spread_score"], reverse=True)
        return results[:limit]


# Module-level singleton
trend_calculator = TrendCalculator()
