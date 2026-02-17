"""
HSS/tube member checks — thin wrapper around supports_pipe.py.

All AISC 360-22 LRFD logic lives in supports_pipe.check_section() and
supports_pipe.select_member().  This module re-exports both functions so
that callers using the 'tube' or 'HSS' terminology still find a coherent
module without any duplicated calculation code.

Typical usage
-------------
from apex_signcalc.supports_tube import check_section, select_member

passed, audit = check_section(sec, M_inlb=240_000, V_lbf=3_000, L_in=144)
best, audit   = select_member(M_inlb=240_000, V_lbf=3_000, L_in=144,
                               families=["HSS_square"])
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
