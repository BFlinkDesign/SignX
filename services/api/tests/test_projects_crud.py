from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_projects_list_envelope(client: AsyncClient):
    """Test projects list returns valid envelope."""
    r = await client.get("/projects")
    assert r.status_code == 200
    data = r.json()
    
    # Envelope structure
    assert set(data.keys()) == {"result", "assumptions", "confidence", "trace"}
    assert 0.0 <= float(data["confidence"]) <= 1.0
    assert isinstance(data["assumptions"], list)
    assert isinstance(data["result"], dict)
    
    # Result structure
    result = data["result"]
    assert "projects" in result
    assert "count" in result
    assert isinstance(result["projects"], list)
    assert result["count"] == len(result["projects"])


@pytest.mark.asyncio
async def test_projects_create_envelope(client: AsyncClient):
    """Test project creation returns valid envelope with project_id."""
    payload = {
        "account_id": "test-account",
        "name": "Test Project",
        "customer": "Test Customer",
        "created_by": "test-user",
    }
    
    r = await client.post("/projects", json=payload)
    assert r.status_code == 200
    data = r.json()
    
    # Envelope
    assert set(data.keys()) == {"result", "assumptions", "confidence", "trace"}
    assert data["confidence"] == 1.0
    
    # Result
    result = data["result"]
    assert "project_id" in result
    assert result["name"] == "Test Project"
    assert result["status"] == "draft"
    assert "created_at" in result
    
    # Trace
    trace = data["trace"]
    assert "code_version" in trace
    assert "model_config" in trace
    assert trace["data"]["inputs"]["name"] == "Test Project"


@pytest.mark.asyncio
async def test_projects_get_envelope(client: AsyncClient, test_project_id: str):
    """Test project get returns valid envelope."""
    r = await client.get(f"/projects/{test_project_id}")
    assert r.status_code == 200
    data = r.json()
    
    assert set(data.keys()) == {"result", "assumptions", "confidence", "trace"}
    result = data["result"]
    assert result["project_id"] == test_project_id
    assert "status" in result


@pytest.mark.asyncio
async def test_projects_get_404(client: AsyncClient):
    """Test project get returns 404 for missing project."""
    r = await client.get("/projects/nonexistent-id")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_projects_events_envelope(client: AsyncClient, test_project_id: str):
    """Test project events returns valid envelope."""
    r = await client.get(f"/projects/{test_project_id}/events")
    assert r.status_code == 200
    data = r.json()
    
    assert set(data.keys()) == {"result", "assumptions", "confidence", "trace"}
    result = data["result"]
    assert "events" in result
    assert "count" in result
    assert isinstance(result["events"], list)
    assert result["count"] == len(result["events"])


@pytest.fixture
async def test_project_id(client: AsyncClient) -> str:
    """Create a test project and return its ID."""
    payload = {
        "account_id": "test-account",
        "name": "Test Project for Events",
        "created_by": "test-user",
    }
    r = await client.post("/projects", json=payload)
    assert r.status_code == 200
    return r.json()["result"]["project_id"]

