"""Sign manufacturing contracts (NAICS 339950) for APEX.

Defines SignRequest and SignResponse used by signs-service and agent_signs.
Models include explicit inclusions/exclusions context and code family hooks.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field


class Dimensions(BaseModel):
    w_mm: float = Field(..., ge=0.0)
    h_mm: float = Field(..., ge=0.0)
    d_mm: float = Field(..., ge=0.0)


class ElectricalInput(BaseModel):
    primary_voltage: float = Field(..., description="Line voltage in VAC")
    phase: Literal["single", "three"]
    available_circuit_A: float = Field(..., ge=0.0)


class Jurisdiction(BaseModel):
    country: str
    state: Optional[str] = None
    county: Optional[str] = None
    city: Optional[str] = None


class MountingParams(BaseModel):
    type: Literal["wall", "raceway", "suspended", "monument_base", "pole/pylon"]
    params: Dict[str, Any] = Field(default_factory=dict)


class SignRequest(BaseModel):
    naics_code: Literal["339950"]
    use_case: Literal[
        "storefront",
        "monument",
        "pylon",
        "channel_letters",
        "cabinet",
        "menu_board",
        "wayfinding",
        "traffic",
    ]
    illumination: Literal["none", "external", "internal-LED", "neon"]
    electrical: ElectricalInput
    environment: Literal["indoor", "outdoor", "coastal", "high-wind", "cold-soak", "high-temp"]
    dimensions: Dimensions
    mounting: MountingParams
    jurisdiction: Jurisdiction
    labels_required: bool = True
    traffic_control_context: bool = False
    provenance: Dict[str, Any] | None = None


class ComplianceFinding(BaseModel):
    source: str
    section: Optional[str] = None
    requirement: str
    satisfied: bool
    notes: Optional[str] = None


class RiskItem(BaseModel):
    id: str
    severity: Literal["low", "medium", "high", "critical"]
    mitigation: str


class ElectricalSpec(BaseModel):
    disconnect: str
    max_input_current_A: float
    branch_circuit_A: float
    listing_category: Optional[str] = None
    required_field_labels: List[str] = Field(default_factory=list)


class MechanicalSpec(BaseModel):
    mounting_pattern: str
    min_fastener_grade: str
    sealants: List[str] = Field(default_factory=list)
    gasket_material: Optional[str] = None


class GraphicsSpec(BaseModel):
    legend: Optional[str] = None
    letter_height_mm: Optional[float] = None
    contrast: Optional[str] = None
    format_standard: Optional[str] = None


class Spec(BaseModel):
    materials: List[str]
    finishes: List[str]
    ip_rating_target: Optional[str] = None
    enclosure_class: Optional[str] = None


class BomItem(BaseModel):
    type: str
    description: str
    quantity: float = 1.0
    unit: str = "ea"
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    ul_category: Optional[str] = None
    ul_file: Optional[str] = None


class SignResponse(BaseModel):
    spec: Spec
    electrical_spec: ElectricalSpec
    mechanical_spec: MechanicalSpec
    graphics_spec: GraphicsSpec
    bom: List[BomItem]
    cad_macro: str
    install_notes: List[str]
    compliance: List[ComplianceFinding]
    risks: List[RiskItem]


def schemas() -> Dict[str, dict]:
    return {
        "SignRequest": SignRequest.model_json_schema(),
        "SignResponse": SignResponse.model_json_schema(),
    }



