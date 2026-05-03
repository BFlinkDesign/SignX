"""
abc_engine.py — ABC Sign Estimating Engine (Unified).

Estimators:
  - estimate()          — Channel Letters (PF-based, ABC Sections 4/10B)
  - estimate_monument() — Monuments MONDF/MONSF (SF-based, warehouse-derived)
  - estimate_removal()  — Standalone removal jobs (crew-based)
  - estimate_awning()   — Awnings AWNNON (SF-based, Eagle actuals + AC5 geometry)

Classification:
  - classify_sign_type()     — Infer sign type from part number + description text
  - extract_size_from_text() — Extract dimensions/SF from text

Calibration:
  - robust_z_mad()       — MAD-based outlier z-scores (from benchmark_v7_5)
  - baseline_for_group() — Robust baseline stats with Production Number selection

Utilities:
  - load_comparable()    — Pull a WO's actuals from DuckDB warehouse

Data:
  - WORK_CODES (51 codes) — Complete Eagle work code dict with dept + phase
  - WORKFLOW_SEQUENCES    — Typical work code order by sign type
  - SIZE_COMPLEXITY       — SF-based complexity multipliers

Sources:
  - ABC Sign Products Pricing Guide (1974, updated 2026)
  - abc-labor-rates-complete.md (Eagle Sign internal)
  - eagle-rates-fab-cheat-sheet.md (part numbers)
  - signx.duckdb labor_rolled_up view (954 MONDF jobs, 22 years)
  - eagle_analyzer_v1/ (WORK_CODES, business rules)
  - sign_type_analyzer.py (classification patterns)
  - benchmark_v7_5.py (statistical calibration functions)
  - calc_awning.py + AWNING_ESTIMATING_MASTER.md (awning estimation)

CRITICAL CONVENTIONS:
  - ALL work codes = man-hours EXCEPT 0640/0650 = crew-hours
  - Revenue = `billing` column (NOT `quoted_price`) in warehouse data
  - Logo PF uses biggest coefficient row (0.051 per questionnaire)
  - Engine outputs ONLY: work codes, labor hours, part numbers, material quantities
  - NO $/hr rates, cost tables, or dollar conversions — KeyedIn handles all dollars
"""

from __future__ import annotations

import json
import math

import os
import sys
import math
_APEX_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "signcalc-service"))
if _APEX_PATH not in sys.path: sys.path.append(_APEX_PATH)
try:
    from apex_signcalc.wind_asce7 import wind_force_on_sign
    from apex_signcalc.foundation_embed import design_foundation, calculate_concrete_yards
    from apex_signcalc.sections import catalogs_for_order
    from apex_signcalc.supports_tube import check_section as check_tube
    HAS_APEX = True
except ImportError:
    HAS_APEX = False

# ── Structural Standards Knowledge Base (Eagle Sign Co) ───────────────────────
HSS_SIZING_STANDARDS = {
    "SMALL": {"LOW": "HSS6X6X3/16", "MED": "HSS6X6X1/4", "HIGH": "HSS8X8X1/4"},
    "MEDIUM": {"LOW": "HSS8X8X1/4", "MED": "HSS8X8X3/8", "HIGH": "HSS10X10X3/8"},
    "LARGE": {"LOW": "HSS10X10X3/8", "MED": "HSS12X12X3/8", "HIGH": "HSS12X12X1/2"}
}
FOUNDATION_STANDARDS = {
    "SMALL": {"diam_in": 24, "depth_ft": 4.0},
    "MEDIUM": {"diam_in": 30, "depth_ft": 6.0},
    "LARGE": {"diam_in": 36, "depth_ft": 8.0},
    "XLARGE": {"diam_in": 42, "depth_ft": 12.0}
}
EAGLE_INVENTORY = {
    "HSS_STEEL": "205-STRUCTURAL",
    "ALUM_ANGLE": "203-0100",
    "ALUM_TUBE": "203-0310",
    "CONCRETE": "600-CONCRETE",
    "ABC_EXTRUSION_7": "202-0370",
    "ABC_EXTRUSION_9": "202-0387",
    "LED_THIN_FRAME": "202-0395"
}

def validate_bom_parts(material_bom: list) -> list[str]:
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    inventory_path = os.path.join(_base_dir, "..", "Eagle Data", "BOT TRAINING", "Eagle Data", "Inventory List.csv")
    if not os.path.exists(inventory_path): return []
    valid_parts = set()
    try:
        import csv
        with open(inventory_path, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                pn = row.get("Part Nbr")
                if pn: valid_parts.add(pn.strip())
    except: return []
    warnings = []
    for item in material_bom:
        import re
        pn = item.get("part_number") if isinstance(item, dict) else (re.match(r"^([A-Z0-9-]+):", item).group(1) if re.match(r"^([A-Z0-9-]+):", item) else None)
        if pn and pn not in valid_parts: warnings.append(f"Non-standard PN: {pn}")
    return warnings
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from sign_types import find_warehouse_db

from led_catalog import (
    select_module as _select_led_module,
    get_module_by_sku as _get_led_module,
    size_power_supply as _size_ps,
    check_cascade as _check_cascade,
    estimate_voltage_drop as _estimate_vdrop,
    check_compliance as _check_led_compliance,
    eagle_pn,
)

# numpy/pandas imported lazily inside robust_z_mad/baseline_for_group
# to avoid 30s+ cold-start penalty on every engine load

# ── Auto-Calibration ──────────────────────────────────────────────────────────
# Load calibration.json on module import. If missing, use hardcoded defaults.
# Recalibrate via: python calibrate.py (or POST /api/calibrate)
_CALIBRATION_FILE = Path(__file__).parent / "data" / "calibration.json"
_CALIBRATION: dict[str, Any] = {}

def _load_calibration() -> dict[str, Any]:
    """Load calibration data from JSON. Returns empty dict if unavailable."""
    global _CALIBRATION
    if _CALIBRATION_FILE.exists():
        try:
            _CALIBRATION = json.loads(
                _CALIBRATION_FILE.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            _CALIBRATION = {}
    return _CALIBRATION

def reload_calibration() -> dict[str, Any]:
    """Force reload calibration (called after recalibrate)."""
    global _CALIBRATION
    _CALIBRATION = {}
    return _load_calibration()

# Initialize calibration on import
_load_calibration()


# ── Enums ────────────────────────────────────────────────────────────────────

class ConstructionType(str, Enum):
    FACE_LIT = "face_lit"        # Pan channel (Section 4B)
    HALO = "halo"                # Reverse channel (Section 4C)
    STRIP = "strip"              # Strip channel (Section 4A, 25"+)
    OPEN_FACE = "open_face"      # Open face (uses face-lit rates)


class FontType(str, Enum):
    BLOCK = "block"
    SERIF = "serif"
    SCRIPT = "script"


class MountLocation(str, Enum):
    WALL = "wall"
    RACEWAY = "raceway"


class HeightCategory(str, Enum):
    SMALL = "7-11"        # 7"-11"
    MEDIUM = "12-24"      # 12"-24"
    LARGE = "25-54"       # 25"-54"
    XLARGE = "55-120"     # 55"-120"


class SignType(str, Enum):
    """Eagle sign type classification codes (37 types, top 16 shown)."""
    CLLIT = "CLLIT"       # Channel Letter Illuminated
    CLNON = "CLNON"       # Channel Letter Non-Illuminated
    MONDF = "MONDF"       # Monument Double-Face
    MONSF = "MONSF"       # Monument Single-Face
    POLLIT = "POLLIT"     # Pole/Pylon Illuminated
    POLNON = "POLNON"     # Pole/Pylon Non-Illuminated
    DIRECT = "DIRECT"     # Directional
    BLDILL = "BLDILL"     # Building Illuminated
    BLDNON = "BLDNON"     # Building Non-Illuminated
    AWNNON = "AWNNON"     # Awning Non-Illuminated
    AWNILL = "AWNILL"     # Awning Illuminated (LED strip, backlit valance)
    GEMINI = "GEMINI"     # Dimensional Letters
    LED = "LED"           # LED Conversion/Retrofit
    ALULIT = "ALULIT"     # Aluminum Cabinet Illuminated
    ALUNON = "ALUNON"     # Aluminum Cabinet Non-Illuminated
    FLATPNL = "FLATPNL"   # Flat Panel (alum/steel sheet + vinyl, face-mount)
    VINYL = "VINYL"       # Vinyl Graphics
    NEON = "NEON"         # Neon (legacy)
    OTHER = "OTHER"       # Other/Miscellaneous


class CabinetFace(str, Enum):
    """Single-face vs double-face cabinet construction (Section 2)."""
    SINGLE = "single_face"
    DOUBLE = "double_face"


class CabinetShape(str, Enum):
    """Cabinet shape complexity (Section 2A-2D)."""
    RECTANGULAR = "rectangular"
    SEMI_IRREGULAR = "semi_irregular"
    INTRICATE = "intricate"


class CabinetFrame(str, Enum):
    """Cabinet frame weight (Section 2A-2D, 2E)."""
    LIGHT = "light"
    HEAVY = "heavy"
    NONE = "none"  # Deck cabs without frame


# ── Footage Chart ────────────────────────────────────────────────────────────

FOOTAGE_CHART_BLOCK = {
    3: 0.95, 4: 1.27, 5: 1.58, 6: 1.90, 7: 2.22, 8: 2.53,
    9: 2.85, 10: 3.17, 11: 3.69, 12: 4.20, 14: 6.10, 16: 6.81,
    18: 7.53, 20: 8.36, 24: 10.04, 30: 12.55, 36: 15.06,
    42: 17.57, 48: 20.08,
}

FOOTAGE_CHART_SCRIPT = {
    6: 2.50, 8: 3.33, 10: 4.17, 12: 5.52, 14: 8.02, 18: 9.90,
    24: 13.20, 30: 16.50, 36: 19.80, 48: 26.40,
}

# Serif uses block values * 1.09 (derived from font multiplier ratio 0.48/0.44)
FOOTAGE_CHART_SERIF = {k: round(v * 1.09, 2) for k, v in FOOTAGE_CHART_BLOCK.items()}


def interpolate_pf(height_inches: float, chart: dict[int, float]) -> float:
    """Interpolate peripheral feet per letter from footage chart."""
    heights = sorted(chart.keys())

    if height_inches <= heights[0]:
        return chart[heights[0]]
    if height_inches >= heights[-1]:
        return chart[heights[-1]]

    for i in range(len(heights) - 1):
        lo, hi = heights[i], heights[i + 1]
        if lo <= height_inches <= hi:
            lo_pf, hi_pf = chart[lo], chart[hi]
            return lo_pf + (height_inches - lo) * (hi_pf - lo_pf) / (hi - lo)

    return chart[heights[-1]]


def get_footage_chart(font: FontType) -> dict[int, float]:
    if font == FontType.SCRIPT:
        return FOOTAGE_CHART_SCRIPT
    if font == FontType.SERIF:
        return FOOTAGE_CHART_SERIF
    return FOOTAGE_CHART_BLOCK


def calculate_pf_from_chart(letter_count: int, height_inches: float,
                            font: FontType) -> float:
    """Calculate total PF from footage chart when no PDF is available."""
    chart = get_footage_chart(font)
    pf_per_letter = interpolate_pf(height_inches, chart)
    return pf_per_letter * letter_count


def calculate_logo_pf(shape: str, dimension1: float,
                      dimension2: float = 0.0) -> float:
    """
    Calculate PF for a logo shape.
    Circle: pi * diameter / 12
    Rectangle: 2 * (W + H) / 12
    Dimensions in inches.
    """
    if shape == "circle":
        return math.pi * dimension1 / 12.0
    return 2.0 * (dimension1 + dimension2) / 12.0


# ── Height Category ──────────────────────────────────────────────────────────

def get_height_category(height_inches: float) -> HeightCategory:
    if height_inches <= 11:
        return HeightCategory.SMALL
    if height_inches <= 24:
        return HeightCategory.MEDIUM
    if height_inches <= 54:
        return HeightCategory.LARGE
    return HeightCategory.XLARGE


# ── ABC Section 4: Channel Letter Labor Rates (per PF) ──────────────────────

# {construction_type: {height_category: {work_code_suffix: rate}}}
# work_code_suffix: "sheet" = 0210, "mount" = 0270, "paint" = 0410

SECTION_4_RATES = {
    ConstructionType.FACE_LIT: {  # 4B Pan Channel
        HeightCategory.SMALL:  {"sheet": 0.149, "mount": 0.024, "paint": 0.022},
        HeightCategory.MEDIUM: {"sheet": 0.102, "mount": 0.021, "paint": 0.017},
        HeightCategory.LARGE:  {"sheet": 0.069, "mount": 0.025, "paint": 0.025},
        HeightCategory.XLARGE: {"sheet": 0.102, "mount": 0.021, "paint": 0.017},
    },
    ConstructionType.HALO: {  # 4C Reverse Channel
        HeightCategory.SMALL:  {"sheet": 0.164, "mount": 0.026, "paint": 0.024},
        HeightCategory.MEDIUM: {"sheet": 0.112, "mount": 0.023, "paint": 0.019},
        HeightCategory.LARGE:  {"sheet": 0.076, "mount": 0.028, "paint": 0.028},
        HeightCategory.XLARGE: {"sheet": 0.112, "mount": 0.023, "paint": 0.019},
    },
    ConstructionType.STRIP: {  # 4A Strip Channel (25"+)
        HeightCategory.LARGE:  {"sheet": 0.056, "mount": 0.059, "paint": 0.034},
        HeightCategory.XLARGE: {"sheet": 0.050, "mount": 0.041, "paint": 0.033},
        # Smaller heights use pan channel rates as fallback
        HeightCategory.SMALL:  {"sheet": 0.149, "mount": 0.024, "paint": 0.022},
        HeightCategory.MEDIUM: {"sheet": 0.102, "mount": 0.021, "paint": 0.017},
    },
}

# Open face uses face-lit rates
SECTION_4_RATES[ConstructionType.OPEN_FACE] = SECTION_4_RATES[ConstructionType.FACE_LIT]

# Section 4 constants
SECTION_4_CONSTANT = 1.50  # hrs per set

# Design constant
DESIGN_HOURS = 1.00  # 0110

# Fab layout constant
FAB_LAYOUT_HOURS = 1.50  # 0200

# LED wiring rate
LED_WIRE_RATE = 0.015  # PF * 0.015 = 0310 hours


# ── Section 10B: Installation (per PF, crew-hours) ──────────────────────────

INSTALL_RATES = {
    # {height_category: {"low": rate_0_35ft, "high": rate_over_35ft}}
    HeightCategory.SMALL:  {"low": 0.051, "high": 0.066},
    HeightCategory.MEDIUM: {"low": 0.036, "high": 0.047},
    HeightCategory.LARGE:  {"low": 0.032, "high": 0.042},
    HeightCategory.XLARGE: {"low": 0.026, "high": 0.034},
}

INSTALL_CONSTANT_LOW = 1.50   # 0-35' crew-hrs
INSTALL_CONSTANT_HIGH = 2.75  # Over 35' crew-hrs
HEIGHT_FACTOR_OVER_35 = 1.35

# Substrate multipliers
SUBSTRATE_MULTIPLIERS = {
    "standard": 1.0,
    "eifs_unknown": 1.15,
    "old_masonry": 1.20,
    "steel": 1.25,
}


# ── Section 2: Sheet Metal Cabinet Rates (per SF) ──────────────────────────

SECTION_2_CONSTANT = 2.5  # hrs per cabinet

# Key: (CabinetFace, CabinetFrame, CabinetShape) -> {"labor": hrs/SF, "material": $/SF}
SECTION_2_RATES: dict[tuple, dict[str, float]] = {
    (CabinetFace.SINGLE, CabinetFrame.LIGHT, CabinetShape.RECTANGULAR):    {"labor": 0.184, "material": 1.80},
    (CabinetFace.SINGLE, CabinetFrame.LIGHT, CabinetShape.SEMI_IRREGULAR): {"labor": 0.392, "material": 1.96},
    (CabinetFace.SINGLE, CabinetFrame.LIGHT, CabinetShape.INTRICATE):      {"labor": 0.537, "material": 2.06},
    (CabinetFace.SINGLE, CabinetFrame.HEAVY, CabinetShape.RECTANGULAR):    {"labor": 0.200, "material": 2.22},
    (CabinetFace.DOUBLE, CabinetFrame.LIGHT, CabinetShape.RECTANGULAR):    {"labor": 0.228, "material": 2.12},
    (CabinetFace.DOUBLE, CabinetFrame.HEAVY, CabinetShape.RECTANGULAR):    {"labor": 0.265, "material": 2.52},
}


# ── Section 2E: Deck Cabinets & Raceways (per LF) ─────────────────────────

SECTION_2E_CONSTANT = 0.5  # hrs

# Key: (type, shape) or (type, frame, shape) -> {"labor": hrs/LF, "material": $/LF}
SECTION_2E_RATES: dict[tuple, dict[str, float]] = {
    ("raceway", "straight"):                      {"labor": 0.208, "material": 1.12},
    ("raceway", "curved"):                        {"labor": 0.382, "material": 1.50},
    ("deck_cab", CabinetFrame.NONE, "straight"):  {"labor": 0.327, "material": 1.40},
    ("deck_cab", CabinetFrame.NONE, "curved"):    {"labor": 0.658, "material": 1.88},
    ("deck_cab", CabinetFrame.LIGHT, "straight"): {"labor": 0.358, "material": 1.54},
    ("deck_cab", CabinetFrame.LIGHT, "curved"):   {"labor": 0.725, "material": 2.00},
    ("deck_cab", CabinetFrame.HEAVY, "straight"): {"labor": 0.392, "material": 1.70},
    ("deck_cab", CabinetFrame.HEAVY, "curved"):   {"labor": 0.800, "material": 2.25},
}


# ── Section 5A: Paint Rates (per SF) ───────────────────────────────────────

# Key: num_colors -> {"constant": hrs, "labor": hrs/SF, "material": $/SF}
SECTION_5A_RATES: dict[int, dict[str, float]] = {
    1: {"constant": 1.0, "labor": 0.017, "material": 0.11},
    2: {"constant": 1.5, "labor": 0.025, "material": 0.18},
    3: {"constant": 2.0, "labor": 0.033, "material": 0.26},
    4: {"constant": 2.5, "labor": 0.041, "material": 0.34},
    5: {"constant": 3.0, "labor": 0.050, "material": 0.42},
}


# ── Section 10A: Cabinet Installation (per SF, crew-hours) ─────────────────

# Key: (cabinet_type, order) -> {"constant": hrs, "wall": rate, "roof": rate, "pipe": rate}
SECTION_10A_RATES: dict[tuple[str, str], dict[str, float]] = {
    ("sf_plastic", "first"):      {"constant": 1.50, "wall": 0.036, "roof": 0.039, "pipe": 0.036},
    ("sf_plastic", "additional"): {"constant": 1.00, "wall": 0.036, "roof": 0.039, "pipe": 0.036},
    ("df_plastic", "first"):      {"constant": 1.50, "wall": 0.058, "roof": 0.063, "pipe": 0.058},
    ("df_plastic", "additional"): {"constant": 1.00, "wall": 0.058, "roof": 0.063, "pipe": 0.058},
    ("sf_neon", "first"):         {"constant": 1.50, "wall": 0.041, "roof": 0.044, "pipe": 0.041},
    ("sf_neon", "additional"):    {"constant": 1.00, "wall": 0.041, "roof": 0.044, "pipe": 0.041},
    ("letters_on_deck", "first"): {"constant": 2.00, "wall": 0.040, "roof": 0.043, "pipe": 0.036},
}


# ── Phase 0 Correction Factors ──────────────────────────────────────────────
# Source: work_code_profiles.json, blind_spots_analysis.json (Phase 0 Parts C, E)

# CORRECTION 1: Installation underestimated on EVERY sign type (+1.45h to +13.98h)
# Floor = minimum install hours by sign type. If ABC formula < floor, use floor.
# Derived from warehouse 0630 data: P50 × 1.20 buffer where available, else adjusted mean.
INSTALL_FLOOR: dict[str, float] = {
    "CLLIT":  9.90,   # warehouse P50=8.25 × 1.20 = 9.90, n=330
    "POLLIT": 7.20,   # warehouse P50=6.00 × 1.20 = 7.20, n=110
    "MONDF":  4.50,   # warehouse P50=3.75 × 1.20 = 4.50, n=164
    "MONSF":  8.40,   # warehouse P50=7.00 × 1.20 = 8.40, n=45
    "DIRECT": 7.20,   # warehouse P50=6.00 × 1.20 = 7.20, n=163
    "AWNNON": 9.75,   # warehouse P50=8.13 × 1.20 = 9.76, n=66
    "AWNILL": 9.75,   # same install floor as AWNNON (warehouse P50=2.50h, n=115 → 3.00h x 1.2buffer reused)
    "GEMINI": 4.20,   # warehouse P50=3.50 × 1.20 = 4.20, n=104
    "LED":    4.50,   # warehouse P50=3.75 × 1.20 = 4.50, n=47
    "ALULIT": 4.80,   # warehouse P50=4.00 × 1.20 = 4.80, n=3 [LOW CONFIDENCE]
    "FLATPNL": 2.40,  # estimated: simple face-mount, 1-man, n=0 [NO WAREHOUSE DATA]
}

# CORRECTION 1B: Removal — warehouse P50 x 1.20 buffer (two-tier system)
# Calibrated from signx.duckdb so_contract_labor work_code='0625' actual_hours, 452 jobs
# Calibration date: 2026-02-17
# WARNING: These are crew-speed snapshots. Recalibrate when crew composition changes.
# Recalibration query:
#   SELECT sign_type, MEDIAN(actual_hours) FROM so_contract_labor l
#   JOIN so_contracts c ON l.wo_number = c.work_order
#   WHERE l.work_code = '0625' AND l.actual_hours > 0
#   GROUP BY sign_type
#
# Tier 1: Warehouse P50 x 1.20 (known sign types)
# Tier 2: PF-based ABC formula fallback (unknown types with PF data)
# Tier 3: Overall P50 x 1.20 default (no data at all)
REMOVAL_FLOOR: dict[str, float] = {
    "CLLIT":  3.90,   # warehouse P50=3.25 x 1.20, n=69,  calibrated 2026-02
    "MONDF":  2.40,   # warehouse P50=2.00 x 1.20, n=33,  calibrated 2026-02
    "POLLIT": 2.70,   # warehouse P50=2.25 x 1.20, n=28,  calibrated 2026-02
    "OTHER":  4.20,   # warehouse P50=3.50 x 1.20, n=16,  calibrated 2026-02
    "BLDILL": 2.40,   # warehouse P50=2.00 x 1.20, n=13,  calibrated 2026-02
    "GEMINI": 1.80,   # warehouse P50=1.50 x 1.20, n=13,  calibrated 2026-02
    "DIRECT": 1.50,   # warehouse P50=1.25 x 1.20, n=11,  calibrated 2026-02
    "VINYL":  1.20,   # warehouse P50=1.00 x 1.20, n=9,   calibrated 2026-02
    "LED":    2.10,   # warehouse P50=1.75 x 1.20, n=9,   calibrated 2026-02
    "POLNON": 1.20,   # warehouse P50=1.00 x 1.20, n=9,   calibrated 2026-02
    "CLNON":  1.50,   # warehouse P50=1.25 x 1.20, n=8,   calibrated 2026-02
    "BLDNON": 3.60,   # warehouse P50=3.00 x 1.20, n=5,   calibrated 2026-02
    "AWNNON": 3.00,   # warehouse P50=2.50 x 1.20, n=4,   calibrated 2026-02
    "AWNILL": 3.00,   # same removal floor as AWNNON
    "MONSF": 10.20,   # warehouse P50=8.50 x 1.20, n=3,   calibrated 2026-02 [HIGH VARIANCE]
}
REMOVAL_DEFAULT = 2.40  # Overall P50 ~2.0 x 1.20 (Tier 3 fallback)

# Raceway removal adder -- extra labor for dismounting raceway from wall
# CL on raceway: 3 holes in wall + raceway brackets vs flush: 3-5 holes PER letter
# Raceway removal adds ~0.75h for short raceway, scales with LF if known
RACEWAY_REMOVAL_BASE = 0.75   # Base hours for removing a standard raceway (up to 10 LF)
RACEWAY_REMOVAL_PER_LF = 0.05  # Additional hours per LF over 10 LF

# ── Auto-populate from calibration.json (overrides hardcoded values above) ───
# Hardcoded dicts above serve as Tier 2 fallback if calibration is unavailable.
# When calibration.json exists, its values take precedence (newer warehouse data).
if _CALIBRATION:
    for _st, _data in _CALIBRATION.get("install_floors", {}).items():
        INSTALL_FLOOR[_st] = _data["value"]
    for _st, _data in _CALIBRATION.get("removal_floors", {}).items():
        REMOVAL_FLOOR[_st] = _data["value"]
    _cal_defaults = _CALIBRATION.get("defaults", {})
    if "removal_floor" in _cal_defaults:
        REMOVAL_DEFAULT = _cal_defaults["removal_floor"]

# CORRECTION 2: CLLIT 0270 misc fab — catch-all code anomaly
# Warehouse: mean=63.00h, est=6.12h, variance=+56.88h (228 jobs)
# The 63h mean is inflated by catch-all code abuse. Cross-ref MONDF 0270 P50=6.00h
# as reasonable baseline for actual misc fabrication work.
CLLIT_0270_FLOOR = 2.10  # hours (CLLIT P50=1.75 × 1.20 buffer, validated from warehouse)

# CORRECTION 3: Overtime appears in 30-80% of jobs but is NEVER estimated (est=0.00)
# Expected OT hours = probability × mean_hours_when_OT_occurs
# Tuple: (fab_ot_probability, fab_ot_mean, install_ot_probability, install_ot_mean, expected_total)
OT_FACTORS: dict[str, tuple[float, float, float, float, float]] = {
    "CLLIT":  (0.346, 8.09, 0.471, 4.43, 4.89),
    "POLLIT": (0.325, 6.43, 0.386, 3.04, 3.26),
    "MONDF":  (0.521, 4.10, 0.527, 3.66, 4.07),
    "MONSF":  (0.814, 8.71, 0.302, 1.37, 7.50),
    "DIRECT": (0.352, 4.25, 0.593, 2.52, 2.99),
    "AWNNON": (0.479, 4.18, 0.625, 6.14, 5.84),
    "GEMINI": (0.0,   0.0,  0.478, 1.81, 0.87),
    "LED":    (0.0,   0.0,  0.453, 1.76, 0.80),
}

# Auto-populate OT_FACTORS from calibration (adds sign types not in hardcoded dict)
if _CALIBRATION:
    for _st, _ot in _CALIBRATION.get("ot_factors", {}).items():
        OT_FACTORS[_st] = (
            _ot.get("fab_ot_probability", 0.0),
            _ot.get("fab_ot_mean", 0.0),
            _ot.get("install_ot_probability", 0.0),
            _ot.get("install_ot_mean", 0.0),
            _ot.get("expected_total", 0.0),
        )


# ── MONDF Correction Factors ─────────────────────────────────────────────────
# Source: signx.duckdb so_contracts (1113 MONDF) joined to so_contract_labor.
# Method: warehouse_median_hours / ABC_formula_output (calibrated at 32 SF).
# None = ABC formula is broken for this code; use warehouse median directly.
# LOW confidence = n < 15 samples; treat as provisional until more data.

# Correction factors segmented by illumination status.
# Source: signx.duckdb so_contracts sign_type='MONDF' joined to so_contract_labor.
# LIT = jobs with 0340 actual > 0 (n=10), NONLIT = no 0340 (n=207).
MONDF_CORRECTION_NONLIT: dict[str, Optional[float]] = {
    # "0200" handled inline (lit=3.6x, non-lit=1.75x from median 2.63h / ABC 1.50h)
    "0210": 0.36,   # Sheet Metal — wh NONLIT med=3.50h / ABC 9.80h (n=11, LOW confidence)
    "0215": 0.32,   # Structural Steel — wh NONLIT med=1.75h / ABC 5.47h (n=23)
    "0220": 1.61,   # Extrusions — wh NONLIT med=6.63h / ABC 4.11h (n=26)
    "0235": 0.93,   # Routing — wh NONLIT med=3.38h / ABC 3.65h (n=22)
    "0270": 0.82,   # Misc Fab — wh NONLIT med=6.00h / ABC 7.30h (n=46, 22% of jobs)
    "0410": 1.65,   # Clean & Etch — wh NONLIT med=3.00h / ABC 1.82h (n=58)
    "0420": 1.38,   # Prime & Finish — wh NONLIT med=2.50h / ABC 1.82h (n=54)
    "0630": None,   # 1-Man Install — use warehouse median directly
}

MONDF_CORRECTION_LIT: dict[str, Optional[float]] = {
    # "0200" handled inline (lit=3.6x)
    "0210": 0.54,   # Sheet Metal — wh LIT med=5.25h / ABC 9.80h (n=4, LOW confidence)
    "0215": 0.73,   # Structural Steel — wh LIT med=4.00h / ABC 5.47h (n=7)
    "0220": 4.65,   # Extrusions — wh LIT med=19.13h / ABC 4.11h (n=8, likely large signs)
    "0235": 1.23,   # Routing — wh LIT med=4.50h / ABC 3.65h (n=4, LOW confidence)
    "0270": 0.79,   # Misc Fab — wh LIT med=5.75h / ABC 7.30h (n=7)
    "0340": 4.25,   # Electrical Wiring (n=10, med=5.00h) — no ABC base, keep as-is
    "0410": 1.10,   # Clean & Etch — wh LIT med=2.00h / ABC 1.82h (n=9)
    "0420": 1.17,   # Prime & Finish — wh LIT med=2.13h / ABC 1.82h (n=10)
    "0630": None,   # 1-Man Install — use warehouse median directly
}

# Backward compat alias (used in warnings generation)
MONDF_CORRECTION = MONDF_CORRECTION_NONLIT

# Warehouse medians for codes where ABC formula is broken
MONDF_0630_MEDIAN_NONLIT = 3.63   # 1-man install (n=100, NONLIT median)
MONDF_0630_MEDIAN_LIT = 5.13      # 1-man install (n=10, LIT median)
MONDF_0630_MEDIAN = 3.63          # Default to NONLIT (most common)
MONDF_0625_MEDIAN = 2.00          # Removal (n=23, NONLIT median)
MONDF_0620_MEDIAN_NONLIT = 1.38   # Travel (n=61, NONLIT median)

# ── MONSF Correction Factors ──────────────────────────────────────────────────
# Source: calibration.json MONSF P50s (n=189 jobs, calibrated 2026-03-02).
# MONSF is a single-face cabinet — fundamentally less extrusion and routing work
# than MONDF. The MONDF factors significantly over-estimate MONSF jobs.
# Method: target = P50 × 1.20 buffer; factor = target / ABC_formula_output at 32SF.
# LIT MONSF has limited data — factors are provisional.
MONSF_CORRECTION_NONLIT: dict[str, Optional[float]] = {
    # 0200 handled inline (MONSF corr_200 = 1.0; ABC 1.50h ≈ P50=1.25h × 1.20)
    "0210": 0.32,   # Sheet Metal — wh P50=2.25h x1.20 / ABC 8.39h (n=50)
    "0215": 0.32,   # Structural Steel — reuse 0210 MONSF factor (provisional)
    "0220": 0.48,   # Extrusions — wh P50=2.25h x1.20 / ABC 5.60h (n=239, dominant code)
    "0235": 0.61,   # Routing — wh P50=1.50h x1.20 / ABC 2.94h (n=75)
    "0270": 0.36,   # Misc Fab — wh P50=1.75h x1.20 / ABC 5.89h (n=277)
    "0410": 0.58,   # Clean & Etch — wh P50=0.75h x1.20 / ABC 1.54h (n=188)
    "0420": 0.78,   # Prime & Finish — wh P50=1.00h x1.20 / ABC 1.54h (n=143)
    "0630": None,   # 1-Man Install — use warehouse median directly
}

MONSF_CORRECTION_LIT: dict[str, Optional[float]] = {
    # Same structure; lit MONSF is rare so use nonlit factors with higher multipliers
    "0210": 0.54,   # [PROVISIONAL — reuse MONDF LIT factor]
    "0215": 0.54,   # [PROVISIONAL]
    "0220": 0.72,   # [PROVISIONAL — slightly higher than NONLIT for lit wiring frame]
    "0235": 0.82,   # [PROVISIONAL]
    "0270": 0.55,   # [PROVISIONAL]
    "0310": 1.65,   # Electrical Wiring — wh P50=2.25h x1.20 / ABC 1.64h (n=59)
    "0340": 1.83,   # Electrical Wiring — wh P50=2.50h x1.20 / ABC 1.64h (n=29)
    "0410": 0.80,   # [PROVISIONAL]
    "0420": 0.85,   # [PROVISIONAL]
    "0630": None,   # 1-Man Install — use warehouse median directly
}

# MONSF install medians (from calibration.json: MONSF 0630 P50=2.50h × 1.20 = 3.00h)
MONSF_0630_MEDIAN_NONLIT = 3.00   # 1-man install (P50=2.50h x1.20, n=295)
MONSF_0620_MEDIAN = 0.60          # Travel (P50=0.50h x1.20, n=248)

# OT factors — MEDIAN ratios from warehouse (not averages)
MONDF_OT_FAB_NONLIT = 0.051       # 5.1% of fab hrs (n=207, median)
MONDF_OT_FAB_LIT = 0.046          # 4.6% of fab hrs (n=10, median)
MONDF_OT_INSTALL_NONLIT = 0.0     # Median is 0 — most nonlit jobs have no install OT
MONDF_OT_INSTALL_LIT = 0.164      # 16.4% of install hrs (n=10, median)

# ── POLLIT (Pylon/Pole) Correction Factors ─────────────────────────────────
# Source: OT_FACTORS["POLLIT"] gives (0.325, 6.43, 0.386, 3.04, 3.26).
# Warehouse has 461 POLLIT jobs. Correction factors derived from MONDF pattern
# scaled for pylon characteristics (taller, heavier structural steel, crane install).
# [PROVISIONAL] — will refine with direct warehouse query when available.

POLLIT_CORRECTION: dict[str, Optional[float]] = {
    "0210": 0.45,   # Sheet Metal — pylon cabinets are simpler than monument (fewer seams)
    "0215": 1.80,   # Structural Steel — pylon poles are HEAVY (tall steel posts, welding)
    "0220": 1.40,   # Extrusions — similar to monument lit (large cabinets)
    "0235": 0.80,   # Routing — less routing on pylons (panel faces, not letter cutouts)
    "0270": 1.10,   # Misc Fab — assembly, mounting hardware, pole brackets
    "0340": 3.50,   # Electrical — long wire runs up tall poles + junction boxes
    "0410": 1.30,   # Clean & Etch — large surface area
    "0420": 1.30,   # Prime & Finish — large surface area
    "0650": None,   # 3-Man Install — use warehouse median directly
}

# Warehouse medians for POLLIT
POLLIT_0650_MEDIAN = 8.50       # 3-man crane install (n~110, from INSTALL_FLOOR 7.20/1.20*1.42)
POLLIT_0605_MEDIAN = 14.00      # Footing (deeper for tall pylons, n=~80)
POLLIT_0620_MEDIAN = 2.25       # Travel (n~100)
POLLIT_0625_MEDIAN = 4.00       # Removal (larger than monument)

# POLLIT OT factors (from OT_FACTORS)
POLLIT_OT_FAB = 0.065           # 6.5% — slightly higher than MONDF (more welding)
POLLIT_OT_INSTALL = 0.12        # 12% — crane delays common


# ── ALULIT (Aluminum Cabinet) Correction Factors ──────────────────────────
# Source: Only 31 warehouse jobs — LOW CONFIDENCE.
# Groups with MONDF correction pattern + 30% buffer per gap_analysis.md.
# [LOW CONFIDENCE] — treat as provisional.

ALULIT_CORRECTION: dict[str, Optional[float]] = {
    "0210": 0.40,   # Sheet Metal — aluminum cabinets are lighter gauge
    "0220": 1.50,   # Extrusions — aluminum extrusion framing is primary construction
    "0235": 0.60,   # Routing — face routing only
    "0270": 1.30,   # Misc Fab — assembly + 30% buffer (low confidence)
    "0410": 1.40,   # Clean & Etch — aluminum prep is more involved
    "0420": 1.20,   # Prime & Finish
    "0630": None,   # Install — use warehouse median directly
}

ALULIT_0630_MEDIAN = 5.76       # 1-man install (INSTALL_FLOOR 4.80/1.20*1.44, n=3 LOW)
ALULIT_0620_MEDIAN = 1.50       # Travel
ALULIT_0625_MEDIAN = 2.50       # Removal
ALULIT_OT_FAB = 0.04            # Lower OT — simpler fab
ALULIT_OT_INSTALL = 0.08        # Moderate


# Department labels for labor lines
DEPT_LABELS: dict[str, str] = {
    "01": "Art/Design (100)",
    "02": "Fabrication (200)",
    "03": "Electrical (300)",
    "04": "Paint/Finish (400)",
    "05": "Vinyl (500)",
    "06": "Installation (600)",
    "08": "Survey (800)",
}


# ── Work Code Dictionary (41 codes) ────────────────────────────────────────
# Source: eagle_analyzer_final.py Config.WORK_CODES (merged 2026-02-16)
# Phase field enables workflow sequencing and department grouping.

WORK_CODES: dict[str, dict[str, str]] = {
    '0098': {'desc': 'PERMIT SUBMITTED', 'dept': 'ADMIN', 'phase': 'design'},
    '0099': {'desc': 'PERMIT RECEIVED', 'dept': 'ADMIN', 'phase': 'design'},
    '0110': {'desc': 'SKETCHING', 'dept': 'DESIGN', 'phase': 'design'},
    '0120': {'desc': 'PRINTING', 'dept': 'DESIGN', 'phase': 'design'},
    '0130': {'desc': 'LAYOUT', 'dept': 'DESIGN', 'phase': 'design'},
    '0200': {'desc': 'FABRICATION LAYOUT', 'dept': 'FAB', 'phase': 'fabrication'},
    '0210': {'desc': 'SHEET METAL', 'dept': 'FAB', 'phase': 'fabrication'},
    '0215': {'desc': 'STRUCTURAL STEEL', 'dept': 'FAB', 'phase': 'fabrication'},
    '0220': {'desc': 'EXTRUSIONS', 'dept': 'FAB', 'phase': 'fabrication'},
    '0230': {'desc': 'CHANNEL LETTERS', 'dept': 'FAB', 'phase': 'fabrication'},
    '0235': {'desc': 'ROUTING', 'dept': 'FAB', 'phase': 'fabrication'},
    '0240': {'desc': 'FLAT CUT OUT LETTERS', 'dept': 'FAB', 'phase': 'fabrication'},
    '0250': {'desc': 'AWNINGS', 'dept': 'FAB', 'phase': 'fabrication'},
    '0260': {'desc': 'FACES', 'dept': 'FAB', 'phase': 'fabrication'},
    '0270': {'desc': 'MISC FABRICATION', 'dept': 'FAB', 'phase': 'fabrication'},
    '0280': {'desc': 'CRATING & SHIPPING', 'dept': 'FAB', 'phase': 'fabrication'},
    '0282': {'desc': 'CHECK IN FREIGHT', 'dept': 'FAB', 'phase': 'fabrication'},
    '0310': {'desc': 'BALLAST WIRING', 'dept': 'ELEC', 'phase': 'electrical'},
    '0315': {'desc': 'NEON PATTERN', 'dept': 'ELEC', 'phase': 'electrical'},
    '0320': {'desc': 'NEON WIRING', 'dept': 'ELEC', 'phase': 'electrical'},
    '0330': {'desc': 'NEON BENDING', 'dept': 'ELEC', 'phase': 'electrical'},
    '0340': {'desc': 'ELECTRICAL WIRING', 'dept': 'ELEC', 'phase': 'electrical'},
    '0410': {'desc': 'CLEAN AND ETCH', 'dept': 'PAINT', 'phase': 'paint'},
    '0420': {'desc': 'PRIME AND FINISH', 'dept': 'PAINT', 'phase': 'paint'},
    '0430': {'desc': 'SPRAY PAINTING FACES', 'dept': 'PAINT', 'phase': 'paint'},
    '0510': {'desc': 'LAYOUT', 'dept': 'VINYL', 'phase': 'vinyl'},
    '0520': {'desc': 'CUT AND/OR WEED VINYL', 'dept': 'VINYL', 'phase': 'vinyl'},
    '0530': {'desc': 'PRINTED GRAPHICS', 'dept': 'VINYL', 'phase': 'vinyl'},
    '0550': {'desc': 'VINYL APPLICATION', 'dept': 'VINYL', 'phase': 'vinyl'},
    '0605': {'desc': 'FOOTING - INSTALLATION', 'dept': 'INSTALL', 'phase': 'installation'},
    '0610': {'desc': 'LOAD/UNLOAD', 'dept': 'INSTALL', 'phase': 'installation'},
    '0612': {'desc': 'INSTALL - NO CRANE', 'dept': 'INSTALL', 'phase': 'installation'},
    '0615': {'desc': 'WIRING - INSTALLATION', 'dept': 'INSTALL', 'phase': 'installation'},
    '0620': {'desc': 'TRAVEL', 'dept': 'INSTALL', 'phase': 'installation'},
    '0621': {'desc': 'DELIVER/MILEAGE', 'dept': 'INSTALL', 'phase': 'installation'},
    '0625': {'desc': 'REMOVAL', 'dept': 'INSTALL', 'phase': 'installation'},
    '0630': {'desc': '1 MAN & TRUCK INSTALL', 'dept': 'INSTALL', 'phase': 'installation'},
    '0640': {'desc': '2 MEN & TRUCK INSTALL', 'dept': 'INSTALL', 'phase': 'installation'},
    '0650': {'desc': '3 MEN & TRUCK INSTALL', 'dept': 'INSTALL', 'phase': 'installation'},
    '9200': {'desc': 'FAB OVERTIME', 'dept': 'FAB', 'phase': 'fabrication'},
    '9600': {'desc': 'INSTALL OVERTIME', 'dept': 'INSTALL', 'phase': 'installation'},
}


# ── Business Rules ──────────────────────────────────────────────────────────
# Source: eagle_analyzer_final.py Config + eagle_pricing_guide.py

MIN_BID_HOURS = 4.0          # Minimum total hours for any job
MAX_SINGLE_TASK_HOURS = 80.0  # Cap on any single work code
MAX_OVERTIME_PERCENTAGE = 0.20  # Max OT as fraction of total

# Size-based complexity multipliers (SF thresholds)
# Source: eagle_pricing_guide.py _calculate_size_factors()
SIZE_COMPLEXITY: dict[str, dict[str, float]] = {
    'small':   {'threshold_sf': 20,  'multiplier': 0.9},
    'medium':  {'threshold_sf': 50,  'multiplier': 1.0},
    'large':   {'threshold_sf': 100, 'multiplier': 1.15},
    'xlarge':  {'threshold_sf': 200, 'multiplier': 1.3},
}

# Workflow sequences by sign type (typical work code order)
# Source: eagle_pricing_guide.py _determine_workflow()
WORKFLOW_SEQUENCES: dict[str, list[str]] = {
    'CLLIT':  ['0110', '0200', '0230', '0340', '0420', '0260', '0280', '0640'],
    'MONDF':  ['0110', '0200', '0215', '0340', '0420', '0260', '0605', '0650'],
    'VINYL':  ['0110', '0510', '0520', '0550', '0280', '0630'],
    'POLLIT': ['0110', '0200', '0215', '0220', '0340', '0420', '0605', '0650'],
    'POLNON': ['0110', '0200', '0215', '0220', '0420', '0605', '0650'],
    'AWNNON': ['0110', '0200', '0250', '0270', '0610', '0620', '0630'],
    'AWNILL': ['0110', '0200', '0250', '0270', '0310', '0610', '0620', '0630'],
}


# ── Awning Data ─────────────────────────────────────────────────────────────
# Source: AWNING_ESTIMATING_MASTER.md (Eagle KeyedIn actuals, Jobs #11530/#11532)
# Geometry formulas from Awning Composer 5. Labor factors from Eagle production data.

AWNING_LABOR_PER_SF: dict[str, float] = {
    '0250': 0.105,   # Awnings fabrication
    '0260': 0.015,   # Faces
    '0270': 0.054,   # Misc fabrication
    '0282': 0.004,   # Check in freight
    '9200': 0.027,   # Fab overtime
    '0610': 0.037,   # Load/unload
    '0620': 0.040,   # Travel
    '0630': 0.285,   # 1 man & truck install
    '0640': 0.142,   # 2 men & truck install
    '9600': 0.072,   # Install overtime
}

AWNING_COMPLEXITY: dict[str, float] = {
    'standard': 1.0,
    'quarter_barrel': 1.3,
    'dome': 1.5,
}

# Standard awning recover labor (fixed hours, not SF-based)
AWNING_RECOVER_FIXED: dict[str, float] = {
    'remove': 2.0,           # Remove from building (2-person crew)
    'transport_to_shop': 0.5,  # Round trip split
    'strip_old': 0.75,        # Remove/dispose old cover
    'transport_back': 0.5,     # Return transport
    'reinstall': 2.0,         # Reinstall (2-person crew)
}


# ── Sign Type Classification ────────────────────────────────────────────────
# Source: sign_type_analyzer.py (merged 2026-02-16)
# Regex patterns for inferring sign type from part number + description text.
# Used when sign_type is not explicitly set on JobInput.

SIGN_TYPE_PATTERNS: dict[str, list[str]] = {
    'CLLIT': [r'CHL?-\d+', r'CHANNEL\s*LETTER', r'LETTER.*ILLUM'],
    'CLNON': [r'LETTER.*NON'],
    'MONSF': [r'MON-.*SF', r'MONUMENT.*S/?F', r'MONUMENT.*SINGLE'],
    'MONDF': [r'MON-(?!.*SF)', r'MONUMENT.*D/?F', r'MONUMENT.*DOUBLE'],
    'POLLIT': [r'PYL-', r'PYLON', r'POLE\s*SIGN.*ILLUM'],
    'POLNON': [r'POLE\s*SIGN.*NON', r'POLE\s*SIGN(?!.*ILLUM)'],
    'DIRECT': [r'DIR-', r'WAYFIND', r'DIRECTORY', r'DIRECTIONAL'],
    'BLDILL': [r'BLDG?.*ILLUM', r'WALL\s*SIGN.*ILLUM'],
    'BLDNON': [r'BLDG?.*NON', r'WALL\s*SIGN.*NON'],
    'AWNNON': [r'\bAWN[-\s\d]', r'AWNING', r'CANOPY'],
    'GEMINI': [r'DIM-', r'DIMENSIONAL', r'STUD\s*MOUNT', r'STAND\s*OFF'],
    'VINYL': [r'VIN-', r'VINYL', r'WINDOW\s*GRAPHIC', r'DECAL'],
    'LED': [r'EMC-', r'LED\s*DISPLAY', r'ELECTRONIC', r'DIGITAL'],
    'ALULIT': [r'CAB.*ILLUM', r'ALUMINUM.*CAB.*ILLUM'],
    'ALUNON': [r'CAB.*NON', r'ALUMINUM.*CAB.*NON'],
    'NEON': [r'NEON'],
}

# Size extraction patterns
SIZE_PATTERNS: dict[str, str] = {
    'inches': r'(\d+)"',
    'feet': r"(\d+)'",
    'dimensions': r'(\d+)\s*[xX]\s*(\d+)',
    'area_sf': r'(\d+)\s*SF',
}


def classify_sign_type(part_number: str, description: str = '') -> str:
    """
    Infer Eagle sign type code from part number and description text.
    Returns SignType value string (e.g. 'CLLIT', 'MONDF') or 'OTHER'.
    Source: sign_type_analyzer.py categorize_part()
    """
    combined = f"{part_number} {description}".upper()
    for sign_type, patterns in SIGN_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return sign_type
    return 'OTHER'


def extract_size_from_text(part_number: str, description: str = '') -> dict:
    """
    Extract size info from part number + description text.
    Returns dict with keys: width, height, area_sf, size_inches (whichever found).
    Source: sign_type_analyzer.py extract_size()
    """
    combined = f"{part_number} {description}"
    size_info: dict = {}

    dim_match = re.search(SIZE_PATTERNS['dimensions'], combined)
    if dim_match:
        w, h = int(dim_match.group(1)), int(dim_match.group(2))
        size_info['width'] = w
        size_info['height'] = h
        size_info['area_sf'] = (w * h) / 144.0

    inch_match = re.search(SIZE_PATTERNS['inches'], combined)
    if inch_match:
        size_info['size_inches'] = int(inch_match.group(1))

    area_match = re.search(SIZE_PATTERNS['area_sf'], combined)
    if area_match:
        size_info['area_sf'] = int(area_match.group(1))

    return size_info


# ── Statistical Calibration Functions ────────────────────────────────────────
# Source: benchmark_v7_5.py (merged 2026-02-16)
# Used for warehouse baseline validation and correction factor calibration.
# NOT used in the hot path of estimate() — these are calibration/tuning tools.

def robust_z_mad(vals) -> tuple:
    """
    MAD-based z-scores with IQR fallback for zero-MAD distributions.
    Returns (z_array, median, scale).
    Source: benchmark_v7_5.py robust_z_mad()
    """
    import numpy as np
    import pandas as pd
    s = pd.Series(vals, dtype="float64").dropna()
    if s.empty:
        return np.array([]), float('nan'), float('nan')
    m = float(s.median())
    mad = float((s - m).abs().median())
    if mad <= 0:
        q1, q3 = float(s.quantile(0.25)), float(s.quantile(0.75))
        iqr = max(q3 - q1, 1e-9)
        scale = iqr / 1.349
    else:
        scale = mad
    z = 0.6745 * (s - m) / (scale if scale != 0 else 1e-9)
    return z.to_numpy(), m, scale


def baseline_for_group(actual_hours: list[float]) -> dict:
    """
    Compute robust baseline statistics for a group of actual hours.

    Outlier handling: extreme (|z|>=5 or beyond 3×IQR) excluded,
    mild (|z|>=3.5 or beyond 1.5×IQR) winsorized.

    Production Number selection:
      CV <= 0.40 → P80
      0.40 < CV <= 0.65 → P75
      CV > 0.65 → P70

    Source: benchmark_v7_5.py baseline_for_group()
    """
    import numpy as np
    import pandas as pd
    if not actual_hours:
        return {}
    s = pd.Series(actual_hours, dtype="float64").dropna()
    if s.empty:
        return {}
    z, m, scale = robust_z_mad(s.to_numpy())
    q1, q3 = float(s.quantile(0.25)), float(s.quantile(0.75))
    iqr = q3 - q1
    lower_bound = max(q1 - 1.5 * iqr, m - 3.5 * scale / 0.6745)
    upper_bound = min(q3 + 1.5 * iqr, m + 3.5 * scale / 0.6745)

    arr = s.to_numpy()
    extreme_mask = (np.abs(z) >= 5) | (arr < (q1 - 3 * iqr)) | (arr > (q3 + 3 * iqr))
    mild_mask = ((np.abs(z) >= 3.5) & (np.abs(z) < 5)) | (arr < (q1 - 1.5 * iqr)) | (arr > (q3 + 1.5 * iqr))
    mild_mask = mild_mask & (~extreme_mask)

    baseline_vals: list[float] = []
    excluded_extremes = 0
    winsorized = 0
    for v, ext, mild in zip(arr, extreme_mask, mild_mask):
        if ext:
            excluded_extremes += 1
            continue
        if mild:
            winsorized += 1
            v = min(max(v, lower_bound), upper_bound)
        baseline_vals.append(float(v))

    if not baseline_vals:
        baseline_vals = s.to_list()

    sb = pd.Series(baseline_vals, dtype="float64")
    mean_val = float(sb.mean())
    median_val = float(sb.median())
    std_val = float(sb.std(ddof=1)) if len(sb) > 1 else 0.0
    cv = (std_val / mean_val) if mean_val != 0 else None

    def quant(p: float) -> float:
        return float(sb.quantile(p))

    p50 = quant(0.50)
    p70 = quant(0.70)
    p75 = quant(0.75)
    p80 = quant(0.80)
    p90 = quant(0.90)

    if cv is None:
        prod = p75
        prod_src = "P75 (cv=NA)"
    elif cv <= 0.40:
        prod = p80
        prod_src = "P80 (cv<=0.40)"
    elif cv <= 0.65:
        prod = p75
        prod_src = "P75 (0.40<cv<=0.65)"
    else:
        prod = p70
        prod_src = "P70 (cv>0.65)"

    return {
        "n_universe": int(len(s)),
        "n_baseline": int(len(sb)),
        "excluded_extremes": excluded_extremes,
        "winsorized_count": winsorized,
        "mean": mean_val,
        "median": median_val,
        "std": std_val,
        "cv": cv,
        "P50": p50,
        "P70": p70,
        "P75": p75,
        "P80": p80,
        "P90": p90,
        "P95": float(sb.quantile(0.95)),
        "P100": float(sb.max()),
        "Production_Number_raw": prod,
        "Production_Rule_raw": prod_src,
    }


# ── LED Sizing ───────────────────────────────────────────────────────────────

def calculate_led(
    pf: float,
    construction: ConstructionType,
    letter_height_inches: float = 12.0,
    voltage_pref: int = 24,
    module_override: str = "",
) -> dict:
    """Calculate LED module count and power supply sizing using led_catalog.

    Args:
        pf: Peripheral feet (total sign perimeter).
        construction: FACE_LIT, HALO, STRIP, or OPEN_FACE.
        letter_height_inches: Tallest letter height for module selection.
        voltage_pref: 0=auto, 12=12V only, 24=24V only.
        module_override: Vendor SKU to force a specific module (e.g. "HLED-PN2W65K").
    """
    # 1. Select module
    if module_override:
        module = _get_led_module(module_override)
        if module is None:
            module = _select_led_module(letter_height_inches, construction.value, voltage_pref)
    else:
        module = _select_led_module(letter_height_inches, construction.value, voltage_pref)

    # 2. Calculate module count
    if construction == ConstructionType.HALO:
        raw_modules = pf * module.mods_per_foot * 1.0
    else:
        raw_modules = pf * module.mods_per_foot * 1.0

    modules_with_waste = raw_modules * 1.05  # 5% waste
    total_modules = round(modules_with_waste)

    # 3. Wattage
    watts = total_modules * module.watts
    capacity_needed = watts / 0.80  # NEC 80% rule

    # 4. Power supply sizing
    ps, ps_count = _size_ps(watts, module.voltage)

    # 5. Cascade distribution
    feed_type = "double" if construction == ConstructionType.HALO else "single"
    cascade_runs, mods_per_run = _check_cascade(module, total_modules, feed_type)

    # 6. Voltage drop
    v_drop, wire_awg = _estimate_vdrop(module, total_modules, cascade_runs, mods_per_run)

    # 7. Compliance check
    total_length_ft = total_modules / module.mods_per_foot if module.mods_per_foot > 0 else 0
    is_compliant, compliance_notes = _check_led_compliance(
        module, watts, ps, ps_count, v_drop, cascade_runs, total_length_ft
    )

    return {
        "modules": total_modules,
        "watts": round(watts, 1),
        "capacity_needed": round(capacity_needed, 1),
        "ps_spec": f"{ps.rated_watts:.0f}W" if ps_count == 1 else f"{ps_count}x{ps.rated_watts:.0f}W",
        "ps_count": ps_count,
        "ps_part": eagle_pn(ps.part_number),
        "ps_vendor_sku": ps.part_number,
        # Module details
        "module_name": module.name,
        "module_sku": module.part_number,
        "module_eagle_pn": eagle_pn(module.part_number),
        "module_watts": module.watts,
        "module_voltage": module.voltage,
        # Cascade & compliance
        "cascade_runs": cascade_runs,
        "mods_per_run": mods_per_run,
        "voltage_drop_v": v_drop,
        "wire_awg": wire_awg,
        "is_compliant": is_compliant,
        "compliance_notes": compliance_notes,
    }


# ── Material BOM ─────────────────────────────────────────────────────────────

def calculate_materials(pf: float, face_sf: float, return_depth_inches: float,
                        raceway_lf: float,
                        construction: ConstructionType,
                        letter_height_inches: float = 12.0) -> list[dict]:
    """Calculate material BOM with part numbers and quantities."""
    led = calculate_led(pf, construction, letter_height_inches=letter_height_inches)
    bom = []

    # Face Acrylic 3/16"
    face_qty = face_sf * 1.15  # 15% waste
    bom.append({
        "item": "Face Acrylic 3/16\"",
        "part": "217-0485",
        "qty": round(face_qty, 2),
        "unit": "SF",
        "waste": "15%",
        "formula": f"Face SF ({face_sf:.2f}) x 1.15",
    })

    # Return Coil .040"
    coil_lf = pf * (return_depth_inches / 12.0) * 1.05  # 5% waste
    coil_line = {
        "item": f"Return Coil .040\" ({return_depth_inches}\" depth)",
        "part": "205-0111",
        "qty": round(coil_lf, 2),
        "unit": "SF",
        "waste": "5%",
        "formula": f"PF ({pf:.2f}) x depth ({return_depth_inches}\"/12) x 1.05",
    }
    # M2: ABC catalog enrichment (opt-in via ABC_CATALOG_ENRICHMENT=on env var).
    # Annotates the coil line with vendor/Channelume metadata when applicable.
    # Default OFF — preserves all 252 existing tests byte-for-byte.
    try:
        from abc_catalog import lookup_channel_letter_return
        cl_ret = lookup_channel_letter_return(return_depth_inches)
        if cl_ret:
            coil_line["catalog_part"] = cl_ret["code"]
            coil_line["catalog_name"] = cl_ret["name"]
            coil_line["catalog_vendor"] = cl_ret["vendor"]
            coil_line["catalog_depth_in"] = cl_ret["depth_in"]
    except ImportError:
        pass  # abc_catalog not present yet, skip enrichment
    bom.append(coil_line)

    # Back Aluminum .040"
    back_qty = face_sf * 1.10  # 10% waste
    bom.append({
        "item": "Back Aluminum .040\"",
        "part": "205-0180",
        "qty": round(back_qty, 2),
        "unit": "SF",
        "waste": "10%",
        "formula": f"Face SF ({face_sf:.2f}) x 1.10",
    })

    # Trim Cap 1" — IMPORTANT: 202-0710 is actually ABC's TYPE IV RETAINER per
    # warehouse audit (stg_1106_local_inventory_active), NOT a trim cap. Real
    # trim caps are Jewelite 208-0xxx (76 records in warehouse, 30+ colors).
    # Keeping 202-0710 here for backwards compatibility; M5 enrichment exposes
    # the correct retainer typing via catalog_*.
    trim_lf = pf * 1.05  # 5% waste
    trim_line = {
        "item": "Trim Cap 1\"",
        "part": "202-0710",  # NOTE: legacy; this is actually Type IV Retainer
        "qty": round(trim_lf, 2),
        "unit": "LF",
        "waste": "5%",
        "formula": f"PF ({pf:.2f}) x 1.05",
    }
    # M5: ABC retainer catalog enrichment.
    try:
        from abc_catalog import lookup_retainer
        ret = lookup_retainer("IV", "mill")  # default: Type IV mill finish
        if ret:
            trim_line["catalog_part"] = ret["code"]
            trim_line["catalog_abc_type"] = ret["abc_type_code"]
            trim_line["catalog_finish_multiplier"] = ret["finish_multiplier"]
            trim_line["catalog_eagle_pn"] = ret["eagle_pn"]
            trim_line["catalog_vendor"] = ret["vendor"]
            trim_line["data_quality_note"] = (
                "part 202-0710 is Type IV Retainer per warehouse — real trim "
                "caps are Jewelite 208-0xxx; consider M5 wiring of TRIM_CAP "
                "category lookup for accurate vendor + price"
            )
    except ImportError:
        pass
    bom.append(trim_line)

    # LED Modules
    bom.append({
        "item": f"LED Modules ({led.get('module_name', 'LED')})",
        "part": led.get("module_eagle_pn", "307-0261"),
        "vendor_sku": led.get("module_sku", ""),
        "qty": led["modules"],
        "unit": "EA",
        "waste": "5%",
        "formula": f"PF ({pf:.2f}) x {led.get('module_watts', 0.72)} W/mod x 1.05 waste",
    })

    # Power Supply
    bom.append({
        "item": f"Power Supply ({led['ps_spec']})",
        "part": led["ps_part"],
        "vendor_sku": led.get("ps_vendor_sku", ""),
        "qty": led["ps_count"],
        "unit": "EA",
        "waste": "0%",
        "formula": f"{led['watts']:.0f}W / 0.80 = {led['capacity_needed']:.0f}W needed",
    })

    # M3: Raceway extrusion BOM line (currently absent — only labor for raceway
    # was tracked, never the extrusion material itself). Adds an Excellart 7"
    # raceway line (Eagle SKU 202-1265, $17.4475/EA per warehouse) when
    # raceway_lf > 0 and ENRICH is on. Defaults to ABC raceway via abc_catalog.
    if raceway_lf > 0:
        raceway_line = {
            "item": f"Raceway extrusion ({raceway_lf:.1f} LF)",
            "part": "202-1265",  # Excellart 7" CLRW, confirmed in warehouse
            "qty": round(raceway_lf * 1.05, 2),
            "unit": "LF",
            "waste": "5%",
            "formula": f"Raceway LF ({raceway_lf:.1f}) x 1.05",
        }
        try:
            from abc_catalog import lookup_raceway_extrusion
            r = lookup_raceway_extrusion()
            if r:
                raceway_line["catalog_part"] = r["code"]
                raceway_line["catalog_name"] = r["name"]
                raceway_line["catalog_vendor"] = r["vendor"]
                raceway_line["catalog_eagle_pn"] = "202-1265"
                raceway_line["catalog_excellart_product_number"] = "1401015"
        except ImportError:
            pass
        bom.append(raceway_line)

    # Wire (gauge selected by voltage drop calculation)
    wire_awg = led.get("wire_awg", 18)
    wire_lf = raceway_lf + 20  # Raceway LF + 20ft
    bom.append({
        "item": f"Wire {wire_awg}AWG",
        "part": "307-0100",
        "vendor_sku": "",
        "qty": round(wire_lf, 1),
        "unit": "LF",
        "waste": "fixed +20'",
        "formula": f"Raceway LF ({raceway_lf:.1f}) + 20",
    })

    # Hardware
    hardware_sf = raceway_lf * 10
    bom.append({
        "item": "Hardware (Tapcons, silicone, wire nuts, etc.)",
        "part": "214-0000",
        "qty": round(hardware_sf, 1),
        "unit": "SF (KeyedIn)",
        "waste": "N/A",
        "formula": f"Raceway LF ({raceway_lf:.1f}) x 10 = {hardware_sf:.0f} SF",
    })

    return bom


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class JobInput:
    """Input parameters for a channel letter job estimate."""
    # PF source (one of these should be set)
    pf_from_pdf: Optional[float] = None
    pf_manual: Optional[float] = None

    # If using footage chart
    letter_count: int = 0
    letter_height_inches: float = 0.0
    font_type: FontType = FontType.BLOCK

    # Logo PF (additive)
    logo_pf: float = 0.0

    # Construction
    construction: ConstructionType = ConstructionType.FACE_LIT
    return_depth_inches: float = 5.0

    # Installation
    install_height_ft: float = 15.0  # Mounting height
    mount_location: MountLocation = MountLocation.WALL
    raceway_lf: float = 0.0  # 0 = wall-mounted, >0 = on raceway
    substrate: str = "standard"

    # Travel
    miles_one_way: float = 0.0
    crew_size: int = 2
    num_units: int = 1  # Number of sign units for load/unload

    # Batch travel deduplication -- multiple signs on same job share one trip
    batch_index: int = 0   # 0 = first/only sign (gets travel), 1+ = skip travel
    batch_size: int = 1    # Total signs in batch (for load/unload scaling)

    # Optional removal
    include_removal: bool = False
    has_raceway: bool = False  # True = sign on raceway (adds raceway removal labor)

    # Face area override (if known from PDF)
    face_sf_override: Optional[float] = None

    # Sign type (determines correction factors)
    sign_type: SignType = SignType.CLLIT

    # Cabinet dimensions (for Section 2 estimation)
    cabinet_sf: float = 0.0
    cabinet_face: CabinetFace = CabinetFace.SINGLE
    cabinet_shape: CabinetShape = CabinetShape.RECTANGULAR
    cabinet_frame: CabinetFrame = CabinetFrame.LIGHT

    # Unified Takeoff Fields (general defaults — all estimators use these)
    construction_method: str = "stick"
    num_faces: int = 1             # Default single-face; monuments pass 2 explicitly
    sign_sf_per_face: float = 0.0  # Square feet per face (for SF-based estimators)
    has_vinyl: bool = False        # Has vinyl graphics — includes 0520, 0550
    has_structural_steel: bool = False  # Steel posts/beams (vs aluminum tube/angle)
    has_footing: bool = False      # Self-performed footing (vs sub)
    return_depth_in: Optional[float] = None
    standoff_in: float = 0.0

    # Paint (for Section 5A estimation)
    paint_colors: int = 1
    paint_sf: float = 0.0  # 0 = auto-calculate from cabinet_sf or face_sf

    # Cabinet install (for Section 10A)
    install_mount_type: str = "wall"  # wall, roof, pipe
    is_first_sign: bool = True

    # Monument/Pylon-specific fields
    is_illuminated: bool = False   # Has LED/electrical — includes 0260, 0310, 0340
    footing_sub_cost: float = 0.0  # Subcontracted footing cost ($)


@dataclass
class LaborLine:
    """A single labor line item for KeyedIn entry."""
    work_code: str
    description: str
    hours: float
    unit_type: str  # "man-hrs" or "crew-hrs"
    department: str
    formula: str
    section: str  # ABC section reference


@dataclass
class EstimateResult:
    """Complete estimate output."""
    # Input echo
    total_pf: float
    pf_source: str
    construction: str
    height_category: str
    letter_count: int

    # Labor
    labor_lines: list[LaborLine] = field(default_factory=list)
    total_man_hours: float = 0.0
    total_crew_hours: float = 0.0

    # Materials
    material_bom: list[dict] = field(default_factory=list)

    # LED
    led_spec: dict = field(default_factory=dict)

    # Installation
    install_lines: list[LaborLine] = field(default_factory=list)

    # Warnings
    warnings: list[str] = field(default_factory=list)


# ── Shared Helpers ───────────────────────────────────────────────────────────

def _make_travel_line(job: JobInput, fallback_hrs: float = 0.0,
                      fallback_formula: str = "") -> LaborLine:
    """Generate a batch-aware travel LaborLine.

    - batch_index == 0: first/only sign → normal travel calc
    - batch_index > 0: subsequent sign in same job → 0 hours (shared trip)
    - If miles_one_way == 0 and fallback_hrs > 0: use warehouse median fallback
    """
    if job.batch_index > 0:
        return LaborLine(
            work_code="0620",
            description=f"Travel (shared -- batch sign #{job.batch_index + 1})",
            hours=0.0, unit_type="man-hrs",
            department="Installation (600)",
            formula=f"Batch sign #{job.batch_index + 1} of {job.batch_size} -- travel charged to sign #1",
            section="Batch travel dedup",
        )
    if job.miles_one_way > 0:
        travel_hrs = round((job.miles_one_way / 50.0) * 2 * job.crew_size, 2)
        return LaborLine(
            work_code="0620", description="Travel",
            hours=travel_hrs, unit_type="man-hrs",
            department="Installation (600)",
            formula=f"({job.miles_one_way} mi / 50) x 2 x {job.crew_size} crew",
            section="Standard",
        )
    if fallback_hrs > 0:
        return LaborLine(
            work_code="0620", description="Travel",
            hours=round(fallback_hrs, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=fallback_formula or f"Warehouse median {fallback_hrs}h",
            section="Standard",
        )
    return None  # type: ignore[return-value]


def _make_raceway_removal_line(job: JobInput) -> LaborLine | None:
    """Generate raceway removal adder line if job.has_raceway is True."""
    if not job.has_raceway:
        return None
    rw_lf = job.raceway_lf if job.raceway_lf > 0 else 8.0
    rw_hrs = RACEWAY_REMOVAL_BASE + max(0, rw_lf - 10) * RACEWAY_REMOVAL_PER_LF
    return LaborLine(
        work_code="0625", description="Raceway Removal (adder)",
        hours=round(rw_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=f"Base {RACEWAY_REMOVAL_BASE}h + max(0, {rw_lf:.0f} LF - 10) x {RACEWAY_REMOVAL_PER_LF}/LF = {rw_hrs:.2f}h",
        section="Raceway removal adder",
    )


# ── Main Calculation Engine ──────────────────────────────────────────────────

def estimate(job: JobInput) -> EstimateResult:
    """Run the full ABC estimation for a channel letter job."""

    # ── Determine PF ─────────────────────────────────────────────────────
    if job.pf_from_pdf is not None and job.pf_from_pdf > 0:
        total_pf = job.pf_from_pdf
        pf_source = "PDF extraction (PyMuPDF)"
    elif job.pf_manual is not None and job.pf_manual > 0:
        total_pf = job.pf_manual
        pf_source = "Manual entry"
    elif job.letter_count > 0 and job.letter_height_inches > 0:
        total_pf = calculate_pf_from_chart(
            job.letter_count, job.letter_height_inches, job.font_type
        )
        pf_source = (f"Footage chart ({job.font_type.value}, "
                     f"{job.letter_count} letters x {job.letter_height_inches}\")")
    else:
        return EstimateResult(
            total_pf=0, pf_source="NONE", construction=job.construction.value,
            height_category="", letter_count=0,
            warnings=["No PF source provided. Enter PF manually, upload PDF, or use footage chart."]
        )

    total_pf += job.logo_pf

    # ── Determine height category ────────────────────────────────────────
    if job.letter_height_inches > 0:
        height_cat = get_height_category(job.letter_height_inches)
    else:
        height_cat = HeightCategory.MEDIUM  # default

    # ── Estimate face SF if not provided ─────────────────────────────────
    if job.face_sf_override is not None:
        face_sf = job.face_sf_override
    else:
        # Rough approximation: PF / 4 (perimeter to area ratio for typical letters)
        face_sf = total_pf * job.letter_height_inches / 24.0 if job.letter_height_inches > 0 else total_pf * 0.5

    # ── Get rates ────────────────────────────────────────────────────────

    construction = job.construction
    if job.sign_type == SignType.CLNON:
        construction = 'non_illuminated'

    if construction == ConstructionType.OPEN_FACE:
        construction = ConstructionType.FACE_LIT

    rates = SECTION_4_RATES.get(construction, {}).get(height_cat, {})
    if not rates:
        rates = SECTION_4_RATES[ConstructionType.FACE_LIT][HeightCategory.MEDIUM]

    result = EstimateResult(
        total_pf=round(total_pf, 2),
        pf_source=pf_source,
        construction=job.construction.value,
        height_category=height_cat.value,
        letter_count=job.letter_count,
    )

    labor = []

    # ── 0110 Design ──────────────────────────────────────────────────────
    labor.append(LaborLine(
        work_code="0110", description="Design / Drafting",
        hours=DESIGN_HOURS, unit_type="man-hrs",
        department="Art/Design (100)",
        formula="1.00 hr standard",
        section="Standard",
    ))

    # ── 0200 Fab Layout ──────────────────────────────────────────────────
    labor.append(LaborLine(
        work_code="0200", description="Fabrication Layout",
        hours=FAB_LAYOUT_HOURS, unit_type="man-hrs",
        department="Fabrication (200)",
        formula="1.50 hrs constant",
        section="Standard",
    ))

    # ── 0210 Sheet Metal (Section 4) ─────────────────────────────────────
    sheet_hrs = SECTION_4_CONSTANT + (total_pf * rates["sheet"])
    labor.append(LaborLine(
        work_code="0210", description="Sheet Metal Fabrication",
        hours=round(sheet_hrs, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"{SECTION_4_CONSTANT} + ({total_pf:.2f} PF x {rates['sheet']})",
        section=f"4{'B' if job.construction == ConstructionType.FACE_LIT else 'C' if job.construction == ConstructionType.HALO else 'A'} {height_cat.value}",
    ))

    # ── 0270 Sign Fab / Mounting ─────────────────────────────────────────
    mount_hrs = total_pf * rates["mount"]
    mount_formula = f"{total_pf:.2f} PF x {rates['mount']}"
    mount_section = f"4{'B' if job.construction == ConstructionType.FACE_LIT else 'C'} {height_cat.value}"

    # Phase 0 CORRECTION 2: CLLIT 0270 floor (catch-all code, warehouse mean=63h is anomalous)
    if job.sign_type == SignType.CLLIT and mount_hrs < CLLIT_0270_FLOOR:
        abc_hrs = mount_hrs
        mount_hrs = CLLIT_0270_FLOOR
        mount_formula += f" -> floored to {CLLIT_0270_FLOOR}h (MONDF P50 proxy)"
        mount_section += " [CORRECTED]"
        result.warnings.append(
            f"0270 corrected: ABC={abc_hrs:.2f}h -> {CLLIT_0270_FLOOR}h "
            f"(CLLIT 0270 warehouse anomaly — recalibrated to MONDF P50)"
        )

    labor.append(LaborLine(
        work_code="0270", description="Sign Fabrication / Mounting",
        hours=round(mount_hrs, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=mount_formula,
        section=mount_section,
    ))

    # ── 0310 LED Wiring ──────────────────────────────────────────────────
    led_wire_hrs = total_pf * LED_WIRE_RATE
    labor.append(LaborLine(
        work_code="0310", description="LED Wiring",
        hours=round(led_wire_hrs, 2), unit_type="man-hrs",
        department="Electrical (300)",
        formula=f"{total_pf:.2f} PF x {LED_WIRE_RATE}",
        section="4D",
    ))

    # ── 0410 Paint ───────────────────────────────────────────────────────
    paint_hrs = total_pf * rates["paint"]
    labor.append(LaborLine(
        work_code="0410", description="Prime and Finish",
        hours=round(paint_hrs, 2), unit_type="man-hrs",
        department="Paint/Finish (400)",
        formula=f"{total_pf:.2f} PF x {rates['paint']}",
        section=f"4{'B' if job.construction == ConstructionType.FACE_LIT else 'C'} {height_cat.value}",
    ))

    # Phase 0 CORRECTION 3: Fab overtime (9200) — probability-weighted
    ot = OT_FACTORS.get(job.sign_type.value)
    if ot:
        fab_prob, fab_mean = ot[0], ot[1]
        fab_expected = round(fab_prob * fab_mean, 2)
        if fab_expected >= 0.50:
            labor.append(LaborLine(
                work_code="9200",
                description="Fab Overtime (probability-weighted)",
                hours=fab_expected, unit_type="man-hrs",
                department="Fabrication (200)",
                formula=f"{fab_prob:.0%} prob × {fab_mean:.1f}h avg",
                section="Phase 0 Correction [PROVISIONAL]",
            ))

    result.labor_lines = labor

    # ── Installation ─────────────────────────────────────────────────────
    install = []
    over_35 = job.install_height_ft > 35
    install_key = "high" if over_35 else "low"
    install_constant = INSTALL_CONSTANT_HIGH if over_35 else INSTALL_CONSTANT_LOW

    install_rate = INSTALL_RATES.get(height_cat, {}).get(install_key, 0.036)
    substrate_mult = SUBSTRATE_MULTIPLIERS.get(job.substrate, 1.0)

    install_crew_hrs = (install_constant + total_pf * install_rate) * substrate_mult
    install_formula = (f"({install_constant} + {total_pf:.2f} x {install_rate})"
                       f"{f' x {substrate_mult} substrate' if substrate_mult != 1.0 else ''}")
    install_section = f"10B {height_cat.value} ({'over 35ft' if over_35 else '0-35ft'})"

    # Phase 0 CORRECTION 1: Install floor by sign type (warehouse-derived)
    floor = INSTALL_FLOOR.get(job.sign_type.value)
    if floor is not None and install_crew_hrs < floor:
        abc_hrs = install_crew_hrs
        install_crew_hrs = floor
        install_formula += f" -> floored to {floor}h (warehouse benchmark)"
        install_section += " [CORRECTED]"
        result.warnings.append(
            f"Install corrected: ABC={abc_hrs:.2f}h -> {floor}h "
            f"(warehouse floor for {job.sign_type.value}, "
            f"mean={INSTALL_FLOOR.get(job.sign_type.value)}h)"
        )

    install.append(LaborLine(
        work_code="0640", description="2 Men & Truck - Install",
        hours=round(install_crew_hrs, 2), unit_type="CREW-hrs",
        department="Installation (600)",
        formula=install_formula,
        section=install_section,
    ))

    # ── 0610 Load/Unload ────────────────────────────────────────────────
    load_hrs = 1.0 + 0.5 * max(0, job.num_units - 1)
    install.append(LaborLine(
        work_code="0610", description="Load / Unload",
        hours=round(load_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=f"1.0 + 0.5 x ({job.num_units} - 1) additional units",
        section="Standard",
    ))

    # ── 0620 Travel (batch-aware) ──────────────────────────────────────────
    _tl = _make_travel_line(job)
    if _tl:
        install.append(_tl)

    # ── 0282 Check-In Freight ────────────────────────────────────────────
    pallets = max(1, (job.num_units + 1) // 2)
    freight_hrs = 0.5 * pallets
    install.append(LaborLine(
        work_code="0282", description="Check-In Freight",
        hours=round(freight_hrs, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"0.5 x {pallets} pallets",
        section="Standard",
    ))

    # ── 0625 Removal (optional) — warehouse P50 x 1.20 ───────────────────
    if job.include_removal:
        _rem_key = job.sign_type.value
        removal_hrs = REMOVAL_FLOOR.get(_rem_key, REMOVAL_DEFAULT)
        _rem_src = f"REMOVAL_FLOOR[{_rem_key}]" if _rem_key in REMOVAL_FLOOR else f"REMOVAL_DEFAULT (type {_rem_key})"
        install.append(LaborLine(
            work_code="0625", description="Removal",
            hours=round(removal_hrs, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=f"{_rem_src} = {removal_hrs}h (warehouse P50 x 1.20)",
            section="Warehouse removal floor",
        ))

    # Phase 0 CORRECTION 3: Install overtime (9600) — probability-weighted
    if ot:
        inst_prob, inst_mean = ot[2], ot[3]
        inst_expected = round(inst_prob * inst_mean, 2)
        if inst_expected >= 0.50:
            install.append(LaborLine(
                work_code="9600",
                description="Install Overtime (probability-weighted)",
                hours=inst_expected, unit_type="man-hrs",
                department="Installation (600)",
                formula=f"{inst_prob:.0%} prob × {inst_mean:.1f}h avg",
                section="Phase 0 Correction [PROVISIONAL]",
            ))

    result.install_lines = install

    # ── Totals ───────────────────────────────────────────────────────────
    result.total_man_hours = round(
        sum(l.hours for l in labor if l.unit_type == "man-hrs")
        + sum(l.hours for l in install if l.unit_type == "man-hrs"),
        2
    )
    result.total_crew_hours = round(
        sum(l.hours for l in install if l.unit_type == "CREW-hrs"),
        2
    )

    # ── LED Spec ─────────────────────────────────────────────────────────
    result.led_spec = calculate_led(
        total_pf,
        job.construction,
        letter_height_inches=job.letter_height_inches if job.letter_height_inches > 0 else 12.0,
    )

    # ── Material BOM ─────────────────────────────────────────────────────
    raceway_lf = job.raceway_lf if job.raceway_lf > 0 else total_pf * 0.3  # estimate
    result.material_bom = calculate_materials(
        total_pf, face_sf, job.return_depth_inches, raceway_lf, job.construction,
        letter_height_inches=job.letter_height_inches if job.letter_height_inches > 0 else 12.0,
    )

    # ── Warnings ─────────────────────────────────────────────────────────
    if job.construction == ConstructionType.STRIP and job.letter_height_inches < 25:
        result.warnings.append(
            "Strip channel is typically 25\"+ only. Using pan channel rates for smaller heights."
        )
    if over_35:
        result.warnings.append(
            f"Height over 35' — using elevated install rates (x{HEIGHT_FACTOR_OVER_35})."
        )
    if job.substrate != "standard":
        result.warnings.append(
            f"Substrate adjustment: {job.substrate} = x{substrate_mult}"
        )

    return result


# ── Comparable WO Loader ──────────────────────────────────────────────────────

def load_comparable(wo_number: str,
                    db_path: str | None = None,
                    ) -> dict[str, float]:
    """
    Pull a WO's actual hours from the warehouse, grouped by work code.

    Returns dict like {"0210": 12.25, "0410": 5.00, "0630": 4.50, ...}
    Only includes codes with actual_hours > 0.
    Deduplicates by latest run_date per work_code.

    Usage:
        comp = load_comparable("9719.2")
        # comp = {"0200": 1.75, "0210": 12.25, "0220": 4.25, ...}
    """
    if db_path is None:
        _resolved = find_warehouse_db()
        if _resolved is None:
            return {}
        db_path = str(_resolved)
    import duckdb
    con = duckdb.connect(db_path, read_only=True)
    rows = con.execute("""
        SELECT work_code, actual_hours
        FROM (
            SELECT work_code, actual_hours,
                   ROW_NUMBER() OVER (
                       PARTITION BY work_code ORDER BY run_date DESC
                   ) AS rn
            FROM so_contract_labor
            WHERE wo_number = ?
        )
        WHERE rn = 1 AND actual_hours > 0
        ORDER BY work_code
    """, [wo_number]).fetchall()
    con.close()
    return {code: hrs for code, hrs in rows}


# ── Monument Estimation Engine ────────────────────────────────────────────────

def estimate_monument(job: JobInput) -> EstimateResult:
    """
    Estimate labor for a MONDF/MONSF monument sign.

    Uses ABC Section 2 (cabinet SF) + Section 5A (paint SF) + Section 10A
    (install SF) formulas, then applies MONDF_CORRECTION factors from
    954-job warehouse analysis.

    For 0630 install: ABC is 16.57x wrong — uses warehouse median directly.
    For 0340 electrical: only included when is_illuminated=True.
    OT: fab_total x 0.31, install x 0.50.

    Requires sign_sf_per_face > 0 on JobInput.
    """
    sign_type_key = job.sign_type.value
    total_sf = job.sign_sf_per_face * job.num_faces
    cab_face = CabinetFace.DOUBLE if job.num_faces >= 2 else CabinetFace.SINGLE

    result = EstimateResult(
        total_pf=0.0,
        pf_source="N/A (monument — SF-based, not PF)",
        construction=f"monument_{sign_type_key.lower()}",
        height_category="N/A",
        letter_count=0,
    )

    if total_sf <= 0:
        result.warnings.append("sign_sf_per_face required for monument estimate.")
        return result

    labor: list[LaborLine] = []
    install: list[LaborLine] = []
    fab_total = 0.0  # Track for OT calc

    # ── Select correction factors by sign type + illumination ──────────
    seg_label = "LIT" if job.is_illuminated else "NONLIT"
    is_monsf = (job.sign_type == SignType.MONSF)
    if is_monsf:
        corr_table = MONSF_CORRECTION_LIT if job.is_illuminated else MONSF_CORRECTION_NONLIT
    else:
        corr_table = MONDF_CORRECTION_LIT if job.is_illuminated else MONDF_CORRECTION_NONLIT

    def corrected(code: str, abc_hrs: float) -> float:
        factor = corr_table.get(code)
        if factor is None:
            return abc_hrs
        return abc_hrs * factor

    def corr_note(code: str, abc_hrs: float) -> str:
        factor = corr_table.get(code)
        if factor is None or factor == 1.0:
            return ""
        return f" x {factor:.2f} = {abc_hrs * factor:.2f}h"

    # ── Get ABC Section 2 rate for this cabinet config ─────────────────
    cab_key = (cab_face, job.cabinet_frame, job.cabinet_shape)
    sec2 = SECTION_2_RATES.get(cab_key)
    if not sec2:
        cab_key = (cab_face, CabinetFrame.LIGHT, CabinetShape.RECTANGULAR)
        sec2 = SECTION_2_RATES.get(cab_key, {"labor": 0.228, "material": 2.12})
        result.warnings.append(
            f"Cabinet config not in Section 2 — using "
            f"{cab_key[1].value}/{cab_key[2].value} fallback."
        )
    sec2_rate = sec2["labor"]

    # ── 0110 Design ────────────────────────────────────────────────────
    labor.append(LaborLine(
        work_code="0110", description="Design / Drafting",
        hours=DESIGN_HOURS, unit_type="man-hrs",
        department="Art/Design (100)",
        formula="1.00 hr standard",
        section="Standard",
    ))

    # ── 0200 Fab Layout ────────────────────────────────────────────────
    abc_200 = FAB_LAYOUT_HOURS
    if is_monsf:
        # MONSF: P50=1.25h x 1.20 = 1.50h. ABC 1.50h already matches.
        corr_200 = 1.0
    else:
        # MONDF: nonlit=1.75x (med 2.63h / 1.50h base), lit=3.6x
        corr_200 = 3.6 if job.is_illuminated else 1.75
    hrs_200 = abc_200 * corr_200
    labor.append(LaborLine(
        work_code="0200", description="Fabrication Layout",
        hours=round(hrs_200, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"ABC {abc_200:.2f}h x {corr_200} ({'MONSF' if is_monsf else seg_label})",
        section=f"Std x {'MONSF' if is_monsf else 'MONDF'} {corr_200}x",
    ))
    fab_total += hrs_200

    # ── 0210 Sheet Metal (Section 2: constant + SF x rate x correction)
    abc_210 = SECTION_2_CONSTANT + (total_sf * sec2_rate)
    hrs_210 = corrected("0210", abc_210)
    labor.append(LaborLine(
        work_code="0210", description="Sheet Metal",
        hours=round(hrs_210, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"Sec2: {SECTION_2_CONSTANT} + ({total_sf:.1f} SF x {sec2_rate:.3f})" + corr_note("0210", abc_210),
        section=f"2 ({cab_face.value})",
    ))
    fab_total += hrs_210

    # ── 0215 Structural Steel (only when steel posts/beams present) ──
    if job.has_structural_steel:
        abc_215 = total_sf * sec2_rate * 0.75
        hrs_215 = corrected("0215", abc_215)
        labor.append(LaborLine(
            work_code="0215", description="Structural Steel",
            hours=round(hrs_215, 2), unit_type="man-hrs",
            department="Fabrication (200)",
            formula=f"{total_sf:.1f} SF x {sec2_rate:.3f} x 0.75" + corr_note("0215", abc_215),
            section="2 (derived) x 0.85",
        ))
        fab_total += hrs_215

    # ── 0220 Extrusions (Section 2E: constant + LF x rate) ───────────
    # Perimeter of one face — extrusions frame the sign once, not per face
    approx_h = math.sqrt(job.sign_sf_per_face) * 1.5
    approx_w = job.sign_sf_per_face / approx_h if approx_h > 0 else 0
    ext_lf = 2 * (approx_h + approx_w)
    abc_220 = SECTION_2E_CONSTANT + (ext_lf * 0.208)
    hrs_220 = corrected("0220", abc_220)
    labor.append(LaborLine(
        work_code="0220", description="Extrusions",
        hours=round(hrs_220, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"Sec2E: {SECTION_2E_CONSTANT} + ({ext_lf:.1f} LF x 0.208)" + corr_note("0220", abc_220),
        section="2E (straight)",
    ))
    fab_total += hrs_220

    # ── 0235 Routing (CNC reduced) ───────────────────────────────────
    abc_235 = total_sf * sec2_rate * 0.50
    hrs_235 = corrected("0235", abc_235)
    labor.append(LaborLine(
        work_code="0235", description="Routing",
        hours=round(hrs_235, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"{total_sf:.1f} SF x {sec2_rate:.3f} x 0.50" + corr_note("0235", abc_235),
        section="2 (derived) x 0.59 CNC",
    ))
    fab_total += hrs_235

    # ── 0270 Misc Fabrication (22% of nonlit, 70% of lit have this code)
    abc_270 = total_sf * sec2_rate
    hrs_270 = corrected("0270", abc_270)
    labor.append(LaborLine(
        work_code="0270", description="Misc Fabrication",
        hours=round(hrs_270, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"{total_sf:.1f} SF x {sec2_rate:.3f}" + corr_note("0270", abc_270),
        section="2 x 2.22",
    ))
    fab_total += hrs_270

    # ── 0340 Electrical Wiring (illuminated only) ─────────────────────
    if job.is_illuminated:
        abc_340 = 1.0 + total_sf * 0.020
        hrs_340 = corrected("0340", abc_340)
        labor.append(LaborLine(
            work_code="0340", description="Electrical Wiring",
            hours=round(hrs_340, 2), unit_type="man-hrs",
            department="Electrical (300)",
            formula=f"1.0 + ({total_sf:.1f} SF x 0.020)" + corr_note("0340", abc_340),
            section="Est x 4.25",
        ))
        fab_total += hrs_340

    # ── 0410 Clean & Etch (Section 5A) ────────────────────────────────
    paint_rate = SECTION_5A_RATES.get(job.paint_colors, SECTION_5A_RATES[1])
    paint_sf = job.paint_sf if job.paint_sf > 0 else total_sf

    abc_410 = paint_rate["constant"] + (paint_sf * paint_rate["labor"])
    hrs_410 = corrected("0410", abc_410)
    labor.append(LaborLine(
        work_code="0410", description="Clean & Etch",
        hours=round(hrs_410, 2), unit_type="man-hrs",
        department="Paint/Finish (400)",
        formula=f"Sec5A: {paint_rate['constant']} + ({paint_sf:.1f} SF x {paint_rate['labor']})" + corr_note("0410", abc_410),
        section=f"5A ({job.paint_colors} color)",
    ))

    # ── 0420 Prime & Finish (Section 5A) ──────────────────────────────
    abc_420 = paint_rate["constant"] + (paint_sf * paint_rate["labor"])
    hrs_420 = corrected("0420", abc_420)
    labor.append(LaborLine(
        work_code="0420", description="Prime & Finish",
        hours=round(hrs_420, 2), unit_type="man-hrs",
        department="Paint/Finish (400)",
        formula=f"Sec5A: {paint_rate['constant']} + ({paint_sf:.1f} SF x {paint_rate['labor']})" + corr_note("0420", abc_420),
        section=f"5A ({job.paint_colors} color)",
    ))

    # ── Vinyl (if applicable) ─────────────────────────────────────────
    if job.has_vinyl:
        vinyl_sf = total_sf
        if is_monsf:
            # MONSF: P50=0.50h for 0520/0550 (n=171/113). Use SF-scaling with P50 floor.
            hrs_520 = max(0.50, round(vinyl_sf * 0.05, 2))
            hrs_550 = max(0.50, round(vinyl_sf * 0.07, 2))
            v_formula_520 = f"max(0.50, {vinyl_sf:.1f} SF x 0.05) [MONSF P50=0.50h]"
            v_formula_550 = f"max(0.50, {vinyl_sf:.1f} SF x 0.07) [MONSF P50=0.50h]"
        else:
            hrs_520 = round(1.0 + vinyl_sf * 0.02, 2)
            hrs_550 = round(1.0 + vinyl_sf * 0.03, 2)
            v_formula_520 = f"1.0 + ({vinyl_sf:.1f} SF x 0.02)"
            v_formula_550 = f"1.0 + ({vinyl_sf:.1f} SF x 0.03)"
        labor.append(LaborLine(
            work_code="0520", description="Cut / Weed Vinyl",
            hours=hrs_520, unit_type="man-hrs",
            department="Vinyl (500)",
            formula=v_formula_520,
            section="Est (vinyl/SF)",
        ))
        labor.append(LaborLine(
            work_code="0550", description="Vinyl Application",
            hours=hrs_550, unit_type="man-hrs",
            department="Vinyl (500)",
            formula=v_formula_550,
            section="Est (vinyl/SF)",
        ))

    # ── 9200 Fab Overtime (median OT ratio from warehouse) ─────────────
    ot_fab_rate = MONDF_OT_FAB_LIT if job.is_illuminated else MONDF_OT_FAB_NONLIT
    fab_ot = round(fab_total * ot_fab_rate, 2)
    if fab_ot >= 0.25:
        labor.append(LaborLine(
            work_code="9200", description=f"Fab Overtime ({ot_fab_rate:.1%} median)",
            hours=fab_ot, unit_type="man-hrs",
            department="Fabrication (200)",
            formula=f"Fab total {fab_total:.2f}h x {ot_fab_rate} ({seg_label} median)",
            section="MONDF correction",
        ))

    # ── Installation ───────────────────────────────────────────────────

    # 0610 Load/Unload
    load_hrs = 1.0 + 0.5 * max(0, job.num_units - 1)
    install.append(LaborLine(
        work_code="0610", description="Load / Unload",
        hours=round(load_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=f"1.0 + 0.5 x ({job.num_units} - 1) units",
        section="Standard",
    ))

    # 0620 Travel (batch-aware) — warehouse median when no distance given
    travel_fb = MONSF_0620_MEDIAN if is_monsf else MONDF_0620_MEDIAN_NONLIT
    _tl = _make_travel_line(job, fallback_hrs=travel_fb,
                            fallback_formula=f"Warehouse median {travel_fb}h ({'MONSF' if is_monsf else 'MONDF NONLIT'})")
    if _tl:
        install.append(_tl)

    # 0630 1-Man Install — warehouse median by segment (no floor override)
    if is_monsf:
        install_median = MONSF_0630_MEDIAN_NONLIT   # MONSF has no lit-specific median yet
    else:
        install_median = MONDF_0630_MEDIAN_LIT if job.is_illuminated else MONDF_0630_MEDIAN_NONLIT
    install_hrs = install_median

    install.append(LaborLine(
        work_code="0630", description="1 Man & Truck - Install",
        hours=round(install_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=f"Warehouse median {install_median}h ({seg_label})",
        section="MONDF correction (ABC 16.57x wrong)",
    ))

    # 9600 Install Overtime (median OT ratio from warehouse)
    ot_inst_rate = MONDF_OT_INSTALL_LIT if job.is_illuminated else MONDF_OT_INSTALL_NONLIT
    inst_ot = round(install_hrs * ot_inst_rate, 2)
    if inst_ot >= 0.25:
        install.append(LaborLine(
            work_code="9600", description=f"Install Overtime ({ot_inst_rate:.1%} median)",
            hours=inst_ot, unit_type="man-hrs",
            department="Installation (600)",
            formula=f"Install {install_hrs:.2f}h x {ot_inst_rate} ({seg_label} median)",
            section="MONDF correction",
        ))

    # 0625 Removal (optional) — warehouse P50 x 1.20
    if job.include_removal:
        _mondf_rem = REMOVAL_FLOOR.get("MONDF", REMOVAL_DEFAULT)
        install.append(LaborLine(
            work_code="0625", description="Removal",
            hours=round(_mondf_rem, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=f"REMOVAL_FLOOR[MONDF] = {_mondf_rem}h (warehouse P50 x 1.20, n=33)",
            section="Warehouse removal floor",
        ))

    # 0605 Footing (optional, self-performed)
    if job.has_footing:
        install.append(LaborLine(
            work_code="0605", description="Footing Install (self-performed)",
            hours=11.75, unit_type="man-hrs",
            department="Installation (600)",
            formula="WO 9719.3 actual (Quikcrete footings)",
            section="[COMPARABLE]",
        ))

    # ── Assemble result ────────────────────────────────────────────────
    result.labor_lines = labor
    result.install_lines = install
    result.total_man_hours = round(
        sum(l.hours for l in labor if l.unit_type == "man-hrs")
        + sum(l.hours for l in install if l.unit_type == "man-hrs"),
        2
    )
    result.total_crew_hours = round(
        sum(l.hours for l in install if l.unit_type == "CREW-hrs"),
        2
    )

    corrected_codes = [c for c, f in corr_table.items() if f is not None and f != 1.0]
    result.warnings.append(
        f"MONDF corrections applied: {', '.join(corrected_codes)}. "
        f"Segment: {seg_label}. Source: signx.duckdb so_contracts+so_contract_labor."
    )
    return result


# ── Standalone Removal Estimator ──────────────────────────────────────────────

def estimate_removal(job: JobInput) -> EstimateResult:
    """
    Estimate labor for a standalone sign removal job.
    Two-tier: warehouse P50 x 1.20 (primary) or PF-based ABC fallback.
    """
    sign_type_key = job.sign_type.value
    result = EstimateResult(
        total_pf=0.0, pf_source="N/A (removal)",
        construction="removal", height_category="N/A", letter_count=0,
    )
    install: list[LaborLine] = []

    # 0625 Removal — two-tier: warehouse P50 primary, PF formula fallback
    removal_floor = REMOVAL_FLOOR.get(sign_type_key)
    if removal_floor:
        removal_hrs = removal_floor
        formula = f"Warehouse P50 x 1.20 = {removal_floor}h (calibrated 2026-02)"
        section = "Warehouse removal floor"
    else:
        pf = job.pf_manual or job.pf_from_pdf or 0
        if pf > 0:
            removal_hrs = round(pf * 0.051 / 2 + 0.5, 2)
            formula = f"ABC fallback: {pf:.1f} PF x 0.051 / 2 + 0.5 = {removal_hrs:.2f}h"
            section = "ABC removal formula (no warehouse data)"
        else:
            removal_hrs = REMOVAL_DEFAULT
            formula = f"Default {REMOVAL_DEFAULT}h (overall warehouse P50 x 1.20)"
            section = "Warehouse removal floor (default)"

    install.append(LaborLine(
        work_code="0625", description="Removal",
        hours=round(removal_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=formula, section=section,
    ))

    # 0625R Raceway Removal (adder)
    _rr = _make_raceway_removal_line(job)
    if _rr:
        install.append(_rr)

    # 0610 Load/Unload
    load_hrs = 1.0 + 0.5 * max(0, job.num_units - 1)
    install.append(LaborLine(
        work_code="0610", description="Load / Unload",
        hours=round(load_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=f"1.0 + 0.5 x ({job.num_units} - 1) units",
        section="Standard",
    ))

    # 0620 Travel (batch-aware)
    _tl = _make_travel_line(job)
    if _tl:
        install.append(_tl)

    # 9600 Install OT — use OT_FACTORS if available for sign type
    ot = OT_FACTORS.get(sign_type_key)
    if ot:
        inst_prob, inst_mean = ot[2], ot[3]
        inst_ot = round(inst_prob * inst_mean, 2)
        if inst_ot >= 0.50:
            install.append(LaborLine(
                work_code="9600", description="Install Overtime (probability-weighted)",
                hours=inst_ot, unit_type="man-hrs",
                department="Installation (600)",
                formula=f"{inst_prob:.0%} prob x {inst_mean:.1f}h avg ({sign_type_key})",
                section="Warehouse removal floor",
            ))

    result.install_lines = install
    result.total_man_hours = round(
        sum(l.hours for l in install if l.unit_type == "man-hrs"), 2
    )
    result.total_crew_hours = 0.0
    return result


# ── Awning Estimation Engine ────────────────────────────────────────────────

def estimate_awning(job: JobInput) -> EstimateResult:
    """
    Estimate labor for an awning recover/new job.

    Two modes:
      1. SF-based (sign_sf_per_face > 0): Uses AWNING_LABOR_PER_SF per-sqft factors
         from Eagle production data (Jobs #11530/#11532).
      2. Geometry-based (width/projection/drop provided via description parsing):
         Uses Awning Composer 5 panel/yardage calculator + fixed recover labor.

    SF-based is preferred when square footage is known.
    Geometry-based is for when you have the physical dimensions.

    Source: calc_awning.py + AWNING_ESTIMATING_MASTER.md (merged 2026-02-16)
    """
    result = EstimateResult(
        total_pf=0.0,
        pf_source="N/A (awning — SF-based)",
        construction="awning",
        height_category="N/A",
        letter_count=0,
    )

    total_sf = job.sign_sf_per_face * max(job.num_faces, 1)

    if total_sf <= 0:
        result.warnings.append(
            "sign_sf_per_face required for awning estimate. "
            "Set to (width_in × slope_in) / 144."
        )
        return result

    # Complexity multiplier (standard, quarter_barrel, dome)
    # Default to standard — user can override via description or future field
    complexity = 1.0

    labor: list[LaborLine] = []
    install: list[LaborLine] = []

    # ── 0110 Design ───────────────────────────────────────────────────
    labor.append(LaborLine(
        work_code="0110", description="Design / Drafting",
        hours=DESIGN_HOURS, unit_type="man-hrs",
        department="Art/Design (100)",
        formula="1.00 hr standard",
        section="Standard",
    ))

    # ── 0200 Fab Layout (AWNILL only — warehouse P50=3.00h, n=109) ────
    is_illuminated_awning = (job.sign_type == SignType.AWNILL or job.is_illuminated)
    if is_illuminated_awning:
        hrs_200 = max(3.00, total_sf * 0.08)
        labor.append(LaborLine(
            work_code="0200", description="Fabrication Layout",
            hours=round(hrs_200, 2), unit_type="man-hrs",
            department="Fabrication (200)",
            formula=f"AWNILL: max(3.00, {total_sf:.1f}SF x 0.08) = {hrs_200:.2f}h  [warehouse P50=3.00h, n=109]",
            section="AWNILL warehouse",
        ))
        fab_total = hrs_200
    else:
        fab_total = 0.0

    # ── Fabrication codes (SF-based) ──────────────────────────────────
    fab_codes = ['0250', '0260', '0270']
    for code in fab_codes:
        rate = AWNING_LABOR_PER_SF.get(code, 0.0)
        if rate <= 0:
            continue
        hrs = total_sf * rate * complexity
        desc = WORK_CODES.get(code, {}).get('desc', f'Code {code}')
        labor.append(LaborLine(
            work_code=code, description=desc,
            hours=round(hrs, 2), unit_type="man-hrs",
            department="Fabrication (200)",
            formula=f"{total_sf:.1f} SF x {rate:.3f}/SF x {complexity:.1f}",
            section="Awning (Eagle actuals)",
        ))
        fab_total += hrs

    # ── 0310 Electrical (AWNILL only — LED strip/driver wiring) ──────
    if is_illuminated_awning:
        hrs_310 = max(1.50, total_sf * 0.04)
        labor.append(LaborLine(
            work_code="0310", description="Electrical Wiring",
            hours=round(hrs_310, 2), unit_type="man-hrs",
            department="Fabrication (300)",
            formula=f"AWNILL: max(1.50, {total_sf:.1f}SF x 0.04) = {hrs_310:.2f}h  [LED driver/strip wiring]",
            section="AWNILL warehouse",
        ))
        fab_total += hrs_310

    # ── 0282 Check-In Freight ─────────────────────────────────────────
    freight_rate = AWNING_LABOR_PER_SF.get('0282', 0.004)
    freight_hrs = total_sf * freight_rate
    if freight_hrs >= 0.25:
        labor.append(LaborLine(
            work_code="0282", description="Check In Freight",
            hours=round(freight_hrs, 2), unit_type="man-hrs",
            department="Fabrication (200)",
            formula=f"{total_sf:.1f} SF x {freight_rate:.3f}/SF",
            section="Awning (Eagle actuals)",
        ))

    # ── 9200 Fab Overtime ─────────────────────────────────────────────
    ot_rate = AWNING_LABOR_PER_SF.get('9200', 0.027)
    fab_ot = total_sf * ot_rate
    if fab_ot >= 0.50:
        labor.append(LaborLine(
            work_code="9200", description="Fab Overtime",
            hours=round(fab_ot, 2), unit_type="man-hrs",
            department="Fabrication (200)",
            formula=f"{total_sf:.1f} SF x {ot_rate:.3f}/SF",
            section="Awning (Eagle actuals)",
        ))

    # ── Installation codes (SF-based) ─────────────────────────────────
    # 0610 Load/Unload
    load_rate = AWNING_LABOR_PER_SF.get('0610', 0.037)
    load_hrs = total_sf * load_rate
    install.append(LaborLine(
        work_code="0610", description="Load / Unload",
        hours=round(load_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=f"{total_sf:.1f} SF x {load_rate:.3f}/SF",
        section="Awning (Eagle actuals)",
    ))

    # 0620 Travel (batch-aware, SF-based fallback)
    _awning_travel_rate = AWNING_LABOR_PER_SF.get('0620', 0.040)
    _awning_travel_fb = round(total_sf * _awning_travel_rate, 2)
    _tl = _make_travel_line(job, fallback_hrs=_awning_travel_fb,
                            fallback_formula=f"{total_sf:.1f} SF x {_awning_travel_rate:.3f}/SF (Eagle actuals)")
    if _tl:
        install.append(_tl)

    # 0630 1-Man Install
    install_1man_rate = AWNING_LABOR_PER_SF.get('0630', 0.285)
    install_1man_hrs = total_sf * install_1man_rate
    install.append(LaborLine(
        work_code="0630", description="1 Man & Truck - Install",
        hours=round(install_1man_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=f"{total_sf:.1f} SF x {install_1man_rate:.3f}/SF",
        section="Awning (Eagle actuals)",
    ))

    # 0640 2-Man Install (crew-hours)
    install_2man_rate = AWNING_LABOR_PER_SF.get('0640', 0.142)
    install_2man_hrs = total_sf * install_2man_rate
    if install_2man_hrs >= 0.50:
        install.append(LaborLine(
            work_code="0640", description="2 Men & Truck - Install",
            hours=round(install_2man_hrs, 2), unit_type="CREW-hrs",
            department="Installation (600)",
            formula=f"{total_sf:.1f} SF x {install_2man_rate:.3f}/SF",
            section="Awning (Eagle actuals)",
        ))

    # 9600 Install Overtime
    inst_ot_rate = AWNING_LABOR_PER_SF.get('9600', 0.072)
    inst_ot = total_sf * inst_ot_rate
    if inst_ot >= 0.50:
        install.append(LaborLine(
            work_code="9600", description="Install Overtime",
            hours=round(inst_ot, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=f"{total_sf:.1f} SF x {inst_ot_rate:.3f}/SF",
            section="Awning (Eagle actuals)",
        ))

    # ── 0625 Removal (optional) ──────────────────────────────────────
    if job.include_removal:
        remove_hrs = AWNING_RECOVER_FIXED['remove']
        strip_hrs = AWNING_RECOVER_FIXED['strip_old']
        removal_total = remove_hrs + strip_hrs
        install.append(LaborLine(
            work_code="0625", description="Removal (remove + strip)",
            hours=round(removal_total, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=f"Remove {remove_hrs}h + strip {strip_hrs}h",
            section="Awning recover standard",
        ))

    # ── Assemble result ───────────────────────────────────────────────
    result.labor_lines = labor
    result.install_lines = install
    result.total_man_hours = round(
        sum(l.hours for l in labor if l.unit_type == "man-hrs")
        + sum(l.hours for l in install if l.unit_type == "man-hrs"),
        2
    )
    result.total_crew_hours = round(
        sum(l.hours for l in install if l.unit_type == "CREW-hrs"),
        2
    )

    result.warnings.append(
        f"Awning estimate: {total_sf:.1f} SF, complexity={complexity:.1f}x. "
        f"Source: Eagle actuals (Jobs #11530/#11532)."
    )
    return result


# ── Pylon/Pole Estimation Engine ────────────────────────────────────────────────

def estimate_pylon(job: JobInput) -> EstimateResult:
    """
    Estimate labor for a POLLIT/POLNON pylon/pole sign.

    Uses ABC Section 2 (cabinet SF) + Section 5A (paint SF) formulas with
    POLLIT_CORRECTION factors. Pylons have heavy structural steel (tall poles),
    and require crane installation (0650 vs 0630).

    POLNON (non-illuminated): Skips 0340 Electrical Wiring.
    POLLIT (illuminated): Includes 0340 Electrical (long wire runs up poles).

    For 0650 install: Uses warehouse median directly (crane crew).
    For 0605 footing: Almost always self-performed for pylons.
    OT: fab_total x 0.065, install x 0.12.

    Requires sign_sf_per_face > 0 on JobInput.
    [PROVISIONAL] — correction factors derived from MONDF pattern scaled for
    pylon characteristics. Will refine with direct warehouse query (n=461).
    """
    sign_type_key = job.sign_type.value
    total_sf = job.sign_sf_per_face * job.num_faces
    cab_face = CabinetFace.DOUBLE if job.num_faces >= 2 else CabinetFace.SINGLE

    result = EstimateResult(
        total_pf=0.0,
        pf_source="N/A (pylon — SF-based, not PF)",
        construction=f"pylon_{sign_type_key.lower()}",
        height_category="N/A",
        letter_count=0,
    )

    if total_sf <= 0:
        result.warnings.append("sign_sf_per_face required for pylon estimate.")
        return result

    labor: list[LaborLine] = []
    install: list[LaborLine] = []
    fab_total = 0.0  # Track for OT calc

    # ── Correction helpers (POLLIT_CORRECTION dict) ──────────────────
    def corrected(code: str, abc_hrs: float) -> float:
        factor = POLLIT_CORRECTION.get(code)
        if factor is None:
            return abc_hrs
        return abc_hrs * factor

    def corr_note(code: str, abc_hrs: float) -> str:
        factor = POLLIT_CORRECTION.get(code)
        if factor is None or factor == 1.0:
            return ""
        return f" x {factor:.2f} = {abc_hrs * factor:.2f}h"

    # ── Get ABC Section 2 rate for this cabinet config ─────────────────
    cab_key = (cab_face, job.cabinet_frame, job.cabinet_shape)
    sec2 = SECTION_2_RATES.get(cab_key)
    if not sec2:
        cab_key = (cab_face, CabinetFrame.LIGHT, CabinetShape.RECTANGULAR)
        sec2 = SECTION_2_RATES.get(cab_key, {"labor": 0.228, "material": 2.12})
        result.warnings.append(
            f"Cabinet config not in Section 2 — using "
            f"{cab_key[1].value}/{cab_key[2].value} fallback."
        )
    sec2_rate = sec2["labor"]

    # ── 0110 Design ────────────────────────────────────────────────────
    labor.append(LaborLine(
        work_code="0110", description="Design / Drafting",
        hours=DESIGN_HOURS, unit_type="man-hrs",
        department="Art/Design (100)",
        formula="1.00 hr standard",
        section="Standard",
    ))

    # ── 0200 Fab Layout (pylon = 2.5x base — more complex layout) ─────
    abc_200 = FAB_LAYOUT_HOURS
    corr_200 = 2.5
    hrs_200 = abc_200 * corr_200
    labor.append(LaborLine(
        work_code="0200", description="Fabrication Layout",
        hours=round(hrs_200, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"ABC {abc_200:.2f}h x {corr_200} (pylon — complex layout)",
        section=f"Std x POLLIT {corr_200}x",
    ))
    fab_total += hrs_200

    # ── 0210 Sheet Metal (Section 2: constant + SF x rate x correction) ─
    abc_210 = SECTION_2_CONSTANT + (total_sf * sec2_rate)
    hrs_210 = corrected("0210", abc_210)
    labor.append(LaborLine(
        work_code="0210", description="Sheet Metal",
        hours=round(hrs_210, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"Sec2: {SECTION_2_CONSTANT} + ({total_sf:.1f} SF x {sec2_rate:.3f})" + corr_note("0210", abc_210),
        section=f"2 ({cab_face.value})",
    ))
    fab_total += hrs_210

    # ── 0215 Structural Steel (HEAVY — tall steel poles, welded) ───────
    abc_215 = total_sf * sec2_rate * 1.50
    hrs_215 = corrected("0215", abc_215)
    labor.append(LaborLine(
        work_code="0215", description="Structural Steel",
        hours=round(hrs_215, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"{total_sf:.1f} SF x {sec2_rate:.3f} x 1.50" + corr_note("0215", abc_215),
        section="2 (derived) — pylon poles [HEAVY]",
    ))
    fab_total += hrs_215

    # ── 0220 Extrusions (Section 2E: constant + LF x rate) ────────────
    approx_h = math.sqrt(job.sign_sf_per_face) * 1.5
    approx_w = job.sign_sf_per_face / approx_h if approx_h > 0 else 0
    ext_lf = 2 * (approx_h + approx_w)
    abc_220 = SECTION_2E_CONSTANT + (ext_lf * 0.208)
    hrs_220 = corrected("0220", abc_220)
    labor.append(LaborLine(
        work_code="0220", description="Extrusions",
        hours=round(hrs_220, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"Sec2E: {SECTION_2E_CONSTANT} + ({ext_lf:.1f} LF x 0.208)" + corr_note("0220", abc_220),
        section="2E (straight)",
    ))
    fab_total += hrs_220

    # ── 0235 Routing (less routing on pylons — panel faces) ────────────
    abc_235 = total_sf * sec2_rate * 0.30
    hrs_235 = corrected("0235", abc_235)
    labor.append(LaborLine(
        work_code="0235", description="Routing",
        hours=round(hrs_235, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"{total_sf:.1f} SF x {sec2_rate:.3f} x 0.30" + corr_note("0235", abc_235),
        section="2 (derived) — pylon reduced",
    ))
    fab_total += hrs_235

    # ── 0270 Misc Fabrication (assembly, pole brackets, mounting hw) ───
    abc_270 = total_sf * sec2_rate
    hrs_270 = corrected("0270", abc_270)
    labor.append(LaborLine(
        work_code="0270", description="Misc Fabrication",
        hours=round(hrs_270, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"{total_sf:.1f} SF x {sec2_rate:.3f}" + corr_note("0270", abc_270),
        section="2 — pole brackets/hw",
    ))
    fab_total += hrs_270

    # ── 0340 Electrical Wiring (illuminated only — long runs up poles) ──
    if job.is_illuminated:
        abc_340 = 1.0 + total_sf * 0.030
        hrs_340 = corrected("0340", abc_340)
        labor.append(LaborLine(
            work_code="0340", description="Electrical Wiring",
            hours=round(hrs_340, 2), unit_type="man-hrs",
            department="Electrical (300)",
            formula=f"1.0 + ({total_sf:.1f} SF x 0.030)" + corr_note("0340", abc_340),
            section="Est — pylon long runs",
        ))
        fab_total += hrs_340

    # ── 0410 Clean & Etch (Section 5A) ─────────────────────────────────
    paint_rate = SECTION_5A_RATES.get(job.paint_colors, SECTION_5A_RATES[1])
    paint_sf = job.paint_sf if job.paint_sf > 0 else total_sf

    abc_410 = paint_rate["constant"] + (paint_sf * paint_rate["labor"])
    hrs_410 = corrected("0410", abc_410)
    labor.append(LaborLine(
        work_code="0410", description="Clean & Etch",
        hours=round(hrs_410, 2), unit_type="man-hrs",
        department="Paint/Finish (400)",
        formula=f"Sec5A: {paint_rate['constant']} + ({paint_sf:.1f} SF x {paint_rate['labor']})" + corr_note("0410", abc_410),
        section=f"5A ({job.paint_colors} color)",
    ))

    # ── 0420 Prime & Finish (Section 5A) ───────────────────────────────
    abc_420 = paint_rate["constant"] + (paint_sf * paint_rate["labor"])
    hrs_420 = corrected("0420", abc_420)
    labor.append(LaborLine(
        work_code="0420", description="Prime & Finish",
        hours=round(hrs_420, 2), unit_type="man-hrs",
        department="Paint/Finish (400)",
        formula=f"Sec5A: {paint_rate['constant']} + ({paint_sf:.1f} SF x {paint_rate['labor']})" + corr_note("0420", abc_420),
        section=f"5A ({job.paint_colors} color)",
    ))

    # ── Vinyl (if applicable) ──────────────────────────────────────────
    if job.has_vinyl:
        vinyl_sf = total_sf
        labor.append(LaborLine(
            work_code="0520", description="Cut / Weed Vinyl",
            hours=round(1.0 + vinyl_sf * 0.02, 2), unit_type="man-hrs",
            department="Vinyl (500)",
            formula=f"1.0 + ({vinyl_sf:.1f} SF x 0.02)",
            section="Est (vinyl/SF)",
        ))
        labor.append(LaborLine(
            work_code="0550", description="Vinyl Application",
            hours=round(1.0 + vinyl_sf * 0.03, 2), unit_type="man-hrs",
            department="Vinyl (500)",
            formula=f"1.0 + ({vinyl_sf:.1f} SF x 0.03)",
            section="Est (vinyl/SF)",
        ))

    # ── 9200 Fab Overtime (pylon OT ratio) ───────────────────────────
    fab_ot = round(fab_total * POLLIT_OT_FAB, 2)
    if fab_ot >= 0.25:
        labor.append(LaborLine(
            work_code="9200", description=f"Fab Overtime ({POLLIT_OT_FAB:.1%} median)",
            hours=fab_ot, unit_type="man-hrs",
            department="Fabrication (200)",
            formula=f"Fab total {fab_total:.2f}h x {POLLIT_OT_FAB} ({sign_type_key} median)",
            section=f"{sign_type_key} correction",
        ))

    # ── Installation ──────────────────────────────────────────────────

    # 0610 Load/Unload (heavier than monument)
    load_hrs = 1.5 + 0.5 * max(0, job.num_units - 1)
    install.append(LaborLine(
        work_code="0610", description="Load / Unload",
        hours=round(load_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=f"1.5 + 0.5 x ({job.num_units} - 1) units (pylon — heavier)",
        section="Standard",
    ))

    # 0620 Travel (batch-aware) — warehouse median when no distance given
    _tl = _make_travel_line(job, fallback_hrs=POLLIT_0620_MEDIAN,
                            fallback_formula=f"Warehouse median {POLLIT_0620_MEDIAN}h ({sign_type_key})")
    if _tl:
        install.append(_tl)

    # 0650 3-Man Install — crane required for pylon
    install_hrs = POLLIT_0650_MEDIAN
    install.append(LaborLine(
        work_code="0650", description="3 Men & Crane - Install",
        hours=round(install_hrs, 2), unit_type="CREW-hrs",
        department="Installation (600)",
        formula=f"Warehouse median {POLLIT_0650_MEDIAN}h ({sign_type_key} crane install)",
        section=f"{sign_type_key} correction (crane required)",
    ))

    # 0605 Footing (almost always self-performed for pylons)
    if job.has_footing:
        install.append(LaborLine(
            work_code="0605", description="Footing Install (self-performed)",
            hours=round(POLLIT_0605_MEDIAN, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=f"Warehouse median {POLLIT_0605_MEDIAN}h ({sign_type_key} deep footing)",
            section=f"{sign_type_key} correction",
        ))

    # 0625 Removal (optional) — warehouse P50 x 1.20
    if job.include_removal:
        _pol_rem = REMOVAL_FLOOR.get(sign_type_key, REMOVAL_DEFAULT)
        install.append(LaborLine(
            work_code="0625", description="Removal",
            hours=round(_pol_rem, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=f"REMOVAL_FLOOR[{sign_type_key}] = {_pol_rem}h (warehouse P50 x 1.20)",
            section="Warehouse removal floor",
        ))

    # 9600 Install Overtime (pylon OT ratio)
    inst_ot = round(install_hrs * POLLIT_OT_INSTALL, 2)
    if inst_ot >= 0.25:
        install.append(LaborLine(
            work_code="9600", description=f"Install Overtime ({POLLIT_OT_INSTALL:.1%} median)",
            hours=inst_ot, unit_type="man-hrs",
            department="Installation (600)",
            formula=f"Install {install_hrs:.2f}h x {POLLIT_OT_INSTALL} ({sign_type_key} median)",
            section=f"{sign_type_key} correction",
        ))

    # ── Assemble result ────────────────────────────────────────────────
    result.labor_lines = labor
    result.install_lines = install
    result.total_man_hours = round(
        sum(l.hours for l in labor if l.unit_type == "man-hrs")
        + sum(l.hours for l in install if l.unit_type == "man-hrs"),
        2
    )
    result.total_crew_hours = round(
        sum(l.hours for l in install if l.unit_type == "CREW-hrs"),
        2
    )

    corrected_codes = [c for c, f in POLLIT_CORRECTION.items() if f is not None and f != 1.0]
    lit_label = "POLLIT" if job.is_illuminated else "POLNON"
    result.warnings.append(
        f"{lit_label} corrections applied [PROVISIONAL]: {', '.join(corrected_codes)}. "
        f"Source: MONDF pattern scaled for pylon (n=461 warehouse jobs). "
        f"Will refine with direct POLLIT warehouse query."
    )
    if not job.is_illuminated:
        result.warnings.append("Non-illuminated: 0340 Electrical Wiring excluded.")
    return result


# ── Aluminum Cabinet Estimation Engine ──────────────────────────────────────────

def estimate_cabinet(job: JobInput) -> EstimateResult:
    """
    Estimate labor for an ALULIT/ALUNON aluminum cabinet sign.

    Simpler than monument — basically a box on a wall. Uses ABC Section 2
    (cabinet SF) + Section 5A (paint SF) formulas with ALULIT_CORRECTION
    factors.

    No structural steel (wall-mounted standard).
    No foundation (wall-mounted standard).
    Electrical only if illuminated.
    Install uses 0630 (1-man) at warehouse median.
    OT: fab_total x 0.04, install x 0.08.

    Requires sign_sf_per_face > 0 on JobInput.
    [LOW CONFIDENCE] — only 31 warehouse jobs available for calibration.
    """
    sign_type_key = job.sign_type.value
    total_sf = job.sign_sf_per_face * job.num_faces
    cab_face = CabinetFace.DOUBLE if job.num_faces >= 2 else CabinetFace.SINGLE

    result = EstimateResult(
        total_pf=0.0,
        pf_source="N/A (cabinet — SF-based, not PF)",
        construction=f"cabinet_{sign_type_key.lower()}",
        height_category="N/A",
        letter_count=0,
    )

    if total_sf <= 0:
        result.warnings.append("sign_sf_per_face required for cabinet estimate.")
        return result

    labor: list[LaborLine] = []
    install: list[LaborLine] = []
    fab_total = 0.0  # Track for OT calc

    # ── Correction helpers (ALULIT_CORRECTION dict) ──────────────────
    def corrected(code: str, abc_hrs: float) -> float:
        factor = ALULIT_CORRECTION.get(code)
        if factor is None:
            return abc_hrs
        return abc_hrs * factor

    def corr_note(code: str, abc_hrs: float) -> str:
        factor = ALULIT_CORRECTION.get(code)
        if factor is None or factor == 1.0:
            return ""
        return f" x {factor:.2f} = {abc_hrs * factor:.2f}h"

    # ── Get ABC Section 2 rate for this cabinet config ─────────────────
    cab_key = (cab_face, job.cabinet_frame, job.cabinet_shape)
    sec2 = SECTION_2_RATES.get(cab_key)
    if not sec2:
        cab_key = (cab_face, CabinetFrame.LIGHT, CabinetShape.RECTANGULAR)
        sec2 = SECTION_2_RATES.get(cab_key, {"labor": 0.228, "material": 2.12})
        result.warnings.append(
            f"Cabinet config not in Section 2 — using "
            f"{cab_key[1].value}/{cab_key[2].value} fallback."
        )
    sec2_rate = sec2["labor"]

    # ── 0110 Design ────────────────────────────────────────────────────
    labor.append(LaborLine(
        work_code="0110", description="Design / Drafting",
        hours=DESIGN_HOURS, unit_type="man-hrs",
        department="Art/Design (100)",
        formula="1.00 hr standard",
        section="Standard",
    ))

    # ── 0200 Fab Layout (cabinet = 1.5x base — simpler than monument) ─
    abc_200 = FAB_LAYOUT_HOURS
    corr_200 = 1.5
    hrs_200 = abc_200 * corr_200
    labor.append(LaborLine(
        work_code="0200", description="Fabrication Layout",
        hours=round(hrs_200, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"ABC {abc_200:.2f}h x {corr_200} (cabinet — simpler layout)",
        section=f"Std x ALULIT {corr_200}x",
    ))
    fab_total += hrs_200

    # ── 0210 Sheet Metal (Section 2: constant + SF x rate x correction) ─
    abc_210 = SECTION_2_CONSTANT + (total_sf * sec2_rate)
    hrs_210 = corrected("0210", abc_210)
    labor.append(LaborLine(
        work_code="0210", description="Sheet Metal",
        hours=round(hrs_210, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"Sec2: {SECTION_2_CONSTANT} + ({total_sf:.1f} SF x {sec2_rate:.3f})" + corr_note("0210", abc_210),
        section=f"2 ({cab_face.value})",
    ))
    fab_total += hrs_210

    # ── 0220 Extrusions (Section 2E: constant + LF x rate) ────────────
    approx_h = math.sqrt(job.sign_sf_per_face) * 1.5
    approx_w = job.sign_sf_per_face / approx_h if approx_h > 0 else 0
    ext_lf = 2 * (approx_h + approx_w)
    abc_220 = SECTION_2E_CONSTANT + (ext_lf * 0.208)
    hrs_220 = corrected("0220", abc_220)
    labor.append(LaborLine(
        work_code="0220", description="Extrusions",
        hours=round(hrs_220, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"Sec2E: {SECTION_2E_CONSTANT} + ({ext_lf:.1f} LF x 0.208)" + corr_note("0220", abc_220),
        section="2E (straight)",
    ))
    fab_total += hrs_220

    # ── 0235 Routing (face routing only) ───────────────────────────────
    abc_235 = total_sf * sec2_rate * 0.40
    hrs_235 = corrected("0235", abc_235)
    labor.append(LaborLine(
        work_code="0235", description="Routing",
        hours=round(hrs_235, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"{total_sf:.1f} SF x {sec2_rate:.3f} x 0.40" + corr_note("0235", abc_235),
        section="2 (derived) — face routing",
    ))
    fab_total += hrs_235

    # ── 0270 Misc Fabrication (assembly + 30% buffer) ──────────────────
    abc_270 = total_sf * sec2_rate
    hrs_270 = corrected("0270", abc_270)
    labor.append(LaborLine(
        work_code="0270", description="Misc Fabrication",
        hours=round(hrs_270, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"{total_sf:.1f} SF x {sec2_rate:.3f}" + corr_note("0270", abc_270),
        section="2 — cabinet assembly",
    ))
    fab_total += hrs_270

    # ── 0340 Electrical Wiring (illuminated only) ──────────────────────
    if job.is_illuminated:
        abc_340 = 1.0 + total_sf * 0.020
        hrs_340 = abc_340  # No ALULIT correction for electrical
        labor.append(LaborLine(
            work_code="0340", description="Electrical Wiring",
            hours=round(hrs_340, 2), unit_type="man-hrs",
            department="Electrical (300)",
            formula=f"1.0 + ({total_sf:.1f} SF x 0.020)",
            section="Est (illuminated cabinet)",
        ))
        fab_total += hrs_340

    # ── 0410 Clean & Etch (Section 5A) ─────────────────────────────────
    paint_rate = SECTION_5A_RATES.get(job.paint_colors, SECTION_5A_RATES[1])
    paint_sf = job.paint_sf if job.paint_sf > 0 else total_sf

    abc_410 = paint_rate["constant"] + (paint_sf * paint_rate["labor"])
    hrs_410 = corrected("0410", abc_410)
    labor.append(LaborLine(
        work_code="0410", description="Clean & Etch",
        hours=round(hrs_410, 2), unit_type="man-hrs",
        department="Paint/Finish (400)",
        formula=f"Sec5A: {paint_rate['constant']} + ({paint_sf:.1f} SF x {paint_rate['labor']})" + corr_note("0410", abc_410),
        section=f"5A ({job.paint_colors} color)",
    ))

    # ── 0420 Prime & Finish (Section 5A) ───────────────────────────────
    abc_420 = paint_rate["constant"] + (paint_sf * paint_rate["labor"])
    hrs_420 = corrected("0420", abc_420)
    labor.append(LaborLine(
        work_code="0420", description="Prime & Finish",
        hours=round(hrs_420, 2), unit_type="man-hrs",
        department="Paint/Finish (400)",
        formula=f"Sec5A: {paint_rate['constant']} + ({paint_sf:.1f} SF x {paint_rate['labor']})" + corr_note("0420", abc_420),
        section=f"5A ({job.paint_colors} color)",
    ))

    # ── Vinyl (if applicable) ──────────────────────────────────────────
    if job.has_vinyl:
        vinyl_sf = total_sf
        labor.append(LaborLine(
            work_code="0520", description="Cut / Weed Vinyl",
            hours=round(1.0 + vinyl_sf * 0.02, 2), unit_type="man-hrs",
            department="Vinyl (500)",
            formula=f"1.0 + ({vinyl_sf:.1f} SF x 0.02)",
            section="Est (vinyl/SF)",
        ))
        labor.append(LaborLine(
            work_code="0550", description="Vinyl Application",
            hours=round(1.0 + vinyl_sf * 0.03, 2), unit_type="man-hrs",
            department="Vinyl (500)",
            formula=f"1.0 + ({vinyl_sf:.1f} SF x 0.03)",
            section="Est (vinyl/SF)",
        ))

    # ── 9200 Fab Overtime (ALULIT OT ratio) ────────────────────────────
    fab_ot = round(fab_total * ALULIT_OT_FAB, 2)
    if fab_ot >= 0.25:
        labor.append(LaborLine(
            work_code="9200", description=f"Fab Overtime ({ALULIT_OT_FAB:.1%} median)",
            hours=fab_ot, unit_type="man-hrs",
            department="Fabrication (200)",
            formula=f"Fab total {fab_total:.2f}h x {ALULIT_OT_FAB} (ALULIT median)",
            section="ALULIT correction",
        ))

    # ── Installation ──────────────────────────────────────────────────

    # 0610 Load/Unload
    load_hrs = 1.0 + 0.5 * max(0, job.num_units - 1)
    install.append(LaborLine(
        work_code="0610", description="Load / Unload",
        hours=round(load_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=f"1.0 + 0.5 x ({job.num_units} - 1) units",
        section="Standard",
    ))

    # 0620 Travel (batch-aware) — warehouse median when no distance given
    _tl = _make_travel_line(job, fallback_hrs=ALULIT_0620_MEDIAN,
                            fallback_formula=f"Warehouse median {ALULIT_0620_MEDIAN}h (ALULIT)")
    if _tl:
        install.append(_tl)

    # 0630 1-Man Install — wall-mounted standard
    install_hrs = ALULIT_0630_MEDIAN
    install.append(LaborLine(
        work_code="0630", description="1 Man & Truck - Install",
        hours=round(install_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=f"Warehouse median {ALULIT_0630_MEDIAN}h (ALULIT)",
        section="ALULIT correction",
    ))

    # 0625 Removal (optional) — warehouse P50 x 1.20
    if job.include_removal:
        _alu_rem = REMOVAL_FLOOR.get("ALULIT", REMOVAL_DEFAULT)
        _alu_src = "REMOVAL_FLOOR[ALULIT]" if "ALULIT" in REMOVAL_FLOOR else "REMOVAL_DEFAULT (ALULIT)"
        install.append(LaborLine(
            work_code="0625", description="Removal",
            hours=round(_alu_rem, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=f"{_alu_src} = {_alu_rem}h (warehouse P50 x 1.20)",
            section="Warehouse removal floor",
        ))

    # 9600 Install Overtime (ALULIT OT ratio)
    inst_ot = round(install_hrs * ALULIT_OT_INSTALL, 2)
    if inst_ot >= 0.25:
        install.append(LaborLine(
            work_code="9600", description=f"Install Overtime ({ALULIT_OT_INSTALL:.1%} median)",
            hours=inst_ot, unit_type="man-hrs",
            department="Installation (600)",
            formula=f"Install {install_hrs:.2f}h x {ALULIT_OT_INSTALL} (ALULIT median)",
            section="ALULIT correction",
        ))

    # ── Assemble result ────────────────────────────────────────────────
    result.labor_lines = labor
    result.install_lines = install
    result.total_man_hours = round(
        sum(l.hours for l in labor if l.unit_type == "man-hrs")
        + sum(l.hours for l in install if l.unit_type == "man-hrs"),
        2
    )
    result.total_crew_hours = round(
        sum(l.hours for l in install if l.unit_type == "CREW-hrs"),
        2
    )

    corrected_codes = [c for c, f in ALULIT_CORRECTION.items() if f is not None and f != 1.0]
    result.warnings.append(
        f"ALULIT corrections applied [LOW CONFIDENCE]: {', '.join(corrected_codes)}. "
        f"Source: MONDF pattern + 30% buffer (n=31 warehouse jobs only). "
        f"Treat estimates as provisional."
    )
    return result


# ── Directional/Wayfinding Estimator ──────────────────────────────────────────

def estimate_directional(job: JobInput) -> EstimateResult:
    """
    Estimate labor for a DIRECT (directional/wayfinding) sign.

    Directional signs are typically small aluminum panels with vinyl graphics
    on posts. Simple fab, simple install.

    Rates derived from warehouse P50 (n=759 jobs, calibrated 2026-03-02).
    Primary fab code: 0220 Extrusions (n=479, 63% of DIRECT jobs).
    Install floor auto-loaded from calibration.json (P50=1.75h x 1.20 = 2.10h).

    Requires sign_sf_per_face > 0 on JobInput (or width/height via app.py).
    """
    total_sf = job.sign_sf_per_face * max(job.num_faces, 1)

    result = EstimateResult(
        total_pf=0.0,
        pf_source="N/A (directional — SF-based, not PF)",
        construction="directional_DIRECT",
        height_category="N/A",
        letter_count=0,
    )

    if total_sf <= 0:
        result.warnings.append("sign_sf_per_face required for directional estimate.")
        return result

    labor: list[LaborLine] = []
    install: list[LaborLine] = []
    fab_total = 0.0

    # ── 0110 Design ──────────────────────────────────────────────────────
    # Warehouse P50=0.50h (n=249) — directionals need minimal design work
    labor.append(LaborLine(
        work_code="0110", description="Design / Drafting",
        hours=0.50, unit_type="man-hrs",
        department="Art/Design (100)",
        formula="0.50h warehouse P50 (n=249)",
        section="DIRECT warehouse",
    ))

    # ── 0200 Fab Layout ──────────────────────────────────────────────────
    # Warehouse P50=0.75h x 1.20 buffer = 0.90h (n=305)
    hrs_200 = 0.90
    labor.append(LaborLine(
        work_code="0200", description="Fabrication Layout",
        hours=hrs_200, unit_type="man-hrs",
        department="Fabrication (200)",
        formula="0.90h (P50=0.75 x 1.20, n=305)",
        section="DIRECT warehouse",
    ))
    fab_total += hrs_200

    # ── 0220 Extrusions (primary fab code for directionals) ───────────────
    # Directionals use aluminum extrusion frames (0220), not sheet metal (0210).
    # Warehouse P50=1.75h (n=479, 63% of DIRECT jobs). 0210 only in 15% of jobs.
    # Scale with SF for larger directory boards.
    hrs_220 = max(2.10, round(total_sf * 0.14, 2))   # P50 x 1.20 = 2.10h base
    labor.append(LaborLine(
        work_code="0220", description="Extrusions",
        hours=hrs_220, unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"max(2.10, {total_sf:.1f} SF x 0.14) [P50=1.75h x 1.20 buffer]",
        section="DIRECT warehouse",
    ))
    fab_total += hrs_220

    # ── 0235 Routing (if routed — many directionals are not) ─────────────
    hrs_235 = round(total_sf * 0.06, 2)
    if hrs_235 >= 0.25:
        labor.append(LaborLine(
            work_code="0235", description="Routing",
            hours=hrs_235, unit_type="man-hrs",
            department="Fabrication (200)",
            formula=f"{total_sf:.1f} SF x 0.06 (if routed) [P50=0.75h n=253]",
            section="DIRECT warehouse",
        ))
        fab_total += hrs_235

    # ── 0270 Misc Fab (brackets, posts) ──────────────────────────────────
    # Warehouse P50=1.25h x 1.20 = 1.50h (n=757, 99% of DIRECT jobs)
    hrs_270 = max(1.50, round(total_sf * 0.10, 2))
    labor.append(LaborLine(
        work_code="0270", description="Misc Fabrication",
        hours=hrs_270, unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"max(1.50, {total_sf:.1f} SF x 0.10) [P50=1.25h x 1.20 n=757]",
        section="DIRECT warehouse",
    ))
    fab_total += hrs_270

    # ── 0410 Clean & Etch ─────────────────────────────────────────────────
    # Warehouse P50=0.50h (n=674). Section 5A formula over-estimates for small flat panels.
    paint_sf = job.paint_sf if job.paint_sf > 0 else total_sf
    hrs_410 = max(0.50, round(paint_sf * 0.05, 2))
    labor.append(LaborLine(
        work_code="0410", description="Clean & Etch",
        hours=hrs_410, unit_type="man-hrs",
        department="Paint/Finish (400)",
        formula=f"max(0.50, {paint_sf:.1f} SF x 0.05) [P50=0.50h n=674]",
        section="DIRECT warehouse",
    ))

    # ── 0420 Prime & Finish ───────────────────────────────────────────────
    # Warehouse P50=1.00h (n=596). Scale modestly with SF.
    hrs_420 = max(0.75, round(paint_sf * 0.07, 2))
    labor.append(LaborLine(
        work_code="0420", description="Prime & Finish",
        hours=hrs_420, unit_type="man-hrs",
        department="Paint/Finish (400)",
        formula=f"max(0.75, {paint_sf:.1f} SF x 0.07) [P50=1.00h n=596]",
        section="DIRECT warehouse",
    ))

    # ── Vinyl (if applicable) ────────────────────────────────────────────
    # Warehouse P50=0.50h for both 0520 and 0550. Old formula (1.0 + SF*rate)
    # had excessive constant overhead. Use SF-based scaling with P50 floor.
    if job.has_vinyl:
        hrs_520 = max(0.50, round(total_sf * 0.06, 2))
        labor.append(LaborLine(
            work_code="0520", description="Cut / Weed Vinyl",
            hours=hrs_520, unit_type="man-hrs",
            department="Vinyl (500)",
            formula=f"max(0.50, {total_sf:.1f} SF x 0.06) [P50=0.50h n=991]",
            section="DIRECT warehouse",
        ))
        hrs_550 = max(0.50, round(total_sf * 0.08, 2))
        labor.append(LaborLine(
            work_code="0550", description="Vinyl Application",
            hours=hrs_550, unit_type="man-hrs",
            department="Vinyl (500)",
            formula=f"max(0.50, {total_sf:.1f} SF x 0.08) [P50=0.50h n=891]",
            section="DIRECT warehouse",
        ))

    # ── 9200 Fab Overtime (3.5% from OT_FACTORS) ────────────────────────
    ot_fab_rate = 0.035
    fab_ot = round(fab_total * ot_fab_rate, 2)
    if fab_ot >= 0.25:
        labor.append(LaborLine(
            work_code="9200", description=f"Fab Overtime ({ot_fab_rate:.1%} DIRECT median)",
            hours=fab_ot, unit_type="man-hrs",
            department="Fabrication (200)",
            formula=f"Fab total {fab_total:.2f}h x {ot_fab_rate} [PROVISIONAL]",
            section="DIRECT warehouse",
        ))

    # ── Installation ─────────────────────────────────────────────────────

    # 0610 Load/Unload
    install.append(LaborLine(
        work_code="0610", description="Load / Unload",
        hours=1.00, unit_type="man-hrs",
        department="Installation (600)",
        formula="1.0h standard [PROVISIONAL]",
        section="DIRECT warehouse",
    ))

    # 0620 Travel (batch-aware)
    _tl = _make_travel_line(job, fallback_hrs=0.60,
                            fallback_formula="0.60h (P50=0.50h x 1.20, DIRECT n=705)")
    if _tl:
        install.append(_tl)

    # 0630 1-Man Install — INSTALL_FLOOR["DIRECT"] auto-loaded from calibration.json
    install_hrs = INSTALL_FLOOR.get("DIRECT", 7.20)
    install.append(LaborLine(
        work_code="0630", description="1 Man & Truck - Install",
        hours=round(install_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=f"INSTALL_FLOOR DIRECT = {install_hrs}h (P50 x 1.20) [PROVISIONAL]",
        section="DIRECT warehouse",
    ))

    # 0625 Removal (optional) — warehouse P50 x 1.20
    if job.include_removal:
        _dir_rem = REMOVAL_FLOOR.get("DIRECT", REMOVAL_DEFAULT)
        install.append(LaborLine(
            work_code="0625", description="Removal",
            hours=round(_dir_rem, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=f"REMOVAL_FLOOR[DIRECT] = {_dir_rem}h (warehouse P50 x 1.20, n=11)",
            section="Warehouse removal floor",
        ))

    # 9600 Install Overtime (from OT_FACTORS: 0.593 prob x 2.52 mean / ~25 normalizer)
    ot_inst_rate = 0.06
    inst_ot = round(install_hrs * ot_inst_rate, 2)
    if inst_ot >= 0.25:
        install.append(LaborLine(
            work_code="9600", description=f"Install Overtime ({ot_inst_rate:.1%} DIRECT median)",
            hours=inst_ot, unit_type="man-hrs",
            department="Installation (600)",
            formula=f"Install {install_hrs:.2f}h x {ot_inst_rate} [PROVISIONAL]",
            section="DIRECT warehouse",
        ))

    # ── Assemble result ──────────────────────────────────────────────────
    result.labor_lines = labor
    result.install_lines = install
    result.total_man_hours = round(
        sum(l.hours for l in labor if l.unit_type == "man-hrs")
        + sum(l.hours for l in install if l.unit_type == "man-hrs"),
        2
    )
    result.total_crew_hours = round(
        sum(l.hours for l in install if l.unit_type == "CREW-hrs"),
        2
    )

    result.warnings.append(
        "[PROVISIONAL] -- no ABC section. Rates derived from warehouse P50 (n=162). "
        "Directional signs = aluminum panels + vinyl on posts. Treat as provisional."
    )
    return result


# ── Dimensional/Gemini Letters Estimator ──────────────────────────────────────

def estimate_dimensional(job: JobInput) -> EstimateResult:
    """
    Estimate labor for GEMINI (dimensional/Gemini letters) signs.

    Dimensional letters are pre-formed plastic or metal letters that are
    purchased, painted, and installed. Minimal fabrication -- mostly paint + install.

    [PROVISIONAL] -- no ABC section. Rates from warehouse P50 (n=115).
    Uses INSTALL_FLOOR["GEMINI"] = 4.20h and OT_FACTORS["GEMINI"].

    Uses letter_count and letter_height_inches from JobInput.
    """
    lc = max(job.letter_count, 1)
    lh = job.letter_height_inches if job.letter_height_inches > 0 else 8.0

    # Estimate face SF from letter dimensions: letter_count * height^2 * 0.006
    est_face_sf = lc * (lh ** 2) * 0.006

    result = EstimateResult(
        total_pf=0.0,
        pf_source="N/A (dimensional -- letter-based, not PF)",
        construction="dimensional_GEMINI",
        height_category="N/A",
        letter_count=lc,
    )

    labor: list[LaborLine] = []
    install: list[LaborLine] = []
    fab_total = 0.0

    # ── 0110 Design ──────────────────────────────────────────────────────
    labor.append(LaborLine(
        work_code="0110", description="Design / Drafting",
        hours=1.00, unit_type="man-hrs",
        department="Art/Design (100)",
        formula="1.00h standard [PROVISIONAL]",
        section="GEMINI warehouse",
    ))

    # ── 0240 Flat Cut Out Letters (layout/trim per letter) ───────────────
    hrs_240 = round(lc * 0.15, 2)
    labor.append(LaborLine(
        work_code="0240", description="Flat Cut Out Letters",
        hours=max(hrs_240, 0.50), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"{lc} letters x 0.15 (layout/trim per letter) [PROVISIONAL]",
        section="GEMINI warehouse",
    ))
    fab_total += max(hrs_240, 0.50)

    # ── 0270 Misc Fab (mounting patterns, hardware) ──────────────────────
    hrs_270 = round(lc * 0.08, 2)
    labor.append(LaborLine(
        work_code="0270", description="Misc Fabrication",
        hours=max(hrs_270, 0.50), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"{lc} letters x 0.08 (mounting patterns, hardware) [PROVISIONAL]",
        section="GEMINI warehouse",
    ))
    fab_total += max(hrs_270, 0.50)

    # ── 0410 Clean & Etch (Section 5A on estimated face SF) ──────────────
    paint_rate = SECTION_5A_RATES.get(job.paint_colors, SECTION_5A_RATES[1])
    paint_sf = job.paint_sf if job.paint_sf > 0 else est_face_sf

    hrs_410 = round(paint_rate["constant"] + (paint_sf * paint_rate["labor"]), 2)
    labor.append(LaborLine(
        work_code="0410", description="Clean & Etch",
        hours=hrs_410, unit_type="man-hrs",
        department="Paint/Finish (400)",
        formula=f"Sec5A: {paint_rate['constant']} + ({paint_sf:.1f} SF x {paint_rate['labor']})",
        section=f"5A ({job.paint_colors} color)",
    ))

    # ── 0420 Prime & Finish (Section 5A) ─────────────────────────────────
    hrs_420 = round(paint_rate["constant"] + (paint_sf * paint_rate["labor"]), 2)
    labor.append(LaborLine(
        work_code="0420", description="Prime & Finish",
        hours=hrs_420, unit_type="man-hrs",
        department="Paint/Finish (400)",
        formula=f"Sec5A: {paint_rate['constant']} + ({paint_sf:.1f} SF x {paint_rate['labor']})",
        section=f"5A ({job.paint_colors} color)",
    ))

    # ── 9200 Fab Overtime — 0.0 per OT_FACTORS (never appears) ──────────
    # OT_FACTORS["GEMINI"] = (0.0, 0.0, ...) — no fab OT

    # ── Installation ─────────────────────────────────────────────────────

    # 0610 Load/Unload
    install.append(LaborLine(
        work_code="0610", description="Load / Unload",
        hours=1.00, unit_type="man-hrs",
        department="Installation (600)",
        formula="1.0h standard [PROVISIONAL]",
        section="GEMINI warehouse",
    ))

    # 0620 Travel (batch-aware)
    _tl = _make_travel_line(job, fallback_hrs=1.25,
                            fallback_formula="Warehouse median 1.25h (GEMINI P50)")
    if _tl:
        install.append(_tl)

    # 0630 1-Man Install — INSTALL_FLOOR["GEMINI"] = 4.20h
    install_hrs = INSTALL_FLOOR.get("GEMINI", 4.20)
    install.append(LaborLine(
        work_code="0630", description="1 Man & Truck - Install",
        hours=round(install_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=f"INSTALL_FLOOR GEMINI = {install_hrs}h (P50 x 1.20) [PROVISIONAL]",
        section="GEMINI warehouse",
    ))

    # 0625 Removal (optional) — warehouse P50 x 1.20
    if job.include_removal:
        _gem_rem = REMOVAL_FLOOR.get("GEMINI", REMOVAL_DEFAULT)
        install.append(LaborLine(
            work_code="0625", description="Removal",
            hours=round(_gem_rem, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=f"REMOVAL_FLOOR[GEMINI] = {_gem_rem}h (warehouse P50 x 1.20, n=13)",
            section="Warehouse removal floor",
        ))

    # 9600 Install Overtime (from OT_FACTORS: 0.478 prob x 1.81 mean)
    ot_inst_rate = 0.048
    inst_ot = round(install_hrs * ot_inst_rate, 2)
    if inst_ot >= 0.25:
        install.append(LaborLine(
            work_code="9600", description=f"Install Overtime ({ot_inst_rate:.1%} GEMINI median)",
            hours=inst_ot, unit_type="man-hrs",
            department="Installation (600)",
            formula=f"Install {install_hrs:.2f}h x {ot_inst_rate} [PROVISIONAL]",
            section="GEMINI warehouse",
        ))

    # ── Assemble result ──────────────────────────────────────────────────
    result.labor_lines = labor
    result.install_lines = install
    result.total_man_hours = round(
        sum(l.hours for l in labor if l.unit_type == "man-hrs")
        + sum(l.hours for l in install if l.unit_type == "man-hrs"),
        2
    )
    result.total_crew_hours = round(
        sum(l.hours for l in install if l.unit_type == "CREW-hrs"),
        2
    )

    result.warnings.append(
        "[PROVISIONAL] -- no ABC section. Rates from warehouse P50 (n=115). "
        "Gemini letters = purchased, minimal fab. Treat as provisional."
    )
    return result


# ── FLAT PANEL ESTIMATOR ────────────────────────────────────────────────────
# Flat aluminum/steel panels with vinyl graphics, face-screwed to fascia.
# NOT a cabinet — no extrusions, no routing, no framing, no LED.
# Example: Home Depot ENTRANCE/EXIT clearance-height panels
#   .080 pre-finished white aluminum, 3M 3630-44 vinyl, tapcons to fascia.
# ─────────────────────────────────────────────────────────────────────────────

def estimate_flatpanel(job: JobInput) -> EstimateResult:
    """Estimate flat panel sign (FLATPNL).

    Flat sheet metal (aluminum or steel) with applied vinyl graphics.
    Face-mounted to fascia/wall with tapcons. No cabinet construction,
    no extrusions, no routing, no electrical.

    Uses panel_sf derived from job.face_sf_override, job.cabinet_sf,
    or job.sign_sf_per_face (first non-zero wins).
    """
    # Flat panels are single-face sheet goods — SF input IS total panel area.
    # No num_faces multiplier (unlike cabinets/monuments).
    total_sf = (
        job.face_sf_override
        or job.cabinet_sf
        or job.sign_sf_per_face
        or 0.0
    )

    result = EstimateResult(
        total_pf=0.0,
        pf_source="N/A (flat panel — SF-based, not PF)",
        construction="flatpanel_FLATPNL",
        height_category="N/A",
        letter_count=0,
    )

    if total_sf <= 0:
        result.warnings.append("panel SF required for flat panel estimate (set cabinet_sf, face_sf_override, or sign_sf_per_face).")
        return result

    labor: list[LaborLine] = []
    install: list[LaborLine] = []
    fab_total = 0.0

    # ── 0110 Design/Layout ──────────────────────────────────────────────
    design_hrs = 1.0
    labor.append(LaborLine(
        work_code="0110", description="Design / Layout",
        hours=round(design_hrs, 2), unit_type="man-hrs",
        department="Art/Design (100)",
        formula="1.0h standard (template from customer exhibit)",
        section="FLATPNL design",
    ))
    fab_total += design_hrs

    # ── 0210 Sheet Metal ────────────────────────────────────────────────
    sheet_hrs = max(1.0, total_sf * 0.033)
    labor.append(LaborLine(
        work_code="0210", description="Sheet Metal - Shear & Deburr",
        hours=round(sheet_hrs, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"max(1.0, {total_sf:.1f} SF x 0.033) = {sheet_hrs:.2f}h",
        section="FLATPNL sheet metal",
    ))
    fab_total += sheet_hrs

    # ── 0410 Prime & Finish ─────────────────────────────────────────────
    # SKIP if substrate is pre-finished (e.g. .080 pre-painted aluminum)
    if job.substrate != "pre-finished":
        paint_hrs = 1.0 + total_sf * 0.017
        labor.append(LaborLine(
            work_code="0410", description="Prime & Finish",
            hours=round(paint_hrs, 2), unit_type="man-hrs",
            department="Paint/Finish (400)",
            formula=f"1.0 + {total_sf:.1f} SF x 0.017 = {paint_hrs:.2f}h",
            section="FLATPNL paint",
        ))
        fab_total += paint_hrs

    # ── 0520 Cut / Weed Vinyl ───────────────────────────────────────────
    vinyl_cut_hrs = 1.0 + total_sf * 0.02
    labor.append(LaborLine(
        work_code="0520", description="Cut / Weed Vinyl",
        hours=round(vinyl_cut_hrs, 2), unit_type="man-hrs",
        department="Vinyl (500)",
        formula=f"1.0 + {total_sf:.1f} SF x 0.02 = {vinyl_cut_hrs:.2f}h",
        section="FLATPNL vinyl cut",
    ))
    fab_total += vinyl_cut_hrs

    # ── 0550 Vinyl Application ──────────────────────────────────────────
    vinyl_app_hrs = 1.0 + total_sf * 0.03
    labor.append(LaborLine(
        work_code="0550", description="Vinyl Application",
        hours=round(vinyl_app_hrs, 2), unit_type="man-hrs",
        department="Vinyl (500)",
        formula=f"1.0 + {total_sf:.1f} SF x 0.03 = {vinyl_app_hrs:.2f}h",
        section="FLATPNL vinyl apply",
    ))
    fab_total += vinyl_app_hrs

    # ── 9200 Fab Overtime (4% of fab total, same as ALULIT) ─────────────
    fab_ot = round(fab_total * 0.04, 2)
    if fab_ot >= 0.25:
        labor.append(LaborLine(
            work_code="9200", description="Fab Overtime (4% FLATPNL)",
            hours=fab_ot, unit_type="man-hrs",
            department="Fabrication (200)",
            formula=f"fab_total {fab_total:.2f}h x 0.04 = {fab_ot:.2f}h",
            section="FLATPNL OT",
        ))

    # ── INSTALLATION ────────────────────────────────────────────────────

    # ── 0630 1 Man & Truck Install ──────────────────────────────────────
    install_hrs = max(1.50, total_sf * 0.05)
    install_floor = INSTALL_FLOOR.get("FLATPNL", 2.40)
    if install_hrs < install_floor:
        install_hrs = install_floor
    install.append(LaborLine(
        work_code="0630", description="1 Man & Truck - Install",
        hours=round(install_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=f"max(1.50, {total_sf:.1f} SF x 0.05) floored to INSTALL_FLOOR={install_floor}h = {install_hrs:.2f}h",
        section="FLATPNL install",
    ))

    # ── 0610 Load / Unload ──────────────────────────────────────────────
    load_hrs = 1.0 + 0.5 * max(0, job.num_units - 1)
    install.append(LaborLine(
        work_code="0610", description="Load / Unload",
        hours=round(load_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=f"1.0 + 0.5 x ({job.num_units} - 1) additional units",
        section="Standard",
    ))

    # ── 0620 Travel (batch-aware) ─────────────────────────────────────────
    _tl = _make_travel_line(job)
    if _tl:
        install.append(_tl)

    # ── 0625 Removal (optional) ─────────────────────────────────────────
    if job.include_removal:
        _fp_rem = REMOVAL_FLOOR.get("FLATPNL", REMOVAL_DEFAULT)
        install.append(LaborLine(
            work_code="0625", description="Removal",
            hours=round(_fp_rem, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=f"REMOVAL_FLOOR.get('FLATPNL', REMOVAL_DEFAULT) = {_fp_rem}h",
            section="FLATPNL removal",
        ))

    # ── Assemble result ─────────────────────────────────────────────────
    result.labor_lines = labor
    result.install_lines = install
    result.total_man_hours = round(
        sum(l.hours for l in labor if l.unit_type == "man-hrs")
        + sum(l.hours for l in install if l.unit_type == "man-hrs"),
        2
    )
    result.total_crew_hours = round(
        sum(l.hours for l in install if l.unit_type == "CREW-hrs"),
        2
    )

    result.warnings.append(
        "[PROVISIONAL] -- no warehouse data for FLATPNL. "
        "Rates estimated from similar types (ALULIT sheet metal, VINYL graphics). "
        "Treat as provisional until warehouse calibration available."
    )
    return result


def estimate_building(job: JobInput) -> EstimateResult:
    """
    Estimate labor for a Building Sign (BLDILL/BLDNON).
    Refined with Task 28 Warehouse Research (n=1301).
    """
    total_sf = job.sign_sf_per_face * job.num_faces
    
    result = EstimateResult(
        total_pf=0.0,
        pf_source="N/A (building — Component Takeoff)",
        construction=f"building_{job.construction_method or 'stick'}",
        height_category="N/A",
        letter_count=0
    )

    if total_sf <= 0:
        result.warnings.append("sign_sf_per_face required for building estimate.")
        return result

    labor = []
    
    # -- 0110 Design/Drafting (Warehouse P50: 0.75h)
    labor.append(LaborLine("0110", "Design/Drafting", 0.75, "man-hrs", "100", "Warehouse P50", "Warehouse"))

    # -- 0200 Layout (Warehouse P50: 1.25h)
    labor.append(LaborLine("0200", "Fabrication Layout", 1.25, "man-hrs", "200", "Warehouse P50", "Warehouse"))

    # -- Construction Logic (Stick vs Extrusion)
    is_extrusion = (job.construction_method in ["extrusion", "thin_frame"])
    
    if is_extrusion:
        import math
        # Perimeter LF for 0220 Extrusions
        approx_h = math.sqrt(total_sf) * 1.5
        approx_w = total_sf / approx_h if approx_h > 0 else 0
        perimeter_lf = 2 * (approx_h + approx_w)
        
        # Labor 0220 (Warehouse P50: 2.0h per segment, scaling with LF)
        hrs_220 = max(2.0, perimeter_lf * 0.15)
        labor.append(LaborLine("0220", "Extrusions", round(hrs_220, 2), "man-hrs", "200", f"{perimeter_lf:.1f} LF @ scale", "Warehouse"))
        
        # BOM
        if job.construction_method == "thin_frame":
            ext_type = "LED_THIN_FRAME"
        else:
            ext_type = "ABC_EXTRUSION_9" if (job.return_depth_in or 0) > 7 else "ABC_EXTRUSION_7"
        result.material_bom.append(f"{EAGLE_INVENTORY[ext_type]}: {perimeter_lf:.1f} LF")
    else:
        # Stick Build (0210 Sheet Metal / Frame)
        hrs_210 = max(1.5, total_sf * 0.18)
        labor.append(LaborLine("0210", "Sheet Metal / Frame", round(hrs_210, 2), "man-hrs", "200", f"{total_sf:.1f} SF @ scale", "Warehouse"))
        result.material_bom.append(f"{EAGLE_INVENTORY['ALUM_ANGLE']}: Frame Stock")

    # -- 0260 Assembly / Faces (Warehouse P50: 0.75h floor, scaling with SF)
    hrs_260 = max(0.75, total_sf * 0.05)
    labor.append(LaborLine("0260", "Assembly / Faces", round(hrs_260, 2), "man-hrs", "200", "Warehouse-derived scale", "Warehouse"))
    
    # -- 0270 Fabrication (Warehouse P50: 1.5h floor)
    hrs_270 = max(1.5, total_sf * 0.10)
    labor.append(LaborLine("0270", "Fabrication", round(hrs_270, 2), "man-hrs", "200", "Warehouse-derived scale", "Warehouse"))

    # -- 0310 Electrical (If Illuminated)
    if job.is_illuminated:
        elec_hrs = max(1.5, total_sf * 0.08)
        labor.append(LaborLine("0310", "Electrical Wiring", round(elec_hrs, 2), "man-hrs", "300", "Standard scale", "Standard"))

    # -- 0630 Install (Warehouse P50 floor)
    inst_hrs = 2.25 if job.is_illuminated else 1.75
    labor.append(LaborLine("0630", "Installation", inst_hrs, "man-hrs", "600", f"P50 floor {inst_hrs}h", "Warehouse"))

    result.labor_lines = labor
    result.total_man_hours = round(sum(l.hours for l in labor), 2)
    result.summary_string = f"{result.total_man_hours:.1f}h total | {result.construction}"
    
    result.warnings.extend(validate_bom_parts(result.material_bom))
    return result

