"""Celery worker application for APEX.

This module sets up the Celery app and imports all task definitions.
Tasks are defined in tasks.py to keep concerns separated.
"""

from __future__ import annotations

import os
from celery import Celery

# Broker and backend configuration
broker = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://cache:6379/0"))
backend = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", broker))

# Create Celery app
app = Celery("apex", broker=broker, backend=backend)

# Configuration
app.conf.update(
    task_acks_late=True,
    task_acks_on_failure_or_timeout=True,
    worker_prefetch_multiplier=int(os.getenv("PREFETCH", "1")),
    broker_transport_options={"visibility_timeout": int(os.getenv("VIS_TIMEOUT_S", "120"))},
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_default_retry_delay=int(os.getenv("TASK_RETRY_DELAY", "5")),
)

# Import tasks to register them with the app
# This must happen after app is created
from . import tasks  # noqa: F401, E402

if __name__ == "__main__":
    app.worker_main(argv=["worker", "--loglevel=INFO", "--concurrency=2"])


