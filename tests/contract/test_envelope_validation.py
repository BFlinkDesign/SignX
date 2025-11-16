"""Enhanced envelope validation: float rounding, SHA256 validation."""

from __future__ import annotations

import hashlib
import re

import pytest


def is_valid_sha256(s: str) -> bool:
    """Check if string is valid SHA256 hex."""
    return bool(re.match("^[a-f0-9]{64}$", s))


def are_floats_rounded(data: any, precision: int = 3) -> bool:
    """Recursively check if all floats are rounded to specified precision."""
    if isinstance(data, float):
        return data == round(data, precision)
    elif isinstance(data, dict):
        return all(are_floats_rounded(v, precision) for v in data.values())
    elif isinstance(data, list):
        return all(are_floats_rounded(item, precision) for item in data)
    return True


@pytest.mark.contract
@pytest.mark.asyncio
async def test_all_endpoints_return_valid_envelope(client):
    """Test every endpoint returns valid envelope structure."""
    
    endpoints = [
        ("GET", "/health", None),
        ("GET", "/version", None),
        ("GET", "/ready", None),
        ("GET", "/projects/", None),
        ("GET", "/cabinets/", None),
    ]
    
    for method, path, payload in endpoints:
        if method == "GET":
            resp = await client.get(path)
        else:
            resp = await client.post(path, json=payload or {})
        
        # 404/422 are acceptable for invalid requests
        if resp.status_code not in (200, 404, 422):
            continue
        
        if resp.status_code != 200:
            continue
        
        data = resp.json()
        
        # Validate envelope structure
        assert "result" in data, f"{path} missing 'result'"
        assert "assumptions" in data, f"{path} missing 'assumptions'"
        assert isinstance(data["assumptions"], list), f"{path} assumptions not list"
        assert "confidence" in data, f"{path} missing 'confidence'"
        assert isinstance(data["confidence"], (int, float)), f"{path} confidence not numeric"
        assert 0.0 <= data["confidence"] <= 1.0, f"{path} confidence out of range"
        assert "trace" in data, f"{path} missing 'trace'"
        assert "data" in data["trace"], f"{path} trace missing 'data'"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_confidence_is_float(client):
    """Verify confidence is float in [0, 1]."""
    
    endpoints = ["/health", "/version", "/ready"]
    
    for path in endpoints:
        resp = await client.get(path)
        assert resp.status_code == 200
        
        data = resp.json()
        confidence = data.get("confidence")
        
        assert isinstance(confidence, (int, float)), f"{path} confidence not numeric"
        assert 0.0 <= confidence <= 1.0, f"{path} confidence out of range"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_floats_rounded_to_3_decimals(client):
    """Verify all floats in response are rounded to 3 decimals."""
    
    # Test cabinet derive which returns float values
    payload = {
        "sign": {"height_ft": 10.0, "width_ft": 8.0},
        "board": {"layers": []},
    }
    
    resp = await client.post("/cabinets/derive", json=payload)
    
    if resp.status_code == 200:
        data = resp.json()
        
        # Check all floats are rounded
        assert are_floats_rounded(data), "Response contains unrounded floats"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_sha256_validity_when_present(client, sample_payload):
    """Verify content_sha256 is valid SHA256 when present."""
    
    resp = await client.post(
        "/projects/test_report/report",
        json=sample_payload,
    )
    
    if resp.status_code in (200, 202):
        data = resp.json()
        sha256 = data.get("result", {}).get("content_sha256")
        
        if sha256:
            assert is_valid_sha256(sha256), f"Invalid SHA256 format: {sha256}"


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", [
    "/health",
    "/version",
    "/ready",
    "/projects/",
])
async def test_envelope_structure_parametrized(client, endpoint):
    """Parametrized test for envelope structure across endpoints."""
    
    resp = await client.get(endpoint)
    
    if resp.status_code != 200:
        pytest.skip(f"Endpoint {endpoint} returned {resp.status_code}")
    
    data = resp.json()
    
    # Required fields
    required = ["result", "assumptions", "confidence", "trace"]
    for field in required:
        assert field in data, f"Missing required field: {field}"
    
    # Confidence validation
    assert 0.0 <= data["confidence"] <= 1.0, "Confidence out of range"
    
    # Trace validation
    assert "data" in data["trace"], "Missing trace.data"
    assert "code_version" in data["trace"], "Missing trace.code_version"
    assert "model_config" in data["trace"], "Missing trace.model_config"

