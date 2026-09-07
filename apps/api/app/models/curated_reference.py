"""CuratedReference model — verified grounding URLs for fact-check search."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CuratedReference(Base):
    """A curated, trusted reference URL for evidence grounding."""

    __tablename__ = "curated_references"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    url: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(256), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ur: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
