"""Prediction schemas."""
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    """Schema for cost prediction request."""
    drivers: dict = Field(
        ...,
        description="Cost drivers (e.g., sign_height_ft, sign_area_sqft, foundation_type)"
    )
    project_id: Optional[str] = Field(None, description="Optional project ID for tracking")


class CostDriverImportance(BaseModel):
    """Individual cost driver importance."""
    driver: str
    importance: float = Field(..., ge=0.0, le=1.0)
    shap_value: Optional[float] = None


class PredictionResponse(BaseModel):
    """Schema for cost prediction response."""
    predicted_cost: Decimal = Field(..., description="Predicted total cost")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence")
    cost_breakdown: Optional[dict] = Field(
        None,
        description="Predicted breakdown (labor, material, etc.)"
    )
    cost_drivers: list[CostDriverImportance] = Field(
        default_factory=list,
        description="Importance of each cost driver"
    )
    similar_projects_count: int = Field(
        default=0,
        description="Number of similar historical projects found"
    )
    anomaly_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Anomaly score (0=normal, 1=highly unusual)"
    )
    model_version: str = Field(default="v1.0", description="ML model version used")


class BatchPredictionRequest(BaseModel):
    """Schema for batch prediction request."""
    predictions: list[PredictionRequest]


class BatchPredictionResponse(BaseModel):
    """Schema for batch prediction response."""
    results: list[PredictionResponse]
    total_predictions: int
    successful: int
    failed: int

