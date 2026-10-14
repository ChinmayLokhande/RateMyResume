import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import analysis_key, cache_delete, dashboard_key
from app.models import ProcessingJob, Resume


def invalidate_dashboard(owner_id: uuid.UUID) -> None:
    cache_delete(dashboard_key(owner_id))


def invalidate_analysis(owner_id: uuid.UUID, resume_id: uuid.UUID) -> None:
    cache_delete(analysis_key(owner_id, resume_id))


def ids_for_job(db: Session, job_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID] | None:
    """Returns (owner_id, resume_id) for a job, or None if the resume was deleted."""
    row = db.execute(
        select(Resume.owner_id, Resume.id)
        .join(ProcessingJob, ProcessingJob.resume_id == Resume.id)
        .where(ProcessingJob.id == job_id)
    ).first()
    return (row.owner_id, row.id) if row else None