"""Shared helper functions for API routes to reduce duplication."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, Request
from slowapi.util import get_remote_address

from ..db import Project, ProjectEvent


async def require_project(project_id: str, db: AsyncSession) -> Project:
    """Verify project exists and return it, or raise 404.
    
    Reduces duplication across routes that need to validate project existence.
    """
    result_query = await db.execute(select(Project).where(Project.project_id == project_id))
    project = result_query.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def fetch_project_with_history(project_id: str, db: AsyncSession) -> Project:
    """Fetch a project with payload and event history eagerly loaded.

    Centralising the eager-loading configuration keeps N+1 optimisations in one
    place and ensures new callers inherit the same performance characteristics.
    """

    query = (
        select(Project)
        .options(
            selectinload(Project.payloads),
            selectinload(Project.events),
        )
        .where(Project.project_id == project_id)
    )

    result = await db.execute(query)
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


def _extract_request_metadata(request: Optional[Request]) -> dict[str, Any]:
    """Extract IP address, user agent, and other request metadata.
    
    Returns dict with ip_address, user_agent, and optional proxy headers.
    """
    metadata: dict[str, Any] = {}
    
    if request:
        # Get IP address (respects X-Forwarded-For for proxies)
        try:
            metadata["ip_address"] = get_remote_address(request)
        except Exception:
            metadata["ip_address"] = request.client.host if request.client else "unknown"
        
        # Get user agent
        metadata["user_agent"] = request.headers.get("User-Agent", "unknown")
        
        # Get additional headers if available
        if "X-Forwarded-For" in request.headers:
            metadata["x_forwarded_for"] = request.headers["X-Forwarded-For"]
        if "X-Real-IP" in request.headers:
            metadata["x_real_ip"] = request.headers["X-Real-IP"]
        
        # Get request ID if available
        if hasattr(request.state, "trace_id"):
            metadata["request_id"] = request.state.trace_id
    
    return metadata


async def log_event(
    session: AsyncSession,
    project_id: str,
    event_type: str,
    actor: str,
    data: dict | None = None,
    request: Optional[Request] = None,
    before_state: Optional[dict] = None,
    after_state: Optional[dict] = None,
) -> None:
    """Helper to append event to audit log with full compliance metadata.
    
    Captures:
    - Who: actor (user_id)
    - What: event_type, before/after states
    - When: timestamp (auto)
    - Where: IP address, user agent
    - Why: context in data field
    
    Args:
        session: Database session
        project_id: Project identifier
        event_type: Event type (e.g., "project.created", "calculation.approved")
        actor: User ID or system identifier
        data: Additional event data
        request: FastAPI request object (optional, for IP/user agent)
        before_state: State before change (for mutations)
        after_state: State after change (for mutations)
    """
    # Build comprehensive event data
    event_data = dict(data or {})
    
    # Add request metadata (IP, user agent)
    request_metadata = _extract_request_metadata(request)
    if request_metadata:
        event_data["request_metadata"] = request_metadata
    
    # Add before/after states for mutations
    if before_state is not None:
        event_data["before"] = before_state
    if after_state is not None:
        event_data["after"] = after_state
    
    # Compute diff if both states provided
    if before_state is not None and after_state is not None:
        diff = _compute_diff(before_state, after_state)
        if diff:
            event_data["diff"] = diff
    
    event = ProjectEvent(
        project_id=project_id,
        event_type=event_type,
        actor=actor,
        timestamp=datetime.now(timezone.utc),
        data=event_data,
    )
    session.add(event)
    await session.flush()


def _compute_diff(before: dict, after: dict) -> dict:
    """Compute diff between before and after states.
    
    Returns dict with:
    - added: keys only in after
    - removed: keys only in before
    - changed: keys with different values
    """
    before_keys = set(before.keys())
    after_keys = set(after.keys())
    
    diff: dict = {
        "added": {k: after[k] for k in after_keys - before_keys},
        "removed": {k: before[k] for k in before_keys - after_keys},
        "changed": {},
    }
    
    # Find changed values
    for key in before_keys & after_keys:
        if before[key] != after[key]:
            diff["changed"][key] = {"before": before[key], "after": after[key]}
    
    # Remove empty sections
    return {k: v for k, v in diff.items() if v}

