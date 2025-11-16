"""Evaluation contracts (Pydantic v2)."""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class EvalRunRequest(BaseModel):
    task_id: str
    suite: str = Field(..., description="Name of the golden test suite to run")
    params: dict = Field(default_factory=dict)


class Metric(BaseModel):
    name: str
    value: float
    threshold: float | None = None


class EvalRunResponse(BaseModel):
    task_id: str
    metrics: List[Metric]
    artifacts: List[str] = Field(default_factory=list)
    failed: bool = False


def schemas() -> Dict[str, dict]:
    return {
        "EvalRunRequest": EvalRunRequest.model_json_schema(),
        "EvalRunResponse": EvalRunResponse.model_json_schema(),
    }


