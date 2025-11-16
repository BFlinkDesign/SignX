"""Prediction endpoints."""
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status

from signx_intel.api.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    CostDriverImportance
)

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse, status_code=status.HTTP_200_OK)
async def predict_cost(request: PredictionRequest):
    """
    Predict project cost based on drivers.
    
    This is a placeholder implementation. Once you train a model,
    this will load the trained model and make real predictions.
    """
    # TODO: Load trained model and make real predictions
    # For now, return mock data with a simple heuristic
    
    drivers = request.drivers
    
    # Simple heuristic based on common sign project drivers
    base_cost = Decimal("1000.00")
    
    # Add cost based on area
    if "sign_area_sqft" in drivers:
        base_cost += Decimal(str(drivers["sign_area_sqft"])) * Decimal("50.00")
    
    # Add cost based on height
    if "sign_height_ft" in drivers:
        base_cost += Decimal(str(drivers["sign_height_ft"])) * Decimal("100.00")
    
    # Foundation type multiplier
    foundation_multipliers = {
        "drilled_pier": 1.5,
        "spread_footing": 1.2,
        "mono_column": 1.0
    }
    if "foundation_type" in drivers:
        multiplier = foundation_multipliers.get(drivers["foundation_type"], 1.0)
        base_cost = base_cost * Decimal(str(multiplier))
    
    # Generate cost driver importance (mock SHAP values)
    cost_drivers = []
    if "sign_area_sqft" in drivers:
        cost_drivers.append(
            CostDriverImportance(driver="sign_area_sqft", importance=0.45, shap_value=0.45)
        )
    if "sign_height_ft" in drivers:
        cost_drivers.append(
            CostDriverImportance(driver="sign_height_ft", importance=0.30, shap_value=0.30)
        )
    if "foundation_type" in drivers:
        cost_drivers.append(
            CostDriverImportance(driver="foundation_type", importance=0.15, shap_value=0.15)
        )
    
    return PredictionResponse(
        predicted_cost=base_cost,
        confidence_score=0.75,  # Mock confidence
        cost_breakdown={
            "material": float(base_cost * Decimal("0.55")),
            "labor": float(base_cost * Decimal("0.35")),
            "overhead": float(base_cost * Decimal("0.10"))
        },
        cost_drivers=cost_drivers,
        similar_projects_count=0,  # TODO: Query database for similar projects
        anomaly_score=0.05,  # Mock anomaly score (low = normal)
        model_version="mock-v1.0"
    )


@router.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_cost_batch(request: BatchPredictionRequest):
    """Batch prediction for multiple projects."""
    results = []
    successful = 0
    failed = 0
    
    for pred_request in request.predictions:
        try:
            result = await predict_cost(pred_request)
            results.append(result)
            successful += 1
        except Exception as e:
            failed += 1
            # Optionally add error result
            continue
    
    return BatchPredictionResponse(
        results=results,
        total_predictions=len(request.predictions),
        successful=successful,
        failed=failed
    )

