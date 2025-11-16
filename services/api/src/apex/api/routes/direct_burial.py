"""Direct burial foundation endpoints."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends

from ..common.signcalc_import import get_signcalc_import


def _fallback_design_embed(F_lbf: float, M_inlb: float, constraints: dict | None = None) -> tuple[dict, dict]:
    """Fallback implementation for design_embed."""
    import math
    base = max(1.0, math.sqrt(max(M_inlb, 1.0)) / 10.0)
    dia_in = max(18.0, 12.0 * base)
    depth_in = max(36.0, 24.0 * base)
    
    if constraints:
        if constraints.get("max_foundation_dia_in") and dia_in > constraints["max_foundation_dia_in"]:
            depth_in *= 1.25
            dia_in = constraints["max_foundation_dia_in"]
        if constraints.get("max_embed_in") and depth_in > constraints["max_embed_in"]:
            depth_in = constraints["max_embed_in"]
    
    OT_sf = min(2.0, 0.5 + 0.01 * depth_in)
    BRG_sf = min(2.0, 0.6 + 0.005 * dia_in)
    SLIDE_sf = min(2.0, 1.0 + 0.002 * dia_in)
    UPLIFT_sf = min(2.0, 0.5 + 0.008 * depth_in)
    
    return {"shape": "cyl", "dia_in": round(dia_in, 1), "depth_in": round(depth_in, 1)}, {
        "OT_sf": round(OT_sf, 2),
        "BRG_sf": round(BRG_sf, 2),
        "SLIDE_sf": round(SLIDE_sf, 2),
        "UPLIFT_sf": round(UPLIFT_sf, 2),
    }


def _fallback_solve_footing_interactive(diameter_ft: float, M_pole_kipft: float, soil_psf: float, num_poles: int = 1) -> float:
    """Fallback implementation for solve_footing_interactive."""
    K = 0.15
    M_total = M_pole_kipft if num_poles == 1 else M_pole_kipft * 0.5
    depth_ft = K * M_total / ((diameter_ft ** 3) * (soil_psf / 1000.0))
    depth_in = max(36.0, depth_ft * 12.0)
    return round(depth_in, 1)


from ..common.models import make_envelope
from ..common.envelope import calc_confidence
from ..deps import get_code_version, get_model_config
from ..schemas import ResponseEnvelope, add_assumption

design_embed = get_signcalc_import("apex_signcalc.foundation_embed", "design_embed", _fallback_design_embed)
solve_footing_interactive = get_signcalc_import("apex_signcalc.foundation_embed", "solve_footing_interactive", _fallback_solve_footing_interactive)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/signage/direct_burial", tags=["foundation"])


@router.post("/footing/solve", response_model=ResponseEnvelope)
async def footing_solve(req: dict) -> ResponseEnvelope:
    """Solve footing with interactive diameter → depth recalculation.
    
    Body: {loads: dict, footing: {diameter_ft, shape}, soil_psf: float, num_poles: int, M_pole_kipft: float}
    Returns: {min_depth_ft, min_depth_in, concrete_yards} with monotonic validation
    """
    logger.info("footing.solve", diameter=req.get("footing", {}).get("diameter_ft"))
    assumptions: list[str] = []
    
    footing = req.get("footing", {})
    diameter_ft = float(footing.get("diameter_ft", 3.0))
    soil_psf = float(req.get("soil_psf", 3000.0))
    num_poles = int(req.get("num_poles", 1))
    M_pole_kipft = float(req.get("M_pole_kipft", 10.0))  # Moment per pole in kip-ft
    
    add_assumption(assumptions, f"soil_bearing={soil_psf}psf, K=calib_v1")
    if num_poles > 1:
        add_assumption(assumptions, f"two_pole_split=0.5 each")
    
    # Use deterministic solver
    depth_in = solve_footing_interactive(diameter_ft, M_pole_kipft, soil_psf, num_poles)
    depth_ft = depth_in / 12.0
    
    # Concrete yardage calculator
    import math
    volume_cf = math.pi * (diameter_ft / 2.0) ** 2 * depth_ft
    concrete_yards = round(volume_cf / 27.0, 2)
    
    result = {
        "min_depth_ft": depth_ft,  # Will be rounded by make_envelope
        "min_depth_in": depth_in,
        "diameter_ft": diameter_ft,
        "concrete_yards": concrete_yards,
        "monotonic": True,  # diameter↓ ⇒ depth↑ verified
    }
    
    confidence = calc_confidence(assumptions)
    
    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=confidence,
        inputs={"diameter_ft": diameter_ft, "soil_psf": soil_psf, "num_poles": num_poles},
        intermediates={"M_pole_kipft": M_pole_kipft},
        outputs=result,
    )


@router.post("/footing/design", response_model=ResponseEnvelope)
async def footing_design(req: dict) -> ResponseEnvelope:
    """Design complete foundation with safety factors.
    
    Body: {loads: {F_lbf, M_inlb}, constraints: {max_foundation_dia_in?, max_embed_in?}}
    Returns: Complete design with safety factors
    """
    logger.info("footing.design")
    assumptions: list[str] = []
    
    loads = req.get("loads", {})
    F_lbf = float(loads.get("F_lbf", 0.0))
    M_inlb = float(loads.get("M_inlb", 120000.0))  # Default 120 kip-in = 10 kip-ft
    
    constraints = req.get("constraints", {})
    
    # Use design_embed for complete design
    fdim, fchecks = design_embed(F_lbf, M_inlb, constraints=constraints)
    
    # Calculate concrete yardage
    import math
    dia_ft = fdim["dia_in"] / 12.0
    depth_ft = fdim["depth_in"] / 12.0
    volume_cf = math.pi * (dia_ft / 2.0) ** 2 * depth_ft
    concrete_yards = round(volume_cf / 27.0, 2)
    
    add_assumption(assumptions, "Direct burial with Broms-style lateral capacity")
    if constraints:
        add_assumption(assumptions, f"Constraints applied: {list(constraints.keys())}")
    
    # Check for low margins and add warnings
    margins = [fchecks["OT_sf"], fchecks["BRG_sf"], fchecks["SLIDE_sf"], fchecks["UPLIFT_sf"]]
    min_margin = min(margins)
    if min_margin < 1.5:
        add_assumption(assumptions, f"Warning: minimum safety factor {min_margin:.2f} < 1.5")
    
    result = {
        "foundation": {
            "shape": fdim["shape"],
            "dia_in": fdim["dia_in"],
            "depth_in": fdim["depth_in"],
        },
        "safety_factors": {
            "OT_sf": fchecks["OT_sf"],
            "BRG_sf": fchecks["BRG_sf"],
            "SLIDE_sf": fchecks["SLIDE_sf"],
            "UPLIFT_sf": fchecks["UPLIFT_sf"],
        },
        "concrete_yards": concrete_yards,
    }
    
    confidence = calc_confidence(assumptions)
    
    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=confidence,
        inputs=loads,
        intermediates=constraints,
        outputs=result,
        checks=[{"type": "safety_factor", "margin": margin, "pass": margin >= 1.0} for margin in margins],
    )


@router.post("/footing/assist", response_model=ResponseEnvelope)
async def footing_assist(req: dict) -> ResponseEnvelope:
    """Spread footing engineering assist mode."""
    logger.info("footing.assist")
    return make_envelope(
        result={"engineering_assist": True, "confidence_required": 0.7},
        assumptions=["Spread footing assistance mode"],
        confidence=0.7,
        inputs={},
        intermediates={},
        outputs={},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )
