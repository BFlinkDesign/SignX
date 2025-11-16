"""Stackup analysis contracts (Pydantic v2).

Defines StackupAnalyzeRequest and StackupAnalyzeResponse for AGENT_STACKUP.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


Distribution = Literal["normal", "uniform"]


class Feature(BaseModel):
    name: str
    nominal: float
    tol_plus: float = Field(..., ge=0.0)
    tol_minus: float = Field(..., ge=0.0)
    distribution: Distribution = "normal"
    correlation_group: Optional[str] = Field(
        default=None, description="Group name for correlated features"
    )


class HistogramBucket(BaseModel):
    bin_center: float
    count: int


class StackupAnalyzeRequest(BaseModel):
    task_id: str
    description: str
    features: List[Feature]
    sample_size: int = Field(10000, ge=1, le=50000)
    lower_spec: Optional[float] = None
    upper_spec: Optional[float] = None


class StackupAnalyzeResponse(BaseModel):
    task_id: str
    mean: float
    sigma: float
    cpk: Optional[float] = None
    ppk: Optional[float] = None
    pass_prob: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    histogram: List[HistogramBucket]
    assumptions: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)


def schemas() -> Dict[str, dict]:
    return {
        "StackupAnalyzeRequest": StackupAnalyzeRequest.model_json_schema(),
        "StackupAnalyzeResponse": StackupAnalyzeResponse.model_json_schema(),
    }


