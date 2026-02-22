"""
led_catalog.py — LED module, power supply, and sign face material database.

Data sourced from:
  - EagleNeon VBA Toolkit (EagleNeon_Measure.bas) — 11 modules, 6 power supplies
  - LED Wizard 8 v8.0.107.0 (Principal Industries) — sign face materials
  - Part numbers confirmed against Principal Sloan LED Wizard 8 .lwmd catalog

Electrical compliance: NEC Article 600, UL 48, NEC 80% continuous load rule.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict


# ── Data Classes ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LEDModule:
    name: str
    part_number: str
    brand: str
    series: str
    voltage: int            # 12 or 24 VDC
    watts: float            # Power per module (W)
    lumens: float           # Lumens per module (lm)
    efficacy: float         # Luminous efficacy (lm/W)
    mods_per_foot: float    # Modules per linear foot at standard spacing
    spacing_inches: float   # Standard spacing between modules (in)
    max_cascade_single: int # Max modules per run — single-end feed
    max_cascade_double: int # Max modules per run — double-end feed
    min_letter_height: float  # Minimum letter height (in)
    max_letter_height: float  # Maximum letter height (in, 999=no max)
    beam_angle_deg: float   # LED beam angle (degrees)
    color_temp_k: int       # Color temperature (K); 0 = RGB/variable
    ip_rating: str          # IP65, IP68, etc.
    notes: str = ""


@dataclass(frozen=True)
class PowerSupply:
    part_number: str
    brand: str
    voltage: int            # 12 or 24 VDC
    rated_watts: float      # Rated capacity
    safe_watts: float       # NEC 80% continuous load limit
    is_class2: bool         # UL Class 2 (<60V, <=100W total)


@dataclass(frozen=True)
class SignFaceMaterial:
    make: str               # Vendor (Lexan, Acrylite LED, 3M, or "")
    name: str               # Product name (SG305-OB, WDR58 DF, etc.)
    color: str
    thickness_inches: float
    transparency: float     # 0.0–1.0 scale


# ── Module Catalog (11 modules) ────────────────────────────────────────────
# Principal Industries / HanleyLED product line
# All specs from publicly documented principal-led.com and LED Wizard 8

MODULE_CATALOG: list[LEDModule] = [
    # ── NRG Series (high-efficacy) ──
    LEDModule(
        name="NRG Mini 1",
        part_number="HLED-PNMINI12",
        brand="Principal / HanleyLED",
        series="NRG",
        voltage=12, watts=0.36, lumens=76, efficacy=211,
        mods_per_foot=4.4, spacing_inches=2.73,
        max_cascade_single=50, max_cascade_double=100,
        min_letter_height=2, max_letter_height=6,
        beam_angle_deg=120, color_temp_k=6500, ip_rating="IP68",
        notes="Tiny letters only. 12V; prefer double-end feed for runs >4 ft.",
    ),
    LEDModule(
        name="NRG Mini 1 Pro",
        part_number="HLED-PNMINIW7K",
        brand="Principal / HanleyLED",
        series="NRG",
        voltage=24, watts=0.36, lumens=59, efficacy=164,
        mods_per_foot=4.4, spacing_inches=2.73,
        max_cascade_single=75, max_cascade_double=150,
        min_letter_height=2, max_letter_height=6,
        beam_angle_deg=120, color_temp_k=6500, ip_rating="IP68",
        notes="24V version of Mini 1. Longer cascade runs.",
    ),
    LEDModule(
        name="NRG 2 Pro",
        part_number="HLED-PN2W65K",
        brand="Principal / HanleyLED",
        series="NRG",
        voltage=24, watts=0.62, lumens=105, efficacy=170,
        mods_per_foot=1.77, spacing_inches=6.78,
        max_cascade_single=80, max_cascade_double=160,
        min_letter_height=4, max_letter_height=18,
        beam_angle_deg=120, color_temp_k=6500, ip_rating="IP68",
        notes="Best all-around for 4-18\" letters. Eagle Sign default.",
    ),
    LEDModule(
        name="NRG 3 Pro",
        part_number="HLED-PN41-7K24",
        brand="Principal / HanleyLED",
        series="NRG",
        voltage=24, watts=1.0, lumens=170, efficacy=170,
        mods_per_foot=1.45, spacing_inches=8.28,
        max_cascade_single=40, max_cascade_double=80,
        min_letter_height=8, max_letter_height=36,
        beam_angle_deg=120, color_temp_k=6500, ip_rating="IP68",
        notes="Medium-large letters. Higher output for deep channels.",
    ),
    LEDModule(
        name="NRG 4 Pro",
        part_number="HLED-PN4-7K24",
        brand="Principal / HanleyLED",
        series="NRG",
        voltage=24, watts=1.44, lumens=244, efficacy=170,
        mods_per_foot=1.27, spacing_inches=9.45,
        max_cascade_single=40, max_cascade_double=80,
        min_letter_height=12, max_letter_height=999,
        beam_angle_deg=120, color_temp_k=6500, ip_rating="IP68",
        notes="High-output for large or outdoor letters.",
    ),
    # ── Phoenix Series (12V) ──
    LEDModule(
        name="Phoenix 2",
        part_number="HLED-PF2080CW",
        brand="Principal / HanleyLED",
        series="Phoenix",
        voltage=12, watts=0.8, lumens=91, efficacy=114,
        mods_per_foot=1.74, spacing_inches=6.90,
        max_cascade_single=60, max_cascade_double=120,
        min_letter_height=4, max_letter_height=18,
        beam_angle_deg=120, color_temp_k=6500, ip_rating="IP65",
        notes="12V versatile module. Good for retrofits on 12V systems.",
    ),
    LEDModule(
        name="Phoenix 3",
        part_number="HLED-PF3120CW",
        brand="Principal / HanleyLED",
        series="Phoenix",
        voltage=12, watts=1.2, lumens=137, efficacy=114,
        mods_per_foot=1.48, spacing_inches=8.11,
        max_cascade_single=40, max_cascade_double=80,
        min_letter_height=8, max_letter_height=999,
        beam_angle_deg=120, color_temp_k=6500, ip_rating="IP65",
        notes="Large letters on 12V systems. Watch voltage drop on long runs.",
    ),
    # ── Peregrine (RGB-W, 12V) ──
    LEDModule(
        name="Peregrine RGB-W",
        part_number="HLED-RGB2072",
        brand="Principal / HanleyLED",
        series="Peregrine",
        voltage=12, watts=0.92, lumens=68, efficacy=74,
        mods_per_foot=1.5, spacing_inches=8.0,
        max_cascade_single=60, max_cascade_double=120,
        min_letter_height=4, max_letter_height=18,
        beam_angle_deg=120, color_temp_k=0,
        ip_rating="IP65",
        notes="Color-changing. Requires RGBW controller. Lower efficacy.",
    ),
    # ── Hellbender (Principal Sloan, high-CRI) ──
    LEDModule(
        name="Hellbender 5000K",
        part_number="HLED-HLBNDR5K",
        brand="Principal Sloan",
        series="Hellbender",
        voltage=24, watts=1.0, lumens=180, efficacy=180,
        mods_per_foot=1.5, spacing_inches=8.0,
        max_cascade_single=50, max_cascade_double=100,
        min_letter_height=6, max_letter_height=999,
        beam_angle_deg=110, color_temp_k=5000, ip_rating="IP68",
        notes="High-CRI outdoor/interior. Premium exterior channel letters.",
    ),
    # ── Kestrel (12V) ──
    LEDModule(
        name="Kestrel KS-2100",
        part_number="HLED-KS2100W",
        brand="Principal Sloan",
        series="Kestrel",
        voltage=12, watts=0.7, lumens=110, efficacy=157,
        mods_per_foot=2.0, spacing_inches=6.0,
        max_cascade_single=55, max_cascade_double=110,
        min_letter_height=3, max_letter_height=14,
        beam_angle_deg=120, color_temp_k=6500, ip_rating="IP67",
        notes="Mid-range 12V. Good price/performance for interior letters.",
    ),
    # ── Tap Out (24V, flexible strip) ──
    LEDModule(
        name="Tap Out Mod HE 24\"",
        part_number="PL-SF24-TO3-P",
        brand="Principal Sloan",
        series="TapOut",
        voltage=24, watts=2.4, lumens=420, efficacy=175,
        mods_per_foot=0.5, spacing_inches=24.0,
        max_cascade_single=20, max_cascade_double=40,
        min_letter_height=8, max_letter_height=999,
        beam_angle_deg=120, color_temp_k=5000, ip_rating="IP65",
        notes="24\" tap-out module. Continuous runs via tap connectors.",
    ),
]


# ── Power Supply Catalog (6 units) ─────────────────────────────────────────
# HanleyLED / Principal class-2 power supplies (NEC Article 600)

PS_CATALOG: list[PowerSupply] = [
    PowerSupply("H45W-SD-12",  "HanleyLED / Principal", 12,  45,  36.0, True),
    PowerSupply("H60W-SD-12",  "HanleyLED / Principal", 12,  60,  48.0, True),
    PowerSupply("H120W-SD-12", "HanleyLED / Principal", 12, 120,  96.0, False),
    PowerSupply("H75W-SD-24",  "HanleyLED / Principal", 24,  75,  60.0, True),
    PowerSupply("H96W-SD-24",  "HanleyLED / Principal", 24,  96,  76.8, False),
    PowerSupply("H150W-SD-24", "HanleyLED / Principal", 24, 150, 120.0, False),
]


# ── Sign Face Material Catalog ──────────────────────────────────────────────
# From LED Wizard 8 SignFaces.xml

FACE_CATALOG: list[SignFaceMaterial] = [
    SignFaceMaterial("",             "7328",       "white", 0.125,   0.31),
    SignFaceMaterial("",             "7328",       "white", 0.1875,  0.23),
    SignFaceMaterial("",             "7328",       "white", 0.248,   0.17),
    SignFaceMaterial("",             "2447",       "white", 0.125,   0.50),
    SignFaceMaterial("",             "2447",       "white", 0.1875,  0.42),
    SignFaceMaterial("",             "2447",       "white", 0.25,    0.35),
    SignFaceMaterial("Lexan",        "SG305-OB",   "white", 0.075,   0.52),
    SignFaceMaterial("Lexan",        "SG305-OB",   "white", 0.118,   0.44),
    SignFaceMaterial("Lexan",        "SG305-OB",   "white", 0.1575,  0.37),
    SignFaceMaterial("Lexan",        "SG305-OB",   "white", 0.236,   0.27),
    SignFaceMaterial("Acrylite LED", "WDR58 DF",   "white", 0.118,   0.52),
    SignFaceMaterial("Acrylite LED", "WDR58 DF",   "white", 0.177,   0.42),
    SignFaceMaterial("Acrylite LED", "WDR52 DF",   "white", 0.118,   0.34),
    SignFaceMaterial("Acrylite LED", "WDR52 DF",   "white", 0.177,   0.24),
    SignFaceMaterial("3M",           "FS-1",       "white", 0.0787,  0.46),
]


# ── Eagle Sign Internal Part Number Mapping ─────────────────────────────────
# Maps vendor SKUs to Eagle Sign KeyedIn part numbers.
# Unmapped SKUs fall back to vendor SKU in BOM output.

EAGLE_PN_MAP: dict[str, str] = {
    # LED Modules
    "HLED-PN2W65K":  "307-0261",   # NRG 2 Pro (current default in abc_engine)
    # Power Supplies
    "H75W-SD-24":    "307-0265",   # 75W 24V (was "60w or closest")
    "H120W-SD-12":   "307-0264",   # 120W 12V
    "H150W-SD-24":   "307-0170",   # 150W 24V (was "192w")
    # TODO: Brady to confirm remaining PN mappings
}


# ── Wire Gauge Constants ────────────────────────────────────────────────────
# Resistance per foot (Ω/ft) — NEC standard copper values

_WIRE_GAUGES = [
    (10.0, 18, 0.00641),   # ≤10A → 18 AWG
    (16.0, 16, 0.00403),   # ≤16A → 16 AWG
    (999,  14, 0.00253),   # >16A → 14 AWG
]


# ── Helper Functions ────────────────────────────────────────────────────────


def eagle_pn(vendor_sku: str) -> str:
    """Return Eagle Sign internal PN for a vendor SKU, or the SKU itself if unmapped."""
    return EAGLE_PN_MAP.get(vendor_sku, vendor_sku)


def get_module_by_sku(sku: str) -> LEDModule | None:
    """Look up a module by its vendor part number (case-insensitive)."""
    sku_upper = sku.upper()
    for m in MODULE_CATALOG:
        if m.part_number.upper() == sku_upper:
            return m
    return None


def select_module(
    letter_height_in: float,
    construction: str,
    voltage_pref: int = 24,
) -> LEDModule:
    """
    Select the best LED module for given letter height and construction type.

    Scoring: efficacy + voltage preference + NRG series bonus.
    Falls back to NRG 2 Pro if nothing matches.

    Args:
        letter_height_in: Tallest letter height in inches.
        construction: "face_lit", "halo", "strip", "open_face".
        voltage_pref: 0=auto, 12=12V only, 24=24V only.
    """
    best_mod = None
    best_score = -1.0

    for m in MODULE_CATALOG:
        # Voltage filter
        if voltage_pref != 0 and m.voltage != voltage_pref:
            continue
        # Skip RGB modules for non-color jobs
        if m.color_temp_k == 0:
            continue
        # Height compatibility
        if letter_height_in < m.min_letter_height:
            continue
        if letter_height_in > m.max_letter_height:
            continue

        # Score: higher efficacy wins
        score = m.efficacy
        # Prefer 24V for larger letters (more efficient power delivery)
        if m.voltage == 24 and letter_height_in > 10:
            score += 20
        if m.voltage == 12 and letter_height_in <= 10:
            score += 10
        # Prefer NRG Pro series (Eagle Sign standard)
        if m.series == "NRG":
            score += 15

        if score > best_score:
            best_score = score
            best_mod = m

    # Fallback: NRG 2 Pro — universal default
    if best_mod is None:
        best_mod = MODULE_CATALOG[2]  # NRG 2 Pro

    return best_mod


def size_power_supply(total_watts: float, voltage: int) -> tuple[PowerSupply, int]:
    """
    Select power supply using NEC 80% continuous load rule.

    Returns (power_supply, count).
    Required rated capacity = total_watts / 0.80.
    """
    required_rated = total_watts / 0.80

    # Find smallest single PS at correct voltage that fits
    best_ps = None
    for ps in PS_CATALOG:
        if ps.voltage != voltage:
            continue
        if ps.rated_watts >= required_rated:
            if best_ps is None or ps.rated_watts < best_ps.rated_watts:
                best_ps = ps

    if best_ps is not None:
        return best_ps, 1

    # No single PS large enough — use multiples of largest available
    largest_ps = None
    for ps in PS_CATALOG:
        if ps.voltage != voltage:
            continue
        if largest_ps is None or ps.rated_watts > largest_ps.rated_watts:
            largest_ps = ps

    if largest_ps is None:
        # Should never happen with our catalog, but safety fallback
        largest_ps = PS_CATALOG[5]  # H150W-SD-24

    count = math.ceil(required_rated / largest_ps.rated_watts)
    return largest_ps, count


def _select_wire_gauge(current_amps: float) -> tuple[int, float]:
    """Select wire gauge by current. Returns (awg, resistance_per_foot)."""
    for max_amps, awg, r_per_ft in _WIRE_GAUGES:
        if current_amps <= max_amps:
            return awg, r_per_ft
    return 14, 0.00253  # fallback to 14 AWG


def estimate_voltage_drop(
    module: LEDModule,
    total_modules: int,
    cascade_runs: int,
    mods_per_run: int,
) -> tuple[float, int]:
    """
    Estimate voltage drop on longest cascade run.

    Uses NEC round-trip formula: dV = 2 * I * L * R_per_ft.

    Returns (voltage_drop_volts, wire_awg).
    """
    run_length_ft = (mods_per_run / module.mods_per_foot) if module.mods_per_foot > 0 else 0
    current_amps = (mods_per_run * module.watts) / module.voltage if module.voltage > 0 else 0

    awg, r_per_ft = _select_wire_gauge(current_amps)
    v_drop = 2 * current_amps * run_length_ft * r_per_ft

    return round(v_drop, 3), awg


def check_cascade(
    module: LEDModule,
    total_modules: int,
    feed_type: str = "single",
) -> tuple[int, int]:
    """
    Distribute modules across cascade runs respecting max cascade limits.

    Args:
        feed_type: "single", "double", or "halo"

    Returns (num_runs, modules_per_run).
    """
    if feed_type.lower() == "double":
        max_cascade = module.max_cascade_double
    else:
        max_cascade = module.max_cascade_single

    if max_cascade <= 0:
        max_cascade = 80  # safety fallback

    if total_modules <= max_cascade:
        return 1, total_modules

    num_runs = math.ceil(total_modules / max_cascade)
    mods_per_run = math.ceil(total_modules / num_runs)
    return num_runs, mods_per_run


def check_compliance(
    module: LEDModule,
    total_watts: float,
    ps: PowerSupply,
    ps_count: int,
    voltage_drop: float,
    cascade_runs: int,
    total_length_ft: float,
) -> tuple[bool, list[str]]:
    """
    Run NEC Article 600 / UL 48 compliance checks.

    Returns (is_compliant, list_of_notes).
    """
    notes: list[str] = []
    compliant = True

    # 1. Voltage drop must be <3% of supply voltage
    max_vdrop = module.voltage * 0.03
    if voltage_drop > max_vdrop:
        compliant = False
        notes.append(
            f"Voltage drop {voltage_drop:.2f}V exceeds 3% limit ({max_vdrop:.2f}V). "
            "Use shorter runs or heavier wire."
        )

    # 2. PS load factor must be <=80%
    total_ps_capacity = ps.rated_watts * ps_count
    load_pct = (total_watts / total_ps_capacity * 100) if total_ps_capacity > 0 else 100
    if load_pct > 80:
        compliant = False
        notes.append(f"PS load {load_pct:.1f}% exceeds NEC 80% continuous load limit.")

    # 3. UL 48 max run lengths
    max_run_ft = 16.4 if module.voltage == 12 else 32.8
    longest_run = total_length_ft / cascade_runs if cascade_runs > 0 else total_length_ft
    if longest_run > max_run_ft:
        compliant = False
        notes.append(
            f"Longest run {longest_run:.1f}ft exceeds UL 48 max {max_run_ft}ft "
            f"for {module.voltage}V. Add more cascade splits."
        )

    # 4. Informational: PS underloaded
    if load_pct < 50:
        notes.append(f"PS underloaded ({load_pct:.1f}%). Consider smaller supply.")

    # 5. Optimal band
    if 65 <= load_pct <= 80:
        notes.append(f"PS load optimal ({load_pct:.1f}%).")

    if not notes:
        notes.append("All checks passed.")

    return compliant, notes


def catalog_to_dicts() -> dict:
    """Return module and PS catalogs as JSON-serializable dicts."""
    return {
        "modules": [asdict(m) for m in MODULE_CATALOG],
        "power_supplies": [asdict(ps) for ps in PS_CATALOG],
        "face_materials": [asdict(f) for f in FACE_CATALOG],
        "eagle_pn_map": EAGLE_PN_MAP,
    }
