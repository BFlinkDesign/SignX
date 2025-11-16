"""Pole/support selection endpoints with dynamic filtering."""

from __future__ import annotations

import sys
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException

# Add signcalc-service to path for imports
_signcalc_path = Path(__file__).parent.parent.parent.parent.parent / "signcalc-service"
if str(_signcalc_path) not in sys.path:
    sys.path.insert(0, str(_signcalc_path))

try:
    from apex_signcalc.sections import Section, catalogs_for_order
except ImportError:
    # Fallback for development
    from dataclasses import dataclass
    from typing import List

    @dataclass
    class Section:
        family: str
        designation: str
        weight_lbf: float
        Sx_in3: float
        Ix_in4: float
        fy_psi: float

    def catalogs_for_order(order):
        return []

from ..common.models import make_envelope
from ..common.caching import cache_result
from ..common.envelope import calc_confidence
from ..deps import get_code_version, get_model_config
from ..schemas import ResponseEnvelope, add_assumption

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/signage/common", tags=["poles"])


def _check_section_strength(section: Section, Mu_required_kipin: float, phi: float = 0.9) -> bool:
    """Pre-filter by strength: φMn >= Mu_required."""
    Mn_kipin = section.Sx_in3 * (section.fy_psi / 1000.0)  # Basic plastic moment
    phiMn = phi * Mn_kipin
    return phiMn >= Mu_required_kipin


def _check_section_deflection(section: Section, L_in: float, Delta_allow_in: float, E_psi: float = 29000000.0) -> bool:
    """Pre-filter by deflection: Δ <= Δ_allow."""
    # Simplified: assume point load at tip P, Δ = PL³/(3EI)
    # Conservative check using Ix
    if section.Ix_in4 <= 0:
        return False
    # For sign loads, use simplified check
    return True  # Placeholder - would need actual load magnitude


@router.post("/poles/options", response_model=ResponseEnvelope)
async def pole_options(req: dict) -> ResponseEnvelope:
    """Get filtered list of feasible pole options.
    
    Body: {loads: {M_kipin, V_kip}, prefs: {family, steel_grade, sort_by}, num_poles: int, material: str, height_ft: float}
    Returns: Filtered list starting with minimum feasible ("value engineered")
    """
    logger.info("poles.options", family=req.get("prefs", {}).get("family"))
    assumptions: list[str] = []
    
    num_poles = int(req.get("num_poles", 1))
    material = req.get("material", "steel")
    height_ft = float(req.get("height_ft", 0.0))
    loads = req.get("loads", {})
    Mu_required_kipin = float(loads.get("M_kipin", 100.0)) / num_poles  # Per-pole moment
    prefs = req.get("prefs", {})
    family_order = prefs.get("family", ["pipe", "tube", "W"])
    sort_by = prefs.get("sort_by", "weight")  # weight, modulus, size
    
    # Material lock validation
    if material == "aluminum" and height_ft > 15.0:
        raise HTTPException(
            status_code=422,
            detail="Aluminum supports limited to 15 ft height per industry practice"
        )
    
    add_assumption(assumptions, f"Material: {material}, num_poles: {num_poles}, Mu_per_pole={Mu_required_kipin:.1f} kip-in")
    
    # Load catalogs
    catalog = catalogs_for_order(family_order)
    
    # Pre-filter by strength
    feasible = [s for s in catalog if _check_section_strength(s, Mu_required_kipin)]
    
    if not feasible:
        add_assumption(assumptions, "No feasible sections found for given loads")
        confidence = calc_confidence(assumptions)
        return make_envelope(
            result={"options": [], "recommended": None},
            assumptions=assumptions,
            confidence=confidence,
            inputs=req,
            intermediates={"catalog_size": len(catalog)},
            outputs={"feasible_count": 0},
        )
    
    # Sort by preference
    if sort_by == "modulus":
        feasible.sort(key=lambda s: s.Sx_in3, reverse=True)
    elif sort_by == "size":
        feasible.sort(key=lambda s: s.weight_lbf, reverse=True)
    else:  # weight (default - "value engineered")
        feasible.sort(key=lambda s: s.weight_lbf)
    
    # Format results (rounding handled by make_envelope)
    options = [
        {
            "family": s.family,
            "designation": s.designation,
            "weight_lbf": s.weight_lbf,
            "Sx_in3": s.Sx_in3,
            "Ix_in4": s.Ix_in4,
            "fy_psi": s.fy_psi,
        }
        for s in feasible
    ]
    
    result = {
        "options": options,
        "recommended": options[0] if options else None,
        "feasible_count": len(feasible),
    }
    
    add_assumption(assumptions, f"Filtered {len(feasible)}/{len(catalog)} sections by strength")
    confidence = calc_confidence(assumptions)
    
    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=confidence,
        inputs=req,
        intermediates={"catalog_size": len(catalog), "Mu_per_pole": Mu_required_kipin},
        outputs={"feasible_count": len(feasible)},
    )

