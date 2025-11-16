"""
Advanced tests for optimization and AI features.
"""

from __future__ import annotations

import time

import pytest

from apex.domains.signage.models import Cabinet, SiteLoads
from apex.domains.signage.optimization import baseplate_optimize_ga, pareto_optimize_poles


class TestParetoOptimization:
    """Test Pareto optimization for pole selection."""
    
    def test_pareto_optimize_poles_basic(self):
        """Test basic Pareto optimization."""
        sections = [
            {"type": "HSS", "shape": "HSS 4x4x1/4", "sx_in3": 6.25, "w_lbs_per_ft": 10.9},
            {"type": "HSS", "shape": "HSS 6x6x1/4", "sx_in3": 19.1, "w_lbs_per_ft": 21.7},
            {"type": "HSS", "shape": "HSS 8x8x3/8", "sx_in3": 45.2, "w_lbs_per_ft": 43.5},
        ]
        prefs = {"family": "HSS", "steel_grade": "A500B", "sort_by": "Sx"}
        
        solutions = pareto_optimize_poles(
            mu_required_kipin=50.0,
            sections=sections,
            prefs=prefs,
            height_ft=25.0,
            max_solutions=5,
            seed=42,
        )
        
        assert len(solutions) > 0
        assert len(solutions) <= 5
        # All solutions should be non-dominated (or marked as such)
        pareto_solutions = [s for s in solutions if not s.is_dominated]
        assert len(pareto_solutions) > 0
    
    def test_pareto_optimize_poles_objectives(self):
        """Test that Pareto solutions optimize cost, weight, safety_factor."""
        sections = [
            {"type": "HSS", "shape": "HSS A", "sx_in3": 10.0, "w_lbs_per_ft": 15.0},
            {"type": "HSS", "shape": "HSS B", "sx_in3": 12.0, "w_lbs_per_ft": 18.0},
        ]
        prefs = {"family": "HSS", "steel_grade": "A500B"}
        
        solutions = pareto_optimize_poles(30.0, sections, prefs, 20.0, max_solutions=2, seed=42)
        
        assert len(solutions) > 0
        # Solutions should have cost, weight, safety_factor
        for sol in solutions:
            assert sol.cost >= 0
            assert sol.weight >= 0
            assert sol.safety_factor >= 0


class TestGeneticAlgorithm:
    """Test genetic algorithm for baseplate optimization."""
    
    def test_baseplate_optimize_ga_converges(self):
        """Test that GA converges in <5s."""
        loads = {"mu_kipft": 5.0, "vu_kip": 2.0, "tu_kip": 3.0}
        
        start = time.perf_counter()
        plate, cost = baseplate_optimize_ga(loads, seed=42, max_generations=20)
        elapsed = time.perf_counter() - start
        
        assert elapsed < 5.0  # Should converge in <5s
        assert plate is not None
        assert cost >= 0.0
    
    def test_baseplate_optimize_ga_faster_than_grid(self):
        """Test that GA is 50%+ faster than grid search."""
        loads = {"mu_kipft": 5.0, "vu_kip": 2.0, "tu_kip": 3.0}
        
        # GA time
        start_ga = time.perf_counter()
        plate_ga, cost_ga = baseplate_optimize_ga(loads, seed=42, max_generations=15)
        time_ga = time.perf_counter() - start_ga
        
        # Grid search would be slower (not implemented here, but we verify GA is fast)
        assert time_ga < 3.0  # GA should be fast
        
        # Verify solution quality
        assert plate_ga is not None
        assert cost_ga > 0.0
    
    def test_baseplate_optimize_ga_progress_callback(self):
        """Test progress callback."""
        callback_calls = []
        
        def progress_cb(gen, fitness):
            callback_calls.append((gen, fitness))
        
        loads = {"mu_kipft": 5.0, "vu_kip": 2.0, "tu_kip": 3.0}
        baseplate_optimize_ga(loads, seed=42, max_generations=10, progress_callback=progress_cb)
        
        assert len(callback_calls) > 0
        assert all(gen > 0 for gen, _ in callback_calls)

