"""
APEX Signage Engineering - Advanced Structural Analysis

Dynamic load analysis, fatigue analysis, and connection design.
"""

from __future__ import annotations

import math
from typing import Dict, List

import numpy as np


# ========== Dynamic Load Analysis (ASCE 7-22 Response Spectrum) ==========


def dynamic_load_analysis(
    static_load_lbf: float,
    natural_period_sec: float,
    damping_ratio: float = 0.05,
    site_class: str = "C",
) -> Dict[str, float]:
    """
    Calculate dynamic amplification factor per ASCE 7-22.
    
    Args:
        static_load_lbf: Static wind load
        natural_period_sec: Natural period of structure
        damping_ratio: Damping ratio (5% typical for steel)
        site_class: Site class (A-F per ASCE 7-22)
    
    Returns:
        Dict with peak_load, static_load, amplification_factor
    
    References:
        ASCE 7-22 Chapter 12: Seismic Design Requirements
        Simplified response spectrum for wind loads
    """
    # Simplified response spectrum
    # For wind loads, amplification is typically 1.0-1.3x
    # More complex for seismic, but simplified here
    
    # Natural frequency
    fn_hz = 1.0 / natural_period_sec if natural_period_sec > 0 else 10.0
    
    # Site factors (simplified - full ASCE 7-22 has complex interpolation)
    site_factors = {
        "A": 1.0,
        "B": 1.0,
        "C": 1.0,
        "D": 1.2,
        "E": 1.5,
        "F": 1.5,
    }
    fa = site_factors.get(site_class, 1.0)
    
    # Amplification factor (simplified - full analysis would use response spectrum)
    # For typical sign structures (fn ~ 2-5 Hz), amplification ~ 1.1-1.2
    if fn_hz < 2.0:
        amplification = 1.3  # Lower frequency -> higher amplification
    elif fn_hz < 5.0:
        amplification = 1.15
    else:
        amplification = 1.05  # Higher frequency -> lower amplification
    
    # Apply damping reduction
    amplification *= (1.0 / (1.0 + 2.0 * damping_ratio))
    
    peak_load = static_load_lbf * amplification * fa
    
    return {
        "peak_load": round(peak_load, 1),
        "static_load": round(static_load_lbf, 1),
        "amplification_factor": round(amplification * fa, 3),
    }


# ========== Fatigue Analysis (AISC 360-16 Appendix 3) ==========


def fatigue_analysis(
    stress_range_ksi: float,
    detail_category: str = "E",
    design_life_years: float = 25.0,
) -> Dict[str, Any]:
    """
    Fatigue analysis per AISC 360-16 Appendix 3.
    
    Args:
        stress_range_ksi: Stress range (max - min stress)
        detail_category: Detail category (A through E' per AISC Table A-3.1)
        design_life_years: Required design life
    
    Returns:
        Dict with design_life_years, passes_25yr_requirement, cycles_to_failure
    
    References:
        AISC 360-16 Appendix 3: Design for Fatigue
        AISC Table A-3.1: Detail Categories
    """
    # Detail category thresholds (ksi) at 2 million cycles
    category_thresholds = {
        "A": 24.0,
        "B": 16.0,
        "B'": 12.0,
        "C": 10.0,
        "C'": 7.0,
        "D": 7.0,
        "E": 4.5,
        "E'": 2.6,
    }
    
    threshold_ksi = category_thresholds.get(detail_category, 4.5)
    
    # Fatigue strength equation: S = (C/N)^(1/3) for N > 5x10^6
    # Simplified: linear relationship for typical ranges
    # Full equation per AISC A-3.2
    
    # Cycles per year (assume daily wind cycles)
    cycles_per_year = 365.0
    
    # Required cycles
    required_cycles = cycles_per_year * design_life_years
    
    # Check if stress range is below threshold
    if stress_range_ksi <= threshold_ksi:
        passes = True
        cycles_to_failure = float("inf")
    else:
        # Estimate cycles to failure (simplified)
        # Full AISC equation: N = (C/S)^3 for constant amplitude
        C = threshold_ksi * (2e6) ** (1.0 / 3.0)  # Threshold constant
        cycles_to_failure = (C / stress_range_ksi) ** 3.0
        passes = cycles_to_failure >= required_cycles
    
    return {
        "design_life_years": design_life_years,
        "passes_25yr_requirement": passes and design_life_years >= 25.0,
        "cycles_to_failure": round(cycles_to_failure, 0) if cycles_to_failure != float("inf") else None,
        "stress_range_ksi": round(stress_range_ksi, 2),
        "detail_category": detail_category,
    }


# ========== Connection Design (AISC 360-16 Chapter J) ==========


def connection_design(
    tension_kip: float,
    shear_kip: float,
    bolt_grade: str = "A325",
    bolt_diameter_in: float = 0.75,
    num_bolts: int = 4,
) -> Dict[str, Any]:
    """
    Bolt group analysis per AISC 360-16 Table J3.2.
    
    Args:
        tension_kip: Tension load
        shear_kip: Shear load
        bolt_grade: Bolt grade (A325, A490)
        bolt_diameter_in: Bolt diameter
        num_bolts: Number of bolts in group
    
    Returns:
        Dict with bolts_required, weld_size_in, connection_capacity
    
    References:
        AISC 360-16 Chapter J: Design of Connections
        AISC Table J3.2: Available Strength of Bolts
    """
    # Bolt capacities per AISC Table J3.2
    fy_bolt = {"A325": 90.0, "A490": 113.0}.get(bolt_grade, 90.0)
    fu_bolt = {"A325": 120.0, "A490": 150.0}.get(bolt_grade, 120.0)
    
    # Bolt area
    ab_in2 = math.pi * (bolt_diameter_in / 2.0) ** 2
    
    # Tension capacity per bolt (AISC J3.6)
    phi_t = 0.75
    rn_tension_kip = phi_t * fu_bolt * ab_in2 / 1000.0
    
    # Shear capacity per bolt (AISC J3.6)
    phi_v = 0.75
    rn_shear_kip = phi_v * 0.6 * fu_bolt * ab_in2 / 1000.0
    
    # Combined tension + shear (AISC J3.7)
    tension_per_bolt = tension_kip / num_bolts
    shear_per_bolt = shear_kip / num_bolts
    
    # Interaction equation: (Tu/Rn_t)^2 + (Vu/Rn_v)^2 <= 1.0
    interaction = (tension_per_bolt / rn_tension_kip) ** 2 + (shear_per_bolt / rn_shear_kip) ** 2
    
    # Required bolts
    bolts_required = math.ceil(num_bolts * interaction)
    
    # Weld sizing (simplified - assumes equal leg fillet weld)
    # AISC Table J2.5: Rn = 0.6 * Fexx * 0.707 * size * length
    fexx = 70.0  # E70XX electrode
    weld_length_in = 4.0 * math.sqrt(ab_in2 * num_bolts)  # Estimate perimeter
    min_weld_size_in = max(0.1875, (shear_kip * 1000.0) / (0.6 * fexx * 0.707 * weld_length_in))
    weld_size_in = math.ceil(min_weld_size_in / 0.0625) * 0.0625  # Round to 1/16"
    
    connection_capacity_kip = min(rn_tension_kip * num_bolts, rn_shear_kip * num_bolts)
    
    return {
        "bolts_required": bolts_required,
        "bolts_provided": num_bolts,
        "weld_size_in": round(weld_size_in, 3),
        "connection_capacity_kip": round(connection_capacity_kip, 2),
        "interaction_ratio": round(interaction, 3),
        "passes": interaction <= 1.0,
    }

