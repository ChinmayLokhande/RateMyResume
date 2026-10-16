import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import CurrentUser, require_role
from app.db.session import get_db
from app.schemas.job_match import JobMatchesResponse
from app.services.job_matching import SCORING_VERSION, calculate_and_save_matches
from app.services.resume_queries import ResumeNotFound, get_owned_resume
from app.services.user_service import get_or_create_profile

router = APIRouter(prefix="/resumes", tags=["job-matches"])


def _run(resume_id: uuid.UUID, user: CurrentUser, db: Session) -> JobMatchesResponse:
    profile = get_or_create_profile(db, user)
    try:
        resume = get_owned_resume(db, profile.id, resume_id)  # ownership check
    except ResumeNotFound:
        raise HTTPException(404, "Resume not found")
    if resume.extraction_status != "completed":
        raise HTTPException(409, "Resume text extraction is not complete yet.")
    try:
        results = calculate_and_save_matches(db, resume)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    except LookupError as exc:
        raise HTTPException(503, str(exc))
    return JobMatchesResponse(
        resume_id=resume.id, scoring_version=SCORING_VERSION, results=results
    )


@router.get("/{resume_id}/job-matches", response_model=JobMatchesResponse)
def read_job_matches(
    resume_id: uuid.UUID,
    user: CurrentUser = Depends(require_role("user")),
    db: Session = Depends(get_db),
):
    return _run(resume_id, user, db)


@router.post("/{resume_id}/job-matches", response_model=JobMatchesResponse)
def refresh_job_matches(
    resume_id: uuid.UUID,
    user: CurrentUser = Depends(require_role("user")),
    db: Session = Depends(get_db),
):
    return _run(resume_id, user, db)
