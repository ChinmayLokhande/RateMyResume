from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import ProcessingJob
from app.tasks.dispatch import enqueue_extraction

with SessionLocal() as db:
    job_ids = db.scalars(
        select(ProcessingJob.id).where(
            ProcessingJob.status == "queued", ProcessingJob.job_type == "extraction"
        )
    ).all()
for job_id in job_ids:
    print(job_id, "enqueued" if enqueue_extraction(job_id) else "FAILED to enqueue")