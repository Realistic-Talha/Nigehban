"""PipelineOrchestrator — routes through Detection Kernel (meta locks verdict)."""

import logging
from datetime import datetime, timezone
from typing import Any

from app.agents.intake import IntakeAgent
from app.cache.layers import content_hash, dedup_cache
from app.core.redis import redis_pool
from app.engines.kernel import detection_kernel

logger = logging.getLogger(__name__)


def _is_weak_cache_hit(cached: dict[str, Any]) -> bool:
    """Do not reuse abstentions — search/NLI quality changes across deploys."""
    verdict = str(cached.get("verdict") or "").lower()
    try:
        conf = float(cached.get("confidence") or cached.get("confidence_score") or 0)
    except (TypeError, ValueError):
        conf = 0.0
    if cached.get("abstain") is True:
        return True
    if verdict in ("unverified", "inconclusive", "needs_caution") and conf < 50:
        return True
    # Retrieval-empty explanations from older engine versions
    expl = (cached.get("explanation_en") or "").lower()
    if "limited signals" in expl or "did not find a claimreview" in expl:
        return True
    return False


class PipelineOrchestrator:
    """Intake routes path; DetectionKernel owns verdict authority."""

    def __init__(self) -> None:
        self.intake = IntakeAgent()

    async def process(
        self,
        input_data: dict[str, Any],
        check_id: str,
        check_type: str,
    ) -> dict[str, Any]:
        logger.info("Pipeline started | check_id=%s check_type=%s", check_id, check_type)
        await self._publish_pipeline_event(check_id, "pipeline_started", "Detection kernel started")

        text_for_hash = input_data.get("text", "") or ""
        if text_for_hash:
            cached = await dedup_cache.get(content_hash(text_for_hash))
            if cached and not _is_weak_cache_hit(cached):
                expl = (cached.get("explanation_en") or "").lower()
                if "mock judge" in expl or "mock scam" in expl or "mock fact-check" in expl:
                    logger.info("Ignoring stale mock L1 cache for check %s", check_id)
                else:
                    cached.setdefault("id", check_id)
                    cached.setdefault("type", check_type)
                    await self._publish_pipeline_event(check_id, "pipeline_complete", "Cached verdict")
                    return cached
            elif cached:
                logger.info("Ignoring weak L1 cache (unverified/abstain) for check %s", check_id)

            from app.cache.layers import embedding_cache

            l2 = await embedding_cache.get(text_for_hash)
            if l2 and not _is_weak_cache_hit(l2):
                expl = (l2.get("explanation_en") or "").lower()
                if "mock judge" in expl or "mock scam" in expl or "mock fact-check" in expl or expl == "cleared mock":
                    logger.info("Ignoring stale mock L2 cache for check %s", check_id)
                else:
                    l2.setdefault("id", check_id)
                    l2.setdefault("type", check_type)
                    await self._publish_pipeline_event(check_id, "pipeline_complete", "Similar verdict")
                    return l2
            elif l2:
                logger.info("Ignoring weak L2 cache for check %s", check_id)

        # Prefer API check_type for path when intake is wrong
        path_from_type = {
            "claim": "factcheck",
            "scam_report": "scamcheck",
            "media_check": "mediacheck",
        }.get(check_type)

        routing_result = await self.intake.execute(input_data, check_id, check_type)
        routing = routing_result.get("output", {})
        path = path_from_type or routing.get("path", "factcheck")

        # Merge intake language; force image OCR when API sent image
        merged = {**input_data}
        if input_data.get("media_url") and check_type == "scam_report":
            merged.setdefault("input_type", input_data.get("input_type") or "image")
        if routing.get("language"):
            merged.setdefault("language", routing["language"])

        final = await detection_kernel.process(merged, check_id, check_type, path=path)

        # Prepend intake to trail
        trail = final.get("agent_trail") or []
        final["agent_trail"] = [
            {
                "agent_name": "intake",
                "status": "complete",
                "output_summary": str(routing)[:200],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            *trail,
        ]

        logger.info(
            "Pipeline complete | check_id=%s verdict=%s confidence=%.1f abstain=%s",
            check_id,
            final.get("verdict"),
            final.get("confidence", 0),
            final.get("abstain"),
        )
        await self._publish_pipeline_event(check_id, "pipeline_complete", "Locked verdict ready")
        return final

    async def _publish_pipeline_event(self, check_id: str, status: str, summary: str = "") -> None:
        import json as _json

        channel = f"pipeline:{check_id}"
        payload = _json.dumps({
            "agent_name": "pipeline",
            "status": status,
            "output_summary": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        try:
            await redis_pool.client.publish(channel, payload)
        except Exception:
            logger.warning("Failed to publish pipeline event", exc_info=True)


pipeline = PipelineOrchestrator()
