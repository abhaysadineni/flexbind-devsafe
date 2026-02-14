"""Celery worker configuration and pipeline task."""

from celery import Celery

from app.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery_app = Celery(
    "flexbind",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(name="run_pipeline", bind=True, max_retries=0)
def run_pipeline_task(self, job_id: str) -> dict:
    """Celery task that runs the full FlexBind pipeline."""
    from app.pipeline.runner import run_pipeline

    run_pipeline(job_id)
    return {"job_id": job_id, "status": "done"}
