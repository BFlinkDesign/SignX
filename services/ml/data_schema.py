"""Data schema for cost estimation ML pipeline.

Defines the canonical structure for project cost data extracted from PDFs
and used for training prediction models.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ExposureCategory(str, Enum):
    """Wind exposure categories per ASCE 7-22."""
    B = "B"
    C = "C"
    D = "D"


class PoleType(str, Enum):
    """Pole structural types."""
    ROUND_HSS = "round_hss"
    SQUARE_HSS = "square_hss"
    PIPE = "pipe"
    I_BEAM = "i_beam"
    W_SHAPE = "w_shape"


class FoundationType(str, Enum):
    """Foundation installation types."""
    DIRECT_BURIAL = "direct_burial"
    BASE_PLATE = "base_plate"
    DRILLED_PIER = "drilled_pier"


class ProjectCostRecord(BaseModel):
    """Complete project cost record extracted from PDF summaries.
    
    This schema represents the canonical structure for historical cost data.
    All extracted PDF data should be normalized to this format.
    """
    
    # Project identification
    project_id: str = Field(..., description="Unique project identifier")
    project_name: Optional[str] = Field(None, description="Project name")
    customer_name: Optional[str] = Field(None, description="Customer name")
    job_number: Optional[str] = Field(None, description="Internal job number")
    quote_date: Optional[date] = Field(None, description="Date of quote/estimate")
    completion_date: Optional[date] = Field(None, description="Project completion date")
    
    # Design specifications
    height_ft: float = Field(..., gt=0, description="Total sign height in feet")
    sign_area_sqft: float = Field(..., gt=0, description="Sign face area in square feet")
    sign_width_ft: Optional[float] = Field(None, gt=0, description="Sign width in feet")
    sign_height_ft: Optional[float] = Field(None, gt=0, description="Sign height in feet")
    
    # Environmental loads
    wind_speed_mph: float = Field(..., ge=85, le=200, description="Design wind speed in mph")
    exposure_category: ExposureCategory = Field(..., description="Wind exposure category")
    importance_factor: float = Field(1.0, ge=0.85, le=1.15, description="Risk category importance factor")
    snow_load_psf: Optional[float] = Field(None, ge=0, description="Ground snow load in psf")
    seismic_category: Optional[str] = Field(None, description="Seismic design category")
    
    # Structural design
    pole_type: PoleType = Field(..., description="Pole structural type")
    pole_size: float = Field(..., gt=0, description="Pole nominal size in inches")
    pole_thickness_in: Optional[float] = Field(None, gt=0, description="Pole wall thickness in inches")
    pole_material_grade: Optional[str] = Field(None, description="Steel grade (e.g., A500B)")
    pole_height_ft: float = Field(..., gt=0, description="Pole height above grade in feet")
    
    # Foundation design
    foundation_type: FoundationType = Field(..., description="Foundation type")
    embedment_depth_ft: Optional[float] = Field(None, gt=0, description="Foundation embedment depth in feet")
    foundation_diameter_ft: Optional[float] = Field(None, gt=0, description="Foundation diameter in feet")
    concrete_volume_cuyd: Optional[float] = Field(None, ge=0, description="Concrete volume in cubic yards")
    soil_bearing_psf: Optional[float] = Field(None, gt=0, description="Allowable soil bearing in psf")
    
    # Cost breakdown
    material_cost: Optional[float] = Field(None, ge=0, description="Material cost in USD")
    labor_cost: Optional[float] = Field(None, ge=0, description="Labor cost in USD")
    engineering_cost: Optional[float] = Field(None, ge=0, description="Engineering/PE stamp cost in USD")
    permit_cost: Optional[float] = Field(None, ge=0, description="Permit fees in USD")
    markup_percent: Optional[float] = Field(None, ge=0, le=100, description="Markup percentage")
    total_cost: float = Field(..., gt=0, description="Total project cost in USD")
    
    # Project metadata
    location_city: Optional[str] = Field(None, description="Project city")
    location_state: Optional[str] = Field(None, description="Project state")
    location_zip: Optional[str] = Field(None, description="Project ZIP code")
    
    # Engineering details
    pe_approved: bool = Field(False, description="PE stamp approved")
    pe_engineer: Optional[str] = Field(None, description="PE engineer name")
    calculated_stress_psi: Optional[float] = Field(None, description="Calculated stress in psi")
    calculated_deflection_in: Optional[float] = Field(None, description="Calculated deflection in inches")
    utilization_ratio: Optional[float] = Field(None, ge=0, le=2, description="Demand/capacity ratio")
    
    # Outcome tracking
    bid_won: Optional[bool] = Field(None, description="Whether bid was won")
    actual_completion_cost: Optional[float] = Field(None, description="Actual cost at completion")
    cost_variance_percent: Optional[float] = Field(None, description="Cost variance from estimate")
    
    # Data provenance
    source_pdf: Optional[str] = Field(None, description="Source PDF filename")
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="Extraction timestamp")
    data_version: str = Field("1.0", description="Schema version")
    
    @field_validator("quote_date", "completion_date", mode="before")
    @classmethod
    def parse_dates(cls, value):
        """Parse various date formats."""
        if value is None:
            return None
        if isinstance(value, (date, datetime)):
            return value
        if isinstance(value, str):
            from dateutil import parser
            return parser.parse(value).date()
        return value
    
    @field_validator("total_cost", "material_cost", "labor_cost", mode="before")
    @classmethod
    def clean_currency(cls, value):
        """Remove currency symbols and commas from cost fields."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remove $, commas
            cleaned = value.replace("$", "").replace(",", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                return None
        return value
    
    def to_features_dict(self) -> dict:
        """Convert to flat feature dictionary for ML training."""
        return {
            "height_ft": self.height_ft,
            "sign_area_sqft": self.sign_area_sqft,
            "wind_speed_mph": self.wind_speed_mph,
            "exposure_code": {"B": 0, "C": 1, "D": 2}[self.exposure_category.value],
            "importance_factor": self.importance_factor,
            "pole_type_code": {
                "round_hss": 0,
                "square_hss": 1,
                "pipe": 2,
                "i_beam": 3,
                "w_shape": 4,
            }[self.pole_type.value],
            "pole_size": self.pole_size,
            "pole_thickness_in": self.pole_thickness_in or 0.25,
            "pole_height_ft": self.pole_height_ft,
            "foundation_type_code": {
                "direct_burial": 0,
                "base_plate": 1,
                "drilled_pier": 2,
            }[self.foundation_type.value],
            "embedment_depth_ft": self.embedment_depth_ft or 0,
            "concrete_volume_cuyd": self.concrete_volume_cuyd or 0,
            "soil_bearing_psf": self.soil_bearing_psf or 3000,
            "snow_load_psf": self.snow_load_psf or 0,
            "material_cost": self.material_cost or 0,
            "labor_cost": self.labor_cost or 0,
            "engineering_cost": self.engineering_cost or 0,
            "total_cost": self.total_cost,
        }


class DataQualityReport(BaseModel):
    """Quality report for extracted dataset."""
    
    total_records: int
    valid_records: int
    invalid_records: int
    completeness_percent: float
    missing_fields: dict[str, int]
    outliers: dict[str, list[str]]
    date_range: tuple[Optional[date], Optional[date]]
    cost_range: tuple[float, float]
    warnings: list[str]
    errors: list[str]

