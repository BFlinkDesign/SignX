from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Optional


# ========== Envelope Schema (Cross-Service) ==========
# ResponseEnvelope is shared across all services for consistent API responses

class ModelConfigModel(BaseModel):
    """LLM/tool provider configuration."""
    model_config = ConfigDict(extra="forbid")
    provider: str = "apex"
    model: str = "dev"
    temperature: float = Field(0.0, ge=0.0, le=1.0)
    max_tokens: int = 1024
    seed: Optional[int] = None


class CodeVersionModel(BaseModel):
    """Code version and build metadata."""
    model_config = ConfigDict(extra="forbid")
    git_sha: str = "dev"
    dirty: bool = False
    build_id: Optional[str] = None


class TraceDataModel(BaseModel):
    """Trace data with inputs, intermediates, and outputs."""
    model_config = ConfigDict(extra="forbid")
    inputs: dict[str, Any]
    intermediates: dict[str, Any]
    outputs: dict[str, Any]


class TraceModel(BaseModel):
    """Complete trace with data, code version, and model config."""
    model_config = ConfigDict(extra="forbid")
    data: TraceDataModel
    code_version: CodeVersionModel
    model_config: ModelConfigModel


class ResponseEnvelope(BaseModel):
    """Standard APEX API response envelope.
    
    All API endpoints must return this structure for auditability.
    """
    model_config = ConfigDict(extra="forbid")
    result: Optional[Any] = None
    assumptions: list[str] = Field(default_factory=list)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    trace: TraceModel


# ========== Domain Models ==========

class ProjectRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str
    name: Optional[str] = None


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address: Optional[str] = None
    zip_code: Optional[str] = None


class MaterialSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    material_type: str
    grade: Optional[str] = None
    thickness_in: Optional[float] = None
    density_lb_ft3: Optional[float] = None

