from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel

from ..schemas import ResponseEnvelope, TraceModel


def round_floats(value: Any, precision: int = 2) -> Any:
    """Recursively round float values for deterministic output."""
    if isinstance(value, float):
        return round(value, precision)
    if isinstance(value, dict):
        return {k: round_floats(v, precision) for k, v in value.items()}
    if isinstance(value, list):
        return [round_floats(item, precision) for item in value]
    return value


def compute_content_sha256(envelope: ResponseEnvelope) -> str:
    """Compute SHA256 of envelope result after rounding."""
    rounded = round_floats(envelope.model_dump(mode="json"))
    content = json.dumps(rounded.get("result"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode()).hexdigest()


def add_version_fields(trace: TraceModel, **versions: str) -> TraceModel:
    """Add version fields to trace for auditability."""
    if not hasattr(trace.model_config, "update"):
        return trace
    cfg = trace.model_config if isinstance(trace.model_config, dict) else {}
    cfg.update(versions)
    return TraceModel(
        data=trace.data,
        code_version=trace.code_version,
        model_config=cfg,
    )
