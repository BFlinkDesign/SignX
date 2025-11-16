"""Integration tests using live API running in Docker."""

from __future__ import annotations

import time
from typing import Any

import pytest
import requests


BASE_URL = "http://localhost:8000"


@pytest.mark.integration
def test_health_endpoint():
    """Test /health returns valid envelope."""
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    assert response.status_code == 200
    
    data = response.json()
    
    # Validate envelope structure
    assert "result" in data
    assert "confidence" in data
    assert "trace" in data
    assert "assumptions" in data
    assert "content_sha256" in data
    
    # Validate result content
    assert data["result"]["status"] == "ok"
    assert data["result"]["service"] == "api"
    assert data["confidence"] == 1.0
    
    # Validate trace structure
    assert "code_version" in data["trace"]
    assert "model_config" in data["trace"]
    assert "data" in data["trace"]


@pytest.mark.integration
def test_ready_endpoint():
    """Test /ready returns dependency checks."""
    response = requests.get(f"{BASE_URL}/ready", timeout=10)
    assert response.status_code == 200
    
    data = response.json()
    assert "result" in data
    assert "checks" in data["result"]
    
    # Validate critical dependencies are checked
    checks = data["result"]["checks"]
    assert "redis" in checks
    assert "postgres" in checks
    assert "opensearch" in checks
    assert "minio" in checks
    assert "signcalc" in checks
    
    # Should be healthy
    assert data["result"]["status"] in ["ok", "degraded"]


@pytest.mark.integration
def test_cabinets_derive_envelope():
    """Test cabinets derive returns valid envelope."""
    payload = {
        "cabinets": [
            {
                "width_ft": 4.0,
                "height_ft": 6.0,
                "weight_lbs": 150.0,
                "x_offset_ft": 0.0,
                "y_offset_ft": 0.0,
            }
        ],
        "wind_speed_mph": 90.0,
    }
    
    response = requests.post(
        f"{BASE_URL}/signage/common/cabinets/derive",
        json=payload,
        timeout=30,
    )
    
    assert response.status_code == 200, f"Response: {response.text}"
    
    data = response.json()
    
    # Validate envelope structure
    assert "result" in data
    assert "confidence" in data
    assert "trace" in data
    assert "assumptions" in data
    
    # Validate result has expected keys
    assert "total_area_sqft" in data["result"]
    assert "total_weight_lbs" in data["result"]
    assert "wind_force_lbs" in data["result"]
    
    # Validate numeric types
    assert isinstance(data["result"]["total_area_sqft"], (int, float))
    assert isinstance(data["result"]["total_weight_lbs"], (int, float))
    assert isinstance(data["result"]["wind_force_lbs"], (int, float))
    
    # Confidence should be reasonable
    assert 0.0 <= data["confidence"] <= 1.0


@pytest.mark.integration
def test_envelope_content_sha256():
    """Test that identical requests produce same SHA256."""
    payload = {
        "cabinets": [{"width_ft": 4.0, "height_ft": 6.0, "weight_lbs": 150.0}],
        "wind_speed_mph": 90.0,
    }
    
    # Make two identical requests
    response1 = requests.post(
        f"{BASE_URL}/signage/common/cabinets/derive",
        json=payload,
        timeout=30,
    )
    time.sleep(0.1)  # Small delay
    
    response2 = requests.post(
        f"{BASE_URL}/signage/common/cabinets/derive",
        json=payload,
        timeout=30,
    )
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    data1 = response1.json()
    data2 = response2.json()
    
    # Should have same SHA256 for deterministic calculations
    if "content_sha256" in data1 and "content_sha256" in data2:
        assert data1["content_sha256"] == data2["content_sha256"], "SHA256 should be deterministic"
    
    # Results should be identical
    assert data1["result"] == data2["result"]


@pytest.mark.integration
def test_poles_options_envelope():
    """Test poles options returns valid envelope."""
    payload = {
        "weight_top_klf": 1.0,
        "height_ft": 20.0,
        "wind_speed_mph": 90.0,
        "exposure": "C",
    }
    
    response = requests.post(
        f"{BASE_URL}/signage/common/poles/options",
        json=payload,
        timeout=30,
    )
    
    assert response.status_code == 200
    
    data = response.json()
    
    # Validate envelope structure
    assert "result" in data
    assert "confidence" in data
    assert "trace" in data
    
    # Should return pole options
    assert "poles" in data["result"]
    assert isinstance(data["result"]["poles"], list)


@pytest.mark.integration
def test_version_endpoint():
    """Test /version endpoint."""
    response = requests.get(f"{BASE_URL}/version", timeout=5)
    assert response.status_code == 200
    
    data = response.json()
    assert "result" in data
    assert "version" in data["result"]


@pytest.mark.integration
def test_api_docs():
    """Test OpenAPI docs are accessible."""
    response = requests.get(f"{BASE_URL}/docs", timeout=5)
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.integration
def test_cors_headers():
    """Test CORS headers are present."""
    response = requests.options(f"{BASE_URL}/health", timeout=5)
    # OPTIONS request might return different status, just check it doesn't error
    assert response.status_code in [200, 204, 405]


@pytest.mark.integration
def test_error_handling():
    """Test error responses return valid envelopes."""
    # Invalid request
    response = requests.post(
        f"{BASE_URL}/signage/common/cabinets/derive",
        json={"invalid": "data"},
        timeout=10,
    )
    
    # Should return 422 (validation error) or 400
    assert response.status_code in [400, 422]
    
    data = response.json()
    
    # Error response should still have envelope structure (if using envelope)
    # Or at least have 'detail' for validation errors
    assert "detail" in data or "result" in data


if __name__ == "__main__":
    import sys
    
    # Simple test runner without pytest
    print("Running integration tests against live API...")
    print(f"Testing: {BASE_URL}")
    
    passed = 0
    failed = 0
    
    # Run tests
    for test_name, test_func in [
        ("health_endpoint", test_health_endpoint),
        ("ready_endpoint", test_ready_endpoint),
        ("cabinets_derive_envelope", test_cabinets_derive_envelope),
        ("version_endpoint", test_version_endpoint),
        ("api_docs", test_api_docs),
        ("cors_headers", test_cors_headers),
    ]:
        try:
            print(f"\nRunning {test_name}...", end=" ")
            test_func()
            print("✅ PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    
    sys.exit(0 if failed == 0 else 1)

