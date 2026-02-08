"""File upload and attachment endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..common.helpers import log_event, require_project
from ..common.models import make_envelope
from ..db import get_db
from ..deps import get_code_version, get_model_config, settings, storage_client
from ..schemas import ResponseEnvelope, add_assumption

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["files"])


@router.post("/{project_id}/files/presign", response_model=ResponseEnvelope)
async def presign_upload(
    project_id: str,
    req: dict,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Generate presigned URL for MinIO upload.
    
    Body: {filename: str, content_type: str}
    Returns presigned PUT URL for direct client upload to MinIO.
    """
    filename = req.get("filename", "")
    content_type = req.get("content_type", "application/octet-stream")
    logger.info("files.presign", project_id=project_id, filename=filename)

    # Verify project exists
    await require_project(project_id, db)

    # Generate unique upload ID and blob key
    upload_id = uuid.uuid4().hex[:16]
    blob_key = f"projects/{project_id}/files/{upload_id}/{filename}"
    
    # Get presigned URL from storage client
    presigned_url = storage_client.presign_put(
        object_name=blob_key,
        expires_seconds=3600,
        content_type=content_type,
    )

    result = {
        "presigned_url": presigned_url or f"{settings.MINIO_URL}/upload/{project_id}/{upload_id}",
        "blob_key": blob_key,
        "expires_in_seconds": 3600,
        "upload_id": upload_id,
    }

    assumptions: list[str] = []
    if presigned_url:
        add_assumption(assumptions, "MinIO presigned URL generated")
    else:
        add_assumption(assumptions, "MinIO presigned URL placeholder (client not configured)")

    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=0.95 if presigned_url else 0.7,
        inputs={"project_id": project_id, "filename": filename},
        intermediates={},
        outputs={"blob_key": blob_key},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.post("/{project_id}/files/attach", response_model=ResponseEnvelope)
async def attach_file(
    project_id: str,
    req: dict,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Attach uploaded file to project with SHA256 verification.
    
    Body: {blob_key: str, sha256: str}
    """
    blob_key = req.get("blob_key", "")
    sha256 = req.get("sha256", "")
    actor = req.get("actor", "system")
    logger.info("files.attach", project_id=project_id, blob_key=blob_key)

    # Verify project exists
    await require_project(project_id, db)

    # Verify file exists in storage
    file_exists = storage_client.object_exists(blob_key)
    
    # Verify SHA256 if storage client is configured
    sha256_valid = False
    if storage_client._client and file_exists:
        stored_sha256 = storage_client.get_object_sha256(blob_key)
        sha256_valid = stored_sha256 and stored_sha256.lower() == sha256.lower()
        if not sha256_valid and sha256:
            logger.error("files.sha256_mismatch", blob_key=blob_key, expected=sha256[:16], got=stored_sha256[:16] if stored_sha256 else None)
            # Log event with error flag
            await log_event(db, project_id, "file.validation_failed", actor, {
                "blob_key": blob_key, 
                "expected_sha256": sha256[:16], 
                "got_sha256": stored_sha256[:16] if stored_sha256 else None,
                "reason": "sha256_mismatch"
            })
            raise HTTPException(status_code=422, detail=f"SHA256 mismatch for {blob_key}: expected {sha256[:16]}..., got {stored_sha256[:16] if stored_sha256 else 'none'}")

    # Log event
    await log_event(db, project_id, "file.attached", actor, {"blob_key": blob_key, "sha256": sha256, "validated": sha256_valid})

    result = {
        "project_id": project_id,
        "blob_key": blob_key,
        "sha256": sha256,
        "attached_at": datetime.now(UTC).isoformat(),
        "validated": sha256_valid,
    }

    assumptions: list[str] = []
    add_assumption(assumptions, f"SHA256: {sha256[:16]}...")
    if sha256_valid:
        add_assumption(assumptions, "SHA256 verified against stored file")
    elif storage_client._client:
        add_assumption(assumptions, "SHA256 verification failed or file not found")
    else:
        add_assumption(assumptions, "SHA256 verification skipped (storage not configured)")

    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=0.95 if sha256_valid else (0.85 if file_exists else 0.6),
        inputs={"project_id": project_id, "blob_key": blob_key},
        intermediates={"sha256": sha256, "validated": sha256_valid},
        outputs=result,
        code_version=get_code_version(),
        model_config=get_model_config(),
    )
