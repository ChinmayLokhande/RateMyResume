import hashlib
import io
import uuid
import zipfile

from sqlalchemy import update

from app.models import ProcessingJob, Resume, UserProfile
from app.services.resume_service import PDF_MIME
from app.services.storage import get_storage


def pdf_bytes() -> bytes:
    return b"%PDF-1.4\n% fixture " + uuid.uuid4().hex.encode() + b"\n%%EOF"


def docx_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", f"<doc>{uuid.uuid4().hex}</doc>")
    return buffer.getvalue()


def upload(client, headers, data, name="resume.pdf"):
    return client.post(
        "/api/v1/resumes",
        files={"file": (name, data, "application/octet-stream")},
        headers=headers,
    )


def set_fields(db, resume_id, **values) -> None:
    db.execute(update(Resume).where(Resume.id == uuid.UUID(str(resume_id))).values(**values))
    db.commit()
    db.expire_all()


def make_resume(db, data: bytes, mime: str = PDF_MIME) -> tuple[uuid.UUID, uuid.UUID]:
    """Creates an owner, a stored file, a resume and a queued extraction job."""
    profile = UserProfile(keycloak_sub=f"sub-{uuid.uuid4().hex}")
    db.add(profile)
    db.flush()
    key = f"{profile.id}/{uuid.uuid4().hex}.pdf"
    get_storage().save(key, data)
    resume = Resume(
        owner_id=profile.id,
        original_filename="test.pdf",
        storage_key=key,
        mime_type=mime,
        file_hash=hashlib.sha256(data).hexdigest(),
        file_size=len(data),
    )
    db.add(resume)
    db.flush()
    job = ProcessingJob(resume_id=resume.id, job_type="extraction")
    db.add(job)
    db.commit()
    return resume.id, job.id
