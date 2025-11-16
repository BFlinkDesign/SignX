"""
Comprehensive Test Suite for Concrete & Rebar Service

Demonstrates testing patterns for cost estimation modules:
- Unit tests for development lengths
- Volume calculations with validation
- Rebar schedule generation
- Material quantity calculations
- Code compliance verification

Author: Claude Code
Date: 2025-11-02
"""

import pytest
from hypothesis import given, strategies as st

from apex.domains.signage.services import (
    ConcreteRebarService,
    RebarSize,
    ConcreteGrade,
    FoundationType,
    RebarScheduleInput,
)
from apex.domains.signage.exceptions import ValidationError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def rebar_service():
    """Create concrete/rebar service instance for testing."""
    return ConcreteRebarService(code_version="ACI318-19-TEST")


@pytest.fixture
def typical_direct_burial_input():
    """Typical direct burial foundation input."""
    return RebarScheduleInput(
        foundation_type=FoundationType.DIRECT_BURIAL,
        diameter_ft=3.0,
        depth_ft=6.0,
        fc_ksi=3.0,
        fy_ksi=60.0,
        min_rebar_size=RebarSize.NO5,
        cover_in=3.0,
    )


@pytest.fixture
def typical_spread_footing_input():
    """Typical spread footing input."""
    return RebarScheduleInput(
        foundation_type=FoundationType.SPREAD_FOOTING,
        width_ft=4.0,
        length_ft=4.0,
        thickness_ft=1.5,
        fc_ksi=3.0,
        fy_ksi=60.0,
        min_rebar_size=RebarSize.NO4,
        cover_in=3.0,
    )


# ============================================================================
# Unit Tests - Development Length
# ============================================================================

class TestDevelopmentLength:
    """Test suite for ACI 318-19 development length calculations."""

    def test_aci318_development_length_no4(self, rebar_service):
        """
        Verify development length for #4 bar matches ACI 318-19.

        Reference calculation:
        - #4 bar, db = 0.500"
        - fc' = 3000 psi, fy = 60,000 psi
        - Normal weight concrete, uncoated
        - ld = (fy * ψt * ψe * ψs) / (25 * λ * √fc') * db
        - ld = (60000 * 1.0 * 1.0 * 0.8) / (25 * 1.0 * √3000) * 0.5
        - ld ≈ 17.5" (minimum 12")
        """
        result = rebar_service.calculate_development_length(
            bar_size=RebarSize.NO4,
            fc_ksi=3.0,
            fy_ksi=60.0,
            coated=False,
            top_bar=False,
        )

        # Verify result structure
        assert result.bar_size == RebarSize.NO4
        assert result.db_in == 0.500
        assert result.fc_ksi == 3.0
        assert result.fy_ksi == 60.0
        assert "ACI318-19" in result.code_ref

        # Verify calculation (within engineering tolerance)
        assert 15.0 <= result.ld_in <= 20.0, \
            f"Development length {result.ld_in}\" outside expected range"

        # Minimum 12" per code
        assert result.ld_in >= 12.0

    def test_development_length_increases_with_bar_size(self, rebar_service):
        """Larger bars require longer development length."""
        ld_no4 = rebar_service.calculate_development_length(
            bar_size=RebarSize.NO4,
            fc_ksi=3.0,
            fy_ksi=60.0,
        )

        ld_no6 = rebar_service.calculate_development_length(
            bar_size=RebarSize.NO6,
            fc_ksi=3.0,
            fy_ksi=60.0,
        )

        ld_no8 = rebar_service.calculate_development_length(
            bar_size=RebarSize.NO8,
            fc_ksi=3.0,
            fy_ksi=60.0,
        )

        assert ld_no4.ld_in < ld_no6.ld_in < ld_no8.ld_in, \
            "Development length must increase with bar size"

    def test_development_length_epoxy_coating_factor(self, rebar_service):
        """Epoxy-coated bars require longer development length."""
        ld_uncoated = rebar_service.calculate_development_length(
            bar_size=RebarSize.NO5,
            fc_ksi=3.0,
            fy_ksi=60.0,
            coated=False,
        )

        ld_coated = rebar_service.calculate_development_length(
            bar_size=RebarSize.NO5,
            fc_ksi=3.0,
            fy_ksi=60.0,
            coated=True,
        )

        # Epoxy coating factor ψe = 1.5
        assert ld_coated.ld_in > ld_uncoated.ld_in, \
            "Coated bars require longer development length"
        assert abs(ld_coated.ld_in / ld_uncoated.ld_in - 1.5) < 0.1, \
            "Coating factor should be ~1.5"

    def test_development_length_top_bar_factor(self, rebar_service):
        """Top bars (>12\" cover below) require longer development length."""
        ld_bottom = rebar_service.calculate_development_length(
            bar_size=RebarSize.NO5,
            fc_ksi=3.0,
            fy_ksi=60.0,
            top_bar=False,
        )

        ld_top = rebar_service.calculate_development_length(
            bar_size=RebarSize.NO5,
            fc_ksi=3.0,
            fy_ksi=60.0,
            top_bar=True,
        )

        # Top bar factor ψt = 1.3
        assert ld_top.ld_in > ld_bottom.ld_in, \
            "Top bars require longer development length"

    def test_development_length_higher_concrete_strength(self, rebar_service):
        """Higher fc' reduces required development length."""
        ld_3ksi = rebar_service.calculate_development_length(
            bar_size=RebarSize.NO5,
            fc_ksi=3.0,
            fy_ksi=60.0,
        )

        ld_4ksi = rebar_service.calculate_development_length(
            bar_size=RebarSize.NO5,
            fc_ksi=4.0,
            fy_ksi=60.0,
        )

        assert ld_4ksi.ld_in < ld_3ksi.ld_in, \
            "Higher fc' should reduce development length"


# ============================================================================
# Unit Tests - Concrete Volume
# ============================================================================

class TestConcreteVolume:
    """Test suite for concrete volume calculations."""

    def test_cylindrical_volume_calculation(self, rebar_service):
        """Verify cylindrical volume: V = π * r² * h."""
        volume = rebar_service.calculate_concrete_volume(
            foundation_type=FoundationType.DIRECT_BURIAL,
            diameter_ft=3.0,
            depth_ft=6.0,
        )

        # Calculate expected volume
        import math
        radius_ft = 3.0 / 2.0
        expected_cf = math.pi * (radius_ft ** 2) * 6.0
        expected_cy = expected_cf / 27.0

        assert abs(volume.volume_cf - expected_cf) < 0.01
        assert abs(volume.volume_cy - expected_cy) < 0.01

    def test_rectangular_volume_calculation(self, rebar_service):
        """Verify rectangular volume: V = l * w * h."""
        volume = rebar_service.calculate_concrete_volume(
            foundation_type=FoundationType.SPREAD_FOOTING,
            width_ft=4.0,
            length_ft=5.0,
            thickness_ft=1.5,
        )

        # Calculate expected volume
        expected_cf = 4.0 * 5.0 * 1.5
        expected_cy = expected_cf / 27.0

        assert abs(volume.volume_cf - expected_cf) < 0.01
        assert abs(volume.volume_cy - expected_cy) < 0.01

    def test_volume_weight_calculation(self, rebar_service):
        """Verify weight calculation (150 pcf for normal weight concrete)."""
        volume = rebar_service.calculate_concrete_volume(
            foundation_type=FoundationType.DIRECT_BURIAL,
            diameter_ft=3.0,
            depth_ft=6.0,
        )

        # Weight = volume_cf * 150 pcf
        expected_weight_lb = volume.volume_cf * 150.0
        expected_weight_ton = expected_weight_lb / 2000.0

        assert abs(volume.weight_ton - expected_weight_ton) < 0.01

    def test_volume_waste_factor(self, rebar_service):
        """Verify waste factor application (default 10%)."""
        volume = rebar_service.calculate_concrete_volume(
            foundation_type=FoundationType.DIRECT_BURIAL,
            diameter_ft=3.0,
            depth_ft=6.0,
            waste_factor=1.10,
        )

        expected_order_cy = volume.volume_cy * 1.10
        assert abs(volume.order_volume_cy - expected_order_cy) < 0.01

    def test_volume_validation_missing_dimensions(self, rebar_service):
        """Test that missing dimensions raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            rebar_service.calculate_concrete_volume(
                foundation_type=FoundationType.DIRECT_BURIAL,
                # Missing diameter_ft and depth_ft
            )

        assert "requires diameter_ft and depth_ft" in str(exc_info.value)


# ============================================================================
# Integration Tests - Rebar Schedule
# ============================================================================

class TestRebarSchedule:
    """Integration tests for complete rebar schedule design."""

    def test_direct_burial_schedule(self, rebar_service, typical_direct_burial_input):
        """Test complete rebar schedule for direct burial foundation."""
        schedule = rebar_service.design_rebar_schedule(typical_direct_burial_input)

        # Verify structure
        assert len(schedule.vertical_bars) >= 1
        assert len(schedule.horizontal_bars) >= 1
        assert schedule.concrete.volume_cy > 0
        assert schedule.development_length_in >= 12.0

        # Verify vertical bars (minimum 6 for drilled pier)
        vertical_bar = schedule.vertical_bars[0]
        assert vertical_bar.quantity >= 6, \
            "ACI 318-19 requires minimum 6 vertical bars for drilled piers"
        assert vertical_bar.size == RebarSize.NO5

        # Verify horizontal bars (spiral)
        horizontal_bar = schedule.horizontal_bars[0]
        assert horizontal_bar.spacing_in is not None
        assert 3.0 <= horizontal_bar.spacing_in <= 6.0, \
            "Spiral spacing should be 3-6 inches"

        # Verify material quantities
        assert schedule.total_rebar_weight_lb > 0
        assert schedule.total_rebar_weight_ton > 0
        assert schedule.concrete_cy_to_order > schedule.concrete.volume_cy, \
            "Order quantity should include waste"

        # Verify code references
        assert len(schedule.code_references) >= 3
        assert any("ACI318-19" in ref for ref in schedule.code_references)

    def test_spread_footing_schedule(self, rebar_service, typical_spread_footing_input):
        """Test complete rebar schedule for spread footing."""
        schedule = rebar_service.design_rebar_schedule(typical_spread_footing_input)

        # Verify structure
        assert len(schedule.vertical_bars) == 0, \
            "Spread footings don't have vertical bars"
        assert len(schedule.horizontal_bars) == 2, \
            "Spread footings have 2 layers of horizontal bars (both directions)"

        # Verify minimum steel ratio
        # As,min = 0.0018 * gross area
        gross_area_in2 = (4.0 * 12) * (1.5 * 12)
        total_bar_area = sum(
            bar.quantity * 0.20  # #4 bar area
            for bar in schedule.horizontal_bars
        )
        steel_ratio = total_bar_area / gross_area_in2
        assert steel_ratio >= 0.0018, \
            "Must meet minimum steel ratio of 0.0018"

    def test_material_quantities_for_estimating(self, rebar_service, typical_direct_burial_input):
        """Verify material quantities are suitable for cost estimation."""
        schedule = rebar_service.design_rebar_schedule(typical_direct_burial_input)

        # Verify all quantities are positive
        assert schedule.concrete_cy_to_order > 0
        assert schedule.rebar_ton_to_order > 0

        # Verify waste factors applied
        assert schedule.concrete_cy_to_order >= schedule.concrete.volume_cy
        assert schedule.rebar_ton_to_order >= schedule.total_rebar_weight_ton

        # Verify rebar waste is reasonable (5%)
        rebar_waste_factor = schedule.rebar_ton_to_order / schedule.total_rebar_weight_ton
        assert 1.04 <= rebar_waste_factor <= 1.06

    def test_rebar_weight_calculation(self, rebar_service, typical_direct_burial_input):
        """Verify rebar weight calculation accuracy."""
        schedule = rebar_service.design_rebar_schedule(typical_direct_burial_input)

        # Manually calculate total weight
        manual_total_lb = 0.0
        for bar in schedule.vertical_bars + schedule.horizontal_bars:
            # From REBAR_PROPERTIES
            if bar.size == RebarSize.NO3:
                weight_plf = 0.376
            elif bar.size == RebarSize.NO4:
                weight_plf = 0.668
            elif bar.size == RebarSize.NO5:
                weight_plf = 1.043
            else:
                continue

            manual_total_lb += bar.quantity * bar.length_ft * weight_plf

        # Should match service calculation
        assert abs(schedule.total_rebar_weight_lb - manual_total_lb) < 1.0


# ============================================================================
# Property-Based Tests (Hypothesis)
# ============================================================================

class TestRebarScheduleProperties:
    """Property-based tests for mathematical correctness."""

    @given(
        diameter=st.floats(min_value=1.0, max_value=5.0),
        depth=st.floats(min_value=3.0, max_value=10.0),
    )
    def test_determinism(self, rebar_service, diameter, depth):
        """Same inputs always produce same outputs (PE requirement)."""
        input_data = RebarScheduleInput(
            foundation_type=FoundationType.DIRECT_BURIAL,
            diameter_ft=diameter,
            depth_ft=depth,
            fc_ksi=3.0,
        )

        result1 = rebar_service.design_rebar_schedule(input_data)
        result2 = rebar_service.design_rebar_schedule(input_data)

        assert result1.total_rebar_weight_lb == result2.total_rebar_weight_lb
        assert result1.concrete_cy_to_order == result2.concrete_cy_to_order

    @given(
        diameter=st.floats(min_value=1.0, max_value=5.0),
    )
    def test_larger_diameter_more_concrete(self, rebar_service, diameter):
        """Larger diameter requires more concrete (monotonicity)."""
        input_small = RebarScheduleInput(
            foundation_type=FoundationType.DIRECT_BURIAL,
            diameter_ft=diameter,
            depth_ft=6.0,
            fc_ksi=3.0,
        )

        input_large = RebarScheduleInput(
            foundation_type=FoundationType.DIRECT_BURIAL,
            diameter_ft=diameter + 0.5,
            depth_ft=6.0,
            fc_ksi=3.0,
        )

        result_small = rebar_service.design_rebar_schedule(input_small)
        result_large = rebar_service.design_rebar_schedule(input_large)

        assert result_large.concrete.volume_cy > result_small.concrete.volume_cy


# ============================================================================
# Parametrized Tests
# ============================================================================

@pytest.mark.parametrize("bar_size,expected_diameter_in", [
    (RebarSize.NO3, 0.375),
    (RebarSize.NO4, 0.500),
    (RebarSize.NO5, 0.625),
    (RebarSize.NO6, 0.750),
    (RebarSize.NO8, 1.000),
])
def test_rebar_properties_database(rebar_service, bar_size, expected_diameter_in):
    """Verify rebar properties match ASTM A615."""
    result = rebar_service.calculate_development_length(
        bar_size=bar_size,
        fc_ksi=3.0,
        fy_ksi=60.0,
    )

    assert result.db_in == expected_diameter_in


@pytest.mark.parametrize("fc_ksi,foundation_type", [
    (2.5, FoundationType.DIRECT_BURIAL),
    (3.0, FoundationType.DIRECT_BURIAL),
    (4.0, FoundationType.DRILLED_PIER),
    (5.0, FoundationType.SPREAD_FOOTING),
])
def test_various_concrete_strengths(rebar_service, fc_ksi, foundation_type):
    """Test service handles various concrete strengths."""
    if foundation_type == FoundationType.SPREAD_FOOTING:
        input_data = RebarScheduleInput(
            foundation_type=foundation_type,
            width_ft=3.0,
            length_ft=3.0,
            thickness_ft=1.0,
            fc_ksi=fc_ksi,
        )
    else:
        input_data = RebarScheduleInput(
            foundation_type=foundation_type,
            diameter_ft=3.0,
            depth_ft=6.0,
            fc_ksi=fc_ksi,
        )

    schedule = rebar_service.design_rebar_schedule(input_data)

    assert schedule.concrete_cy_to_order > 0
    assert schedule.total_rebar_weight_ton > 0
