"""
sign_types.py -- Canonical sign type taxonomy and warehouse path resolution.

Single source of truth for:
- Warehouse data paths (CSV, DuckDB)
- Sign type alias mapping (human-readable names to warehouse codes)
- Sign type code expansion (input code -> all related codes)
- Filename keyword -> estimator type mapping (for G: drive file classification)

Every module that needs sign type aliases or CSV/DB paths imports from here.
Do NOT duplicate these mappings elsewhere.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


# -- Warehouse CSV Path Resolution ------------------------------------------------

def _env_or_default(key: str, defaults: list[str]) -> list[Path]:
    """Return env-configured path first, then hardcoded fallbacks."""
    env_val = os.environ.get(key, "")
    paths = []
    if env_val:
        paths.append(Path(env_val))
    for d in defaults:
        paths.append(Path(d))
    return paths


WAREHOUSE_CSV_PATHS = _env_or_default("SIGNX_WAREHOUSE_CSV", [
    r"C:\Scripts\signx-warehouse\warehouse\raw\so_contracts_parsed.csv",
    r"C:\Scripts\SignX\Keyedin\warehouse\warehouse\raw\so_contracts_parsed.csv",
])

QUOTE_CSV_PATHS = _env_or_default("SIGNX_QUOTE_CSV", [
    r"C:\Scripts\signx-warehouse\warehouse\raw\quote_status_report.csv",
    r"C:\Scripts\SignX\Keyedin\warehouse\warehouse\raw\quote_status_report.csv",
])


def find_warehouse_csv() -> Optional[Path]:
    """Return the first existing warehouse CSV path, or None."""
    for p in WAREHOUSE_CSV_PATHS:
        if p.exists():
            return p
    return None


def find_quote_csv() -> Optional[Path]:
    """Return the first existing quote CSV path, or None."""
    for p in QUOTE_CSV_PATHS:
        if p.exists():
            return p
    return None


WAREHOUSE_DB_PATHS = _env_or_default("SIGNX_WAREHOUSE_DB", [
    r"C:\Scripts\signx-warehouse\warehouse\signx.duckdb",
])


def find_warehouse_db() -> Optional[Path]:
    """Return the first existing DuckDB warehouse path, or None."""
    for p in WAREHOUSE_DB_PATHS:
        if p.exists():
            return p
    return None


# -- Sign Type Alias Map ----------------------------------------------------------
#
# Keys are human-friendly group names.
# Values are warehouse sales codes (from KeyedIn so_contracts).
#
# This is the CANONICAL list. Expand it here when new types appear
# in the warehouse data. All consumers import from this module.

SIGN_TYPE_ALIASES: dict[str, list[str]] = {
    "CHANNEL_LETTER":  ["CLLIT", "CLNON", "CHANNL"],
    "MONUMENT":        ["MONDF", "MONSF"],
    "PYLON":           ["POLLIT", "POLNON"],
    "CABINET":         ["ALULIT", "ALUNON", "BLDILL", "BLDNON"],
    "AWNING":          ["AWNNON", "AWNLIT", "AWNILL", "AWNREC"],
    "DIRECTIONAL":     ["DIRECT"],
    "DIMENSIONAL":     ["GEMINI"],
    "REMOVAL":         ["REMOVAL", "REMOVE"],
    "NEON":            ["NEON", "NEONRP"],
    "ELECTRONIC":      ["EMC", "EMCLED"],
    "BANNER":          ["BANNER", "BNNR"],
    "VINYL":           ["VINYL", "VNLGR"],
    "VEHICLE":         ["VHCLWR", "VHCLLT"],
    "WINDOW":          ["WNDGR", "WNDLT"],
    "POST_AND_PANEL":  ["P&P", "PNLNON"],
    "PROJECTING":      ["PROJLT", "PROJNON"],
    "WALL_SIGN":       ["WLLIT", "WLNON"],
    "DESIGN":          ["DESIGN"],
    "SURVEY":          ["SURVEY"],
    "INSTALL_ONLY":    ["INSTL"],
    # Additional types from warehouse taxonomy (38 distinct codes total)
    "LED_SIGN":        ["LED", "ILLUM"],
    "RACEWAY_TRIM":    ["RTLT"],
    "FLAT_FACE":       ["FFACE"],
    "FORMED_LETTER":   ["FORMED", "LETPLA"],
    "STEEL_SIGN":      ["STLLIT", "STLNON"],
    "PRINT_GRAPHICS":  ["PRNGRA", "BANPRN", "BANSTK", "JOBPRN"],
    "OVERLAY":         ["OVRLAY", "CASMET"],
    "ADA_SIGN":        ["ADA"],
    "FLAG":            ["FLAG"],
    "MAGNET":          ["MAGNET"],
    "JOB_VINYL":       ["JOBVIN"],
    "BLANK":           ["BLANK"],
}


def expand_sign_type(code: str) -> set[str]:
    """Given a sign type code or alias name, return all related codes.

    Examples:
        expand_sign_type("CLLIT")           -> {"CLLIT", "CLNON", "CHANNL"}
        expand_sign_type("CHANNEL_LETTER")  -> {"CLLIT", "CLNON", "CHANNL"}
        expand_sign_type("UNKNOWN")         -> {"UNKNOWN"}
    """
    upper = code.upper().strip()
    result = {upper}

    # Check if it's a group name
    if upper in SIGN_TYPE_ALIASES:
        result.update(SIGN_TYPE_ALIASES[upper])
        return result

    # Check if it's a code within a group
    for _group, codes in SIGN_TYPE_ALIASES.items():
        if upper in codes:
            result.update(codes)
            return result

    return result


def sign_type_label(code: str) -> str:
    """Return the human-friendly group name for a sign type code.

    Examples:
        sign_type_label("CLLIT")   -> "Channel Letter"
        sign_type_label("MONDF")   -> "Monument"
        sign_type_label("FOOBAR")  -> "FOOBAR"
    """
    upper = code.upper().strip()

    if upper in SIGN_TYPE_ALIASES:
        return upper.replace("_", " ").title()

    for group, codes in SIGN_TYPE_ALIASES.items():
        if upper in codes:
            return group.replace("_", " ").title()

    return code


# -- Filename Keyword -> Estimator Type Map ------------------------------------
#
# Maps keywords found in G: drive filenames to estimator type categories.
# Used by drawing_search.py and project_files.py for file classification.
# Keep entries lowercase for case-insensitive matching.

FILENAME_TYPE_MAP: dict[str, str] = {
    "monument":     "monument",
    "mon face":     "monument",
    "mon ":         "monument",
    "pylon":        "pylon",
    "pole sign":    "pylon",
    "pole face":    "pylon",
    "channel let":  "channel_letter",
    "channel lit":  "channel_letter",
    "letters":      "channel_letter",
    "emc":          "pylon",
    "emcenter":     "pylon",
    "electronic":   "pylon",
    "awning":       "awning",
    "canopy":       "awning",
    "cabinet":      "cabinet",
    "lightbox":     "cabinet",
    "light box":    "cabinet",
    "dimensional":  "dimensional",
    "gemini":       "dimensional",
    "flat cut":     "dimensional",
    "directional":  "directional",
    "wayfinding":   "directional",
    "info panel":   "directional",
    "removal":      "removal",
    "remove":       "removal",
}
