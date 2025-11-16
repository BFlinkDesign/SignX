from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, constr


SchemaVersion = constr(pattern=r"^req-1\.0$|^resp-1\.0$")


class AskRequest(BaseModel):
    schema_version: SchemaVersion = "req-1.0"
    question: constr(min_length=3)
    intent: Optional[str] = Field(
        default=None,
        description="Optional hint: status|endpoints|contracts|services|agents|queue|events|files|todo",
    )


class Ref(BaseModel):
    path: str
    summary: str
    lines: Optional[str] = None


class AskAnswer(BaseModel):
    answer: str
    refs: List[Ref] = []
    confidence: float


class Trace(BaseModel):
    data_sha256: str
    inputs_hash: str
    trace_id: str
    span_id: str
    monotonic_ms: float
    code_version: Dict[str, str]
    model_config: Dict[str, str]


class AskResponse(BaseModel):
    schema_version: SchemaVersion = "resp-1.0"
    result: AskAnswer
    assumptions: List[str] = []
    confidence: float
    trace: Trace


