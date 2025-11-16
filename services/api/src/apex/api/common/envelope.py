"""Enhanced envelope utilities for deterministic, auditable responses."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import orjson
import structlog

# ResponseEnvelope imported locally in functions to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..schemas import ResponseEnvelope

logger = structlog.get_logger(__name__)


def round_floats(obj: Any, precision: int = 3) -> Any:
    """Recursively round float values for deterministic output.
    
    Args:
        obj: Value to round (float, dict, list, or any)
        precision: Decimal places (default 3 for engineering precision)
    
    Returns:
        Value with floats rounded to specified precision
    """
    if isinstance(obj, float):
        return round(obj, precision)
    if isinstance(obj, dict):
        return {k: round_floats(v, precision) for k, v in obj.items()}
    if isinstance(obj, list):
        return [round_floats(item, precision) for item in obj]
    return obj


def envelope_sha(envelope: Any) -> str:
    """Compute SHA256 of envelope for content-addressed storage.
    
    Args:
        envelope: ResponseEnvelope or dict representation
    
    Returns:
        SHA256 hex digest
    """
    from ..schemas import ResponseEnvelope
    # Convert to dict if needed
    if isinstance(envelope, ResponseEnvelope):
        payload = envelope.model_dump(mode="json")
    else:
        payload = envelope
    
    # Round floats for determinism
    rounded = round_floats(payload, precision=3)
    
    # Sort keys and serialize deterministically
    content = orjson.dumps(
        rounded.get("result"),
        option=orjson.OPT_SORT_KEYS,
    ).decode("utf-8")
    
    # Compute hash
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def calc_confidence(assumptions: list[str] | None) -> float:
    """Calculate confidence score based on assumptions (warnings/failures).
    
    Penalizes for:
    - "warning" keywords: -0.1 each
    - "fail" or "failed" keywords: -0.3 each
    - "abstain" or "cannot solve": -0.5
    - "request engineering": -0.3
    - "no feasible": -0.4
    
    Args:
        assumptions: List of assumption strings
    
    Returns:
        Confidence score [0.0, 1.0]
    """
    if not assumptions:
        return 1.0
    
    confidence = 1.0
    assumptions_lower = [a.lower() for a in assumptions]
    
    # Count penalties
    for assumption in assumptions_lower:
        if "abstain" in assumption or "cannot solve" in assumption:
            confidence -= 0.5
        elif "no feasible" in assumption:
            confidence -= 0.4
        elif any(keyword in assumption for keyword in ["fail", "failed"]):
            confidence -= 0.3
        elif "request engineering" in assumption:
            confidence -= 0.3
        elif "warning" in assumption:
            confidence -= 0.1
    
    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, confidence))


def deterministic_sort(items: list[dict[str, Any]], sort_key: str = "id", seed: str | None = None) -> list[dict[str, Any]]:
    """Sort list deterministically with optional seed.
    
    Args:
        items: List of dicts to sort
        sort_key: Key to use for sorting
        seed: Optional seed for stable ordering
    
    Returns:
        Sorted list
    """
    if not items:
        return items
    
    # Sort by primary key first
    sorted_items = sorted(items, key=lambda x: x.get(sort_key, ""))
    
    # If seed provided, apply stable shuffle
    if seed:
        import random
        random.seed(hash(seed))
        # Don't actually shuffle - seed just ensures stable "randomness" for tie-breaking
        # In practice, we keep deterministic sort for reproducibility
    
    return sorted_items


def extract_solver_warnings(result: Any, warnings_key: str = "warnings") -> list[str]:
    """Extract warnings from solver results (Agent 4 tuple pattern).
    
    Args:
        result: Solver result (may be tuple or dict)
        warnings_key: Key name for warnings in dict results
    
    Returns:
        List of warning strings
    """
    warnings: list[str] = []
    
    # Handle tuple results (result, warnings, flags) from Agent 4
    if isinstance(result, tuple):
        if len(result) >= 2:
            warnings = result[1]
        if len(result) >= 3:
            flags = result[2]
            # Convert flags to warnings if needed
            if isinstance(flags, dict):
                for key, value in flags.items():
                    if not value:  # False flag means problem
                        warnings.append(f"{key} check failed")
    
    # Handle dict results
    elif isinstance(result, dict):
        if warnings_key in result:
            warnings = result[warnings_key]
        # Check for common flag patterns
        if "request_engineering" in result and result["request_engineering"]:
            warnings.append("Engineering review required")
        if "all_pass" in result and not result["all_pass"]:
            warnings.append("Some checks failed")
    
    # Ensure list format
    if not isinstance(warnings, list):
        warnings = [str(warnings)] if warnings else []
    
    return warnings

