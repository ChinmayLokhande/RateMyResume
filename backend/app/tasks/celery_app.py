from celery import Celery

from app.core.config import get_settings

celery_app = Celery(
    "ratemyresume",
    broker=get_settings().celery_broker_url,
    include=["app.tasks.extraction_tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    task_ignore_result=True,  # Postgres is the record of truth, not Celery results
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)