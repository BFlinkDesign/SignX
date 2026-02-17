"""
models.py — Pydantic input validation models for SignX estimation pipeline.

Provides validated request models for all four estimators:
  - MonumentEstimateRequest   (MONDF/MONSF, SF-based)
  - AwningEstimateRequest     (AWNNON, linear-foot + SF geometry)
  - RemovalEstimateRequest    (standalone removal crew work)
  - ChannelLetterEstimateRequest (CLLIT/CLNON, PF-based ABC engine)

All models enforce:
  - Unit consistency  (dimensions must be in the same unit system)
  - Range checks on price factors, heights, and areas
  - Enum coercion for sign type, construction type, font type
  - Sensible defaults matching abc_engine.py JobInput defaults
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Re-export enums from abc_engine for convenience ──────────────────────────
# Consumers can import directly from models.py instead of abc_engine.py

from abc_engine import (
    CabinetFace,
    CabinetFrame,
    CabinetShape,
    ConstructionType,
    FontType,
    SignType,
)


# ── Unit system ───────────────────────────────────────────────────────────────

class DimensionUnit(str, Enum):
    """Measurement unit for all dimension inputs."""
    INCHES = "inches"
    FEET = "feet"
    MM = "mm"


def _to_inches(value: float, unit: DimensionUnit) -> float:
    """Convert a dimension value to inches regardless of input unit."""
    if unit == DimensionUnit.FEET:
        return value * 12.0
    if unit == DimensionUnit.MM:
        return value / 25.4
    return value  # already inches


# ── Channel Letter Estimate Request ──────────────────────────────────────────

class ChannelLetterEstimateRequest(BaseModel):
    """
    Input model for channel letter estimates (CLLIT/CLNON).
    Drives the abc_engine.estimate() function.

    Dimension unit: ALL height/depth fields must use the same unit system.
    Use `dimension_unit` to specify inches (default), feet, or mm.
    PF values are ALWAYS in feet regardless of dimension_unit.
    """

    # Sign classification
    sign_type: SignType = Field(
        default=SignType.CLLIT,
        description="Eagle sign type code",
    )
    construction: ConstructionType = Field(
        default=ConstructionType.FACE_LIT,
        description="Channel letter construction method",
    )

    # Dimension unit (applies to letter heights and return depth only)
    dimension_unit: DimensionUnit = Field(
        default=DimensionUnit.INCHES,
        description="Unit system for all height/depth dimensions (NOT for PF values)",
    )

    # Letter specification — either PF direct OR letter_count + height
    pf_manual: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=5000.0,
        description="Pre-calculated peripheral feet (from PDF or measurement). "
                    "If provided, overrides letter_count + height calculation. "
                    "Always in feet.",
    )
    letter_count: int = Field(
        default=0,
        ge=0,
        le=500,
        description="Number of letters/characters in the sign set",
    )
    letter_height: float = Field(
        default=12.0,
        ge=0.0,
        le=240.0,
        description="Character height in the unit specified by dimension_unit",
    )
    font_type: FontType = Field(
        default=FontType.BLOCK,
        description="Font classification affecting PF per letter from footage chart",
    )
    return_depth: float = Field(
        default=5.0,
        ge=0.0,
        le=36.0,
        description="Channel return depth in the unit specified by dimension_unit",
    )

    # Cabinet (optional — Section 2 work)
    cabinet_sf: float = Field(
        default=0.0,
        ge=0.0,
        le=10000.0,
        description="Cabinet face area in square feet (Section 2 sheet metal work)",
    )
    cabinet_face: CabinetFace = Field(default=CabinetFace.SINGLE)
    cabinet_shape: CabinetShape = Field(default=CabinetShape.RECTANGULAR)
    cabinet_frame: CabinetFrame = Field(default=CabinetFrame.LIGHT)

    # Paint (optional — Section 5A work)
    paint_sf: float = Field(
        default=0.0,
        ge=0.0,
        le=10000.0,
        description="Surface area to be painted in square feet",
    )
    paint_colors: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Number of paint colors (1–5, drives Section 5A rates)",
    )

    # Installation
    install_height_ft: float = Field(
        default=15.0,
        ge=0.0,
        le=200.0,
        description="Installation height above ground in feet (always feet, not dimension_unit)",
    )
    install_mount_type: Literal["wall", "raceway", "deck", "pipe"] = Field(
        default="wall",
        description="Mounting substrate type",
    )
    is_first_sign: bool = Field(
        default=True,
        description="True if this is the first sign of the day (affects Section 10A constant)",
    )
    substrate: Literal["standard", "eifs_unknown", "old_masonry", "steel"] = Field(
        default="standard",
        description="Wall substrate type (affects install multiplier)",
    )

    # Travel / crew
    miles_one_way: float = Field(
        default=0.0,
        ge=0.0,
        le=1000.0,
        description="One-way travel distance in miles",
    )
    crew_size: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Number of crew members for installation",
    )
    num_units: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Number of sign units in the set",
    )

    @field_validator("letter_height")
    @classmethod
    def letter_height_positive_when_count_set(cls, v: float) -> float:
        # Zero height is only valid when pf_manual is used instead
        return v

    @model_validator(mode="after")
    def require_pf_source(self) -> "ChannelLetterEstimateRequest":
        """Either pf_manual OR letter_count > 0 is required to produce a valid PF."""
        has_pf = self.pf_manual is not None and self.pf_manual > 0
        has_chart = self.letter_count > 0
        if not has_pf and not has_chart:
            raise ValueError(
                "Provide either pf_manual > 0 or letter_count > 0 to calculate peripheral feet. "
                "A job with zero PF will produce a floor-only estimate."
            )
        return self

    @model_validator(mode="after")
    def validate_dimension_unit_consistency(self) -> "ChannelLetterEstimateRequest":
        """
        Warn (via conversion) if letter_height looks like it was supplied in the
        wrong unit. Specifically: reject obviously mis-sized values.
        - If unit=INCHES: height > 200 is likely a mm value supplied by mistake
        - If unit=MM: height < 50 is likely an inch value supplied by mistake
        - If unit=FEET: height > 20 ft (240") is above our max, already caught by ge/le
        """
        h = self.letter_height
        if self.dimension_unit == DimensionUnit.INCHES and h > 200:
            raise ValueError(
                f"letter_height={h} with unit=inches looks like a mm value. "
                "Either convert to inches or set dimension_unit='mm'."
            )
        if self.dimension_unit == DimensionUnit.MM and h < 50:
            raise ValueError(
                f"letter_height={h} with unit=mm looks like an inch value. "
                "Either convert to mm (multiply by 25.4) or set dimension_unit='inches'."
            )
        if self.dimension_unit == DimensionUnit.FEET and h > 20:
            raise ValueError(
                f"letter_height={h} with unit=feet exceeds 20 ft — likely a unit error. "
                "Use dimension_unit='inches' for heights in inches."
            )
        return self

    def to_job_input(self):
        """Convert to abc_engine.JobInput, normalizing all dimensions to inches."""
        from abc_engine import JobInput

        height_in = _to_inches(self.letter_height, self.dimension_unit)
        depth_in = _to_inches(self.return_depth, self.dimension_unit)

        return JobInput(
            sign_type=self.sign_type,
            construction=self.construction,
            pf_manual=self.pf_manual,
            letter_count=self.letter_count,
            letter_height_inches=height_in,
            font_type=self.font_type,
            return_depth_inches=depth_in,
            cabinet_sf=self.cabinet_sf,
            cabinet_face=self.cabinet_face,
            cabinet_shape=self.cabinet_shape,
            cabinet_frame=self.cabinet_frame,
            paint_sf=self.paint_sf,
            paint_colors=self.paint_colors,
            install_height_ft=self.install_height_ft,
            install_mount_type=self.install_mount_type,
            is_first_sign=self.is_first_sign,
            miles_one_way=self.miles_one_way,
            crew_size=self.crew_size,
            num_units=self.num_units,
        )


# ── Monument Estimate Request ─────────────────────────────────────────────────

class MonumentEstimateRequest(BaseModel):
    """
    Input model for monument sign estimates (MONDF/MONSF).
    Drives abc_engine.estimate_monument().

    Area-based estimate. Width and height must be in the same unit.
    Use dimension_unit to specify inches, feet (default), or mm.
    """

    sign_type: SignType = Field(
        default=SignType.MONDF,
        description="Monument type: MONDF (double-face) or MONSF (single-face)",
    )
    dimension_unit: DimensionUnit = Field(
        default=DimensionUnit.FEET,
        description="Unit system for width and height dimensions",
    )

    # Sign face dimensions
    width: float = Field(
        ge=0.0,
        le=200.0,
        description="Monument sign face width in the specified dimension_unit",
    )
    height: float = Field(
        ge=0.0,
        le=50.0,
        description="Monument sign face height in the specified dimension_unit",
    )

    # Optional override when area is pre-calculated
    face_area_sf: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2000.0,
        description="Pre-calculated face area in square feet. "
                    "If provided, overrides width * height calculation.",
    )

    # Illumination
    illuminated: bool = Field(
        default=False,
        description="True if the monument has internal or external illumination",
    )

    # Install
    install_height_ft: float = Field(
        default=6.0,
        ge=0.0,
        le=50.0,
        description="Height of the top of the monument in feet",
    )
    miles_one_way: float = Field(
        default=0.0,
        ge=0.0,
        le=1000.0,
    )
    crew_size: int = Field(default=2, ge=1, le=10)

    @field_validator("sign_type")
    @classmethod
    def must_be_monument_type(cls, v: SignType) -> SignType:
        if v not in (SignType.MONDF, SignType.MONSF):
            raise ValueError(
                f"MonumentEstimateRequest requires sign_type MONDF or MONSF, got {v.value}"
            )
        return v

    @model_validator(mode="after")
    def require_dimensions_or_area(self) -> "MonumentEstimateRequest":
        has_area = self.face_area_sf is not None and self.face_area_sf > 0
        has_dims = self.width > 0 and self.height > 0
        if not has_area and not has_dims:
            raise ValueError(
                "Provide either face_area_sf > 0 or both width > 0 and height > 0"
            )
        return self

    @model_validator(mode="after")
    def validate_dimension_unit_consistency(self) -> "MonumentEstimateRequest":
        """Prevent obvious unit mixing: reject impossibly small mm values or huge foot values."""
        if self.dimension_unit == DimensionUnit.MM:
            if self.width > 0 and self.width < 100:
                raise ValueError(
                    f"width={self.width} with unit=mm is suspiciously small (< 100mm). "
                    "Likely an inch value — use dimension_unit='inches' instead."
                )
        if self.dimension_unit == DimensionUnit.FEET:
            if self.width > 50:
                raise ValueError(
                    f"width={self.width} with unit=feet is > 50 ft — likely a unit error. "
                    "Use dimension_unit='inches' for inch values."
                )
        return self

    def get_face_area_sf(self) -> float:
        """Return face area in square feet, computing from dimensions if needed."""
        if self.face_area_sf is not None and self.face_area_sf > 0:
            return self.face_area_sf
        w_in = _to_inches(self.width, self.dimension_unit)
        h_in = _to_inches(self.height, self.dimension_unit)
        return (w_in * h_in) / 144.0


# ── Awning Estimate Request ───────────────────────────────────────────────────

class AwningEstimateRequest(BaseModel):
    """
    Input model for awning estimates (AWNNON).
    Drives abc_engine.estimate_awning().

    Uses linear-foot projection plus face SF for material quantities.
    Dimension unit: all length/depth/height values use the same unit.
    """

    sign_type: SignType = Field(
        default=SignType.AWNNON,
        description="Must be AWNNON",
    )
    dimension_unit: DimensionUnit = Field(
        default=DimensionUnit.INCHES,
        description="Unit system for projection, width, valance_height, and soffit_depth",
    )

    # Awning geometry
    projection: float = Field(
        ge=0.0,
        le=600.0,  # 50 ft in inches
        description="Horizontal projection (depth) of awning in dimension_unit",
    )
    width: float = Field(
        ge=0.0,
        le=1200.0,  # 100 ft in inches
        description="Awning width (horizontal span) in dimension_unit",
    )
    valance_height: float = Field(
        default=0.0,
        ge=0.0,
        le=120.0,
        description="Valance face height in dimension_unit",
    )
    soffit_depth: float = Field(
        default=0.0,
        ge=0.0,
        le=600.0,
        description="Soffit/underside depth in dimension_unit (usually same as projection)",
    )

    # Frame
    num_bays: int = Field(
        default=1,
        ge=1,
        le=50,
        description="Number of awning structural bays",
    )
    has_valance: bool = Field(
        default=True,
        description="True if awning includes a valance face panel",
    )

    # Install
    install_height_ft: float = Field(
        default=10.0,
        ge=0.0,
        le=100.0,
        description="Bottom of awning height in feet (always feet, not dimension_unit)",
    )
    miles_one_way: float = Field(default=0.0, ge=0.0, le=1000.0)
    crew_size: int = Field(default=2, ge=1, le=10)

    @field_validator("sign_type")
    @classmethod
    def must_be_awning_type(cls, v: SignType) -> SignType:
        if v != SignType.AWNNON:
            raise ValueError(
                f"AwningEstimateRequest requires sign_type AWNNON, got {v.value}"
            )
        return v

    @model_validator(mode="after")
    def require_nonzero_geometry(self) -> "AwningEstimateRequest":
        if self.projection <= 0 or self.width <= 0:
            raise ValueError(
                "Both projection and width must be > 0 to estimate awning work"
            )
        return self

    @model_validator(mode="after")
    def validate_dimension_unit_consistency(self) -> "AwningEstimateRequest":
        """Catch obvious unit confusion on awning dimensions."""
        if self.dimension_unit == DimensionUnit.FEET:
            # Awnings rarely exceed 20 ft projection
            if self.projection > 20:
                raise ValueError(
                    f"projection={self.projection} with unit=feet is > 20 ft — "
                    "likely supplied in inches. Use dimension_unit='inches'."
                )
        if self.dimension_unit == DimensionUnit.MM:
            if self.projection < 100:
                raise ValueError(
                    f"projection={self.projection} with unit=mm is < 100mm — "
                    "likely supplied in inches. Use dimension_unit='inches'."
                )
        return self

    def get_projection_inches(self) -> float:
        return _to_inches(self.projection, self.dimension_unit)

    def get_width_inches(self) -> float:
        return _to_inches(self.width, self.dimension_unit)

    def get_face_sf(self) -> float:
        """Calculate awning face area including valance if present."""
        w_in = self.get_width_inches()
        val_in = _to_inches(self.valance_height, self.dimension_unit)
        if self.has_valance and val_in > 0:
            return (w_in * val_in) / 144.0
        return 0.0


# ── Removal Estimate Request ──────────────────────────────────────────────────

class RemovalEstimateRequest(BaseModel):
    """
    Input model for sign removal estimates.
    Drives abc_engine.estimate_removal().

    Removal is crew-time based: number of units * complexity multiplier * travel.
    """

    # What is being removed
    sign_type: SignType = Field(
        default=SignType.CLLIT,
        description="Type of sign being removed (drives complexity multiplier)",
    )
    num_units: int = Field(
        default=1,
        ge=1,
        le=200,
        description="Number of individual sign units or faces to remove",
    )

    # Size of what's being removed (for crew-time estimation)
    face_area_sf: float = Field(
        default=0.0,
        ge=0.0,
        le=5000.0,
        description="Total face area in square feet of signs being removed",
    )

    # Access conditions
    remove_height_ft: float = Field(
        default=15.0,
        ge=0.0,
        le=200.0,
        description="Height of the sign being removed in feet",
    )
    requires_crane: bool = Field(
        default=False,
        description="True if removal requires a crane (drives significant upcharge)",
    )
    requires_demolition: bool = Field(
        default=False,
        description="True if foundation/pole demolition is required",
    )

    # Crew
    crew_size: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Number of crew members for removal",
    )
    miles_one_way: float = Field(
        default=0.0,
        ge=0.0,
        le=1000.0,
    )

    # Destination of removed signs
    haul_to: Literal["warehouse", "dumpster", "customer", "none"] = Field(
        default="warehouse",
        description="Where removed signs are taken after removal",
    )

    @model_validator(mode="after")
    def warn_large_crane_job(self) -> "RemovalEstimateRequest":
        """Validate that crane jobs also have height > 15 ft (sanity check)."""
        if self.requires_crane and self.remove_height_ft < 15:
            raise ValueError(
                f"requires_crane=True but remove_height_ft={self.remove_height_ft} ft. "
                "Crane is typically only needed for signs at 15+ ft. "
                "Verify height is correct."
            )
        return self

    @model_validator(mode="after")
    def warn_demolition_without_pole(self) -> "RemovalEstimateRequest":
        """Demolition only makes sense for pole/monument signs."""
        if self.requires_demolition and self.sign_type not in (
            SignType.POLLIT, SignType.MONDF, SignType.MONSF,
        ):
            raise ValueError(
                f"requires_demolition=True on sign_type={self.sign_type.value} — "
                "demolition applies to pole/monument signs (POLLIT, MONDF, MONSF). "
                "If this is intentional, set sign_type to the closest applicable type."
            )
        return self
