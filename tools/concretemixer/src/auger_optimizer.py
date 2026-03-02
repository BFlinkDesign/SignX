#!/usr/bin/env python3
"""
MudMixer Auger Generative Design Framework

This module provides computational tools for optimizing the design of a
shaftless helical auger for continuous concrete mixing.

Usage:
    python auger_optimizer.py --housing-id 6.0 --torque 95 --aggregate 0.5

Dependencies:
    - numpy
    - scipy (optional, for advanced optimization)
    - matplotlib (optional, for visualization)
"""

import math
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
from enum import Enum


class FingerMaterial(Enum):
    """Available finger materials with mechanical properties."""
    STEEL_1045 = ("1045 Steel", 12000, 250)           # (name, shear_psi, max_temp_F)
    STAINLESS_304 = ("304 SS", 10000, 1500)
    UHMW_STANDARD = ("UHMW-PE", 2000, 180)
    UHMW_HIGH_TEMP = ("High-Temp UHMW", 1800, 275)
    PTFE = ("PTFE/Teflon", 600, 500)

    def __init__(self, display_name: str, shear_strength_psi: int, max_temp_f: int):
        self.display_name = display_name
        self.shear_strength_psi = shear_strength_psi
        self.max_temp_f = max_temp_f


class DutyCycle(Enum):
    """Operating duty cycle classifications."""
    # (name, bags_per_session, sessions_per_day, runtime_hours, cool_down_mins)
    LIGHT = ("light", 5, 10, 0.5, 30)
    MEDIUM = ("medium", 20, 5, 2.0, 15)
    HEAVY = ("heavy", 50, 3, 4.0, 10)
    CONTINUOUS = ("continuous", 100, 1, 8.0, 5)
    JOBSITE_12HR = ("jobsite_12hr", 500, 1, 12.0, 0)  # NEW: 12+ hour continuous

    def __init__(self, name: str, bags_per_session: int, sessions_per_day: int,
                 runtime_hours: float, cool_down_mins: float):
        self._name = name
        self.bags_per_session = bags_per_session
        self.sessions_per_day = sessions_per_day
        self.runtime_hours = runtime_hours
        self.cool_down_mins = cool_down_mins

    @property
    def is_continuous(self) -> bool:
        """Returns True if duty cycle requires continuous thermal management."""
        return self.runtime_hours >= 4.0

    @property
    def thermal_severity(self) -> str:
        """Classification for material selection."""
        if self.runtime_hours <= 1:
            return "LOW"
        elif self.runtime_hours <= 4:
            return "MEDIUM"
        elif self.runtime_hours <= 8:
            return "HIGH"
        else:
            return "EXTREME"  # 12+ hours


@dataclass
class AugerGeometry:
    """Defines the geometric parameters of the shaftless auger."""
    outer_diameter: float           # inches
    inner_diameter: float           # inches (open center)
    length_hopper: float            # inches (section 1)
    length_chute: float             # inches (section 2)
    pitch_hopper: float             # inches (section 1 pitch)
    pitch_chute: float              # inches (section 2 pitch)
    flight_thickness: float = 0.1875  # inches (3/16")

    @property
    def total_length(self) -> float:
        return self.length_hopper + self.length_chute

    @property
    def pd_ratio_hopper(self) -> float:
        return self.pitch_hopper / self.outer_diameter

    @property
    def pd_ratio_chute(self) -> float:
        return self.pitch_chute / self.outer_diameter

    def validate(self) -> List[str]:
        """Validate geometry against patent specifications."""
        issues = []

        # Patent 10,259,140: P/D ratio 0.2-0.9 for hopper
        if not (0.2 <= self.pd_ratio_hopper <= 0.9):
            issues.append(f"Hopper P/D ratio {self.pd_ratio_hopper:.2f} outside range 0.2-0.9")

        # Patent 11,285,639: P/D ratio 0.6-1.0 for chute
        if not (0.6 <= self.pd_ratio_chute <= 1.0):
            issues.append(f"Chute P/D ratio {self.pd_ratio_chute:.2f} outside range 0.6-1.0")

        # Chute pitch must be greater than hopper pitch
        if self.pitch_chute <= self.pitch_hopper:
            issues.append("Chute pitch must be greater than hopper pitch (variable pitch design)")

        return issues


@dataclass
class FingerConfig:
    """Defines the finger (mixing element) configuration."""
    material: FingerMaterial
    diameter: float                 # inches
    length: float                   # inches (how far into interior)
    count: int                      # total number of fingers
    angle: float = 90.0             # degrees from flight surface

    @property
    def cross_section_area(self) -> float:
        """Cross-sectional area in square inches."""
        return math.pi * (self.diameter / 2) ** 2


@dataclass
class OperatingConditions:
    """Defines the operating environment and constraints."""
    motor_power_hp: float = 0.5
    motor_rpm: float = 27.0
    max_aggregate_size: float = 0.5     # inches (CONFIRMED for MudMixer)
    duty_cycle: DutyCycle = DutyCycle.MEDIUM
    ambient_temp_f: float = 70.0
    water_pressure_psi: float = 40.0

    @property
    def motor_torque_ft_lb(self) -> float:
        """Calculate motor output torque from power and RPM."""
        # HP = Torque(ft-lb) × RPM / 5252
        return (self.motor_power_hp * 5252) / self.motor_rpm

    @property
    def motor_torque_nm(self) -> float:
        """Motor torque in Newton-meters."""
        return self.motor_torque_ft_lb * 1.3558


class AugerOptimizer:
    """
    Generative design optimizer for shaftless helical auger.

    This class performs engineering calculations to validate and optimize
    auger geometry, finger configuration, and material selection.
    """

    def __init__(
        self,
        housing_id: float,
        conditions: Optional[OperatingConditions] = None
    ):
        """
        Initialize optimizer with housing internal diameter.

        Args:
            housing_id: Internal diameter of chute housing (inches)
            conditions: Operating conditions (uses defaults if None)
        """
        self.housing_id = housing_id
        self.conditions = conditions or OperatingConditions()
        self.safety_factor = 2.5

    def calculate_clearance(self, auger_od: float) -> Dict[str, float]:
        """
        Calculate clearance between auger and housing.

        Args:
            auger_od: Outer diameter of auger (inches)

        Returns:
            Dict with clearance analysis results
        """
        clearance_per_side = (self.housing_id - auger_od) / 2
        clearance_ratio = clearance_per_side / self.conditions.max_aggregate_size

        # Determine if clearance is adequate
        min_clearance = self.conditions.max_aggregate_size * 1.2  # 20% safety

        result = {
            "housing_id": self.housing_id,
            "auger_od": auger_od,
            "clearance_per_side": clearance_per_side,
            "clearance_total": clearance_per_side * 2,
            "clearance_ratio": clearance_ratio,
            "min_required": min_clearance,
            "status": "OK" if clearance_per_side >= min_clearance else "FAIL"
        }

        if clearance_per_side < min_clearance:
            result["warning"] = (
                f"Clearance {clearance_per_side:.3f}\" < minimum {min_clearance:.3f}\". "
                f"Risk of aggregate jamming with {self.conditions.max_aggregate_size}\" stone."
            )
        elif clearance_per_side > self.conditions.max_aggregate_size * 2:
            result["warning"] = (
                f"Clearance {clearance_per_side:.3f}\" may be excessive. "
                "Reduced shear efficiency and material bypass possible."
            )

        return result

    def calculate_finger_shear(self, fingers: FingerConfig) -> Dict[str, any]:
        """
        Determine if fingers can shear aggregate based on torque and geometry.

        Args:
            fingers: Finger configuration

        Returns:
            Dict with shear analysis results
        """
        # Force at finger tip = Torque / Radius
        # Assume fingers at average radius
        avg_radius = (self.housing_id / 2) * 0.7  # 70% of housing radius
        avg_radius_ft = avg_radius / 12

        force_per_finger = (
            self.conditions.motor_torque_ft_lb /
            (avg_radius_ft * fingers.count)
        )
        force_per_finger_lbf = force_per_finger

        # Contact area: finger diameter × aggregate size (worst case)
        contact_area = fingers.diameter * self.conditions.max_aggregate_size

        # Pressure on finger
        pressure_psi = force_per_finger_lbf / contact_area

        # Compare to material shear strength
        material_strength = fingers.material.shear_strength_psi
        design_strength = material_strength / self.safety_factor

        result = {
            "force_per_finger_lbf": force_per_finger_lbf,
            "contact_area_sq_in": contact_area,
            "pressure_psi": pressure_psi,
            "material": fingers.material.display_name,
            "material_strength_psi": material_strength,
            "design_strength_psi": design_strength,
            "utilization": pressure_psi / design_strength,
        }

        if pressure_psi > design_strength:
            result["status"] = "FAIL"
            result["recommendation"] = (
                f"Finger stress {pressure_psi:.0f} psi > allowable {design_strength:.0f} psi. "
                "Options: increase finger diameter, add more fingers, or use stronger material."
            )
        elif pressure_psi < design_strength * 0.3:
            result["status"] = "OVER-DESIGNED"
            result["recommendation"] = (
                f"Finger utilization only {result['utilization']*100:.0f}%. "
                "Consider smaller fingers or fewer count for weight reduction."
            )
        else:
            result["status"] = "OK"
            result["recommendation"] = "Finger geometry adequate for shear requirements."

        return result

    def calculate_skeleton_diameter(self) -> Dict[str, float]:
        """
        Calculate minimum stainless steel skeleton wire diameter for torsion.

        For a shaftless auger with SS skeleton + UHMW flighting, the skeleton
        must resist the full motor torque.

        Returns:
            Dict with skeleton sizing results
        """
        torque_in_lb = self.conditions.motor_torque_ft_lb * 12  # ft-lb to in-lb

        # Shear stress formula for solid round bar in torsion:
        # τ = 16T / (π × d³)
        # Solving for d: d = ∛(16T / (π × τ_allow))

        # 304 Stainless Steel shear allowable (with safety factor)
        ss_shear_ultimate = 31000  # psi
        ss_shear_allow = ss_shear_ultimate / self.safety_factor

        d_cubed = (16 * torque_in_lb * self.safety_factor) / (math.pi * ss_shear_allow)
        min_diameter = d_cubed ** (1/3)

        # Round up to standard wire sizes
        standard_sizes = [0.125, 0.1875, 0.25, 0.3125, 0.375, 0.5, 0.625, 0.75]
        recommended_size = next((s for s in standard_sizes if s >= min_diameter), standard_sizes[-1])

        return {
            "torque_in_lb": torque_in_lb,
            "min_diameter_in": min_diameter,
            "recommended_diameter_in": recommended_size,
            "material": "304 Stainless Steel",
            "shear_allowable_psi": ss_shear_allow,
            "safety_factor": self.safety_factor,
        }

    def calculate_thermal_rise(
        self,
        fingers: FingerConfig,
        runtime_minutes: float = 60
    ) -> Dict[str, any]:
        """
        Estimate temperature rise in fingers due to friction.

        Args:
            fingers: Finger configuration
            runtime_minutes: Continuous operation time

        Returns:
            Dict with thermal analysis results
        """
        # Friction power = coefficient × normal force × velocity
        # This is a simplified model

        friction_coeff = 0.3  # Concrete on UHMW estimate
        avg_radius = self.housing_id / 2 * 0.7
        velocity = 2 * math.pi * (avg_radius / 12) * self.conditions.motor_rpm / 60  # ft/s

        # Assume 10% of motor power goes to finger friction
        friction_power_watts = self.conditions.motor_power_hp * 746 * 0.10
        friction_power_btu_hr = friction_power_watts * 3.412

        # Simplified heat rise (very rough estimate)
        # Assumes adiabatic conditions (no cooling)
        heat_capacity = 0.5  # BTU/(lb·°F) for UHMW
        finger_weight_lb = (
            fingers.cross_section_area * fingers.length *
            0.034 * fingers.count  # UHMW density ~0.034 lb/in³
        )

        temp_rise = (friction_power_btu_hr * runtime_minutes / 60) / (finger_weight_lb * heat_capacity)
        final_temp = self.conditions.ambient_temp_f + temp_rise

        result = {
            "friction_power_watts": friction_power_watts,
            "runtime_minutes": runtime_minutes,
            "estimated_temp_rise_f": temp_rise,
            "final_temp_f": final_temp,
            "material_max_temp_f": fingers.material.max_temp_f,
        }

        if final_temp > fingers.material.max_temp_f:
            result["status"] = "FAIL"
            result["recommendation"] = (
                f"Estimated temp {final_temp:.0f}°F exceeds {fingers.material.display_name} "
                f"limit of {fingers.material.max_temp_f}°F. Use high-temp material or add cooling."
            )
        else:
            margin = fingers.material.max_temp_f - final_temp
            result["status"] = "OK"
            result["temp_margin_f"] = margin

        return result

    def generate_optimized_design(
        self,
        target_throughput_bags_hr: float = 45
    ) -> Dict[str, any]:
        """
        Generate an optimized auger design based on constraints.

        Args:
            target_throughput_bags_hr: Target throughput in 80-lb bags/hour

        Returns:
            Complete design specification
        """
        # Calculate optimal auger diameter (leave clearance for aggregate)
        optimal_clearance = self.conditions.max_aggregate_size * 1.5
        auger_od = self.housing_id - (2 * optimal_clearance)
        auger_id = auger_od * 0.82  # ~18% wall for shaftless flight

        # Calculate pitch based on P/D ratios
        pd_hopper = 0.65  # Middle of 0.5-0.8 preferred range
        pd_chute = 0.85   # Middle of 0.6-1.0 range

        pitch_hopper = pd_hopper * auger_od
        pitch_chute = pd_chute * auger_od

        # Estimate lengths (based on 16-30" chute range)
        length_hopper = 10.0  # inches
        length_chute = 14.0   # inches

        geometry = AugerGeometry(
            outer_diameter=auger_od,
            inner_diameter=auger_id,
            length_hopper=length_hopper,
            length_chute=length_chute,
            pitch_hopper=pitch_hopper,
            pitch_chute=pitch_chute,
        )

        # Optimize finger configuration
        fingers = FingerConfig(
            material=FingerMaterial.STEEL_1045,  # Default to steel for durability
            diameter=0.375,  # 3/8" standard
            length=2.0,      # 2" inward projection
            count=8,         # 8 fingers total
        )

        # Run all analyses
        clearance = self.calculate_clearance(auger_od)
        shear = self.calculate_finger_shear(fingers)
        skeleton = self.calculate_skeleton_diameter()
        thermal = self.calculate_thermal_rise(fingers, runtime_minutes=30)

        return {
            "geometry": {
                "auger_od": auger_od,
                "auger_id": auger_id,
                "housing_id": self.housing_id,
                "clearance_per_side": optimal_clearance,
                "pitch_hopper": pitch_hopper,
                "pitch_chute": pitch_chute,
                "length_total": geometry.total_length,
                "pd_ratio_hopper": pd_hopper,
                "pd_ratio_chute": pd_chute,
            },
            "fingers": {
                "material": fingers.material.display_name,
                "diameter": fingers.diameter,
                "length": fingers.length,
                "count": fingers.count,
            },
            "skeleton": skeleton,
            "analysis": {
                "clearance": clearance,
                "shear": shear,
                "thermal": thermal,
            },
            "validation": geometry.validate(),
        }


class PowerSystem:
    """
    Dual power system calculator for AC and DeWalt FlexVolt battery.

    Supports:
    - 120V AC primary (jobsite continuous)
    - DeWalt 20V/60V FlexVolt battery (portable short runs)
    """

    # DeWalt FlexVolt battery specifications
    FLEXVOLT_BATTERIES = {
        "DCB606": {"nominal_v": 54, "max_v": 60, "ah": 6.0},
        "DCB609": {"nominal_v": 54, "max_v": 60, "ah": 9.0},
        "DCB612": {"nominal_v": 54, "max_v": 60, "ah": 12.0},
        "DCB615": {"nominal_v": 54, "max_v": 60, "ah": 15.0},
    }

    def __init__(
        self,
        motor_power_watts: float = 373,  # 0.5 HP
        system_voltage: float = 24.0,     # DC bus voltage
        efficiency: float = 0.85,         # Overall system efficiency
    ):
        self.motor_power = motor_power_watts
        self.system_voltage = system_voltage
        self.efficiency = efficiency

    @property
    def total_power_draw(self) -> float:
        """Total power including losses (watts)."""
        return self.motor_power / self.efficiency

    @property
    def current_draw_24v(self) -> float:
        """Current at 24V DC bus (amps)."""
        return self.total_power_draw / self.system_voltage

    def calculate_ac_specs(self) -> Dict[str, float]:
        """Calculate AC power requirements."""
        return {
            "input_voltage": 120,
            "input_current": self.total_power_draw / 120,
            "power_watts": self.total_power_draw,
            "recommended_circuit": 15,  # amps
            "recommended_wire_gauge": 14,  # AWG for < 50 ft
            "psu_rating_watts": self.total_power_draw * 1.25,  # 25% headroom
        }

    def calculate_battery_runtime(
        self,
        battery_model: str = "DCB612",
        count: int = 1,
        series: bool = False
    ) -> Dict[str, any]:
        """
        Calculate runtime for DeWalt FlexVolt battery configuration.

        Args:
            battery_model: Battery model (DCB606, DCB609, DCB612, DCB615)
            count: Number of batteries
            series: If True, batteries in series (60V+60V=120V)

        Returns:
            Runtime and configuration details
        """
        if battery_model not in self.FLEXVOLT_BATTERIES:
            raise ValueError(f"Unknown battery: {battery_model}")

        battery = self.FLEXVOLT_BATTERIES[battery_model]

        if series and count >= 2:
            # Series: voltage doubles, Ah stays same
            voltage = battery["nominal_v"] * 2  # 108V nominal
            capacity_ah = battery["ah"]
            config = f"{count}× {battery_model} in SERIES (120V MAX)"
        else:
            # Parallel or single: voltage same, Ah multiplies
            voltage = battery["nominal_v"]
            capacity_ah = battery["ah"] * count
            config = f"{count}× {battery_model} ({'PARALLEL' if count > 1 else 'SINGLE'})"

        # Energy in watt-hours
        energy_wh = voltage * capacity_ah

        # Runtime calculation
        runtime_hours = energy_wh / self.total_power_draw
        runtime_minutes = runtime_hours * 60

        # Bags estimate (1 bag per minute at full speed)
        bags_estimate = int(runtime_minutes * 0.8)  # 80% efficiency

        return {
            "configuration": config,
            "voltage_nominal": voltage,
            "capacity_ah": capacity_ah,
            "energy_wh": energy_wh,
            "runtime_hours": runtime_hours,
            "runtime_minutes": runtime_minutes,
            "bags_estimate": bags_estimate,
            "dc_dc_input_range": f"{voltage * 0.8:.0f}-{voltage * 1.1:.0f}V",
            "recommended_dc_dc": f"{voltage}V to 24V @ {self.current_draw_24v:.0f}A",
        }

    def generate_power_system_bom(self) -> List[Dict[str, any]]:
        """Generate bill of materials for dual power system."""
        ac_specs = self.calculate_ac_specs()

        return [
            {
                "item": "AC-DC Power Supply",
                "spec": f"24V {ac_specs['psu_rating_watts']:.0f}W",
                "model": "Mean Well HLG-480H-24A or equiv",
                "qty": 1,
                "est_cost": 120,
            },
            {
                "item": "DC-DC Converter (Battery)",
                "spec": "48-120V input, 24V 20A output",
                "model": "Isolated buck converter",
                "qty": 1,
                "est_cost": 80,
            },
            {
                "item": "FlexVolt Battery Adapter",
                "spec": "60V terminal access",
                "model": "Custom or 3rd party",
                "qty": 1,
                "est_cost": 40,
            },
            {
                "item": "Motor Controller",
                "spec": "24V 30A, FWD/REV",
                "model": "Industrial DC controller",
                "qty": 1,
                "est_cost": 150,
            },
            {
                "item": "Auto Transfer Switch",
                "spec": "AC priority, battery backup",
                "model": "Solid-state relay based",
                "qty": 1,
                "est_cost": 60,
            },
            {
                "item": "Thermal Management",
                "spec": "Fans, heatsinks, sensors",
                "model": "12V cooling system",
                "qty": 1,
                "est_cost": 35,
            },
        ]


class ThermalAnalyzer:
    """
    Advanced thermal analysis for continuous duty operation.

    Critical for 12+ hour jobsite operation where heat buildup
    can exceed material limits.
    """

    # Material thermal properties
    MATERIAL_PROPERTIES = {
        "UHMW_STANDARD": {
            "max_continuous_f": 180,
            "heat_deflection_f": 116,
            "thermal_conductivity": 0.25,  # BTU/(hr·ft·°F)
            "specific_heat": 0.55,  # BTU/(lb·°F)
            "density": 0.034,  # lb/in³
            "melting_f": 275,
        },
        "UHMW_HIGH_TEMP": {
            "max_continuous_f": 250,
            "heat_deflection_f": 160,
            "thermal_conductivity": 0.25,
            "specific_heat": 0.55,
            "density": 0.034,
            "melting_f": 300,
        },
        "TIVAR_HOT": {  # Specialized high-temp UHMW
            "max_continuous_f": 275,
            "heat_deflection_f": 200,
            "thermal_conductivity": 0.28,
            "specific_heat": 0.50,
            "density": 0.035,
            "melting_f": 325,
        },
        "STEEL_1045": {
            "max_continuous_f": 800,
            "heat_deflection_f": 800,
            "thermal_conductivity": 26,
            "specific_heat": 0.12,
            "density": 0.284,
            "melting_f": 2700,
        },
        "STAINLESS_304": {
            "max_continuous_f": 1500,
            "heat_deflection_f": 1500,
            "thermal_conductivity": 9.4,
            "specific_heat": 0.12,
            "density": 0.289,
            "melting_f": 2550,
        },
    }

    def __init__(
        self,
        motor_power_hp: float = 0.5,
        ambient_temp_f: float = 95.0,  # Hot jobsite
        friction_loss_pct: float = 0.15,  # 15% to friction
    ):
        self.motor_power_hp = motor_power_hp
        self.motor_power_watts = motor_power_hp * 746
        self.ambient_temp = ambient_temp_f
        self.friction_loss_pct = friction_loss_pct

    def calculate_steady_state_temp(
        self,
        material: str,
        component_mass_lb: float,
        surface_area_in2: float,
        runtime_hours: float,
        convection_coeff: float = 2.0,  # BTU/(hr·ft²·°F), natural convection
    ) -> Dict[str, any]:
        """
        Calculate steady-state temperature for continuous operation.

        Uses lumped capacitance model with convective cooling.
        """
        if material not in self.MATERIAL_PROPERTIES:
            raise ValueError(f"Unknown material: {material}")

        props = self.MATERIAL_PROPERTIES[material]

        # Heat generation rate (BTU/hr)
        friction_power_watts = self.motor_power_watts * self.friction_loss_pct
        heat_gen_btu_hr = friction_power_watts * 3.412

        # Convective cooling (BTU/hr per °F)
        surface_area_ft2 = surface_area_in2 / 144
        cooling_rate = convection_coeff * surface_area_ft2

        # Steady-state temperature rise (when heat in = heat out)
        # Q_gen = h × A × (T_surface - T_ambient)
        # T_rise = Q_gen / (h × A)
        temp_rise_steady = heat_gen_btu_hr / cooling_rate

        # Time constant for thermal response
        thermal_mass = component_mass_lb * props["specific_heat"]
        time_constant_hr = thermal_mass / cooling_rate

        # Temperature at specified runtime
        fraction_of_steady = 1 - math.exp(-runtime_hours / time_constant_hr)
        temp_rise_at_runtime = temp_rise_steady * fraction_of_steady

        final_temp = self.ambient_temp + temp_rise_at_runtime

        # Safety evaluation
        max_temp = props["max_continuous_f"]
        margin = max_temp - final_temp
        status = "OK" if final_temp < max_temp else "FAIL"

        return {
            "material": material,
            "ambient_temp_f": self.ambient_temp,
            "heat_generation_btu_hr": heat_gen_btu_hr,
            "cooling_rate_btu_hr_f": cooling_rate,
            "temp_rise_steady_state_f": temp_rise_steady,
            "time_constant_hours": time_constant_hr,
            "runtime_hours": runtime_hours,
            "temp_rise_at_runtime_f": temp_rise_at_runtime,
            "final_temp_f": final_temp,
            "max_continuous_f": max_temp,
            "margin_f": margin,
            "status": status,
            "at_steady_state": runtime_hours > 3 * time_constant_hr,
        }

    def recommend_finger_material(
        self,
        duty_cycle: DutyCycle,
        finger_mass_lb: float = 0.5,
        finger_surface_in2: float = 10.0,
    ) -> Dict[str, any]:
        """
        Recommend finger material based on duty cycle thermal requirements.
        """
        runtime = duty_cycle.runtime_hours
        severity = duty_cycle.thermal_severity

        # Test each material
        results = {}
        for material in self.MATERIAL_PROPERTIES:
            analysis = self.calculate_steady_state_temp(
                material=material,
                component_mass_lb=finger_mass_lb,
                surface_area_in2=finger_surface_in2,
                runtime_hours=runtime,
            )
            results[material] = analysis

        # Find suitable materials
        suitable = [m for m, r in results.items() if r["status"] == "OK"]
        unsuitable = [m for m, r in results.items() if r["status"] == "FAIL"]

        # Recommend based on severity and material properties
        if severity == "EXTREME":
            # 12+ hours: Must use steel or stainless
            if "STEEL_1045" in suitable:
                recommended = "STEEL_1045"
                reason = "12+ hour operation requires metal fingers for thermal stability"
            else:
                recommended = "STAINLESS_304"
                reason = "Maximum thermal resistance for extreme duty"
        elif severity == "HIGH":
            # 4-8 hours: High-temp UHMW may work, steel preferred
            if "TIVAR_HOT" in suitable:
                recommended = "TIVAR_HOT"
                reason = "Specialized high-temp UHMW adequate for 4-8 hour duty"
            else:
                recommended = "STEEL_1045"
                reason = "Standard UHMW insufficient, steel required"
        elif severity == "MEDIUM":
            if "UHMW_HIGH_TEMP" in suitable:
                recommended = "UHMW_HIGH_TEMP"
                reason = "High-temp UHMW suitable for medium duty"
            else:
                recommended = "TIVAR_HOT"
                reason = "Elevated temps require better UHMW grade"
        else:
            recommended = "UHMW_STANDARD"
            reason = "Standard UHMW adequate for light duty"

        return {
            "duty_cycle": duty_cycle._name,
            "thermal_severity": severity,
            "runtime_hours": runtime,
            "recommended_material": recommended,
            "reason": reason,
            "suitable_materials": suitable,
            "unsuitable_materials": unsuitable,
            "detailed_analysis": results[recommended],
            "warning": (
                "⚠️ UHMW heat deflection temp (116°F) is LOWER than max continuous. "
                "Under load, deformation may occur before melting."
                if "UHMW" in recommended else None
            ),
        }


class CFDParameters:
    """
    Boundary conditions for Computational Fluid Dynamics simulation.

    Concrete is modeled as a Bingham Plastic fluid:
    τ = τ_y + μ_p × γ̇

    Where:
        τ = shear stress
        τ_y = yield stress (concrete acts solid below this)
        μ_p = plastic viscosity
        γ̇ = shear rate
    """

    def __init__(
        self,
        slump_inches: float = 4.0,
        water_cement_ratio: float = 0.5,
        aggregate_fraction: float = 0.65,
    ):
        self.slump = slump_inches
        self.wc_ratio = water_cement_ratio
        self.aggregate_fraction = aggregate_fraction

    @property
    def yield_stress_pa(self) -> float:
        """Estimate yield stress from slump (empirical correlation)."""
        # τ_y ≈ 300 × (10 - slump) for slump in inches
        return 300 * (10 - self.slump)

    @property
    def plastic_viscosity_pa_s(self) -> float:
        """Estimate plastic viscosity from w/c ratio."""
        # Higher w/c = lower viscosity
        base_viscosity = 30  # Pa·s at w/c = 0.5
        return base_viscosity * (0.5 / self.wc_ratio) ** 1.5

    def generate_cfd_setup(self) -> Dict[str, any]:
        """Generate CFD simulation parameters."""
        return {
            "material_model": "Bingham Plastic",
            "density_kg_m3": 2400,
            "yield_stress_pa": self.yield_stress_pa,
            "plastic_viscosity_pa_s": self.plastic_viscosity_pa_s,
            "inlet": {
                "type": "mass_flow",
                "material": "dry_premix",
                "moisture_content": 0.0,
            },
            "water_injection": {
                "type": "spray_nozzle",
                "count": 2,
                "pressure_psi": 40,
                "angle_degrees": 65,
                "location": "aperture_zone",
            },
            "outlet": {
                "type": "pressure_outlet",
                "target_moisture": 0.12,  # ~12% by weight
            },
            "mesh": {
                "type": "polyhedral",
                "base_size_mm": 5,
                "prism_layers": 5,
                "wall_y_plus": 30,
            },
            "solver": {
                "type": "unsteady_rans",
                "turbulence_model": "k-omega-sst",
                "time_step_s": 0.001,
                "max_iterations": 50,
            },
        }


def main():
    """Example usage of the optimizer with 12-hour jobsite duty cycle."""
    print("=" * 70)
    print("MudMixer Generative Design Framework")
    print("OPTIMIZED FOR 12-HOUR JOBSITE CONTINUOUS OPERATION")
    print("=" * 70)
    print()

    # Initialize with known/assumed housing ID
    housing_id = 6.0  # inches (ASSUMED - needs measurement)

    # NEW: 12-hour continuous duty cycle
    conditions = OperatingConditions(
        motor_power_hp=0.5,
        motor_rpm=27,
        max_aggregate_size=0.5,  # CONFIRMED
        duty_cycle=DutyCycle.JOBSITE_12HR,  # 12+ hours continuous
        ambient_temp_f=95.0,  # Hot jobsite conditions
    )

    optimizer = AugerOptimizer(housing_id, conditions)

    print(f"Housing Internal Diameter: {housing_id}\" (ASSUMED)")
    print(f"Motor: {conditions.motor_power_hp} HP @ {conditions.motor_rpm} RPM")
    print(f"Torque: {conditions.motor_torque_ft_lb:.1f} ft-lb ({conditions.motor_torque_nm:.1f} N·m)")
    print(f"Max Aggregate: {conditions.max_aggregate_size}\" (CONFIRMED)")
    print(f"Duty Cycle: {conditions.duty_cycle._name} ({conditions.duty_cycle.runtime_hours} hours)")
    print(f"Thermal Severity: {conditions.duty_cycle.thermal_severity}")
    print()

    # Generate optimized design
    design = optimizer.generate_optimized_design()

    print("-" * 70)
    print("OPTIMIZED GEOMETRY")
    print("-" * 70)
    for key, value in design["geometry"].items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}\"")
        else:
            print(f"  {key}: {value}")

    print()
    print("-" * 70)
    print("FINGER CONFIGURATION")
    print("-" * 70)
    for key, value in design["fingers"].items():
        print(f"  {key}: {value}")

    print()
    print("-" * 70)
    print("SKELETON SIZING")
    print("-" * 70)
    skeleton = design["skeleton"]
    print(f"  Minimum diameter: {skeleton['min_diameter_in']:.3f}\"")
    print(f"  Recommended: {skeleton['recommended_diameter_in']}\" SS wire")

    print()
    print("=" * 70)
    print("THERMAL ANALYSIS (12-HOUR CONTINUOUS)")
    print("=" * 70)

    thermal_analyzer = ThermalAnalyzer(
        motor_power_hp=0.5,
        ambient_temp_f=95.0,  # Hot jobsite
        friction_loss_pct=0.15,
    )

    # Get material recommendation for 12-hour duty
    material_rec = thermal_analyzer.recommend_finger_material(
        duty_cycle=DutyCycle.JOBSITE_12HR,
        finger_mass_lb=0.5,
        finger_surface_in2=10.0,
    )

    print(f"  Thermal Severity: {material_rec['thermal_severity']}")
    print(f"  Recommended Material: {material_rec['recommended_material']}")
    print(f"  Reason: {material_rec['reason']}")
    print()
    print(f"  Suitable materials: {', '.join(material_rec['suitable_materials'])}")
    print(f"  Unsuitable materials: {', '.join(material_rec['unsuitable_materials'])}")
    if material_rec.get("warning"):
        print(f"  {material_rec['warning']}")

    print()
    print("=" * 70)
    print("DUAL POWER SYSTEM")
    print("=" * 70)

    power = PowerSystem(motor_power_watts=373, system_voltage=24.0)

    # AC specifications
    ac_specs = power.calculate_ac_specs()
    print()
    print("  PRIMARY: 120V AC")
    print(f"    Input current: {ac_specs['input_current']:.1f} A")
    print(f"    Power draw: {ac_specs['power_watts']:.0f} W")
    print(f"    PSU rating: {ac_specs['psu_rating_watts']:.0f} W (with headroom)")
    print(f"    Runtime: UNLIMITED (continuous)")

    # Battery configurations
    print()
    print("  SECONDARY: DeWalt FlexVolt Battery")
    print()

    for battery in ["DCB609", "DCB612", "DCB615"]:
        # Single battery
        single = power.calculate_battery_runtime(battery, count=1)
        print(f"    {single['configuration']}:")
        print(f"      Runtime: {single['runtime_minutes']:.0f} min ({single['runtime_hours']:.2f} hr)")
        print(f"      Bags: ~{single['bags_estimate']}")

    print()
    # Dual battery series
    dual = power.calculate_battery_runtime("DCB612", count=2, series=True)
    print(f"    {dual['configuration']}:")
    print(f"      Runtime: {dual['runtime_minutes']:.0f} min ({dual['runtime_hours']:.2f} hr)")
    print(f"      Bags: ~{dual['bags_estimate']}")

    print()
    print("=" * 70)
    print("POWER SYSTEM BOM")
    print("=" * 70)
    bom = power.generate_power_system_bom()
    total_cost = 0
    for item in bom:
        print(f"  {item['item']}: {item['spec']}")
        print(f"    Model: {item['model']}, Qty: {item['qty']}, Est: ${item['est_cost']}")
        total_cost += item['est_cost']
    print(f"\n  TOTAL ESTIMATED: ${total_cost}")

    print()
    print("=" * 70)
    print("CFD SIMULATION PARAMETERS")
    print("=" * 70)
    cfd = CFDParameters(slump_inches=4.0)
    params = cfd.generate_cfd_setup()
    print(f"  Material Model: {params['material_model']}")
    print(f"  Yield Stress: {params['yield_stress_pa']:.0f} Pa")
    print(f"  Plastic Viscosity: {params['plastic_viscosity_pa_s']:.1f} Pa·s")

    print()
    print("=" * 70)
    print("CRITICAL FINDINGS FOR 12-HOUR OPERATION")
    print("=" * 70)
    print("""
  1. FINGER MATERIAL: Must use STEEL or STAINLESS STEEL
     - Standard UHMW will FAIL (max 180°F, heat deflection 116°F)
     - 12-hour friction heat exceeds plastic limits

  2. THERMAL MANAGEMENT: Active cooling recommended
     - Electronics enclosure needs ventilation
     - Motor controller needs heatsink + fan

  3. POWER SYSTEM: Dual-source design
     - 120V AC primary for continuous operation
     - DeWalt FlexVolt battery for portable runs (1.5-3 hr max)

  4. MOTOR UPGRADE: Consider 0.75 HP for continuous duty
     - 0.5 HP marginal for 12-hour operation
     - Higher power allows lower duty cycle per bag
""")


if __name__ == "__main__":
    main()
