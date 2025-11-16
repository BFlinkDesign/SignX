"""
Double Pole Sign Structural Analysis - IBC 2024 / ASCE 7-22 / AISC 360-22 Compliant

This module analyzes double-pole sign structures (typically large monument signs,
pylon signs, or multi-column supports) using current building code standards.

Key Differences from Single-Pole:
- Load distribution between two poles (equal or proportional)
- Lateral stability requirements between poles
- Differential settlement considerations
- Coordinated foundation design

Code Compliance:
- IBC 2024: International Building Code (Section 1605 Load Combinations, Section 1807 Foundations)
- ASCE 7-22: Wind loads per Chapters 26-29 (Directional Procedure)
- AISC 360-22: Steel Construction Manual (Allowable Stress Design)

Determinism: All calculations are pure functions - same inputs always produce same outputs.
"""

from typing import NamedTuple, Optional, Literal
from dataclasses import dataclass
import math

from apex.domains.signage.asce7_wind import (
    calculate_wind_force_on_sign,
    calculate_wind_moment_at_base,
    ExposureCategory,
    RiskCategory,
)
from apex.domains.signage.single_pole_solver import (
    PoleSection,
    E_STEEL_KSI,
    ASD_ALLOWABLE_BENDING_FACTOR,
    ASD_ALLOWABLE_SHEAR_FACTOR,
    IBC_OVERTURNING_SAFETY_FACTOR_MIN,
    DEFLECTION_LIMIT_L_OVER,
)


LoadDistributionMethod = Literal["equal", "proportional"]


@dataclass
class DoublePoleConfig:
    """Configuration for double-pole sign analysis."""
    # Pole geometry (two identical poles)
    pole_height_ft: float
    pole_section: PoleSection
    pole_spacing_ft: float  # Center-to-center spacing between poles
    embedment_depth_ft: float

    # Sign geometry
    sign_width_ft: float
    sign_height_ft: float
    sign_area_sqft: float
    sign_weight_psf: float = 3.0

    # Load distribution
    load_distribution_method: LoadDistributionMethod = "equal"
    lateral_bracing_required: bool = False
    differential_settlement_limit_in: float = 0.5  # Max differential settlement

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


class DoublePoleResults(NamedTuple):
    """Complete results from double-pole structural analysis."""
    # Wind load analysis (total)
    velocity_pressure_qz_psf: float
    exposure_coefficient_kz: float
    wind_importance_factor_iw: float
    design_wind_pressure_psf: float
    total_wind_force_lbs: float
    wind_moment_total_kipft: float

    # Load distribution
    load_per_pole_lbs: float
    moment_per_pole_kipft: float
    lateral_stability_check: bool

    # Dead loads
    dead_load_sign_lbs: float
    dead_load_per_pole_lbs: float
    total_dead_load_lbs: float

    # Structural analysis (per pole)
    max_bending_moment_per_pole_kipft: float
    max_shear_force_per_pole_kips: float
    bending_stress_fb_ksi: float
    shear_stress_fv_ksi: float
    allowable_bending_Fb_ksi: float
    allowable_shear_Fv_ksi: float
    bending_stress_ratio: float
    shear_stress_ratio: float
    combined_stress_ratio: float

    # Deflection analysis
    max_deflection_in: float
    deflection_ratio_l_over: float
    deflection_limit_l_over: float

    # Foundation analysis (per pole)
    overturning_moment_per_pole_kipft: float
    resisting_moment_per_pole_kipft: float
    safety_factor_overturning: float
    max_soil_pressure_psf: float
    foundation_diameter_ft: float
    foundation_depth_ft: float
    concrete_volume_total_cuyd: float

    # Pass/fail checks
    passes_strength_check: bool
    passes_deflection_check: bool
    passes_overturning_check: bool
    passes_soil_bearing_check: bool
    passes_lateral_stability_check: bool
    passes_all_checks: bool

    # Critical failure mode
    critical_failure_mode: Optional[str]

    # Warnings and code references
    warnings: list[str]
    code_references: list[str]


def analyze_double_pole_sign(config: DoublePoleConfig) -> DoublePoleResults:
    """
    Complete structural analysis of double-pole sign per IBC 2024 / ASCE 7-22 / AISC 360-22.

    Key Assumptions:
    - Two identical poles support the sign
    - Equal load distribution: each pole carries 50% of total load
    - Proportional load distribution: load distributed based on tributary area
    - Lateral stability provided by sign structure and/or bracing

    This is a deterministic, pure function - same inputs always produce same outputs.

    Args:
        config: Double pole configuration with geometry, loads, and design criteria

    Returns:
        DoublePoleResults with complete structural analysis

    Raises:
        ValueError: If configuration is invalid (negative values, spacing too small, etc.)
    """
    warnings = []
    code_refs = []

    # Validate configuration
    if config.pole_spacing_ft < 3.0:
        raise ValueError(f"Pole spacing {config.pole_spacing_ft} ft is too small (minimum 3 ft)")

    # =========================================================================
    # STEP 1: Wind Load Analysis (ASCE 7-22) - Same as Single Pole
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

    wind_moment_total = calculate_wind_moment_at_base(
        total_wind_force_lbs=wind_result.total_wind_force_lbs,
        pole_height_ft=config.pole_height_ft,
        sign_height_ft=config.sign_height_ft,
    )

    code_refs.extend(wind_result.code_references)

    # =========================================================================
    # STEP 2: Load Distribution Between Poles
    # =========================================================================

    if config.load_distribution_method == "equal":
        # Equal distribution: each pole carries 50% of total load
        load_per_pole = wind_result.total_wind_force_lbs / 2.0
        moment_per_pole = wind_moment_total / 2.0

        code_refs.append("Load Distribution: Equal (50% per pole)")

    elif config.load_distribution_method == "proportional":
        # Proportional distribution based on tributary area
        # For symmetric signs, this is typically equal, but included for future non-symmetric cases
        # Assume equal for now
        load_per_pole = wind_result.total_wind_force_lbs / 2.0
        moment_per_pole = wind_moment_total / 2.0

        warnings.append(
            "Proportional load distribution assumes symmetric sign geometry. "
            "For non-symmetric signs, manual adjustment may be required."
        )
        code_refs.append("Load Distribution: Proportional (symmetric assumed)")

    else:
        raise ValueError(f"Invalid load distribution method: {config.load_distribution_method}")

    # =========================================================================
    # STEP 3: Lateral Stability Check
    # =========================================================================

    # Check if lateral bracing is required
    # Rule of thumb: If spacing > 1.5 × pole height, bracing recommended
    spacing_to_height_ratio = config.pole_spacing_ft / config.pole_height_ft

    lateral_stability_ok = True
    if spacing_to_height_ratio > 1.5 and not config.lateral_bracing_required:
        warnings.append(
            f"Pole spacing ({config.pole_spacing_ft} ft) exceeds 1.5× pole height "
            f"({config.pole_height_ft} ft). Lateral bracing recommended."
        )
        lateral_stability_ok = False
    elif spacing_to_height_ratio > 2.0:
        warnings.append(
            f"Pole spacing ({config.pole_spacing_ft} ft) exceeds 2× pole height. "
            f"Lateral bracing REQUIRED for stability."
        )
        lateral_stability_ok = False

    # If bracing is provided, stability is adequate
    if config.lateral_bracing_required:
        lateral_stability_ok = True
        code_refs.append("Lateral bracing provided between poles")

    # =========================================================================
    # STEP 4: Dead Load Calculations
    # =========================================================================

    # Total sign weight
    dead_load_sign = config.sign_area_sqft * config.sign_weight_psf

    # Pole weight (per pole)
    dead_load_per_pole = config.pole_section.weight_plf * config.pole_height_ft

    # Total dead load (both poles + sign)
    total_dead_load = dead_load_sign + (2 * dead_load_per_pole)

    # Dead load per pole (for foundation analysis)
    # Sign weight distributed equally between poles
    dead_load_on_pole = (dead_load_sign / 2.0) + dead_load_per_pole

    # =========================================================================
    # STEP 5: Structural Analysis (AISC 360-22 ASD) - Per Pole
    # =========================================================================

    # Maximum bending moment at base (per pole)
    max_bending_moment_per_pole = moment_per_pole

    # Maximum shear force at base (per pole)
    max_shear_per_pole = load_per_pole / 1000.0  # Convert to kips

    # Bending stress: fb = M / Sx
    bending_stress_fb = (max_bending_moment_per_pole * 12.0) / config.pole_section.sx_in3

    # Shear stress: fv = V / A
    shear_stress_fv = max_shear_per_pole / config.pole_section.area_in2

    # Allowable stresses (AISC 360-22 ASD)
    allowable_bending_Fb = ASD_ALLOWABLE_BENDING_FACTOR * config.pole_section.fy_ksi
    allowable_shear_Fv = ASD_ALLOWABLE_SHEAR_FACTOR * config.pole_section.fy_ksi

    # Stress ratios
    bending_ratio = bending_stress_fb / allowable_bending_Fb
    shear_ratio = shear_stress_fv / allowable_shear_Fv
    combined_ratio = bending_ratio + shear_ratio

    code_refs.append("AISC 360-22 Chapter F: Flexural Design (ASD)")
    code_refs.append("AISC 360-22 Chapter G: Shear Design (ASD)")

    # =========================================================================
    # STEP 6: Deflection Analysis
    # =========================================================================

    # Cantilever deflection per pole: δ = (F * L³) / (3 * E * I)
    pole_height_in = config.pole_height_ft * 12.0
    sign_centroid_in = pole_height_in + (config.sign_height_ft * 12.0 / 2.0)

    # Force per pole applied at sign centroid
    deflection_in = (
        load_per_pole * math.pow(sign_centroid_in, 3)
    ) / (3.0 * E_STEEL_KSI * 1000.0 * config.pole_section.ix_in4)

    # Deflection ratio: L/δ
    if deflection_in > 0:
        deflection_ratio = pole_height_in / deflection_in
    else:
        deflection_ratio = float('inf')

    code_refs.append("AISC 360-22 Chapter L: Serviceability (Deflection)")

    # =========================================================================
    # STEP 7: Foundation Analysis (IBC 2024) - Per Pole
    # =========================================================================

    # Overturning moment per pole
    overturning_moment_per_pole = moment_per_pole

    # Foundation sizing
    foundation_depth = config.embedment_depth_ft

    foundation_diameter = _calculate_foundation_diameter_double_pole(
        overturning_moment_kipft=overturning_moment_per_pole,
        dead_load_lbs=dead_load_on_pole,
        embedment_depth_ft=foundation_depth,
        soil_bearing_capacity_psf=config.soil_bearing_capacity_psf,
        target_safety_factor=config.overturning_safety_factor_min,
    )

    # Resisting moment per pole
    resisting_moment_weight = (dead_load_on_pole / 1000.0) * (foundation_diameter / 2.0)

    # Passive pressure resistance
    soil_density_pcf = 120
    passive_coeff = 3.0
    passive_force = (
        0.5 * soil_density_pcf * math.pow(foundation_depth, 2) *
        passive_coeff * foundation_diameter
    ) / 1000.0
    passive_moment = passive_force * (foundation_depth / 3.0)

    total_resisting_moment_per_pole = resisting_moment_weight + passive_moment

    # Safety factor against overturning
    if overturning_moment_per_pole > 0:
        safety_factor_overturning = total_resisting_moment_per_pole / overturning_moment_per_pole
    else:
        safety_factor_overturning = float('inf')

    # Soil bearing pressure
    foundation_area_sqft = math.pi * math.pow(foundation_diameter / 2.0, 2)
    max_soil_pressure = (dead_load_on_pole / foundation_area_sqft) + (
        overturning_moment_per_pole * 1000.0 * 12.0 * (foundation_diameter / 2.0) /
        (math.pi * math.pow(foundation_diameter / 2.0, 4) / 4.0)
    )

    # Total concrete volume (both foundations)
    concrete_volume_per_foundation = (foundation_area_sqft * foundation_depth) / 27.0
    concrete_volume_total = concrete_volume_per_foundation * 2

    code_refs.append("IBC 2024 Section 1605.2.1: Overturning Stability")
    code_refs.append("IBC 2024 Section 1807: Foundations")

    # =========================================================================
    # STEP 8: Pass/Fail Checks
    # =========================================================================

    passes_strength = (bending_ratio <= 1.0) and (shear_ratio <= 1.0)
    passes_deflection = deflection_ratio >= config.deflection_limit_ratio
    passes_overturning = safety_factor_overturning >= config.overturning_safety_factor_min
    passes_soil_bearing = max_soil_pressure <= config.soil_bearing_capacity_psf
    passes_lateral_stability = lateral_stability_ok

    passes_all = (
        passes_strength and
        passes_deflection and
        passes_overturning and
        passes_soil_bearing and
        passes_lateral_stability
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
        if not passes_lateral_stability:
            failure_modes.append(("LATERAL_STABILITY", 1.0))

        failure_modes.sort(key=lambda x: x[1], reverse=True)
        critical_failure = failure_modes[0][0] if failure_modes else None

    # =========================================================================
    # STEP 9: Additional Warnings
    # =========================================================================

    if bending_ratio > 0.9:
        warnings.append(f"Bending stress ratio {bending_ratio:.2f} exceeds 0.90 - near capacity")

    if safety_factor_overturning < 2.0:
        warnings.append(
            f"Overturning SF {safety_factor_overturning:.2f} below 2.0 (exceeds IBC min 1.5 but low margin)"
        )

    # Differential settlement warning
    if config.pole_spacing_ft > 15:
        warnings.append(
            f"Large pole spacing ({config.pole_spacing_ft} ft) may result in differential settlement. "
            f"Foundation coordination critical."
        )

    # =========================================================================
    # STEP 10: Return Results
    # =========================================================================

    return DoublePoleResults(
        # Wind loads (total)
        velocity_pressure_qz_psf=wind_result.velocity_pressure_qz_psf,
        exposure_coefficient_kz=wind_result.exposure_coefficient_kz,
        wind_importance_factor_iw=wind_result.wind_importance_factor_iw,
        design_wind_pressure_psf=wind_result.design_wind_pressure_psf,
        total_wind_force_lbs=wind_result.total_wind_force_lbs,
        wind_moment_total_kipft=wind_moment_total,

        # Load distribution
        load_per_pole_lbs=load_per_pole,
        moment_per_pole_kipft=moment_per_pole,
        lateral_stability_check=lateral_stability_ok,

        # Dead loads
        dead_load_sign_lbs=dead_load_sign,
        dead_load_per_pole_lbs=dead_load_per_pole,
        total_dead_load_lbs=total_dead_load,

        # Structural analysis (per pole)
        max_bending_moment_per_pole_kipft=max_bending_moment_per_pole,
        max_shear_force_per_pole_kips=max_shear_per_pole,
        bending_stress_fb_ksi=bending_stress_fb,
        shear_stress_fv_ksi=shear_stress_fv,
        allowable_bending_Fb_ksi=allowable_bending_Fb,
        allowable_shear_Fv_ksi=allowable_shear_Fv,
        bending_stress_ratio=bending_ratio,
        shear_stress_ratio=shear_ratio,
        combined_stress_ratio=combined_ratio,

        # Deflection
        max_deflection_in=deflection_in,
        deflection_ratio_l_over=deflection_ratio,
        deflection_limit_l_over=config.deflection_limit_ratio,

        # Foundation (per pole)
        overturning_moment_per_pole_kipft=overturning_moment_per_pole,
        resisting_moment_per_pole_kipft=total_resisting_moment_per_pole,
        safety_factor_overturning=safety_factor_overturning,
        max_soil_pressure_psf=max_soil_pressure,
        foundation_diameter_ft=foundation_diameter,
        foundation_depth_ft=foundation_depth,
        concrete_volume_total_cuyd=concrete_volume_total,

        # Pass/fail
        passes_strength_check=passes_strength,
        passes_deflection_check=passes_deflection,
        passes_overturning_check=passes_overturning,
        passes_soil_bearing_check=passes_soil_bearing,
        passes_lateral_stability_check=passes_lateral_stability,
        passes_all_checks=passes_all,

        # Failure mode
        critical_failure_mode=critical_failure,

        # Metadata
        warnings=warnings,
        code_references=code_refs,
    )


def _calculate_foundation_diameter_double_pole(
    overturning_moment_kipft: float,
    dead_load_lbs: float,
    embedment_depth_ft: float,
    soil_bearing_capacity_psf: float,
    target_safety_factor: float = 1.5,
) -> float:
    """
    Calculate required foundation diameter for double-pole configuration.

    Similar to single-pole, but accounts for load distribution between poles.

    Args:
        overturning_moment_kipft: Overturning moment per pole (kip-ft)
        dead_load_lbs: Dead load per pole (lbs)
        embedment_depth_ft: Foundation embedment depth (ft)
        soil_bearing_capacity_psf: Allowable soil bearing pressure (psf)
        target_safety_factor: Target safety factor (default 1.5 per IBC)

    Returns:
        Required foundation diameter in feet
    """
    min_diameter = 3.0
    max_diameter = 8.0  # Smaller than single-pole since load is distributed

    for diameter in [d / 10.0 for d in range(int(min_diameter * 10), int(max_diameter * 10) + 1)]:
        resisting_moment_weight = (dead_load_lbs / 1000.0) * (diameter / 2.0)

        soil_density_pcf = 120
        passive_coeff = 3.0
        passive_force = (
            0.5 * soil_density_pcf * math.pow(embedment_depth_ft, 2) *
            passive_coeff * diameter
        ) / 1000.0
        passive_moment = passive_force * (embedment_depth_ft / 3.0)

        total_resisting = resisting_moment_weight + passive_moment

        if overturning_moment_kipft > 0:
            safety_factor = total_resisting / overturning_moment_kipft
            if safety_factor >= target_safety_factor:
                return diameter

    return max_diameter


# Example usage
if __name__ == "__main__":
    logger.info("Double Pole Sign Structural Analysis Example\n")
    logger.info("=" * 70)

    # Example: 20 ft double-pole monument with HSS6×6×1/4
    from apex.domains.signage.single_pole_solver import PoleSection
import logging

logger = logging.getLogger(__name__)

    pole = PoleSection(
        designation="HSS6X6X1/4",
        type="HSS",
        area_in2=5.36,
        depth_in=6.0,
        weight_plf=18.2,
        sx_in3=11.2,
        ix_in4=33.5,
        rx_in=2.50,
        fy_ksi=50.0,
        fu_ksi=65.0,
    )

    config = DoublePoleConfig(
        pole_height_ft=17.0,
        pole_section=pole,
        pole_spacing_ft=12.0,  # 12 ft between poles
        embedment_depth_ft=5.0,
        sign_width_ft=16.0,
        sign_height_ft=6.0,
        sign_area_sqft=96.0,
        basic_wind_speed_mph=115,
        risk_category=RiskCategory.II,
        exposure_category=ExposureCategory.C,
        load_distribution_method="equal",
    )

    result = analyze_double_pole_sign(config)

    logger.info("Configuration:")
    logger.info(f"  Poles: Two {pole.designation}, {config.pole_height_ft} ft tall")
    logger.info(f"  Spacing: {config.pole_spacing_ft} ft center-to-center")
    logger.info(f"  Sign: {config.sign_width_ft}×{config.sign_height_ft} ft ({config.sign_area_sqft} sqft)")
    logger.info(f"  Wind: {config.basic_wind_speed_mph} mph, Exposure {config.exposure_category.value}")
    logger.info()

    logger.info("Wind Loads (ASCE 7-22):")
    logger.info(f"  Total wind force:      {result.total_wind_force_lbs:.0f} lbs")
    logger.info(f"  Load per pole:         {result.load_per_pole_lbs:.0f} lbs (50%)")
    logger.info(f"  Moment per pole:       {result.moment_per_pole_kipft:.2f} kip-ft")
    logger.info()

    logger.info("Structural Analysis (AISC 360-22 ASD) - Per Pole:")
    logger.info(f"  Bending stress ratio:  {result.bending_stress_ratio:.3f}")
    logger.info(f"  Shear stress ratio:    {result.shear_stress_ratio:.3f}")
    logger.info(f"  Deflection:            {result.max_deflection_in:.2f} in (L/{result.deflection_ratio_l_over:.0f})")
    logger.info()

    logger.info("Foundation (IBC 2024) - Per Pole:")
    logger.info(f"  Diameter required:     {result.foundation_diameter_ft:.1f} ft")
    logger.info(f"  Embedment depth:       {result.foundation_depth_ft:.1f} ft")
    logger.info(f"  Overturning SF:        {result.safety_factor_overturning:.2f}")
    logger.info(f"  Total concrete:        {result.concrete_volume_total_cuyd:.2f} cu yd (both)")
    logger.info()

    logger.info("Design Status:")
    logger.error(f"  ✓ Strength check:         {'PASS' if result.passes_strength_check else 'FAIL'}")
    logger.error(f"  ✓ Deflection check:       {'PASS' if result.passes_deflection_check else 'FAIL'}")
    logger.error(f"  ✓ Overturning check:      {'PASS' if result.passes_overturning_check else 'FAIL'}")
    logger.error(f"  ✓ Soil bearing check:     {'PASS' if result.passes_soil_bearing_check else 'FAIL'}")
    logger.error(f"  ✓ Lateral stability:      {'PASS' if result.passes_lateral_stability_check else 'FAIL'}")
    logger.error(f"  ✓ Overall:                {'PASS' if result.passes_all_checks else 'FAIL'}")

    if result.warnings:
        logger.warning("\nWarnings:")
        for warning in result.warnings:
            logger.warning(f"  ⚠ {warning}")

    logger.info("\n" + "=" * 70)
    logger.info("Advantage: Reduced moment per pole = smaller sections possible")
    logger.info("=" * 70)
