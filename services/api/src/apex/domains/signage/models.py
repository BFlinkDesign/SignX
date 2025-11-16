"""
APEX Signage Engineering - Domain Models (Pydantic v2)
Shared primitives for sign structure design
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


# Type Aliases
Unit = float  # JSON floats; wrap with pint.Quantity at service boundary
Exposure = Literal["B", "C", "D"]
MaterialSteel = Literal["A500B", "A53B", "A36", "A572-50"]
ModuleType = Literal[
    "signage.single_pole.direct_burial",
    "signage.single_pole.base_plate",
    "signage.two_pole.direct_burial",
]


# ========== Common Site & Cabinet Models ==========


class SiteLoads(BaseModel):
    """Wind and snow load data for a specific location."""

    wind_speed_mph: Unit
    snow_load_psf: Optional[Unit] = None
    exposure: Exposure = "C"

    model_config = ConfigDict(str_strip_whitespace=True)


class Cabinet(BaseModel):
    """Single sign cabinet dimensions and weight."""

    width_ft: Unit
    height_ft: Unit
    depth_in: Unit = 12.0
    weight_psf: Unit = 10.0


class LoadDerivation(BaseModel):
    """Derived load calculations from cabinets and site."""

    a_ft2: Unit  # Projected area
    z_cg_ft: Unit  # Centroid height
    weight_estimate_lb: Unit
    mu_kipft: Unit  # Ultimate moment


# ========== Pole Selection Models ==========


class PolePrefs(BaseModel):
    """User preferences for pole selection."""

    family: Literal["HSS", "Pipe", "W"] = "HSS"
    steel_grade: MaterialSteel = "A500B"
    sort_by: Literal["tube_size", "Sx", "weight_per_ft"] = "Sx"


class PoleOption(BaseModel):
    """A feasible pole section option."""

    shape: str
    weight_per_ft: Unit
    sx_in3: Unit
    fy_ksi: Unit


# ========== Direct Burial Foundation Models ==========


class FootingConfig(BaseModel):
    """Direct burial footing configuration."""

    shape: Literal["round", "square"] = "round"
    diameter_ft: Unit
    min_depth_ft: Optional[Unit] = None
    spread_required: bool = False
    footing_type: Optional[Literal["single", "per_support"]] = None  # multi-pole only


class FootingResult(BaseModel):
    """Footing depth calculation result."""

    min_depth_ft: Unit
    mu_used_kipft: Unit
    soil_psf: Unit


# ========== Base Plate Foundation Models ==========


class BasePlateInput(BaseModel):
    """Base plate design parameters."""

    plate_w_in: Unit
    plate_l_in: Unit
    plate_thk_in: Unit
    fy_ksi: Unit = 36.0
    weld_size_in: Unit
    anchor_dia_in: Unit
    anchor_grade_ksi: Unit
    anchor_embed_in: Unit
    rows: int
    bolts_per_row: int
    row_spacing_in: Unit
    edge_distance_in: Unit


class CheckResult(BaseModel):
    """Individual engineering check result."""

    name: str
    demand: Unit
    capacity: Unit
    unit: str
    pass_: bool = Field(alias="pass")  # noqa: A003
    governing: Optional[str] = None
    
    model_config = ConfigDict(populate_by_name=True)


class BasePlateChecks(BaseModel):
    """Complete base plate check set."""

    all_pass: bool
    checks: List[CheckResult]


class BasePlateSolution(BaseModel):
    """Auto-solved base plate design."""

    input: BasePlateInput
    checks: BasePlateChecks
    cost_proxy: Unit
    governing_constraints: List[str]


# ========== Multi-Pole Support Models ==========


class SupportConfig(BaseModel):
    """Support structure configuration."""

    foundation_type: Literal["direct_burial", "base_plate"]
    num_supports: int = 1
    pole_material: Literal["steel", "aluminum"] = "steel"


# ========== Full Project Configuration Models ==========


class SignageConfig(BaseModel):
    """Complete signage project configuration."""

    module: ModuleType
    site: SiteLoads
    overall_height_ft: Unit
    cabinets: List[Cabinet]
    supports: SupportConfig
    pole_prefs: PolePrefs
    pole_size: Optional[str] = None  # From filtered options
    footing: Optional[FootingConfig] = None
    baseplate: Optional[BasePlateInput] = None

    model_config = ConfigDict(extra="forbid")


