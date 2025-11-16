"""
Type Definitions for Signage Engineering Domain

Enhanced type safety using NewType for domain-specific units.
Prevents unit confusion errors (e.g., mixing feet and inches, kips and pounds).

Author: Claude Code
Date: 2025-11-02
"""

from typing import NewType

# ============================================================================
# Dimensional Types
# ============================================================================

Feet = NewType('Feet', float)
"""Length in feet"""

Inches = NewType('Inches', float)
"""Length in inches"""

Meters = NewType('Meters', float)
"""Length in meters"""


# ============================================================================
# Force Types
# ============================================================================

Pounds = NewType('Pounds', float)
"""Force in pounds (lb)"""

Kips = NewType('Kips', float)
"""Force in kips (1 kip = 1000 lb)"""

KipFt = NewType('KipFt', float)
"""Moment in kip-feet"""

KipIn = NewType('KipIn', float)
"""Moment in kip-inches"""


# ============================================================================
# Stress Types
# ============================================================================

Psi = NewType('Psi', float)
"""Stress in pounds per square inch"""

Ksi = NewType('Ksi', float)
"""Stress in kips per square inch (1 ksi = 1000 psi)"""

Psf = NewType('Psf', float)
"""Pressure in pounds per square foot"""


# ============================================================================
# Velocity & Speed
# ============================================================================

Mph = NewType('Mph', float)
"""Velocity in miles per hour"""

Fps = NewType('Fps', float)
"""Velocity in feet per second"""


# ============================================================================
# Volume & Mass
# ============================================================================

CubicFeet = NewType('CubicFeet', float)
"""Volume in cubic feet"""

CubicYards = NewType('CubicYards', float)
"""Volume in cubic yards"""

Tons = NewType('Tons', float)
"""Mass in tons (US short tons, 2000 lb)"""


# ============================================================================
# Area
# ============================================================================

SquareFeet = NewType('SquareFeet', float)
"""Area in square feet"""

SquareInches = NewType('SquareInches', float)
"""Area in square inches"""


# ============================================================================
# Unitless Ratios
# ============================================================================

Ratio = NewType('Ratio', float)
"""Dimensionless ratio (0.0 to 1.0)"""

Percentage = NewType('Percentage', float)
"""Percentage (0.0 to 100.0)"""


# ============================================================================
# Helper Functions
# ============================================================================

def kips_to_pounds(k: Kips) -> Pounds:
    """Convert kips to pounds."""
    return Pounds(k * 1000.0)


def pounds_to_kips(lb: Pounds) -> Kips:
    """Convert pounds to kips."""
    return Kips(lb / 1000.0)


def feet_to_inches(ft: Feet) -> Inches:
    """Convert feet to inches."""
    return Inches(ft * 12.0)


def inches_to_feet(inches: Inches) -> Feet:
    """Convert inches to feet."""
    return Feet(inches / 12.0)


def ksi_to_psi(ksi_val: Ksi) -> Psi:
    """Convert ksi to psi."""
    return Psi(ksi_val * 1000.0)


def psi_to_ksi(psi_val: Psi) -> Ksi:
    """Convert psi to ksi."""
    return Ksi(psi_val / 1000.0)


def calculate_moment(force: Kips, arm: Feet) -> KipFt:
    """Calculate moment from force and moment arm (type-safe)."""
    return KipFt(force * arm)


def cubic_feet_to_cubic_yards(cf: CubicFeet) -> CubicYards:
    """Convert cubic feet to cubic yards."""
    return CubicYards(cf / 27.0)


def cubic_yards_to_cubic_feet(cy: CubicYards) -> CubicFeet:
    """Convert cubic yards to cubic feet."""
    return CubicFeet(cy * 27.0)
