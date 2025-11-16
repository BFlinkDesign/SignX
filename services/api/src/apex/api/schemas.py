from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelConfigModel(BaseModel):
    provider: str = Field(..., description="LLM/tool provider identifier")
    model: str = Field(..., description="Model name")
    temperature: float = Field(..., ge=0.0, le=1.0)
    max_tokens: int = Field(..., ge=1)
    seed: Optional[int] = Field(None, ge=0)


class CodeVersionModel(BaseModel):
    git_sha: str = Field(..., description="Short git SHA")
    dirty: bool = Field(..., description="Working tree dirty state")
    build_id: Optional[str] = Field(None, description="Optional CI build id")


class TraceDataModel(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    intermediates: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    calculations: dict[str, Any] = Field(default_factory=dict, description="Intermediate calculation results")
    checks: list[dict[str, Any]] = Field(default_factory=list, description="Validation checks performed")
    artifacts: list[dict[str, Any]] = Field(default_factory=list, description="Generated artifacts (blobs, reports)")
    pack_metadata: dict[str, Any] = Field(default_factory=dict, description="Constants pack versions and SHAs")


class TraceModel(BaseModel):
    data: TraceDataModel
    code_version: CodeVersionModel
    llm_config: ModelConfigModel = Field(..., alias="model_config", description="LLM/tool provider configuration")


class ResponseEnvelope(BaseModel):
    """APEX envelope format for all API responses.
    
    Includes deterministic content SHA256, round-trip traceability,
    confidence scoring, and assumptions tracking.
    """
    result: Optional[Any] = Field(None, description="Domain result data")
    assumptions: list[str] = Field(default_factory=list, description="Assumptions and warnings")
    confidence: float = Field(0.95, ge=0.0, le=1.0, description="Confidence score [0,1]")
    trace: TraceModel = Field(..., description="Audit trace data")
    content_sha256: Optional[str] = Field(None, description="SHA256 of rounded result (deterministic)")
    envelope_version: str = Field("1.0", description="Envelope schema version")
    
    model_config = ConfigDict(
        extra="allow",
        protected_namespaces=(),
        arbitrary_types_allowed=True
    )


# Helpers for envelope standardization across services
def ensure_assumptions(items: list[str] | None) -> list[str]:
    """Deduplicate and sanitize assumptions list preserving order."""
    if not items:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        s = (it or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def compute_confidence(base: float, adjustments: dict[str, float] | None = None) -> float:
    """Blend a base confidence with adjustments, clamp to [0,1].

    Example: compute_confidence(0.6, {"coverage": 0.2, "margin": 0.1}) → 0.9
    """
    value = float(base)
    for _, delta in (adjustments or {}).items():
        value += float(delta)
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value

def compute_confidence_from_margins(margins: list[float], ideal_target: float = 2.0) -> float:
    """Compute confidence from safety factor margins.
    
    Maps minimum margin to confidence [0,1]:
    - margin >= ideal_target → confidence = 1.0
    - margin >= 1.0 → confidence = (margin - 1.0) / (ideal_target - 1.0)
    - margin < 1.0 → confidence = margin (lower bound)
    """
    if not margins:
        return 0.0
    min_margin = min(margins)
    if min_margin >= ideal_target:
        return 1.0
    if min_margin >= 1.0:
        return min(1.0, (min_margin - 1.0) / (ideal_target - 1.0))
    return max(0.0, min_margin)


def add_assumption(assumptions: list[str], msg: str) -> None:
    """Helper to append assumption with consistent formatting."""
    assumptions.append(msg)


def add_assumption_if(assumptions: list[str], condition: bool, msg: str) -> None:
    """Helper to conditionally append assumption."""
    if condition:
        add_assumption(assumptions, msg)

