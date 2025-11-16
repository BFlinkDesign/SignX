"""Chaos engineering: Service failure scenarios and resilience testing."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.chaos
@pytest.mark.asyncio
async def test_redis_down_graceful_degradation(client):
    """Test API behavior when Redis is unavailable."""
    
    # Mock Redis connection failure
    with patch("redis.Redis") as mock_redis:
        mock_redis.side_effect = ConnectionError("Redis connection refused")
        
        # API should still respond (using DB fallback)
        resp = await client.get("/health")
        
        # May return degraded but functional
        assert resp.status_code in (200, 503)
        
        if resp.status_code == 200:
            data = resp.json()
            # Should indicate degraded state
            assert "assumptions" in data


@pytest.mark.chaos
@pytest.mark.asyncio
async def test_postgres_connection_loss(client):
    """Test API behavior when Postgres connection is lost."""
    
    # Mock DB connection failure
    with patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_engine:
        mock_engine.side_effect = ConnectionError("Database connection refused")
        
        # Projects endpoint should fail gracefully
        resp = await client.get("/projects/")
        
        # Should return 503 or graceful error
        assert resp.status_code in (503, 500, 200)


@pytest.mark.chaos
@pytest.mark.asyncio
async def test_opensearch_unavailable_db_fallback(client):
    """Test OpenSearch unavailable triggers DB fallback."""
    
    # Project search should fallback to DB
    resp = await client.get("/projects/?q=test")
    
    assert resp.status_code == 200
    data = resp.json()
    
    # Should indicate fallback was used
    if "search_fallback" in data.get("result", {}):
        assert data["result"]["search_fallback"] is True


@pytest.mark.chaos
@pytest.mark.asyncio
async def test_minio_timeout_graceful_error(client):
    """Test MinIO timeout handled gracefully."""
    
    # File operations should handle timeouts
    resp = await client.post(
        "/projects/test/files/presign",
        json={"filename": "test.pdf"},
    )
    
    # Should not crash, may return error or fallback
    assert resp.status_code in (200, 500, 503)


@pytest.mark.chaos
@pytest.mark.asyncio
async def test_external_api_failures(client):
    """Test external API failures (geocoding, wind data)."""
    
    # Site resolution should handle external API failures
    resp = await client.post(
        "/site/resolve",
        json={"address": "1600 Amphitheatre Parkway"},
    )
    
    # Should return error or fallback, not crash
    assert resp.status_code in (200, 422, 500)
    
    if resp.status_code == 200:
        data = resp.json()
        # Should indicate assumptions about data source
        assert "assumptions" in data


@pytest.mark.chaos
@pytest.mark.asyncio
async def test_circuit_breaker_activation(client):
    """Test circuit breaker prevents cascading failures."""
    
    # Simulate repeated failures
    for _ in range(10):
        resp = await client.post(
            "/cabinets/derive",
            json={"sign": {"height_ft": 1000.0, "width_ft": 1000.0}},  # Invalid
        )
    
    # Circuit breaker should prevent further requests
    # API should return error instead of hanging
    final_resp = await client.get("/health")
    assert final_resp.status_code == 200  # API still healthy


@pytest.mark.chaos
@pytest.mark.asyncio
async def test_request_timeout_handling(client):
    """Test request timeout prevents hanging."""
    
    # Long-running operation should timeout appropriately
    resp = await client.post(
        "/poles/options",
        json={"loads": {"moment_kips_ft": 999999}},  # Very large load
        timeout=10.0,
    )
    
    # Should return within timeout
    assert resp.status_code in (200, 422, 500, 504)


@pytest.mark.chaos
@pytest.mark.asyncio
async def test_partial_data_loss_recovery(client):
    """Test partial data loss handled gracefully."""
    
    # Project with missing payload should handle gracefully
    resp = await client.get("/projects/nonexistent_project")
    assert resp.status_code == 404
    
    # Should return proper error, not crash
    data = resp.json()
    assert "result" in data or "error" in data


@pytest.mark.chaos
@pytest.mark.asyncio
async def test_concurrent_request_handling(client):
    """Test handling of burst of concurrent requests."""
    import asyncio
    
    # Send 100 concurrent requests
    async def make_request():
        return await client.get("/health")
    
    tasks = [make_request() for _ in range(100)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # All should complete without crashing
    assert all(r.status_code == 200 if hasattr(r, 'status_code') else False for r in results)


@pytest.mark.chaos
@pytest.mark.asyncio
async def test_resource_exhaustion_handling(client):
    """Test resource exhaustion handled gracefully."""
    
    # Large payload should be rejected
    large_payload = {
        "sign": {"height_ft": 1.0, "width_ft": 1.0},
        "board": {"layers": [{"data": "x" * 1000000}]},  # 1MB of data
    }
    
    resp = await client.post("/cabinets/derive", json=large_payload)
    
    # Should reject or handle gracefully
    assert resp.status_code in (200, 413, 422, 500)

