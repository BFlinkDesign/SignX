"""Direct burial foundation design with versioned calibration constants."""

from __future__ import annotations

from typing import Dict, Tuple


CALIBRATION_VERSION = "footing_v1"
K_FACTOR = 0.15


def design_embed(F_lbf: float, M_inlb: float, constraints: Dict[str, float] | None = None) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Design direct-burial footing with monotonic properties."""
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


def solve_footing_interactive(diameter_ft: float, M_pole_kipft: float, soil_psf: float, num_poles: int = 1) -> float:
    """Compute minimum depth for given diameter (interactive mode).
    
    Monotonic: diameter↓ ⇒ depth↑
    """
    import math
    
    K = K_FACTOR  # calibration constant (versioned)
    M_total = M_pole_kipft if num_poles == 1 else M_pole_kipft * 0.5  # per-support for multi
    
    depth_ft = K * M_total / ((diameter_ft ** 3) * (soil_psf / 1000.0))
    depth_in = max(36.0, depth_ft * 12.0)
    
    return round(depth_in, 1)


