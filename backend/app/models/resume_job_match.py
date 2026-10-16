import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class ResumeJobMatch(UUIDPrimaryKeyMixin, Base):
    """Persisted, explainable match between one resume and one job description."""

    __tablename__ = "resume_job_matches"
    __table_args__ = (
        CheckConstraint("fit_percentage >= 0 AND fit_percentage <= 100", name="fit_percentage_range"),
        UniqueConstraint("resume_id", "job_description_id", name="uq_resume_job_match_pair"),
        Index("ix_resume_job_matches_resume_score", "resume_id", "fit_percentage"),
    )

    resume_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"))
    job_description_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_descriptions.id", ondelete="CASCADE"))
    fit_percentage: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    matching_skills: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    missing_required_skills: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    relevant_evidence: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    match_summary: Mapped[str] = mapped_column(String(1000), nullable=False)
    resume_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    job_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(50), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)