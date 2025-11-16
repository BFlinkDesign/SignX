"""
Engineering Constants for Signage Domain

All constants with code references for traceability and PE compliance.
No magic numbers in calculation code - all values defined here with sources.

Standards:
- ASCE 7-22: Minimum Design Loads
- IBC 2024: International Building Code
- AISC 360-22: Specification for Structural Steel Buildings
- ACI 318-19: Building Code Requirements for Structural Concrete

Author: Claude Code
Date: 2025-11-02
"""

# ============================================================================
# ASCE 7-22 Constants
# ============================================================================

# Wind Load Constants
ASCE7_22_VELOCITY_PRESSURE_COEFFICIENT = 0.00256  # psf/(mph²) - Equation 26.10-1
ASCE7_22_WIND_DIRECTIONALITY_SIGNS = 0.85  # Kd for signs - Table 26.6-1
ASCE7_22_GUST_EFFECT_RIGID = 0.85  # G for rigid structures - Section 26.11
ASCE7_22_FORCE_COEFF_FLAT_SIGN = 1.2  # Cf for flat signs - Figure 29.4-1

# Wind Speed Ranges
ASCE7_22_WIND_SPEED_MIN_MPH = 85.0  # Minimum basic wind speed (ASCE 7 maps)
ASCE7_22_WIND_SPEED_MAX_MPH = 200.0  # Typical maximum (special regions may exceed)

# Load Combinations (Section 2.3)
ASCE7_22_LOAD_FACTOR_DEAD = 1.2  # Dead load factor (strength design)
ASCE7_22_LOAD_FACTOR_WIND = 1.0  # Wind load factor (ultimate strength)
ASCE7_22_LOAD_FACTOR_SEISMIC = 1.0  # Seismic load factor


# ============================================================================
# IBC 2024 Constants
# ============================================================================

# Foundation Design
IBC_2024_MIN_FOUNDATION_DEPTH_FT = 2.0  # Minimum depth below grade - Section 1807.1.6.2
IBC_2024_FOUNDATION_CONSTANT = 4.36  # Empirical constant for Equation 18-1
IBC_2024_OVERTURNING_SAFETY_FACTOR = 1.5  # Safety factor for overturning - Section 1605.2.1

# Soil Properties
IBC_2024_SOIL_BEARING_DEFAULT_PSF = 3000.0  # Table 1806.2 (medium clay)
IBC_2024_SOIL_LATERAL_COEFF = 150.0  # pcf - Table 1806.2


# ============================================================================
# AISC 360-22 Constants
# ============================================================================

# Steel Material Properties
AISC_360_22_E_STEEL_KSI = 29000.0  # Modulus of elasticity (ksi) - Table 2-4
AISC_360_22_G_STEEL_KSI = 11200.0  # Shear modulus (ksi) - Table 2-4

# Design Factors (ASD)
AISC_360_22_ASD_BENDING_FACTOR = 0.66  # Fb = 0.66 * Fy (allowable bending stress)
AISC_360_22_ASD_SHEAR_FACTOR = 0.40  # Fv = 0.40 * Fy (allowable shear stress)
AISC_360_22_ASD_COMPRESSION_FACTOR = 0.60  # Fc = 0.60 * Fy (stocky compression)

# Design Factors (LRFD)
AISC_360_22_PHI_BENDING = 0.90  # Resistance factor for bending - Section F1
AISC_360_22_PHI_COMPRESSION = 0.90  # Resistance factor for compression - Section E1
AISC_360_22_PHI_TENSION = 0.90  # Resistance factor for tension - Section D2

# Steel Grades (Yield Strength in ksi)
AISC_360_22_FY_A36_KSI = 36.0  # A36 hot-rolled steel
AISC_360_22_FY_A500B_KSI = 46.0  # A500 Grade B HSS (rectangular)
AISC_360_22_FY_A500C_KSI = 50.0  # A500 Grade C HSS (round)
AISC_360_22_FY_A572_50_KSI = 50.0  # A572 Grade 50
AISC_360_22_FY_A992_KSI = 50.0  # A992 W-shapes

# Base Plate Design
AISC_360_22_BASEPLATE_BEARING_FACTOR = 0.85  # φ for bearing on concrete


# ============================================================================
# ACI 318-19 Constants
# ============================================================================

# Concrete Material Properties
ACI_318_19_FC_DEFAULT_KSI = 3.0  # Default concrete compressive strength (3000 psi)
ACI_318_19_CONCRETE_DENSITY_PCF = 150.0  # Normal weight concrete (pcf)

# Rebar Properties
ACI_318_19_FY_REBAR_KSI = 60.0  # Grade 60 rebar yield strength (most common)
ACI_318_19_ES_REBAR_KSI = 29000.0  # Modulus of elasticity for steel

# Design Factors
ACI_318_19_PHI_FLEXURE = 0.90  # Strength reduction factor for flexure - Section 21.2
ACI_318_19_PHI_SHEAR = 0.75  # Strength reduction factor for shear - Section 21.2
ACI_318_19_PHI_COMPRESSION = 0.65  # Strength reduction factor for compression - Section 21.2

# Cover Requirements (Table 20.6.1.3.1)
ACI_318_19_MIN_COVER_IN = 3.0  # Minimum cover for concrete cast against earth (in)
ACI_318_19_MIN_COVER_FORMED_IN = 1.5  # Minimum cover for formed surfaces (in)

# Development Length
ACI_318_19_DEVELOPMENT_LENGTH_FACTOR = 25.0  # Constant in development length equation
ACI_318_19_MIN_DEVELOPMENT_LENGTH_IN = 12.0  # Minimum development length (in)

# Reinforcement Ratios
ACI_318_19_MIN_STEEL_RATIO = 0.0018  # Minimum reinforcement ratio for slabs
ACI_318_19_MAX_STEEL_RATIO = 0.025  # Maximum practical reinforcement ratio


# ============================================================================
# Precision Standards for PE Compliance
# ============================================================================

# Deterministic rounding precision for all outputs
PRECISION_FORCE_LBS = 1  # Round forces to 1 lb
PRECISION_MOMENT_KIPFT = 2  # Round moments to 0.01 kip-ft
PRECISION_STRESS_KSI = 3  # Round stresses to 0.001 ksi
PRECISION_DIMENSION_FT = 2  # Round dimensions to 0.01 ft
PRECISION_DIMENSION_IN = 2  # Round dimensions to 0.01 in


# ============================================================================
# System Limits
# ============================================================================

# Calculation Bounds
MAX_FOOTING_DEPTH_FT = 15.0  # Maximum practical footing depth
MAX_POLE_HEIGHT_FT = 100.0  # Maximum pole height
MAX_SIGN_AREA_FT2 = 1000.0  # Maximum single sign face area

# Database Cache
DEFAULT_CACHE_SIZE = 256  # LRU cache size for calculations
