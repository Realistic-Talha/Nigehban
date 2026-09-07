"""Media retention cleanup stub — delete old local/MinIO objects."""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.media_check import MediaCheck

logger = logging.getLogger(__name__)

RETENTION_DAYS = 30


async def cleanup_old_media() -> int:
    """Remove media files older than retention period (local paths only)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    removed = 0
    local_dir = Path(settings.LOCAL_STORAGE_DIR)

    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(MediaCheck).where(MediaCheck.created_at < cutoff)
            )
        ).scalars().all()

        for row in rows:
            if row.file_url and str(local_dir) in row.file_url:
                path = Path(row.file_url.split("?")[0])
                if path.exists():
                    path.unlink(missing_ok=True)
                    removed += 1

    logger.info("Cleanup removed %d local media files", removed)
    return removed
