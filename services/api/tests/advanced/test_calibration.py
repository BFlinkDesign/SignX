"""Tests for calibration and uncertainty analysis."""

from __future__ import annotations

import pytest

from apex.domains.signage.calibration import (
    compute_uncertainty_bands,
    monte_carlo_reliability,
    sensitivity_analysis,
)


class TestMonteCarloReliability:
    """Test Monte Carlo reliability analysis."""
    
    def test_monte_carlo_reliability_basic(self):
        """Test basic reliability analysis."""
        result = monte_carlo_reliability(
            load_mean=10.0,
            load_std=1.0,
            resistance_mean=20.0,
            resistance_std=2.0,
            n_samples=1000,
            target_beta=3.5,
        )
        
        assert "beta" in result
        assert "failure_probability" in result
        assert "passes_target" in result
        assert "beta_ci" in result
        assert "pf_ci" in result
        
        assert result["beta"] > 0
        assert 0.0 <= result["failure_probability"] <= 1.0
    
    def test_monte_carlo_reliability_high_margin(self):
        """Test that high safety margin yields high beta."""
        result = monte_carlo_reliability(
            load_mean=10.0,
            load_std=1.0,
            resistance_mean=50.0,  # High resistance
            resistance_std=2.0,
            n_samples=1000,
        )
        
        # Should have high beta and low failure probability
        assert result["beta"] > 2.0
        assert result["failure_probability"] < 0.1


class TestSensitivityAnalysis:
    """Test sensitivity analysis."""
    
    def test_sensitivity_analysis_basic(self):
        """Test basic sensitivity analysis."""
        
        def output_func(inputs):
            # Simple function: output = 2*x1 + x2 - 0.5*x3
            return 2.0 * inputs["x1"] + inputs["x2"] - 0.5 * inputs["x3"]
        
        result = sensitivity_analysis(
            input_means={"x1": 10.0, "x2": 5.0, "x3": 2.0},
            input_stds={"x1": 1.0, "x2": 0.5, "x3": 0.2},
            output_function=output_func,
            n_samples=500,
        )
        
        assert "ranked_inputs" in result
        assert "sensitivities" in result
        
        assert len(result["ranked_inputs"]) == 3
        # x1 should be most sensitive (coefficient 2.0)
        assert result["sensitivities"]["x1"] >= result["sensitivities"]["x3"]


class TestUncertaintyBands:
    """Test uncertainty band computation."""
    
    def test_uncertainty_bands_basic(self):
        """Test basic uncertainty bands."""
        result = compute_uncertainty_bands(
            nominal_value=100.0,
            coefficient_of_variation=0.1,
            confidence_level=0.9,
        )
        
        assert "nominal" in result
        assert "lower_bound" in result
        assert "upper_bound" in result
        assert "std_dev" in result
        
        assert result["lower_bound"] < result["nominal"]
        assert result["upper_bound"] > result["nominal"]
        assert result["std_dev"] > 0
    
    def test_uncertainty_bands_coverage(self):
        """Test that bands cover nominal with confidence."""
        result = compute_uncertainty_bands(100.0, 0.1, 0.95)
        
        # 95% CI should be wider than 90%
        result_90 = compute_uncertainty_bands(100.0, 0.1, 0.9)
        
        width_95 = result["upper_bound"] - result["lower_bound"]
        width_90 = result_90["upper_bound"] - result_90["lower_bound"]
        
        assert width_95 > width_90

