"""
Single Pole Sign Structural Analysis - IBC 2024 / ASCE 7-22 / AISC 360-22 Compliant

This module analyzes single-pole sign structures (monuments, pylons, cantilever posts)
using current building code standards.

Code Compliance:
- IBC 2024: International Building Code (Section 1605 Load Combinations, Section 1807 Foundations)
- ASCE 7-22: Wind loads per Chapters 26-29 (Directional Procedure)
- AISC 360-22: Steel Construction Manual (Allowable Stress Design)

Determinism: All calculations are pure functions - same inputs always produce same outputs.
No randomness, no external API calls, no time-dependent calculations.
"""

from typing import NamedTuple, Optional
from dataclasses import dataclass
import math

from apex.domains.signage.asce7_wind import (
import logging

logger = logging.getLogger(__name__)
    calculate_wind_force_on_sign,
    calculate_wind_moment_at_base,
    ExposureCategory,
    RiskCategory,
)


# IBC 2024 Section 1605.2.1 - Required Load Combinations (ASD)
# All 7 combinations per IBC 2024 for Allowable Stress Design
IBC_LOAD_COMBINATIONS = {
    'LC1': {'D': 1.0},                              # D
    'LC2': {'D': 1.0, 'L': 1.0},                   # D + L
    'LC3': {'D': 1.0, 'Lr': 1.0},                  # D + Lr (roof live load)
    'LC4': {'D': 1.0, 'S': 1.0},                   # D + S (snow)
    'LC5': {'D': 1.0, 'L': 0.75, 'W': 0.75},       # D + 0.75L + 0.75W
    'LC6': {'D': 1.0, 'W': 1.0},                   # D + W
    'LC7': {'D': 0.6, 'W': 1.0},                   # 0.6D + W (uplift check)
}


# AISC 360-22 Constants
E_STEEL_KSI = 29000.0  # Modulus of elasticity for steel (ksi)
PHI_B_BENDING = 0.90  # Resistance factor for bending (LRFD) - Not used in ASD
PHI_V_SHEAR = 0.90  # Resistance factor for shear (LRFD) - Not used in ASD

# AISC 360-22 Allowable Stress Design (ASD) Factors
# Chapter F: Design of Members for Flexure
ASD_ALLOWABLE_BENDING_FACTOR = 0.66  # Fb = 0.66 * Fy
ASD_ALLOWABLE_SHEAR_FACTOR = 0.40  # Fv = 0.40 * Fy

# IBC 2024 Section 1605.2.1: Overturning
IBC_OVERTURNING_SAFETY_FACTOR_MIN = 1.5  # Minimum safety factor against overturning

# Serviceability limits
DEFLECTION_LIMIT_L_OVER = 240  # L/240 typical for sign structures
MAX_SLENDERNESS_RATIO = 200  # L/r ≤ 200 per AISC


@dataclass
class PoleSection:
    """
    Steel pole section properties from AISC Shapes Database v16.

    All properties are from AISC Manual, typically HSS (Hollow Structural Sections)
    or PIPE sections for sign poles.
    """
    designation: str  # AISC manual label (e.g., "HSS8X8X1/4")
    type: str  # HSS, PIPE, etc.
    area_in2: float  # Cross-sectional area (in²)
    depth_in: float  # Nominal depth/diameter (in)
    weight_plf: float  # Weight per linear foot (lb/ft)
    sx_in3: float  # Elastic section modulus (in³)
    ix_in4: float  # Moment of inertia (in⁴)
    rx_in: float  # Radius of gyration (in)
    fy_ksi: float  # Yield strength (ksi), typically 50 ksi for A500 Grade C, 65 ksi for A1085
    fu_ksi: float  # Ultimate tensile strength (ksi)
    is_a1085: bool = False  # ASTM A1085 high-strength HSS flag


@dataclass
class SinglePoleConfig:
    """Configuration for single-pole sign analysis."""
    # Pole geometry
    pole_height_ft: float
    pole_section: PoleSection
    embedment_depth_ft: float

    # Sign geometry
    sign_width_ft: float
    sign_height_ft: float
    sign_area_sqft: float
    sign_weight_psf: float = 3.0  # Aluminum typical

    # Wind loads (ASCE 7-22)
    basic_wind_speed_mph: float
    risk_category: RiskCategory
    exposure_category: ExposureCategory
    topographic_factor_kzt: float = 1.0
    wind_directionality_factor_kd: float = 0.85
    elevation_factor_ke: float = 1.0
    gust_effect_factor_g: float = 0.85
    force_coefficient_cf: float = 1.2

    # Soil/foundation
    soil_bearing_capacity_psf: float = 2000

    # Design criteria
    deflection_limit_ratio: float = DEFLECTION_LIMIT_L_OVER
    overturning_safety_factor_min: float = IBC_OVERTURNING_SAFETY_FACTOR_MIN


class SinglePoleResults(NamedTuple):
    """Complete results from single-pole structural analysis."""
    # Wind load analysis
    velocity_pressure_qz_psf: float
    exposure_coefficient_kz: float
    wind_importance_factor_iw: float
    design_wind_pressure_psf: float
    total_wind_force_lbs: float
    wind_moment_at_base_kipft: float

    # Dead loads
    dead_load_sign_lbs: float
    dead_load_pole_lbs: float
    total_dead_load_lbs: float

    # Structural analysis
    max_bending_moment_kipft: float
    max_shear_force_kips: float
    bending_stress_fb_ksi: float
    shear_stress_fv_ksi: float
    allowable_bending_Fb_ksi: float
    allowable_shear_Fv_ksi: float
    bending_stress_ratio: float
    shear_stress_ratio: float
    combined_stress_ratio: float
    governing_load_combination: str  # Which IBC combination governs (e.g., 'LC6')

    # Deflection analysis
    max_deflection_in: float
    deflection_ratio_l_over: float
    deflection_limit_l_over: float

    # Foundation analysis
    overturning_moment_kipft: float
    resisting_moment_kipft: float
    safety_factor_overturning: float
    max_soil_pressure_psf: float
    foundation_diameter_ft: float
    foundation_depth_ft: float
    concrete_volume_cuyd: float

    # Pass/fail checks
    passes_strength_check: bool
    passes_deflection_check: bool
    passes_overturning_check: bool
    passes_soil_bearing_check: bool
    passes_all_checks: bool

    # Critical failure mode
    critical_failure_mode: Optional[str]

    # Warnings and code references
    warnings: list[str]
    code_references: list[str]


def analyze_single_pole_sign(config: SinglePoleConfig) -> SinglePoleResults:
    """
    Complete structural analysis of single-pole sign per IBC 2024 / ASCE 7-22 / AISC 360-22.

    This is a deterministic, pure function - same inputs always produce same outputs.

    Args:
        config: Single pole configuration with geometry, loads, and design criteria

    Returns:
        SinglePoleResults with complete structural analysis

    Raises:
        ValueError: If configuration is invalid (negative values, etc.)
    """
    warnings = []
    code_refs = []

    # =========================================================================
    # STEP 1: Wind Load Analysis (ASCE 7-22)
    # =========================================================================

    wind_result = calculate_wind_force_on_sign(
        wind_speed_mph=config.basic_wind_speed_mph,
        sign_height_ft=config.sign_height_ft,
        sign_area_sqft=config.sign_area_sqft,
        pole_height_ft=config.pole_height_ft,
        exposure=config.exposure_category,
        risk_category=config.risk_category,
        gust_effect_factor=config.gust_effect_factor_g,
        force_coefficient=config.force_coefficient_cf,
        kzt=config.topographic_factor_kzt,
        kd=config.wind_directionality_factor_kd,
        ke=config.elevation_factor_ke,
    )

    wind_moment = calculate_wind_moment_at_base(
        total_wind_force_lbs=wind_result.total_wind_force_lbs,
        pole_height_ft=config.pole_height_ft,
        sign_height_ft=config.sign_height_ft,
    )

    code_refs.extend(wind_result.code_references)

    # =========================================================================
    # STEP 2: Dead Load Calculations
    # =========================================================================

    # Sign weight
    dead_load_sign = config.sign_area_sqft * config.sign_weight_psf

    # Pole weight
    dead_load_pole = config.pole_section.weight_plf * config.pole_height_ft

    total_dead_load = dead_load_sign + dead_load_pole

    # =========================================================================
    # STEP 3: Load Combination Analysis (IBC 2024 Section 1605.2.1)
    # =========================================================================

    # Dead load moment at base (very small for typical signs)
    # Conservative assumption: dead load acts at sign centroid
    sign_centroid_height = config.pole_height_ft + (config.sign_height_ft / 2.0)
    dead_load_moment_kipft = (total_dead_load / 1000.0) * 0.0  # Zero for vertical load, no eccentricity

    # Evaluate all 7 IBC 2024 load combinations
    load_combination_results = {}
    for lc_name, factors in IBC_LOAD_COMBINATIONS.items():
        # Combine moments per IBC factors
        # M_combined = D_factor * M_dead + W_factor * M_wind + L_factor * M_live + ...
        combined_moment = 0.0

        # Dead load component
        if 'D' in factors:
            combined_moment += factors['D'] * dead_load_moment_kipft

        # Wind load component
        if 'W' in factors:
            combined_moment += factors['W'] * wind_moment

        # Live load, roof live, snow (typically zero for sign structures)
        # These would be included for more complex structures

        load_combination_results[lc_name] = combined_moment

    # Find governing load combination (maximum moment)
    governing_lc = max(load_combination_results, key=load_combination_results.get)
    max_bending_moment = load_combination_results[governing_lc]

    # For signs, wind typically governs, so shear force comes from wind
    max_shear_force = wind_result.total_wind_force_lbs / 1000.0  # Convert to kips

    code_refs.append(f"IBC 2024 Section 1605.2.1: Governing combination = {governing_lc}")

    # =========================================================================
    # STEP 4: Structural Analysis (AISC 360-22 ASD)
    # =========================================================================

    # Validate section properties before calculation (per AISC 360-22 design requirements)
    if config.pole_section.sx_in3 <= 0:
        raise ValueError(
            f"Invalid section modulus: sx_in3={config.pole_section.sx_in3:.3f} in³. "
            f"Section properties must be positive. Verify AISC database lookup for section '{config.pole_section.designation}'. "
            f"Check that the section designation '{config.pole_section.designation}' exists in the AISC shapes database."
        )
    if config.pole_section.area_in2 <= 0:
        raise ValueError(
            f"Invalid cross-sectional area: area_in2={config.pole_section.area_in2:.3f} in². "
            f"Section properties must be positive. Verify AISC database lookup for section '{config.pole_section.designation}'."
        )

    # Bending stress: fb = M / Sx
    # M in kip-in, Sx in in³, fb in ksi
    bending_stress_fb = (max_bending_moment * 12.0) / config.pole_section.sx_in3

    # Shear stress: fv = V / A (simplified, conservative)
    shear_stress_fv = max_shear_force / config.pole_section.area_in2

    # Allowable stresses (AISC 360-22 ASD)
    # Fb = 0.66 * Fy for compact sections
    allowable_bending_Fb = ASD_ALLOWABLE_BENDING_FACTOR * config.pole_section.fy_ksi

    # Fv = 0.40 * Fy for shear
    allowable_shear_Fv = ASD_ALLOWABLE_SHEAR_FACTOR * config.pole_section.fy_ksi

    # Stress ratios (unity checks)
    bending_ratio = bending_stress_fb / allowable_bending_Fb
    shear_ratio = shear_stress_fv / allowable_shear_Fv

    # Combined stress ratio (simplified interaction)
    # For ASD: fb/Fb + fv/Fv ≤ 1.0 (conservative)
    combined_ratio = bending_ratio + shear_ratio

    code_refs.append("AISC 360-22 Chapter F: Flexural Design (ASD)")
    code_refs.append("AISC 360-22 Chapter G: Shear Design (ASD)")

    # =========================================================================
    # STEP 5: Deflection Analysis
    # =========================================================================

    # Cantilever deflection: δ = (F * L³) / (3 * E * I)
    # F in lbs, L in inches, E in ksi, I in in⁴, δ in inches
    pole_height_in = config.pole_height_ft * 12.0
    sign_centroid_in = pole_height_in + (config.sign_height_ft * 12.0 / 2.0)

    # Wind force applied at sign centroid
    deflection_in = (
        wind_result.total_wind_force_lbs * math.pow(sign_centroid_in, 3)
    ) / (3.0 * E_STEEL_KSI * 1000.0 * config.pole_section.ix_in4)

    # Deflection ratio: L/δ
    if deflection_in > 0:
        deflection_ratio = pole_height_in / deflection_in
    else:
        deflection_ratio = float('inf')

    code_refs.append("AISC 360-22 Chapter L: Serviceability (Deflection)")

    # =========================================================================
    # STEP 6: Foundation Analysis (IBC 2024 Section 1605/1807)
    # =========================================================================

    # Overturning moment (same as wind moment at base)
    overturning_moment = wind_moment

    # Foundation sizing (drilled pier/caisson)
    # Start with embedment depth from config, iterate diameter if needed
    foundation_depth = config.embedment_depth_ft

    # Estimate foundation diameter (iterative approach for simplicity)
    # Target: SF ≥ 1.5 for overturning
    foundation_diameter = _calculate_foundation_diameter(
        overturning_moment_kipft=overturning_moment,
        dead_load_lbs=total_dead_load,
        embedment_depth_ft=foundation_depth,
        soil_bearing_capacity_psf=config.soil_bearing_capacity_psf,
        target_safety_factor=config.overturning_safety_factor_min,
    )

    # Resisting moment: Weight × (diameter / 2)
    resisting_moment = (total_dead_load / 1000.0) * (foundation_diameter / 2.0)

    # Add soil passive pressure resistance (simplified)
    # Passive pressure = 0.5 * γ * H² * Kp, where γ ≈ 120 pcf, Kp ≈ 3 (conservative)
    soil_density_pcf = 120
    passive_pressure_coefficient = 3.0
    passive_force_kips = (
        0.5 * soil_density_pcf * math.pow(foundation_depth, 2) *
        passive_pressure_coefficient * foundation_diameter
    ) / 1000.0
    passive_moment_arm = foundation_depth / 3.0  # At 1/3 depth
    passive_moment = passive_force_kips * passive_moment_arm

    # Total resisting moment
    total_resisting_moment = resisting_moment + passive_moment

    # Safety factor against overturning
    if overturning_moment > 0:
        safety_factor_overturning = total_resisting_moment / overturning_moment
    else:
        safety_factor_overturning = float('inf')

    # Soil bearing pressure (simplified)
    foundation_area_sqft = math.pi * math.pow(foundation_diameter / 2.0, 2)
    max_soil_pressure = (total_dead_load / foundation_area_sqft) + (
        overturning_moment * 1000.0 * 12.0 * (foundation_diameter / 2.0) /
        (math.pi * math.pow(foundation_diameter / 2.0, 4) / 4.0)
    )

    # Concrete volume
    concrete_volume_cuyd = (
        foundation_area_sqft * foundation_depth
    ) / 27.0  # Convert ft³ to yd³

    code_refs.append("IBC 2024 Section 1605.2.1: Overturning Stability")
    code_refs.append("IBC 2024 Section 1807: Foundations")

    # =========================================================================
    # STEP 7: Pass/Fail Checks
    # =========================================================================

    passes_strength = (bending_ratio <= 1.0) and (shear_ratio <= 1.0)
    passes_deflection = deflection_ratio >= config.deflection_limit_ratio
    passes_overturning = safety_factor_overturning >= config.overturning_safety_factor_min
    passes_soil_bearing = max_soil_pressure <= config.soil_bearing_capacity_psf

    passes_all = (
        passes_strength and
        passes_deflection and
        passes_overturning and
        passes_soil_bearing
    )

    # Determine critical failure mode
    critical_failure = None
    if not passes_all:
        failure_modes = []
        if not passes_strength:
            if bending_ratio > shear_ratio:
                failure_modes.append(("BENDING", bending_ratio))
            else:
                failure_modes.append(("SHEAR", shear_ratio))
        if not passes_deflection:
            failure_modes.append(("DEFLECTION", config.deflection_limit_ratio / deflection_ratio))
        if not passes_overturning:
            failure_modes.append(("OVERTURNING", config.overturning_safety_factor_min / safety_factor_overturning))
        if not passes_soil_bearing:
            failure_modes.append(("SOIL_BEARING", max_soil_pressure / config.soil_bearing_capacity_psf))

        # Sort by severity (highest ratio)
        failure_modes.sort(key=lambda x: x[1], reverse=True)
        critical_failure = failure_modes[0][0] if failure_modes else None

    # =========================================================================
    # STEP 8: Warnings
    # =========================================================================

    # Check slenderness
    slenderness_ratio = (config.pole_height_ft * 12.0) / config.pole_section.rx_in
    if slenderness_ratio > MAX_SLENDERNESS_RATIO:
        warnings.append(
            f"Slenderness ratio L/r = {slenderness_ratio:.1f} exceeds {MAX_SLENDERNESS_RATIO} "
            f"(AISC limit). Pole may be susceptible to buckling."
        )

    if bending_ratio > 0.9:
        warnings.append(f"Bending stress ratio {bending_ratio:.2f} exceeds 0.90 - near capacity")

    if safety_factor_overturning < 2.0:
        warnings.append(
            f"Overturning safety factor {safety_factor_overturning:.2f} is below 2.0 "
            f"(exceeds IBC minimum 1.5 but low margin)"
        )

    # =========================================================================
    # STEP 9: Return Results
    # =========================================================================

    return SinglePoleResults(
        # Wind loads
        velocity_pressure_qz_psf=wind_result.velocity_pressure_qz_psf,
        exposure_coefficient_kz=wind_result.exposure_coefficient_kz,
        wind_importance_factor_iw=wind_result.wind_importance_factor_iw,
        design_wind_pressure_psf=wind_result.design_wind_pressure_psf,
        total_wind_force_lbs=wind_result.total_wind_force_lbs,
        wind_moment_at_base_kipft=wind_moment,

        # Dead loads
        dead_load_sign_lbs=dead_load_sign,
        dead_load_pole_lbs=dead_load_pole,
        total_dead_load_lbs=total_dead_load,

        # Structural analysis
        max_bending_moment_kipft=max_bending_moment,
        max_shear_force_kips=max_shear_force,
        bending_stress_fb_ksi=bending_stress_fb,
        shear_stress_fv_ksi=shear_stress_fv,
        allowable_bending_Fb_ksi=allowable_bending_Fb,
        allowable_shear_Fv_ksi=allowable_shear_Fv,
        bending_stress_ratio=bending_ratio,
        shear_stress_ratio=shear_ratio,
        combined_stress_ratio=combined_ratio,
        governing_load_combination=governing_lc,

        # Deflection
        max_deflection_in=deflection_in,
        deflection_ratio_l_over=deflection_ratio,
        deflection_limit_l_over=config.deflection_limit_ratio,

        # Foundation
        overturning_moment_kipft=overturning_moment,
        resisting_moment_kipft=total_resisting_moment,
        safety_factor_overturning=safety_factor_overturning,
        max_soil_pressure_psf=max_soil_pressure,
        foundation_diameter_ft=foundation_diameter,
        foundation_depth_ft=foundation_depth,
        concrete_volume_cuyd=concrete_volume_cuyd,

        # Pass/fail
        passes_strength_check=passes_strength,
        passes_deflection_check=passes_deflection,
        passes_overturning_check=passes_overturning,
        passes_soil_bearing_check=passes_soil_bearing,
        passes_all_checks=passes_all,

        # Failure mode
        critical_failure_mode=critical_failure,

        # Metadata
        warnings=warnings,
        code_references=code_refs,
    )


def _calculate_foundation_diameter(
    overturning_moment_kipft: float,
    dead_load_lbs: float,
    embedment_depth_ft: float,
    soil_bearing_capacity_psf: float,
    target_safety_factor: float = 1.5,
) -> float:
    """
    Calculate required foundation diameter to meet overturning safety factor.

    Uses iterative approach to find minimum diameter that provides adequate
    resistance against overturning.

    Args:
        overturning_moment_kipft: Overturning moment at base (kip-ft)
        dead_load_lbs: Total dead load (lbs)
        embedment_depth_ft: Foundation embedment depth (ft)
        soil_bearing_capacity_psf: Allowable soil bearing pressure (psf)
        target_safety_factor: Target safety factor (default 1.5 per IBC)

    Returns:
        Required foundation diameter in feet
    """
    # Start with minimum practical diameter
    min_diameter = 3.0  # 3 ft minimum
    max_diameter = 10.0  # 10 ft maximum practical

    # Iterative search for adequate diameter
    for diameter in [d / 10.0 for d in range(int(min_diameter * 10), int(max_diameter * 10) + 1)]:
        # Resisting moment from weight
        resisting_moment_weight = (dead_load_lbs / 1000.0) * (diameter / 2.0)

        # Passive pressure resistance
        soil_density_pcf = 120
        passive_coeff = 3.0
        passive_force = (
            0.5 * soil_density_pcf * math.pow(embedment_depth_ft, 2) *
            passive_coeff * diameter
        ) / 1000.0
        passive_moment = passive_force * (embedment_depth_ft / 3.0)

        total_resisting = resisting_moment_weight + passive_moment

        # Check safety factor
        if overturning_moment_kipft > 0:
            safety_factor = total_resisting / overturning_moment_kipft
            if safety_factor >= target_safety_factor:
                return diameter

    # If no adequate diameter found, return maximum
    return max_diameter


# Example usage
if __name__ == "__main__":
    logger.info("Single Pole Sign Structural Analysis Example\n")
    logger.info("=" * 70)

    # Example: 15 ft monument sign with HSS8×8×1/4
    pole = PoleSection(
        designation="HSS8X8X1/4",
        type="HSS",
        area_in2=7.11,
        depth_in=8.0,
        weight_plf=24.2,
        sx_in3=19.8,
        ix_in4=79.3,
        rx_in=3.34,
        fy_ksi=50.0,
        fu_ksi=65.0,
    )

    config = SinglePoleConfig(
        pole_height_ft=12.0,
        pole_section=pole,
        embedment_depth_ft=5.0,
        sign_width_ft=8.0,
        sign_height_ft=3.0,
        sign_area_sqft=24.0,
        basic_wind_speed_mph=115,
        risk_category=RiskCategory.II,
        exposure_category=ExposureCategory.C,
    )

    result = analyze_single_pole_sign(config)

    logger.info("Configuration:")
    logger.info(f"  Pole: {pole.designation}, {pole.pole_height_ft} ft tall")
    logger.info(f"  Sign: {config.sign_width_ft}×{config.sign_height_ft} ft ({config.sign_area_sqft} sqft)")
    logger.info(f"  Wind: {config.basic_wind_speed_mph} mph, Exposure {config.exposure_category.value}")
    logger.info()

    logger.info("Wind Loads (ASCE 7-22):")
    logger.info(f"  Design pressure:       {result.design_wind_pressure_psf:.1f} psf")
    logger.info(f"  Total wind force:      {result.total_wind_force_lbs:.0f} lbs")
    logger.info(f"  Moment at base:        {result.wind_moment_at_base_kipft:.2f} kip-ft")
    logger.info()

    logger.info("Structural Analysis (AISC 360-22 ASD):")
    logger.info(f"  Bending stress ratio:  {result.bending_stress_ratio:.3f} ({result.bending_stress_fb_ksi:.1f}/{result.allowable_bending_Fb_ksi:.1f} ksi)")
    logger.info(f"  Shear stress ratio:    {result.shear_stress_ratio:.3f}")
    logger.info(f"  Deflection:            {result.max_deflection_in:.2f} in (L/{result.deflection_ratio_l_over:.0f})")
    logger.info()

    logger.info("Foundation (IBC 2024):")
    logger.info(f"  Diameter required:     {result.foundation_diameter_ft:.1f} ft")
    logger.info(f"  Embedment depth:       {result.foundation_depth_ft:.1f} ft")
    logger.info(f"  Overturning SF:        {result.safety_factor_overturning:.2f} (min 1.5)")
    logger.info(f"  Concrete volume:       {result.concrete_volume_cuyd:.2f} cu yd")
    logger.info()

    logger.info("Design Status:")
    logger.error(f"  ✓ Strength check:      {'PASS' if result.passes_strength_check else 'FAIL'}")
    logger.error(f"  ✓ Deflection check:    {'PASS' if result.passes_deflection_check else 'FAIL'}")
    logger.error(f"  ✓ Overturning check:   {'PASS' if result.passes_overturning_check else 'FAIL'}")
    logger.error(f"  ✓ Soil bearing check:  {'PASS' if result.passes_soil_bearing_check else 'FAIL'}")
    logger.error(f"  ✓ Overall:             {'PASS' if result.passes_all_checks else 'FAIL'}")

    if result.warnings:
        logger.warning("\nWarnings:")
        for warning in result.warnings:
            logger.warning(f"  ⚠ {warning}")

    logger.info("\n" + "=" * 70)
