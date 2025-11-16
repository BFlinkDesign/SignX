"""Integration tests for AI/ML prediction endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# Note: These tests require a trained model at models/cost/v1/
# Skip if model not available


@pytest.fixture
def client():
    """Create test client."""
    from apex.api.main import app
    return TestClient(app)


def test_predict_cost_endpoint_valid_request(client):
    """Test cost prediction with valid request."""
    request_data = {
        "height_ft": 25.0,
        "sign_area_sqft": 80.0,
        "wind_speed_mph": 115.0,
        "exposure_category": "C",
        "pole_size": 8.0,
        "pole_type": "round_hss",
        "foundation_type": "direct_burial",
        "embedment_depth_ft": 8.0,
    }
    
    response = client.post("/ai/predict-cost", json=request_data)
    
    # May return 503 if model not trained - that's okay for this test
    if response.status_code == 503:
        pytest.skip("Model not loaded - train model first")
    
    assert response.status_code == 200
    
    # Check envelope structure
    data = response.json()
    assert "result" in data
    assert "assumptions" in data
    assert "confidence" in data
    assert "trace" in data
    
    # Check prediction structure
    result = data["result"]
    assert "predicted_cost" in result
    assert "confidence_interval_90" in result
    assert "model_version" in result
    
    # Check reasonable values
    assert result["predicted_cost"] > 0
    assert isinstance(result["confidence_interval_90"], list)
    assert len(result["confidence_interval_90"]) == 2


def test_predict_cost_validation_errors(client):
    """Test that invalid requests are rejected."""
    invalid_requests = [
        # Negative height
        {"height_ft": -5, "sign_area_sqft": 80, "wind_speed_mph": 115, "exposure_category": "C"},
        # Invalid exposure
        {"height_ft": 25, "sign_area_sqft": 80, "wind_speed_mph": 115, "exposure_category": "X"},
        # Missing required fields
        {"height_ft": 25},
    ]
    
    for req in invalid_requests:
        response = client.post("/ai/predict-cost", json=req)
        assert response.status_code == 422  # Validation error


def test_model_info_endpoint(client):
    """Test model info endpoint."""
    response = client.get("/ai/model-info")
    
    # May return 503 if model not loaded
    if response.status_code == 503:
        pytest.skip("Model not loaded")
    
    assert response.status_code == 200
    
    data = response.json()
    assert "result" in data
    
    result = data["result"]
    assert "model_type" in result
    assert "version" in result
    assert "n_features" in result


def test_ai_endpoints_return_envelope_format(client):
    """Verify AI endpoints follow APEX envelope pattern."""
    request_data = {
        "height_ft": 20.0,
        "sign_area_sqft": 60.0,
        "wind_speed_mph": 115.0,
        "exposure_category": "C",
        "pole_size": 8.0,
    }
    
    response = client.post("/ai/predict-cost", json=request_data)
    
    if response.status_code == 503:
        pytest.skip("Model not loaded")
    
    data = response.json()
    
    # Verify envelope structure
    required_keys = {"result", "assumptions", "confidence", "trace"}
    assert set(data.keys()) == required_keys
    
    # Verify trace structure
    trace = data["trace"]
    assert "data" in trace
    assert "code_version" in trace
    assert "model_config" in trace
    
    # Verify trace data
    trace_data = trace["data"]
    assert "inputs" in trace_data
    assert "outputs" in trace_data

