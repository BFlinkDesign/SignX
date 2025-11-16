from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


SCHEMA_VERSION = "sign-1.0"


class Standard(BaseModel):
    code: Literal["ASCE7", "EN1991"]
    version: str
    importance: Literal["I", "II", "III"]


class Site(BaseModel):
    lat: float
    lon: float
    elevation_m: float
    exposure: Literal["B", "C", "D"]
    topography: str
    soil_bearing_psf: float
    frost_depth_in: float


class SignGeom(BaseModel):
    width_ft: float
    height_ft: float
    centroid_height_ft: float
    gross_weight_lbf: float


class Constraints(BaseModel):
    max_foundation_dia_in: Optional[float] = None
    max_embed_in: Optional[float] = None


class SignDesignRequest(BaseModel):
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    jurisdiction: Literal["US", "EU"]
    standard: Standard
    site: Site
    sign: SignGeom
    support_options: List[Literal["pipe", "W", "tube"]]
    embed: dict = Field(default_factory=lambda: {"type": "direct"})
    constraints: Constraints = Field(default_factory=Constraints)
    provenance: Dict[str, Any] | None = None


class SelectedSupport(BaseModel):
    type: Literal["pipe", "W", "tube"]
    designation: str


class Foundation(BaseModel):
    shape: Literal["cyl", "rect"]
    dia_in: Optional[float] = None
    width_in: Optional[float] = None
    depth_in: float
    rebar_schedule_ref: str
    anchor_bolt_ref: Optional[str] = None


class Checks(BaseModel):
    OT_sf: float
    BRG_sf: float
    SLIDE_sf: float
    UPLIFT_sf: float
    DEF_ok: bool


class ResultSelected(BaseModel):
    support: SelectedSupport
    foundation: Foundation
    checks: Checks


class Loads(BaseModel):
    V_basic: float
    qz_psf: Optional[float] = None
    qb_pa: Optional[float] = None
    F_w_sign_lbf: float


class Reports(BaseModel):
    calc_json_ref: str
    pdf_ref: Optional[str] = None
    dxf_ref: Optional[str] = None


class SignDesignResponse(BaseModel):
    result: Dict[str, Any]
    assumptions: List[str]
    confidence: float = Field(..., ge=0.0, le=1.0)
    trace: Dict[str, Any]



