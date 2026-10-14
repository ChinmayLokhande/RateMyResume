import math
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.security import CurrentUser, require_role
from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.schemas.resume import (
    BulkUploadResponse,
    ResumeDetail,
    ResumeListResponse,
    ResumeStatus,
    ResumeSummary,
    UploadItemResult,
)
from app.services.cache_invalidation import invalidate_analysis, invalidate_dashboard
from app.services.resume_queries import (
    ResumeNotFound,
    RetryNotAllowed,
    delete_resume,
    get_owned_resume,
    list_resumes,
    request_retry,
)
from app.services.resume_service import (
    DuplicateUpload,
    UploadRejected,
    clean_filename,
    ingest_resume,
    read_limited,
)
from app.services.storage import get_storage
from app.services.user_service import get_or_create_profile
from app.tasks.dispatch import enqueue_extraction

router = APIRouter(prefix="/resumes", tags=["resumes"])

NOT_FOUND = HTTPException(status_code=404, detail="Resume not found")


def _store(db: Session, owner_id: uuid.UUID, upload: UploadFile) -> uuid.UUID:
    data = read_limited(upload.file, get_settings().max_upload_bytes)
    resume_id, job_id = ingest_resume(
        db, get_storage(), owner_id, clean_filename(upload.filename), data
    )
    invalidate_dashboard(owner_id)  # the counts just changed
    enqueue_extraction(job_id)  # after the commit, so the worker always finds the rows
    return resume_id


@router.post("", response_model=UploadItemResult, status_code=status.HTTP_202_ACCEPTED)
def upload_resume(
    file: UploadFile,
    user: CurrentUser = Depends(require_role("user")),
    _limit: None = Depends(rate_limit("upload", 30, 60)),
    db: Session = Depends(get_db),
) -> UploadItemResult:
    profile = get_or_create_profile(db, user)
    try:
        resume_id = _store(db, profile.id, file)
    except DuplicateUpload as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": exc.message, "existing_resume_id": str(exc.existing_resume_id)},
        )
    except UploadRejected as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    return UploadItemResult(
        filename=clean_filename(file.filename), status="accepted", resume_id=resume_id
    )


@router.post("/bulk", response_model=BulkUploadResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_resumes_bulk(
    files: list[UploadFile],
    user: CurrentUser = Depends(require_role("user")),
    _limit: None = Depends(rate_limit("upload", 30, 60)),
    db: Session = Depends(get_db),
) -> BulkUploadResponse:
    max_files = get_settings().max_bulk_files
    if not files or len(files) > max_files:
        raise HTTPException(status_code=400, detail=f"Upload between 1 and {max_files} files")

    profile = get_or_create_profile(db, user)
    results: list[UploadItemResult] = []
    for upload in files:  # one bad file never blocks the others
        filename = clean_filename(upload.filename)
        try:
            resume_id = _store(db, profile.id, upload)
            results.append(UploadItemResult(filename=filename, status="accepted", resume_id=resume_id))
        except DuplicateUpload as exc:
            results.append(
                UploadItemResult(
                    filename=filename,
                    status="duplicate",
                    resume_id=exc.existing_resume_id,
                    detail=exc.message,
                )
            )
        except UploadRejected as exc:
            results.append(UploadItemResult(filename=filename, status="rejected", detail=exc.message))

    accepted = sum(1 for r in results if r.status == "accepted")
    return BulkUploadResponse(accepted=accepted, rejected=len(results) - accepted, results=results)


@router.get("", response_model=ResumeListResponse)
def list_my_resumes(
    q: str | None = Query(None, max_length=100),
    status_filter: Literal["queued", "processing", "completed", "failed"] | None = Query(
        None, alias="status"
    ),
    sort: Literal["uploaded_at", "candidate_name", "email", "extraction_status"] = "uploaded_at",
    direction: Literal["asc", "desc"] = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(require_role("user")),
    db: Session = Depends(get_db),
) -> ResumeListResponse:
    profile = get_or_create_profile(db, user)
    rows, total = list_resumes(
        db, profile.id, q=q, status=status_filter, sort=sort,
        direction=direction, page=page, page_size=page_size,
    )
    return ResumeListResponse(
        items=[ResumeSummary.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/{resume_id}", response_model=ResumeDetail)
def get_resume(
    resume_id: uuid.UUID,
    user: CurrentUser = Depends(require_role("user")),
    db: Session = Depends(get_db),
) -> ResumeDetail:
    profile = get_or_create_profile(db, user)
    try:
        resume = get_owned_resume(db, profile.id, resume_id)
    except ResumeNotFound:
        raise NOT_FOUND
    return ResumeDetail.model_validate(resume)


@router.get("/{resume_id}/status", response_model=ResumeStatus)
def get_resume_status(
    resume_id: uuid.UUID,
    user: CurrentUser = Depends(require_role("user")),
    db: Session = Depends(get_db),
) -> ResumeStatus:
    profile = get_or_create_profile(db, user)
    try:
        resume = get_owned_resume(db, profile.id, resume_id)
    except ResumeNotFound:
        raise NOT_FOUND
    return ResumeStatus.model_validate(resume)


@router.post("/{resume_id}/retry", response_model=ResumeStatus, status_code=status.HTTP_202_ACCEPTED)
def retry_resume(
    resume_id: uuid.UUID,
    user: CurrentUser = Depends(require_role("user")),
    _limit: None = Depends(rate_limit("retry", 20, 60)),
    db: Session = Depends(get_db),
) -> ResumeStatus:
    profile = get_or_create_profile(db, user)
    try:
        job_id = request_retry(db, profile.id, resume_id)
    except ResumeNotFound:
        raise NOT_FOUND
    except RetryNotAllowed as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    invalidate_dashboard(profile.id)
    enqueue_extraction(job_id)
    return ResumeStatus.model_validate(get_owned_resume(db, profile.id, resume_id))


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_resume(
    resume_id: uuid.UUID,
    user: CurrentUser = Depends(require_role("user")),
    db: Session = Depends(get_db),
) -> Response:
    profile = get_or_create_profile(db, user)
    try:
        delete_resume(db, get_storage(), profile.id, resume_id)
    except ResumeNotFound:
        raise NOT_FOUND
    invalidate_dashboard(profile.id)
    invalidate_analysis(profile.id, resume_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)