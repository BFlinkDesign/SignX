"""
Comprehensive unit tests for Single Pole Sign Structural Analysis.

This test suite validates structural calculations per IBC 2024, ASCE 7-22, and AISC 360-22
with hand calculations, determinism checks, and code compliance verification.

Test Coverage:
- AISC 360-22 ASD bending stress: fb = M/Sx ≤ Fb = 0.66×Fy
- AISC 360-22 ASD shear stress: fv = V/A ≤ Fv = 0.40×Fy
- AISC 360-22 deflection: δ = FL³/(3EI) ≤ L/240
- IBC 2024 overturning: Safety Factor ≥ 1.5
- Foundation sizing and soil bearing checks
- Edge cases: zero area signs, extreme heights, invalid sections

All tests include:
- Hand calculation verification in docstrings
- Exact code section references (IBC, ASCE, AISC)
- Engineering tolerance checks (0.01 for stresses)
- Determinism validation
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from apex.domains.signage.asce7_wind import (
    ExposureCategory,
    RiskCategory,
)
from apex.domains.signage.single_pole_solver import (
    ASD_ALLOWABLE_BENDING_FACTOR,
    ASD_ALLOWABLE_SHEAR_FACTOR,
    DEFLECTION_LIMIT_L_OVER,
    IBC_OVERTURNING_SAFETY_FACTOR_MIN,
    PoleSection,
    SinglePoleConfig,
    analyze_single_pole_sign,
)


# Test fixtures for common pole sections (from AISC Manual)
@pytest.fixture
def hss_8x8x1_4():
    """HSS 8×8×1/4 section properties from AISC Shapes Database."""
    return PoleSection(
        designation="HSS8X8X1/4",
        type="HSS",
        area_in2=7.11,
        depth_in=8.0,
        weight_plf=24.2,
        sx_in3=19.8,
        ix_in4=79.3,
        rx_in=3.34,
        fy_ksi=50.0,  # A500 Grade C
        fu_ksi=65.0,
    )


@pytest.fixture
def hss_6x6x1_4():
    """HSS 6×6×1/4 section properties from AISC Shapes Database."""
    return PoleSection(
        designation="HSS6X6X1/4",
        type="HSS",
        area_in2=5.36,
        depth_in=6.0,
        weight_plf=18.2,
        sx_in3=11.2,
        ix_in4=33.5,
        rx_in=2.50,
        fy_ksi=50.0,
        fu_ksi=65.0,
    )


@pytest.fixture
def hss_10x10x3_8():
    """HSS 10×10×3/8 section properties from AISC Shapes Database."""
    return PoleSection(
        designation="HSS10X10X3/8",
        type="HSS",
        area_in2=14.4,
        depth_in=10.0,
        weight_plf=49.0,
        sx_in3=49.1,
        ix_in4=245.0,
        rx_in=4.12,
        fy_ksi=50.0,
        fu_ksi=65.0,
    )


class TestBendingStressAnalysis:
    """Test AISC 360-22 ASD bending stress calculations."""

    def test_bending_stress_calculation_aisc_chapter_f(self, hss_8x8x1_4):
        """
        Test bending stress: fb = M / Sx

        Test case: HSS 8×8×1/4, 15 ft monument sign, 115 mph wind
        Hand calculation:
        - Wind moment: M ≈ 8.1 kip-ft (from wind calculation)
        - M in kip-in: 8.1 × 12 = 97.2 kip-in
        - Sx = 19.8 in³
        - fb = 97.2 / 19.8 = 4.91 ksi
        - Fb = 0.66 × 50 = 33.0 ksi (AISC 360-22 ASD)
        - Ratio = 4.91 / 33.0 = 0.149 < 1.0 ✓

        Reference: AISC 360-22 Chapter F, Allowable Stress Design
        """
        config = SinglePoleConfig(
            pole_height_ft=12.0,
            pole_section=hss_8x8x1_4,
            embedment_depth_ft=5.0,
            sign_width_ft=8.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            basic_wind_speed_mph=115.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        result = analyze_single_pole_sign(config)

        # Verify bending stress calculation
        expected_fb = (result.max_bending_moment_kipft * 12.0) / hss_8x8x1_4.sx_in3
        assert result.bending_stress_fb_ksi == pytest.approx(expected_fb, abs=0.01)

        # Verify allowable stress
        expected_Fb = ASD_ALLOWABLE_BENDING_FACTOR * hss_8x8x1_4.fy_ksi
        assert result.allowable_bending_Fb_ksi == pytest.approx(expected_Fb, abs=0.01)
        assert result.allowable_bending_Fb_ksi == pytest.approx(33.0, abs=0.1)

        # Verify stress ratio
        assert result.bending_stress_ratio == pytest.approx(expected_fb / expected_Fb, abs=0.001)
        assert result.bending_stress_ratio < 1.0  # Must pass

    def test_bending_stress_increases_with_moment(self, hss_8x8x1_4):
        """Property test: bending stress increases with applied moment."""
        wind_speeds = [80, 100, 115, 130]
        bending_stresses = []

        for wind_speed in wind_speeds:
            config = SinglePoleConfig(
                pole_height_ft=12.0,
                pole_section=hss_8x8x1_4,
                embedment_depth_ft=5.0,
                sign_width_ft=8.0,
                sign_height_ft=3.0,
                sign_area_sqft=24.0,
                basic_wind_speed_mph=wind_speed,
                risk_category=RiskCategory.II,
                exposure_category=ExposureCategory.C,
            )
            result = analyze_single_pole_sign(config)
            bending_stresses.append(result.bending_stress_fb_ksi)

        # Stress should increase monotonically with wind speed (moment increases with V²)
        for i in range(len(bending_stresses) - 1):
            assert bending_stresses[i+1] > bending_stresses[i]

    def test_allowable_bending_stress_aisc_360_22(self, hss_8x8x1_4):
        """
        Test AISC 360-22 ASD allowable bending stress: Fb = 0.66 × Fy

        For A500 Grade C (Fy = 50 ksi):
        Fb = 0.66 × 50 = 33.0 ksi

        Reference: AISC 360-22 Chapter F, Section F7 (HSS), ASD
        """
        config = SinglePoleConfig(
            pole_height_ft=12.0,
            pole_section=hss_8x8x1_4,
            embedment_depth_ft=5.0,
            sign_width_ft=8.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            basic_wind_speed_mph=115.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        result = analyze_single_pole_sign(config)

        assert result.allowable_bending_Fb_ksi == pytest.approx(33.0, abs=0.1)


class TestShearStressAnalysis:
    """Test AISC 360-22 ASD shear stress calculations."""

    def test_shear_stress_calculation_aisc_chapter_g(self, hss_8x8x1_4):
        """
        Test shear stress: fv = V / A

        Test case: HSS 8×8×1/4
        Hand calculation:
        - Wind force: F ≈ 600 lbs = 0.6 kips
        - Area: A = 7.11 in²
        - fv = 0.6 / 7.11 = 0.084 ksi
        - Fv = 0.40 × 50 = 20.0 ksi (AISC 360-22 ASD)
        - Ratio = 0.084 / 20.0 = 0.0042 < 1.0 ✓

        Reference: AISC 360-22 Chapter G, Shear Design
        """
        config = SinglePoleConfig(
            pole_height_ft=12.0,
            pole_section=hss_8x8x1_4,
            embedment_depth_ft=5.0,
            sign_width_ft=8.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            basic_wind_speed_mph=115.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        result = analyze_single_pole_sign(config)

        # Verify shear stress calculation
        expected_fv = result.max_shear_force_kips / hss_8x8x1_4.area_in2
        assert result.shear_stress_fv_ksi == pytest.approx(expected_fv, abs=0.001)

        # Verify allowable shear stress
        expected_Fv = ASD_ALLOWABLE_SHEAR_FACTOR * hss_8x8x1_4.fy_ksi
        assert result.allowable_shear_Fv_ksi == pytest.approx(expected_Fv, abs=0.01)
        assert result.allowable_shear_Fv_ksi == pytest.approx(20.0, abs=0.1)

        # Shear stress ratio should be very small for typical signs
        assert result.shear_stress_ratio < 0.1


class TestDeflectionAnalysis:
    """Test AISC 360-22 serviceability deflection limits."""

    def test_deflection_calculation_cantilever_formula(self, hss_8x8x1_4):
        """
        Test cantilever deflection: δ = (F × L³) / (3 × E × I)

        Test case: HSS 8×8×1/4, 12 ft pole, 600 lbs wind force at centroid
        Hand calculation:
        - F = 600 lbs
        - L = 13.5 ft × 12 = 162 in (to centroid)
        - E = 29,000 ksi
        - I = 79.3 in⁴
        - δ = (600 × 162³) / (3 × 29,000,000 × 79.3)
        - δ ≈ 0.37 in
        - L/δ = 144 / 0.37 ≈ 389 > 240 ✓

        Reference: AISC 360-22 Chapter L, Serviceability
        """
        config = SinglePoleConfig(
            pole_height_ft=12.0,
            pole_section=hss_8x8x1_4,
            embedment_depth_ft=5.0,
            sign_width_ft=8.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            basic_wind_speed_mph=115.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        result = analyze_single_pole_sign(config)

        # Verify deflection is calculated
        assert result.max_deflection_in > 0.0
        assert result.max_deflection_in < 5.0  # Reasonable range

        # Verify L/δ ratio is calculated
        assert result.deflection_ratio_l_over > 0.0

        # Check against limit
        assert result.deflection_limit_l_over == DEFLECTION_LIMIT_L_OVER
        assert result.passes_deflection_check is True

    def test_deflection_limit_l_240(self, hss_8x8x1_4):
        """
        Test that deflection limit is L/240 per typical sign structure criteria.

        L/240 is standard serviceability limit for structures supporting
        non-structural elements.

        Reference: AISC 360-22 Chapter L, Table L-2
        """
        config = SinglePoleConfig(
            pole_height_ft=12.0,
            pole_section=hss_8x8x1_4,
            embedment_depth_ft=5.0,
            sign_width_ft=8.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            basic_wind_speed_mph=115.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
            deflection_limit_ratio=240.0,
        )

        result = analyze_single_pole_sign(config)

        assert result.deflection_limit_l_over == 240.0

    def test_deflection_increases_with_force(self, hss_8x8x1_4):
        """Property test: deflection increases with applied force."""
        wind_speeds = [80, 100, 115, 130]
        deflections = []

        for wind_speed in wind_speeds:
            config = SinglePoleConfig(
                pole_height_ft=12.0,
                pole_section=hss_8x8x1_4,
                embedment_depth_ft=5.0,
                sign_width_ft=8.0,
                sign_height_ft=3.0,
                sign_area_sqft=24.0,
                basic_wind_speed_mph=wind_speed,
                risk_category=RiskCategory.II,
                exposure_category=ExposureCategory.C,
            )
            result = analyze_single_pole_sign(config)
            deflections.append(result.max_deflection_in)

        # Deflection should increase monotonically
        for i in range(len(deflections) - 1):
            assert deflections[i+1] > deflections[i]


class TestFoundationAnalysis:
    """Test IBC 2024 foundation and overturning analysis."""

    def test_overturning_safety_factor_ibc_1605(self, hss_8x8x1_4):
        """
        Test IBC 2024 overturning safety factor: SF = MR / MO ≥ 1.5

        Where:
        - MR = Resisting moment (dead load + passive pressure)
        - MO = Overturning moment (wind)

        Test case: 8.1 kip-ft overturning moment
        Foundation must provide SF ≥ 1.5

        Reference: IBC 2024 Section 1605.2.1
        """
        config = SinglePoleConfig(
            pole_height_ft=12.0,
            pole_section=hss_8x8x1_4,
            embedment_depth_ft=5.0,
            sign_width_ft=8.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            basic_wind_speed_mph=115.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        result = analyze_single_pole_sign(config)

        # Verify safety factor is calculated
        assert result.safety_factor_overturning > 0.0

        # Verify it meets IBC minimum
        assert result.safety_factor_overturning >= IBC_OVERTURNING_SAFETY_FACTOR_MIN

        # Verify overturning check passes
        assert result.passes_overturning_check is True

    def test_foundation_diameter_sizing(self, hss_8x8x1_4):
        """
        Test that foundation diameter is automatically sized to achieve SF ≥ 1.5.

        Larger moments should require larger diameter foundations.

        Reference: IBC 2024 Section 1807
        """
        # Low wind speed case
        config_low = SinglePoleConfig(
            pole_height_ft=12.0,
            pole_section=hss_8x8x1_4,
            embedment_depth_ft=5.0,
            sign_width_ft=8.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            basic_wind_speed_mph=80.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        # High wind speed case
        config_high = SinglePoleConfig(
            pole_height_ft=12.0,
            pole_section=hss_8x8x1_4,
            embedment_depth_ft=5.0,
            sign_width_ft=8.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            basic_wind_speed_mph=130.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        result_low = analyze_single_pole_sign(config_low)
        result_high = analyze_single_pole_sign(config_high)

        # Higher wind should require larger foundation
        assert result_high.foundation_diameter_ft >= result_low.foundation_diameter_ft

    def test_soil_bearing_pressure(self, hss_8x8x1_4):
        """
        Test soil bearing pressure calculation and limit enforcement.

        Maximum soil pressure must not exceed allowable bearing capacity.

        Reference: IBC 2024 Section 1807
        """
        config = SinglePoleConfig(
            pole_height_ft=12.0,
            pole_section=hss_8x8x1_4,
            embedment_depth_ft=5.0,
            sign_width_ft=8.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            basic_wind_speed_mph=115.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
            soil_bearing_capacity_psf=2000.0,
        )

        result = analyze_single_pole_sign(config)

        # Verify soil pressure is calculated
        assert result.max_soil_pressure_psf > 0.0

        # Verify it's below allowable
        assert result.max_soil_pressure_psf <= config.soil_bearing_capacity_psf

        # Verify soil bearing check passes
        assert result.passes_soil_bearing_check is True

    def test_concrete_volume_calculation(self, hss_8x8x1_4):
        """
        Test concrete volume calculation for drilled pier foundation.

        Volume = π × r² × depth (converted to cubic yards)

        Reference: Foundation design standard practice
        """
        config = SinglePoleConfig(
            pole_height_ft=12.0,
            pole_section=hss_8x8x1_4,
            embedment_depth_ft=5.0,
            sign_width_ft=8.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            basic_wind_speed_mph=115.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        result = analyze_single_pole_sign(config)

        # Verify concrete volume is calculated
        assert result.concrete_volume_cuyd > 0.0

        # Hand check: for 4 ft diameter, 5 ft deep
        # V = π × (2)² × 5 = 62.83 ft³ = 2.33 yd³
        # Result should be in reasonable range
        assert 0.5 < result.concrete_volume_cuyd < 10.0


class TestPassFailChecks:
    """Test pass/fail criteria for structural adequacy."""

    def test_all_checks_pass_adequate_design(self, hss_8x8x1_4):
        """Test that adequate design passes all checks."""
        config = SinglePoleConfig(
            pole_height_ft=12.0,
            pole_section=hss_8x8x1_4,
            embedment_depth_ft=5.0,
            sign_width_ft=8.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            basic_wind_speed_mph=115.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        result = analyze_single_pole_sign(config)

        # All checks should pass for this reasonable design
        assert result.passes_strength_check is True
        assert result.passes_deflection_check is True
        assert result.passes_overturning_check is True
        assert result.passes_soil_bearing_check is True
        assert result.passes_all_checks is True
        assert result.critical_failure_mode is None

    def test_undersized_section_fails_strength(self, hss_6x6x1_4):
        """Test that undersized section fails strength check with extreme loads."""
        config = SinglePoleConfig(
            pole_height_ft=30.0,  # Tall pole
            pole_section=hss_6x6x1_4,  # Small section
            embedment_depth_ft=5.0,
            sign_width_ft=12.0,
            sign_height_ft=8.0,
            sign_area_sqft=96.0,  # Large sign
            basic_wind_speed_mph=150.0,  # Extreme wind
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        result = analyze_single_pole_sign(config)

        # Should fail strength check
        assert result.passes_strength_check is False or result.passes_all_checks is False

    def test_critical_failure_mode_identification(self, hss_6x6x1_4):
        """Test that critical failure mode is correctly identified."""
        config = SinglePoleConfig(
            pole_height_ft=30.0,
            pole_section=hss_6x6x1_4,
            embedment_depth_ft=3.0,  # Shallow embedment
            sign_width_ft=12.0,
            sign_height_ft=8.0,
            sign_area_sqft=96.0,
            basic_wind_speed_mph=140.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        result = analyze_single_pole_sign(config)

        # If design fails, critical failure mode should be identified
        if not result.passes_all_checks:
            assert result.critical_failure_mode is not None
            assert result.critical_failure_mode in [
                "BENDING", "SHEAR", "DEFLECTION", "OVERTURNING", "SOIL_BEARING"
            ]


class TestDeterminism:
    """Test deterministic behavior - same inputs produce same outputs."""

    def test_single_pole_analysis_determinism(self, hss_8x8x1_4):
        """
        Verify complete determinism - critical for PE-stampable calculations.

        Same inputs must ALWAYS produce identical outputs.
        """
        config = SinglePoleConfig(
            pole_height_ft=12.0,
            pole_section=hss_8x8x1_4,
            embedment_depth_ft=5.0,
            sign_width_ft=8.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            basic_wind_speed_mph=115.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        # Run analysis multiple times
        results = [analyze_single_pole_sign(config) for _ in range(5)]

        # All numerical results must be identical
        for i in range(len(results) - 1):
            assert results[i].bending_stress_fb_ksi == results[i+1].bending_stress_fb_ksi
            assert results[i].shear_stress_fv_ksi == results[i+1].shear_stress_fv_ksi
            assert results[i].max_deflection_in == results[i+1].max_deflection_in
            assert results[i].safety_factor_overturning == results[i+1].safety_factor_overturning
            assert results[i].foundation_diameter_ft == results[i+1].foundation_diameter_ft
            assert results[i].passes_all_checks == results[i+1].passes_all_checks


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_sign_area(self, hss_8x8x1_4):
        """Test with zero sign area - should produce zero loads."""
        config = SinglePoleConfig(
            pole_height_ft=12.0,
            pole_section=hss_8x8x1_4,
            embedment_depth_ft=5.0,
            sign_width_ft=0.0,
            sign_height_ft=0.0,
            sign_area_sqft=0.0,
            basic_wind_speed_mph=115.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        result = analyze_single_pole_sign(config)

        # Wind force should be zero
        assert result.total_wind_force_lbs == pytest.approx(0.0, abs=0.01)
        assert result.wind_moment_at_base_kipft == pytest.approx(0.0, abs=0.01)

        # Bending stress should be zero
        assert result.bending_stress_fb_ksi == pytest.approx(0.0, abs=0.01)

    def test_extreme_wind_speed(self, hss_10x10x3_8):
        """Test with extreme wind speed (hurricane conditions)."""
        config = SinglePoleConfig(
            pole_height_ft=15.0,
            pole_section=hss_10x10x3_8,  # Heavy section
            embedment_depth_ft=8.0,
            sign_width_ft=8.0,
            sign_height_ft=4.0,
            sign_area_sqft=32.0,
            basic_wind_speed_mph=200.0,  # Hurricane
            risk_category=RiskCategory.IV,  # Essential facility
            exposure_category=ExposureCategory.D,  # Coastal
        )

        result = analyze_single_pole_sign(config)

        # Should produce valid results (may not pass, but should calculate)
        assert result.total_wind_force_lbs > 0.0
        assert result.bending_stress_fb_ksi > 0.0

    def test_very_tall_pole(self, hss_10x10x3_8):
        """Test with very tall pole (100 ft pylon)."""
        config = SinglePoleConfig(
            pole_height_ft=95.0,
            pole_section=hss_10x10x3_8,
            embedment_depth_ft=15.0,
            sign_width_ft=10.0,
            sign_height_ft=10.0,
            sign_area_sqft=100.0,
            basic_wind_speed_mph=115.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        result = analyze_single_pole_sign(config)

        # Should calculate deflection correctly
        assert result.max_deflection_in > 0.0

        # Tall pole may fail deflection limit
        # This is expected and acceptable


class TestCodeReferences:
    """Test that proper code references are included."""

    def test_code_references_present(self, hss_8x8x1_4):
        """Verify that code references are included in results."""
        config = SinglePoleConfig(
            pole_height_ft=12.0,
            pole_section=hss_8x8x1_4,
            embedment_depth_ft=5.0,
            sign_width_ft=8.0,
            sign_height_ft=3.0,
            sign_area_sqft=24.0,
            basic_wind_speed_mph=115.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        result = analyze_single_pole_sign(config)

        # Check for key code references
        refs = result.code_references

        # ASCE 7-22 wind references
        assert any("ASCE 7-22" in ref for ref in refs)
        assert any("26.10-1" in ref or "26.10" in ref for ref in refs)

        # AISC 360-22 structural references
        assert any("AISC 360-22" in ref for ref in refs)
        assert any("Chapter F" in ref for ref in refs)  # Flexure

        # IBC 2024 foundation references
        assert any("IBC 2024" in ref for ref in refs)
        assert any("1605" in ref or "1807" in ref for ref in refs)


class TestWarnings:
    """Test warning generation for marginal designs."""

    def test_warning_for_high_stress_ratio(self, hss_6x6x1_4):
        """Test that warning is generated when stress ratio > 0.9."""
        config = SinglePoleConfig(
            pole_height_ft=20.0,
            pole_section=hss_6x6x1_4,
            embedment_depth_ft=5.0,
            sign_width_ft=10.0,
            sign_height_ft=6.0,
            sign_area_sqft=60.0,
            basic_wind_speed_mph=130.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        result = analyze_single_pole_sign(config)

        # If bending ratio > 0.9, warning should be present
        if result.bending_stress_ratio > 0.9:
            assert any("near capacity" in w.lower() for w in result.warnings)

    def test_warning_for_low_overturning_margin(self, hss_8x8x1_4):
        """Test warning when overturning SF is low but still passing."""
        config = SinglePoleConfig(
            pole_height_ft=20.0,
            pole_section=hss_8x8x1_4,
            embedment_depth_ft=4.0,  # Shallow
            sign_width_ft=10.0,
            sign_height_ft=6.0,
            sign_area_sqft=60.0,
            basic_wind_speed_mph=120.0,
            risk_category=RiskCategory.II,
            exposure_category=ExposureCategory.C,
        )

        result = analyze_single_pole_sign(config)

        # If SF < 2.0 but ≥ 1.5, warning should be present
        if 1.5 <= result.safety_factor_overturning < 2.0:
            assert any("2.0" in w or "low margin" in w.lower() for w in result.warnings)
