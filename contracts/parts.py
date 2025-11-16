"""Parts retrieval contracts (Pydantic v2)."""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class PartsQueryRequest(BaseModel):
    task_id: str
    query: str = Field(..., description="Natural language part query")
    hard_constraints: dict = Field(default_factory=dict)
    soft_constraints: dict = Field(default_factory=dict)


class PartMatch(BaseModel):
    part_id: str
    score: float = Field(..., ge=0.0, le=100.0)
    specs: dict
    dataset_path: str
    row_id: int


class PartsQueryResponse(BaseModel):
    task_id: str
    top_matches: List[PartMatch]
    normalized_spec: dict
    retrieval_provenance: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)


def schemas() -> Dict[str, dict]:
    return {
        "PartsQueryRequest": PartsQueryRequest.model_json_schema(),
        "PartsQueryResponse": PartsQueryResponse.model_json_schema(),
    }


