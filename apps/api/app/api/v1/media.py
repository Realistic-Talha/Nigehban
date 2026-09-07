"""Media file serving endpoint."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.media_check import MediaCheck

router = APIRouter(prefix="/media")


@router.get("/{check_id}")
async def get_media_file(
    check_id: uuid.UUID,
    artifact: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Serve uploaded media or a forensic overlay artifact for a check."""
    result = await db.execute(select(MediaCheck).where(MediaCheck.id == check_id))
    record = result.scalar_one_or_none()
    if not record or not record.file_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    target = record.file_url
    if artifact and isinstance(record.signals, dict):
        report = record.signals.get("authenticity_report") or {}
        overlays = report.get("overlays") or {}
        # Also check engine features
        if artifact not in overlays:
            for eng in record.signals.get("engines") or []:
                feats = eng.get("features") or {}
                ov = feats.get("overlays") or {}
                if artifact in ov:
                    overlays = ov
                    break
        if artifact not in overlays:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Artifact '{artifact}' not found")
        target = overlays[artifact]

    path = Path(str(target).split("?")[0])
    local_dir = Path(settings.LOCAL_STORAGE_DIR)
    if not path.is_absolute():
        # uploads\xxx or uploads/xxx
        name = path.name
        path = local_dir / name
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not on disk")

    return FileResponse(path)
