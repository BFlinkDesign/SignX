"""Materials selection contracts (Pydantic v2).

Defines MaterialPickRequest and MaterialPickResponse used by AGENT_MATERIALS.
Includes a helper to export JSON Schemas for artifact publishing.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class WeightVector(BaseModel):
    """Weights for scoring properties. Must sum to 1.0 in the agent.

    Values are floats in [0, 1]. The agent will normalize if slightly off due to
    rounding; the orchestrator does not compute domain logic.
    """

    cost: float = Field(0.0, description="Weight for cost (lower is better)")
    strength: float = Field(0.0, description="Weight for strength/yield")
    corrosion: float = Field(0.0, description="Weight for corrosion resistance")


class MaterialPickRequest(BaseModel):
    """Request to select materials based on weighted criteria."""

    task_id: str = Field(..., description="Unique task identifier")
    application: str = Field(..., description="Short description of the part/use")
    key_requirements: List[str] = Field(
        default_factory=list, description="List of qualitative requirements"
    )
    min_yield_mpa: Optional[float] = Field(
        default=None, description="Minimum required yield strength in MPa"
    )
    weights: WeightVector = Field(..., description="Weights for scoring")


class Recommendation(BaseModel):
    material: str
    score: float = Field(..., ge=0.0, le=100.0)
    reason: str
    constraints_satisfied: List[str] = Field(default_factory=list)


class Contribution(BaseModel):
    property: str
    weight: float
    normalized_value: float = Field(..., ge=0.0, le=100.0)
    contribution: float = Field(..., description="weight * normalized_value")


class MaterialPickResponse(BaseModel):
    """Response containing ranked recommendations and explanations."""

    task_id: str
    top_recommendations: List[Recommendation]
    contributions: List[Contribution]
    confidence: float = Field(..., ge=0.0, le=1.0)
    caveats: List[str] = Field(default_factory=list)
    provenance: List[str] = Field(
        default_factory=list, description="Data sources or references"
    )


def schemas() -> Dict[str, dict]:
    """Return JSON Schemas for public models."""
    return {
        "MaterialPickRequest": MaterialPickRequest.model_json_schema(),
        "MaterialPickResponse": MaterialPickResponse.model_json_schema(),
    }


