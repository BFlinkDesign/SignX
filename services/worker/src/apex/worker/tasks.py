"""Celery tasks for project submission, report generation, and notifications."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

import structlog
from celery import Task

from .app import celery_app

logger = structlog.get_logger(__name__)


class BaseTask(Task):  # type: ignore
    """Base task with structured logging and error handling."""

    def on_failure(self, exc: Exception, task_id: str, args: tuple[Any, ...], kwargs: dict[str, Any], einfo: Any) -> None:
        """Log task failures with context."""
        logger.error(
            "task.failure",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
            args=args,
            kwargs=kwargs,
        )

    def on_success(self, retval: Any, task_id: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        """Log task success."""
        logger.info(
            "task.success",
            task_id=task_id,
            task_name=self.name,
        )


@celery_app.task(name="projects.report.generate", base=BaseTask, bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def generate_report_task(self: Task, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Generate PDF report asynchronously.
    
    Args:
        project_id: Project identifier
        payload: Project payload dict with module, config, files, cost_snapshot
    
    Returns:
        {"sha256": str, "pdf_ref": str, "cached": bool}
    """
    logger.info("task.report.generate", project_id=project_id, attempt=self.request.retries + 1)
    
    # Import here to avoid circular dependencies
    import sys
    from pathlib import Path
    
    # Add services/api to path for utils
    api_path = Path(__file__).parent.parent.parent.parent.parent / "api" / "src"
    if str(api_path) not in sys.path:
        sys.path.insert(0, str(api_path))
    
    try:
        from apex.api.utils.report import generate_report_from_payload
        
        # Get artifacts root from environment
        artifacts_root = Path(os.getenv("MINIO_BUCKET", "./artifacts")).expanduser().resolve()
        artifacts_root.mkdir(parents=True, exist_ok=True)
        
        # Generate report (note: generate_report_from_payload is async, but Celery tasks are sync)
        # For now, we'll use a sync wrapper or call it directly
        # In production, would use celery's async support or sync adapter
        import asyncio
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(generate_report_from_payload(project_id, payload, artifacts_root))
        finally:
            loop.close()
        
        logger.info("task.report.generate.success", project_id=project_id, sha256=result["sha256"][:16])
        return result
    except Exception as e:
        logger.error("task.report.generate.error", project_id=project_id, error=str(e))
        raise


@celery_app.task(name="projects.submit.dispatch", base=BaseTask, bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def dispatch_to_pm_task(self: Task, project_id: str, project_data: dict[str, Any], idempotency_key: str | None = None) -> dict[str, Any]:
    """Dispatch project to project management system (e.g., Smartsheet API).
    
    Args:
        project_id: Project identifier
        project_data: Full project metadata and payload
        idempotency_key: Idempotency key for duplicate prevention
    
    Returns:
        {"project_number": str, "pm_ref": str, "status": str}
    """
    logger.info("task.pm.dispatch", project_id=project_id, idempotency_key=idempotency_key, attempt=self.request.retries + 1)
    
    # TODO: Wire into actual PM system API (Smartsheet, Asana, etc.)
    # For now, generate placeholder project number
    
    project_number = f"PRJ-{uuid.uuid4().hex[:8].upper()}"
    
    # Placeholder: would make HTTP request to PM API
    # Example:
    # async with aiohttp.ClientSession() as session:
    #     async with session.post(
    #         "https://api.smartsheet.com/2.0/sheets/{sheet_id}/rows",
    #         headers={"Authorization": f"Bearer {api_key}"},
    #         json={
    #             "toTop": True,
    #             "cells": [
    #                 {"columnId": col_id, "value": project_data.get("name")},
    #                 ...
    #             ]
    #         }
    #     ) as resp:
    #         if resp.status == 200:
    #             data = await resp.json()
    #             pm_ref = data["result"]["id"]
    
    result = {
        "project_number": project_number,
        "pm_ref": f"pm-placeholder-{project_id}",
        "status": "dispatched",
        "note": "PM integration pending - using placeholder",
    }
    
    logger.info("task.pm.dispatch.success", project_id=project_id, project_number=project_number)
    return result


@celery_app.task(name="projects.email.send", base=BaseTask, bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_email_notification_task(self: Task, to_email: str, subject: str, template: str, context: dict[str, Any]) -> dict[str, Any]:
    """Send email notification (e.g., project submitted, report ready).
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        template: Template name (e.g., "project_submitted", "report_ready")
        context: Template context variables
    
    Returns:
        {"message_id": str, "status": str}
    """
    logger.info("task.email.send", to=to_email, template=template, attempt=self.request.retries + 1)
    
    # TODO: Wire into email service (SendGrid, SES, etc.)
    # For now, log and return placeholder
    # Example:
    # async with aiohttp.ClientSession() as session:
    #     async with session.post(
    #         "https://api.sendgrid.com/v3/mail/send",
    #         headers={
    #             "Authorization": f"Bearer {sendgrid_key}",
    #             "Content-Type": "application/json",
    #         },
    #         json={
    #             "personalizations": [{"to": [{"email": to_email}]}],
    #             "from": {"email": "noreply@apex-eng.com"},
    #             "subject": subject,
    #             "content": [{"type": "text/html", "value": render_template(template, context)}],
    #         }
    #     ) as resp:
    #         if resp.status in (200, 202):
    #             message_id = resp.headers.get("X-Message-Id", "unknown")
    
    message_id = f"email-{uuid.uuid4().hex[:12]}"
    
    result = {
        "message_id": message_id,
        "status": "sent",
        "note": "Email integration pending - logged only",
    }
    
    logger.info("task.email.send.success", to=to_email, message_id=message_id)
    return result

