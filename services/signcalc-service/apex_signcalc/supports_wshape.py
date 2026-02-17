"""
W-shape member checks — thin wrapper around supports_pipe.py.

All AISC 360-22 LRFD logic lives in supports_pipe.check_section() and
supports_pipe.select_member().  This module re-exports both functions so
that callers using the 'W-shape' or 'wide-flange' terminology still find
a coherent module without any duplicated calculation code.

The W-shape family is handled inside check_section() via the branch:
    if sec.family.lower() == "w": _Mn_W_shape(...)

which implements full F2 (LTB + flange LB) provisions.

Typical usage
-------------
from apex_signcalc.supports_wshape import check_section, select_member

passed, audit = check_section(sec, M_inlb=480_000, V_lbf=6_000, L_in=192,
                               load_type="simple_point")
best, audit   = select_member(M_inlb=480_000, V_lbf=6_000, L_in=192,
                               families=["W"], load_type="simple_point")
"""
from __future__ import annotations

# Re-export the full public API from the canonical implementation.
from .supports_pipe import (  # noqa: F401
    check_section,
    select_member,
    PHI_B,
    PHI_V,
    PHI_C,
    E_PSI,
    DEF_LIMIT,
)

__all__ = [
    "check_section",
    "select_member",
    "PHI_B",
    "PHI_V",
    "PHI_C",
    "E_PSI",
    "DEF_LIMIT",
]
