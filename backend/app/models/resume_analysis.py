import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class ResumeAnalysis(UUIDPrimaryKeyMixin, Base):
    """One completed analysis run. Failures are tracked on the resume/job, not here,
    so the newest row here is always the current good analysis."""

    __tablename__ = "resume_analyses"
    __table_args__ = (
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)", name="score_range"
        ),
        Index("ix_resume_analyses_resume_created_at", "resume_id", "created_at"),
    )

    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE")
    )
    score: Mapped[int | None] = mapped_column(SmallInteger)
    summary: Mapped[str] = mapped_column(Text)
    detailed_result: Mapped[dict[str, Any]] = mapped_column(JSONB)
    rubric_version: Mapped[str] = mapped_column(String(50))
    prompt_version: Mapped[str] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(100))
    model_version: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )