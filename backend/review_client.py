"""Best-effort notification; Node reconciles durable signals after outages."""

import json
import logging
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import get_settings
from database import SessionLocal
from models import ProcessingJob

logger = logging.getLogger(__name__)


def notify_review(job_id: str) -> None:
    try:
        settings = get_settings()
        if not settings.review_service_url:
            return
        with SessionLocal() as session:
            job = session.get(ProcessingJob, uuid.UUID(job_id))
            if job is None:
                return
            document_id = job.document_id
        request = Request(
            settings.review_service_url.rstrip("/") + "/api/review-tasks",
            data=json.dumps({"document_id": document_id}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=settings.review_service_timeout_seconds):
            pass
    except HTTPError as exc:
        # Clean documents have no review signal; 422 is an expected no-op.
        if exc.code != 422:
            logger.warning("review_notification_failed", extra={"code": "http_error"})
    except (URLError, TimeoutError, OSError):
        logger.warning("review_notification_failed", extra={"code": "unavailable"})
    except Exception:
        # Notification errors must never turn successful extraction into a retry.
        logger.warning(
            "review_notification_failed", extra={"code": "notification_error"}
        )
