"""CAD macro synthesis contracts (Pydantic v2)."""

from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, Field


Target = Literal["freecad", "solidworks"]


class CADMacroRequest(BaseModel):
    task_id: str
    target: Target
    primitives: List[str] = Field(
        ..., description="Operations in order, e.g., pad, pocket, fillet"
    )
    constraints: List[str] = Field(default_factory=list)
    dims: dict = Field(default_factory=dict, description="Dimension map with units")


class CADMacroResponse(BaseModel):
    task_id: str
    script_path: str
    features: List[str]
    params: List[str]
    preview_notes: List[str] = Field(default_factory=list)


def schemas() -> Dict[str, dict]:
    return {
        "CADMacroRequest": CADMacroRequest.model_json_schema(),
        "CADMacroResponse": CADMacroResponse.model_json_schema(),
    }


