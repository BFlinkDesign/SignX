"""Enhanced file upload endpoints with virus scanning, thumbnails, and access control."""

from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..auth import get_current_user, TokenData
from ..rbac import require_permission
from ..storage import StorageClient
from ..deps import storage_client
from ..file_upload_service import upload_file, get_presigned_download_url
from ..models_audit import FileUpload
from ..schemas import ResponseEnvelope, add_assumption
from ..common.models import make_envelope
from ..common.helpers import get_code_version, get_model_config
from sqlalchemy import select

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/uploads", tags=["uploads"])


@router.post("", response_model=ResponseEnvelope)
async def upload_file_endpoint(
    file: UploadFile = File(...),
    project_id: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Upload file with virus scanning, thumbnail generation, and metadata storage.
    
    Accepts: images (JPEG, PNG, GIF, WebP), PDFs, DXF, DWG
    Max size: 50 MB
    
    Returns:
        FileUpload metadata with presigned download URL
    """
    from fastapi import Request
    from starlette.requests import Request as StarletteRequest
    
    # Extract IP and user agent from request context
    # Note: We need to pass Request through middleware or dependency
    ip_address = None  # Would be extracted from request
    user_agent = None  # Would be extracted from request
    
    # Upload file
    upload_record = await upload_file(
        db=db,
        storage=storage_client,
        file=file,
        project_id=project_id,
        user_id=current_user.user_id,
        account_id=current_user.account_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    # Generate presigned download URL
    download_url = await get_presigned_download_url(
        storage=storage_client,
        file_key=upload_record.file_key,
        expires_seconds=3600,
    )
    
    result = {
        "upload_id": upload_record.upload_id,
        "file_key": upload_record.file_key,
        "filename": upload_record.filename,
        "content_type": upload_record.content_type,
        "size_bytes": upload_record.size_bytes,
        "sha256": upload_record.sha256,
        "virus_scan_status": upload_record.virus_scan_status,
        "thumbnail_key": upload_record.thumbnail_key,
        "download_url": download_url,
        "expires_in_seconds": 3600,
    }
    
    assumptions: list[str] = []
    add_assumption(assumptions, f"SHA256: {upload_record.sha256[:16]}...")
    if upload_record.virus_scan_status == "clean":
        add_assumption(assumptions, "Virus scan passed")
    elif upload_record.virus_scan_status == "pending":
        add_assumption(assumptions, "Virus scan pending")
    
    if upload_record.thumbnail_key:
        add_assumption(assumptions, "Thumbnail generated")
    
    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=0.95 if upload_record.virus_scan_status == "clean" else 0.8,
        inputs={"filename": file.filename, "content_type": file.content_type},
        intermediates={"sha256": upload_record.sha256, "virus_scan": upload_record.virus_scan_status},
        outputs=result,
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.get("/{upload_id}", response_model=ResponseEnvelope)
async def get_upload(
    upload_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Get file upload metadata and presigned download URL.
    
    Access control: User must have access to the file's account or project.
    """
    # Get upload record
    result = await db.execute(
        select(FileUpload).where(FileUpload.upload_id == upload_id)
    )
    upload_record = result.scalar_one_or_none()
    
    if not upload_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    
    # Check access: user must be in same account or have read permission
    if upload_record.account_id != current_user.account_id:
        # Check if user has file.read permission
        from ..rbac import check_permission
        has_permission = await check_permission(db, current_user, "file.read")
        if not has_permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Generate presigned download URL
    download_url = await get_presigned_download_url(
        storage=storage_client,
        file_key=upload_record.file_key,
        expires_seconds=3600,
    )
    
    # Generate thumbnail URL if available
    thumbnail_url = None
    if upload_record.thumbnail_key:
        thumbnail_url = await get_presigned_download_url(
            storage=storage_client,
            file_key=upload_record.thumbnail_key,
            expires_seconds=3600,
        )
    
    result = {
        "upload_id": upload_record.upload_id,
        "file_key": upload_record.file_key,
        "filename": upload_record.filename,
        "content_type": upload_record.content_type,
        "size_bytes": upload_record.size_bytes,
        "sha256": upload_record.sha256,
        "virus_scan_status": upload_record.virus_scan_status,
        "download_url": download_url,
        "thumbnail_url": thumbnail_url,
        "expires_in_seconds": 3600,
    }
    
    return make_envelope(
        result=result,
        assumptions=[],
        confidence=0.95,
        inputs={"upload_id": upload_id},
        outputs=result,
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.delete("/{upload_id}", response_model=ResponseEnvelope)
@require_permission("file.delete")
async def delete_upload(
    upload_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Delete file upload (soft delete - marks as expired).
    
    Requires: file.delete permission
    """
    result = await db.execute(
        select(FileUpload).where(FileUpload.upload_id == upload_id)
    )
    upload_record = result.scalar_one_or_none()
    
    if not upload_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    
    # Check access
    if upload_record.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Soft delete: set expiration
    from datetime import datetime, timezone, timedelta
    upload_record.expires_at = datetime.now(timezone.utc) + timedelta(seconds=1)
    await db.commit()
    
    # Log audit
    from ..audit import log_audit
    await log_audit(
        db=db,
        action="file.deleted",
        resource_type="file",
        resource_id=str(upload_id),
        user_id=current_user.user_id,
        account_id=current_user.account_id,
        before_state={"filename": upload_record.filename},
    )
    
    return make_envelope(
        result={"deleted": True, "upload_id": upload_id},
        assumptions=[],
        confidence=1.0,
        inputs={"upload_id": upload_id},
        outputs={"deleted": True},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )

