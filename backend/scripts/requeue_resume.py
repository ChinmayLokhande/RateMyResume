import sys
import uuid

from sqlalchemy import update

from app.db.session import SessionLocal
from app.models import ProcessingJob, Resume
from app.tasks.dispatch import enqueue_extraction

resume_id = uuid.UUID(sys.argv[1])
with SessionLocal() as db:
    job = ProcessingJob(resume_id=resume_id, job_type="extraction")
    db.add(job)
    db.execute(
        update(Resume)
        .where(Resume.id == resume_id)
        .values(extraction_status="queued", error_message=None)
    )
    db.flush()
    job_id = job.id
    db.commit()
print("enqueued" if enqueue_extraction(job_id) else "FAILED to enqueue", job_id)