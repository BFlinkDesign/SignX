"""Load tests for API endpoints using pytest-benchmark."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def client():
    """Async test client."""
    from apex.api.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


async def test_health_endpoint_benchmark(client: AsyncClient, benchmark):
    """Benchmark health endpoint."""
    def _call():
        import asyncio
        return asyncio.run(client.get("/health"))
    
    result = benchmark(_call)
    assert result.status_code == 200


async def test_projects_list_benchmark(client: AsyncClient, benchmark):
    """Benchmark projects list endpoint."""
    def _call():
        import asyncio
        return asyncio.run(client.get("/projects?limit=10"))
    
    result = benchmark(_call)
    assert result.status_code in [200, 401, 403]  # May require auth


@pytest.mark.parametrize("endpoint", [
    "/signage/common/poles/options",
    "/utilities/concrete/yards",
])
async def test_query_endpoints_benchmark(client: AsyncClient, endpoint, benchmark):
    """Benchmark query endpoints (should be fast with caching)."""
    # Simple payload
    payload = {
        "poles/options": {
            "loads": {"M_kipin": 100},
            "prefs": {"family": ["pipe"]},
            "material": "steel",
            "height_ft": 20,
            "num_poles": 1,
        },
        "concrete/yards": {
            "diameter_ft": 3.0,
            "depth_ft": 6.0,
        },
    }[endpoint.split("/")[-1]]
    
    def _call():
        import asyncio
        return asyncio.run(client.post(endpoint, json=payload))
    
    result = benchmark(_call)
    # Should be fast (<100ms for cached results)
    assert result.status_code == 200

