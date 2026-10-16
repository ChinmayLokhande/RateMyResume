from typing import Any

from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class JobDescription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A reusable job description that resumes can be matched against."""

    __tablename__ = "job_descriptions"
    __table_args__ = (Index("ix_job_descriptions_active", "is_active"),)

    title: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str] = mapped_column(Text)
    required_skills: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    preferred_skills: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    responsibility_keywords: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    experience_years: Mapped[int | None] = mapped_column()
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")