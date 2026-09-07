"""TrendSnapshot model — point-in-time trending metrics for an entity."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TrendSnapshot(Base):
    """A snapshot of trending metrics for a claim, scam, or media check."""

    __tablename__ = "trend_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    related_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)  # claim | scam_report | media_check
    report_volume: Mapped[int] = mapped_column(Integer, default=0)
    spread_score: Mapped[float] = mapped_column(Float, default=0.0)

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
