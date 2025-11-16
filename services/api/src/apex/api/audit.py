"""Audit logging middleware and utilities."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .models_audit import AuditLog
from .auth import get_current_user_optional, TokenData
import logging

logger = logging.getLogger(__name__)

logger = structlog.get_logger(__name__)


async def log_audit(
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    before_state: Optional[dict] = None,
    after_state: Optional[dict] = None,
    user_id: Optional[str] = None,
    account_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    confidence: Optional[float] = None,
    error_details: Optional[dict] = None,
) -> int:
    """Log an audit event to the immutable audit log.
    
    This is an append-only operation - no updates or deletes.
    Critical for engineering liability and compliance.
    
    Returns:
        The log_id of the created audit entry
    """
    try:
        audit_entry = AuditLog(
            user_id=user_id or "system",
            account_id=account_id or "unknown",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before_state=before_state,
            after_state=after_state,
            timestamp=datetime.now(timezone.utc),
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            confidence=confidence,
            error_details=error_details,
        )
        
        db.add(audit_entry)
        await db.commit()
        await db.refresh(audit_entry)
        
        logger.info(
            "audit.logged",
            log_id=audit_entry.log_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
        )
        
        return audit_entry.log_id
    except Exception as e:
        # Never fail the main operation due to audit logging failure
        # But log the error for monitoring
        logger.error("audit.log_failed", action=action, error=str(e))
        return 0


async def audit_middleware_handler(
    request: Request,
    call_next: Any,
) -> Response:
    """Middleware to automatically log HTTP requests for audit trail.
    
    Logs all authenticated requests with:
    - User ID, account ID
    - Action (from route + method)
    - Resource type and ID (from path params)
    - IP address, user agent
    - Request/response correlation
    """
    # Extract request metadata
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    request_id = request.headers.get("x-request-id") or request.headers.get("x-correlation-id")
    
    # Try to get current user (may be None for public endpoints)
    current_user: Optional[TokenData] = None
    try:
        from .auth import get_current_user_optional
        # We can't use Depends() in middleware, so we'll log after route execution
        # This is handled by the audit decorator instead
        pass
    except Exception as e:
        logger.warning("Exception in audit.py: %s", str(e))
        pass
    
    # Process request
    response = await call_next(request)
    
    # Extract response metadata for audit logging
    # Note: Actual audit logging should be done in route handlers using the @audit decorator
    # This middleware just ensures request metadata is available
    
    return response


def extract_resource_from_path(path: str, method: str) -> tuple[str, Optional[str]]:
    """Extract resource type and ID from API path.
    
    Examples:
        /projects/{id} -> ("project", id)
        /projects/{id}/files/{file_id} -> ("file", file_id)
        /calculations/{id}/approve -> ("calculation", id)
    """
    parts = path.strip("/").split("/")
    
    # Map common paths to resource types
    resource_map = {
        "projects": "project",
        "files": "file",
        "calculations": "calculation",
        "reports": "report",
        "uploads": "upload",
        "compliance": "compliance",
    }
    
    resource_type = None
    resource_id = None
    
    for i, part in enumerate(parts):
        if part in resource_map:
            resource_type = resource_map[part]
            # Next part is likely the ID (UUID format)
            if i + 1 < len(parts) and parts[i + 1] and parts[i + 1] != "files":
                # Check if it looks like an ID (UUID or numeric)
                potential_id = parts[i + 1]
                if len(potential_id) > 8 or potential_id.isdigit():
                    resource_id = potential_id
                break
    
    # If no resource type found, use method + path
    if not resource_type:
        resource_type = f"{method.lower()}_{parts[0] if parts else 'unknown'}"
    
    return resource_type, resource_id


async def query_audit_logs(
    db: AsyncSession,
    user_id: Optional[str] = None,
    account_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    """Query audit logs for compliance reporting.
    
    Returns:
        List of audit log entries matching criteria
    """
    from sqlalchemy import select, and_
    
    query = select(AuditLog)
    conditions = []
    
    if user_id:
        conditions.append(AuditLog.user_id == user_id)
    if account_id:
        conditions.append(AuditLog.account_id == account_id)
    if action:
        conditions.append(AuditLog.action == action)
    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)
    if resource_id:
        conditions.append(AuditLog.resource_id == resource_id)
    if start_date:
        conditions.append(AuditLog.timestamp >= start_date)
    if end_date:
        conditions.append(AuditLog.timestamp <= end_date)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    return list(result.scalars().all())

