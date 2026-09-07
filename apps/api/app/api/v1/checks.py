"""Checks endpoint — retrieve full detail and agent trail for any check."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.stream import create_sse_response
from app.core.database import get_db
from app.models.agent_log import AgentLog
from app.models.claim import Claim
from app.models.media_check import MediaCheck
from app.models.scam_report import ScamReport

router = APIRouter(prefix="/checks")


@router.get("/{check_id}")
async def get_check_detail(
    check_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return full verdict detail plus agent reasoning trail for a specific check.

    Looks up across claims, scam_reports, and media_checks tables.
    """
    # Try each table
    record: Claim | ScamReport | MediaCheck | None = None
    check_type: str = ""

    for model, ctype in [(Claim, "claim"), (ScamReport, "scam_report"), (MediaCheck, "media_check")]:
        result = await db.execute(select(model).where(model.id == check_id))
        record = result.scalar_one_or_none()
        if record:
            check_type = ctype
            break

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check not found")

    # Fetch agent trail
    logs_result = await db.execute(
        select(AgentLog)
        .where(AgentLog.parent_check_id == check_id)
        .order_by(AgentLog.created_at)
    )
    logs = logs_result.scalars().all()

    red_flags: list | None = None
    sources: list | None = None
    engines = None
    abstain = None
    verdict = ""
    confidence: float | None = None
    explanation_en: str | None = None
    explanation_ur: str | None = None
    created_at = None
    is_processing = True
    authenticity_report = None
    domain_shift_warning = None
    media_url = None

    if isinstance(record, Claim):
        verdict = record.verdict or "unverified"
        confidence = record.confidence_score
        explanation_en = record.explanation_en
        explanation_ur = record.explanation_ur
        sources = record.sources
        created_at = record.created_at
        is_processing = record.verdict is None
    elif isinstance(record, ScamReport):
        verdict = record.risk_verdict or "needs_caution"
        confidence = record.confidence_score
        explanation_en = record.explanation_en
        explanation_ur = record.explanation_ur
        rf = record.red_flags
        if isinstance(rf, dict):
            red_flags = rf.get("flags")
            engines = rf.get("engines")
            abstain = rf.get("abstain")
        else:
            red_flags = rf
        created_at = record.created_at
        is_processing = record.risk_verdict is None
    elif isinstance(record, MediaCheck):
        is_processing = record.verdict is None
        verdict = record.verdict or ("" if is_processing else "inconclusive")
        confidence = record.authenticity_score
        explanation_en = record.explanation_en
        explanation_ur = record.explanation_ur
        created_at = record.created_at
        authenticity_report = None
        domain_shift_warning = None
        media_url = record.file_url
        if isinstance(record.signals, dict):
            engines = record.signals.get("engines")
            abstain = record.signals.get("abstain")
            authenticity_report = record.signals.get("authenticity_report")
            domain_shift_warning = record.signals.get("domain_shift_warning")

    if is_processing:
        status_val = "processing"
    elif verdict == "error":
        status_val = "error"
    else:
        status_val = "complete"

    payload = {
        "id": str(check_id),
        "type": check_type,
        "status": status_val,
        "verdict": verdict,
        "confidence": confidence,
        "confidence_score": confidence,
        "explanation_en": explanation_en,
        "explanation_ur": explanation_ur,
        "sources": sources,
        "red_flags": red_flags,
        "engines": engines,
        "abstain": abstain,
        "agent_trail": [
            {
                "agent_name": log.agent_name,
                "status": "complete",
                "output_summary": log.output_summary,
                "timestamp": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "created_at": created_at.isoformat() if created_at else None,
    }
    if check_type == "media_check":
        payload["media_url"] = media_url
        payload["domain_shift_warning"] = domain_shift_warning
        payload["authenticity_report"] = authenticity_report
    return payload


@router.get("/{check_id}/stream")
async def stream_check_progress(check_id: uuid.UUID):
    """SSE endpoint — streams pipeline progress events for a specific check.

    Subscribes to Redis channel ``pipeline:{check_id}`` and yields events
    until the judge agent completes or the connection times out.
    """
    return create_sse_response(f"pipeline:{check_id}", timeout=60.0)
