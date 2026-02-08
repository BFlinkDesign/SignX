"""Cabinet design endpoints."""

from __future__ import annotations

import structlog
from fastapi import APIRouter

from ..common.envelope import calc_confidence
from ..common.models import make_envelope
from ..schemas import ResponseEnvelope, add_assumption

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/signage/common", tags=["cabinets"])


@router.post("/cabinets/derive", response_model=ResponseEnvelope)
async def derive_cabinets(req: dict) -> ResponseEnvelope:  # type: ignore
    """Compute cabinet geometry: area, centroid, weight.
    
    Body: {overall_height_ft: float, cabinets: [{width_ft, height_ft, depth_in, weight_psf}]}
    Returns: {A_ft2, z_cg_ft, weight_estimate_lb, view_token}
    """
    logger.info("cabinets.derive")
    assumptions: list[str] = []
    
    overall_height = req.get("overall_height_ft", 0.0)
    cabinets = req.get("cabinets", [])
    
    if not cabinets:
        total_area = 0.0
        total_weight = 0.0
        z_cg = 0.0
    else:
        # Accumulate area and weighted CG
        total_area = 0.0
        total_weight = 0.0
        moment_sum = 0.0
        
        for cab in cabinets:
            w = float(cab.get("width_ft", 0.0))
            h = float(cab.get("height_ft", 0.0))
            psf = float(cab.get("weight_psf", 10.0))
            A_cab = w * h
            W_cab = A_cab * psf
            
            # CG at mid-height of cabinet
            z_cab = float(cab.get("z_offset_ft", 0.0)) + h / 2.0
            
            total_area += A_cab
            total_weight += W_cab
            moment_sum += W_cab * z_cab
            
        z_cg = moment_sum / total_weight if total_weight > 0 else 0.0
        
        add_assumption(assumptions, f"{len(cabinets)} cabinet(s) processed")
    
    view_token = f"cab_{hash(str(cabinets)) % 10000}"  # deterministic
    
    result = {
        "A_ft2": total_area,  # Will be rounded by make_envelope
        "z_cg_ft": z_cg,
        "weight_estimate_lb": total_weight,
        "view_token": view_token,
    }
    
    # Calculate confidence from assumptions
    confidence = calc_confidence(assumptions)
    
    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=confidence,
        inputs={"overall_height_ft": overall_height, "cabinet_count": len(cabinets)},
        intermediates={"view_token": view_token},
        outputs=result,
    )


@router.post("/cabinets/add", response_model=ResponseEnvelope)
async def add_cabinet(
    req: dict,
    project_id: str | None = None,
) -> ResponseEnvelope:
    """Add cabinet to stack and update project payload.
    
    Body: {cabinet: {width_ft, height_ft, depth_in, weight_psf, z_offset_ft}, project_id?: str}
    Returns: Updated cabinet geometry and optionally saves to project payload
    """
    logger.info("cabinets.add", project_id=project_id)
    assumptions: list[str] = []
    
    # Recompute with new cabinet added
    cabinets = req.get("existing_cabinets", [])
    new_cabinet = req.get("cabinet", {})
    
    if new_cabinet:
        cabinets.append(new_cabinet)
    
    # Use derive logic to recompute
    overall_height = req.get("overall_height_ft", 0.0)
    
    total_area = 0.0
    total_weight = 0.0
    moment_sum = 0.0
    
    for cab in cabinets:
        w = float(cab.get("width_ft", 0.0))
        h = float(cab.get("height_ft", 0.0))
        psf = float(cab.get("weight_psf", 10.0))
        A_cab = w * h
        W_cab = A_cab * psf
        z_cab = float(cab.get("z_offset_ft", 0.0)) + h / 2.0
        
        total_area += A_cab
        total_weight += W_cab
        moment_sum += W_cab * z_cab
    
    z_cg = moment_sum / total_weight if total_weight > 0 else 0.0
    view_token = f"cab_{hash(str(cabinets)) % 10000}"
    
    result = {
        "A_ft2": total_area,  # Will be rounded by make_envelope
        "z_cg_ft": z_cg,
        "weight_estimate_lb": total_weight,
        "view_token": view_token,
        "cabinet_count": len(cabinets),
    }
    
    add_assumption(assumptions, f"{len(cabinets)} cabinet(s) in stack")
    
    # TODO: If project_id provided, update project payload with new cabinet config
    # Would require payload save endpoint integration
    
    # Calculate confidence from assumptions
    confidence = calc_confidence(assumptions)
    
    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=confidence,
        inputs={"overall_height_ft": overall_height, "cabinet": new_cabinet},
        intermediates={"cabinet_count": len(cabinets), "view_token": view_token},
        outputs=result,
    )

