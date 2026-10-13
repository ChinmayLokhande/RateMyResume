import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.security import CurrentUser, require_role
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.resume import BulkUploadResponse, UploadItemResult
from app.services.resume_service import (
    DuplicateUpload,
    UploadRejected,
    clean_filename,
    ingest_resume,
    read_limited,
)
from app.services.storage import get_storage
from app.services.user_service import get_or_create_profile

router = APIRouter(prefix="/resumes", tags=["resumes"])


def _store(db: Session, owner_id: uuid.UUID, upload: UploadFile) -> uuid.UUID:
    data = read_limited(upload.file, get_settings().max_upload_bytes)
    return ingest_resume(db, get_storage(), owner_id, clean_filename(upload.filename), data)


@router.post("", response_model=UploadItemResult, status_code=status.HTTP_202_ACCEPTED)
def upload_resume(
    file: UploadFile,
    user: CurrentUser = Depends(require_role("user")),
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