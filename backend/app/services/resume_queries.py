import logging
import uuid

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.models import ProcessingJob, Resume
from app.services.storage import FileStorage

logger = logging.getLogger(__name__)

SORT_COLUMNS = {
    "uploaded_at": Resume.uploaded_at,
    "candidate_name": Resume.candidate_name,
    "email": Resume.email,
    "extraction_status": Resume.extraction_status,
}


class ResumeNotFound(Exception):
    pass


class RetryNotAllowed(Exception):
    pass


def _like_pattern(term: str) -> str:
    """Escapes % and _ so user input is matched literally, not as wildcards."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def list_resumes(
    db: Session,
    owner_id: uuid.UUID,
    *,
    q: str | None,
    status: str | None,
    sort: str,
    direction: str,
    page: int,
    page_size: int,
) -> tuple[list[Resume], int]:
    conditions = [Resume.owner_id == owner_id]
    if q and q.strip():
        pattern = _like_pattern(q.strip())
        conditions.append(
            or_(
                Resume.candidate_name.ilike(pattern, escape="\\"),
                Resume.email.ilike(pattern, escape="\\"),
            )
        )
    if status:
        conditions.append(Resume.extraction_status == status)

    total = db.scalar(select(func.count()).select_from(Resume).where(*conditions)) or 0

    column = SORT_COLUMNS[sort]
    ordering = column.asc() if direction == "asc" else column.desc()
    rows = db.scalars(
        select(Resume)
        .where(*conditions)
        .order_by(ordering.nulls_last(), Resume.id)
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()
    return list(rows), total


def get_owned_resume(db: Session, owner_id: uuid.UUID, resume_id: uuid.UUID) -> Resume:
    resume = db.scalar(
        select(Resume).where(Resume.id == resume_id, Resume.owner_id == owner_id)
    )
    if resume is None:
        raise ResumeNotFound
    return resume


def request_retry(db: Session, owner_id: uuid.UUID, resume_id: uuid.UUID) -> uuid.UUID:
    """Moves failed -> queued atomically and creates a new job. Returns the new job id."""
    updated = db.execute(
        update(Resume)
        .where(
            Resume.id == resume_id,
            Resume.owner_id == owner_id,
            Resume.extraction_status == "failed",
        )
        .values(extraction_status="queued", error_message=None)
        .returning(Resume.id)
    ).first()
    if updated is None:
        db.rollback()
        get_owned_resume(db, owner_id, resume_id)  # raises ResumeNotFound if not theirs
        raise RetryNotAllowed("Only failed resumes can be retried")

    job = ProcessingJob(resume_id=resume_id, job_type="extraction")
    db.add(job)
    db.flush()
    job_id = job.id
    db.commit()
    return job_id


def delete_resume(
    db: Session, storage: FileStorage, owner_id: uuid.UUID, resume_id: uuid.UUID
) -> None:
    resume = get_owned_resume(db, owner_id, resume_id)
    storage_key = resume.storage_key
    db.delete(resume)  # analyses and jobs are removed by the database (ON DELETE CASCADE)
    db.commit()
    try:
        storage.delete(storage_key)
    except OSError:
        # The record is already gone; log the key (no personal data in it) for cleanup
        logger.error("Could not delete stored file %s", storage_key)