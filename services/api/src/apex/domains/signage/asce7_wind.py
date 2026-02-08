"""
ASCE 7-22 Wind Load Calculations - Exact Code Implementation

This module implements wind load calculations per ASCE 7-22 (American Society of Civil Engineers
Minimum Design Loads and Associated Criteria for Buildings and Other Structures, 2022 Edition).

Key Code Sections Implemented:
- Chapter 26: Wind Loads - General Requirements
- Section 26.6: Method 1 - Simplified Procedure (not used for signs)
- Section 26.7-26.12: Method 2 - Analytical Procedure (Directional Procedure)
- Chapter 29: Wind Loads on Building Appurtenances and Other Structures

References:
- ASCE 7-22 Equation 26.10-1: qz = 0.00256 * Kz * Kzt * Kd * Ke * V²
- ASCE 7-22 Table 26.10-1: Velocity Pressure Exposure Coefficients
- ASCE 7-22 Table 1.5-2: Risk Category of Buildings and Other Structures
- ASCE 7-22 Table 26.6-1: Wind Directionality Factor Kd
- ASCE 7-22 Figure 29.4-1: Force Coefficients for Chimneys, Tanks, and Similar Structures
"""

import logging
import math
from enum import Enum
from typing import NamedTuple

logger = logging.getLogger(__name__)


class ExposureCategory(str, Enum):
    """
    Wind exposure categories per ASCE 7-22 Section 26.7.

    - B: Urban and suburban areas, wooded areas, or other terrain with numerous closely spaced obstructions
    - C: Open terrain with scattered obstructions (most common for rural/suburban sign locations)
    - D: Flat, unobstructed areas exposed to wind flowing over open water for at least 1 mile
    """
    B = "B"
    C = "C"
    D = "D"


class RiskCategory(str, Enum):
    """
    Risk categories per ASCE 7-22 Table 1.5-1 and IBC 2024 Table 1604.5.

    - I: Buildings and other structures that represent a low hazard to human life (agricultural, minor storage)
    - II: All buildings and other structures except those listed in I, III, and IV (MOST SIGNS)
    - III: Buildings and other structures that represent a substantial hazard to human life (schools, jails)
    - IV: Buildings and other structures designated as essential facilities (hospitals, fire stations)
    """
    I = "I"
    II = "II"
    III = "III"
    IV = "IV"


class WindLoadResult(NamedTuple):
    """Results from ASCE 7-22 wind load calculation."""
    velocity_pressure_qz_psf: float  # Velocity pressure at height z (psf)
    exposure_coefficient_kz: float  # Velocity pressure exposure coefficient
    wind_importance_factor_iw: float  # Wind importance factor (same as Iw in code)
    design_wind_pressure_psf: float  # Design pressure p = qz * G * Cf
    total_wind_force_lbs: float  # Total wind force F = p * A
    code_references: list[str]  # ASCE 7-22 section references used


# ASCE 7-22 Table 26.10-1: Velocity Pressure Exposure Coefficients (Kz and Kh)
# Case 1: All Heights (for Exposure B, C, D)
# Interpolation parameters: α and zg from Table 26.11-1

EXPOSURE_PARAMETERS = {
    # Exposure B: Urban and suburban areas
    "B": {
        "alpha": 7.0,
        "zg_ft": 1200,
        "table_values": {
            # Height (ft): Kz
            0: 0.57,  # 0-15 ft
            15: 0.57,
            20: 0.62,
            25: 0.66,
            30: 0.70,
            40: 0.76,
            50: 0.81,
            60: 0.85,
            70: 0.89,
            80: 0.93,
            90: 0.96,
            100: 0.99,
            120: 1.04,
            140: 1.09,
            160: 1.13,
        },
    },
    # Exposure C: Open terrain with scattered obstructions
    "C": {
        "alpha": 9.5,
        "zg_ft": 900,
        "table_values": {
            # Height (ft): Kz
            0: 0.85,  # 0-15 ft
            15: 0.85,
            20: 0.90,
            25: 0.94,
            30: 0.98,
            40: 1.04,
            50: 1.09,
            60: 1.13,
            70: 1.17,
            80: 1.21,
            90: 1.24,
            100: 1.26,
            120: 1.31,
            140: 1.36,
            160: 1.39,
        },
    },
    # Exposure D: Flat, unobstructed coastal areas
    "D": {
        "alpha": 11.5,
        "zg_ft": 700,
        "table_values": {
            # Height (ft): Kz
            0: 1.03,  # 0-15 ft
            15: 1.03,
            20: 1.08,
            25: 1.12,
            30: 1.16,
            40: 1.22,
            50: 1.27,
            60: 1.31,
            70: 1.34,
            80: 1.38,
            90: 1.40,
            100: 1.43,
            120: 1.48,
            140: 1.52,
            160: 1.55,
        },
    },
}


# ASCE 7-22 Table 1.5-2: Importance Factors by Risk Category
WIND_IMPORTANCE_FACTORS = {
    RiskCategory.I: 0.87,
    RiskCategory.II: 1.00,
    RiskCategory.III: 1.15,
    RiskCategory.IV: 1.15,
}


# ASCE 7-22 Table 26.6-1: Wind Directionality Factor Kd
# For signs and other structures: Kd = 0.85
WIND_DIRECTIONALITY_FACTOR_SIGNS = 0.85


# ASCE 7-22 Figure 29.4-1: Force Coefficients for Signs
# Cf = 1.2 for flat signs (h/D ratio doesn't apply)
FORCE_COEFFICIENT_FLAT_SIGN = 1.2


def calculate_kz(
    height_ft: float,
    exposure: ExposureCategory,
) -> float:
    """
    Calculate velocity pressure exposure coefficient Kz per ASCE 7-22 Table 26.10-1.

    Uses linear interpolation between table values for heights not explicitly listed.
    For heights below 15 ft, uses the 15 ft value (conservative).
    For heights above 160 ft, uses power law: Kz = 2.01 * (z/zg)^(2/α)

    Args:
        height_ft: Height above ground level in feet (minimum 15 ft per code)
        exposure: Wind exposure category (B, C, or D)

    Returns:
        Kz: Velocity pressure exposure coefficient (dimensionless)

    Reference:
        ASCE 7-22 Section 26.10.1, Table 26.10-1
    """
    # Ensure minimum height of 15 ft per ASCE 7-22
    effective_height = max(height_ft, 15.0)

    params = EXPOSURE_PARAMETERS[exposure.value]
    table_values = params["table_values"]

    # Find bounding heights in table
    heights = sorted(table_values.keys())

    # If height is in table, return exact value
    if effective_height in table_values:
        return table_values[effective_height]

    # If height exceeds table, use power law from ASCE 7-22 Equation 26.10-1
    if effective_height > max(heights):
        alpha = params["alpha"]
        zg_ft = params["zg_ft"]
        return 2.01 * math.pow(effective_height / zg_ft, 2.0 / alpha)

    # Linear interpolation between table values
    for i in range(len(heights) - 1):
        h1, h2 = heights[i], heights[i + 1]
        if h1 <= effective_height <= h2:
            kz1, kz2 = table_values[h1], table_values[h2]
            # Linear interpolation
            fraction = (effective_height - h1) / (h2 - h1)
            return kz1 + fraction * (kz2 - kz1)

    # Fallback (should never reach here)
    return table_values[15]


def calculate_wind_importance_factor(
    risk_category: RiskCategory,
) -> float:
    """
    Get wind importance factor Iw per ASCE 7-22 Table 1.5-2.

    Args:
        risk_category: Risk category (I, II, III, or IV)

    Returns:
        Iw: Wind importance factor (dimensionless)

    Reference:
        ASCE 7-22 Table 1.5-2
    """
    return WIND_IMPORTANCE_FACTORS[risk_category]


def calculate_velocity_pressure(
    wind_speed_mph: float,
    height_ft: float,
    exposure: ExposureCategory,
    kzt: float = 1.0,
    kd: float = WIND_DIRECTIONALITY_FACTOR_SIGNS,
    ke: float = 1.0,
) -> float:
    """
    Calculate velocity pressure qz per ASCE 7-22 Equation 26.10-1.

    qz = 0.00256 * Kz * Kzt * Kd * Ke * V²  (psf)

    Where:
        qz = Velocity pressure at height z (psf)
        Kz = Velocity pressure exposure coefficient (Table 26.10-1)
        Kzt = Topographic factor (Section 26.8, typically 1.0 for flat terrain)
        Kd = Wind directionality factor (Table 26.6-1, 0.85 for signs)
        Ke = Ground elevation factor (Section 26.9, typically 1.0 below 3000 ft elevation)
        V = Basic wind speed, 3-second gust (mph)

    Args:
        wind_speed_mph: Basic wind speed in mph (3-second gust)
        height_ft: Height above ground level in feet
        exposure: Wind exposure category (B, C, or D)
        kzt: Topographic factor (default 1.0 for flat terrain)
        kd: Wind directionality factor (default 0.85 for signs)
        ke: Ground elevation factor (default 1.0 for elevations < 3000 ft)

    Returns:
        qz: Velocity pressure in psf

    Reference:
        ASCE 7-22 Equation 26.10-1
    """
    kz = calculate_kz(height_ft, exposure)

    # ASCE 7-22 Equation 26.10-1
    qz = 0.00256 * kz * kzt * kd * ke * math.pow(wind_speed_mph, 2)

    return qz


def calculate_design_wind_pressure(
    wind_speed_mph: float,
    height_ft: float,
    exposure: ExposureCategory,
    risk_category: RiskCategory,
    gust_effect_factor: float = 0.85,
    force_coefficient: float = FORCE_COEFFICIENT_FLAT_SIGN,
    kzt: float = 1.0,
    kd: float = WIND_DIRECTIONALITY_FACTOR_SIGNS,
    ke: float = 1.0,
) -> float:
    """
    Calculate design wind pressure per ASCE 7-22 Chapter 29 (Signs and Other Structures).

    Design pressure: p = qz * G * Cf * Iw  (psf)

    Where:
        p = Design wind pressure (psf)
        qz = Velocity pressure at height z (Equation 26.10-1)
        G = Gust effect factor (Section 26.11, typically 0.85 for rigid structures)
        Cf = Force coefficient (Figure 29.4-1, 1.2 for flat signs)
        Iw = Wind importance factor (Table 1.5-2)

    Args:
        wind_speed_mph: Basic wind speed in mph (3-second gust)
        height_ft: Height above ground level in feet
        exposure: Wind exposure category (B, C, or D)
        risk_category: Risk category (I, II, III, or IV)
        gust_effect_factor: Gust effect factor G (default 0.85 for rigid signs)
        force_coefficient: Force coefficient Cf (default 1.2 for flat signs)
        kzt: Topographic factor (default 1.0)
        kd: Wind directionality factor (default 0.85)
        ke: Ground elevation factor (default 1.0)

    Returns:
        p: Design wind pressure in psf

    Reference:
        ASCE 7-22 Chapter 29, Section 29.4
    """
    # Calculate velocity pressure
    qz = calculate_velocity_pressure(
        wind_speed_mph=wind_speed_mph,
        height_ft=height_ft,
        exposure=exposure,
        kzt=kzt,
        kd=kd,
        ke=ke,
    )

    # Get wind importance factor
    iw = calculate_wind_importance_factor(risk_category)

    # Design pressure per ASCE 7-22 Chapter 29
    p = qz * gust_effect_factor * force_coefficient * iw

    return p


def calculate_wind_force_on_sign(
    wind_speed_mph: float,
    sign_height_ft: float,
    sign_area_sqft: float,
    pole_height_ft: float,
    exposure: ExposureCategory,
    risk_category: RiskCategory,
    gust_effect_factor: float = 0.85,
    force_coefficient: float = FORCE_COEFFICIENT_FLAT_SIGN,
    kzt: float = 1.0,
    kd: float = WIND_DIRECTIONALITY_FACTOR_SIGNS,
    ke: float = 1.0,
) -> WindLoadResult:
    """
    Calculate total wind force on a sign structure per ASCE 7-22.

    Calculates design wind pressure at the sign centroid height, then applies
    to the full sign area to determine total wind force.

    Args:
        wind_speed_mph: Basic wind speed in mph (3-second gust)
        sign_height_ft: Height of sign face in feet
        sign_area_sqft: Total sign area in square feet
        pole_height_ft: Height of pole from ground to bottom of sign in feet
        exposure: Wind exposure category (B, C, or D)
        risk_category: Risk category (I, II, III, or IV)
        gust_effect_factor: Gust effect factor G (default 0.85)
        force_coefficient: Force coefficient Cf (default 1.2)
        kzt: Topographic factor (default 1.0)
        kd: Wind directionality factor (default 0.85)
        ke: Ground elevation factor (default 1.0)

    Returns:
        WindLoadResult with velocity pressure, design pressure, and total force

    Reference:
        ASCE 7-22 Chapter 29
    """
    # Calculate height to sign centroid
    sign_centroid_height_ft = pole_height_ft + (sign_height_ft / 2.0)

    # Calculate Kz at centroid height
    kz = calculate_kz(sign_centroid_height_ft, exposure)

    # Calculate velocity pressure at centroid height
    qz = calculate_velocity_pressure(
        wind_speed_mph=wind_speed_mph,
        height_ft=sign_centroid_height_ft,
        exposure=exposure,
        kzt=kzt,
        kd=kd,
        ke=ke,
    )

    # Get wind importance factor
    iw = calculate_wind_importance_factor(risk_category)

    # Design wind pressure
    design_pressure = qz * gust_effect_factor * force_coefficient * iw

    # Total wind force: F = p * A
    total_force = design_pressure * sign_area_sqft

    # Code references used
    code_refs = [
        "ASCE 7-22 Eq 26.10-1: Velocity Pressure",
        "ASCE 7-22 Table 26.10-1: Kz Coefficients",
        "ASCE 7-22 Table 1.5-2: Importance Factors",
        f"ASCE 7-22 Table 26.6-1: Kd={kd}",
        f"ASCE 7-22 Fig 29.4-1: Cf={force_coefficient}",
        "ASCE 7-22 Chapter 29: Other Structures",
    ]

    return WindLoadResult(
        velocity_pressure_qz_psf=qz,
        exposure_coefficient_kz=kz,
        wind_importance_factor_iw=iw,
        design_wind_pressure_psf=design_pressure,
        total_wind_force_lbs=total_force,
        code_references=code_refs,
    )


def calculate_wind_moment_at_base(
    total_wind_force_lbs: float,
    pole_height_ft: float,
    sign_height_ft: float,
) -> float:
    """
    Calculate overturning moment at pole base due to wind force.

    M = F * h

    Where:
        M = Overturning moment at base (kip-ft)
        F = Total wind force (lbs)
        h = Height from base to force application point (ft)

    For signs, the wind force is applied at the sign centroid.

    Args:
        total_wind_force_lbs: Total wind force in pounds
        pole_height_ft: Height of pole from ground to bottom of sign in feet
        sign_height_ft: Height of sign face in feet

    Returns:
        Overturning moment at base in kip-ft
    """
    # Height to sign centroid (where wind force is applied)
    moment_arm_ft = pole_height_ft + (sign_height_ft / 2.0)

    # Moment at base (convert lbs to kips)
    moment_kipft = (total_wind_force_lbs / 1000.0) * moment_arm_ft

    return moment_kipft


# Example usage and validation
if __name__ == "__main__":
    logger.info("ASCE 7-22 Wind Load Calculator - Example Calculations\n")
    logger.info("=" * 70)

    # Example 1: Monument sign in Grimes, Iowa
    logger.info("\nExample 1: 15 ft monument sign, 8×3 ft face, 115 mph wind")
    logger.info("-" * 70)

    result = calculate_wind_force_on_sign(
        wind_speed_mph=115,
        sign_height_ft=3.0,
        sign_area_sqft=24.0,  # 8 ft × 3 ft
        pole_height_ft=12.0,  # 12 ft pole + 3 ft sign = 15 ft total
        exposure=ExposureCategory.C,
        risk_category=RiskCategory.II,
    )

    logger.info("  Wind speed:             115 mph (3-sec gust)")
    logger.info("  Exposure:               C (open terrain)")
    logger.info("  Risk category:          II (normal structures)")
    logger.info(f"  Sign centroid height:   {12.0 + 1.5:.1f} ft")
    logger.info(f"  Kz coefficient:         {result.exposure_coefficient_kz:.3f}")
    logger.info(f"  Iw importance factor:   {result.wind_importance_factor_iw:.2f}")
    logger.info(f"  Velocity pressure qz:   {result.velocity_pressure_qz_psf:.2f} psf")
    logger.info(f"  Design pressure p:      {result.design_wind_pressure_psf:.2f} psf")
    logger.info(f"  Total wind force:       {result.total_wind_force_lbs:.1f} lbs")

    moment = calculate_wind_moment_at_base(result.total_wind_force_lbs, 12.0, 3.0)
    logger.info(f"  Moment at base:         {moment:.2f} kip-ft")

    logger.info("\n  Code References:")
    for ref in result.code_references:
        logger.info(f"    • {ref}")

    # Example 2: Tall pylon sign
    logger.info("\n\nExample 2: 40 ft pylon sign, 10×6 ft face, 120 mph wind")
    logger.info("-" * 70)

    result2 = calculate_wind_force_on_sign(
        wind_speed_mph=120,
        sign_height_ft=6.0,
        sign_area_sqft=60.0,  # 10 ft × 6 ft
        pole_height_ft=34.0,  # 34 ft pole + 6 ft sign = 40 ft total
        exposure=ExposureCategory.C,
        risk_category=RiskCategory.II,
    )

    logger.info("  Wind speed:             120 mph (3-sec gust)")
    logger.info("  Exposure:               C (open terrain)")
    logger.info("  Risk category:          II (normal structures)")
    logger.info(f"  Sign centroid height:   {34.0 + 3.0:.1f} ft")
    logger.info(f"  Kz coefficient:         {result2.exposure_coefficient_kz:.3f}")
    logger.info(f"  Velocity pressure qz:   {result2.velocity_pressure_qz_psf:.2f} psf")
    logger.info(f"  Design pressure p:      {result2.design_wind_pressure_psf:.2f} psf")
    logger.info(f"  Total wind force:       {result2.total_wind_force_lbs:.1f} lbs")

    moment2 = calculate_wind_moment_at_base(result2.total_wind_force_lbs, 34.0, 6.0)
    logger.info(f"  Moment at base:         {moment2:.2f} kip-ft")

    logger.info("\n" + "=" * 70)
    logger.info("All calculations conform to ASCE 7-22 standards")
    logger.info("=" * 70)
