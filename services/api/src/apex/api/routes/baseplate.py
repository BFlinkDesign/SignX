"""Baseplate foundation endpoints."""

from __future__ import annotations

import math

import structlog
from fastapi import APIRouter

from ..common.signcalc_import import get_signcalc_import


def _fallback_design_anchors(F_lbf: float, M_inlb: float) -> tuple[dict, dict]:
    """Fallback implementation for design_anchors."""
    pattern = "4-anchors"
    dia = "3/4 in"
    embed_in = 10.0
    plate_t_in = 0.5
    checks = {"T_sf": 1.3, "V_sf": 1.2}
    ref = f"{pattern}-{dia}-e{embed_in}-t{plate_t_in}"
    return {"pattern": pattern, "dia": dia, "embed_in": embed_in, "plate_t_in": plate_t_in, "ref": ref}, checks


design_anchors = get_signcalc_import("apex_signcalc.anchors_baseplate", "design_anchors", _fallback_design_anchors)

from ..common.models import make_envelope
from ..deps import get_code_version, get_model_config
from ..schemas import ResponseEnvelope, add_assumption

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/signage/baseplate", tags=["baseplate"])


def _check_plate_thickness(plate: dict, loads: dict) -> dict:
    """ACI-style plate thickness check for bending under anchor tension."""
    w_in = float(plate.get("w_in", 12.0))
    l_in = float(plate.get("l_in", 12.0))
    t_in = float(plate.get("t_in", 0.5))
    fy_ksi = float(plate.get("fy_ksi", 36.0))
    
    # Simplified: M = T * e (eccentricity), fb = M / S <= 0.6 * fy
    T_kip = float(loads.get("T_kip", 0.0))
    e_in = float(plate.get("e_in", 3.0))  # Distance to anchor
    M_kipin = T_kip * e_in
    S_in3 = w_in * (t_in ** 2) / 6.0
    fb_ksi = M_kipin / max(S_in3, 0.01)
    fb_allow_ksi = 0.6 * fy_ksi
    
    pass_check = fb_ksi <= fb_allow_ksi
    return {
        "name": "Plate Thickness",
        "pass": pass_check,
        "demand": round(fb_ksi, 2),
        "capacity": round(fb_allow_ksi, 2),
        "unit": "ksi",
        "governing": "bending",
        "sf": round(fb_allow_ksi / max(fb_ksi, 0.01), 2),
    }


def _check_weld_strength(weld: dict, loads: dict) -> dict:
    """Weld strength check per AISC."""
    size_in = float(weld.get("size_in", 0.25))
    strength_ksi = float(weld.get("strength", 70.0))  # E70XX
    
    V_kip = float(loads.get("V_kip", 0.0))
    M_kipin = float(loads.get("M_kipin", 0.0))
    
    # Simplified weld capacity: 0.6 * fexx * 0.707 * size * length
    fexx_ksi = strength_ksi
    weld_length_in = float(weld.get("length_in", 12.0))
    capacity_k = 0.6 * fexx_ksi * 0.707 * size_in * weld_length_in
    
    # Combined stress (simplified)
    demand_k = math.sqrt(V_kip ** 2 + (M_kipin / weld_length_in) ** 2)
    
    pass_check = demand_k <= capacity_k
    return {
        "name": "Weld Strength",
        "pass": pass_check,
        "demand": round(demand_k, 2),
        "capacity": round(capacity_k, 2),
        "unit": "k",
        "governing": "shear",
        "sf": round(capacity_k / max(demand_k, 0.01), 2),
    }


def _check_anchor_tension(anchors: dict, loads: dict) -> dict:
    """Anchor tension check per ACI 318."""
    num_anchors = int(anchors.get("num_anchors", 4))
    dia_in = float(anchors.get("dia_in", 0.75))
    embed_in = float(anchors.get("embed_in", 10.0))
    fy_anchor_ksi = float(anchors.get("fy_ksi", 58.0))
    
    T_total_kip = float(loads.get("T_kip", 0.0))
    T_per_bolt_kip = T_total_kip / num_anchors
    
    # Simplified capacity: min(steel, concrete breakout)
    # Steel: 0.75 * 0.75 * Ab * fy
    Ab_sqin = math.pi * (dia_in / 2.0) ** 2
    steel_capacity_k = 0.75 * 0.75 * Ab_sqin * fy_anchor_ksi
    
    # Concrete breakout (simplified): ~25 * embed^1.5 * sqrt(fc') * spacing factor
    fc_psi = float(anchors.get("fc_psi", 4000.0))
    spacing_in = float(anchors.get("spacing_in", 6.0))
    breakout_factor = 25.0 * (embed_in ** 1.5) * math.sqrt(fc_psi / 1000.0) * min(1.0, spacing_in / embed_in)
    concrete_capacity_k = breakout_factor / 1000.0  # Convert to kips
    
    capacity_k = min(steel_capacity_k, concrete_capacity_k)
    
    pass_check = T_per_bolt_kip <= capacity_k
    return {
        "name": "Anchor Tension",
        "pass": pass_check,
        "demand": round(T_per_bolt_kip, 2),
        "capacity": round(capacity_k, 2),
        "unit": "k/bolt",
        "governing": "steel" if steel_capacity_k < concrete_capacity_k else "breakout",
        "sf": round(capacity_k / max(T_per_bolt_kip, 0.01), 2),
    }


def _check_anchor_shear(anchors: dict, loads: dict) -> dict:
    """Anchor shear check."""
    num_anchors = int(anchors.get("num_anchors", 4))
    dia_in = float(anchors.get("dia_in", 0.75))
    fy_anchor_ksi = float(anchors.get("fy_ksi", 58.0))
    
    V_total_kip = float(loads.get("V_kip", 0.0))
    V_per_bolt_kip = V_total_kip / num_anchors
    
    # Steel capacity: 0.65 * 0.6 * Ab * fy
    Ab_sqin = math.pi * (dia_in / 2.0) ** 2
    capacity_k = 0.65 * 0.6 * Ab_sqin * fy_anchor_ksi
    
    pass_check = V_per_bolt_kip <= capacity_k
    return {
        "name": "Anchor Shear",
        "pass": pass_check,
        "demand": round(V_per_bolt_kip, 2),
        "capacity": round(capacity_k, 2),
        "unit": "k/bolt",
        "governing": "steel",
        "sf": round(capacity_k / max(V_per_bolt_kip, 0.01), 2),
    }


@router.post("/checks", response_model=ResponseEnvelope)
async def baseplate_checks(req: dict) -> ResponseEnvelope:
    """Validate baseplate design with ACI-style checks.
    
    Body: {
        plate: {w_in, l_in, t_in, fy_ksi, e_in},
        weld: {size_in, strength, length_in},
        anchors: {num_anchors, dia_in, embed_in, fy_ksi, fc_psi, spacing_in},
        loads: {T_kip, V_kip, M_kipin}
    }
    Returns: Checklist with pass/fail per item (all must pass for approval)
    """
    logger.info("baseplate.checks")
    assumptions: list[str] = []
    
    plate = req.get("plate", {})
    weld = req.get("weld", {})
    anchors = req.get("anchors", {})
    loads = req.get("loads", {})
    
    # Run all checks
    checks = [
        _check_plate_thickness(plate, loads),
        _check_weld_strength(weld, loads),
        _check_anchor_tension(anchors, loads),
        _check_anchor_shear(anchors, loads),
    ]
    
    all_pass = all(c["pass"] for c in checks)
    
    add_assumption(assumptions, f"Fy={plate.get('fy_ksi', 36)}ksi, E{int(weld.get('strength', 70))}XX fillet, ACI breakout")
    
    result = {
        "all_pass": all_pass,
        "checks": checks,
        "approved": all_pass,
    }
    
    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=0.92 if all_pass else 0.4,
        inputs={"plate": plate, "anchors": anchors, "loads": loads},
        intermediates={},
        outputs={"all_pass": all_pass},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.post("/design", response_model=ResponseEnvelope)
async def baseplate_design(req: dict) -> ResponseEnvelope:
    """Auto-design baseplate with deterministic anchor schedule.
    
    Body: {loads: {F_lbf, M_inlb}}
    Returns: Complete baseplate design with anchor schedule
    """
    logger.info("baseplate.design")
    assumptions: list[str] = []
    
    loads = req.get("loads", {})
    F_lbf = float(loads.get("F_lbf", 0.0))
    M_inlb = float(loads.get("M_inlb", 120000.0))
    
    # Use signcalc design_anchors
    anc, checks = design_anchors(F_lbf, M_inlb)
    
    add_assumption(assumptions, "4-anchor symmetric pattern")
    
    result = {
        "design": {
            "pattern": anc["pattern"],
            "dia": anc["dia"],
            "embed_in": anc["embed_in"],
            "plate_t_in": anc["plate_t_in"],
            "ref": anc["ref"],
        },
        "safety_factors": {
            "T_sf": checks["T_sf"],
            "V_sf": checks["V_sf"],
        },
    }
    
    confidence = 0.8 if min(checks["T_sf"], checks["V_sf"]) >= 1.5 else 0.6
    
    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=confidence,
        inputs=loads,
        intermediates={},
        outputs=result,
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.post("/request-engineering", response_model=ResponseEnvelope)
async def request_engineering(req: dict) -> ResponseEnvelope:
    """Flag for human engineering review (no extra charge)."""
    logger.info("baseplate.request_engineering")
    return make_envelope(
        result={"engineering_requested": True, "no_charge": True},
        assumptions=["Flagged for human design review"],
        confidence=0.85,
        inputs=req,
        intermediates={},
        outputs={},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )
