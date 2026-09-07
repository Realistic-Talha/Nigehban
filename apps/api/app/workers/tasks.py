"""Background pipeline task runner."""

import json
import logging
import uuid
from datetime import datetime, timezone

from app.agents.orchestrator import pipeline
from app.cache.layers import content_hash, dedup_cache, response_cache
from app.core.database import AsyncSessionLocal
from app.core.redis import redis_pool
from app.services.embeddings import embedding_service

logger = logging.getLogger(__name__)


async def run_pipeline_task(check_id: str, check_type: str, input_data: dict) -> None:
    """Run the full pipeline and persist results to the database."""
    try:
        result = await pipeline.process(input_data, check_id, check_type)

        async with AsyncSessionLocal() as session:
            await _save_result(session, check_id, check_type, result, input_data)
            await session.commit()

        await _publish_feed_update(check_id, check_type, result)
        await response_cache.set(check_id, result)

        text = input_data.get("text", "")
        if text:
            # Never persist mock-LLM responses into L1 (shared Redis across providers).
            expl = (result.get("explanation_en") or "").lower()
            from app.agents.orchestrator import _is_weak_cache_hit

            if (
                "mock judge" not in expl
                and "mock scam" not in expl
                and "mock fact-check" not in expl
                and not _is_weak_cache_hit(result)
            ):
                await dedup_cache.set(content_hash(text), result)

        logger.info(
            "Pipeline task finished | check_id=%s type=%s verdict=%s",
            check_id,
            check_type,
            result.get("verdict"),
        )
    except Exception:
        logger.exception(
            "Pipeline task FAILED | check_id=%s type=%s", check_id, check_type,
        )
        await _mark_error(check_id, check_type)


async def _save_result(
    session,
    check_id: str,
    check_type: str,
    result: dict,
    input_data: dict,
) -> None:
    from sqlalchemy import select

    verdict = result.get("verdict")
    confidence = result.get("confidence")
    explanation_en = result.get("explanation_en")
    explanation_ur = result.get("explanation_ur")
    sources = result.get("sources")
    text = input_data.get("text", "") or input_data.get("submitted_text", "")

    if check_type == "claim":
        from app.models.claim import Claim

        stmt = select(Claim).where(Claim.id == check_id)
        record = (await session.execute(stmt)).scalar_one_or_none()
        if record:
            record.verdict = verdict
            record.confidence_score = confidence
            record.explanation_en = explanation_en
            record.explanation_ur = explanation_ur
            record.sources = sources
            record.category = result.get("category") or record.category
            if text:
                record.content_hash = content_hash(text)
                record.embedding = await embedding_service.generate_embedding(text)

    elif check_type == "scam_report":
        from app.models.scam_report import ScamReport

        stmt = select(ScamReport).where(ScamReport.id == check_id)
        record = (await session.execute(stmt)).scalar_one_or_none()
        if record:
            record.risk_verdict = verdict
            record.confidence_score = confidence
            record.explanation_en = explanation_en
            record.explanation_ur = explanation_ur
            # Persist kernel evidence (JSON column accepts list or dict)
            record.red_flags = {
                "flags": result.get("red_flags") or [],
                "engines": result.get("engines") or [],
                "evidence": result.get("evidence") or [],
                "abstain": result.get("abstain"),
                "calibration": result.get("calibration"),
            }
            embed_text = text or record.submitted_text or record.extracted_text or ""
            if embed_text:
                record.content_hash = content_hash(embed_text)
                record.embedding = await embedding_service.generate_embedding(embed_text)

    elif check_type == "media_check":
        from app.models.media_check import MediaCheck
        from app.models.media_fingerprint import MediaFingerprint
        from app.services.media_fingerprint import compute_image_fingerprint

        stmt = select(MediaCheck).where(MediaCheck.id == check_id)
        record = (await session.execute(stmt)).scalar_one_or_none()
        if record:
            record.verdict = verdict
            record.authenticity_score = confidence
            record.explanation_en = explanation_en
            record.explanation_ur = explanation_ur
            record.signals = {
                "engines": result.get("engines") or [],
                "evidence": result.get("evidence") or [],
                "abstain": result.get("abstain"),
                "domain_shift_warning": result.get("domain_shift_warning"),
                "calibration": result.get("calibration"),
                "authenticity_report": result.get("authenticity_report"),
                "raw": result.get("signals"),
            }
            if record.file_url:
                fp = await compute_image_fingerprint(record.file_url)
                if fp:
                    record.file_hash = fp.get("file_hash")
                    session.add(
                        MediaFingerprint(
                            id=uuid.uuid4(),
                            media_check_id=record.id,
                            phash=fp.get("phash"),
                            file_hash=fp.get("file_hash"),
                        )
                    )


async def _publish_feed_update(check_id: str, check_type: str, result: dict) -> None:
    try:
        client = redis_pool.client
        payload = json.dumps({
            "id": check_id,
            "type": check_type,
            "verdict": result.get("verdict"),
            "confidence": result.get("confidence"),
            "explanation_en": result.get("explanation_en"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await client.publish("feed:updates", payload)
    except Exception:
        logger.warning("Could not publish feed:updates for %s", check_id, exc_info=True)


async def _mark_error(check_id: str, check_type: str) -> None:
    try:
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            if check_type == "claim":
                from app.models.claim import Claim
                stmt = select(Claim).where(Claim.id == check_id)
                record = (await session.execute(stmt)).scalar_one_or_none()
                if record:
                    record.verdict = "error"
                    record.explanation_en = "An internal error occurred. Please try again."
            elif check_type == "scam_report":
                from app.models.scam_report import ScamReport
                stmt = select(ScamReport).where(ScamReport.id == check_id)
                record = (await session.execute(stmt)).scalar_one_or_none()
                if record:
                    record.risk_verdict = "error"
                    record.explanation_en = "An internal error occurred. Please try again."
            elif check_type == "media_check":
                from app.models.media_check import MediaCheck
                stmt = select(MediaCheck).where(MediaCheck.id == check_id)
                record = (await session.execute(stmt)).scalar_one_or_none()
                if record:
                    record.verdict = "error"
                    record.explanation_en = "An internal error occurred. Please try again."
            await session.commit()
    except Exception:
        logger.warning("Could not mark %s as errored", check_id, exc_info=True)
