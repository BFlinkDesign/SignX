"""ETag generation and optimistic locking utilities."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def compute_etag(content: dict[str, Any], updated_at: datetime | str | None = None) -> str:
    """Compute ETag from content + timestamp.
    
    Args:
        content: Dictionary with state to hash
        updated_at: Optional timestamp for version tracking
    
    Returns:
        SHA256 hex digest (truncated to 32 chars for readability)
    """
    # Sort keys for deterministic hash
    sorted_items = sorted(content.items())
    content_str = str(sorted_items)
    
    # Add timestamp if provided
    if updated_at:
        if isinstance(updated_at, datetime):
            timestamp_str = updated_at.isoformat()
        else:
            timestamp_str = str(updated_at)
        content_str = f"{content_str}:{timestamp_str}"
    
    # Compute hash
    etag = hashlib.sha256(content_str.encode()).hexdigest()[:32]
    return etag


def compute_project_etag(
    project_id: str,
    status: str,
    updated_at: datetime,
    additional_fields: dict[str, Any] | None = None,
) -> str:
    """Compute ETag for project entity.
    
    Args:
        project_id: Project identifier
        status: Current project status
        updated_at: Last updated timestamp
        additional_fields: Optional additional fields to include in hash
    
    Returns:
        ETag hex digest
    """
    content = {
        "project_id": project_id,
        "status": status,
    }
    
    # Include additional fields if provided
    if additional_fields:
        content.update(additional_fields)
    
    return compute_etag(content, updated_at)


def validate_if_match(current_etag: str, if_match_header: str | None) -> tuple[bool, str | None]:
    """Validate If-Match header against current ETag.
    
    Args:
        current_etag: Current entity ETag from database
        if_match_header: If-Match header value from request
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not if_match_header:
        return True, None  # No If-Match header, proceed
    
    # Clean header value (remove quotes if present)
    if_match_etag = if_match_header.strip().strip('"')
    
    if current_etag != if_match_etag:
        logger.warning(
            "etag_mismatch",
            expected=current_etag,
            received=if_match_etag,
        )
        return False, f"ETag mismatch: expected {current_etag}, got {if_match_etag}"
    
    return True, None

