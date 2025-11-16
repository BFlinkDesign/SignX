"""DFMA evaluation contracts (Pydantic v2)."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DFMAEvaluateRequest(BaseModel):
    task_id: str
    description: str = Field(..., description="Part/process description")
    process: str = Field(
        ..., description="Process type, e.g., 'sheet_metal' | 'machining' | '3dp'"
    )
    params: dict = Field(default_factory=dict, description="Process-specific params")


class CostBreakdown(BaseModel):
    material_cost: float
    process_cost: float
    setup_cost: float
    penalty_cost: float


class DFMAEvaluateResponse(BaseModel):
    task_id: str
    violations: List[str]
    suggestions: List[str]
    estimated_unit_cost: float
    breakdown: CostBreakdown
    confidence: float = Field(..., ge=0.0, le=1.0)


def schemas() -> Dict[str, dict]:
    return {
        "DFMAEvaluateRequest": DFMAEvaluateRequest.model_json_schema(),
        "DFMAEvaluateResponse": DFMAEvaluateResponse.model_json_schema(),
    }


