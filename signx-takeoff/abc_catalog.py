"""ABC catalog lookup helpers — pure, side-effect-free functions for abc_engine.py.

Per the Engineering Department charter (Option C strategy):
- Sibling module to led_catalog.py (precedent at abc_engine.py:111-119)
- Read-only lookups against signx-takeoff/data/abc_catalog.json
- Opt-in via env var ABC_CATALOG_ENRICHMENT — default OFF preserves all 252 existing tests
- Fail-soft: every lookup returns None if catalog is missing or part is unknown

Usage in abc_engine.calculate_materials():

    from abc_catalog import lookup_channel_letter_return, ENRICH

    # ... existing BOM build ...
    if ENRICH:
        ret = lookup_channel_letter_return(return_depth_inches)
        if ret:
            bom[-1]["catalog_part"] = ret["eagle_pn"]
            bom[-1]["catalog_name"] = ret["name"]
            bom[-1]["vendor"] = "abc"

When ENRICH is off, behavior is byte-identical to current — no test perturbation.
When ENRICH is on, BOM lines gain catalog metadata but core dict shape is preserved.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

# Opt-in flag — set ABC_CATALOG_ENRICHMENT=on to activate. Default OFF.
ENRICH: bool = os.environ.get("ABC_CATALOG_ENRICHMENT", "off").lower() == "on"

# Catalog sits next to abc_engine.py at signx-takeoff/data/abc_catalog.json
_CATALOG_PATH = Path(__file__).resolve().parent / "data" / "abc_catalog.json"


@lru_cache(maxsize=1)
def _catalog() -> dict:
    """Load the ABC catalog once. Returns {} if file missing — caller falls back to defaults."""
    if not _CATALOG_PATH.exists():
        return {}
    try:
        return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


# =============================================================================
#  M2 — Channel letter return BOM line by depth
# =============================================================================

# Per the warehouse audit, ABC's Channelume is in 3 standard depths.
# Eagle SKU 202-0710 is the Type IV Retainer used as generic trim today —
# the actual Channelume part numbers need to come from a future Eagle SKU
# import (200-EXT range). For now we return the catalog name + depth.

def lookup_channel_letter_return(depth_in: float | None) -> dict | None:
    """Pick the right Channelume profile for a given letter return depth.

    Returns: {"code": "CHANNELUME5", "depth_in": 5, "name": "5\" Channelume",
              "eagle_pn": None}
    or None if depth is too small for an extruded return (use coil aluminum instead).
    """
    if not ENRICH or depth_in is None:
        return None
    if depth_in < 3.5:
        return None  # use coil aluminum (205-0111) — too shallow for Channelume
    catalog = _catalog().get("channel_letter_returns", [])
    if not catalog:
        return None
    # Pick the closest equal-or-larger Channelume depth
    sorted_returns = sorted(
        (r for r in catalog if r.get("depth_in") is not None),
        key=lambda r: r["depth_in"],
    )
    for r in sorted_returns:
        if r["depth_in"] >= depth_in:
            return {
                "code": r["code"],
                "depth_in": r["depth_in"],
                "name": r["name"],
                "eagle_pn": None,  # TODO: map to Eagle 200-EXT range when warehouse confirms
                "vendor": "abc",
            }
    # Letter is deeper than 8" — return the deepest available (8")
    deepest = sorted_returns[-1]
    return {
        "code": deepest["code"],
        "depth_in": deepest["depth_in"],
        "name": deepest["name"],
        "eagle_pn": None,
        "vendor": "abc",
        "note": f"depth {depth_in}\" exceeds catalog max — using {deepest['code']}",
    }


# =============================================================================
#  M3 — Raceway extrusion BOM line
# =============================================================================

def lookup_raceway_extrusion(profile: str | None = None) -> dict | None:
    """Pick a raceway extrusion + cover. Default returns ABC's standard Raceway profile.

    For Excellart 7\" raceways, abc_engine should call out to bridge's vendor catalog
    via /catalog/parts/{vendor}/{sku} — this helper is the ABC fallback.
    """
    if not ENRICH:
        return None
    raceways = _catalog().get("raceways", [])
    if not raceways:
        return None
    # Prefer "Raceway Bottoms" or the first listed
    for r in raceways:
        if "Raceway Bottoms" in str(r):
            return {"code": "ABC-RACEWAY-BOTTOM", "name": str(r), "eagle_pn": None, "vendor": "abc"}
    return {"code": "ABC-RACEWAY", "name": str(raceways[0]), "eagle_pn": None, "vendor": "abc"}


# =============================================================================
#  M5 — Retainer typing + finish multipliers
# =============================================================================

# Finish multiplier — applied to retainer cost lines when bronze (or other)
# finishes are specified. ABC list-price ratios from the warehouse:
#   Mill = 1.0 baseline
#   Bronze = ~1.34x (per 1971 vs 1972N price ratio in distributor data)
FINISH_MULTIPLIER: dict[str, float] = {
    "default": 1.0,
    "mill": 1.0,
    "bronze": 1.34,
    "black": 1.20,
    "anodized": 1.15,
}


def lookup_retainer(
    abc_type_code: str | None = None,
    finish: str = "mill",
    is_vhb: bool = False,
    is_radius: bool = False,
) -> dict | None:
    """Resolve a retainer profile by ABC type code + finish.

    Returns: {"code": "Type IV Flat Retainer (Mill Finish)",
              "abc_type_code": "IV", "finish": "mill",
              "finish_multiplier": 1.0, "eagle_pn": "202-0710",
              "vendor": "abc"}
    """
    if not ENRICH:
        return None
    retainers = _catalog().get("retainers", [])
    if not retainers:
        return None
    finish_norm = finish.lower() if finish else "mill"
    type_norm = abc_type_code.upper() if abc_type_code else None

    candidates = []
    for r in retainers:
        # If caller specified a type code, require an exact match
        # (untyped retainers do NOT match "IV" — fixes silent fallthrough bug)
        if type_norm:
            r_type = r.get("abc_type_code")
            if not r_type or r_type.upper() != type_norm:
                continue
        rfinish = (r.get("finish") or "mill").lower()
        if rfinish != finish_norm and rfinish != "default":
            continue
        if is_vhb and not r.get("is_vhb"):
            continue
        if is_radius and not r.get("is_radius"):
            continue
        candidates.append(r)

    if not candidates:
        return None
    chosen = candidates[0]
    eagle_pn = "202-0710" if chosen.get("abc_type_code") == "IV" else None
    return {
        "code": chosen["name"],
        "abc_type_code": chosen.get("abc_type_code"),
        "finish": chosen.get("finish"),
        "finish_multiplier": FINISH_MULTIPLIER.get(finish_norm, 1.0),
        "is_vhb": bool(chosen.get("is_vhb")),
        "is_radius": bool(chosen.get("is_radius")),
        "eagle_pn": eagle_pn,
        "vendor": "abc",
    }


# =============================================================================
#  M6 — Tubing catalog with gauge specs
# =============================================================================

def lookup_tubing(
    nominal_size: str | None = None,
    wall_thousandths: str | None = None,
    material: str = "steel",
    shape: str = "square",
) -> dict | None:
    """Resolve a tubing profile (steel/alum, square/round/rect) by size + wall.

    Returns: {"code": "2.5 x .141 Steel Square Tube", "nominal_size": "2.5",
              "wall_thousandths": "141", "material": "steel", "shape": "square",
              "vendor": "abc"}
    """
    if not ENRICH:
        return None
    tubing = _catalog().get("tubing", [])
    if not tubing:
        return None
    mat_norm = material.lower() if material else None
    shape_norm = shape.lower() if shape else None

    for t in tubing:
        if mat_norm and t.get("material") != mat_norm:
            continue
        if shape_norm and t.get("shape") != shape_norm:
            continue
        if nominal_size and t.get("nominal_size") != nominal_size:
            continue
        if wall_thousandths and t.get("wall_thousandths") != wall_thousandths:
            continue
        return {
            "code": t["name"],
            "nominal_size": t.get("nominal_size"),
            "wall_thousandths": t.get("wall_thousandths"),
            "material": t.get("material"),
            "shape": t.get("shape"),
            "eagle_pn": None,
            "vendor": "abc",
        }
    return None


# =============================================================================
#  M7 — Material complexity multiplier
# =============================================================================

def complexity_multiplier(
    material_count: int = 1,
    paint_colors: int = 1,
    has_radius: bool = False,
) -> float:
    """ABC's complexity factors per face shape (verified from bill_mat_nm.abc):
       METAL_RECTANGLE × 1.05, METAL_TRAPEZOID × 1.05,
       METAL_IRREGULAR × 1.10, METAL_INTRICATE × 1.20.

    We don't expose those raw multipliers (they're applied inside abc_engine
    formulas already). This helper composes the EXTERNAL multiplier added on
    top for: many materials + many colors + radius corners.
    """
    if not ENRICH:
        return 1.0
    mult = 1.0
    if material_count >= 5:
        mult *= 1.10
    elif material_count >= 3:
        mult *= 1.05
    if paint_colors >= 3:
        mult *= 1.08
    elif paint_colors >= 2:
        mult *= 1.04
    if has_radius:
        mult *= 1.05
    return round(mult, 4)


# =============================================================================
#  Public API exposed to abc_engine.py
# =============================================================================

__all__ = [
    "ENRICH",
    "FINISH_MULTIPLIER",
    "complexity_multiplier",
    "lookup_channel_letter_return",
    "lookup_raceway_extrusion",
    "lookup_retainer",
    "lookup_tubing",
]
