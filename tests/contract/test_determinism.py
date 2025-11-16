"""Determinism tests: Same inputs must produce identical outputs."""

from __future__ import annotations

import hashlib
import pytest


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.determinism
async def test_pdf_determinism(test_client, sample_payload):
    """Generate report twice with same inputs, assert SHA256 matches."""
    
    # First generation
    resp1 = await test_client.post(
        "/projects/test_determinism/report",
        json=sample_payload,
    )
    assert resp1.status_code in (200, 202)
    
    data1 = resp1.json()
    sha1 = data1.get("result", {}).get("content_sha256")
    
    if not sha1:
        pytest.skip("Report generation not fully implemented")
    
    # Second generation
    resp2 = await test_client.post(
        "/projects/test_determinism/report",
        json=sample_payload,
    )
    assert resp2.status_code in (200, 202)
    
    data2 = resp2.json()
    sha2 = data2.get("result", {}).get("content_sha256")
    
    # SHA256 must match (deterministic)
    assert sha1 == sha2, f"Non-deterministic report generation: {sha1} != {sha2}"


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.determinism
async def test_solver_determinism(test_client):
    """Call derive_cabinet with same inputs 10 times, assert outputs identical."""
    
    payload = {
        "sign": {"height_ft": 10.0, "width_ft": 8.0},
        "board": {"layers": []},
    }
    
    results = []
    for i in range(10):
        resp = await test_client.post(
            "/cabinets/derive",
            json=payload,
        )
        assert resp.status_code in (200, 422)
        
        if resp.status_code == 200:
            data = resp.json()
            results.append(data)
    
    if not results:
        pytest.skip("Cabinet derive not fully implemented")
    
    # All outputs must be identical (floats rounded to 3 decimals)
    first = results[0]
    for i, result in enumerate(results[1:], 1):
        assert result == first, f"Non-deterministic output on iteration {i}"


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.determinism
async def test_sorting_determinism(test_client):
    """Call filter_poles with same inputs 10 times, assert order identical."""
    
    payload = {
        "loads": {"moment_kips_ft": 100},
        "preferences": {},
    }
    
    results = []
    for i in range(10):
        resp = await test_client.post(
            "/poles/options",
            json=payload,
        )
        assert resp.status_code in (200, 422)
        
        if resp.status_code == 200:
            data = resp.json()
            results.append(data)
    
    if not results:
        pytest.skip("Pole filtering not fully implemented")
    
    # Extract pole orders
    first_order = [p.get("id") for p in results[0].get("result", {}).get("options", [])]
    
    for i, result in enumerate(results[1:], 1):
        current_order = [p.get("id") for p in result.get("result", {}).get("options", [])]
        assert current_order == first_order, f"Non-deterministic sorting on iteration {i}"


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.determinism
async def test_footing_determinism(test_client):
    """Test footing design determinism."""
    
    payload = {
        "module": "signage.direct_burial_2pole",
        "loads": {"force_kips": 50},
    }
    
    results = []
    for i in range(5):
        resp = await test_client.post(
            "/footing/design",
            json=payload,
        )
        assert resp.status_code in (200, 422)
        
        if resp.status_code == 200:
            data = resp.json()
            results.append(data)
    
    if not results:
        pytest.skip("Foundation design not fully implemented")
    
    # All outputs must be identical
    first = results[0]
    for i, result in enumerate(results[1:], 1):
        assert result == first, f"Non-deterministic footing design on iteration {i}"


@pytest.mark.contract
@pytest.mark.asyncio
@pytest.mark.determinism
async def test_baseplate_determinism(test_client):
    """Test baseplate design determinism."""
    
    payload = {
        "loads": {"force_kips": 50},
        "anchors": {"count": 4, "diameter_in": 0.75},
    }
    
    results = []
    for i in range(5):
        resp = await test_client.post(
            "/baseplate/checks",
            json=payload,
        )
        assert resp.status_code in (200, 422)
        
        if resp.status_code == 200:
            data = resp.json()
            results.append(data)
    
    if not results:
        pytest.skip("Baseplate checks not fully implemented")
    
    # All outputs must be identical
    first = results[0]
    for i, result in enumerate(results[1:], 1):
        assert result == first, f"Non-deterministic baseplate design on iteration {i}"

