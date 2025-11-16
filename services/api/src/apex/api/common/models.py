"""Shared primitives for CalcuSign-style workflows in APEX.

Common types used across project management, signage, and calculation services.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# Type imported locally in make_envelope to avoid circular imports


# Unit type alias for clarity (floats at API boundary; pint for internal conversions later)
Unit = float

# Exposure categories per ASCE 7
Exposure = Literal["B", "C", "D"]

# Material specifications
MaterialSteel = Literal["A500B", "A53B", "A36", "A572-50"]


class SiteLoads(BaseModel):
    """Wind and snow loads resolved for a site."""

    wind_speed_mph: Unit = Field(..., description="Basic wind speed in mph")
    snow_load_psf: Optional[Unit] = Field(None, description="Ground snow load psf")
    exposure: Exposure = Field("C", description="Wind exposure category")


class Cabinet(BaseModel):
    """Cabinet/sign face geometry and weight properties."""

    width_ft: Unit = Field(..., ge=0.0, description="Width in feet")
    height_ft: Unit = Field(..., ge=0.0, description="Height in feet")
    depth_in: Unit = Field(12.0, ge=0.0, description="Depth in inches")
    weight_psf: Unit = Field(10.0, ge=0.0, description="Weight in pounds per square foot")


# Helper functions
def compute_confidence(base: float, penalties: list[float] | None = None) -> float:
    """Compute confidence from base with optional penalties."""
    confidence = max(0.0, min(1.0, base))
    if penalties:
        for p in penalties:
            confidence -= abs(p)
            if confidence <= 0.0:
                return 0.0
    return max(0.0, min(1.0, confidence))


def add_assumption(assumptions: list[str], note: str) -> list[str]:
    """Add an assumption to the list."""
    updated = list(assumptions)
    updated.append(note)
    return updated


def make_envelope(
    *,
    result: Any | None,
    assumptions: list[str] | None = None,
    confidence: float = 1.0,
    inputs: dict[str, Any] | None = None,
    intermediates: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    calculations: dict[str, Any] | None = None,
    checks: list[dict[str, Any]] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    code_version: Any | None = None,
    model_config: Any | None = None,
) -> Any:
    """Build a ResponseEnvelope with trace data.
    
    Unified envelope builder that:
    - Auto-injects request_id from context if available
    - Auto-fetches code_version and model_config if not provided
    - Provides sensible defaults for all optional fields
    - Applies deterministic rounding to result
    - Computes content_sha256 for auditability
    """
    from ..schemas import ResponseEnvelope as Envelope, TraceDataModel, TraceModel
    from ..deps import get_code_version, get_model_config
    from .envelope import round_floats
    
    # Try to get request_id from context (if middleware is active)
    try:
        from ..middleware import REQUEST_ID_VAR
        rid = REQUEST_ID_VAR.get()
        base_inputs = dict(inputs or {})
        if rid and "request_id" not in base_inputs:
            base_inputs["request_id"] = rid
        inputs = base_inputs
    except (ImportError, AttributeError):
        inputs = {}
    
    # Auto-fetch code_version and model_config if not provided
    if code_version is None:
        code_version = get_code_version()
    if model_config is None:
        model_config = get_model_config()
    
    # Load constants pack metadata
    try:
        from .constants import get_pack_metadata
        pack_metadata = get_pack_metadata()
    except Exception:
        pack_metadata = {}
    
    # Apply deterministic rounding to result
    rounded_result = round_floats(result, precision=3) if result is not None else None

    trace = TraceModel(
        data=TraceDataModel(
            inputs=inputs,
            intermediates=intermediates or {},
            outputs=outputs or {},
            calculations=calculations or {},
            checks=checks or [],
            artifacts=artifacts or [],
            pack_metadata=pack_metadata,
        ),
        code_version=code_version,
        model_config=model_config,
    )
    
    envelope = Envelope(
        result=rounded_result,
        assumptions=assumptions or [],
        confidence=confidence,
        trace=trace,
        content_sha256=None,  # Will be computed after creation
    )
    
    # Compute content SHA256 for deterministic auditability
    if rounded_result is not None:
        from .envelope import envelope_sha
        envelope.content_sha256 = envelope_sha(envelope)
    
    return envelope


def build_response_envelope(
    *,
    result: Any | None,
    assumptions: list[str] | None = None,
    confidence: float = 1.0,
    trace_inputs: dict[str, Any] | None = None,
    trace_intermediates: dict[str, Any] | None = None,
    trace_outputs: dict[str, Any] | None = None,
    trace_calculations: dict[str, Any] | None = None,
    trace_checks: list[dict[str, Any]] | None = None,
    trace_artifacts: list[dict[str, Any]] | None = None,
    code_version: Any | None = None,
    model_config: Any | None = None,
) -> Any:
    """Shorthand for building envelopes from route handlers.

    FastAPI routes frequently need to construct envelopes with trace data. This
    helper keeps the call-sites terse and ensures we consistently defer to
    :func:`make_envelope` for deterministic rounding, hashing, and metadata
    population.

    Args:
        result: Primary payload returned to the client
        assumptions: Collection of assumptions injected into the response envelope
        confidence: Confidence score in ``[0, 1]``
        trace_inputs: Inputs captured for traceability
        trace_intermediates: Intermediate values captured during processing
        trace_outputs: Summary outputs captured for traceability
        trace_calculations: Detailed calculation artifacts (optional)
        trace_checks: Limit-state or compliance checks performed (optional)
        trace_artifacts: External artifact references (e.g., MinIO keys)
        code_version: Optional explicit code version override
        model_config: Optional explicit model configuration override
    """

    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=confidence,
        inputs=trace_inputs,
        intermediates=trace_intermediates,
        outputs=trace_outputs,
        calculations=trace_calculations,
        checks=trace_checks,
        artifacts=trace_artifacts,
        code_version=code_version,
        model_config=model_config,
    )