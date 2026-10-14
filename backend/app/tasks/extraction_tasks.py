import logging
import uuid

from sqlalchemy import select

from app.ai.llm import get_llm_provider
from app.ai.ocr import get_ocr_engine
from app.db.session import SessionLocal
from app.models import ProcessingJob
from app.services.analysis_queries import AnalysisNotAllowed, queue_analysis_job
from app.services.cache_invalidation import ids_for_job, invalidate_dashboard
from app.services.processing import process_extraction
from app.services.storage import get_storage
from app.tasks.analysis_tasks import enqueue_analysis
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _start_analysis(job_id: uuid.UUID) -> None:
    """Queues an analysis after a successful extraction. A failure here never affects extraction."""
    try:
        with SessionLocal() as db:
            resume_id = db.scalar(
                select(ProcessingJob.resume_id).where(ProcessingJob.id == job_id)
            )
            if resume_id is None:
                return
            analysis_job_id = queue_analysis_job(db, resume_id)
        enqueue_analysis(analysis_job_id)
    except AnalysisNotAllowed:
        pass  # an analysis is already queued or running
    except Exception:
        logger.exception("Could not start analysis after extraction job %s", job_id)


@celery_app.task(bind=True, name="extraction.run", max_retries=None)
def run_extraction(self, job_id: str) -> str:
    job = uuid.UUID(job_id)
    with SessionLocal() as db:
        outcome = process_extraction(
            db, job, get_storage(), get_ocr_engine(), get_llm_provider()
        )
        if outcome.status in ("completed", "failed"):
            ids = ids_for_job(db, job)  # the dashboard counts just changed
            if ids:
                invalidate_dashboard(ids[0])
    if outcome.status == "retry":
        # attempt count lives in Postgres and caps retries, so max_retries is unlimited here
        raise self.retry(countdown=min(5 * 2**outcome.attempt, 120))
    if outcome.status == "completed":
        _start_analysis(job)
    return outcome.status