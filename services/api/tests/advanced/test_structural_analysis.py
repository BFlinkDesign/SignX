"""Tests for advanced structural analysis."""

from __future__ import annotations

import pytest

from apex.domains.signage.structural_analysis import (
    connection_design,
    dynamic_load_analysis,
    fatigue_analysis,
)


class TestDynamicLoadAnalysis:
    """Test dynamic load analysis."""
    
    def test_dynamic_load_amplification(self):
        """Test that dynamic loads show amplification."""
        result = dynamic_load_analysis(
            static_load_lbf=1000.0,
            natural_period_sec=0.5,
            damping_ratio=0.05,
            site_class="C",
        )
        
        assert "peak_load" in result
        assert "static_load" in result
        assert "amplification_factor" in result
        
        assert result["peak_load"] >= result["static_load"]
        assert result["amplification_factor"] >= 1.0
    
    def test_dynamic_load_site_class_effect(self):
        """Test that site class affects amplification."""
        result_c = dynamic_load_analysis(1000.0, 0.5, 0.05, "C")
        result_d = dynamic_load_analysis(1000.0, 0.5, 0.05, "D")
        
        # Site D may have higher amplification
        assert result_d["amplification_factor"] >= result_c["amplification_factor"]


class TestFatigueAnalysis:
    """Test fatigue analysis."""
    
    def test_fatigue_analysis_passes(self):
        """Test fatigue analysis for typical stress range."""
        result = fatigue_analysis(
            stress_range_ksi=5.0,
            detail_category="E",
            design_life_years=25.0,
        )
        
        assert "design_life_years" in result
        assert "passes_25yr_requirement" in result
        assert "stress_range_ksi" in result
    
    def test_fatigue_analysis_category_effect(self):
        """Test that detail category affects fatigue life."""
        result_e = fatigue_analysis(5.0, "E", 25.0)
        result_c = fatigue_analysis(5.0, "C", 25.0)
        
        # Category C should pass more easily (higher threshold)
        assert result_c["passes_25yr_requirement"] >= result_e["passes_25yr_requirement"]


class TestConnectionDesign:
    """Test connection design."""
    
    def test_connection_design_bolts_required(self):
        """Test bolt group analysis."""
        result = connection_design(
            tension_kip=10.0,
            shear_kip=5.0,
            bolt_grade="A325",
            bolt_diameter_in=0.75,
            num_bolts=4,
        )
        
        assert "bolts_required" in result
        assert "bolts_provided" in result
        assert "weld_size_in" in result
        assert "connection_capacity_kip" in result
        assert "interaction_ratio" in result
        assert "passes" in result
        
        assert result["bolts_required"] >= 0
        assert result["weld_size_in"] > 0
    
    def test_connection_design_interaction(self):
        """Test combined tension+shear interaction."""
        result = connection_design(20.0, 10.0, "A325", 0.75, 4)
        
        # Interaction ratio should be reasonable
        assert result["interaction_ratio"] >= 0.0
        # If passes, interaction should be <= 1.0
        if result["passes"]:
            assert result["interaction_ratio"] <= 1.0

