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

import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# numpy/pandas imported lazily inside robust_z_mad/baseline_for_group
# to avoid 30s+ cold-start penalty on every engine load


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
    DIRECT = "DIRECT"     # Directional
    BLDILL = "BLDILL"     # Building Illuminated
    BLDNON = "BLDNON"     # Building Non-Illuminated
    AWNNON = "AWNNON"     # Awning Non-Illuminated
    GEMINI = "GEMINI"     # Dimensional Letters
    LED = "LED"           # LED Conversion/Retrofit
    ALULIT = "ALULIT"     # Aluminum Cabinet Illuminated
    ALUNON = "ALUNON"     # Aluminum Cabinet Non-Illuminated
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
    "GEMINI": 4.20,   # warehouse P50=3.50 × 1.20 = 4.20, n=104
    "LED":    4.50,   # warehouse P50=3.75 × 1.20 = 4.50, n=47
    "ALULIT": 4.80,   # warehouse P50=4.00 × 1.20 = 4.80, n=3 [LOW CONFIDENCE]
}

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

# OT factors — MEDIAN ratios from warehouse (not averages)
MONDF_OT_FAB_NONLIT = 0.051       # 5.1% of fab hrs (n=207, median)
MONDF_OT_FAB_LIT = 0.046          # 4.6% of fab hrs (n=10, median)
MONDF_OT_INSTALL_NONLIT = 0.0     # Median is 0 — most nonlit jobs have no install OT
MONDF_OT_INSTALL_LIT = 0.164      # 16.4% of install hrs (n=10, median)

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
    'AWNNON': ['0110', '0200', '0250', '0270', '0610', '0620', '0630'],
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
    'POLLIT': [r'PYL-', r'PYLON', r'POLE\s*SIGN'],
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

def calculate_led(pf: float, construction: ConstructionType) -> dict:
    """Calculate LED module count and power supply sizing."""
    if construction == ConstructionType.HALO:
        modules = pf * 1.0
    else:
        modules = pf * 1.2

    modules_with_waste = modules * 1.05
    watts = modules_with_waste * 0.72
    capacity = watts / 0.80

    # Power supply sizing
    if capacity <= 80:
        ps_spec = "100W"
        ps_count = 1
        ps_part = "307-0265"  # 60w or closest
    elif capacity <= 120:
        ps_spec = "150W"
        ps_count = 1
        ps_part = "307-0264"  # 120w
    elif capacity <= 160:
        ps_spec = "200W"
        ps_count = 1
        ps_part = "307-0170"  # 192w
    else:
        # Split into 2 supplies
        ps_spec = "2x100W"
        ps_count = 2
        ps_part = "307-0265"

    return {
        "modules": round(modules_with_waste),
        "watts": round(watts, 1),
        "capacity_needed": round(capacity, 1),
        "ps_spec": ps_spec,
        "ps_count": ps_count,
        "ps_part": ps_part,
    }


# ── Material BOM ─────────────────────────────────────────────────────────────

def calculate_materials(pf: float, face_sf: float, return_depth_inches: float,
                        raceway_lf: float,
                        construction: ConstructionType) -> list[dict]:
    """Calculate material BOM with part numbers and quantities."""
    led = calculate_led(pf, construction)
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
    bom.append({
        "item": f"Return Coil .040\" ({return_depth_inches}\" depth)",
        "part": "205-0111",
        "qty": round(coil_lf, 2),
        "unit": "SF",
        "waste": "5%",
        "formula": f"PF ({pf:.2f}) x depth ({return_depth_inches}\"/12) x 1.05",
    })

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

    # Trim Cap 1"
    trim_lf = pf * 1.05  # 5% waste
    bom.append({
        "item": "Trim Cap 1\"",
        "part": "202-0710",
        "qty": round(trim_lf, 2),
        "unit": "LF",
        "waste": "5%",
        "formula": f"PF ({pf:.2f}) x 1.05",
    })

    # LED Modules
    bom.append({
        "item": "LED Modules",
        "part": "307-0261",
        "qty": led["modules"],
        "unit": "EA",
        "waste": "5%",
        "formula": f"PF ({pf:.2f}) x {'1.0' if construction == ConstructionType.HALO else '1.2'} x 1.05",
    })

    # Power Supply
    bom.append({
        "item": f"Power Supply ({led['ps_spec']})",
        "part": led["ps_part"],
        "qty": led["ps_count"],
        "unit": "EA",
        "waste": "0%",
        "formula": f"{led['watts']:.0f}W / 0.80 = {led['capacity_needed']:.0f}W needed",
    })

    # Wire 18AWG
    wire_lf = raceway_lf + 20  # Raceway LF + 20ft
    bom.append({
        "item": "Wire 18AWG",
        "part": "307-0100",
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

    # Optional removal
    include_removal: bool = False

    # Face area override (if known from PDF)
    face_sf_override: Optional[float] = None

    # Sign type (determines correction factors)
    sign_type: SignType = SignType.CLLIT

    # Cabinet dimensions (for Section 2 estimation)
    cabinet_sf: float = 0.0
    cabinet_face: CabinetFace = CabinetFace.SINGLE
    cabinet_shape: CabinetShape = CabinetShape.RECTANGULAR
    cabinet_frame: CabinetFrame = CabinetFrame.LIGHT

    # Paint (for Section 5A estimation)
    paint_colors: int = 1
    paint_sf: float = 0.0  # 0 = auto-calculate from cabinet_sf or face_sf

    # Cabinet install (for Section 10A)
    install_mount_type: str = "wall"  # wall, roof, pipe
    is_first_sign: bool = True

    # Monument-specific fields (for estimate_monument)
    is_illuminated: bool = False   # Has LED/electrical — includes 0260, 0310, 0340
    has_vinyl: bool = True         # Has vinyl graphics — includes 0520, 0550
    has_structural_steel: bool = False  # Steel posts/beams (vs aluminum tube/angle)
    has_footing: bool = False      # Self-performed footing (vs sub)
    footing_sub_cost: float = 0.0  # Subcontracted footing cost ($)
    num_faces: int = 2             # D/F=2, S/F=1
    sign_sf_per_face: float = 0.0  # Square feet per face (for Section 2/5A calc)


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

    # ── 0620 Travel ──────────────────────────────────────────────────────
    if job.miles_one_way > 0:
        travel_hrs = (job.miles_one_way / 50.0) * 2 * job.crew_size
        install.append(LaborLine(
            work_code="0620", description="Travel",
            hours=round(travel_hrs, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=f"({job.miles_one_way} mi / 50) x 2 x {job.crew_size} crew",
            section="Standard",
        ))

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

    # ── 0625 Removal (optional) ──────────────────────────────────────────
    if job.include_removal:
        removal_hrs = install_crew_hrs * 0.65 * 2
        install.append(LaborLine(
            work_code="0625", description="Removal",
            hours=round(removal_hrs, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=f"Install crew-hrs ({install_crew_hrs:.2f}) x 0.65 x 2",
            section="Standard",
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
    result.led_spec = calculate_led(total_pf, job.construction)

    # ── Material BOM ─────────────────────────────────────────────────────
    raceway_lf = job.raceway_lf if job.raceway_lf > 0 else total_pf * 0.3  # estimate
    result.material_bom = calculate_materials(
        total_pf, face_sf, job.return_depth_inches, raceway_lf, job.construction
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
                    db_path: str = "C:/Scripts/signx-warehouse/warehouse/signx.duckdb"
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

    # ── Select correction factors by illumination ──────────────────────
    seg_label = "LIT" if job.is_illuminated else "NONLIT"
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

    # ── 0200 Fab Layout (correction: lit=3.6x, non-lit=1.75x from warehouse)
    abc_200 = FAB_LAYOUT_HOURS
    corr_200 = 3.6 if job.is_illuminated else 1.75  # nonlit: med 2.63h / 1.50h base
    hrs_200 = abc_200 * corr_200
    labor.append(LaborLine(
        work_code="0200", description="Fabrication Layout",
        hours=round(hrs_200, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"ABC {abc_200:.2f}h x {corr_200} ({'lit' if job.is_illuminated else 'non-lit'})",
        section=f"Std x MONDF {corr_200}x",
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

    # 0620 Travel — warehouse median when no distance given
    if job.miles_one_way > 0:
        travel_hrs = (job.miles_one_way / 50.0) * 2 * job.crew_size
        travel_formula = f"({job.miles_one_way} mi / 50) x 2 x {job.crew_size} crew"
    else:
        travel_hrs = MONDF_0620_MEDIAN_NONLIT
        travel_formula = f"Warehouse median {MONDF_0620_MEDIAN_NONLIT}h (n=61, NONLIT)"
    install.append(LaborLine(
        work_code="0620", description="Travel",
        hours=round(travel_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=travel_formula,
        section="Standard",
    ))

    # 0630 1-Man Install — warehouse median by segment (no floor override)
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

    # 0625 Removal (optional)
    if job.include_removal:
        install.append(LaborLine(
            work_code="0625", description="Removal",
            hours=round(MONDF_0625_MEDIAN, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=f"Warehouse median {MONDF_0625_MEDIAN}h (n=23, NONLIT)",
            section="MONDF correction",
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
    Uses install floor x 0.65 x 2 (ABC formula) or warehouse median.
    """
    sign_type_key = job.sign_type.value
    result = EstimateResult(
        total_pf=0.0, pf_source="N/A (removal)",
        construction="removal", height_category="N/A", letter_count=0,
    )
    install: list[LaborLine] = []

    # 0625 Removal
    floor = INSTALL_FLOOR.get(sign_type_key)
    if floor:
        removal_hrs = floor * 0.65 * 2
        formula = f"Install floor {floor}h x 0.65 x 2"
        section = "ABC (install x 0.65 x 2)"
    else:
        removal_hrs = MONDF_0625_MEDIAN
        formula = f"Warehouse median {MONDF_0625_MEDIAN}h (n=23, NONLIT)"
        section = "MONDF correction"

    install.append(LaborLine(
        work_code="0625", description="Removal",
        hours=round(removal_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=formula, section=section,
    ))

    # 0610 Load/Unload
    load_hrs = 1.0 + 0.5 * max(0, job.num_units - 1)
    install.append(LaborLine(
        work_code="0610", description="Load / Unload",
        hours=round(load_hrs, 2), unit_type="man-hrs",
        department="Installation (600)",
        formula=f"1.0 + 0.5 x ({job.num_units} - 1) units",
        section="Standard",
    ))

    # 0620 Travel
    if job.miles_one_way > 0:
        travel_hrs = (job.miles_one_way / 50.0) * 2 * job.crew_size
        install.append(LaborLine(
            work_code="0620", description="Travel",
            hours=round(travel_hrs, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=f"({job.miles_one_way} mi / 50) x 2 x {job.crew_size} crew",
            section="Standard",
        ))

    # 9600 Install OT
    inst_ot = round(removal_hrs * MONDF_OT_INSTALL_FACTOR, 2)
    if inst_ot >= 0.50:
        install.append(LaborLine(
            work_code="9600", description="Install Overtime (50% factor)",
            hours=inst_ot, unit_type="man-hrs",
            department="Installation (600)",
            formula=f"Removal {removal_hrs:.2f}h x {MONDF_OT_INSTALL_FACTOR}",
            section="MONDF correction",
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

    # ── Fabrication codes (SF-based) ──────────────────────────────────
    fab_codes = ['0250', '0260', '0270']
    fab_total = 0.0
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

    # 0620 Travel (SF-based rate OR miles if provided)
    if job.miles_one_way > 0:
        travel_hrs = (job.miles_one_way / 50.0) * 2 * job.crew_size
        install.append(LaborLine(
            work_code="0620", description="Travel",
            hours=round(travel_hrs, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=f"({job.miles_one_way} mi / 50) x 2 x {job.crew_size} crew",
            section="Standard",
        ))
    else:
        travel_rate = AWNING_LABOR_PER_SF.get('0620', 0.040)
        travel_hrs = total_sf * travel_rate
        install.append(LaborLine(
            work_code="0620", description="Travel",
            hours=round(travel_hrs, 2), unit_type="man-hrs",
            department="Installation (600)",
            formula=f"{total_sf:.1f} SF x {travel_rate:.3f}/SF",
            section="Awning (Eagle actuals)",
        ))

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
