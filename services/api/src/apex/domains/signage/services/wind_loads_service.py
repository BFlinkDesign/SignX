"""
Wind Load Service - ASCE 7-22 Implementation

Complete refactored service demonstrating best practices:
- Service layer pattern with dependency injection
- Comprehensive type safety
- Structured error handling
- Engineering validation
- Full code compliance documentation

Standards: ASCE 7-22 Minimum Design Loads for Buildings and Other Structures

Author: Claude Code (Refactoring Pattern Example)
Date: 2025-11-02
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

import structlog
from pydantic import BaseModel, Field, field_validator

from ..constants import (
    ASCE7_22_VELOCITY_PRESSURE_COEFFICIENT,
    ASCE7_22_WIND_DIRECTIONALITY_SIGNS,
    ASCE7_22_GUST_EFFECT_RIGID,
    ASCE7_22_FORCE_COEFF_FLAT_SIGN,
    ASCE7_22_WIND_SPEED_MIN_MPH,
    ASCE7_22_WIND_SPEED_MAX_MPH,
)
from ..exceptions import ValidationError, CalculationError
from ..types import Psf, Mph, Feet, Pounds

logger = structlog.get_logger(__name__)


# ============================================================================
# Domain Models
# ============================================================================

class ExposureCategory(str, Enum):
    """Wind exposure categories per ASCE 7-22 Section 26.7."""
    B = "B"  # Urban/suburban (many obstructions)
    C = "C"  # Open terrain (most common)
    D = "D"  # Flat coastal areas


class RiskCategory(str, Enum):
    """Risk categories per ASCE 7-22 Table 1.5-1."""
    I = "I"      # Low hazard
    II = "II"    # Normal (most buildings)
    III = "III"  # Substantial hazard
    IV = "IV"    # Essential facilities


class WindLoadInput(BaseModel):
    """Type-safe, validated input for wind load calculations."""

    wind_speed_mph: float = Field(
        ge=ASCE7_22_WIND_SPEED_MIN_MPH,
        le=300,  # Allow higher for special regions
        description="Basic wind speed (3-second gust) per ASCE 7-22 Figure 26.5-1"
    )

    height_ft: float = Field(
        gt=0,
        le=500,  # Reasonable limit for sign structures
        description="Height above ground level (ft)"
    )

    exposure: ExposureCategory = Field(
        default=ExposureCategory.C,
        description="Wind exposure category per ASCE 7-22 Section 26.7"
    )

    risk_category: RiskCategory = Field(
        default=RiskCategory.II,
        description="Risk category per ASCE 7-22 Table 1.5-1"
    )

    # Optional factors (defaults per ASCE 7-22)
    kzt: float = Field(
        default=1.0,
        ge=1.0,
        le=2.0,
        description="Topographic factor per Section 26.8 (1.0 for flat terrain)"
    )

    kd: float = Field(
        default=ASCE7_22_WIND_DIRECTIONALITY_SIGNS,
        ge=0.85,
        le=1.0,
        description="Wind directionality factor per Table 26.6-1"
    )

    ke: float = Field(
        default=1.0,
        ge=0.9,
        le=1.2,
        description="Elevation factor per Section 26.9"
    )

    @field_validator('wind_speed_mph')
    @classmethod
    def validate_wind_speed(cls, v: float) -> float:
        """Validate wind speed is within ASCE 7-22 range."""
        if v > ASCE7_22_WIND_SPEED_MAX_MPH:
            logger.warning(
                "wind.speed_exceeds_typical_range",
                wind_speed_mph=v,
                typical_max=ASCE7_22_WIND_SPEED_MAX_MPH,
                message="Verify with local jurisdiction for special wind regions"
            )
        return v


class VelocityPressureResult(BaseModel):
    """Type-safe result from velocity pressure calculation."""

    qz_psf: float = Field(description="Velocity pressure (psf)")
    kz: float = Field(description="Velocity pressure exposure coefficient")
    height_ft: float = Field(description="Height used in calculation (ft)")
    exposure: ExposureCategory = Field(description="Exposure category used")
    code_ref: str = Field(description="ASCE 7-22 equation reference")

    class Config:
        frozen = True  # Immutable for determinism


class WindForceResult(BaseModel):
    """Complete wind force analysis result."""

    # Velocity pressure
    qz_psf: float
    kz: float

    # Design pressure
    design_pressure_psf: float
    gust_effect_factor: float
    force_coefficient: float

    # Wind force
    total_wind_force_lbs: float
    tributary_area_ft2: float

    # Code references
    code_references: list[str]

    class Config:
        frozen = True


# ============================================================================
# Wind Load Service
# ============================================================================

class WindLoadService:
    """
    ASCE 7-22 Wind Load Service.

    Provides deterministic, code-compliant wind load calculations
    with comprehensive validation and error handling.

    This service demonstrates the refactored architecture pattern:
    - Dependency injection for testing
    - Type-safe inputs/outputs
    - Structured error handling
    - Comprehensive logging
    - Code compliance documentation

    Standards:
        ASCE 7-22 Minimum Design Loads for Buildings and Other Structures

    Examples:
        >>> service = WindLoadService(code_version="ASCE7-22")
        >>> result = service.calculate_velocity_pressure(
        ...     wind_speed_mph=115,
        ...     height_ft=15,
        ...     exposure=ExposureCategory.C
        ... )
        >>> print(f"qz = {result.qz_psf:.2f} psf")
        qz = 24.46 psf
    """

    def __init__(self, code_version: str = "ASCE7-22"):
        """
        Initialize wind load service.

        Args:
            code_version: Code version string for traceability
        """
        self.code_version = code_version
        logger.info("wind_service.initialized", code_version=code_version)

    def calculate_velocity_pressure(
        self,
        wind_speed_mph: float,
        height_ft: float,
        exposure: ExposureCategory | Literal["B", "C", "D"],
        kzt: float = 1.0,
        kd: float = ASCE7_22_WIND_DIRECTIONALITY_SIGNS,
        ke: float = 1.0,
    ) -> VelocityPressureResult:
        """
        Calculate velocity pressure qz per ASCE 7-22 Equation 26.10-1.

        Implements: qz = 0.00256 * Kz * Kzt * Kd * Ke * V²

        Args:
            wind_speed_mph: Basic wind speed (3-second gust) in mph
            height_ft: Height above ground in feet
            exposure: Wind exposure category (B, C, or D)
            kzt: Topographic factor (default 1.0 for flat terrain)
            kd: Wind directionality factor (default 0.85 for signs)
            ke: Elevation factor (default 1.0 for elevations < 3000 ft)

        Returns:
            VelocityPressureResult with qz, kz, and metadata

        Raises:
            ValidationError: If inputs are outside valid ranges
            CalculationError: If calculation fails

        References:
            - ASCE 7-22 Section 26.10: Velocity Pressure
            - ASCE 7-22 Equation 26.10-1
            - ASCE 7-22 Table 26.10-1: Velocity Pressure Exposure Coefficients
        """
        # Convert exposure to enum if string
        if isinstance(exposure, str):
            exposure = ExposureCategory(exposure)

        # Validate inputs using Pydantic model
        try:
            validated_input = WindLoadInput(
                wind_speed_mph=wind_speed_mph,
                height_ft=height_ft,
                exposure=exposure,
                kzt=kzt,
                kd=kd,
                ke=ke,
            )
        except Exception as e:
            raise ValidationError(
                message=f"Invalid wind load input: {e}",
                code_ref="ASCE 7-22 Section 26.10",
                wind_speed_mph=wind_speed_mph,
                height_ft=height_ft,
            ) from e

        # Calculate Kz (exposure coefficient)
        kz = self._calculate_kz(validated_input.height_ft, validated_input.exposure)

        # Calculate velocity pressure per Equation 26.10-1
        # qz = 0.00256 * Kz * Kzt * Kd * Ke * V²
        qz = (
            ASCE7_22_VELOCITY_PRESSURE_COEFFICIENT
            * kz
            * validated_input.kzt
            * validated_input.kd
            * validated_input.ke
            * (validated_input.wind_speed_mph ** 2)
        )

        # Log calculation for audit trail
        logger.info(
            "wind.velocity_pressure_calculated",
            qz_psf=round(qz, 2),
            kz=round(kz, 4),
            wind_speed_mph=validated_input.wind_speed_mph,
            height_ft=validated_input.height_ft,
            exposure=validated_input.exposure.value,
        )

        return VelocityPressureResult(
            qz_psf=qz,
            kz=kz,
            height_ft=validated_input.height_ft,
            exposure=validated_input.exposure,
            code_ref=f"{self.code_version} Eq 26.10-1",
        )

    def _calculate_kz(
        self,
        height_ft: float,
        exposure: ExposureCategory,
    ) -> float:
        """
        Calculate velocity pressure exposure coefficient Kz.

        Per ASCE 7-22 Table 26.10-1 and Section 26.10.1.

        Args:
            height_ft: Height above ground (ft)
            exposure: Exposure category

        Returns:
            Kz coefficient (dimensionless)

        References:
            - ASCE 7-22 Table 26.10-1
            - ASCE 7-22 Equation 26.10-1 (for heights > 160 ft)
        """
        # Use minimum height of 15 ft per code
        z = max(15.0, height_ft)

        # Exposure B: Urban/suburban
        if exposure == ExposureCategory.B:
            if z <= 30:
                return 0.57
            elif z <= 40:
                return 0.62
            elif z <= 50:
                return 0.66
            elif z <= 60:
                return 0.70
            elif z <= 70:
                return 0.73
            elif z <= 80:
                return 0.76
            elif z <= 90:
                return 0.79
            elif z <= 100:
                return 0.81
            else:
                # Power law for heights > 100 ft
                alpha = 7.0  # Exposure B
                zg = 1200.0  # Gradient height (ft)
                return 2.01 * ((z / zg) ** (2.0 / alpha))

        # Exposure C: Open terrain (most common)
        elif exposure == ExposureCategory.C:
            if z <= 20:
                return 0.85
            elif z <= 25:
                return 0.90
            elif z <= 30:
                return 0.94
            elif z <= 40:
                return 1.00
            elif z <= 50:
                return 1.04
            elif z <= 60:
                return 1.09
            elif z <= 70:
                return 1.13
            elif z <= 80:
                return 1.17
            elif z <= 90:
                return 1.20
            elif z <= 100:
                return 1.24
            else:
                # Power law for heights > 100 ft
                alpha = 9.5  # Exposure C
                zg = 900.0  # Gradient height (ft)
                return 2.01 * ((z / zg) ** (2.0 / alpha))

        # Exposure D: Flat coastal
        elif exposure == ExposureCategory.D:
            if z <= 20:
                return 1.03
            elif z <= 25:
                return 1.08
            elif z <= 30:
                return 1.12
            elif z <= 40:
                return 1.19
            elif z <= 50:
                return 1.25
            elif z <= 60:
                return 1.31
            elif z <= 70:
                return 1.36
            elif z <= 80:
                return 1.41
            elif z <= 90:
                return 1.45
            elif z <= 100:
                return 1.49
            else:
                # Power law for heights > 100 ft
                alpha = 11.5  # Exposure D
                zg = 700.0  # Gradient height (ft)
                return 2.01 * ((z / zg) ** (2.0 / alpha))

        else:
            raise CalculationError(
                message=f"Invalid exposure category: {exposure}",
                code_ref="ASCE 7-22 Section 26.7",
                exposure=exposure,
            )

    def calculate_wind_force(
        self,
        wind_speed_mph: float,
        height_ft: float,
        exposure: ExposureCategory | Literal["B", "C", "D"],
        tributary_area_ft2: float,
        risk_category: RiskCategory | Literal["I", "II", "III", "IV"] = RiskCategory.II,
        force_coefficient: float = ASCE7_22_FORCE_COEFF_FLAT_SIGN,
        gust_effect_factor: float = ASCE7_22_GUST_EFFECT_RIGID,
    ) -> WindForceResult:
        """
        Calculate total wind force on sign per ASCE 7-22 Chapter 29.

        Implements complete wind force calculation for sign structures.

        Args:
            wind_speed_mph: Basic wind speed (mph)
            height_ft: Height above ground (ft)
            exposure: Exposure category
            tributary_area_ft2: Sign projected area (ft²)
            risk_category: Risk category (default II)
            force_coefficient: Cf per Figure 29.4-1 (default 1.2 for flat signs)
            gust_effect_factor: G per Section 26.11 (default 0.85 for rigid)

        Returns:
            WindForceResult with complete analysis

        References:
            - ASCE 7-22 Chapter 29: Wind Loads on Building Appurtenances
            - ASCE 7-22 Figure 29.4-1: Force Coefficients
        """
        # Convert to enums if strings
        if isinstance(exposure, str):
            exposure = ExposureCategory(exposure)
        if isinstance(risk_category, str):
            risk_category = RiskCategory(risk_category)

        # Calculate velocity pressure
        vp_result = self.calculate_velocity_pressure(
            wind_speed_mph=wind_speed_mph,
            height_ft=height_ft,
            exposure=exposure,
        )

        # Wind importance factor per Table 1.5-2
        iw_factors = {
            RiskCategory.I: 0.87,
            RiskCategory.II: 1.00,
            RiskCategory.III: 1.15,
            RiskCategory.IV: 1.15,
        }
        iw = iw_factors[risk_category]

        # Design pressure: p = qz * G * Cf * Iw
        design_pressure_psf = vp_result.qz_psf * gust_effect_factor * force_coefficient * iw

        # Total wind force: F = p * A
        total_force_lbs = design_pressure_psf * tributary_area_ft2

        code_refs = [
            vp_result.code_ref,
            f"{self.code_version} Chapter 29: Wind Loads on Signs",
            f"{self.code_version} Figure 29.4-1: Force Coefficients",
            f"{self.code_version} Table 1.5-2: Wind Importance Factors",
        ]

        logger.info(
            "wind.force_calculated",
            total_force_lbs=round(total_force_lbs, 1),
            design_pressure_psf=round(design_pressure_psf, 2),
            tributary_area_ft2=tributary_area_ft2,
        )

        return WindForceResult(
            qz_psf=vp_result.qz_psf,
            kz=vp_result.kz,
            design_pressure_psf=design_pressure_psf,
            gust_effect_factor=gust_effect_factor,
            force_coefficient=force_coefficient,
            total_wind_force_lbs=total_force_lbs,
            tributary_area_ft2=tributary_area_ft2,
            code_references=code_refs,
        )
