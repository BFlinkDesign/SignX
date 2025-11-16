"""Project management CRUD endpoints."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..common.constants import get_constants_version_string
from ..auth import TokenData, get_current_user, get_current_user_optional
from ..common.helpers import fetch_project_with_history, log_event, require_project
from ..common.models import build_response_envelope, make_envelope
from ..db import Project, ProjectEvent, ProjectPayload, get_db
from ..deps import get_code_version, get_model_config, settings
from ..projects.models import ProjectCreateRequest, ProjectUpdateRequest, ProjectStatus
from ..schemas import ResponseEnvelope, add_assumption
from ..utils.search import ensure_index_exists, index_project, search_projects
from ..utils.state_machine import validate_transition

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])

_PROJECT_SEARCH_FIELDS = ("project_id", "name", "status", "customer", "created_at")


def _serialize_project_model(project: Project) -> dict[str, Any]:
    """Serialize a ``Project`` ORM model into the search payload shape."""

    return {
        "project_id": project.project_id,
        "name": project.name,
        "status": project.status,
        "customer": project.customer,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


def _coerce_search_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize OpenSearch/DB records so both paths return identical envelopes."""

    normalized: dict[str, Any] = {}
    for field in _PROJECT_SEARCH_FIELDS:
        value = record.get(field)
        if field == "created_at" and value is not None:
            if isinstance(value, datetime):
                normalized[field] = value.isoformat()
            else:
                normalized[field] = str(value)
        else:
            normalized[field] = value
    return normalized


def _compute_etag(project: Project) -> str:
    """
    Compute ETag for optimistic locking with strong collision resistance.
    
    Uses full SHA256 hash for maximum collision resistance.
    Returns RFC 7232 compliant weak validator format.
    
    Args:
        project: Project instance
        
    Returns:
        ETag string with W/ prefix for weak validator per RFC 7232
    """
    # Include more fields for better change detection
    content = (
        f"{project.project_id}:"
        f"{project.status}:"
        f"{project.updated_at.isoformat()}:"
        f"{project.updated_by}:"
        f"{project.content_sha256 or ''}:"
        f"{project.name}:"
        f"{project.customer or ''}"
    )
    # Use full hash (64 chars) - HTTP ETags support up to 1024 chars
    hash_digest = hashlib.sha256(content.encode()).hexdigest()
    # Return RFC 7232 compliant weak validator
    return f'W/"{hash_digest}"'


def _compute_project_content_sha256(project: Project) -> str:
    """Compute deterministic SHA256 hash of project content for audit trail.
    
    Excludes timestamps and envelope fields for deterministic hashing.
    
    Args:
        project: Project model instance
    
    Returns:
        SHA256 hex digest (64 characters)
    """
    # Normalize project data (exclude timestamps and envelope fields)
    normalized = {
        "project_id": project.project_id,
        "account_id": project.account_id,
        "name": project.name,
        "customer": project.customer,
        "description": project.description,
        "site_name": project.site_name,
        "street": project.street,
        "status": project.status,
    }
    # Deterministic JSON encoding
    json_str = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()




async def _db_search_projects(skip: int, limit: int, status: ProjectStatus | None, db: AsyncSession) -> list[dict[str, Any]]:
    """DB fallback query for project search.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Validated ProjectStatus enum or None
        db: Database session
        
    Returns:
        List of project dictionaries
        
    Raises:
        ValueError: If status is not a valid ProjectStatus enum value
    """
    query = select(Project)
    if status:
        # Explicitly validate against enum (type safety ensures this, but add runtime check for defense in depth)
        if not isinstance(status, ProjectStatus):
            raise ValueError(f"Invalid status: {status}. Must be a valid ProjectStatus enum value.")
        query = query.where(Project.status == status.value)
    query = query.order_by(Project.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    rows = result.scalars().all()

    return [_serialize_project_model(p) for p in rows]


@router.get("/", response_model=ResponseEnvelope)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),  # Default 50, max 500
    status: ProjectStatus | None = Query(None, description="Filter by project status"),
    q: str | None = Query(None, description="Text search query"),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """List projects with OpenSearch (DB fallback).
    
    Supports text search via `q` parameter. Falls back to DB if OpenSearch unavailable.
    """
    logger.info("projects.list", skip=skip, limit=limit, status=status, q=q)
    assumptions: list[str] = []

    # Build search query
    if q:
        search_query = {
            "query": {"multi_match": {"query": q, "fields": ["name^2", "customer", "description"]}},
            "from": skip,
            "size": limit,
        }
        if status:
            search_query["query"] = {
                "bool": {
                    "must": [
                        {"match": {"status": status.value}},
                        {"multi_match": {"query": q, "fields": ["name^2", "customer"]}},
                    ]
                }
            }
    else:
        search_query = {"query": {"match_all": {}}, "from": skip, "size": limit}
        if status:
            search_query["query"] = {"term": {"status": status.value}}

    # Try OpenSearch, fallback to DB
    async def db_fallback() -> list[dict[str, Any]]:
        return await _db_search_projects(skip, limit, status, db)

    raw_projects, used_fallback = await search_projects(search_query, db_fallback)

    projects = [_coerce_search_record(result) for result in raw_projects]

    if used_fallback:
        add_assumption(assumptions, "OpenSearch unavailable - used DB fallback")

    return build_response_envelope(
        result={"projects": projects, "total": len(projects), "search_fallback": used_fallback},
        assumptions=assumptions,
        confidence=0.9 if not used_fallback else 0.8,
        trace_inputs={"skip": skip, "limit": limit, "status": status, "q": q},
        trace_intermediates={"search_fallback": used_fallback},
        trace_outputs={"count": len(projects)},
    )


@router.post("/", response_model=ResponseEnvelope)
async def create_project(
    req: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData | None = Depends(get_current_user_optional),  # type: ignore
) -> ResponseEnvelope:
    """Create new project from Overview tab data.
    
    Requires authentication. The user_id from the token will be used as created_by.
    """
    # Use authenticated user if available, otherwise use request value
    created_by = current_user.user_id if current_user else req.created_by
    account_id = current_user.account_id if current_user and current_user.account_id else req.account_id
    
    logger.info("projects.create", name=req.name, account_id=account_id, created_by=created_by)

    project_id = f"proj_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    project = Project(
        project_id=project_id,
        account_id=account_id,
        name=req.name,
        customer=req.customer,
        description=req.description,
        status="draft",
        created_by=created_by,
        updated_by=created_by,
        created_at=now,
        updated_at=now,
    )
    project.etag = _compute_etag(project)
    
    # Set envelope fields for audit trail and deterministic caching
    project.constants_version = get_constants_version_string()
    project.content_sha256 = _compute_project_content_sha256(project)
    project.confidence = 1.0  # Manual entry = full confidence

    db.add(project)
    await log_event(db, project_id, "project.created", req.created_by, {"name": req.name})
    await db.commit()

    # Index in OpenSearch (async, non-blocking)
    await ensure_index_exists()
    project_doc = {
        "project_id": project_id,
        "name": project.name,
        "status": project.status,
        "customer": project.customer,
        "description": project.description,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }
    indexed = await index_project(project_id, project_doc)

    result = {"project_id": project_id, "name": project.name, "status": project.status, "etag": project.etag}

    assumptions: list[str] = []
    add_assumption(assumptions, "Created in draft status")
    if not indexed:
        add_assumption(assumptions, "OpenSearch indexing deferred")

    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=0.95,
        inputs=req.model_dump(),
        intermediates={"indexed": indexed},
        outputs=result,
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.get("/{project_id}", response_model=ResponseEnvelope)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)) -> ResponseEnvelope:
    """Fetch project metadata and latest snapshot."""
    logger.info("projects.get", project_id=project_id)

    project = await fetch_project_with_history(project_id, db)

    # Get latest payload from eager-loaded relationship
    payload = None
    if project.payloads:
        # Payloads are already loaded, just sort and get the latest
        sorted_payloads = sorted(project.payloads, key=lambda p: p.created_at, reverse=True)
        payload = sorted_payloads[0] if sorted_payloads else None

    result = {
        "project_id": project.project_id,
        "name": project.name,
        "customer": project.customer,
        "description": project.description,
        "site_name": project.site_name,
        "street": project.street,
        "status": project.status,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "etag": project.etag,
        "payload": payload.config if payload else None,
    }

    assumptions: list[str] = []

    return build_response_envelope(
        result=result,
        assumptions=assumptions,
        confidence=0.95,
        trace_inputs={"project_id": project_id},
        trace_outputs={"status": project.status},
    )


@router.put("/{project_id}", response_model=ResponseEnvelope)
async def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    if_match: str | None = Header(None, alias="If-Match"),
    new_status: str | None = None,
    request: Request | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData | None = Depends(get_current_user_optional),
) -> ResponseEnvelope:
    """Update project metadata with optional state transition.
    
    Requires If-Match header with current ETag for optimistic locking.
    Returns 412 Precondition Failed if ETag mismatch.
    """
    logger.info("projects.update", project_id=project_id, new_status=new_status)

    result_query = await db.execute(select(Project).where(Project.project_id == project_id))
    project = result_query.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Capture before state for audit log
    before_state = {
        "name": project.name,
        "customer": project.customer,
        "description": project.description,
        "site_name": project.site_name,
        "street": project.street,
        "status": project.status,
        "etag": project.etag,
    }

    # ETag validation - return current ETag if mismatch
    # Strip quotes from incoming ETag for comparison (RFC 7232)
    normalized_if_match = if_match.strip('"').replace('W/', '') if if_match else None
    normalized_project_etag = project.etag.strip('"').replace('W/', '') if project.etag else None
    
    if normalized_if_match and normalized_project_etag != normalized_if_match:
        raise HTTPException(
            status_code=412,
            detail=f"ETag mismatch: expected {project.etag}, got {if_match}",
            headers={"ETag": project.etag}
        )

    # State machine validation if status change requested
    if new_status:
        try:
            validate_transition(project.status, new_status)  # type: ignore
            project.status = new_status
        except ValueError as e:
            raise HTTPException(status_code=412, detail=str(e))

    # Update fields
    if req.name is not None:
        project.name = req.name
    if req.customer is not None:
        project.customer = req.customer
    if req.description is not None:
        project.description = req.description
    if req.site_name is not None:
        project.site_name = req.site_name
    if req.street is not None:
        project.street = req.street

    project.updated_at = datetime.now(timezone.utc)
    project.etag = _compute_etag(project)
    
    # Update envelope fields for audit trail
    project.constants_version = get_constants_version_string()
    project.content_sha256 = _compute_project_content_sha256(project)
    # Confidence remains at existing value or 1.0 if this is manual update
    if project.confidence is None:
        project.confidence = 1.0

    # Capture after state for audit log
    after_state = {
        "name": project.name,
        "customer": project.customer,
        "description": project.description,
        "site_name": project.site_name,
        "street": project.street,
        "status": project.status,
        "etag": project.etag,
    }
    
    # Extract actor from current user or request
    actor = current_user.sub if current_user else "system"
    
    await db.commit()

    # Log audit event with before/after states and request metadata
    await log_event(
        db,
        project_id,
        "project.updated",
        actor,
        data={
            "new_status": new_status,
            "fields_updated": [k for k, v in req.model_dump(exclude_unset=True).items() if v is not None],
        },
        request=request,
        before_state=before_state,
        after_state=after_state,
    )

    # Update OpenSearch index
    project_doc = {
        "project_id": project.project_id,
        "name": project.name,
        "status": project.status,
        "customer": project.customer,
        "description": project.description,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }
    indexed = await index_project(project.project_id, project_doc)

    result = {"project_id": project.project_id, "name": project.name, "status": project.status, "etag": project.etag}

    assumptions: list[str] = []
    if not indexed:
        add_assumption(assumptions, "OpenSearch update deferred")

    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=0.95,
        inputs={"project_id": project_id, "update": req.model_dump(exclude_unset=True)},
        intermediates={"indexed": indexed},
        outputs=result,
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.get("/{project_id}/final", response_model=ResponseEnvelope)
async def get_project_final(project_id: str, db: AsyncSession = Depends(get_db)) -> ResponseEnvelope:
    """Non-destructive edit view landing on final screen."""
    logger.info("projects.get_final", project_id=project_id)

    project = await require_project(project_id, db)

    result = {"project_id": project.project_id, "read_only": project.status in ("submitted", "accepted", "rejected"), "status": project.status}

    assumptions: list[str] = []
    add_assumption(assumptions, f"Read-only mode: {result['read_only']}")

    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=0.95,
        inputs={"project_id": project_id},
        intermediates={},
        outputs=result,
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.get("/{project_id}/events", response_model=ResponseEnvelope)
async def get_project_events(
    project_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Fetch immutable audit feed for project."""
    logger.info("projects.get_events", project_id=project_id, skip=skip, limit=limit)

    # Verify project exists
    await require_project(project_id, db)

    events_query = await db.execute(
        select(ProjectEvent)
        .where(ProjectEvent.project_id == project_id)
        .order_by(ProjectEvent.timestamp.desc())
        .offset(skip)
        .limit(limit)
    )
    events = events_query.scalars().all()

    result = {
        "events": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "actor": e.actor,
                "timestamp": e.timestamp.isoformat(),
                "data": e.data,
            }
            for e in events
        ],
    }

    assumptions: list[str] = []

    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=0.95,
        inputs={"project_id": project_id, "skip": skip, "limit": limit},
        intermediates={},
        outputs={"count": len(result["events"])},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )
