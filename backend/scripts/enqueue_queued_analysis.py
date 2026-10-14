from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import ProcessingJob
from app.tasks.analysis_tasks import enqueue_analysis

with SessionLocal() as db:
    job_ids = db.scalars(
        select(ProcessingJob.id).where(
            ProcessingJob.status == "queued", ProcessingJob.job_type == "analysis"
        )
    ).all()
for job_id in job_ids:
    print(job_id, "enqueued" if enqueue_analysis(job_id) else "FAILED to enqueue")