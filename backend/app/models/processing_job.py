import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProcessingJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Work log: one row per extraction or analysis job. Retries update the same row."""

    __tablename__ = "processing_jobs"
    __table_args__ = (
        CheckConstraint(
            "job_type IN ('extraction', 'analysis')", name="job_type_valid"
        ),
        CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed')",
            name="status_valid",
        ),
        CheckConstraint("attempt_count >= 0", name="attempt_count_non_negative"),
        Index("ix_processing_jobs_resume_job_type", "resume_id", "job_type"),
    )

    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE")
    )
    job_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), server_default="queued")
    attempt_count: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(SmallInteger, server_default=text("3"))
    celery_task_id: Mapped[str | None] = mapped_column(String(255))
    last_error: Mapped[str | None] = mapped_column(Text)  # internal only
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))