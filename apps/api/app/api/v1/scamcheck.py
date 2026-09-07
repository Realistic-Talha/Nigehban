"""Scam-check endpoints — submit suspicious text and search the scam database."""

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.scam_report import ScamReport
from app.models.scam_pattern import ScamPattern
from app.services.storage import storage
from app.workers.redis_queue import enqueue_pipeline

router = APIRouter(prefix="/scamcheck")


@router.post("/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_scam_check(
    text: str | None = Form(None),
    file: UploadFile | None = File(None),
    language: str = Form("en"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Accept text or a screenshot for scam analysis."""
    file_url: str | None = None

    if file and file.filename:
        content = await file.read()
        content_type = file.content_type or "image/png"
        file_url = await storage.upload_file(content, file.filename, content_type)

    report = ScamReport(
        submitted_text=text,
        extracted_text=text,
    )
    db.add(report)
    await db.flush()

    check_id = str(report.id)
    input_data: dict = {
        "text": text or "",
        "language": language,
    }
    if file_url:
        input_data["media_url"] = file_url
        input_data["input_type"] = "image"

    await enqueue_pipeline(check_id, "scam_report", input_data)

    return {"id": check_id, "status": "processing"}


@router.get("/search")
async def search_scam_database(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Full-text search across known scam patterns and past reports."""
    pattern_stmt = (
        select(ScamPattern)
        .where(
            ScamPattern.pattern_text.ilike(f"%{q}%")
            | ScamPattern.description_en.ilike(f"%{q}%")
        )
        .limit(limit)
    )
    pattern_result = await db.execute(pattern_stmt)
    patterns = pattern_result.scalars().all()

    results: list[dict] = [
        {
            "id": str(p.id),
            "pattern_text": p.pattern_text,
            "scam_type": p.scam_type,
            "description_en": p.description_en,
            "description_ur": p.description_ur,
            "times_reported": p.times_reported,
            "source": "pattern",
        }
        for p in patterns
    ]

    report_stmt = (
        select(ScamReport)
        .where(
            ScamReport.risk_verdict.isnot(None),
            (
                ScamReport.submitted_text.ilike(f"%{q}%")
                | ScamReport.extracted_text.ilike(f"%{q}%")
            ),
        )
        .order_by(ScamReport.created_at.desc())
        .limit(limit)
    )
    report_result = await db.execute(report_stmt)
    reports = report_result.scalars().all()

    results.extend(
        {
            "id": str(r.id),
            "pattern_text": (r.submitted_text or r.extracted_text or "")[:256],
            "scam_type": (r.scam_type or ["unknown"])[0] if r.scam_type else "unknown",
            "description_en": r.explanation_en,
            "description_ur": r.explanation_ur,
            "times_reported": None,
            "source": "report",
            "verdict": r.risk_verdict,
        }
        for r in reports
    )

    return results[:limit]
