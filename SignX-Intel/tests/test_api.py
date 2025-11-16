"""Test API endpoints."""
import pytest
from httpx import AsyncClient
from signx_intel.api.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "signx-intel"


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data


@pytest.mark.asyncio
async def test_predict_endpoint():
    """Test prediction endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/predict",
            json={
                "drivers": {
                    "sign_height_ft": 25,
                    "sign_area_sqft": 120,
                    "foundation_type": "drilled_pier"
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "predicted_cost" in data
        assert "confidence_score" in data
        assert float(data["predicted_cost"]) > 0

