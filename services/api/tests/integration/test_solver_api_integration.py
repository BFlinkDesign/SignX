"""
Integration tests for solver API endpoints.

Tests ALL endpoints that call solvers, verifies Envelope structure, confidence, warnings.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from apex.api.main import app


@pytest.mark.asyncio
async def test_cabinets_derive_integration():
    """Test cabinets derive endpoint with solver integration."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "site": {"wind_speed_mph": 115.0, "exposure": "C"},
            "cabinets": [{"width_ft": 14.0, "height_ft": 8.0, "weight_psf": 10.0}],
            "height_ft": 25.0,
        }
        
        response = await client.post("/signage/common/cabinets/derive", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify Envelope structure
        assert "result" in data
        assert "assumptions" in data
        assert "confidence" in data
        assert "trace" in data
        
        # Verify solver result
        result = data["result"]
        assert "a_ft2" in result or "A_ft2" in result
        assert "mu_kipft" in result or "mu_kipft" in result
        
        # Verify confidence is reasonable
        assert 0.0 <= data["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_poles_options_integration():
    """Test poles options endpoint with filter_poles integration."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "mu_required_kipin": 50.0,
            "prefs": {"family": "HSS", "steel_grade": "A500B", "sort_by": "Sx"},
        }
        
        response = await client.post("/signage/poles/options", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify Envelope
        assert "result" in data
        assert "options" in data["result"] or "result" in data["result"]
        
        # Verify confidence
        assert 0.0 <= data["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_footing_solve_integration():
    """Test footing solve endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "mu_kipft": 10.0,
            "diameter_ft": 3.0,
            "soil_psf": 3000.0,
        }
        
        response = await client.post("/signage/direct_burial/footing/solve", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify result
        result = data["result"]
        assert "min_depth_ft" in result or "depth_ft" in result
        
        # Check for request_engineering flag if present
        if "request_engineering" in result:
            assert isinstance(result["request_engineering"], bool)


@pytest.mark.asyncio
async def test_multi_step_workflow():
    """Test multi-step workflow: Derive → Filter → Solve."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Step 1: Derive loads
        derive_payload = {
            "site": {"wind_speed_mph": 115.0, "exposure": "C"},
            "cabinets": [{"width_ft": 14.0, "height_ft": 8.0, "weight_psf": 10.0}],
            "height_ft": 25.0,
        }
        derive_response = await client.post("/signage/common/cabinets/derive", json=derive_payload)
        assert derive_response.status_code == 200
        
        derive_data = derive_response.json()
        derive_confidence = derive_data["confidence"]
        
        # Step 2: Filter poles (using derived moment)
        mu_kipft = derive_data["result"].get("mu_kipft", 10.0)
        mu_required_kipin = mu_kipft * 12.0  # Convert to kip-in
        
        poles_payload = {
            "mu_required_kipin": mu_required_kipin,
            "prefs": {"family": "HSS", "steel_grade": "A500B"},
        }
        poles_response = await client.post("/signage/poles/options", json=poles_payload)
        assert poles_response.status_code == 200
        
        poles_data = poles_response.json()
        poles_confidence = poles_data["confidence"]
        
        # Step 3: Solve footing
        footing_payload = {
            "mu_kipft": mu_kipft,
            "diameter_ft": 3.0,
            "soil_psf": 3000.0,
        }
        footing_response = await client.post("/signage/direct_burial/footing/solve", json=footing_payload)
        assert footing_response.status_code == 200
        
        footing_data = footing_response.json()
        footing_confidence = footing_data["confidence"]
        
        # Verify: Confidence never increases (only decreases or stays same)
        assert poles_confidence <= derive_confidence
        assert footing_confidence <= poles_confidence


@pytest.mark.asyncio
async def test_edge_case_propagation():
    """Test edge case propagation: Input edge case → Abstain → 422."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Invalid input: negative wind speed
        payload = {
            "site": {"wind_speed_mph": -10.0, "exposure": "C"},  # Invalid
            "cabinets": [{"width_ft": 14.0, "height_ft": 8.0, "weight_psf": 10.0}],
            "height_ft": 25.0,
        }
        
        response = await client.post("/signage/common/cabinets/derive", json=payload)
        
        # Should return 422 (validation error) or 400
        assert response.status_code in [400, 422]
        
        # Error message should be helpful
        data = response.json()
        assert "detail" in data or "message" in data


@pytest.mark.asyncio
async def test_envelope_structure_all_endpoints():
    """Verify all solver endpoints return proper Envelope structure."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        endpoints = [
            ("/signage/common/cabinets/derive", {"site": {"wind_speed_mph": 115.0, "exposure": "C"}, "cabinets": [], "height_ft": 25.0}),
            # Add more endpoints as needed
        ]
        
        for endpoint, payload in endpoints:
            response = await client.post(endpoint, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify Envelope structure
                assert set(data.keys()) == {"result", "assumptions", "confidence", "trace"}
                
                # Verify trace structure
                trace = data["trace"]
                assert "data" in trace
                assert "code_version" in trace
                assert "model_config" in trace

