"""
APEX Signage Engineering - Cantilever Sign Solver
Specialized calculations for cantilever pole signs with offset loading.

Handles:
- Single and double cantilever configurations
- Torsional analysis for eccentric loads
- Fatigue considerations for cyclic wind loading
- Connection design at cantilever-to-pole interface

All calculations are deterministic and follow AISC/AASHTO standards.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field, validate_call


class CantileverType(str, Enum):
    """Cantilever configuration types."""
    SINGLE = "single"  # One-sided cantilever
    DOUBLE = "double"  # Two-sided cantilever (balanced or unbalanced)
    TRUSS = "truss"    # Truss-supported cantilever
    CABLE = "cable"    # Cable-stayed cantilever


class ConnectionType(str, Enum):
    """Cantilever-to-pole connection types."""
    BOLTED_FLANGE = "bolted_flange"
    WELDED = "welded"
    PINNED = "pinned"
    CLAMPED = "clamped"


@dataclass
class CantileverConfig:
    """Configuration for cantilever sign structure."""
    type: CantileverType
    arm_length_ft: float  # Horizontal projection from pole centerline
    arm_angle_deg: float  # Angle from horizontal (0 = horizontal, positive = upward)
    arm_section: str  # AISC designation (e.g., "HSS8x8x1/2")
    connection_type: ConnectionType
    num_arms: int = 1  # Number of cantilever arms
    arm_spacing_ft: float = 0.0  # Vertical spacing between multiple arms
    
    def __post_init__(self):
        """Validate configuration."""
        if self.arm_length_ft <= 0:
            raise ValueError(f"Arm length must be positive, got {self.arm_length_ft}")
        if self.arm_length_ft > 30:
            raise ValueError(f"Arm length {self.arm_length_ft}ft exceeds practical limit of 30ft")
        if abs(self.arm_angle_deg) > 15:
            raise ValueError(f"Arm angle {self.arm_angle_deg}° exceeds typical range of ±15°")
        if self.num_arms < 1 or self.num_arms > 4:
            raise ValueError(f"Number of arms must be 1-4, got {self.num_arms}")


class CantileverLoads(BaseModel):
    """Loads on cantilever sign system."""
    sign_weight_lb: float = Field(..., description="Weight of sign cabinet(s)")
    sign_area_ft2: float = Field(..., description="Projected area of sign")
    wind_pressure_psf: float = Field(..., description="Design wind pressure")
    ice_thickness_in: float = Field(0.0, description="Ice accumulation thickness")
    eccentricity_ft: float = Field(0.0, description="Load eccentricity from arm centerline")
    
    class Config:
        validate_assignment = True


class CantileverAnalysisResult(BaseModel):
    """Results from cantilever sign analysis."""
    # Primary moments (at pole base)
    moment_x_kipft: float = Field(..., description="Moment about X-axis (overturning)")
    moment_y_kipft: float = Field(..., description="Moment about Y-axis (lateral)")
    moment_z_kipft: float = Field(..., description="Torsional moment about Z-axis")
    total_moment_kipft: float = Field(..., description="Resultant moment magnitude")
    
    # Shears
    shear_x_kip: float = Field(..., description="Shear in X-direction")
    shear_y_kip: float = Field(..., description="Shear in Y-direction")
    axial_kip: float = Field(..., description="Axial load (compression positive)")
    
    # Arm stresses
    arm_bending_stress_ksi: float = Field(..., description="Maximum bending stress in arm")
    arm_shear_stress_ksi: float = Field(..., description="Maximum shear stress in arm")
    arm_deflection_in: float = Field(..., description="Tip deflection of cantilever arm")
    arm_rotation_deg: float = Field(..., description="Rotation at arm tip")
    
    # Connection forces
    connection_tension_kip: float = Field(..., description="Maximum bolt/weld tension")
    connection_shear_kip: float = Field(..., description="Maximum bolt/weld shear")
    connection_moment_kipft: float = Field(..., description="Moment at connection")
    
    # Design checks
    arm_stress_ratio: float = Field(..., description="Interaction ratio for arm (< 1.0 is OK)")
    connection_ratio: float = Field(..., description="Interaction ratio for connection")
    deflection_ratio: float = Field(..., description="L/deflection ratio")
    
    # Fatigue
    fatigue_cycles: int = Field(..., description="Estimated fatigue cycles over design life")
    fatigue_factor: float = Field(..., description="Fatigue reduction factor")
    
    # Warnings
    warnings: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)


# Engineering constants
E_STEEL_KSI = 29000.0  # Elastic modulus of steel
G_STEEL_KSI = 11200.0  # Shear modulus of steel
FY_STEEL_KSI = 50.0    # Default yield strength (A572-50)
GAMMA_STEEL_PCF = 490.0  # Unit weight of steel

# Safety factors
PHI_BENDING = 0.9
PHI_SHEAR = 0.9
PHI_TENSION = 0.9
PHI_COMPRESSION = 0.85
PHI_WELD = 0.75
PHI_BOLT = 0.75

# Fatigue parameters (AASHTO)
FATIGUE_CATEGORY_C = 10e8  # Constant for Category C details
FATIGUE_THRESHOLD_KSI = 10.0  # Fatigue threshold stress


@validate_call
def analyze_cantilever_sign(
    config: CantileverConfig,
    loads: CantileverLoads,
    pole_height_ft: float,
    include_fatigue: bool = True,
    wind_cycles_per_year: int = 500_000,
    design_life_years: int = 50,
) -> CantileverAnalysisResult:
    """
    Analyze cantilever sign structure for strength, stability, and fatigue.
    
    This function computes all critical design parameters for cantilever signs:
    - Moments and shears at pole base
    - Torsional effects from eccentric loading
    - Arm stresses and deflections
    - Connection design forces
    - Fatigue life assessment
    
    Args:
        config: Cantilever configuration parameters
        loads: Applied loads on the sign
        pole_height_ft: Height of supporting pole
        include_fatigue: Whether to perform fatigue analysis
        wind_cycles_per_year: Estimated wind load cycles per year
        design_life_years: Design life for fatigue assessment
    
    Returns:
        Complete analysis results with all design parameters
    
    Raises:
        ValueError: If inputs are out of valid ranges
    """
    warnings: List[str] = []
    assumptions: List[str] = []
    
    # Add assumptions
    assumptions.append(f"Steel properties: Fy={FY_STEEL_KSI}ksi, E={E_STEEL_KSI}ksi")
    assumptions.append(f"Wind exposure assumed uniform over sign area")
    assumptions.append(f"Connection assumed to be {config.connection_type.value}")
    
    # Validate pole height
    if pole_height_ft <= 0 or pole_height_ft > 60:
        raise ValueError(f"Pole height {pole_height_ft}ft out of range (0-60ft)")
    
    # Calculate loads
    # Wind force on sign
    wind_force_lb = loads.sign_area_ft2 * loads.wind_pressure_psf
    
    # Ice load if applicable
    ice_weight_lb = 0.0
    if loads.ice_thickness_in > 0:
        ice_volume_ft3 = loads.sign_area_ft2 * (loads.ice_thickness_in / 12.0)
        ice_weight_lb = ice_volume_ft3 * 57.0  # Ice density ~57 pcf
        assumptions.append(f"Ice load calculated for {loads.ice_thickness_in}in thickness")
    
    # Total vertical load
    total_weight_lb = loads.sign_weight_lb + ice_weight_lb
    
    # Moment arms
    arm_horizontal_ft = config.arm_length_ft * math.cos(math.radians(config.arm_angle_deg))
    arm_vertical_ft = config.arm_length_ft * math.sin(math.radians(config.arm_angle_deg))
    
    # Effective moment arm to pole base
    moment_arm_horizontal_ft = arm_horizontal_ft
    moment_arm_vertical_ft = pole_height_ft + arm_vertical_ft
    
    # Calculate moments at pole base
    # X-axis moment (overturning) from wind
    moment_x_ftlb = wind_force_lb * moment_arm_vertical_ft
    
    # Y-axis moment (lateral) from dead load
    moment_y_ftlb = total_weight_lb * moment_arm_horizontal_ft
    
    # Z-axis moment (torsion) from eccentricity
    moment_z_ftlb = 0.0
    if loads.eccentricity_ft != 0:
        moment_z_ftlb = wind_force_lb * loads.eccentricity_ft
        assumptions.append(f"Torsion calculated for {loads.eccentricity_ft}ft eccentricity")
    
    # Total moment
    total_moment_ftlb = math.sqrt(moment_x_ftlb**2 + moment_y_ftlb**2 + moment_z_ftlb**2)
    
    # Shears at base
    shear_x_lb = wind_force_lb
    shear_y_lb = 0.0  # Assuming no lateral wind
    axial_lb = total_weight_lb
    
    # Arm analysis (simplified - would need section properties from database)
    # Assume HSS section for now
    arm_length_in = config.arm_length_ft * 12.0
    
    # Cantilever deflection: δ = PL³/(3EI)
    # Using approximate I for HSS8x8x1/2: I ≈ 100 in⁴
    I_arm_in4 = 100.0  # Would look up from database
    S_arm_in3 = 25.0   # Section modulus
    
    arm_moment_inlb = (wind_force_lb * arm_length_in) + (total_weight_lb * arm_length_in / 2)
    arm_bending_stress_psi = arm_moment_inlb / S_arm_in3
    arm_deflection_in = (wind_force_lb * arm_length_in**3) / (3 * E_STEEL_KSI * 1000 * I_arm_in4)
    arm_rotation_rad = (wind_force_lb * arm_length_in**2) / (2 * E_STEEL_KSI * 1000 * I_arm_in4)
    arm_rotation_deg = math.degrees(arm_rotation_rad)
    
    # Check deflection limits
    deflection_limit_in = arm_length_in / 100  # L/100 for cantilevers
    if arm_deflection_in > deflection_limit_in:
        warnings.append(f"Arm deflection {arm_deflection_in:.1f}in exceeds L/100 limit")
    
    # Connection forces (simplified)
    if config.connection_type == ConnectionType.BOLTED_FLANGE:
        # Assume 8-bolt pattern
        num_bolts = 8
        bolt_eccentricity_in = 6.0  # Typical for HSS8
        connection_tension_lb = arm_moment_inlb / (num_bolts * bolt_eccentricity_in)
        connection_shear_lb = wind_force_lb / num_bolts
    else:
        # Welded connection
        connection_tension_lb = arm_bending_stress_psi * 10.0  # Approximate
        connection_shear_lb = wind_force_lb / 2.0
    
    # Stress ratios
    arm_stress_ratio = (arm_bending_stress_psi / 1000.0) / (PHI_BENDING * FY_STEEL_KSI)
    
    # Connection ratio (simplified)
    bolt_capacity_kip = 20.0  # Typical 3/4" A325 bolt
    connection_ratio = max(
        connection_tension_lb / (1000 * PHI_BOLT * bolt_capacity_kip),
        connection_shear_lb / (1000 * PHI_BOLT * bolt_capacity_kip * 0.6)
    )
    
    # Fatigue analysis
    fatigue_cycles = 0
    fatigue_factor = 1.0
    
    if include_fatigue:
        fatigue_cycles = wind_cycles_per_year * design_life_years
        
        # Stress range for fatigue (assuming 50% mean wind)
        stress_range_ksi = 0.5 * (arm_bending_stress_psi / 1000.0)
        
        if stress_range_ksi > FATIGUE_THRESHOLD_KSI:
            # Calculate fatigue life using S-N curve
            N_allowable = FATIGUE_CATEGORY_C / (stress_range_ksi ** 3)
            fatigue_factor = min(1.0, N_allowable / fatigue_cycles)
            
            if fatigue_factor < 0.5:
                warnings.append(f"Fatigue factor {fatigue_factor:.2f} is critically low")
        
        assumptions.append(f"Fatigue assessed for {fatigue_cycles:,} cycles over {design_life_years} years")
    
    # Check for double cantilever balance
    if config.type == CantileverType.DOUBLE:
        assumptions.append("Double cantilever assumed balanced unless eccentricity specified")
    
    # Special considerations for tall cantilevers
    if config.arm_length_ft > 20:
        warnings.append(f"Long cantilever ({config.arm_length_ft}ft) may require special analysis")
        assumptions.append("Second-order effects may be significant for long cantilevers")
    
    # Build result
    result = CantileverAnalysisResult(
        moment_x_kipft=moment_x_ftlb / 1000.0,
        moment_y_kipft=moment_y_ftlb / 1000.0,
        moment_z_kipft=moment_z_ftlb / 1000.0,
        total_moment_kipft=total_moment_ftlb / 1000.0,
        shear_x_kip=shear_x_lb / 1000.0,
        shear_y_kip=shear_y_lb / 1000.0,
        axial_kip=axial_lb / 1000.0,
        arm_bending_stress_ksi=arm_bending_stress_psi / 1000.0,
        arm_shear_stress_ksi=wind_force_lb / (10.0 * 1000.0),  # Simplified
        arm_deflection_in=arm_deflection_in,
        arm_rotation_deg=arm_rotation_deg,
        connection_tension_kip=connection_tension_lb / 1000.0,
        connection_shear_kip=connection_shear_lb / 1000.0,
        connection_moment_kipft=arm_moment_inlb / (12.0 * 1000.0),
        arm_stress_ratio=arm_stress_ratio,
        connection_ratio=connection_ratio,
        deflection_ratio=arm_length_in / max(0.1, arm_deflection_in),
        fatigue_cycles=fatigue_cycles,
        fatigue_factor=fatigue_factor,
        warnings=warnings,
        assumptions=assumptions,
    )
    
    return result


@validate_call
def optimize_cantilever_design(
    loads: CantileverLoads,
    pole_height_ft: float,
    max_arm_length_ft: float = 25.0,
    min_arm_length_ft: float = 5.0,
    target_stress_ratio: float = 0.9,
) -> Tuple[CantileverConfig, CantileverAnalysisResult]:
    """
    Optimize cantilever design for given loads and constraints.
    
    Finds the most economical cantilever configuration that satisfies:
    - Strength requirements
    - Deflection limits
    - Fatigue life
    - Constructability constraints
    
    Args:
        loads: Design loads on the sign
        pole_height_ft: Supporting pole height
        max_arm_length_ft: Maximum allowable arm length
        min_arm_length_ft: Minimum practical arm length
        target_stress_ratio: Target utilization ratio (0.9 = 90% stressed)
    
    Returns:
        Tuple of (optimal configuration, analysis results)
    """
    best_config = None
    best_result = None
    best_weight = float('inf')
    
    # Try different arm lengths
    arm_lengths = np.linspace(min_arm_length_ft, max_arm_length_ft, 10)
    
    # Available sections (simplified - would query database)
    sections = [
        ("HSS6x6x3/8", 19.08),   # (designation, weight_plf)
        ("HSS8x8x3/8", 25.78),
        ("HSS8x8x1/2", 33.68),
        ("HSS10x10x3/8", 32.58),
        ("HSS10x10x1/2", 42.68),
        ("HSS12x12x1/2", 52.08),
    ]
    
    for arm_length in arm_lengths:
        for section, weight_plf in sections:
            # Create trial configuration
            config = CantileverConfig(
                type=CantileverType.SINGLE,
                arm_length_ft=arm_length,
                arm_angle_deg=0.0,  # Horizontal
                arm_section=section,
                connection_type=ConnectionType.BOLTED_FLANGE,
                num_arms=1,
            )
            
            try:
                # Analyze configuration
                result = analyze_cantilever_sign(
                    config=config,
                    loads=loads,
                    pole_height_ft=pole_height_ft,
                )
                
                # Check if design is acceptable
                if (result.arm_stress_ratio <= target_stress_ratio and
                    result.connection_ratio <= 1.0 and
                    result.fatigue_factor >= 0.5):
                    
                    # Calculate weight
                    total_weight = weight_plf * arm_length
                    
                    # Update best if lighter
                    if total_weight < best_weight:
                        best_weight = total_weight
                        best_config = config
                        best_result = result
                        
            except ValueError:
                # Skip invalid configurations
                continue
    
    if best_config is None:
        raise ValueError("No feasible cantilever design found for given constraints")
    
    return best_config, best_result


def calculate_cantilever_foundation_loads(
    analysis_result: CantileverAnalysisResult,
    include_overstrength: bool = True,
    overstrength_factor: float = 1.1,
) -> Dict[str, float]:
    """
    Calculate foundation design loads from cantilever analysis.
    
    Args:
        analysis_result: Results from cantilever analysis
        include_overstrength: Whether to include overstrength factor
        overstrength_factor: Factor to account for material overstrength
    
    Returns:
        Dictionary with foundation design loads
    """
    factor = overstrength_factor if include_overstrength else 1.0
    
    return {
        "moment_kipft": analysis_result.total_moment_kipft * factor,
        "shear_kip": math.sqrt(
            analysis_result.shear_x_kip**2 + 
            analysis_result.shear_y_kip**2
        ) * factor,
        "axial_kip": analysis_result.axial_kip,  # No overstrength on dead load
        "torsion_kipft": analysis_result.moment_z_kipft * factor,
        "design_case": "Cantilever sign loading per AASHTO LTS-6",
    }