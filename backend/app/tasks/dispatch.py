import logging
import uuid

from app.tasks.extraction_tasks import run_extraction

logger = logging.getLogger(__name__)


def enqueue_extraction(job_id: uuid.UUID) -> bool:
    """Never raises: if Redis is down, the job stays 'queued' in Postgres."""
    try:
        run_extraction.delay(str(job_id))
        return True
    except Exception:
        logger.exception("Could not enqueue extraction job %s", job_id)
        return False