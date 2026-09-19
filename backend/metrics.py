import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from sqlalchemy import func, select

from database import SessionLocal
from models import ProcessingJob

REQUESTS = Counter(
    "freightiq_http_requests_total",
    "HTTP requests handled by the API.",
    ("method", "route", "status"),
)
REQUEST_DURATION = Histogram(
    "freightiq_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "route"),
)
JOBS = Gauge(
    "freightiq_processing_jobs",
    "Durable processing jobs by current state.",
    ("status",),
)
FAILURES = Gauge(
    "freightiq_processing_failures",
    "Durable failed processing jobs by safe error code.",
    ("error_code",),
)
PROCESSING_DURATION = Gauge(
    "freightiq_processing_duration_seconds_average",
    "Average duration of completed processing jobs.",
)


async def observe_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    started = time.perf_counter()
    response_status = 500
    try:
        response = await call_next(request)
        response_status = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        route_path = getattr(route, "path", "unmatched")
        REQUESTS.labels(request.method, route_path, str(response_status)).inc()
        REQUEST_DURATION.labels(request.method, route_path).observe(
            time.perf_counter() - started
        )


def metrics_response() -> Response:
    statuses = ("queued", "processing", "completed", "failed")
    with SessionLocal() as session:
        counts = dict(
            session.execute(
                select(ProcessingJob.status, func.count()).group_by(
                    ProcessingJob.status
                )
            ).all()
        )
        for status in statuses:
            JOBS.labels(status).set(counts.get(status, 0))

        FAILURES.clear()
        failure_counts = session.execute(
            select(ProcessingJob.error_code, func.count())
            .where(
                ProcessingJob.status == "failed",
                ProcessingJob.error_code.is_not(None),
            )
            .group_by(ProcessingJob.error_code)
        ).all()
        for error_code, count in failure_counts:
            FAILURES.labels(error_code).set(count)

        average_duration = session.scalar(
            select(
                func.avg(
                    func.extract(
                        "epoch", ProcessingJob.completed_at - ProcessingJob.started_at
                    )
                )
            ).where(
                ProcessingJob.status == "completed",
                ProcessingJob.started_at.is_not(None),
                ProcessingJob.completed_at.is_not(None),
            )
        )
        PROCESSING_DURATION.set(float(average_duration or 0))

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
