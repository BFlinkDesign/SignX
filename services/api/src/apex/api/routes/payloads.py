"""Project payload management endpoints."""

from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..common.hashing import compute_payload_sha256
from ..common.helpers import require_project
from ..common.models import make_envelope
from ..common.transactions import with_transaction
from ..common.validation import validate_module
from ..db import ProjectPayload, get_db
from ..deps import get_code_version, get_model_config
from ..schemas import ResponseEnvelope, add_assumption

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["payloads"])


# SHA256 computation moved to common.hashing.compute_payload_sha256


@with_transaction
@router.post("/{project_id}/payload", response_model=ResponseEnvelope)
async def save_payload(
    project_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    actor: str = "system",
) -> ResponseEnvelope:
    """Save project design payload with deterministic SHA256.
    
    Body: {module: str, config: dict, files: list[str], cost_snapshot: dict}
    Returns: {payload_id: int, sha256: str}
    """
    logger.info("payload.save", project_id=project_id, module=payload.get("module"))
    assumptions: list[str] = []
    
    # Verify project exists
    await require_project(project_id, db)
    
    # Validate required fields
    module = validate_module(payload.get("module", ""))
    
    # Compute SHA256
    sha256 = compute_payload_sha256(payload)
    
    # Check for duplicate payload (same SHA256)
    existing_query = await db.execute(
        select(ProjectPayload).where(
            ProjectPayload.project_id == project_id,
            ProjectPayload.sha256 == sha256,
        ).limit(1)
    )
    existing = existing_query.scalar_one_or_none()
    if existing:
        add_assumption(assumptions, f"Payload already exists with same SHA256: {sha256[:16]}...")
        return make_envelope(
            result={"payload_id": existing.payload_id, "sha256": existing.sha256, "duplicate": True},
            assumptions=assumptions,
            confidence=0.95,
            inputs={"project_id": project_id},
            intermediates={"sha256": sha256},
            outputs={"payload_id": existing.payload_id},
            code_version=get_code_version(),
            model_config=get_model_config(),
        )
    
    # Create new payload
    payload_row = ProjectPayload(
        project_id=project_id,
        module=module,
        config=payload.get("config", {}),
        files=payload.get("files", []),
        cost_snapshot=payload.get("cost_snapshot", {}),
        sha256=sha256,
        created_at=datetime.now(timezone.utc),
    )
    
    db.add(payload_row)
    await db.flush()  # Get payload_id
    
    # Log event
    from ..common.helpers import log_event
    await log_event(
        db,
        project_id,
        "payload.saved",
        actor,
        {"payload_id": payload_row.payload_id, "module": module, "sha256": sha256},
    )
    
    # Transaction auto-commits via decorator
    
    result = {
        "payload_id": payload_row.payload_id,
        "sha256": sha256,
        "duplicate": False,
    }
    
    add_assumption(assumptions, f"Payload saved with SHA256: {sha256[:16]}...")
    
    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=0.95,
        inputs={"project_id": project_id, "module": module},
        intermediates={"sha256": sha256},
        outputs=result,
        code_version=get_code_version(),
        model_config=get_model_config(),
    )

