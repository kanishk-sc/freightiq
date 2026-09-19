from celery import Celery

from config import get_settings
from processing import (
    PermanentProcessingError,
    TransientProcessingError,
    process_job,
    set_job_state,
)

settings = get_settings()
celery_app = Celery(
    "freightiq",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
)


@celery_app.task(bind=True, max_retries=2, name="freightiq.process_invoice")
def process_invoice(self, job_id: str) -> int | None:
    try:
        return process_job(job_id)
    except PermanentProcessingError as exc:
        set_job_state(job_id, status="failed", error_code=str(exc))
        return None
    except TransientProcessingError as exc:
        if self.request.retries >= self.max_retries:
            set_job_state(job_id, status="failed", error_code=str(exc))
            return None
        set_job_state(job_id, status="queued", error_code=str(exc))
        raise self.retry(
            exc=TransientProcessingError(str(exc)), countdown=2**self.request.retries
        ) from None
