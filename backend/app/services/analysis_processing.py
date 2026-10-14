import logging
import uuid
from dataclasses import asdict
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.analysis import PROMPT_VERSION, generate_narrative
from app.ai.llm import LlmError, LlmProvider
from app.models import ProcessingJob, Resume, ResumeAnalysis
from app.services.processing import Outcome
from app.services.rubric import RUBRIC_VERSION, RubricResult, compute_rubric

logger = logging.getLogger(__name__)

ADVISORY = (
    "This assessment is advisory only. It describes how complete and clear the resume is, "
    "not the value or employability of the candidate."
)
NO_NARRATIVE_SUMMARY = "Automated score only. The written assessment was not generated."


def _claim(db: Session, job_id: uuid.UUID):
    claimed = db.execute(
        update(ProcessingJob)
        .where(
            ProcessingJob.id == job_id,
            ProcessingJob.job_type == "analysis",
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
        update(Resume).where(Resume.id == claimed.resume_id).values(analysis_status="processing")
    )
    db.commit()
    return claimed


def _set_state(db, job_id, resume_id, status, internal_error=None) -> None:
    job_values: dict[str, Any] = {"status": status, "last_error": internal_error}
    if status == "failed":
        job_values["finished_at"] = func.now()
    db.execute(update(ProcessingJob).where(ProcessingJob.id == job_id).values(**job_values))
    db.execute(update(Resume).where(Resume.id == resume_id).values(analysis_status=status))
    db.commit()


def _retry_or_fail(db, job_id, resume_id, attempt, max_attempts, error_name) -> Outcome:
    if attempt < max_attempts:
        _set_state(db, job_id, resume_id, "queued", error_name)
        return Outcome("retry", attempt)
    _set_state(db, job_id, resume_id, "failed", error_name)  # earlier analyses stay untouched
    return Outcome("failed", attempt)


def _build_detail(rubric: RubricResult, narrative: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "advisory_notice": ADVISORY,
        "rubric": {
            "version": RUBRIC_VERSION,
            "total": rubric.score,
            "max": 100,
            "criteria": [asdict(criterion) for criterion in rubric.criteria],
        },
        "missing_or_unclear": rubric.missing,
        "narrative_available": narrative is not None,
        "narrative": narrative,
    }


def process_analysis(db: Session, job_id: uuid.UUID, llm: LlmProvider | None) -> Outcome:
    claimed = _claim(db, job_id)
    if claimed is None:
        return Outcome("skipped")
    resume_id, attempt, max_attempts = claimed.resume_id, claimed.attempt_count, claimed.max_attempts

    resume = db.execute(
        select(
            Resume.extracted_text, Resume.email, Resume.mobile, Resume.location, Resume.skills
        ).where(Resume.id == resume_id)
    ).first()
    if resume is None:  # deleted while queued
        return Outcome("skipped")
    if not resume.extracted_text:
        _set_state(db, job_id, resume_id, "failed", "NoExtractedText")
        return Outcome("failed", attempt)

    rubric = compute_rubric(
        resume.extracted_text,
        email=resume.email,
        mobile=resume.mobile,
        location=resume.location,
        skills=resume.skills,
    )

    narrative = None
    if llm is not None:
        try:
            narrative = generate_narrative(resume.extracted_text, llm)
        except LlmError:
            logger.warning("Analysis model step failed for job %s (attempt %s)", job_id, attempt)
            return _retry_or_fail(db, job_id, resume_id, attempt, max_attempts, "LlmError")
        except Exception as exc:
            logger.exception("Analysis crashed for job %s", job_id)
            return _retry_or_fail(db, job_id, resume_id, attempt, max_attempts, type(exc).__name__)

    summary = (narrative or {}).get("professional_summary") or NO_NARRATIVE_SUMMARY
    try:
        db.add(
            ResumeAnalysis(
                resume_id=resume_id,
                score=rubric.score,
                summary=summary,
                detailed_result=_build_detail(rubric, narrative),
                rubric_version=RUBRIC_VERSION,
                prompt_version=PROMPT_VERSION if llm else "none",
                model_name=llm.model if llm else "rubric-only",
            )
        )
        db.execute(update(Resume).where(Resume.id == resume_id).values(analysis_status="completed"))
        db.execute(
            update(ProcessingJob)
            .where(ProcessingJob.id == job_id)
            .values(status="completed", finished_at=func.now(), last_error=None)
        )
        db.commit()
    except IntegrityError:  # the resume was deleted while we worked
        db.rollback()
        return Outcome("skipped")
    return Outcome("completed", attempt)