"""Unit tests for cantilever sign solver."""

import math
import pytest
from services.api.src.apex.domains.signage.cantilever_solver import (
    CantileverConfig,
    CantileverLoads,
    CantileverType,
    ConnectionType,
    analyze_cantilever_sign,
    optimize_cantilever_design,
    calculate_cantilever_foundation_loads,
)


class TestCantileverConfig:
    """Tests for CantileverConfig validation."""
    
    def test_valid_config(self):
        """Test creation of valid cantilever configuration."""
        config = CantileverConfig(
            type=CantileverType.SINGLE,
            arm_length_ft=15.0,
            arm_angle_deg=0.0,
            arm_section="HSS8x8x1/2",
            connection_type=ConnectionType.BOLTED_FLANGE,
            num_arms=1,
        )
        assert config.arm_length_ft == 15.0
        assert config.type == CantileverType.SINGLE
    
    def test_invalid_arm_length(self):
        """Test that invalid arm lengths are rejected."""
        with pytest.raises(ValueError, match="Arm length must be positive"):
            CantileverConfig(
                type=CantileverType.SINGLE,
                arm_length_ft=-5.0,
                arm_angle_deg=0.0,
                arm_section="HSS8x8x1/2",
                connection_type=ConnectionType.BOLTED_FLANGE,
            )
        
        with pytest.raises(ValueError, match="exceeds practical limit"):
            CantileverConfig(
                type=CantileverType.SINGLE,
                arm_length_ft=35.0,  # Too long
                arm_angle_deg=0.0,
                arm_section="HSS8x8x1/2",
                connection_type=ConnectionType.BOLTED_FLANGE,
            )
    
    def test_invalid_arm_angle(self):
        """Test that excessive arm angles are rejected."""
        with pytest.raises(ValueError, match="exceeds typical range"):
            CantileverConfig(
                type=CantileverType.SINGLE,
                arm_length_ft=15.0,
                arm_angle_deg=20.0,  # Too steep
                arm_section="HSS8x8x1/2",
                connection_type=ConnectionType.BOLTED_FLANGE,
            )


class TestCantileverAnalysis:
    """Tests for cantilever analysis calculations."""
    
    def test_basic_analysis(self):
        """Test basic cantilever analysis with typical values."""
        config = CantileverConfig(
            type=CantileverType.SINGLE,
            arm_length_ft=15.0,
            arm_angle_deg=0.0,
            arm_section="HSS8x8x1/2",
            connection_type=ConnectionType.BOLTED_FLANGE,
        )
        
        loads = CantileverLoads(
            sign_weight_lb=500.0,
            sign_area_ft2=48.0,
            wind_pressure_psf=35.0,
            ice_thickness_in=0.0,
            eccentricity_ft=0.0,
        )
        
        result = analyze_cantilever_sign(
            config=config,
            loads=loads,
            pole_height_ft=20.0,
            include_fatigue=False,
        )
        
        # Check that moments are calculated
        assert result.moment_x_kipft > 0  # Wind moment
        assert result.moment_y_kipft > 0  # Dead load moment
        assert result.total_moment_kipft > 0
        
        # Check shears
        assert result.shear_x_kip == pytest.approx(loads.sign_area_ft2 * loads.wind_pressure_psf / 1000.0)
        assert result.axial_kip == pytest.approx(loads.sign_weight_lb / 1000.0)
        
        # Check stress ratios
        assert 0 < result.arm_stress_ratio < 2.0  # Should be reasonable
        assert 0 < result.connection_ratio < 2.0
        
        # Check deflection
        assert result.arm_deflection_in > 0
        assert result.deflection_ratio > 0
    
    def test_eccentric_loading(self):
        """Test cantilever with eccentric loading (torsion)."""
        config = CantileverConfig(
            type=CantileverType.SINGLE,
            arm_length_ft=15.0,
            arm_angle_deg=0.0,
            arm_section="HSS10x10x1/2",
            connection_type=ConnectionType.WELDED,
        )
        
        loads = CantileverLoads(
            sign_weight_lb=500.0,
            sign_area_ft2=48.0,
            wind_pressure_psf=35.0,
            ice_thickness_in=0.0,
            eccentricity_ft=3.0,  # 3ft offset
        )
        
        result = analyze_cantilever_sign(
            config=config,
            loads=loads,
            pole_height_ft=20.0,
        )
        
        # Should have torsional moment
        assert result.moment_z_kipft > 0
        assert "3.0ft eccentricity" in " ".join(result.assumptions)
    
    def test_ice_loading(self):
        """Test cantilever with ice accumulation."""
        config = CantileverConfig(
            type=CantileverType.SINGLE,
            arm_length_ft=10.0,
            arm_angle_deg=0.0,
            arm_section="HSS8x8x1/2",
            connection_type=ConnectionType.BOLTED_FLANGE,
        )
        
        loads_no_ice = CantileverLoads(
            sign_weight_lb=500.0,
            sign_area_ft2=48.0,
            wind_pressure_psf=35.0,
            ice_thickness_in=0.0,
            eccentricity_ft=0.0,
        )
        
        loads_with_ice = CantileverLoads(
            sign_weight_lb=500.0,
            sign_area_ft2=48.0,
            wind_pressure_psf=35.0,
            ice_thickness_in=1.0,  # 1 inch ice
            eccentricity_ft=0.0,
        )
        
        result_no_ice = analyze_cantilever_sign(config, loads_no_ice, 20.0)
        result_with_ice = analyze_cantilever_sign(config, loads_with_ice, 20.0)
        
        # Ice should increase dead load moment
        assert result_with_ice.moment_y_kipft > result_no_ice.moment_y_kipft
        assert result_with_ice.axial_kip > result_no_ice.axial_kip
    
    def test_fatigue_analysis(self):
        """Test fatigue analysis for cantilever."""
        config = CantileverConfig(
            type=CantileverType.SINGLE,
            arm_length_ft=20.0,
            arm_angle_deg=0.0,
            arm_section="HSS10x10x1/2",
            connection_type=ConnectionType.BOLTED_FLANGE,
        )
        
        loads = CantileverLoads(
            sign_weight_lb=800.0,
            sign_area_ft2=64.0,
            wind_pressure_psf=40.0,
            ice_thickness_in=0.0,
            eccentricity_ft=0.0,
        )
        
        result = analyze_cantilever_sign(
            config=config,
            loads=loads,
            pole_height_ft=25.0,
            include_fatigue=True,
            wind_cycles_per_year=500_000,
            design_life_years=50,
        )
        
        # Should have fatigue calculations
        assert result.fatigue_cycles == 500_000 * 50
        assert 0 < result.fatigue_factor <= 1.0
        assert "Fatigue assessed" in " ".join(result.assumptions)


class TestCantileverOptimization:
    """Tests for cantilever design optimization."""
    
    def test_optimize_design(self):
        """Test optimization finds feasible design."""
        loads = CantileverLoads(
            sign_weight_lb=500.0,
            sign_area_ft2=48.0,
            wind_pressure_psf=35.0,
            ice_thickness_in=0.0,
            eccentricity_ft=0.0,
        )
        
        config, result = optimize_cantilever_design(
            loads=loads,
            pole_height_ft=20.0,
            max_arm_length_ft=20.0,
            min_arm_length_ft=8.0,
            target_stress_ratio=0.9,
        )
        
        # Should find a feasible design
        assert config is not None
        assert result is not None
        
        # Design should meet constraints
        assert 8.0 <= config.arm_length_ft <= 20.0
        assert result.arm_stress_ratio <= 0.9
        assert result.connection_ratio <= 1.0
        assert result.fatigue_factor >= 0.5
    
    def test_optimize_no_feasible(self):
        """Test optimization with infeasible constraints."""
        loads = CantileverLoads(
            sign_weight_lb=5000.0,  # Very heavy
            sign_area_ft2=200.0,    # Very large
            wind_pressure_psf=50.0,  # High wind
            ice_thickness_in=2.0,
            eccentricity_ft=5.0,
        )
        
        with pytest.raises(ValueError, match="No feasible cantilever design"):
            optimize_cantilever_design(
                loads=loads,
                pole_height_ft=30.0,
                max_arm_length_ft=10.0,  # Too short for loads
                min_arm_length_ft=5.0,
                target_stress_ratio=0.5,  # Very conservative
            )


class TestFoundationLoads:
    """Tests for foundation load calculations."""
    
    def test_foundation_loads(self):
        """Test calculation of foundation loads from cantilever analysis."""
        config = CantileverConfig(
            type=CantileverType.SINGLE,
            arm_length_ft=15.0,
            arm_angle_deg=0.0,
            arm_section="HSS8x8x1/2",
            connection_type=ConnectionType.BOLTED_FLANGE,
        )
        
        loads = CantileverLoads(
            sign_weight_lb=500.0,
            sign_area_ft2=48.0,
            wind_pressure_psf=35.0,
            ice_thickness_in=0.0,
            eccentricity_ft=2.0,
        )
        
        result = analyze_cantilever_sign(config, loads, 20.0)
        foundation_loads = calculate_cantilever_foundation_loads(result)
        
        # Should have foundation design loads
        assert "moment_kipft" in foundation_loads
        assert "shear_kip" in foundation_loads
        assert "axial_kip" in foundation_loads
        assert "torsion_kipft" in foundation_loads
        
        # With overstrength factor
        foundation_loads_os = calculate_cantilever_foundation_loads(
            result,
            include_overstrength=True,
            overstrength_factor=1.1,
        )
        
        # Overstrength should increase moment and shear
        assert foundation_loads_os["moment_kipft"] > foundation_loads["moment_kipft"]
        assert foundation_loads_os["shear_kip"] > foundation_loads["shear_kip"]
        # But not axial (dead load)
        assert foundation_loads_os["axial_kip"] == foundation_loads["axial_kip"]


class TestDeterminism:
    """Tests to ensure calculations are deterministic."""
    
    def test_deterministic_results(self):
        """Test that same inputs produce same outputs."""
        config = CantileverConfig(
            type=CantileverType.DOUBLE,
            arm_length_ft=12.5,
            arm_angle_deg=2.5,
            arm_section="HSS8x8x3/8",
            connection_type=ConnectionType.BOLTED_FLANGE,
            num_arms=2,
            arm_spacing_ft=4.0,
        )
        
        loads = CantileverLoads(
            sign_weight_lb=750.0,
            sign_area_ft2=56.0,
            wind_pressure_psf=38.5,
            ice_thickness_in=0.75,
            eccentricity_ft=1.5,
        )
        
        # Run analysis multiple times
        results = []
        for _ in range(5):
            result = analyze_cantilever_sign(
                config=config,
                loads=loads,
                pole_height_ft=22.5,
                include_fatigue=True,
                wind_cycles_per_year=450_000,
                design_life_years=45,
            )
            results.append(result)
        
        # All results should be identical
        for i in range(1, 5):
            assert results[i].moment_x_kipft == results[0].moment_x_kipft
            assert results[i].moment_y_kipft == results[0].moment_y_kipft
            assert results[i].moment_z_kipft == results[0].moment_z_kipft
            assert results[i].arm_deflection_in == results[0].arm_deflection_in
            assert results[i].arm_stress_ratio == results[0].arm_stress_ratio
            assert results[i].fatigue_factor == results[0].fatigue_factor


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_minimum_cantilever(self):
        """Test minimum practical cantilever configuration."""
        config = CantileverConfig(
            type=CantileverType.SINGLE,
            arm_length_ft=1.0,  # Very short
            arm_angle_deg=0.0,
            arm_section="HSS6x6x3/8",
            connection_type=ConnectionType.WELDED,
        )
        
        loads = CantileverLoads(
            sign_weight_lb=50.0,  # Light sign
            sign_area_ft2=4.0,    # Small area
            wind_pressure_psf=20.0,
            ice_thickness_in=0.0,
            eccentricity_ft=0.0,
        )
        
        result = analyze_cantilever_sign(config, loads, 10.0)
        
        # Should still calculate without errors
        assert result.moment_x_kipft >= 0
        assert result.arm_deflection_in >= 0
    
    def test_angled_cantilever(self):
        """Test cantilever with upward angle."""
        config_horizontal = CantileverConfig(
            type=CantileverType.SINGLE,
            arm_length_ft=15.0,
            arm_angle_deg=0.0,  # Horizontal
            arm_section="HSS8x8x1/2",
            connection_type=ConnectionType.BOLTED_FLANGE,
        )
        
        config_angled = CantileverConfig(
            type=CantileverType.SINGLE,
            arm_length_ft=15.0,
            arm_angle_deg=10.0,  # Upward angle
            arm_section="HSS8x8x1/2",
            connection_type=ConnectionType.BOLTED_FLANGE,
        )
        
        loads = CantileverLoads(
            sign_weight_lb=500.0,
            sign_area_ft2=48.0,
            wind_pressure_psf=35.0,
            ice_thickness_in=0.0,
            eccentricity_ft=0.0,
        )
        
        result_horizontal = analyze_cantilever_sign(config_horizontal, loads, 20.0)
        result_angled = analyze_cantilever_sign(config_angled, loads, 20.0)
        
        # Angled cantilever should have different moment arms
        assert result_angled.moment_x_kipft != result_horizontal.moment_x_kipft
        assert result_angled.moment_y_kipft != result_horizontal.moment_y_kipft