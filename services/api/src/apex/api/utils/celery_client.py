"""Celery client utilities for enqueueing tasks from API."""

from __future__ import annotations

from typing import Any

from celery import Celery

from ..deps import settings

# Singleton Celery client to avoid creating new instances on every call
_celery_client: Celery | None = None


def get_celery_client() -> Celery:
    """Get Celery client for enqueueing tasks (singleton pattern)."""
    global _celery_client
    if _celery_client is None:
        _celery_client = Celery(
            "apex-client",
            broker=settings.REDIS_URL,
            backend=settings.REDIS_URL,
        )
        # Configure client for efficient operation
        _celery_client.conf.update(
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
            timezone="UTC",
            enable_utc=True,
        )
    return _celery_client


def enqueue_report_generation(project_id: str, payload: dict[str, Any]) -> str:
    """Enqueue PDF report generation task.
    
    Returns: Task ID
    """
    celery = get_celery_client()
    result = celery.send_task("projects.report.generate", args=[project_id, payload])
    return result.id


def enqueue_pm_dispatch(project_id: str, project_data: dict[str, Any], idempotency_key: str | None = None) -> str:
    """Enqueue project management dispatch task.
    
    Returns: Task ID
    """
    celery = get_celery_client()
    result = celery.send_task("projects.submit.dispatch", args=[project_id, project_data], kwargs={"idempotency_key": idempotency_key})
    return result.id


def enqueue_email(to_email: str, subject: str, template: str, context: dict[str, Any]) -> str:
    """Enqueue email notification task.
    
    Returns: Task ID
    """
    celery = get_celery_client()
    result = celery.send_task("projects.email.send", args=[to_email, subject, template, context])
    return result.id

