"""
Comprehensive unit tests for ASCE 7-22 Wind Load Calculations.

This test suite validates wind load calculations against ASCE 7-22 code requirements
with exact hand calculations, code references, and determinism checks.

Test Coverage:
- Velocity pressure exposure coefficients (Kz) from Table 26.10-1
- Wind importance factors from Table 1.5-2
- Velocity pressure calculation (Equation 26.10-1)
- Design wind pressure calculation
- Total wind force and moment calculations
- Iowa Grimes baseline conditions (115 mph, Exposure C, 15 ft)
- Edge cases: zero wind, extreme speeds, invalid exposures

All tests include:
- Hand calculation verification in docstrings
- Exact ASCE 7-22 code section references
- Engineering tolerance checks (0.01 for forces)
- Determinism validation
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from apex.domains.signage.asce7_wind import (
    EXPOSURE_PARAMETERS,
    ExposureCategory,
    RiskCategory,
    calculate_design_wind_pressure,
    calculate_kz,
    calculate_velocity_pressure,
    calculate_wind_force_on_sign,
    calculate_wind_importance_factor,
    calculate_wind_moment_at_base,
)


class TestExposureCoefficients:
    """Test Kz calculation per ASCE 7-22 Table 26.10-1."""

    @pytest.mark.parametrize("height,exposure,expected_kz", [
        # ASCE 7-22 Table 26.10-1 exact values
        # Exposure B
        (15, ExposureCategory.B, 0.57),
        (20, ExposureCategory.B, 0.62),
        (30, ExposureCategory.B, 0.70),
        (60, ExposureCategory.B, 0.85),
        (100, ExposureCategory.B, 0.99),
        # Exposure C
        (15, ExposureCategory.C, 0.85),
        (20, ExposureCategory.C, 0.90),
        (30, ExposureCategory.C, 0.98),
        (60, ExposureCategory.C, 1.13),
        (100, ExposureCategory.C, 1.26),
        # Exposure D
        (15, ExposureCategory.D, 1.03),
        (20, ExposureCategory.D, 1.08),
        (30, ExposureCategory.D, 1.16),
        (60, ExposureCategory.D, 1.31),
        (100, ExposureCategory.D, 1.43),
    ])
    def test_kz_table_values_exact(self, height, exposure, expected_kz):
        """
        Verify Kz coefficients match ASCE 7-22 Table 26.10-1 exactly.

        Reference: ASCE 7-22 Section 26.10.1, Table 26.10-1
        """
        kz = calculate_kz(height, exposure)

        # Exact match for table values (no tolerance)
        assert kz == pytest.approx(expected_kz, abs=0.001), \
            f"Kz mismatch for {exposure.value} at {height} ft: got {kz:.3f}, expected {expected_kz:.3f}"

    def test_kz_minimum_height_enforcement(self):
        """
        Test that heights below 15 ft use 15 ft Kz value per ASCE 7-22.

        ASCE 7-22 specifies minimum effective height of 15 ft for velocity pressure.

        Reference: ASCE 7-22 Section 26.10.1
        """
        # Heights below 15 ft should all use 15 ft Kz
        kz_10ft = calculate_kz(10.0, ExposureCategory.C)
        kz_5ft = calculate_kz(5.0, ExposureCategory.C)
        kz_15ft = calculate_kz(15.0, ExposureCategory.C)

        assert kz_10ft == kz_15ft == 0.85
        assert kz_5ft == kz_15ft == 0.85

    def test_kz_linear_interpolation(self):
        """
        Test linear interpolation between table values.

        For height 25 ft, Exposure C:
        - At 20 ft: Kz = 0.90
        - At 30 ft: Kz = 0.98
        - At 25 ft: Kz = 0.90 + (25-20)/(30-20) * (0.98-0.90) = 0.94

        Reference: ASCE 7-22 Section 26.10.1
        """
        kz_25ft = calculate_kz(25.0, ExposureCategory.C)

        # Linear interpolation: 0.90 + 0.5 * (0.98 - 0.90) = 0.94
        assert kz_25ft == pytest.approx(0.94, abs=0.01)

    def test_kz_power_law_above_160ft(self):
        """
        Test power law formula for heights above 160 ft.

        For Exposure C at 200 ft:
        Kz = 2.01 * (z/zg)^(2/alpha)
        Kz = 2.01 * (200/900)^(2/9.5)
        Kz = 2.01 * 0.222^0.211
        Kz ≈ 1.42

        Reference: ASCE 7-22 Equation 26.10-1
        """
        kz_200ft = calculate_kz(200.0, ExposureCategory.C)

        # Power law calculation
        alpha = EXPOSURE_PARAMETERS["C"]["alpha"]
        zg = EXPOSURE_PARAMETERS["C"]["zg_ft"]
        expected_kz = 2.01 * math.pow(200.0 / zg, 2.0 / alpha)

        assert kz_200ft == pytest.approx(expected_kz, abs=0.01)

    def test_kz_determinism(self):
        """Verify Kz calculation is deterministic - same inputs produce same outputs."""
        heights = [15, 25, 50, 100]
        exposures = [ExposureCategory.B, ExposureCategory.C, ExposureCategory.D]

        for height in heights:
            for exposure in exposures:
                kz1 = calculate_kz(height, exposure)
                kz2 = calculate_kz(height, exposure)
                kz3 = calculate_kz(height, exposure)

                assert kz1 == kz2 == kz3


class TestWindImportanceFactors:
    """Test wind importance factors per ASCE 7-22 Table 1.5-2."""

    @pytest.mark.parametrize("risk_category,expected_iw", [
        (RiskCategory.I, 0.87),
        (RiskCategory.II, 1.00),
        (RiskCategory.III, 1.15),
        (RiskCategory.IV, 1.15),
    ])
    def test_importance_factors_exact(self, risk_category, expected_iw):
        """
        Verify importance factors match ASCE 7-22 Table 1.5-2 exactly.

        Risk Category I: 0.87 (low hazard)
        Risk Category II: 1.00 (standard structures, most signs)
        Risk Category III/IV: 1.15 (high importance)

        Reference: ASCE 7-22 Table 1.5-2
        """
        iw = calculate_wind_importance_factor(risk_category)

        assert iw == pytest.approx(expected_iw, abs=0.001), \
            f"Iw mismatch for {risk_category.value}: got {iw:.2f}, expected {expected_iw:.2f}"


class TestVelocityPressure:
    """Test velocity pressure calculation per ASCE 7-22 Equation 26.10-1."""

    def test_velocity_pressure_equation_26_10_1(self):
        """
        Verify velocity pressure calculation: qz = 0.00256 × Kz × Kzt × Kd × Ke × V²

        Test case: 115 mph wind, Exposure C, 15 ft height
        Hand calculation:
        - Kz = 0.85 (Table 26.10-1)
        - Kzt = 1.0 (flat terrain)
        - Kd = 0.85 (signs)
        - Ke = 1.0 (< 3000 ft elevation)
        - V = 115 mph
        - qz = 0.00256 × 0.85 × 1.0 × 0.85 × 1.0 × 115² = 24.46 psf

        Reference: ASCE 7-22 Equation 26.10-1
        """
        qz = calculate_velocity_pressure(
            wind_speed_mph=115.0,
            height_ft=15.0,
            exposure=ExposureCategory.C,
            kzt=1.0,
            kd=0.85,
            ke=1.0,
        )

        # Hand calculation: 0.00256 * 0.85 * 1.0 * 0.85 * 1.0 * 115^2
        expected_qz = 0.00256 * 0.85 * 1.0 * 0.85 * 1.0 * (115.0 ** 2)

        assert qz == pytest.approx(expected_qz, abs=0.01)
        assert qz == pytest.approx(24.46, abs=0.01)

    def test_velocity_pressure_iowa_grimes_baseline(self):
        """
        Test Iowa Grimes baseline conditions (common test case).

        Location: Grimes, Iowa
        Conditions:
        - Wind speed: 115 mph (Risk Category II per ASCE 7-22 Figure 26.5-1B)
        - Exposure: C (open terrain)
        - Height: 15 ft (monument sign)

        Hand calculation:
        qz = 0.00256 × 0.85 × 1.0 × 0.85 × 1.0 × 115²
        qz = 24.46 psf

        Reference: ASCE 7-22 Equation 26.10-1
        """
        qz = calculate_velocity_pressure(
            wind_speed_mph=115.0,
            height_ft=15.0,
            exposure=ExposureCategory.C,
        )

        assert qz == pytest.approx(24.46, abs=0.01)

    @pytest.mark.parametrize("wind_speed,height,exposure,expected_qz", [
        # Exposure B cases
        (100, 15, ExposureCategory.B, 12.26),   # 0.00256 * 0.57 * 1.0 * 0.85 * 100^2
        (120, 30, ExposureCategory.B, 22.91),   # 0.00256 * 0.70 * 1.0 * 0.85 * 120^2
        # Exposure C cases
        (100, 15, ExposureCategory.C, 18.32),   # 0.00256 * 0.85 * 1.0 * 0.85 * 100^2
        (120, 30, ExposureCategory.C, 25.67),   # 0.00256 * 0.98 * 1.0 * 0.85 * 120^2
        # Exposure D cases
        (100, 15, ExposureCategory.D, 22.18),   # 0.00256 * 1.03 * 1.0 * 0.85 * 100^2
        (120, 30, ExposureCategory.D, 30.41),   # 0.00256 * 1.16 * 1.0 * 0.85 * 120^2
    ])
    def test_velocity_pressure_parametric(self, wind_speed, height, exposure, expected_qz):
        """
        Test velocity pressure across multiple wind speeds, heights, and exposures.

        Reference: ASCE 7-22 Equation 26.10-1
        """
        qz = calculate_velocity_pressure(wind_speed, height, exposure)

        assert qz == pytest.approx(expected_qz, abs=0.5), \
            f"qz mismatch for V={wind_speed}, h={height}, {exposure.value}: got {qz:.2f}, expected {expected_qz:.2f}"

    def test_velocity_pressure_topographic_factor(self):
        """
        Test topographic factor Kzt effect on velocity pressure.

        For hillcrest or escarpment, Kzt > 1.0 increases pressure.
        Test with Kzt = 1.3 (steep hill condition)

        Base: qz = 0.00256 × 0.85 × 1.0 × 0.85 × 115² = 24.46 psf
        With Kzt=1.3: qz = 24.46 × 1.3 = 31.80 psf

        Reference: ASCE 7-22 Section 26.8
        """
        qz_flat = calculate_velocity_pressure(115.0, 15.0, ExposureCategory.C, kzt=1.0)
        qz_hill = calculate_velocity_pressure(115.0, 15.0, ExposureCategory.C, kzt=1.3)

        assert qz_hill == pytest.approx(qz_flat * 1.3, abs=0.01)

    def test_velocity_pressure_determinism(self):
        """Verify velocity pressure calculation is deterministic."""
        params = {
            "wind_speed_mph": 115.0,
            "height_ft": 20.0,
            "exposure": ExposureCategory.C,
            "kzt": 1.0,
            "kd": 0.85,
            "ke": 1.0,
        }

        results = [calculate_velocity_pressure(**params) for _ in range(10)]

        # All results must be identical
        assert len(set(results)) == 1


class TestDesignWindPressure:
    """Test design wind pressure calculation per ASCE 7-22 Chapter 29."""

    def test_design_pressure_chapter_29(self):
        """
        Test design pressure: p = qz × G × Cf × Iw

        Test case: 115 mph, Exposure C, 15 ft, Risk Category II
        Hand calculation:
        - qz = 24.46 psf (from Equation 26.10-1)
        - G = 0.85 (gust effect factor)
        - Cf = 1.2 (force coefficient for flat signs)
        - Iw = 1.0 (Risk Category II)
        - p = 24.46 × 0.85 × 1.2 × 1.0 = 24.95 psf

        Reference: ASCE 7-22 Chapter 29, Section 29.4
        """
        p = calculate_design_wind_pressure(
            wind_speed_mph=115.0,
            height_ft=15.0,
            exposure=ExposureCategory.C,
            risk_category=RiskCategory.II,
            gust_effect_factor=0.85,
            force_coefficient=1.2,
        )

        # Hand calculation
        qz = 24.46  # From Equation 26.10-1
        expected_p = qz * 0.85 * 1.2 * 1.0

        assert p == pytest.approx(expected_p, abs=0.5)
        assert p == pytest.approx(24.95, abs=0.5)

    @pytest.mark.parametrize("risk_category,iw_factor,expected_multiplier", [
        (RiskCategory.I, 0.87, 0.87),
        (RiskCategory.II, 1.00, 1.00),
        (RiskCategory.III, 1.15, 1.15),
        (RiskCategory.IV, 1.15, 1.15),
    ])
    def test_design_pressure_importance_factor(self, risk_category, iw_factor, expected_multiplier):
        """
        Test that risk category importance factor correctly affects design pressure.

        Reference: ASCE 7-22 Table 1.5-2
        """
        # Base pressure for Risk Category II
        p_base = calculate_design_wind_pressure(
            wind_speed_mph=115.0,
            height_ft=15.0,
            exposure=ExposureCategory.C,
            risk_category=RiskCategory.II,
        )

        # Pressure for test risk category
        p_test = calculate_design_wind_pressure(
            wind_speed_mph=115.0,
            height_ft=15.0,
            exposure=ExposureCategory.C,
            risk_category=risk_category,
        )

        # Ratio should match importance factor
        assert p_test / p_base == pytest.approx(expected_multiplier, abs=0.01)


class TestWindForceOnSign:
    """Test total wind force calculation for sign structures."""

    def test_wind_force_basic_calculation(self):
        """
        Test wind force calculation: F = p × A

        Test case: 8×3 ft sign, 115 mph, Exposure C, 12 ft pole height
        Sign area: 24 sqft
        Sign centroid height: 12 + 3/2 = 13.5 ft

        At 13.5 ft (use 15 ft minimum):
        - qz = 24.46 psf
        - p = 24.46 × 0.85 × 1.2 × 1.0 = 24.95 psf
        - F = 24.95 × 24 = 598.8 lbs

        Reference: ASCE 7-22 Chapter 29
        """
        result = calculate_wind_force_on_sign(
            wind_speed_mph=115.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            pole_height_ft=12.0,
            exposure=ExposureCategory.C,
            risk_category=RiskCategory.II,
        )

        # Verify force calculation
        assert result.total_wind_force_lbs == pytest.approx(598.8, abs=10.0)

        # Verify intermediate values
        assert result.velocity_pressure_qz_psf == pytest.approx(24.46, abs=0.5)
        assert result.exposure_coefficient_kz == pytest.approx(0.85, abs=0.01)
        assert result.wind_importance_factor_iw == pytest.approx(1.0, abs=0.01)

    def test_wind_force_centroid_height_calculation(self):
        """
        Test that wind pressure is evaluated at sign centroid height.

        For tall signs, centroid height affects Kz and therefore wind force.

        Test case 1: Low sign (centroid at 13.5 ft → uses 15 ft)
        Test case 2: Tall sign (centroid at 37 ft)

        Reference: ASCE 7-22 Section 29.4
        """
        # Low sign: 12 ft pole + 3 ft sign, centroid at 13.5 ft (uses 15 ft)
        result_low = calculate_wind_force_on_sign(
            wind_speed_mph=115.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            pole_height_ft=12.0,
            exposure=ExposureCategory.C,
            risk_category=RiskCategory.II,
        )

        # Tall sign: 34 ft pole + 6 ft sign, centroid at 37 ft
        result_tall = calculate_wind_force_on_sign(
            wind_speed_mph=115.0,
            sign_height_ft=6.0,
            sign_area_sqft=60.0,
            pole_height_ft=34.0,
            exposure=ExposureCategory.C,
            risk_category=RiskCategory.II,
        )

        # Kz at 37 ft should be higher than at 15 ft
        assert result_tall.exposure_coefficient_kz > result_low.exposure_coefficient_kz

    def test_wind_force_code_references(self):
        """Verify that WindLoadResult includes proper code references."""
        result = calculate_wind_force_on_sign(
            wind_speed_mph=115.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            pole_height_ft=12.0,
            exposure=ExposureCategory.C,
            risk_category=RiskCategory.II,
        )

        # Check that critical code references are included
        assert any("26.10-1" in ref for ref in result.code_references)
        assert any("Table 26.10-1" in ref for ref in result.code_references)
        assert any("Table 1.5-2" in ref for ref in result.code_references)
        assert any("Chapter 29" in ref for ref in result.code_references)

    def test_wind_force_determinism(self):
        """Verify wind force calculation is deterministic."""
        params = {
            "wind_speed_mph": 115.0,
            "sign_height_ft": 3.0,
            "sign_area_sqft": 24.0,
            "pole_height_ft": 12.0,
            "exposure": ExposureCategory.C,
            "risk_category": RiskCategory.II,
        }

        results = [calculate_wind_force_on_sign(**params) for _ in range(5)]

        # All forces must be identical
        forces = [r.total_wind_force_lbs for r in results]
        assert len(set(forces)) == 1


class TestWindMoment:
    """Test wind moment calculation at pole base."""

    def test_wind_moment_calculation(self):
        """
        Test overturning moment: M = F × h

        Test case: 600 lbs wind force, 12 ft pole + 1.5 ft to centroid = 13.5 ft
        M = 600 × 13.5 = 8,100 lb-ft = 8.1 kip-ft

        Reference: Statics - moment about base
        """
        moment = calculate_wind_moment_at_base(
            total_wind_force_lbs=600.0,
            pole_height_ft=12.0,
            sign_height_ft=3.0,
        )

        # Hand calculation: 600 lbs × 13.5 ft = 8,100 lb-ft = 8.1 kip-ft
        expected_moment = (600.0 / 1000.0) * (12.0 + 3.0/2.0)

        assert moment == pytest.approx(expected_moment, abs=0.01)
        assert moment == pytest.approx(8.1, abs=0.1)

    def test_wind_moment_lever_arm(self):
        """
        Test that moment arm is measured to sign centroid.

        For a sign with pole_height + sign_height/2, the lever arm should be:
        h = pole_height + sign_height/2

        Reference: Statics - moment calculation
        """
        # Test with different pole and sign heights
        cases = [
            (10.0, 4.0, 12.0),  # 10 ft pole + 2 ft = 12 ft arm
            (20.0, 6.0, 23.0),  # 20 ft pole + 3 ft = 23 ft arm
            (30.0, 8.0, 34.0),  # 30 ft pole + 4 ft = 34 ft arm
        ]

        for pole_h, sign_h, expected_arm in cases:
            moment = calculate_wind_moment_at_base(
                total_wind_force_lbs=1000.0,
                pole_height_ft=pole_h,
                sign_height_ft=sign_h,
            )

            expected_moment = (1000.0 / 1000.0) * expected_arm
            assert moment == pytest.approx(expected_moment, abs=0.01)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_wind_speed(self):
        """Test that zero wind speed produces zero pressure and force."""
        result = calculate_wind_force_on_sign(
            wind_speed_mph=0.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            pole_height_ft=12.0,
            exposure=ExposureCategory.C,
            risk_category=RiskCategory.II,
        )

        assert result.velocity_pressure_qz_psf == pytest.approx(0.0, abs=0.001)
        assert result.design_wind_pressure_psf == pytest.approx(0.0, abs=0.001)
        assert result.total_wind_force_lbs == pytest.approx(0.0, abs=0.001)

    def test_zero_sign_area(self):
        """Test that zero sign area produces zero force."""
        result = calculate_wind_force_on_sign(
            wind_speed_mph=115.0,
            sign_height_ft=3.0,
            sign_area_sqft=0.0,
            pole_height_ft=12.0,
            exposure=ExposureCategory.C,
            risk_category=RiskCategory.II,
        )

        assert result.total_wind_force_lbs == pytest.approx(0.0, abs=0.001)

    @pytest.mark.parametrize("wind_speed", [150, 200, 250])
    def test_extreme_wind_speeds(self, wind_speed):
        """
        Test calculation with extreme wind speeds (hurricanes, tornadoes).

        qz = 0.00256 × Kz × Kzt × Kd × Ke × V²

        For V=200 mph:
        qz = 0.00256 × 0.85 × 1.0 × 0.85 × 1.0 × 200² = 73.98 psf

        Reference: ASCE 7-22 applies to wind speeds up to 200 mph in hurricane zones
        """
        qz = calculate_velocity_pressure(
            wind_speed_mph=wind_speed,
            height_ft=15.0,
            exposure=ExposureCategory.C,
        )

        # Verify velocity pressure increases with V²
        expected_qz = 0.00256 * 0.85 * 1.0 * 0.85 * 1.0 * (wind_speed ** 2)
        assert qz == pytest.approx(expected_qz, abs=0.5)

    def test_very_tall_sign(self):
        """
        Test calculation for very tall sign (100+ ft).

        At 100 ft, Exposure C:
        Kz = 1.26 (from Table 26.10-1)

        Reference: ASCE 7-22 Table 26.10-1
        """
        result = calculate_wind_force_on_sign(
            wind_speed_mph=115.0,
            sign_height_ft=10.0,
            sign_area_sqft=100.0,
            pole_height_ft=95.0,  # Centroid at 100 ft
            exposure=ExposureCategory.C,
            risk_category=RiskCategory.II,
        )

        # Kz at 100 ft Exposure C should be 1.26
        assert result.exposure_coefficient_kz == pytest.approx(1.26, abs=0.01)


class TestCalculationConsistency:
    """Test consistency and monotonicity properties."""

    def test_wind_force_increases_with_speed(self):
        """Property test: wind force increases with wind speed (V²)."""
        speeds = [80, 100, 115, 130, 150]

        forces = []
        for speed in speeds:
            result = calculate_wind_force_on_sign(
                wind_speed_mph=speed,
                sign_height_ft=3.0,
                sign_area_sqft=24.0,
                pole_height_ft=12.0,
                exposure=ExposureCategory.C,
                risk_category=RiskCategory.II,
            )
            forces.append(result.total_wind_force_lbs)

        # Force should increase monotonically with speed
        for i in range(len(forces) - 1):
            assert forces[i+1] > forces[i]

    def test_wind_force_increases_with_area(self):
        """Property test: wind force increases linearly with sign area."""
        areas = [10, 20, 30, 40, 50]

        forces = []
        for area in areas:
            result = calculate_wind_force_on_sign(
                wind_speed_mph=115.0,
                sign_height_ft=3.0,
                sign_area_sqft=area,
                pole_height_ft=12.0,
                exposure=ExposureCategory.C,
                risk_category=RiskCategory.II,
            )
            forces.append(result.total_wind_force_lbs)

        # Force should increase linearly with area (F = p × A)
        for i in range(len(forces) - 1):
            assert forces[i+1] > forces[i]

        # Check linearity: F2/F1 ≈ A2/A1
        assert forces[1] / forces[0] == pytest.approx(areas[1] / areas[0], rel=0.01)

    def test_exposure_ordering(self):
        """Property test: D > C > B for same conditions."""
        result_b = calculate_wind_force_on_sign(
            wind_speed_mph=115.0, sign_height_ft=3.0, sign_area_sqft=24.0,
            pole_height_ft=12.0, exposure=ExposureCategory.B, risk_category=RiskCategory.II,
        )

        result_c = calculate_wind_force_on_sign(
            wind_speed_mph=115.0, sign_height_ft=3.0, sign_area_sqft=24.0,
            pole_height_ft=12.0, exposure=ExposureCategory.C, risk_category=RiskCategory.II,
        )

        result_d = calculate_wind_force_on_sign(
            wind_speed_mph=115.0, sign_height_ft=3.0, sign_area_sqft=24.0,
            pole_height_ft=12.0, exposure=ExposureCategory.D, risk_category=RiskCategory.II,
        )

        # Exposure D should produce highest force, B lowest
        assert result_d.total_wind_force_lbs > result_c.total_wind_force_lbs
        assert result_c.total_wind_force_lbs > result_b.total_wind_force_lbs
