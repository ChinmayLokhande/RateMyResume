import logging
import uuid

from app.ai.llm import get_llm_provider
from app.db.session import SessionLocal
from app.services.analysis_processing import process_analysis
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="analysis.run", max_retries=None)
def run_analysis(self, job_id: str) -> str:
    with SessionLocal() as db:
        outcome = process_analysis(db, uuid.UUID(job_id), get_llm_provider())
    if outcome.status == "retry":
        raise self.retry(countdown=min(5 * 2**outcome.attempt, 120))
    return outcome.status


def enqueue_analysis(job_id: uuid.UUID) -> bool:
    """Never raises: if Redis is down, the job stays 'queued' in Postgres."""
    try:
        run_analysis.delay(str(job_id))
        return True
    except Exception:
        logger.exception("Could not enqueue analysis job %s", job_id)
        return False