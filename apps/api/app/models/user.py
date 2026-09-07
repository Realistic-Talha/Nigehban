"""User model — a WhatsApp or web user."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    """A user identified by their WhatsApp number."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    whatsapp_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    language_preference: Mapped[str] = mapped_column(String(8), default="en")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
