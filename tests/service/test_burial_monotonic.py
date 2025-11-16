"""
Monotonicity tests for direct burial foundation design.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Import from signcalc-service
_signcalc_path = Path(__file__).parent.parent.parent / "services" / "signcalc-service"
if str(_signcalc_path) not in sys.path:
    sys.path.insert(0, str(_signcalc_path))

from apex_signcalc.foundation_embed import solve_footing_interactive


def test_diameter_decreases_depth_increases() -> None:
    """Verify inverse relationship: diameter↓ ⇒ depth↑"""
    M_pole = 10.0  # kip-ft
    soil = 3000.0  # psf
    num_poles = 1

    d1_in = solve_footing_interactive(2.0, M_pole, soil, num_poles)
    d2_in = solve_footing_interactive(3.0, M_pole, soil, num_poles)
    d3_in = solve_footing_interactive(4.0, M_pole, soil, num_poles)

    assert d1_in > d2_in > d3_in, f"Monotonic violation: {d1_in=}, {d2_in=}, {d3_in=}"


def test_moment_increase_raises_depth() -> None:
    """Higher moment → deeper foundation"""
    diameter_ft = 3.0
    soil = 3000.0
    num_poles = 1

    depth_low = solve_footing_interactive(diameter_ft, 5.0, soil, num_poles)
    depth_high = solve_footing_interactive(diameter_ft, 15.0, soil, num_poles)

    assert depth_high > depth_low, f"Higher moment should require deeper embed: {depth_low=}, {depth_high=}"


def test_multi_pole_split_reduces_depth() -> None:
    """Two-pole splits moment → shallower per support"""
    diameter_ft = 3.0
    M_pole = 10.0
    soil = 3000.0

    depth_single = solve_footing_interactive(diameter_ft, M_pole, soil, num_poles=1)
    depth_two = solve_footing_interactive(diameter_ft, M_pole, soil, num_poles=2)

    assert depth_two < depth_single, f"Two-pole should split moment: {depth_single=}, {depth_two=}"


def test_minimum_depth_enforced() -> None:
    """Minimum 36 inches enforced regardless of calculation"""
    diameter_ft = 10.0  # Very large diameter should reduce depth
    M_pole = 1.0  # Very small moment
    soil = 5000.0  # High bearing capacity
    num_poles = 1

    depth = solve_footing_interactive(diameter_ft, M_pole, soil, num_poles)
    assert depth >= 36.0, f"Minimum depth should be 36 inches: got {depth}"


def test_grid_monotonicity() -> None:
    """Test monotonicity across a grid of diameters"""
    M_pole = 10.0
    soil = 3000.0
    num_poles = 1

    diameters = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
    depths = [solve_footing_interactive(d, M_pole, soil, num_poles) for d in diameters]

    for i in range(len(depths) - 1):
        assert depths[i] > depths[i + 1], f"Monotonic violation at {diameters[i]=}: {depths[i]} <= {depths[i+1]}"

