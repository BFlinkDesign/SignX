"""Audit logging middleware for mutation tracking."""

from __future__ import annotations

import json
import structlog
from typing import Any

logger = structlog.get_logger(__name__)


async def audit_mutations(request: Any, response: Any) -> None:
    """Log mutations to audit trail.
    
    Currently uses ProjectEvent table via log_event helper.
    This middleware is a placeholder for future enhancement.
    """
    # Only audit mutations
    if request.method not in ["POST", "PUT", "PATCH", "DELETE"]:
        return
    
    # Extract actor from request (JWT or default)
    actor = getattr(request.state, "user_id", "system")
    
    # Log to structured logs (already happens via ProjectEvent in routes)
    logger.info(
        "audit.mutation",
        method=request.method,
        path=request.url.path,
        actor=actor,
        status_code=response.status_code,
    )
    

async def audit_request_middleware(request: Any, call_next: Any) -> Any:
    """Middleware to audit all mutations.
    
    Note: Actual audit logging happens in routes via log_event.
    This is just a pass-through for now.
    """
    response = await call_next(request)
    
    # Async audit logging (don't block response)
    try:
        await audit_mutations(request, response)
    except Exception as e:
        logger.warning("audit.failed", error=str(e))
    
    return response

