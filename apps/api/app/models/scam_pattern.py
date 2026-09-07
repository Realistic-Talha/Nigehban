"""ScamPattern model — a known scam pattern for similarity matching."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScamPattern(Base):
    """A known scam pattern with embedding for similarity search."""

    __tablename__ = "scam_patterns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pattern_text: Mapped[str] = mapped_column(Text, nullable=False)
    scam_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ur: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    times_reported: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
