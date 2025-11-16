"""
Comprehensive Test Suite for Wind Load Service

Demonstrates testing patterns:
- Unit tests with pytest
- Property-based testing with hypothesis
- Determinism tests for PE compliance
- Monotonicity tests for engineering validity
- Code compliance verification
- Edge case coverage

Author: Claude Code (Refactoring Pattern Example)
Date: 2025-11-02
"""

import pytest
from hypothesis import given, strategies as st, assume

from apex.domains.signage.services.wind_loads_service import (
    WindLoadService,
    ExposureCategory,
    RiskCategory,
    VelocityPressureResult,
    WindForceResult,
)
from apex.domains.signage.exceptions import ValidationError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def wind_service():
    """Create wind load service instance for testing."""
    return WindLoadService(code_version="ASCE7-22-TEST")


@pytest.fixture
def typical_wind_inputs():
    """Typical wind load inputs for testing."""
    return {
        "wind_speed_mph": 115.0,
        "height_ft": 15.0,
        "exposure": ExposureCategory.C,
    }


# ============================================================================
# Unit Tests - Velocity Pressure
# ============================================================================

class TestVelocityPressure:
    """Test suite for velocity pressure calculations."""

    def test_asce7_example_calculation(self, wind_service):
        """
        Verify against ASCE 7-22 Commentary Example.

        Per ASCE 7-22 Commentary Example C26.10-1:
        - V = 115 mph
        - Exposure C
        - z = 15 ft
        - Expected qz ≈ 24.5 psf
        """
        result = wind_service.calculate_velocity_pressure(
            wind_speed_mph=115,
            height_ft=15,
            exposure=ExposureCategory.C,
        )

        # Verify result structure
        assert isinstance(result, VelocityPressureResult)
        assert result.exposure == ExposureCategory.C
        assert result.height_ft == 15.0
        assert "ASCE7-22" in result.code_ref

        # Verify calculation (within 2% tolerance)
        expected_qz = 24.46  # From ASCE 7-22 example
        assert abs(result.qz_psf - expected_qz) < 0.5, \
            f"Expected qz ≈ {expected_qz} psf, got {result.qz_psf:.2f} psf"

        # Verify Kz for Exposure C at 15 ft
        assert abs(result.kz - 0.85) < 0.01, \
            f"Expected Kz = 0.85 for Exposure C at 15 ft, got {result.kz:.4f}"

    def test_exposure_b_urban(self, wind_service):
        """Test Exposure B (urban/suburban) calculations."""
        result = wind_service.calculate_velocity_pressure(
            wind_speed_mph=100,
            height_ft=30,
            exposure=ExposureCategory.B,
        )

        # Exposure B should have lower Kz than C (more obstructions)
        assert result.kz < 0.85, \
            "Exposure B should have lower Kz than Exposure C"

        # Verify Kz from ASCE 7-22 Table 26.10-1
        assert abs(result.kz - 0.57) < 0.01, \
            f"Expected Kz = 0.57 for Exposure B at 30 ft"

    def test_exposure_d_coastal(self, wind_service):
        """Test Exposure D (flat coastal) calculations."""
        result = wind_service.calculate_velocity_pressure(
            wind_speed_mph=120,
            height_ft=20,
            exposure=ExposureCategory.D,
        )

        # Exposure D should have higher Kz than C (less obstructions)
        assert result.kz > 0.85, \
            "Exposure D should have higher Kz than Exposure C"

        # Verify Kz from ASCE 7-22 Table 26.10-1
        assert abs(result.kz - 1.03) < 0.01, \
            f"Expected Kz = 1.03 for Exposure D at 20 ft"

    def test_minimum_height_enforcement(self, wind_service):
        """
        Test that heights < 15 ft use Kz at 15 ft per ASCE 7-22.

        ASCE 7-22 requires minimum height of 15 ft for velocity pressure.
        """
        result_low = wind_service.calculate_velocity_pressure(
            wind_speed_mph=100,
            height_ft=5,  # Below minimum
            exposure=ExposureCategory.C,
        )

        result_15 = wind_service.calculate_velocity_pressure(
            wind_speed_mph=100,
            height_ft=15,  # Minimum
            exposure=ExposureCategory.C,
        )

        # Both should use Kz at 15 ft
        assert result_low.kz == result_15.kz, \
            "Heights < 15 ft should use Kz at 15 ft per code"

        # But height_ft in result should reflect actual input
        assert result_low.height_ft == 5.0
        assert result_15.height_ft == 15.0

    def test_topographic_factor(self, wind_service):
        """Test topographic factor Kzt increases pressure."""
        result_flat = wind_service.calculate_velocity_pressure(
            wind_speed_mph=100,
            height_ft=20,
            exposure=ExposureCategory.C,
            kzt=1.0,  # Flat terrain
        )

        result_hill = wind_service.calculate_velocity_pressure(
            wind_speed_mph=100,
            height_ft=20,
            exposure=ExposureCategory.C,
            kzt=1.15,  # Hill/ridge
        )

        # Higher Kzt should increase qz proportionally
        expected_ratio = 1.15 / 1.0
        actual_ratio = result_hill.qz_psf / result_flat.qz_psf

        assert abs(actual_ratio - expected_ratio) < 0.01, \
            f"Kzt should scale qz linearly"

    def test_validates_negative_wind_speed(self, wind_service):
        """Test that negative wind speeds are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            wind_service.calculate_velocity_pressure(
                wind_speed_mph=-10.0,
                height_ft=15,
                exposure=ExposureCategory.C,
            )

        assert "Invalid wind load input" in str(exc_info.value)

    def test_validates_zero_height(self, wind_service):
        """Test that zero or negative height is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            wind_service.calculate_velocity_pressure(
                wind_speed_mph=100,
                height_ft=0,
                exposure=ExposureCategory.C,
            )

        assert "Invalid wind load input" in str(exc_info.value)

    def test_validates_extreme_wind_speed(self, wind_service):
        """Test handling of extreme wind speeds (logs warning but proceeds)."""
        # Very high wind speed (should log warning but not error)
        result = wind_service.calculate_velocity_pressure(
            wind_speed_mph=250,
            height_ft=20,
            exposure=ExposureCategory.C,
        )

        # Should still calculate (special wind regions may have high speeds)
        assert result.qz_psf > 0
        assert result.qz_psf > 100  # Should be very high pressure


# ============================================================================
# Property-Based Tests (Hypothesis)
# ============================================================================

class TestVelocityPressureProperties:
    """Property-based tests for mathematical correctness."""

    @given(
        wind_speed=st.floats(min_value=85, max_value=200),
        height=st.floats(min_value=0.1, max_value=100),
    )
    def test_determinism(self, wind_service, wind_speed, height):
        """
        Same inputs always produce same outputs (PE requirement).

        This is CRITICAL for PE-stampable software.
        """
        result1 = wind_service.calculate_velocity_pressure(
            wind_speed, height, ExposureCategory.C
        )
        result2 = wind_service.calculate_velocity_pressure(
            wind_speed, height, ExposureCategory.C
        )

        assert result1.qz_psf == result2.qz_psf, \
            "Calculations must be deterministic for PE stamping"

        assert result1.kz == result2.kz, \
            "Kz must be deterministic"

    @given(
        wind_speed=st.floats(min_value=85, max_value=200),
    )
    def test_monotonicity_with_wind_speed(self, wind_service, wind_speed):
        """
        Higher wind speed → higher velocity pressure (monotonicity).

        This is a fundamental engineering property that must hold.
        """
        assume(wind_speed < 199)  # Leave room for wind_speed + 1

        result_lower = wind_service.calculate_velocity_pressure(
            wind_speed, 20, ExposureCategory.C
        )
        result_higher = wind_service.calculate_velocity_pressure(
            wind_speed + 1, 20, ExposureCategory.C
        )

        assert result_higher.qz_psf > result_lower.qz_psf, \
            "qz must increase monotonically with wind speed"

    @given(
        height1=st.floats(min_value=15, max_value=50),
        height2=st.floats(min_value=51, max_value=100),
    )
    def test_monotonicity_with_height(self, wind_service, height1, height2):
        """
        Greater height → higher velocity pressure (for most exposures).

        Velocity pressure increases with height due to reduced ground effects.
        """
        result_lower = wind_service.calculate_velocity_pressure(
            100, height1, ExposureCategory.C
        )
        result_higher = wind_service.calculate_velocity_pressure(
            100, height2, ExposureCategory.C
        )

        # Kz increases with height
        assert result_higher.kz >= result_lower.kz, \
            "Kz should increase (or stay same) with height"

        # qz increases with height
        assert result_higher.qz_psf >= result_lower.qz_psf, \
            "qz should increase with height"

    @given(
        wind_speed=st.floats(min_value=85, max_value=200),
        height=st.floats(min_value=15, max_value=100),
    )
    def test_exposure_ordering(self, wind_service, wind_speed, height):
        """
        Verify exposure categories follow expected ordering.

        Exposure D (coastal) > Exposure C (open) > Exposure B (urban)
        """
        result_b = wind_service.calculate_velocity_pressure(
            wind_speed, height, ExposureCategory.B
        )
        result_c = wind_service.calculate_velocity_pressure(
            wind_speed, height, ExposureCategory.C
        )
        result_d = wind_service.calculate_velocity_pressure(
            wind_speed, height, ExposureCategory.D
        )

        # Kz ordering
        assert result_b.kz <= result_c.kz <= result_d.kz, \
            "Kz should follow: B ≤ C ≤ D"

        # qz ordering (same wind speed, so follows Kz)
        assert result_b.qz_psf <= result_c.qz_psf <= result_d.qz_psf, \
            "qz should follow: B ≤ C ≤ D for same wind speed"


# ============================================================================
# Unit Tests - Wind Force
# ============================================================================

class TestWindForce:
    """Test suite for complete wind force calculations."""

    def test_basic_wind_force_calculation(self, wind_service):
        """Test basic wind force on sign."""
        result = wind_service.calculate_wind_force(
            wind_speed_mph=115,
            height_ft=15,
            exposure=ExposureCategory.C,
            tributary_area_ft2=48.0,  # 8 ft × 6 ft sign
            risk_category=RiskCategory.II,
        )

        # Verify result structure
        assert isinstance(result, WindForceResult)
        assert len(result.code_references) >= 4

        # Verify force is reasonable
        assert result.total_wind_force_lbs > 0
        assert result.total_wind_force_lbs < 5000  # Reasonable for small sign

        # Verify design pressure includes gust effect
        assert result.design_pressure_psf > result.qz_psf, \
            "Design pressure should exceed velocity pressure (due to G and Cf)"

    def test_risk_category_importance_factor(self, wind_service):
        """Test that risk category affects wind force through importance factor."""
        result_cat2 = wind_service.calculate_wind_force(
            wind_speed_mph=100,
            height_ft=20,
            exposure=ExposureCategory.C,
            tributary_area_ft2=50.0,
            risk_category=RiskCategory.II,  # Iw = 1.00
        )

        result_cat3 = wind_service.calculate_wind_force(
            wind_speed_mph=100,
            height_ft=20,
            exposure=ExposureCategory.C,
            tributary_area_ft2=50.0,
            risk_category=RiskCategory.III,  # Iw = 1.15
        )

        # Cat III should have 15% higher force
        expected_ratio = 1.15 / 1.00
        actual_ratio = result_cat3.total_wind_force_lbs / result_cat2.total_wind_force_lbs

        assert abs(actual_ratio - expected_ratio) < 0.01, \
            "Risk Category III should increase force by 15%"

    def test_force_proportional_to_area(self, wind_service):
        """Test that wind force scales linearly with tributary area."""
        result_small = wind_service.calculate_wind_force(
            wind_speed_mph=100,
            height_ft=20,
            exposure=ExposureCategory.C,
            tributary_area_ft2=25.0,
        )

        result_large = wind_service.calculate_wind_force(
            wind_speed_mph=100,
            height_ft=20,
            exposure=ExposureCategory.C,
            tributary_area_ft2=100.0,  # 4x larger
        )

        # Force should scale linearly with area
        expected_ratio = 100.0 / 25.0
        actual_ratio = result_large.total_wind_force_lbs / result_small.total_wind_force_lbs

        assert abs(actual_ratio - expected_ratio) < 0.01, \
            "Wind force should scale linearly with tributary area"


# ============================================================================
# Integration Tests
# ============================================================================

class TestWindServiceIntegration:
    """Integration tests for complete workflows."""

    def test_complete_sign_wind_analysis(self, wind_service):
        """
        Test complete wind analysis workflow for typical sign.

        Scenario:
        - 8 ft × 6 ft sign (48 ft² area)
        - 15 ft above ground
        - Exposure C (open terrain)
        - 115 mph basic wind speed
        - Risk Category II
        """
        # Calculate velocity pressure
        vp_result = wind_service.calculate_velocity_pressure(
            wind_speed_mph=115,
            height_ft=15,
            exposure=ExposureCategory.C,
        )

        # Calculate wind force
        force_result = wind_service.calculate_wind_force(
            wind_speed_mph=115,
            height_ft=15,
            exposure=ExposureCategory.C,
            tributary_area_ft2=48.0,
        )

        # Verify consistency
        assert force_result.qz_psf == vp_result.qz_psf, \
            "Velocity pressure should match between calls"

        # Verify complete code references
        assert any("26.10-1" in ref for ref in force_result.code_references), \
            "Should reference velocity pressure equation"
        assert any("Chapter 29" in ref for ref in force_result.code_references), \
            "Should reference signs chapter"

        # Verify result is reasonable
        expected_force_range = (800, 1600)  # Reasonable for this sign
        assert expected_force_range[0] < force_result.total_wind_force_lbs < expected_force_range[1], \
            f"Force {force_result.total_wind_force_lbs:.0f} lbs outside expected range"


# ============================================================================
# Parametrized Tests
# ============================================================================

@pytest.mark.parametrize("exposure,expected_kz", [
    (ExposureCategory.B, 0.57),   # Urban at 30 ft
    (ExposureCategory.C, 0.94),   # Open at 30 ft
    (ExposureCategory.D, 1.12),   # Coastal at 30 ft
])
def test_kz_table_values(wind_service, exposure, expected_kz):
    """
    Verify Kz values match ASCE 7-22 Table 26.10-1.

    Parametrized test for all exposure categories at 30 ft height.
    """
    result = wind_service.calculate_velocity_pressure(
        wind_speed_mph=100,
        height_ft=30,
        exposure=exposure,
    )

    assert abs(result.kz - expected_kz) < 0.01, \
        f"Kz for {exposure.value} at 30 ft should be {expected_kz}"


@pytest.mark.parametrize("height_ft", [15, 20, 30, 40, 50, 60, 80, 100])
def test_kz_increases_with_height(wind_service, height_ft):
    """
    Verify Kz increases monotonically with height.

    Parametrized test across typical height range.
    """
    if height_ft == 15:
        return  # Skip base case

    result_current = wind_service.calculate_velocity_pressure(
        100, height_ft, ExposureCategory.C
    )
    result_previous = wind_service.calculate_velocity_pressure(
        100, height_ft - 5, ExposureCategory.C
    )

    assert result_current.kz >= result_previous.kz, \
        f"Kz should increase from {height_ft-5} ft to {height_ft} ft"
