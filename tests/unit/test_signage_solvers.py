"""
APEX Signage Engineering - Unit Tests for Deterministic Solvers
"""

from __future__ import annotations

import pytest

from apex.domains.signage.models import Cabinet, SiteLoads
from apex.domains.signage.solvers import (
    baseplate_checks,
    derive_loads,
    footing_solve,
    filter_poles,
)


def test_load_derivation():
    """Test load derivation from cabinets and site."""
    site = SiteLoads(wind_speed_mph=115.0, exposure="C")
    cabinets = [
        Cabinet(width_ft=14.0, height_ft=8.0, depth_in=12.0, weight_psf=10.0)
    ]

    derived = derive_loads(site, cabinets, 25.0)

    assert derived.a_ft2 > 0
    assert derived.z_cg_ft > 0
    assert derived.mu_kipft > 0
    assert derived.weight_estimate_lb > 0


def test_footing_solve_monotonicity():
    """Test monotonicity: smaller diameter -> larger depth."""
    mu_kipft = 100.0
    soil_psf = 3000.0

    depth_6ft = footing_solve(mu_kipft, 6.0, soil_psf)
    depth_4ft = footing_solve(mu_kipft, 4.0, soil_psf)

    # Smaller diameter should require deeper footing
    assert depth_4ft > depth_6ft


def test_footing_solve_two_pole_per_support():
    """Test two-pole per-support splits moment."""
    mu_total = 100.0
    soil_psf = 3000.0

    depth_single = footing_solve(mu_total, 6.0, soil_psf, poles=1)
    depth_per_support = footing_solve(
        mu_total, 6.0, soil_psf, poles=2, footing_type="per_support"
    )

    # Per-support should need less depth (half the moment)
    assert depth_per_support < depth_single


def test_baseplate_checks_structure():
    """Test baseplate checks return proper structure."""
    from apex.domains.signage.models import BasePlateInput

    plate = BasePlateInput(
        plate_w_in=12.0,
        plate_l_in=12.0,
        plate_thk_in=1.25,
        fy_ksi=36.0,
        weld_size_in=0.25,
        anchor_dia_in=0.625,
        anchor_grade_ksi=60.0,
        anchor_embed_in=12.0,
        rows=3,
        bolts_per_row=2,
        row_spacing_in=10.0,
        edge_distance_in=2.0,
    )

    loads = {"mu_kipft": 50.0, "vu_kip": 10.0}

    checks = baseplate_checks(plate, loads)

    assert len(checks) > 0
    assert all(hasattr(c, "name") for c in checks)
    assert all(hasattr(c, "pass") for c in checks)


def test_pole_filter_empty_if_no_sections():
    """Test pole filter returns empty list when no sections provided."""
    mu = 100.0 * 12  # kip-in
    prefs = {"family": "HSS", "steel_grade": "A500B", "sort_by": "Sx"}

    result = filter_poles(mu, [], prefs)

    assert result == []


def test_all_solvers_deterministic():
    """Smoke test: all solvers should produce consistent results."""
    site = SiteLoads(wind_speed_mph=115.0)
    cabinets = [Cabinet(width_ft=14.0, height_ft=8.0)]

    derived1 = derive_loads(site, cabinets, 25.0)
    derived2 = derive_loads(site, cabinets, 25.0)

    assert derived1.mu_kipft == derived2.mu_kipft
    assert derived1.a_ft2 == derived2.a_ft2

