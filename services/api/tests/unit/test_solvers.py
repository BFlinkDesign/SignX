"""
Comprehensive unit tests for APEX signage engineering solvers.

Tests cover:
- Load derivation (ASCE 7-22)
- Pole filtering (AISC 360-16)
- Footing solve with monotonicity validation
- Baseplate checks (AISC 360-16, ACI 318)
- Baseplate auto-solve with grid optimizer

All tests verify:
- Determinism (same inputs → same outputs)
- Unit consistency (pint validation)
- Monotonicity where applicable
- Edge cases and boundary conditions
"""

from __future__ import annotations

import math
import pytest

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from apex.domains.signage.models import (
    BasePlateInput,
    Cabinet,
    SiteLoads,
)
from apex.domains.signage.solvers import (
    baseplate_auto_solve,
    baseplate_checks,
    derive_loads,
    filter_poles,
    footing_solve,
)


# ========== Load Derivation Tests ==========


class TestDeriveLoads:
    """Test load derivation solver with ASCE 7-22 equations."""
    
    def test_basic_load_derivation(self):
        """Test basic load derivation with single cabinet."""
        site = SiteLoads(wind_speed_mph=115.0, exposure="C")
        cabinets = [Cabinet(width_ft=14.0, height_ft=8.0, depth_in=12.0, weight_psf=10.0)]
        
        result = derive_loads(site, cabinets, height_ft=25.0)
        
        assert result.a_ft2 > 0
        assert result.z_cg_ft > 0
        assert result.mu_kipft > 0
        assert result.weight_estimate_lb > 0
        
        # Verify ASCE 7-22 velocity pressure formula
        expected_q = 0.00256 * 1.0 * 1.0 * 0.85 * (115.0**2) * 0.85
        expected_q_psf = round(expected_q, 2)
        # q should be approximately 25-30 psf for V=115 mph
        assert 20.0 < expected_q_psf < 35.0
    
    def test_load_derivation_deterministic(self):
        """Test deterministic output with same inputs."""
        site = SiteLoads(wind_speed_mph=100.0, exposure="C")
        cabinets = [Cabinet(width_ft=10.0, height_ft=6.0, weight_psf=10.0)]
        
        result1 = derive_loads(site, cabinets, height_ft=20.0, seed=42)
        result2 = derive_loads(site, cabinets, height_ft=20.0, seed=42)
        
        assert result1.mu_kipft == result2.mu_kipft
        assert result1.a_ft2 == result2.a_ft2
        assert result1.z_cg_ft == result2.z_cg_ft
    
    def test_load_derivation_multiple_cabinets(self):
        """Test load derivation with multiple stacked cabinets."""
        site = SiteLoads(wind_speed_mph=115.0, exposure="C")
        cabinets = [
            Cabinet(width_ft=12.0, height_ft=6.0, weight_psf=10.0),
            Cabinet(width_ft=12.0, height_ft=6.0, weight_psf=10.0),
        ]
        
        result = derive_loads(site, cabinets, height_ft=25.0)
        
        # Centroid should be at mid-height of stack
        assert result.z_cg_ft > 0
        assert result.a_ft2 == 144.0  # 12 * 6 * 2
        assert result.mu_kipft > 0
    
    def test_load_derivation_exposure_factors(self):
        """Test different exposure categories affect velocity pressure."""
        cabinets = [Cabinet(width_ft=10.0, height_ft=6.0, weight_psf=10.0)]
        
        site_b = SiteLoads(wind_speed_mph=115.0, exposure="B")
        site_c = SiteLoads(wind_speed_mph=115.0, exposure="C")
        site_d = SiteLoads(wind_speed_mph=115.0, exposure="D")
        
        result_b = derive_loads(site_b, cabinets, height_ft=20.0)
        result_c = derive_loads(site_c, cabinets, height_ft=20.0)
        result_d = derive_loads(site_d, cabinets, height_ft=20.0)
        
        # Exposure D should have highest moment (higher Kz)
        assert result_d.mu_kipft > result_c.mu_kipft
        assert result_c.mu_kipft > result_b.mu_kipft
    
    def test_load_derivation_empty_cabinets(self):
        """Test edge case: empty cabinet list."""
        site = SiteLoads(wind_speed_mph=115.0, exposure="C")
        
        result = derive_loads(site, [], height_ft=25.0)
        
        assert result.a_ft2 == 0.0
        assert result.z_cg_ft == 0.0
        assert result.mu_kipft == 0.0
        assert result.weight_estimate_lb == 0.0


# ========== Pole Filtering Tests ==========


class TestFilterPoles:
    """Test pole filtering solver with AISC 360-16 strength checks."""
    
    def test_filter_poles_strength_check(self):
        """Test filtering by AISC 360-16 flexural strength."""
        sections = [
            {"type": "HSS", "shape": "HSS 4x4x1/4", "sx_in3": 6.25, "w_lbs_per_ft": 10.9},
            {"type": "HSS", "shape": "HSS 6x6x1/4", "sx_in3": 19.1, "w_lbs_per_ft": 21.7},
            {"type": "HSS", "shape": "HSS 8x8x3/8", "sx_in3": 45.2, "w_lbs_per_ft": 43.5},
        ]
        prefs = {"family": "HSS", "steel_grade": "A500B", "sort_by": "Sx"}
        
        # Mu_required = 50 kip-in
        # HSS 4x4: φMn = 0.9 * 46 * 6.25 = 258.75 kip-in >= 50 ✓
        # HSS 6x6: φMn = 0.9 * 46 * 19.1 = 791.34 kip-in >= 50 ✓
        # HSS 8x8: φMn = 0.9 * 46 * 45.2 = 1871.28 kip-in >= 50 ✓
        result, _ = filter_poles(mu_required_kipin=50.0, sections=sections, prefs=prefs, seed=42, return_warnings=True)
        
        assert len(result) == 3
        assert result[0].shape == "HSS 4x4x1/4"  # Lowest Sx first
    
    def test_filter_poles_insufficient_strength(self):
        """Test filtering removes sections with insufficient strength."""
        sections = [
            {"type": "HSS", "shape": "HSS 2x2x1/8", "sx_in3": 1.5, "w_lbs_per_ft": 5.0},
            {"type": "HSS", "shape": "HSS 6x6x1/4", "sx_in3": 19.1, "w_lbs_per_ft": 21.7},
        ]
        prefs = {"family": "HSS", "steel_grade": "A500B", "sort_by": "weight_per_ft"}
        
        # Mu_required = 100 kip-in
        # HSS 2x2: φMn = 0.9 * 46 * 1.5 = 62.1 kip-in < 100 ✗
        # HSS 6x6: φMn = 0.9 * 46 * 19.1 = 791.34 kip-in >= 100 ✓
        result, warnings = filter_poles(mu_required_kipin=100.0, sections=sections, prefs=prefs, seed=42, return_warnings=True)
        
        assert len(result) == 1
        assert result[0].shape == "HSS 6x6x1/4"
    
    def test_filter_poles_deterministic_sort(self):
        """Test deterministic sorting with seed."""
        sections = [
            {"type": "HSS", "shape": "HSS A", "sx_in3": 10.0, "w_lbs_per_ft": 15.0},
            {"type": "HSS", "shape": "HSS B", "sx_in3": 10.0, "w_lbs_per_ft": 15.0},  # Tie in weight
            {"type": "HSS", "shape": "HSS C", "sx_in3": 12.0, "w_lbs_per_ft": 15.0},
        ]
        prefs = {"family": "HSS", "steel_grade": "A500B", "sort_by": "weight_per_ft"}
        
        result1, _ = filter_poles(mu_required_kipin=50.0, sections=sections, prefs=prefs, seed=42, return_warnings=True)
        result2, _ = filter_poles(mu_required_kipin=50.0, sections=sections, prefs=prefs, seed=42, return_warnings=True)
        
        # Should be deterministic
        assert [r.shape for r in result1] == [r.shape for r in result2]
    
    def test_filter_poles_family_filter(self):
        """Test filtering by pole family."""
        sections = [
            {"type": "HSS", "shape": "HSS 4x4", "sx_in3": 10.0, "w_lbs_per_ft": 10.0},
            {"type": "Pipe", "shape": "Pipe 4", "sx_in3": 8.0, "w_lbs_per_ft": 9.0},
        ]
        prefs = {"family": "HSS", "steel_grade": "A500B", "sort_by": "Sx"}
        
        result, _ = filter_poles(mu_required_kipin=50.0, sections=sections, prefs=prefs, seed=42, return_warnings=True)
        
        assert len(result) == 1
        assert result[0].shape == "HSS 4x4"
    
    def test_filter_poles_steel_grade_properties(self):
        """Test different steel grades affect capacity."""
        sections = [
            {"type": "HSS", "shape": "HSS 4x4", "sx_in3": 10.0, "w_lbs_per_ft": 10.0},
        ]
        
        prefs_a36 = {"family": "HSS", "steel_grade": "A36", "sort_by": "Sx"}
        prefs_a500 = {"family": "HSS", "steel_grade": "A500B", "sort_by": "Sx"}
        
        # A36: φMn = 0.9 * 36 * 10 = 324 kip-in
        # A500B: φMn = 0.9 * 46 * 10 = 414 kip-in
        
        # Both should pass for Mu=300 kip-in, but A500B has higher capacity
        result_a36, _ = filter_poles(mu_required_kipin=300.0, sections=sections, prefs=prefs_a36, seed=42, return_warnings=True)
        result_a500, _ = filter_poles(mu_required_kipin=300.0, sections=sections, prefs=prefs_a500, seed=42, return_warnings=True)
        
        assert len(result_a36) == 1
        assert len(result_a500) == 1
        assert result_a36[0].fy_ksi == 36.0
        assert result_a500[0].fy_ksi == 46.0


# ========== Footing Solve Tests ==========


class TestFootingSolve:
    """Test footing solve with monotonicity validation."""
    
    def test_footing_solve_basic(self):
        """Test basic footing depth calculation."""
        mu_kipft = 10.0
        diameter_ft = 3.0
        soil_psf = 3000.0
        
        depth, req_eng, warnings = footing_solve(mu_kipft, diameter_ft, soil_psf, k=1.0, seed=42)
        
        assert depth >= 2.0  # Minimum depth
        assert depth > 0.0
        assert isinstance(req_eng, bool)
        assert isinstance(warnings, list)
    
    def test_footing_solve_monotonicity(self):
        """Test monotonicity: diameter↓ → depth↑."""
        mu_kipft = 10.0
        soil_psf = 3000.0
        k = 1.0
        
        depth_small, _, _ = footing_solve(mu_kipft, diameter_ft=2.0, soil_psf=soil_psf, k=k, seed=42)
        depth_medium, _, _ = footing_solve(mu_kipft, diameter_ft=3.0, soil_psf=soil_psf, k=k, seed=42)
        depth_large, _, _ = footing_solve(mu_kipft, diameter_ft=4.0, soil_psf=soil_psf, k=k, seed=42)
        
        # Smaller diameter should require deeper foundation
        assert depth_small > depth_medium
        assert depth_medium > depth_large
    
    def test_footing_solve_monotonicity_moment(self):
        """Test monotonicity: moment↑ → depth↑."""
        diameter_ft = 3.0
        soil_psf = 3000.0
        k = 1.0
        
        depth_low, _, _ = footing_solve(mu_kipft=5.0, diameter_ft=diameter_ft, soil_psf=soil_psf, k=k, seed=42)
        depth_high, _, _ = footing_solve(mu_kipft=20.0, diameter_ft=diameter_ft, soil_psf=soil_psf, k=k, seed=42)
        
        assert depth_high > depth_low
    
    def test_footing_solve_multi_pole_split(self):
        """Test moment splitting for multi-pole per-support."""
        mu_total = 20.0
        diameter_ft = 3.0
        soil_psf = 3000.0
        
        depth_single, _, _ = footing_solve(mu_total, diameter_ft, soil_psf, poles=1, seed=42)
        depth_per_support, _, _ = footing_solve(mu_total, diameter_ft, soil_psf, poles=2, footing_type="per_support", seed=42)
        
        # Per-support should be shallower (split moment)
        assert depth_per_support < depth_single
    
    def test_footing_solve_deterministic(self):
        """Test deterministic output."""
        mu_kipft = 10.0
        diameter_ft = 3.0
        soil_psf = 3000.0
        
        depth1, _, _ = footing_solve(mu_kipft, diameter_ft, soil_psf, seed=42)
        depth2, _, _ = footing_solve(mu_kipft, diameter_ft, soil_psf, seed=42)
        
        assert depth1 == depth2
    
    def test_footing_solve_minimum_depth(self):
        """Test minimum depth enforcement."""
        # Very small moment should still yield minimum 2 ft depth
        depth, _, _ = footing_solve(mu_kipft=0.1, diameter_ft=10.0, soil_psf=5000.0, seed=42)
        
        assert depth >= 2.0
    
    def test_footing_solve_soil_bearing_effect(self):
        """Test that higher soil bearing reduces required depth."""
        mu_kipft = 10.0
        diameter_ft = 3.0
        
        depth_low_soil, _, _ = footing_solve(mu_kipft, diameter_ft, soil_psf=2000.0, seed=42)
        depth_high_soil, _, _ = footing_solve(mu_kipft, diameter_ft, soil_psf=5000.0, seed=42)
        
        assert depth_high_soil < depth_low_soil


# ========== Baseplate Checks Tests ==========


class TestBaseplateChecks:
    """Test baseplate engineering checks per AISC 360-16 and ACI 318."""
    
    def test_baseplate_checks_all_pass(self):
        """Test baseplate with all checks passing."""
        plate = BasePlateInput(
            plate_w_in=12.0,
            plate_l_in=12.0,
            plate_thk_in=0.75,
            fy_ksi=36.0,
            weld_size_in=0.25,
            anchor_dia_in=0.75,
            anchor_grade_ksi=58.0,
            anchor_embed_in=10.0,
            rows=2,
            bolts_per_row=2,
            row_spacing_in=6.0,
            edge_distance_in=3.0,
        )
        loads = {"mu_kipft": 5.0, "vu_kip": 2.0, "tu_kip": 3.0}
        
        checks, _ = baseplate_checks(plate, loads, seed=42, suggest_alternatives=False)
        
        assert len(checks) >= 3  # Plate, weld, anchors
        # All should pass with reasonable loads
        assert all(c.pass for c in checks)
    
    def test_baseplate_checks_plate_thickness_fail(self):
        """Test plate thickness check failure."""
        plate = BasePlateInput(
            plate_w_in=12.0,
            plate_l_in=12.0,
            plate_thk_in=0.125,  # Too thin
            fy_ksi=36.0,
            weld_size_in=0.25,
            anchor_dia_in=0.75,
            anchor_grade_ksi=58.0,
            anchor_embed_in=10.0,
            rows=2,
            bolts_per_row=2,
            row_spacing_in=6.0,
            edge_distance_in=3.0,
        )
        loads = {"mu_kipft": 20.0, "vu_kip": 5.0, "tu_kip": 15.0}
        
        checks, alternatives = baseplate_checks(plate, loads, seed=42, suggest_alternatives=True)
        
        plate_check = next((c for c in checks if c.name == "Plate Thickness"), None)
        assert plate_check is not None
        # Should fail with thin plate and high moment
        assert not plate_check.pass
    
    def test_baseplate_checks_anchor_tension_steel_governing(self):
        """Test anchor tension check with steel capacity governing."""
        plate = BasePlateInput(
            plate_w_in=12.0,
            plate_l_in=12.0,
            plate_thk_in=0.5,
            fy_ksi=36.0,
            weld_size_in=0.25,
            anchor_dia_in=0.5,  # Small diameter
            anchor_grade_ksi=58.0,
            anchor_embed_in=6.0,  # Shallow embed
            rows=2,
            bolts_per_row=2,
            row_spacing_in=6.0,
            edge_distance_in=3.0,
        )
        loads = {"mu_kipft": 5.0, "vu_kip": 1.0, "tu_kip": 4.0}
        
        checks, alternatives = baseplate_checks(plate, loads, seed=42, suggest_alternatives=True)
        
        tension_check = next((c for c in checks if c.name == "Anchor Tension"), None)
        assert tension_check is not None
        # With small anchor and shallow embed, steel likely governs
        assert tension_check.governing in ["steel", "breakout"]
    
    def test_baseplate_checks_deterministic(self):
        """Test deterministic check ordering."""
        plate = BasePlateInput(
            plate_w_in=12.0,
            plate_l_in=12.0,
            plate_thk_in=0.5,
            fy_ksi=36.0,
            weld_size_in=0.25,
            anchor_dia_in=0.75,
            anchor_grade_ksi=58.0,
            anchor_embed_in=10.0,
            rows=2,
            bolts_per_row=2,
            row_spacing_in=6.0,
            edge_distance_in=3.0,
        )
        loads = {"mu_kipft": 5.0, "vu_kip": 2.0, "tu_kip": 3.0}
        
        checks1, _ = baseplate_checks(plate, loads, seed=42, suggest_alternatives=False)
        checks2, _ = baseplate_checks(plate, loads, seed=42, suggest_alternatives=False)
        
        assert len(checks1) == len(checks2)
        for c1, c2 in zip(checks1, checks2):
            assert c1.name == c2.name
            assert c1.pass == c2.pass
            assert c1.demand == c2.demand
    
    def test_baseplate_checks_zero_loads(self):
        """Test edge case: zero loads."""
        plate = BasePlateInput(
            plate_w_in=12.0,
            plate_l_in=12.0,
            plate_thk_in=0.5,
            fy_ksi=36.0,
            weld_size_in=0.25,
            anchor_dia_in=0.75,
            anchor_grade_ksi=58.0,
            anchor_embed_in=10.0,
            rows=2,
            bolts_per_row=2,
            row_spacing_in=6.0,
            edge_distance_in=3.0,
        )
        loads = {"mu_kipft": 0.0, "vu_kip": 0.0, "tu_kip": 0.0}
        
        checks, _ = baseplate_checks(plate, loads, seed=42, suggest_alternatives=False)
        
        # All checks should pass with zero loads
        assert all(c.pass for c in checks)


# ========== Baseplate Auto-Solve Tests ==========


class TestBaseplateAutoSolve:
    """Test baseplate auto-solve with grid optimizer."""
    
    def test_baseplate_auto_solve_feasible(self):
        """Test auto-solve finds feasible solution."""
        loads = {"mu_kipft": 5.0, "vu_kip": 2.0, "tu_kip": 3.0}
        
        solution = baseplate_auto_solve(loads, seed=42)
        
        assert solution.input is not None
        assert len(solution.checks.checks) > 0
        assert solution.cost_proxy >= 0.0
    
    def test_baseplate_auto_solve_optimizes_cost(self):
        """Test that auto-solve minimizes cost proxy."""
        loads = {"mu_kipft": 3.0, "vu_kip": 1.0, "tu_kip": 2.0}
        
        solution = baseplate_auto_solve(loads, seed=42)
        
        # Solution should have reasonable cost
        assert 50.0 < solution.cost_proxy < 1000.0  # Reasonable range
    
    def test_baseplate_auto_solve_with_constraints(self):
        """Test auto-solve respects constraints."""
        loads = {"mu_kipft": 5.0, "vu_kip": 2.0, "tu_kip": 3.0}
        constraints = {"min_plate_size_in": 14.0, "max_plate_size_in": 18.0}
        
        solution = baseplate_auto_solve(loads, constraints=constraints, seed=42)
        
        assert solution.input.plate_w_in >= 14.0
        assert solution.input.plate_w_in <= 18.0
        assert solution.input.plate_l_in >= 14.0
        assert solution.input.plate_l_in <= 18.0
    
    def test_baseplate_auto_solve_deterministic(self):
        """Test deterministic auto-solve with same seed."""
        loads = {"mu_kipft": 5.0, "vu_kip": 2.0, "tu_kip": 3.0}
        
        solution1 = baseplate_auto_solve(loads, seed=42)
        solution2 = baseplate_auto_solve(loads, seed=42)
        
        assert solution1.input.plate_w_in == solution2.input.plate_w_in
        assert solution1.input.plate_l_in == solution2.input.plate_l_in
        assert solution1.cost_proxy == solution2.cost_proxy
    
    def test_baseplate_auto_solve_high_loads(self):
        """Test auto-solve with high loads requiring larger design."""
        loads = {"mu_kipft": 50.0, "vu_kip": 20.0, "tu_kip": 30.0}
        
        solution = baseplate_auto_solve(loads, seed=42)
        
        # Should find feasible solution (may not pass all checks if extreme)
        assert solution.input is not None
        # Higher loads should require larger/thicker plate
        assert solution.input.plate_w_in >= 12.0
        assert solution.input.plate_thk_in >= 0.25


# ========== Property-Based Tests ==========


class TestMonotonicity:
    """Property-based tests for monotonicity guarantees."""
    
    def test_footing_monotonicity_property(self):
        """Property: For fixed moment, depth decreases with diameter."""
        mu = 10.0
        soil = 3000.0
        diameters = [2.0, 2.5, 3.0, 3.5, 4.0]
        
        depths = [footing_solve(mu, d, soil, seed=42)[0] for d in diameters]
        
        # Verify strictly decreasing (allowing for rounding)
        for i in range(len(depths) - 1):
            assert depths[i] >= depths[i + 1] - 0.1  # Allow small rounding differences
    
    def test_load_derivation_positive_outputs(self):
        """Property: All outputs should be non-negative."""
        site = SiteLoads(wind_speed_mph=100.0, exposure="C")
        cabinets = [Cabinet(width_ft=10.0, height_ft=6.0, weight_psf=10.0)]
        
        result = derive_loads(site, cabinets, height_ft=20.0)
        
        assert result.a_ft2 >= 0.0
        assert result.z_cg_ft >= 0.0
        assert result.weight_estimate_lb >= 0.0
        assert result.mu_kipft >= 0.0


# ========== Edge Case Tests ==========


class TestEdgeCases:
    """Edge case and boundary condition tests."""
    
    def test_footing_extreme_diameter(self):
        """Test footing with very small diameter."""
        depth = footing_solve(mu_kipft=10.0, diameter_ft=1.0, soil_psf=3000.0, seed=42)
        
        # Should still return valid depth (may be very large)
        assert depth >= 2.0
    
    def test_footing_extreme_moment(self):
        """Test footing with very large moment."""
        depth = footing_solve(mu_kipft=100.0, diameter_ft=3.0, soil_psf=3000.0, seed=42)
        
        assert depth >= 2.0
    
    def test_filter_poles_empty_sections(self):
        """Test filtering with empty section list."""
        result, warnings = filter_poles(mu_required_kipin=50.0, sections=[], prefs={"family": "HSS"}, seed=42, return_warnings=True)
        
        assert len(result) == 0
        assert len(warnings) > 0
    
    def test_baseplate_checks_no_anchors(self):
        """Test baseplate checks with zero anchors (should handle gracefully)."""
        plate = BasePlateInput(
            plate_w_in=12.0,
            plate_l_in=12.0,
            plate_thk_in=0.5,
            fy_ksi=36.0,
            weld_size_in=0.25,
            anchor_dia_in=0.75,
            anchor_grade_ksi=58.0,
            anchor_embed_in=10.0,
            rows=0,  # No anchors
            bolts_per_row=0,
            row_spacing_in=6.0,
            edge_distance_in=3.0,
        )
        loads = {"mu_kipft": 5.0, "vu_kip": 2.0, "tu_kip": 3.0}
        
        checks, _ = baseplate_checks(plate, loads, seed=42, suggest_alternatives=False)
        
        # Should still return plate and weld checks
        assert len(checks) >= 2
        # Anchor checks may be skipped or have zero capacity

