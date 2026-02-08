"""
APEX Signage Engineering - Advanced Edge Case Handling

Multi-cabinet stacking, extreme conditions, soil edge cases, and abstain paths.
"""

from __future__ import annotations

import math
from typing import Any

from .models import Cabinet, SiteLoads

# ========== Multi-Cabinet Stacking Edge Cases ==========


class EdgeCaseDetector:
    """Detects advanced edge cases requiring special handling."""
    
    def detect_eccentric_loading(
        self,
        cabinets: list[Cabinet],
        pole_center_x: float = 0.0,
    ) -> dict[str, Any]:
        """
        Detect eccentric loading (cabinets not aligned on pole centerline).
        
        Args:
            cabinets: Cabinet list
            pole_center_x: Pole centerline X coordinate (ft)
        
        Returns:
            Dict with is_eccentric, eccentricity_ft, torsional_moment_kipft, recommendation
        """
        if not cabinets:
            return {"is_eccentric": False, "eccentricity_ft": 0.0, "torsional_moment_kipft": 0.0, "recommendation": ""}
        
        # Calculate weighted centroid X coordinate
        total_moment_x = 0.0
        total_weight = 0.0
        
        for cab in cabinets:
            cab_weight = cab.width_ft * cab.height_ft * cab.weight_psf
            cab_center_x = cab.width_ft / 2.0  # Simplified: assume cabinet center
            total_moment_x += cab_weight * cab_center_x
            total_weight += cab_weight
        
        centroid_x = total_moment_x / total_weight if total_weight > 0 else 0.0
        eccentricity_ft = abs(centroid_x - pole_center_x)
        
        # Torsional moment (simplified: T = F * e)
        # This is a simplified approximation - full analysis requires 3D analysis
        wind_force_estimate = 1000.0  # Placeholder
        torsional_moment_kipft = (wind_force_estimate * eccentricity_ft) / 1000.0
        
        is_eccentric = eccentricity_ft > 0.5  # Threshold: >6" eccentricity
        
        recommendation = ""
        if is_eccentric:
            recommendation = (
                f"Eccentric loading detected: {eccentricity_ft:.2f}ft offset from pole centerline. "
                "Torsional analysis recommended. Consider adding lateral bracing or redistributing cabinets."
            )
        
        return {
            "is_eccentric": is_eccentric,
            "eccentricity_ft": round(eccentricity_ft, 2),
            "torsional_moment_kipft": round(torsional_moment_kipft, 2),
            "recommendation": recommendation,
        }
    
    def detect_non_symmetric_arrangement(
        self,
        cabinets: list[Cabinet],
    ) -> dict[str, Any]:
        """
        Detect non-symmetric cabinet arrangements (torsional concerns).
        
        Args:
            cabinets: Cabinet list
    
        Returns:
            Dict with is_non_symmetric, asymmetry_ratio, recommendation
        """
        if len(cabinets) < 2:
            return {"is_non_symmetric": False, "asymmetry_ratio": 1.0, "recommendation": ""}
        
        # Calculate left/right distribution
        left_weight = 0.0
        right_weight = 0.0
        
        for cab in cabinets:
            cab_weight = cab.width_ft * cab.height_ft * cab.weight_psf
            # Simplified: assume centered at origin, left is negative X
            # In reality, would need actual X positions
            left_weight += cab_weight / 2.0  # Placeholder
            right_weight += cab_weight / 2.0
        
        total_weight = left_weight + right_weight
        asymmetry_ratio = abs(left_weight - right_weight) / total_weight if total_weight > 0 else 0.0
        
        is_non_symmetric = asymmetry_ratio > 0.2  # >20% asymmetry
        
        recommendation = ""
        if is_non_symmetric:
            recommendation = (
                f"Non-symmetric arrangement detected (asymmetry ratio: {asymmetry_ratio:.2f}). "
                "Torsional moment analysis required. Consider symmetric redesign or add torsional bracing."
            )
        
        return {
            "is_non_symmetric": is_non_symmetric,
            "asymmetry_ratio": round(asymmetry_ratio, 3),
            "recommendation": recommendation,
        }
    
    def analyze_progressive_failure(
        self,
        cabinets: list[Cabinet],
        site: SiteLoads,
    ) -> dict[str, Any]:
        """
        Analyze progressive failure scenario (what if one cabinet fails?).
        
        Args:
            cabinets: Cabinet list
            site: Site loads
    
        Returns:
            Dict with worst_case_cabinet, failure_load_factor, recommendation
        """
        if len(cabinets) < 2:
            return {"worst_case_cabinet": None, "failure_load_factor": 1.0, "recommendation": ""}
        
        # Analyze what happens if each cabinet fails individually
        worst_case = None
        min_load_factor = float("inf")
        
        for i, cab in enumerate(cabinets):
            # Remove this cabinet, recalculate loads
            remaining = [c for j, c in enumerate(cabinets) if j != i]
            if not remaining:
                continue
            
            # Simplified load calculation
            remaining_area = sum(c.width_ft * c.height_ft for c in remaining)
            remaining_weight = sum(c.width_ft * c.height_ft * c.weight_psf for c in remaining)
            
            # Estimate load factor (simplified)
            q_psf = 0.00256 * site.wind_speed_mph**2
            remaining_load = q_psf * remaining_area
            load_factor = remaining_load / remaining_weight if remaining_weight > 0 else 1.0
            
            if load_factor < min_load_factor:
                min_load_factor = load_factor
                worst_case = i
        
        recommendation = ""
        if min_load_factor < 1.5:  # Low load factor indicates vulnerability
            recommendation = (
                f"Progressive failure analysis: Cabinet {worst_case} removal reduces capacity significantly. "
                "Consider redundant connections or over-design for critical cabinets."
            )
        
        return {
            "worst_case_cabinet": worst_case,
            "failure_load_factor": round(min_load_factor, 2),
            "recommendation": recommendation,
        }


# ========== Extreme Environmental Conditions ==========


def check_combined_wind_seismic(
    wind_load_kipft: float,
    seismic_load_kipft: float,
    site_class: str = "C",
) -> dict[str, Any]:
    """
    Check combined wind + seismic per ASCE 7-22 Section 12.4.3.
    
    Args:
        wind_load_kipft: Wind load
        seismic_load_kipft: Seismic load
        site_class: Site class
    
    Returns:
        Dict with combined_load, load_combination, recommendation
    """
    # ASCE 7-22 Load Combination 5: 0.6W + E (wind + seismic)
    combined_load = 0.6 * wind_load_kipft + seismic_load_kipft
    
    # Check if combined exceeds either individual
    max_individual = max(wind_load_kipft, seismic_load_kipft)
    
    recommendation = ""
    if combined_load > max_individual * 1.2:
        recommendation = (
            "Combined wind + seismic load exceeds 120% of maximum individual load. "
            "Detailed seismic analysis per ASCE 7-22 Section 12.4.3 recommended."
        )
    
    return {
        "combined_load_kipft": round(combined_load, 2),
        "load_combination": "0.6W + E (ASCE 7-22)",
        "recommendation": recommendation,
        "exceeds_individual": combined_load > max_individual,
    }


def check_ice_loading(
    cabinet_area_ft2: float,
    ice_thickness_in: float = 0.5,
    site_temperature_f: float = 32.0,
) -> dict[str, Any]:
    """
    Check ice loading on cabinets per ASCE 7-22 Chapter 10.
    
    Args:
        cabinet_area_ft2: Cabinet area
        ice_thickness_in: Ice thickness (inches)
        site_temperature_f: Site temperature (°F)
    
    Returns:
        Dict with ice_load_lbf, added_weight_lb, recommendation
    """
    # ASCE 7-22: Ice load = 0.52 * thickness^1.25 (simplified)
    # Unit conversion: thickness in inches, density = 57 pcf
    ice_density_pcf = 57.0
    ice_thickness_ft = ice_thickness_in / 12.0
    ice_load_psf = ice_density_pcf * ice_thickness_ft
    
    ice_load_lbf = ice_load_psf * cabinet_area_ft2
    added_weight_lb = ice_load_lbf  # Ice adds weight
    
    recommendation = ""
    if ice_load_lbf > 1000.0:  # Significant ice load
        recommendation = (
            f"Ice loading detected: {ice_load_lbf:.0f} lbf additional load. "
            "Consider ice-resistant design or increased pole capacity. "
            "Verify temperature range: icing occurs below 32°F."
        )
    
    return {
        "ice_load_lbf": round(ice_load_lbf, 0),
        "added_weight_lb": round(added_weight_lb, 0),
        "ice_thickness_in": ice_thickness_in,
        "recommendation": recommendation,
    }


def check_temperature_effects(
    temperature_f: float,
    pole_length_ft: float,
    material: str = "steel",
) -> dict[str, Any]:
    """
    Check thermal expansion and cold weather effects.
    
    Args:
        temperature_f: Site temperature (°F)
        pole_length_ft: Pole length
        material: Material type
    
    Returns:
        Dict with thermal_expansion_in, brittleness_risk, recommendation
    """
    # Coefficient of thermal expansion: steel ~6.5e-6 /°F
    alpha_per_f = {"steel": 6.5e-6, "aluminum": 12.8e-6}.get(material, 6.5e-6)
    
    # Reference temperature: 70°F
    delta_temp = temperature_f - 70.0
    thermal_expansion_in = alpha_per_f * delta_temp * pole_length_ft * 12.0
    
    # Cold weather brittleness (simplified)
    brittleness_risk = "low"
    if temperature_f < 0.0:
        brittleness_risk = "high"
        recommendation = "Cold weather (<0°F) increases brittleness risk. Consider impact testing per AISC 360-16."
    elif temperature_f < 32.0:
        brittleness_risk = "medium"
        recommendation = "Freezing temperatures may affect material properties. Review material specifications."
    else:
        recommendation = ""
    
    return {
        "thermal_expansion_in": round(thermal_expansion_in, 3),
        "temperature_f": temperature_f,
        "brittleness_risk": brittleness_risk,
        "recommendation": recommendation,
    }


# ========== Soil Condition Edge Cases ==========


def check_layered_soil(
    soil_layers: list[dict[str, float]],
    footing_depth_ft: float,
) -> dict[str, Any]:
    """
    Check layered soil profiles (different bearing at different depths).
    
    Args:
        soil_layers: List of {depth_top_ft, depth_bottom_ft, bearing_psf}
        footing_depth_ft: Proposed footing depth
    
    Returns:
        Dict with effective_bearing_psf, governing_layer, recommendation
    """
    if not soil_layers:
        return {"effective_bearing_psf": 3000.0, "governing_layer": None, "recommendation": ""}
    
    # Find layer at footing depth
    governing_layer = None
    effective_bearing = 3000.0  # Default
    
    for layer in soil_layers:
        depth_top = layer.get("depth_top_ft", 0.0)
        depth_bottom = layer.get("depth_bottom_ft", 100.0)
        bearing = layer.get("bearing_psf", 3000.0)
        
        if depth_top <= footing_depth_ft <= depth_bottom:
            governing_layer = layer
            effective_bearing = bearing
            break
    
    recommendation = ""
    if governing_layer and effective_bearing < 2000.0:
        recommendation = (
            f"Footing depth {footing_depth_ft:.1f}ft intersects weak soil layer "
            f"(bearing: {effective_bearing}psf). Consider deeper footing or soil improvement. "
            "Geotechnical report recommended."
        )
    
    return {
        "effective_bearing_psf": round(effective_bearing, 0),
        "governing_layer": governing_layer,
        "recommendation": recommendation,
    }


def check_groundwater_effects(
    groundwater_depth_ft: float,
    footing_depth_ft: float,
    soil_bearing_psf: float = 3000.0,
) -> dict[str, Any]:
    """
    Check groundwater effects: saturated soil, buoyancy.
    
    Args:
        groundwater_depth_ft: Groundwater table depth
        footing_depth_ft: Footing depth
        soil_bearing_psf: Dry soil bearing
    
    Returns:
        Dict with effective_bearing_psf, buoyancy_lbf, recommendation
    """
    # Reduced bearing capacity in saturated soil
    if groundwater_depth_ft < footing_depth_ft:
        # Saturated soil typically has 50-70% of dry bearing
        reduction_factor = 0.6
        effective_bearing = soil_bearing_psf * reduction_factor
        
        # Buoyancy (simplified)
        submerged_depth = footing_depth_ft - groundwater_depth_ft
        footing_diameter_ft = 3.0  # Assume typical
        volume_cf = math.pi * (footing_diameter_ft / 2.0) ** 2 * submerged_depth
        buoyancy_lbf = 62.4 * volume_cf  # Water density
        
        recommendation = (
            f"Groundwater at {groundwater_depth_ft:.1f}ft affects footing. "
            f"Effective bearing reduced to {effective_bearing:.0f}psf. "
            f"Buoyancy force: {buoyancy_lbf:.0f} lbf. "
            "Consider dewatering or deeper foundation."
        )
    else:
        effective_bearing = soil_bearing_psf
        buoyancy_lbf = 0.0
        recommendation = ""
    
    return {
        "effective_bearing_psf": round(effective_bearing, 0),
        "buoyancy_lbf": round(buoyancy_lbf, 0),
        "groundwater_depth_ft": groundwater_depth_ft,
        "recommendation": recommendation,
    }


def check_frost_heave(
    frost_depth_ft: float,
    footing_depth_ft: float,
    location: str = "northern",
) -> dict[str, Any]:
    """
    Check frost heave concerns (seasonal movement).
    
    Args:
        frost_depth_ft: Typical frost depth
        footing_depth_ft: Proposed footing depth
        location: Geographic location
    
    Returns:
        Dict with frost_risk, recommended_depth_ft, recommendation
    """
    frost_risk = "none"
    recommended_depth = footing_depth_ft
    
    if footing_depth_ft < frost_depth_ft:
        frost_risk = "high"
        recommended_depth = frost_depth_ft + 0.5  # Below frost + margin
        recommendation = (
            f"Footing depth {footing_depth_ft:.1f}ft is above frost depth {frost_depth_ft:.1f}ft. "
            f"Recommended depth: {recommended_depth:.1f}ft minimum. "
            "Frost heave can cause seasonal movement and structural damage."
        )
    elif footing_depth_ft < frost_depth_ft + 0.5:
        frost_risk = "medium"
        recommendation = (
            f"Footing depth {footing_depth_ft:.1f}ft is near frost depth {frost_depth_ft:.1f}ft. "
            "Consider deeper foundation for stability."
        )
    else:
        recommendation = ""
    
    return {
        "frost_risk": frost_risk,
        "recommended_depth_ft": round(recommended_depth, 1),
        "frost_depth_ft": frost_depth_ft,
        "recommendation": recommendation,
    }


# ========== Abstain with Recommendation ==========


def abstain_with_recommendation(
    edge_case_type: str,
    reason: str,
    recommendation: str,
    confidence: float = 0.0,
) -> dict[str, Any]:
    """
    Return abstain response with specific recommendation.
    
    Args:
        edge_case_type: Type of edge case ("eccentric", "extreme_wind", "soil", etc.)
        reason: Explanation of why abstaining
        recommendation: Specific recommendation (e.g., "Requires geotechnical report")
        confidence: Confidence level (0.0 for abstain)
    
    Returns:
        Dict with result=None, confidence=0.0, assumptions, recommendation
    """
    return {
        "result": None,
        "confidence": confidence,
        "assumptions": [
            f"Edge case detected: {edge_case_type}",
            reason,
        ],
        "recommendation": recommendation,
        "edge_case_type": edge_case_type,
        "requires_review": True,
    }

