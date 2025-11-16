from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Dict, List, Optional
import json

from pydantic import BaseModel, Field, confloat


SCHEMA_VERSION = "1.0.0"


class Weights(BaseModel):
    yield_strength: confloat(ge=0) = 0.0
    density: confloat(ge=0) = 0.0
    cost: confloat(ge=0) = 0.0
    corrosion: confloat(ge=0) = 0.0
    fatigue: confloat(ge=0) = 0.0


class Units(BaseModel):
    stress: str = "MPa"
    density: str = "g/cm^3"
    cost: str = "USD/kg"


class Constraints(BaseModel):
    min_yield_strength: Optional[float] = None
    max_density: Optional[float] = None
    max_cost: Optional[float] = None
    environment: Optional[str] = None  # e.g., "outdoor-marine"


class Contribution(BaseModel):
    name: str              # e.g., "yield_strength"
    normalized: float      # 0..100
    weight: float          # 0..1
    contribution: float    # normalized * weight
    note: Optional[str] = None


class Provenance(BaseModel):
    source: str            # "ASM Handbook Vol.1", "MatWeb"
    note: Optional[str] = None
    version: Optional[str] = None


class CandidateMaterial(BaseModel):
    id: str
    name: str
    properties: Dict[str, float] = Field(default_factory=dict)
    qualities: Dict[str, str] = Field(default_factory=dict)
    provenance: List[Provenance] = Field(default_factory=list)


class RankedMaterial(BaseModel):
    id: str
    name: str              # "Aluminum 6061-T6"
    score: float           # 0..100
    contributions: List[Contribution]
    constraints_satisfied: bool
    caveats: List[str] = []
    provenance: List[Provenance] = []


class Trace(BaseModel):
    request_hash: str
    code_version: str
    model_config: Dict[str, str]
    timestamp_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat()+"Z")


class MaterialPickRequest(BaseModel):
    schema_version: str = SCHEMA_VERSION
    units: Units = Units()
    weights: Weights
    constraints: Constraints
    materials: List[CandidateMaterial]
    must_have: Dict[str, str] = {}
    nice_to_have: Dict[str, str] = {}

    def trace_hash(self) -> str:
        return sha256(json.dumps(self.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()


class MaterialPickResponse(BaseModel):
    schema_version: str = SCHEMA_VERSION
    result: Dict[str, List[RankedMaterial]]
    assumptions: List[str] = []
    confidence: float = 0.0
    abstain: bool = False
    trace: Trace


def export_json_schema() -> Dict[str, object]:
    """Return JSON Schema for request/response models."""
    return {
        "MaterialPickRequest": MaterialPickRequest.model_json_schema(),
        "MaterialPickResponse": MaterialPickResponse.model_json_schema(),
        "RankedMaterial": RankedMaterial.model_json_schema(),
    }


