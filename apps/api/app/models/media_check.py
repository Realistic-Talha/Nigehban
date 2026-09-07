"""MediaCheck model — image/video authenticity analysis result."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MediaCheck(Base):
    """An image or video authenticity check with forensic signals."""

    __tablename__ = "media_checks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    media_type: Mapped[str] = mapped_column(String(16), nullable=False)  # image | video
    file_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    authenticity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    signals: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(32), nullable=True)
    explanation_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation_ur: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
