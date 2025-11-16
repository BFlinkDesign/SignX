from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


class StandardRef(BaseModel):
    code: Literal["ASCE7", "EN1991", "AASHTO"]
    version: str
    importance: Optional[str] = None


class Site(BaseModel):
    lat: float
    lon: float
    elevation_m: float
    exposure: Literal["B", "C", "D"]
    topography: Literal["none", "hill", "escarpment"] = "none"
    soil_bearing_psf: float
    frost_depth_in: Optional[float] = None


class SignGeom(BaseModel):
    width_ft: float
    height_ft: float
    centroid_height_ft: float
    gross_weight_lbf: Optional[float] = None


class Embed(BaseModel):
    type: Literal["direct", "baseplate"]


class Constraints(BaseModel):
    max_foundation_dia_in: Optional[float] = None
    max_embed_in: Optional[float] = None


class Safety(BaseModel):
    abstain_below_confidence: float = Field(0.75, ge=0.0, le=1.0)


class SignDesignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["sign-1.0"] = "sign-1.0"
    project_id: str
    jurisdiction: Literal["US", "EU", "INTL"]
    standard: StandardRef
    site: Site
    sign: SignGeom
    support_options: List[Literal["pipe", "W", "tube"]]
    embed: Embed
    constraints: Constraints = Field(default_factory=Constraints)
    safety: Safety = Field(default_factory=Safety)


class SelectedDesign(BaseModel):
    support: Dict[str, Any]
    foundation: Dict[str, Any]
    checks: Dict[str, Any]


class ReportsRefs(BaseModel):
    calc_json_ref: Optional[str] = None
    pdf_ref: Optional[str] = None


class LoadsOut(BaseModel):
    V_basic: Optional[float] = None
    qz_psf: Optional[float] = None
    F_w_sign_lbf: Optional[float] = None


class SignDesignResult(BaseModel):
    selected: SelectedDesign
    alternates: List[Dict[str, Any]] = Field(default_factory=list)
    loads: LoadsOut = Field(default_factory=LoadsOut)
    reports: ReportsRefs = Field(default_factory=ReportsRefs)


class SignDesignResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    result: SignDesignResult
    assumptions: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    trace: Dict[str, Any]


def schemas() -> Dict[str, dict]:
    return {
        "SignDesignRequest": SignDesignRequest.model_json_schema(),
        "SignDesignResponse": SignDesignResponse.model_json_schema(),
    }


