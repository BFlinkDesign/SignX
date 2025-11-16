from __future__ import annotations

import os

import structlog
from celery import Celery


logger = structlog.get_logger(__name__)


def create_celery() -> Celery:
    broker_url = os.getenv("REDIS_URL", "redis://cache:6379/0")
    backend_url = os.getenv("REDIS_URL", "redis://cache:6379/0")
    app = Celery("apex-worker", broker=broker_url, backend=backend_url)
    app.conf.update(
        task_acks_late=True,
        broker_transport_options={"visibility_timeout": 600},
        worker_prefetch_multiplier=1,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_time_limit=300,
        task_soft_time_limit=270,
        task_default_retry_delay=5,
        broker_heartbeat=10,
        broker_connection_retry_on_startup=True,
    )
    return app


celery_app = create_celery()


@celery_app.task(name="health.ping", bind=True, autoretry_for=(Exception,), retry_backoff=2, retry_kwargs={"max_retries": 3})
def ping(self):  # type: ignore[no-untyped-def]
    logger.info("worker_ping")
    return {"status": "ok"}


# Import tasks to register them
from . import tasks  # noqa: F401


