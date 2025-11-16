from __future__ import annotations

from typing import Any
from ..deps import get_code_version, get_model_config
from ..schemas import ResponseEnvelope, TraceDataModel, TraceModel

# Try to import request_id context if middleware is available
try:
    from ..middleware import REQUEST_ID_VAR
    _has_request_id = True
except (ImportError, AttributeError):
    _has_request_id = False


def build_envelope(
    *,
    result: Any,
    assumptions: list[str] | None = None,
    confidence: float = 1.0,
    inputs: dict | None = None,
    outputs: dict | None = None,
    intermediates: dict | None = None,
) -> ResponseEnvelope:
    """Build ResponseEnvelope with automatic request_id injection.
    
    This is the unified envelope builder for the apex/ codebase.
    For services/api codebase, use make_envelope from common.models.
    """
    base_inputs = dict(inputs or {})
    
    # Auto-inject request_id if middleware is active
    if _has_request_id:
        rid = REQUEST_ID_VAR.get()
        if rid and "request_id" not in base_inputs:
            base_inputs["request_id"] = rid
    
    return ResponseEnvelope(
        result=result,
        assumptions=assumptions or [],
        confidence=confidence,
        trace=TraceModel(
            data=TraceDataModel(
                inputs=base_inputs,
                intermediates=intermediates or {},
                outputs=outputs or {},
            ),
            code_version=get_code_version(),
            model_config=get_model_config(),
        ),
    )
