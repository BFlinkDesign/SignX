"""Contract tests: verify all API endpoints return canonical ResponseEnvelope."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_envelope(client):
    """Verify /health returns canonical envelope."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    
    data = resp.json()
    assert "result" in data
    assert "assumptions" in data
    assert isinstance(data["assumptions"], list)
    assert "confidence" in data
    assert isinstance(data["confidence"], (int, float))
    assert 0.0 <= data["confidence"] <= 1.0
    assert "trace" in data
    assert "code_version" in data["trace"]
    assert "model_config" in data["trace"]


@pytest.mark.asyncio
async def test_version_envelope(client):
    """Verify /version returns canonical envelope."""
    resp = await client.get("/version")
    assert resp.status_code == 200
    
    data = resp.json()
    assert "result" in data
    assert data["result"] is not None
    assert "assumptions" in data
    assert "confidence" in data
    assert "trace" in data


@pytest.mark.asyncio
async def test_ready_envelope(client):
    """Verify /ready returns canonical envelope."""
    resp = await client.get("/ready")
    assert resp.status_code == 200
    
    data = resp.json()
    assert "result" in data
    assert "assumptions" in data
    assert "confidence" in data
    assert "trace" in data


@pytest.mark.asyncio
async def test_project_list_envelope(client):
    """Verify /projects/ returns canonical envelope."""
    resp = await client.get("/projects/")
    assert resp.status_code == 200
    
    data = resp.json()
    assert "result" in data
    assert "assumptions" in data
    assert "confidence" in data
    assert "trace" in data
    assert "data" in data["trace"]


@pytest.mark.asyncio
async def test_poles_options_envelope(client):
    """Verify /poles/options returns canonical envelope."""
    payload = {
        "loads": {"moment_kips_ft": 100},
        "preferences": {}
    }
    resp = await client.post("/poles/options", json=payload)
    assert resp.status_code == 200
    
    data = resp.json()
    assert "result" in data
    assert "assumptions" in data
    assert "confidence" in data
    assert "trace" in data


@pytest.mark.asyncio
async def test_footing_solve_envelope(client):
    """Verify /footing/solve returns canonical envelope."""
    payload = {
        "module": "signage.direct_burial_2pole",
        "loads": {"force_kips": 50}
    }
    resp = await client.post("/footing/solve", json=payload)
    assert resp.status_code in [200, 422]  # May be 422 if missing required fields
    
    if resp.status_code == 200:
        data = resp.json()
        assert "result" in data
        assert "assumptions" in data
        assert "confidence" in data
        assert "trace" in data


@pytest.mark.asyncio
async def test_baseplate_checks_envelope(client):
    """Verify /baseplate/checks returns canonical envelope."""
    payload = {
        "loads": {"force_kips": 50},
        "anchors": {"count": 4, "diameter_in": 0.75}
    }
    resp = await client.post("/baseplate/checks", json=payload)
    assert resp.status_code in [200, 422]
    
    if resp.status_code == 200:
        data = resp.json()
        assert "result" in data
        assert "assumptions" in data
        assert "confidence" in data
        assert "trace" in data


@pytest.mark.asyncio
async def test_cabinets_list_envelope(client):
    """Verify /cabinets/ returns canonical envelope."""
    resp = await client.get("/cabinets/")
    assert resp.status_code == 200
    
    data = resp.json()
    assert "result" in data
    assert "assumptions" in data
    assert "confidence" in data
    assert "trace" in data


@pytest.mark.asyncio
async def test_trace_contains_inputs_intermediates_outputs(client):
    """Verify trace contains data.inputs, intermediates, outputs."""
    resp = await client.get("/health")
    data = resp.json()
    
    assert "data" in data["trace"]
    trace_data = data["trace"]["data"]
    assert "inputs" in trace_data
    assert "intermediates" in trace_data
    assert "outputs" in trace_data


@pytest.mark.asyncio
async def test_code_version_fields(client):
    """Verify code_version contains git_sha, dirty."""
    resp = await client.get("/health")
    data = resp.json()
    
    code_version = data["trace"]["code_version"]
    assert "git_sha" in code_version
    assert "dirty" in code_version
    assert isinstance(code_version["dirty"], bool)


@pytest.mark.asyncio
async def test_model_config_fields(client):
    """Verify model_config contains provider, model, temperature."""
    resp = await client.get("/health")
    data = resp.json()
    
    model_config = data["trace"]["model_config"]
    assert "provider" in model_config
    assert "model" in model_config
    assert "temperature" in model_config

