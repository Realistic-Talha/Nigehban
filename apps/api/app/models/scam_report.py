"""ScamReport model — a user-submitted or AI-generated scam report."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScamReport(Base):
    """A scam report with risk verdict and red flags."""

    __tablename__ = "scam_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    submitted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    scam_type: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    risk_verdict: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    explanation_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation_ur: Mapped[str | None] = mapped_column(Text, nullable=True)
    red_flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sender_identifier: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reported_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
