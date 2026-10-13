import hashlib
import io
import logging
import uuid
import zipfile
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ProcessingJob, Resume
from app.services.storage import FileStorage

logger = logging.getLogger(__name__)

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
EXTENSIONS = {PDF_MIME: ".pdf", DOCX_MIME: ".docx"}
MAX_DOCX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024  # guards against zip bombs


class UploadRejected(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class DuplicateUpload(UploadRejected):
    def __init__(self, existing_resume_id: uuid.UUID) -> None:
        super().__init__("This file was already uploaded", 409)
        self.existing_resume_id = existing_resume_id


def clean_filename(name: str | None) -> str:
    """For display only. The stored file always gets a generated name."""
    base = Path((name or "").replace("\\", "/")).name
    base = "".join(ch for ch in base if ch.isprintable()).strip()
    return base[:255] or "resume"


def read_limited(fileobj: BinaryIO, limit: int) -> bytes:
    # Ensure pointer is at the start of the file
    if hasattr(fileobj, "seek"):
        fileobj.seek(0)

    data = fileobj.read(limit + 1)
    if len(data) > limit:
        raise UploadRejected(f"File exceeds the {limit // (1024 * 1024)} MB limit", 413)
    return data


def _is_docx(data: bytes) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
            total_size = sum(item.file_size for item in archive.infolist())
    except zipfile.BadZipFile:
        return False
    return (
        "[Content_Types].xml" in names
        and "word/document.xml" in names
        and total_size <= MAX_DOCX_UNCOMPRESSED_BYTES
    )


def detect_mime(data: bytes) -> str:
    """Decide the type from the file's actual bytes, not its name or browser MIME type."""
    if data.startswith(b"%PDF-"):
        return PDF_MIME
    if data.startswith(b"PK\x03\x04") and _is_docx(data):
        return DOCX_MIME
    raise UploadRejected("Only PDF and DOCX files are supported", 415)


def _find_existing(db: Session, owner_id: uuid.UUID, file_hash: str) -> uuid.UUID | None:
    return db.scalar(
        select(Resume.id).where(Resume.owner_id == owner_id, Resume.file_hash == file_hash)
    )


def ingest_resume(
    db: Session, storage: FileStorage, owner_id: uuid.UUID, filename: str, data: bytes
) -> tuple[uuid.UUID, uuid.UUID]:  # CHANGED: returns (resume_id, job_id)
    if not data:
        raise UploadRejected("File is empty", 400)
    mime_type = detect_mime(data)
    file_hash = hashlib.sha256(data).hexdigest()

    existing_id = _find_existing(db, owner_id, file_hash)
    if existing_id:
        raise DuplicateUpload(existing_id)

    storage_key = f"{owner_id}/{uuid.uuid4().hex}{EXTENSIONS[mime_type]}"
    storage.save(storage_key, data)
    try:
        resume = Resume(
            owner_id=owner_id,
            original_filename=filename,
            storage_key=storage_key,
            mime_type=mime_type,
            file_hash=file_hash,
            file_size=len(data),
        )
        db.add(resume)
        db.flush()  # assigns resume.id
        resume_id = resume.id
        job = ProcessingJob(resume_id=resume_id, job_type="extraction")  # CHANGED
        db.add(job)  # CHANGED
        db.flush()  # CHANGED: assigns job.id
        job_id = job.id  # CHANGED
        db.commit()
    except IntegrityError:
        db.rollback()
        storage.delete(storage_key)
        existing_id = _find_existing(db, owner_id, file_hash)
        if existing_id:  # lost a race with an identical upload
            raise DuplicateUpload(existing_id)
        raise
    except Exception:
        db.rollback()
        storage.delete(storage_key)  # never leave a file without a database record
        raise
    return resume_id, job_id  # CHANGED