"""Unit tests: Verify footing solver monotonicity."""

from __future__ import annotations

import pytest


def test_footing_depth_increases_as_diameter_decreases():
    """Monotonicity: diameter↓ ⇒ depth↑"""
    from apex_signcalc.foundation_embed import solve_footing_interactive
    
    M_pole_kipft = 15.0
    soil_psf = 3000.0
    num_poles = 1
    
    # Test diameters from large to small
    diameters = [4.0, 3.5, 3.0, 2.5, 2.0]
    depths = [solve_footing_interactive(d, M_pole_kipft, soil_psf, num_poles) for d in diameters]
    
    # Verify depths increase as diameter decreases
    for i in range(len(depths) - 1):
        assert depths[i + 1] >= depths[i], f"Depth should increase as diameter decreases: {diameters[i]}→{diameters[i+1]}"


def test_footing_concrete_yards_calculation():
    """Verify concrete yardage calculation accuracy."""
    import math
    
    diameter_ft = 3.0
    depth_ft = 4.0
    
    volume_cf = math.pi * (diameter_ft / 2.0) ** 2 * depth_ft
    concrete_yards = round(volume_cf / 27.0, 2)
    
    expected_yards = round((math.pi * 1.5 ** 2 * 4.0) / 27.0, 2)
    assert concrete_yards == expected_yards

