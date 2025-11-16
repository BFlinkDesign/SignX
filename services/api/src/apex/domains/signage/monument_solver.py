"""Monument sign pole engineering calculations.

Implements ASCE 7-22 wind load analysis and foundation design for single-pole monument signs.
Leverages the AISC shapes database for optimal section selection.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class ExposureCategory(Enum):
    """ASCE 7-22 exposure categories for wind analysis."""
    B = "B"  # Urban/suburban with buildings
    C = "C"  # Open terrain with scattered obstructions
    D = "D"  # Flat unobstructed coastal areas


class ImportanceFactor(Enum):
    """ASCE 7-22 importance factors."""
    I = "I"      # Low hazard buildings (1.0)
    II = "II"    # Standard occupancy (1.0)  
    III = "III"  # High occupancy (1.15)
    IV = "IV"    # Essential facilities (1.15)


@dataclass
class MonumentConfig:
    """Monument sign configuration parameters."""
    
    # Project identification
    project_id: str
    config_id: str
    
    # Pole geometry
    pole_height_ft: float
    pole_section: str  # AISC designation (e.g., "HSS8X8X1/2")
    base_plate_size_in: Optional[float] = None
    embedment_depth_ft: Optional[float] = None
    
    # Sign geometry
    sign_width_ft: float
    sign_height_ft: float
    sign_area_sqft: float
    sign_thickness_in: float = 0.125  # 1/8" aluminum typical
    clearance_to_grade_ft: float = 8.0
    
    # Environmental loads
    basic_wind_speed_mph: float
    exposure_category: ExposureCategory = ExposureCategory.C
    importance_factor: ImportanceFactor = ImportanceFactor.II
    gust_factor: float = 0.85
    force_coefficient: float = 1.2  # Cf for flat signs
    
    # Site conditions
    ground_snow_load_psf: float = 0
    ice_thickness_in: float = 0
    seismic_sds: float = 0
    soil_bearing_capacity_psf: float = 2000
    
    # Design criteria
    deflection_limit_ratio: float = 200  # L/200
    stress_ratio_limit: float = 0.9
    foundation_type: str = "spread_footing"


@dataclass
class SectionProperties:
    """AISC section properties for monument pole."""
    
    designation: str
    type: str  # HSS, PIPE, W
    weight_plf: float
    area_in2: float
    ix_in4: float  # Moment of inertia
    sx_in3: float  # Section modulus
    rx_in: float   # Radius of gyration
    fy_ksi: float = 50  # Yield strength
    is_a1085: bool = False


@dataclass
class MonumentResults:
    """Monument sign analysis results."""
    
    # Configuration reference
    config_id: str
    project_id: str
    
    # Wind load analysis
    design_wind_pressure_psf: float
    gust_effect_factor: float
    velocity_pressure_qz_psf: float
    total_wind_force_lbs: float
    wind_moment_at_base_kipft: float
    
    # Additional loads
    dead_load_lbs: float
    snow_load_lbs: float = 0
    ice_load_lbs: float = 0
    seismic_force_lbs: float = 0
    
    # Pole stress analysis
    max_bending_stress_ksi: float
    max_shear_stress_ksi: float
    combined_stress_ratio: float
    max_deflection_in: float
    deflection_ratio: float
    
    # Foundation analysis
    overturning_moment_kipft: float
    resisting_moment_kipft: float
    overturning_safety_factor: float
    max_soil_pressure_psf: float
    foundation_width_ft: Optional[float] = None
    foundation_length_ft: Optional[float] = None
    foundation_thickness_ft: Optional[float] = None
    
    # Design status
    pole_adequate: bool
    foundation_adequate: bool
    overall_passes: bool
    
    # Metadata
    warnings: List[str]
    design_notes: List[str]
    assumptions: List[str]


class MonumentSolver:
    """Monument sign engineering solver using ASCE 7-22 standards."""
    
    def __init__(self):
        self.logger = logger.bind(component="monument_solver")
    
    def analyze_monument_sign(self, config: MonumentConfig, 
                            section_props: SectionProperties) -> MonumentResults:
        """Complete monument sign analysis.
        
        Args:
            config: Monument configuration parameters
            section_props: AISC section properties for the pole
            
        Returns:
            Complete analysis results with pass/fail status
        """
        self.logger.info("monument.analysis.start", 
                        pole_height=config.pole_height_ft,
                        section=section_props.designation,
                        wind_speed=config.basic_wind_speed_mph)
        
        assumptions = []
        warnings = []
        notes = []
        
        # Step 1: Wind load analysis
        wind_results = self._calculate_wind_loads(config, assumptions)
        
        # Step 2: Additional loads
        dead_load = self._calculate_dead_loads(config, section_props, assumptions)
        snow_load = self._calculate_snow_loads(config, assumptions) if config.ground_snow_load_psf > 0 else 0
        ice_load = self._calculate_ice_loads(config, assumptions) if config.ice_thickness_in > 0 else 0
        seismic_load = self._calculate_seismic_loads(config, assumptions) if config.seismic_sds > 0 else 0
        
        # Step 3: Pole stress analysis
        stress_results = self._analyze_pole_stresses(
            config, section_props, wind_results['moment_kipft'], 
            wind_results['force_lbs'], assumptions, warnings
        )
        
        # Step 4: Foundation analysis
        foundation_results = self._analyze_foundation(
            config, wind_results['moment_kipft'], dead_load,
            assumptions, warnings
        )
        
        # Step 5: Combined checks
        pole_adequate = (stress_results['combined_ratio'] <= config.stress_ratio_limit and
                        stress_results['deflection_ratio'] >= config.deflection_limit_ratio)
        
        foundation_adequate = (foundation_results['safety_factor'] >= 1.5 and
                             foundation_results['max_soil_pressure'] <= config.soil_bearing_capacity_psf)
        
        overall_passes = pole_adequate and foundation_adequate
        
        # Generate warnings
        if stress_results['combined_ratio'] > 0.95:
            warnings.append(f"High stress ratio: {stress_results['combined_ratio']:.2f}")
        
        if stress_results['deflection_ratio'] < config.deflection_limit_ratio:
            warnings.append(f"Deflection exceeds L/{config.deflection_limit_ratio}")
        
        if foundation_results['safety_factor'] < 2.0:
            warnings.append(f"Low overturning safety factor: {foundation_results['safety_factor']:.2f}")
        
        # Generate design notes
        if section_props.is_a1085:
            notes.append("Using ASTM A1085 HSS with superior tolerances")
        
        notes.append(f"Analysis per ASCE 7-22, {config.exposure_category.value} exposure")
        notes.append(f"Design wind speed: {config.basic_wind_speed_mph} mph")
        
        self.logger.info("monument.analysis.complete",
                        pole_adequate=pole_adequate,
                        foundation_adequate=foundation_adequate,
                        stress_ratio=stress_results['combined_ratio'])
        
        return MonumentResults(
            config_id=config.config_id,
            project_id=config.project_id,
            
            # Wind loads
            design_wind_pressure_psf=wind_results['pressure_psf'],
            gust_effect_factor=wind_results['gust_factor'],
            velocity_pressure_qz_psf=wind_results['velocity_pressure'],
            total_wind_force_lbs=wind_results['force_lbs'],
            wind_moment_at_base_kipft=wind_results['moment_kipft'],
            
            # Additional loads
            dead_load_lbs=dead_load,
            snow_load_lbs=snow_load,
            ice_load_lbs=ice_load,
            seismic_force_lbs=seismic_load,
            
            # Pole analysis
            max_bending_stress_ksi=stress_results['bending_stress_ksi'],
            max_shear_stress_ksi=stress_results['shear_stress_ksi'],
            combined_stress_ratio=stress_results['combined_ratio'],
            max_deflection_in=stress_results['deflection_in'],
            deflection_ratio=stress_results['deflection_ratio'],
            
            # Foundation
            overturning_moment_kipft=foundation_results['overturning_moment'],
            resisting_moment_kipft=foundation_results['resisting_moment'],
            overturning_safety_factor=foundation_results['safety_factor'],
            max_soil_pressure_psf=foundation_results['max_soil_pressure'],
            foundation_width_ft=foundation_results.get('width_ft'),
            foundation_length_ft=foundation_results.get('length_ft'),
            foundation_thickness_ft=foundation_results.get('thickness_ft'),
            
            # Status
            pole_adequate=pole_adequate,
            foundation_adequate=foundation_adequate,
            overall_passes=overall_passes,
            
            # Metadata
            warnings=warnings,
            design_notes=notes,
            assumptions=assumptions
        )
    
    def _calculate_wind_loads(self, config: MonumentConfig, 
                            assumptions: List[str]) -> Dict[str, float]:
        """Calculate wind loads per ASCE 7-22."""
        
        # Velocity pressure coefficient Kz (ASCE 7-22 Table 26.10-1)
        if config.exposure_category == ExposureCategory.B:
            if config.pole_height_ft <= 30:
                kz = 0.7 + 0.01 * config.pole_height_ft  # Approximation
            else:
                kz = 1.0
        elif config.exposure_category == ExposureCategory.C:
            if config.pole_height_ft <= 15:
                kz = 0.85
            elif config.pole_height_ft <= 20:
                kz = 0.9
            elif config.pole_height_ft <= 30:
                kz = 1.0
            else:
                kz = 1.05
        else:  # Exposure D
            kz = 1.15
        
        assumptions.append(f"Kz = {kz:.2f} for {config.exposure_category.value} exposure at {config.pole_height_ft} ft")
        
        # Importance factor
        importance_factors = {
            ImportanceFactor.I: 1.0,
            ImportanceFactor.II: 1.0,
            ImportanceFactor.III: 1.15,
            ImportanceFactor.IV: 1.15
        }
        iw = importance_factors[config.importance_factor]
        
        # Velocity pressure (ASCE 7-22 Eq. 26.10-1)
        qz = 0.00256 * kz * iw * config.basic_wind_speed_mph**2
        assumptions.append(f"Velocity pressure qz = {qz:.1f} psf")
        
        # Design wind pressure (ASCE 7-22 Eq. 29.4-1 for signs)
        # p = qz * G * Cf
        cf = config.force_coefficient  # Force coefficient for flat signs
        gf = config.gust_factor  # Gust effect factor
        
        p = qz * gf * cf
        assumptions.append(f"Design wind pressure = {p:.1f} psf (G={gf}, Cf={cf})")
        
        # Total wind force
        force = p * config.sign_area_sqft
        
        # Wind moment at base (force at centroid of sign)
        sign_centroid_height = config.clearance_to_grade_ft + config.sign_height_ft / 2
        moment_kipft = force * sign_centroid_height / 1000  # Convert lbs-ft to kip-ft
        
        return {
            'pressure_psf': p,
            'velocity_pressure': qz,
            'gust_factor': gf,
            'force_lbs': force,
            'moment_kipft': moment_kipft
        }
    
    def _calculate_dead_loads(self, config: MonumentConfig, 
                            section_props: SectionProperties,
                            assumptions: List[str]) -> float:
        """Calculate dead loads (pole + sign weight)."""
        
        # Pole weight
        pole_weight = section_props.weight_plf * config.pole_height_ft
        
        # Sign weight (aluminum sign panel)
        aluminum_density_pcf = 169  # lbs/ft³
        sign_volume_ft3 = config.sign_area_sqft * config.sign_thickness_in / 12
        sign_weight = sign_volume_ft3 * aluminum_density_pcf
        
        # Hardware/connections (estimated)
        hardware_weight = 50  # lbs estimate
        
        total_dead_load = pole_weight + sign_weight + hardware_weight
        
        assumptions.append(f"Dead load: pole={pole_weight:.0f} + sign={sign_weight:.0f} + hardware={hardware_weight} = {total_dead_load:.0f} lbs")
        
        return total_dead_load
    
    def _calculate_snow_loads(self, config: MonumentConfig,
                            assumptions: List[str]) -> float:
        """Calculate snow loads on sign (simplified)."""
        
        # Snow accumulation on top edge of sign (conservative)
        snow_load = config.ground_snow_load_psf * config.sign_width_ft * 1.0  # 1 ft depth
        assumptions.append(f"Snow load on sign edge: {snow_load:.0f} lbs")
        
        return snow_load
    
    def _calculate_ice_loads(self, config: MonumentConfig,
                           assumptions: List[str]) -> float:
        """Calculate ice loads (simplified)."""
        
        # Ice weight on sign and pole
        ice_density_pcf = 57  # lbs/ft³
        
        # Ice on sign
        ice_volume_sign = config.sign_area_sqft * config.ice_thickness_in / 12
        ice_load_sign = ice_volume_sign * ice_density_pcf
        
        # Ice on pole (simplified as cylindrical)
        pole_diameter_est = math.sqrt(config.sign_area_sqft / 40)  # Rough estimate
        ice_volume_pole = math.pi * pole_diameter_est * config.ice_thickness_in/12 * config.pole_height_ft
        ice_load_pole = ice_volume_pole * ice_density_pcf
        
        total_ice_load = ice_load_sign + ice_load_pole
        assumptions.append(f"Ice load: sign={ice_load_sign:.0f} + pole={ice_load_pole:.0f} = {total_ice_load:.0f} lbs")
        
        return total_ice_load
    
    def _calculate_seismic_loads(self, config: MonumentConfig,
                               assumptions: List[str]) -> float:
        """Calculate seismic loads (simplified)."""
        
        # Simplified seismic force F = Sds * W (very conservative)
        seismic_force = config.seismic_sds * config.sign_area_sqft * 5  # Rough estimate
        assumptions.append(f"Seismic force: {seismic_force:.0f} lbs (simplified)")
        
        return seismic_force
    
    def _analyze_pole_stresses(self, config: MonumentConfig,
                             section_props: SectionProperties,
                             moment_kipft: float,
                             shear_force_lbs: float,
                             assumptions: List[str],
                             warnings: List[str]) -> Dict[str, float]:
        """Analyze pole stresses and deflection."""
        
        # Material properties
        fy_ksi = section_props.fy_ksi
        e_ksi = 29000  # Steel modulus
        
        # Bending stress
        moment_kipin = moment_kipft * 12
        fb_ksi = moment_kipin / section_props.sx_in3
        
        # Shear stress (simplified)
        fv_ksi = shear_force_lbs / 1000 / section_props.area_in2
        
        # Combined stress ratio (simplified interaction)
        # Using AISC interaction equation approximation
        phi_b = 0.9  # Flexural resistance factor
        allowable_bending = fy_ksi * phi_b
        
        stress_ratio = fb_ksi / allowable_bending
        
        # Deflection calculation (cantilever beam)
        # δ = PL³/(3EI) for point load at tip
        force_kips = shear_force_lbs / 1000
        length_in = config.pole_height_ft * 12
        
        deflection_in = (force_kips * length_in**3) / (3 * e_ksi * section_props.ix_in4)
        deflection_ratio = length_in / deflection_in if deflection_in > 0 else float('inf')
        
        assumptions.append(f"Bending stress: {fb_ksi:.1f} ksi (allowable: {allowable_bending:.1f} ksi)")
        assumptions.append(f"Deflection: {deflection_in:.2f} in (L/{deflection_ratio:.0f})")
        
        return {
            'bending_stress_ksi': fb_ksi,
            'shear_stress_ksi': fv_ksi,
            'combined_ratio': stress_ratio,
            'deflection_in': deflection_in,
            'deflection_ratio': deflection_ratio
        }
    
    def _analyze_foundation(self, config: MonumentConfig,
                          overturning_moment_kipft: float,
                          dead_load_lbs: float,
                          assumptions: List[str],
                          warnings: List[str]) -> Dict[str, float]:
        """Analyze foundation requirements."""
        
        # Estimate foundation dimensions (simplified)
        # Start with minimum based on pole size
        min_width_ft = max(3.0, math.sqrt(config.sign_area_sqft) / 3)
        
        # Resisting moment from dead loads
        # Assume foundation extends 1.5 ft beyond pole center each direction
        foundation_width_ft = min_width_ft
        
        # Foundation weight (estimate)
        foundation_depth_ft = max(3.0, config.pole_height_ft / 8)  # Rule of thumb
        concrete_weight_pcf = 150
        foundation_volume_ft3 = foundation_width_ft**2 * foundation_depth_ft
        foundation_weight_lbs = foundation_volume_ft3 * concrete_weight_pcf
        
        total_dead_load = dead_load_lbs + foundation_weight_lbs
        
        # Resisting moment (dead load at foundation centroid)
        resisting_moment_kipft = total_dead_load * foundation_width_ft / 2 / 1000
        
        # Safety factor against overturning
        safety_factor = resisting_moment_kipft / overturning_moment_kipft if overturning_moment_kipft > 0 else float('inf')
        
        # Soil pressure analysis (simplified)
        # Maximum soil pressure under foundation edge
        net_moment = overturning_moment_kipft - resisting_moment_kipft
        foundation_area_sqft = foundation_width_ft**2
        
        # Pressure = P/A ± M*c/I (simplified as rectangular)
        avg_pressure = total_dead_load / foundation_area_sqft
        moment_pressure = abs(net_moment * 1000 * 6) / (foundation_width_ft**3)  # Simplified
        
        max_soil_pressure = avg_pressure + moment_pressure
        
        assumptions.append(f"Foundation: {foundation_width_ft:.1f}x{foundation_width_ft:.1f}x{foundation_depth_ft:.1f} ft")
        assumptions.append(f"Overturning safety factor: {safety_factor:.2f}")
        assumptions.append(f"Max soil pressure: {max_soil_pressure:.0f} psf")
        
        return {
            'overturning_moment': overturning_moment_kipft,
            'resisting_moment': resisting_moment_kipft,
            'safety_factor': safety_factor,
            'max_soil_pressure': max_soil_pressure,
            'width_ft': foundation_width_ft,
            'length_ft': foundation_width_ft,
            'thickness_ft': foundation_depth_ft
        }


def optimize_monument_pole(config: MonumentConfig,
                         available_sections: List[SectionProperties]) -> Tuple[SectionProperties, MonumentResults]:
    """Find the optimal pole section for given monument requirements.
    
    Args:
        config: Monument configuration
        available_sections: List of available AISC sections
        
    Returns:
        Tuple of (optimal_section, analysis_results)
    """
    solver = MonumentSolver()
    
    best_section = None
    best_results = None
    best_score = float('inf')
    
    for section in available_sections:
        try:
            results = solver.analyze_monument_sign(config, section)
            
            # Skip if doesn't pass
            if not results.overall_passes:
                continue
            
            # Scoring: weight cost + stress penalty
            stress_penalty = max(0, results.combined_stress_ratio - 0.5) * 100
            score = section.weight_plf + stress_penalty
            
            if score < best_score:
                best_score = score
                best_section = section
                best_results = results
                
        except Exception as e:
            logger.warning("monument.optimization.section_failed", 
                         section=section.designation, error=str(e))
            continue
    
    if best_section is None:
        raise ValueError("No suitable sections found for monument requirements")
    
    return best_section, best_results