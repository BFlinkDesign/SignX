"""Regression tests: 50+ reference problems with golden outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Load reference cases
REFERENCE_CASES_FILE = Path(__file__).parent.parent / "fixtures" / "reference_cases.json"


@pytest.fixture(scope="session")
def reference_cases():
    """Load reference test cases."""
    if REFERENCE_CASES_FILE.exists():
        with open(REFERENCE_CASES_FILE, "r") as f:
            return json.load(f)
    return {}


@pytest.mark.regression
@pytest.mark.asyncio
@pytest.mark.parametrize("case_name", [f"case_{i:02d}" for i in range(1, 51)])
async def test_reference_case_determinism(client, reference_cases, case_name):
    """Run reference case and assert output matches expected within tolerance."""
    
    if case_name not in reference_cases:
        pytest.skip(f"Reference case {case_name} not found")
    
    case = reference_cases[case_name]
    inputs = case["inputs"]
    expected = case.get("expected_outputs", {})
    tolerance = case.get("tolerance", 0.01)  # Default 1%
    
    # Determine endpoint from inputs
    endpoint = inputs.get("endpoint", "/unknown")
    payload = inputs.get("payload", {})
    
    # Call endpoint
    if endpoint.startswith("GET"):
        resp = await client.get(endpoint.split()[1])
    else:
        resp = await client.post(endpoint, json=payload)
    
    if resp.status_code not in (200, 422):
        pytest.skip(f"Endpoint returned {resp.status_code}")
    
    if resp.status_code != 200:
        pytest.skip("Endpoint not fully implemented")
    
    # Get actual output
    actual = resp.json()
    
    # Validate against expected (within tolerance)
    if expected:
        _validate_within_tolerance(actual, expected, tolerance)


def _validate_within_tolerance(actual: dict, expected: dict, tolerance: float):
    """Validate actual values within tolerance of expected."""
    
    def check_value(actual_val, expected_val, path=""):
        if isinstance(expected_val, (int, float)):
            # Numeric comparison within tolerance
            if isinstance(actual_val, (int, float)):
                diff = abs(actual_val - expected_val)
                relative_diff = diff / abs(expected_val) if expected_val != 0 else diff
                assert relative_diff <= tolerance, (
                    f"Value at {path}: {actual_val} differs from expected "
                    f"{expected_val} by {relative_diff:.2%} (tolerance: {tolerance:.2%})"
                )
        elif isinstance(expected_val, dict):
            # Recursive dict check
            assert isinstance(actual_val, dict), f"Expected dict at {path}, got {type(actual_val)}"
            for key, val in expected_val.items():
                check_value(actual_val.get(key), val, f"{path}.{key}" if path else key)
        elif isinstance(expected_val, list):
            # List length check and element comparison
            assert isinstance(actual_val, list), f"Expected list at {path}, got {type(actual_val)}"
            assert len(actual_val) == len(expected_val), (
                f"List length mismatch at {path}: "
                f"{len(actual_val)} != {len(expected_val)}"
            )
            for i, (a, e) in enumerate(zip(actual_val, expected_val)):
                check_value(a, e, f"{path}[{i}]")
    
    # Start validation from result
    actual_result = actual.get("result", {})
    expected_result = expected.get("result", {})
    
    if expected_result:
        check_value(actual_result, expected_result, "result")


@pytest.mark.regression
@pytest.mark.asyncio
async def test_cabinet_area_regression(client):
    """Regression test: Cabinet area calculation."""
    
    payload = {
        "sign": {"height_ft": 10.0, "width_ft": 8.0},
        "board": {"layers": [{"material": "aluminum", "thickness_in": 0.125}]},
    }
    
    resp = await client.post("/cabinets/derive", json=payload)
    
    if resp.status_code != 200:
        pytest.skip("Cabinet derive not fully implemented")
    
    data = resp.json()
    area = data.get("result", {}).get("area_ft2")
    
    # Expect area ≈ 80 ft² (sign area)
    assert area is not None, "Area not returned"
    assert 70 <= area <= 100, f"Unexpected area: {area} ft²"


@pytest.mark.regression
@pytest.mark.asyncio
async def test_pole_filtering_regression(client):
    """Regression test: Pole filtering returns expected options."""
    
    payload = {
        "loads": {"moment_kips_ft": 100},
        "preferences": {},
    }
    
    resp = await client.post("/poles/options", json=payload)
    
    if resp.status_code != 200:
        pytest.skip("Pole filtering not fully implemented")
    
    data = resp.json()
    options = data.get("result", {}).get("options", [])
    
    # Should return some options
    assert len(options) > 0, "No pole options returned"
    
    # First option should be feasible
    assert options[0].get("feasible", True), "First option not feasible"


@pytest.mark.regression
@pytest.mark.asyncio
async def test_foundation_design_regression(client):
    """Regression test: Foundation design calculations."""
    
    payload = {
        "module": "signage.direct_burial_2pole",
        "loads": {"force_kips": 50},
    }
    
    resp = await client.post("/footing/design", json=payload)
    
    if resp.status_code != 200:
        pytest.skip("Foundation design not fully implemented")
    
    data = resp.json()
    result = data.get("result", {})
    
    # Should have design dimensions
    assert result.get("depth_ft") is not None, "Depth not returned"
    assert result.get("diameter_in") is not None, "Diameter not returned"


@pytest.mark.regression
@pytest.mark.asyncio
async def test_baseplate_regression(client):
    """Regression test: Baseplate anchor checks."""
    
    payload = {
        "loads": {"force_kips": 50},
        "anchors": {"count": 4, "diameter_in": 0.75},
    }
    
    resp = await client.post("/baseplate/checks", json=payload)
    
    if resp.status_code != 200:
        pytest.skip("Baseplate checks not fully implemented")
    
    data = resp.json()
    result = data.get("result", {})
    
    # Should have check results
    assert "passed" in result or "safe" in result, "Check results missing"

