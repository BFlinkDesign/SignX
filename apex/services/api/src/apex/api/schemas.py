from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field
from pydantic import ConfigDict


class ModelConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = "apex"
    model: str = "dev"
    temperature: float = Field(0.0, ge=0.0, le=1.0)
    max_tokens: int = 1024
    seed: Optional[int] = None


class CodeVersionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    git_sha: str = "dev"
    dirty: bool = False
    build_id: Optional[str] = None


class TraceDataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inputs: dict[str, Any]
    intermediates: dict[str, Any]
    outputs: dict[str, Any]


class TraceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data: TraceDataModel
    code_version: CodeVersionModel
    model_config: ModelConfigModel


class ResponseEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result: Optional[Any] = None
    assumptions: list[str] = Field(default_factory=list)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    trace: TraceModel


