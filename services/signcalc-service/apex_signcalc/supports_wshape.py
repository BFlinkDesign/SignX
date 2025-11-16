from __future__ import annotations

from typing import Dict, Tuple

from .sections import Section


def check_section(sec: Section, M_inlb: float, V_lbf: float, L_in: float) -> Tuple[bool, Dict[str, float]]:
    fb = M_inlb / max(sec.Sx_in3, 1e-6)
    allow = 0.6 * sec.fy_psi
    ir = fb / allow
    E = 29_000_000.0
    delta_in = (V_lbf * (L_in ** 3)) / (48.0 * E * max(sec.Ix_in4, 1e-6))
    return ir <= 1.0 and delta_in <= L_in / 120.0, {"IR_bend": ir, "DEF_in": delta_in}


