import uuid

from app.ai.llm import get_llm_provider
from app.ai.ocr import get_ocr_engine
from app.db.session import SessionLocal
from app.services.processing import process_extraction
from app.services.storage import get_storage
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="extraction.run", max_retries=None)
def run_extraction(self, job_id: str) -> str:
    with SessionLocal() as db:
        outcome = process_extraction(
            db, uuid.UUID(job_id), get_storage(), get_ocr_engine(), get_llm_provider()
        )
    if outcome.status == "retry":
        # attempt count lives in Postgres and caps retries, so max_retries is unlimited here
        raise self.retry(countdown=min(5 * 2**outcome.attempt, 120))
    return outcome.status