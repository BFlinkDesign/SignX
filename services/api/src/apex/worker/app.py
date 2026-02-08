from __future__ import annotations

import os

from celery import Celery


def create_celery_app() -> Celery:
    broker_url = os.getenv("APEX_REDIS_URL") or os.getenv("REDIS_URL") or "redis://cache:6379/0"
    backend_url = broker_url
    app = Celery(
        "apex-worker",
        broker=broker_url,
        backend=backend_url,
        include=[
            "apex.worker.tasks.projects_report",
            "apex.worker.tasks.projects_submit",
            "apex.worker.tasks.projects_email",
        ],
    )
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_acks_late=True,
        worker_max_tasks_per_child=1000,
        task_default_retry_delay=2,
    )
    return app


app = create_celery_app()


