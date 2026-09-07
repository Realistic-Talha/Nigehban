"""Reports endpoint — user-submitted scam/misinformation reports."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.scam_report import ScamReport
from app.schemas.requests import UserReport
from app.workers.redis_queue import enqueue_pipeline

router = APIRouter(prefix="/reports")


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_report(
    body: UserReport,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Accept a user-submitted scam or misinformation report."""
    report = ScamReport(
        submitted_text=body.text,
        scam_type=[body.scam_type] if body.scam_type else None,
        sender_identifier=body.sender_identifier,
    )
    db.add(report)
    await db.flush()

    check_id = str(report.id)
    input_data: dict = {
        "text": body.text,
        "language": "en",
    }
    if body.sender_identifier:
        input_data["sender_identifier"] = body.sender_identifier

    await enqueue_pipeline(check_id, "scam_report", input_data)

    return {"id": check_id, "status": "submitted"}
