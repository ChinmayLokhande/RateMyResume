import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import ProcessingJob, Resume, ResumeAnalysis


class AnalysisNotAllowed(Exception):
    pass


def queue_analysis_job(db: Session, resume_id: uuid.UUID) -> uuid.UUID:
    """Atomically marks the resume's analysis as queued and creates a job.
    Only allowed once extraction is complete and no analysis is already running."""
    updated = db.execute(
        update(Resume)
        .where(
            Resume.id == resume_id,
            Resume.extraction_status == "completed",
            Resume.analysis_status.in_(("not_started", "completed", "failed")),
        )
        .values(analysis_status="queued")
        .returning(Resume.id)
    ).first()
    if updated is None:
        db.rollback()
        raise AnalysisNotAllowed(
            "Analysis needs completed extraction and cannot run twice at once"
        )
    job = ProcessingJob(resume_id=resume_id, job_type="analysis")
    db.add(job)
    db.flush()
    job_id = job.id
    db.commit()
    return job_id


def get_latest_analysis(db: Session, resume_id: uuid.UUID) -> ResumeAnalysis | None:
    return db.scalar(
        select(ResumeAnalysis)
        .where(ResumeAnalysis.resume_id == resume_id)
        .order_by(ResumeAnalysis.created_at.desc(), ResumeAnalysis.id)
        .limit(1)
    )