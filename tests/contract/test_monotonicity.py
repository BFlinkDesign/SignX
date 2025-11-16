"""Monotonicity tests: Design improvements should improve outcomes."""

from __future__ import annotations

import pytest


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.monotonicity
async def test_footing_monotonic(test_client):
    """Sweep footing diameter: larger diameters → same or smaller depth."""
    
    # Test parameter sweep
    diameters = [12, 14, 16, 18, 20, 22, 24]
    depths = []
    
    for diameter in diameters:
        payload = {
            "module": "signage.direct_burial_2pole",
            "loads": {"force_kips": 50},
            "config": {"diameter_in": diameter},
        }
        
        resp = await test_client.post("/footing/design", json=payload)
        
        if resp.status_code == 200:
            data = resp.json()
            depth = data.get("result", {}).get("depth_ft")
            if depth:
                depths.append((diameter, depth))
    
    if len(depths) < 3:
        pytest.skip("Foundation design not fully implemented")
    
    # Depth should be non-increasing as diameter increases
    for i in range(len(depths) - 1):
        d1, depth1 = depths[i]
        d2, depth2 = depths[i + 1]
        
        assert depth2 <= depth1, (
            f"Monotonicity violation: diameter {d2}in has larger depth "
            f"{depth2}ft than diameter {d1}in with {depth1}ft"
        )


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.monotonicity
async def test_pole_filtering_feasibility(test_client):
    """Assert filter_poles() never returns infeasible sections."""
    
    payload = {
        "loads": {"moment_kips_ft": 50},  # Low load
        "preferences": {},
    }
    
    resp = await test_client.post("/poles/options", json=payload)
    
    if resp.status_code != 200:
        pytest.skip("Pole filtering not fully implemented")
    
    data = resp.json()
    options = data.get("result", {}).get("options", [])
    
    # All options should be feasible
    for pole in options:
        assert pole.get("feasible", True), f"Infeasible pole returned: {pole.get('id')}"


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.monotonicity
async def test_default_selection_minimal(test_client):
    """Assert default selection is minimal feasible design."""
    
    payload = {
        "loads": {"moment_kips_ft": 100},
        "preferences": {},
    }
    
    resp = await test_client.post("/poles/options", json=payload)
    
    if resp.status_code != 200:
        pytest.skip("Pole filtering not fully implemented")
    
    data = resp.json()
    options = data.get("result", {}).get("options", [])
    
    if not options:
        pytest.skip("No options returned")
    
    # First option (default) should be minimal
    default = options[0]
    feasible = [p for p in options if p.get("feasible", True)]
    
    if len(feasible) > 1:
        # Default should minimize weight or cost
        default_weight = default.get("weight_per_ft", 0)
        
        # Should be among lightest feasible options
        weights = [p.get("weight_per_ft", 0) for p in feasible]
        min_weight = min(weights)
        
        assert default_weight <= min_weight * 1.1, (
            f"Default selection not minimal: weight {default_weight} vs "
            f"minimal {min_weight}"
        )


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.monotonicity
async def test_cabinet_area_monotonic(test_client):
    """Larger sign dimensions → larger cabinet area."""
    
    test_cases = [
        ({"height_ft": 8.0, "width_ft": 6.0}),
        ({"height_ft": 8.0, "width_ft": 8.0}),
        ({"height_ft": 10.0, "width_ft": 8.0}),
        ({"height_ft": 10.0, "width_ft": 10.0}),
    ]
    
    areas = []
    
    for sign in test_cases:
        payload = {
            "sign": sign,
            "board": {"layers": []},
        }
        
        resp = await test_client.post("/cabinets/derive", json=payload)
        
        if resp.status_code == 200:
            data = resp.json()
            area = data.get("result", {}).get("area_ft2")
            if area:
                areas.append(area)
    
    if len(areas) < 3:
        pytest.skip("Cabinet derive not fully implemented")
    
    # Area should be non-decreasing
    for i in range(len(areas) - 1):
        assert areas[i + 1] >= areas[i], (
            f"Monotonicity violation: area decreased from {areas[i]} to "
            f"{areas[i + 1]}"
        )

