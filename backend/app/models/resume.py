import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Resume(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One row per uploaded resume file, plus what we extracted from it."""

    __tablename__ = "resumes"
    __table_args__ = (
        UniqueConstraint("owner_id", "file_hash", name="uq_resumes_owner_file_hash"),
        CheckConstraint(
            "extraction_status IN ('queued', 'processing', 'completed', 'failed')",
            name="extraction_status_valid",
        ),
        CheckConstraint(
            "analysis_status IN ('not_started', 'queued', 'processing', 'completed', 'failed')",
            name="analysis_status_valid",
        ),
        CheckConstraint(
            "extraction_method IS NULL OR extraction_method IN ('native_text', 'ocr')",
            name="extraction_method_valid",
        ),
        CheckConstraint("file_size > 0", name="file_size_positive"),
        CheckConstraint("char_length(file_hash) = 64", name="file_hash_length"),
        Index("ix_resumes_owner_uploaded_at", "owner_id", "uploaded_at"),
        Index("ix_resumes_owner_extraction_status", "owner_id", "extraction_status"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="RESTRICT")
    )

    # File details
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    mime_type: Mapped[str] = mapped_column(String(100))
    file_hash: Mapped[str] = mapped_column(String(64))
    file_size: Mapped[int] = mapped_column(BigInteger)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Extracted candidate info (all optional: we never invent missing data)
    candidate_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(320))
    mobile: Mapped[str | None] = mapped_column(String(50))
    location: Mapped[str | None] = mapped_column(String(255))
    skills: Mapped[list[Any]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    # deferred = not loaded unless asked for, so list queries stay fast
    extracted_text: Mapped[str | None] = mapped_column(Text, deferred=True)
    extraction_method: Mapped[str | None] = mapped_column(String(20))
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Processing state
    extraction_status: Mapped[str] = mapped_column(
        String(20), server_default="queued"
    )
    analysis_status: Mapped[str] = mapped_column(
        String(20), server_default="not_started"
    )
    error_message: Mapped[str | None] = mapped_column(Text)  # safe, user-facing only