import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.ai.candidate_extraction import extract_candidate
from app.ai.llm import LlmError, LlmProvider
from app.ai.ocr import OcrEngine
from app.models import ProcessingJob, Resume
from app.services.extraction import ExtractionError, extract_resume_text
from app.services.storage import FileStorage

logger = logging.getLogger(__name__)
GENERIC_FAILURE = "Processing failed. Please try again later."
PARTIAL_NOTE = "Some details could not be filled in automatically."


@dataclass(frozen=True)
class Outcome:
    status: str  # completed | failed | retry | skipped
    attempt: int = 0


def _claim(db: Session, job_id: uuid.UUID):
    """Atomically move queued -> processing. Returns None if someone else got it."""
    claimed = db.execute(
        update(ProcessingJob)
        .where(
            ProcessingJob.id == job_id,
            ProcessingJob.job_type == "extraction",
            ProcessingJob.status == "queued",
        )
        .values(
            status="processing",
            started_at=func.now(),
            attempt_count=ProcessingJob.attempt_count + 1,
        )
        .returning(ProcessingJob.resume_id, ProcessingJob.attempt_count, ProcessingJob.max_attempts)
    ).first()
    if claimed is None:
        db.rollback()
        return None
    db.execute(
        update(Resume)
        .where(Resume.id == claimed.resume_id)
        .values(extraction_status="processing", error_message=None)
    )
    db.commit()
    return claimed


def _set_state(db, job_id, resume_id, status, *, user_message=None, internal_error=None):
    job_values = {"status": status, "last_error": internal_error}
    if status in ("failed", "completed"):
        job_values["finished_at"] = func.now()
    db.execute(update(ProcessingJob).where(ProcessingJob.id == job_id).values(**job_values))
    db.execute(
        update(Resume)
        .where(Resume.id == resume_id)
        .values(extraction_status=status, error_message=user_message)
    )
    db.commit()


def _fail(db, job_id, resume_id, attempt, user_message, internal_error) -> Outcome:
    _set_state(db, job_id, resume_id, "failed",
               user_message=user_message, internal_error=internal_error)
    return Outcome("failed", attempt)


def _retry_or_fail(db, job_id, resume_id, attempt, max_attempts, error_name) -> Outcome:
    if attempt < max_attempts:
        _set_state(db, job_id, resume_id, "queued", internal_error=error_name)
        return Outcome("retry", attempt)
    return _fail(db, job_id, resume_id, attempt, GENERIC_FAILURE, error_name)


def process_extraction(
    db: Session,
    job_id: uuid.UUID,
    storage: FileStorage,
    ocr_engine: OcrEngine,
    llm: LlmProvider | None,
) -> Outcome:
    claimed = _claim(db, job_id)
    if claimed is None:
        return Outcome("skipped")
    resume_id, attempt, max_attempts = claimed.resume_id, claimed.attempt_count, claimed.max_attempts

    resume = db.execute(
        select(Resume.storage_key, Resume.mime_type, Resume.extracted_text).where(
            Resume.id == resume_id
        )
    ).first()
    if resume is None:  # deleted while queued
        return Outcome("skipped")

    # Stage 1: text. Skipped on a retry if the text was already saved.
    text = resume.extracted_text
    if not text:
        try:
            data = storage.read(resume.storage_key)
            result = extract_resume_text(data, resume.mime_type, ocr_engine)
        except FileNotFoundError:
            return _fail(db, job_id, resume_id, attempt,
                         "The stored file could not be found", "FileNotFoundError")
        except ExtractionError as exc:  # permanent: retrying will not help
            return _fail(db, job_id, resume_id, attempt, str(exc), str(exc))
        except Exception as exc:  # unexpected, maybe transient
            logger.exception("Text extraction crashed for job %s", job_id)
            return _retry_or_fail(db, job_id, resume_id, attempt, max_attempts, type(exc).__name__)
        db.execute(
            update(Resume)
            .where(Resume.id == resume_id)
            .values(
                extracted_text=result.text,
                extraction_method=result.method,
                extracted_at=func.now(),
            )
        )
        db.commit()
        text = result.text

    # Stage 2: candidate fields. The saved text survives any failure here.
    note = None
    try:
        info = extract_candidate(text, llm)
    except LlmError:
        logger.warning("Language model step failed for job %s (attempt %s)", job_id, attempt)
        if attempt < max_attempts:
            _set_state(db, job_id, resume_id, "queued", internal_error="LlmError")
            return Outcome("retry", attempt)
        info = extract_candidate(text, None)  # keep email and phone, skip the model fields
        note = PARTIAL_NOTE
    except Exception as exc:
        logger.exception("Candidate extraction crashed for job %s", job_id)
        return _retry_or_fail(db, job_id, resume_id, attempt, max_attempts, type(exc).__name__)

    db.execute(
        update(Resume)
        .where(Resume.id == resume_id)
        .values(
            candidate_name=info.full_name,
            email=info.email,
            mobile=info.mobile,
            location=info.location,
            skills=info.skills,
            extraction_status="completed",
            error_message=note,
        )
    )
    db.execute(
        update(ProcessingJob)
        .where(ProcessingJob.id == job_id)
        .values(status="completed", finished_at=func.now(), last_error=None)
    )
    db.commit()
    return Outcome("completed", attempt)