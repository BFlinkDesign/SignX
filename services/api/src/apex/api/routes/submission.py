"""Project submission and finalization endpoints."""

from __future__ import annotations

from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from ..common.helpers import log_event, require_project
from ..common.models import make_envelope
from ..common.transactions import transaction
from ..db import Project, ProjectEvent, ProjectPayload, get_db
from ..deps import get_code_version, get_model_config, settings
from ..schemas import ResponseEnvelope, add_assumption
from ..utils.celery_client import enqueue_email, enqueue_pm_dispatch, enqueue_report_generation
from ..utils.report import generate_report_from_payload

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["submission"])


@router.post("/{project_id}/submit", response_model=ResponseEnvelope)
async def submit_project(
    project_id: str,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    actor: str = "system",
) -> ResponseEnvelope:
    """Submit project for formal engineering (idempotent).
    
    Flow: finalize pricing → push to PM → record project_number → email PM
    State transition: estimating → submitted
    
    Idempotent: If already submitted with same idempotency_key, returns existing result.
    """
    logger.info("project.submit", project_id=project_id, idempotency_key=idempotency_key)
    assumptions: list[str] = []
    
    # Verify project exists
    project = await require_project(project_id, db)
    
    # Idempotency check: look for existing submission event with same key
    # Note: SQLAlchemy JSON queries use cast() for PostgreSQL
    from sqlalchemy import cast, String
    
    if idempotency_key:
        event_query = await db.execute(
            select(ProjectEvent).where(
                ProjectEvent.project_id == project_id,
                ProjectEvent.event_type == "project.submitted",
                cast(ProjectEvent.data["idempotency_key"], String) == idempotency_key,
            ).limit(1)
        )
        existing = event_query.scalar_one_or_none()
        if existing:
            # Return existing submission result
            pm_ref = existing.data.get("pm_ref", "placeholder")
            project_number = existing.data.get("project_number", "placeholder")
            add_assumption(assumptions, f"Idempotent: reused existing submission with key {idempotency_key[:8]}...")
            return make_envelope(
                result={
                    "project_id": project_id,
                    "status": "submitted",
                    "project_number": project_number,
                    "pm_ref": pm_ref,
                    "idempotent": True,
                },
                assumptions=assumptions,
                confidence=0.95,
                inputs={"project_id": project_id, "idempotency_key": idempotency_key},
                intermediates={"existing_event_id": existing.event_id},
                outputs={"project_number": project_number},
                code_version=get_code_version(),
                model_config=get_model_config(),
            )
    
    # Get latest payload for submission
    payload_query = await db.execute(
        select(ProjectPayload).where(ProjectPayload.project_id == project_id).order_by(ProjectPayload.created_at.desc()).limit(1)
    )
    payload_row = payload_query.scalar_one_or_none()
    
    if not payload_row:
        raise HTTPException(status_code=422, detail="No design payload found. Complete design stages first.")
    
    # Prepare project data for PM dispatch
    project_data = {
        "project_id": project_id,
        "name": project.name,
        "customer": project.customer,
        "status": project.status,
        "payload": {
            "module": payload_row.module,
            "config": payload_row.config,
            "cost_snapshot": payload_row.cost_snapshot,
        },
    }
    
    # Enqueue PM dispatch task
    pm_task_id = enqueue_pm_dispatch(project_id, project_data, idempotency_key)
    add_assumption(assumptions, f"PM dispatch enqueued: task_id={pm_task_id}")
    
    # State transition and logging in single transaction
    # Use context manager for explicit transaction control
    try:
        async with transaction(db, operation="project_submit"):
            # State transition: estimating → submitted
            if project.status == "estimating":
                project.status = "submitted"
            
            # Log submission event
            await log_event(
                db,
                project_id,
                "project.submitted",
                actor,
                {
                    "idempotency_key": idempotency_key,
                    "pm_task_id": pm_task_id,
                    "payload_sha256": payload_row.sha256,
                },
            )
            # Transaction auto-commits on successful exit
    except Exception as e:
        logger.error("submission.transaction_failed", project_id=project_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to complete project submission. Changes rolled back."
        )
    
    # Enqueue email notification (if project has manager email)
    # TODO: Extract manager email from project metadata when available
    manager_email = project_data.get("manager_email")
    if manager_email:
        email_task_id = enqueue_email(
            manager_email,
            f"Project {project.name} Submitted",
            "project_submitted",
            {"project_id": project_id, "project_name": project.name},
        )
        add_assumption(assumptions, f"Email notification enqueued: task_id={email_task_id}")
    else:
        add_assumption(assumptions, "No manager email - skipping notification")
    
    result = {
        "project_id": project_id,
        "status": "submitted",
        "project_number": "pending",  # Will be updated by PM dispatch task
        "pm_task_id": pm_task_id,
        "idempotent": False,
    }
    
    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=0.85,
        inputs={"project_id": project_id, "idempotency_key": idempotency_key},
        intermediates={"pm_task_id": pm_task_id, "payload_sha256": payload_row.sha256},
        outputs={"status": "submitted"},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.post("/{project_id}/report", response_model=ResponseEnvelope)
async def generate_report(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Generate PDF report (free, instant, cached).
    
    Pages: (1) Cover, (2) Elevation, (3) Design Output, (4) Notes
    
    Caching: Reports are cached by payload SHA256 for deterministic reuse.
    """
    logger.info("project.generate_report", project_id=project_id)
    assumptions: list[str] = []
    
    # Verify project exists
    await require_project(project_id, db)
    
    # Get latest payload
    payload_query = await db.execute(
        select(ProjectPayload).where(ProjectPayload.project_id == project_id).order_by(ProjectPayload.created_at.desc()).limit(1)
    )
    payload_row = payload_query.scalar_one_or_none()
    
    if not payload_row:
        raise HTTPException(status_code=422, detail="No design payload found for project. Complete design stages first.")
    
    # Convert payload to dict format
    payload = {
        "module": payload_row.module,
        "config": payload_row.config,
        "files": payload_row.files,
        "cost_snapshot": payload_row.cost_snapshot,
    }
    
    # Option 1: Generate synchronously (instant for cached reports)
    # Option 2: Enqueue async task (for heavy generation)
    # For now, use sync for instant response when cached
    artifacts_root = Path(settings.MINIO_BUCKET or "./artifacts").expanduser().resolve()
    artifacts_root.mkdir(parents=True, exist_ok=True)
    
    report_data = await generate_report_from_payload(project_id, payload, artifacts_root)
    
    # Alternative: For async generation, uncomment:
    # report_task_id = enqueue_report_generation(project_id, payload)
    # return ResponseEnvelope(
    #     result={"task_id": report_task_id, "status": "generating"},
    #     assumptions=["Report generation enqueued"],
    #     ...
    # )
    
    add_assumption(assumptions, f"Report {'cached' if report_data['cached'] else 'generated'} by SHA256: {report_data['sha256'][:16]}...")
    
    result = {
        "project_id": project_id,
        "sha256": report_data["sha256"],
        "pdf_ref": report_data["pdf_ref"],
        "cached": report_data["cached"],
        "download_url": f"/artifacts/{report_data['pdf_ref']}",  # Relative URL for API
    }
    
    confidence = 0.95 if report_data["cached"] else 0.90
    
    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=confidence,
        inputs={"project_id": project_id},
        intermediates={"payload_sha256": payload_row.sha256, "cached": report_data["cached"]},
        outputs={"pdf_sha256": report_data["sha256"]},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )

