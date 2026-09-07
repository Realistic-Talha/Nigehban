"""Media-check endpoints — image and video authenticity analysis."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.media_check import MediaCheck
from app.services.storage import storage
from app.workers.redis_queue import enqueue_pipeline

router = APIRouter(prefix="/mediacheck")

_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
_VIDEO_TYPES = {"video/mp4"}
_MAX_IMAGE_SIZE = 10 * 1024 * 1024
_MAX_VIDEO_SIZE = 50 * 1024 * 1024


@router.post("/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_media_check(
    media_type: str = Form(..., description="image or video"),
    file: UploadFile | None = File(None),
    url: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit an image or video for authenticity analysis."""
    if not file and not url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either a file upload or URL must be provided.",
        )

    file_url: str | None = url

    if file and file.filename:
        content_type = file.content_type or ""

        if media_type == "image":
            if content_type not in _IMAGE_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unsupported image format '{content_type}'. Accepted: JPG, PNG, WebP.",
                )
        elif media_type == "video":
            if content_type not in _VIDEO_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unsupported video format '{content_type}'. Accepted: MP4.",
                )

        content = await file.read()
        file_size = len(content)

        if media_type == "image" and file_size > _MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Image too large ({file_size} bytes). Maximum is 10 MB.",
            )
        if media_type == "video" and file_size > _MAX_VIDEO_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Video too large ({file_size} bytes). Maximum is 50 MB.",
            )

        file_url = await storage.upload_file(content, file.filename, content_type)

    check = MediaCheck(
        media_type=media_type,
        file_url=file_url,
    )
    db.add(check)
    await db.flush()

    check_id = str(check.id)
    input_data: dict = {
        "media_type": media_type,
        "media_url": file_url,
    }

    await enqueue_pipeline(check_id, "media_check", input_data)

    return {"id": check_id, "status": "processing"}
