import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth.security import CurrentUser, require_role
from app.core.cache import analysis_key, cache_delete, cache_get, cache_set
from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.schemas.analysis import AnalysisResponse
from app.schemas.resume import ResumeStatus
from app.services.analysis_queries import AnalysisNotAllowed, get_latest_analysis, queue_analysis_job
from app.services.resume_queries import ResumeNotFound, get_owned_resume
from app.services.user_service import get_or_create_profile
from app.tasks.analysis_tasks import enqueue_analysis

router = APIRouter(prefix="/resumes", tags=["analysis"])

NOT_FOUND = HTTPException(status_code=404, detail="Resume not found")


@router.post("/{resume_id}/analyze", response_model=ResumeStatus, status_code=status.HTTP_202_ACCEPTED)
def analyze_resume(
    resume_id: uuid.UUID,
    user: CurrentUser = Depends(require_role("user")),
    _limit: None = Depends(rate_limit("analyze", 10, 60)),
    db: Session = Depends(get_db),
) -> ResumeStatus:
    profile = get_or_create_profile(db, user)
    try:
        get_owned_resume(db, profile.id, resume_id)
        job_id = queue_analysis_job(db, resume_id)
    except ResumeNotFound:
        raise NOT_FOUND
    except AnalysisNotAllowed as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    enqueue_analysis(job_id)
    return ResumeStatus.model_validate(get_owned_resume(db, profile.id, resume_id))


@router.get("/{resume_id}/analysis", response_model=AnalysisResponse)
def get_analysis(
    resume_id: uuid.UUID,
    user: CurrentUser = Depends(require_role("user")),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    profile = get_or_create_profile(db, user)
    try:
        # Authorization always goes to the database; the cache is never trusted for access control
        resume = get_owned_resume(db, profile.id, resume_id)
    except ResumeNotFound:
        raise NOT_FOUND

    key = analysis_key(profile.id, resume_id)
    cached = cache_get(key)
    if isinstance(cached, dict):
        try:
            return AnalysisResponse(**cached, analysis_status=resume.analysis_status)
        except ValidationError:
            cache_delete(key)  # unusable entry: drop it and fall through to the database

    analysis = get_latest_analysis(db, resume_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="No analysis available yet")
    response = AnalysisResponse(
        id=analysis.id,
        resume_id=analysis.resume_id,
        analysis_status=resume.analysis_status,
        score=analysis.score,
        summary=analysis.summary,
        detailed_result=analysis.detailed_result,
        rubric_version=analysis.rubric_version,
        prompt_version=analysis.prompt_version,
        model_name=analysis.model_name,
        model_version=analysis.model_version,
        created_at=analysis.created_at,
    )
    # analysis_status changes independently, so it is added fresh on every read
    cache_set(
        key,
        response.model_dump(mode="json", exclude={"analysis_status"}),
        get_settings().analysis_cache_ttl_seconds,
    )
    return response