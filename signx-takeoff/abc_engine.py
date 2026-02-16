"""
abc_engine.py — ABC Sign Estimating Engine for Channel Letters.

Implements Section 4B (Pan Channel), 4C (Reverse Channel), 4A (Strip Channel),
Section 10B (Installation), LED sizing, material BOM, and all installation extras.

Sources:
  - ABC Sign Products Pricing Guide (1974, updated 2026)
  - abc-labor-rates-complete.md (Eagle Sign internal)
  - eagle-rates-fab-cheat-sheet.md (part numbers)

CRITICAL CONVENTIONS:
  - ALL work codes = man-hours EXCEPT 0640/0650 = crew-hours
  - Revenue = `billing` column (NOT `quoted_price`) in warehouse data
  - Logo PF uses biggest coefficient row (0.051 per questionnaire)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


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
    import math
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
        "formula": f"Raceway LF ({raceway_lf:.1f}) x 10 = {hardware_sf:.0f} SF @ $0.58/SF = ${hardware_sf * 0.58:.2f}",
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
    labor.append(LaborLine(
        work_code="0270", description="Sign Fabrication / Mounting",
        hours=round(mount_hrs, 2), unit_type="man-hrs",
        department="Fabrication (200)",
        formula=f"{total_pf:.2f} PF x {rates['mount']}",
        section=f"4{'B' if job.construction == ConstructionType.FACE_LIT else 'C'} {height_cat.value}",
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

    result.labor_lines = labor

    # ── Installation ─────────────────────────────────────────────────────
    install = []
    over_35 = job.install_height_ft > 35
    install_key = "high" if over_35 else "low"
    install_constant = INSTALL_CONSTANT_HIGH if over_35 else INSTALL_CONSTANT_LOW

    install_rate = INSTALL_RATES.get(height_cat, {}).get(install_key, 0.036)
    substrate_mult = SUBSTRATE_MULTIPLIERS.get(job.substrate, 1.0)

    install_crew_hrs = (install_constant + total_pf * install_rate) * substrate_mult

    install.append(LaborLine(
        work_code="0640", description="2 Men & Truck - Install",
        hours=round(install_crew_hrs, 2), unit_type="CREW-hrs",
        department="Installation (600)",
        formula=(f"({install_constant} + {total_pf:.2f} x {install_rate})"
                 f"{f' x {substrate_mult} substrate' if substrate_mult != 1.0 else ''}"),
        section=f"10B {height_cat.value} ({'over 35ft' if over_35 else '0-35ft'})",
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
