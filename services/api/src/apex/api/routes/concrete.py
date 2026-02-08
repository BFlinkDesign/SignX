"""Concrete yardage calculator utility."""

from __future__ import annotations

import math

import structlog
from fastapi import APIRouter

from ..common.models import make_envelope
from ..deps import get_code_version, get_model_config
from ..schemas import ResponseEnvelope, add_assumption

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/signage/common", tags=["utilities"])


@router.post("/concrete/yards", response_model=ResponseEnvelope)
async def calculate_concrete_yards(req: dict) -> ResponseEnvelope:
    """Calculate concrete yardage for cylindrical footing.
    
    Body: {diameter_ft: float, depth_ft: float}
    Returns: {concrete_yards: float, volume_cf: float}
    """
    logger.info("concrete.yards", diameter=req.get("diameter_ft"))
    assumptions: list[str] = []
    
    from ..common.validation import require_positive
    
    diameter_ft = require_positive(float(req.get("diameter_ft", 0.0)), "diameter_ft")
    depth_ft = require_positive(float(req.get("depth_ft", 0.0)), "depth_ft")
    
    # Volume in cubic feet: V = π * r² * h
    radius_ft = diameter_ft / 2.0
    volume_cf = math.pi * (radius_ft ** 2) * depth_ft
    
    # Convert to cubic yards: 1 cu yd = 27 cu ft
    concrete_yards = round(volume_cf / 27.0, 2)
    volume_cf_rounded = round(volume_cf, 2)
    
    result = {
        "concrete_yards": concrete_yards,
        "volume_cf": volume_cf_rounded,
        "diameter_ft": diameter_ft,
        "depth_ft": depth_ft,
    }
    
    add_assumption(assumptions, "Formula: V = π × (d/2)² × h / 27")
    
    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=1.0,
        inputs={"diameter_ft": diameter_ft, "depth_ft": depth_ft},
        intermediates={"volume_cf": volume_cf},
        outputs=result,
        code_version=get_code_version(),
        model_config=get_model_config(),
    )

