"""Custom exception handlers with Sentry integration."""

from __future__ import annotations

import uuid

import structlog
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from pydantic import ValidationError

from .common.models import make_envelope
from .common.envelope import calc_confidence
from .deps import get_code_version, get_model_config, settings

logger = structlog.get_logger(__name__)


# Try to import Sentry, but don't fail if not available
try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    sentry_sdk = None  # type: ignore


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> ORJSONResponse:
    """Handle Pydantic validation errors with field paths.
    
    Returns envelope with detailed error information.
    """
    trace_id = getattr(request.state, "trace_id", "unknown")
    error_id = str(uuid.uuid4())
    
    # Extract field paths from errors
    errors = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
        })
    
    logger.warning(
        "validation_error",
        error_id=error_id,
        trace_id=trace_id,
        path=request.url.path,
        errors=errors,
    )
    
    # Send to Sentry if available
    if SENTRY_AVAILABLE and settings.ENV == "prod":
        sentry_sdk.capture_exception(exc)
    
    assumptions = [f"Validation failed: {len(errors)} error(s)"]
    envelope = make_envelope(
        result=None,
        assumptions=assumptions,
        confidence=calc_confidence(assumptions),
        inputs={"path": request.url.path, "method": request.method},
        intermediates={"errors": errors, "error_id": error_id},
        outputs={},
    )
    
    # Add errors array to response for better UX
    envelope_dict = envelope.model_dump(mode="json")
    envelope_dict["errors"] = errors
    
    return ORJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=envelope_dict,
        headers={"X-Error-ID": error_id, "X-Trace-ID": trace_id},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> ORJSONResponse:
    """Handle unexpected exceptions with Sentry integration."""
    trace_id = getattr(request.state, "trace_id", "unknown")
    error_id = str(uuid.uuid4())
    
    logger.exception(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        error_id=error_id,
        trace_id=trace_id,
        path=request.url.path,
        method=request.method,
    )
    
    # Send to Sentry if available
    if SENTRY_AVAILABLE and settings.ENV == "prod":
        sentry_sdk.capture_exception(exc)
    
    envelope = make_envelope(
        result={
            "error_id": error_id,
            "error_type": type(exc).__name__,
            "message": "An unexpected error occurred. The service abstains.",
        },
        assumptions=["An unexpected error occurred. The service abstains."],
        confidence=0.1,
        inputs={"path": request.url.path, "method": request.method},
        intermediates={"error": type(exc).__name__, "error_id": error_id, "trace_id": trace_id},
        outputs={},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )
    
    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=envelope.model_dump(mode="json"),
        headers={"X-Error-ID": error_id, "X-Trace-ID": trace_id},
    )

