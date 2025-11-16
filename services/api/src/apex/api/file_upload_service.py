"""Enhanced file upload service with virus scanning, thumbnails, and R2/S3 support."""

from __future__ import annotations

import asyncio
import hashlib
import io
from pathlib import Path
from typing import Optional, BinaryIO
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .storage import StorageClient
from .models_audit import FileUpload
from .audit import log_audit
from .deps import settings

logger = structlog.get_logger(__name__)


# Allowed file types
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_DOCUMENT_TYPES = {"application/pdf", "application/dxf", "application/x-dwg", "image/dwg"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_DOCUMENT_TYPES

# Max file size: 50 MB
MAX_FILE_SIZE = 50 * 1024 * 1024

# Virus scanning (async wrapper for ClamAV or similar)
async def scan_file_for_viruses(file_content: bytes, filename: str) -> tuple[str, Optional[str]]:
    """Scan file for viruses using ClamAV or similar.
    
    Returns:
        Tuple of (status, error_message)
        Status: "clean", "infected", "error", "pending"
    """
    # In production, integrate with ClamAV daemon or cloud scanning service
    # For now, return "pending" if no scanner available
    
    # Check if ClamAV is available
    try:
        import clamd
        
        # Connect to ClamAV daemon (default: localhost:3310)
        cd = clamd.ClamdUnixSocket()  # or ClamdNetworkSocket() for remote
        
        # Scan file content
        result = cd.instream(io.BytesIO(file_content))
        
        if result["stream"][0] == "OK":
            return "clean", None
        elif result["stream"][0].startswith("FOUND"):
            virus_name = result["stream"][0].split()[1]
            return "infected", f"Virus detected: {virus_name}"
        else:
            return "error", "Scan failed"
            
    except ImportError:
        logger.warning("virus_scan.not_available", reason="clamd package not installed")
        return "pending", None
    except Exception as e:
        logger.error("virus_scan.failed", error=str(e))
        return "error", str(e)


async def generate_thumbnail(
    file_content: bytes,
    content_type: str,
    max_size: tuple[int, int] = (300, 300),
) -> Optional[bytes]:
    """Generate thumbnail for image files.
    
    Returns:
        Thumbnail bytes (JPEG) or None if not an image
    """
    if not PIL_AVAILABLE:
        logger.warning("thumbnail.pil_not_available")
        return None
    
    if content_type not in ALLOWED_IMAGE_TYPES:
        return None
    
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(file_content))
        
        # Convert to RGB if necessary (handles PNG transparency)
        if image.mode in ("RGBA", "P"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
            image = background
        
        # Resize maintaining aspect ratio
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert to JPEG bytes
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=85, optimize=True)
        return output.getvalue()
        
    except Exception as e:
        logger.error("thumbnail.generation_failed", error=str(e))
        return None


async def upload_file(
    db: AsyncSession,
    storage: StorageClient,
    file: UploadFile,
    project_id: Optional[str],
    user_id: str,
    account_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> FileUpload:
    """Upload file with virus scanning, thumbnail generation, and metadata storage.
    
    Args:
        db: Database session
        storage: Storage client (MinIO/S3/R2)
        file: Uploaded file
        project_id: Optional project association
        user_id: User who uploaded
        account_id: Account context
        ip_address: Client IP (for audit)
        user_agent: Client user agent (for audit)
    
    Returns:
        FileUpload model instance
    
    Raises:
        HTTPException: If file type/size invalid or virus detected
    """
    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed: {file.content_type}. Allowed: {ALLOWED_TYPES}",
        )
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Validate file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large: {file_size} bytes. Max: {MAX_FILE_SIZE} bytes",
        )
    
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty",
        )
    
    # Compute SHA256
    sha256 = hashlib.sha256(content).hexdigest()
    
    # Check if file already exists (deduplication)
    existing = await db.execute(
        select(FileUpload).where(FileUpload.sha256 == sha256)
    )
    existing_upload = existing.scalar_one_or_none()
    
    if existing_upload:
        logger.info("file.duplicate_detected", sha256=sha256[:16], existing_id=existing_upload.upload_id)
        # Return existing file but create new association if different project
        if project_id and existing_upload.project_id != project_id:
            # Create new upload record for this project association
            new_upload = FileUpload(
                file_key=existing_upload.file_key,  # Same storage key
                filename=file.filename or "unknown",
                content_type=file.content_type or "application/octet-stream",
                size_bytes=file_size,
                sha256=sha256,
                virus_scan_status=existing_upload.virus_scan_status,
                virus_scan_at=existing_upload.virus_scan_at,
                thumbnail_key=existing_upload.thumbnail_key,
                project_id=project_id,
                uploaded_by=user_id,
                account_id=account_id,
            )
            db.add(new_upload)
            await db.commit()
            await db.refresh(new_upload)
            return new_upload
        return existing_upload
    
    # Virus scan
    scan_status, scan_error = await scan_file_for_viruses(content, file.filename or "unknown")
    
    if scan_status == "infected":
        # Log audit event for security
        await log_audit(
            db=db,
            action="file.upload_blocked",
            resource_type="file",
            user_id=user_id,
            account_id=account_id,
            ip_address=ip_address,
            user_agent=user_agent,
            error_details={"reason": "virus_detected", "message": scan_error, "filename": file.filename},
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File rejected: {scan_error}",
        )
    
    # Generate storage key
    from uuid import uuid4
    upload_id = uuid4().hex[:16]
    file_key = f"uploads/{account_id}/{upload_id}/{file.filename or 'file'}"
    
    # Upload to storage
    if storage._client:
        try:
            from minio import Minio
            from minio.error import S3Error
            
            storage._client.put_object(
                storage.bucket,
                file_key,
                io.BytesIO(content),
                length=file_size,
                content_type=file.content_type or "application/octet-stream",
            )
            logger.info("file.uploaded", file_key=file_key, size=file_size)
        except Exception as e:
            logger.error("file.storage_upload_failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage",
            )
    else:
        logger.warning("file.storage_not_configured", file_key=file_key)
    
    # Generate thumbnail if image
    thumbnail_key = None
    if file.content_type in ALLOWED_IMAGE_TYPES:
        thumbnail_bytes = await generate_thumbnail(content, file.content_type)
        if thumbnail_bytes:
            thumbnail_key = f"{file_key}.thumbnail.jpg"
            if storage._client:
                try:
                    storage._client.put_object(
                        storage.bucket,
                        thumbnail_key,
                        io.BytesIO(thumbnail_bytes),
                        length=len(thumbnail_bytes),
                        content_type="image/jpeg",
                    )
                    logger.info("file.thumbnail_generated", thumbnail_key=thumbnail_key)
                except Exception as e:
                    logger.error("file.thumbnail_upload_failed", error=str(e))
                    # Don't fail the upload if thumbnail fails
    
    # Create database record
    upload_record = FileUpload(
        file_key=file_key,
        filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=file_size,
        sha256=sha256,
        virus_scan_status=scan_status,
        virus_scan_at=datetime.now(timezone.utc) if scan_status != "pending" else None,
        thumbnail_key=thumbnail_key,
        project_id=project_id,
        uploaded_by=user_id,
        account_id=account_id,
    )
    
    db.add(upload_record)
    await db.commit()
    await db.refresh(upload_record)
    
    # Log audit event
    await log_audit(
        db=db,
        action="file.uploaded",
        resource_type="file",
        resource_id=str(upload_record.upload_id),
        after_state={
            "filename": file.filename,
            "size_bytes": file_size,
            "sha256": sha256[:16],
            "virus_scan_status": scan_status,
        },
        user_id=user_id,
        account_id=account_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    logger.info(
        "file.upload_complete",
        upload_id=upload_record.upload_id,
        file_key=file_key,
        sha256=sha256[:16],
        virus_scan_status=scan_status,
    )
    
    return upload_record


async def get_presigned_download_url(
    storage: StorageClient,
    file_key: str,
    expires_seconds: int = 3600,
) -> Optional[str]:
    """Generate presigned download URL for file access.
    
    Returns:
        Presigned URL or None if storage not configured
    """
    if not storage._client:
        return None
    
    try:
        from datetime import timedelta
        
        url = storage._client.presigned_get_object(
            storage.bucket,
            file_key,
            expires=timedelta(seconds=expires_seconds),
        )
        return url
    except Exception as e:
        logger.error("file.presign_failed", file_key=file_key, error=str(e))
        return None



