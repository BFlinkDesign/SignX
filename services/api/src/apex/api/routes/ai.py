"""AI-powered prediction endpoints.

Serves GPU-trained ML models for cost estimation and design optimization.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

# Add services/ml to path
ml_services_path = Path(__file__).parent.parent.parent.parent.parent / "ml"
sys.path.insert(0, str(ml_services_path))

from cost_model import CostPredictor

from ..common.models import build_response_envelope
from ..deps import get_code_version, get_model_config
from ..schemas import ResponseEnvelope

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/ai", tags=["ai-predictions"])

# Load model at startup (singleton)
_cost_model: Optional[CostPredictor] = None


def get_cost_model() -> CostPredictor:
    """Dependency to get loaded cost prediction model."""
    global _cost_model
    
    if _cost_model is None:
        model_path = Path("models/cost/v1")
        
        if not model_path.exists():
            raise HTTPException(
                status_code=503,
                detail="Cost model not loaded. Train model first: python scripts/train_cost_model.py"
            )
        
        try:
            _cost_model = CostPredictor.load(model_path)
            logger.info("ai.model.loaded", path=str(model_path))
        except Exception as e:
            logger.error("ai.model.load_failed", error=str(e))
            raise HTTPException(
                status_code=503,
                detail=f"Failed to load cost model: {e}"
            )
    
    return _cost_model


class CostPredictionRequest(BaseModel):
    """Request for cost prediction."""
    
    height_ft: float = Field(..., gt=0, le=100, description="Total sign height in feet")
    sign_area_sqft: float = Field(..., gt=0, le=1000, description="Sign area in square feet")
    wind_speed_mph: float = Field(115.0, ge=85, le=200, description="Design wind speed in mph")
    exposure_category: str = Field("C", pattern="^[BCD]$", description="Wind exposure (B, C, or D)")
    pole_size: float = Field(8.0, gt=0, le=24, description="Pole size in inches")
    pole_type: str = Field("round_hss", description="Pole type")
    foundation_type: str = Field("direct_burial", description="Foundation type")
    embedment_depth_ft: Optional[float] = Field(None, description="Foundation depth in feet")
    
    # Optional fields
    importance_factor: float = Field(1.0, ge=0.85, le=1.15)
    pole_thickness_in: float = Field(0.25, gt=0)
    concrete_volume_cuyd: Optional[float] = None
    soil_bearing_psf: float = Field(3000.0, gt=0)
    snow_load_psf: float = Field(0.0, ge=0)


class CostPredictionResponse(BaseModel):
    """Response from cost prediction."""
    
    predicted_cost: float = Field(..., description="Predicted total cost in USD")
    confidence_interval_90: tuple[float, float] = Field(..., description="90% confidence interval")
    confidence_interval_95: tuple[float, float] = Field(..., description="95% confidence interval")
    std_dev: float = Field(..., description="Standard deviation of predictions")
    model_version: str = Field(..., description="Model version used")
    features_used: int = Field(..., description="Number of features used")


@router.post("/predict-cost", response_model=ResponseEnvelope)
async def predict_cost(
    request: CostPredictionRequest,
    model: CostPredictor = Depends(get_cost_model)
) -> ResponseEnvelope:
    """Predict project cost using GPU-trained ML model.
    
    Returns cost estimate with confidence intervals based on historical
    Eagle Sign Company project data.
    """
    logger.info("ai.predict_cost.start", 
               height=request.height_ft,
               area=request.sign_area_sqft)
    
    try:
        # Convert request to feature dict
        features = {
            "height_ft": request.height_ft,
            "sign_area_sqft": request.sign_area_sqft,
            "wind_speed_mph": request.wind_speed_mph,
            "exposure_code": {"B": 0, "C": 1, "D": 2}[request.exposure_category],
            "importance_factor": request.importance_factor,
            "pole_type_code": {
                "round_hss": 0,
                "square_hss": 1,
                "pipe": 2,
                "i_beam": 3,
                "w_shape": 4,
            }.get(request.pole_type, 0),
            "pole_size": request.pole_size,
            "pole_thickness_in": request.pole_thickness_in,
            "pole_height_ft": request.height_ft,  # Approximate
            "foundation_type_code": {
                "direct_burial": 0,
                "base_plate": 1,
                "drilled_pier": 2,
            }.get(request.foundation_type, 0),
            "embedment_depth_ft": request.embedment_depth_ft or 0,
            "concrete_volume_cuyd": request.concrete_volume_cuyd or 0,
            "soil_bearing_psf": request.soil_bearing_psf,
            "snow_load_psf": request.snow_load_psf,
        }
        
        # Predict
        prediction = model.predict_with_uncertainty(features)
        
        result = CostPredictionResponse(
            predicted_cost=prediction["predicted_cost"],
            confidence_interval_90=prediction["confidence_interval_90"],
            confidence_interval_95=prediction["confidence_interval_95"],
            std_dev=prediction["std_dev"],
            model_version=prediction["model_version"],
            features_used=len(model.feature_columns or []),
        )
        
        assumptions = [
            "Based on historical Eagle Sign Company project data",
            "Confidence intervals via Monte Carlo simulation",
            f"Model trained on {model.training_metrics.get('n_train_samples', 0)} projects"
        ]
        
        # Add assumption if using extrapolated data
        if request.height_ft > 40:
            assumptions.append("Height exceeds typical range - prediction may be less reliable")
        
        logger.info("ai.predict_cost.success",
                   predicted=prediction["predicted_cost"],
                   ci_90=prediction["confidence_interval_90"])
        
        return build_response_envelope(
            result=result.model_dump(),
            assumptions=assumptions,
            confidence=0.85,  # Conservative for ML predictions
            trace_inputs=request.model_dump(),
            trace_outputs={
                "predicted_cost": prediction["predicted_cost"],
                "prediction_interval_width": prediction["confidence_interval_90"][1] - prediction["confidence_interval_90"][0]
            },
        )
        
    except Exception as e:
        logger.error("ai.predict_cost.error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Cost prediction failed: {e}"
        )


@router.get("/model-info", response_model=ResponseEnvelope)
async def get_model_info(
    model: CostPredictor = Depends(get_cost_model)
) -> ResponseEnvelope:
    """Get information about the loaded cost prediction model."""
    
    info = {
        "model_type": "XGBoost Regressor",
        "version": "1.0",
        "gpu_trained": model.use_gpu,
        "n_features": len(model.feature_columns or []),
        "feature_columns": model.feature_columns,
        "training_metrics": model.training_metrics,
        "top_features": model.feature_importances_.head(10).to_dict(orient="records") if model.feature_importances_ is not None else None,
    }
    
    return build_response_envelope(
        result=info,
        assumptions=["Model trained on historical project data"],
        confidence=1.0,
        trace_inputs={},
        trace_outputs={"model_version": "1.0"},
    )

