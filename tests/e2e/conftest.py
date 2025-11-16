"""E2E test fixtures with full Docker stack."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient

# Add API source to path
repo_root = Path(__file__).resolve().parent.parent.parent
api_path = repo_root / "services" / "api" / "src"
if str(api_path) not in sys.path:
    sys.path.insert(0, str(api_path))


@pytest.fixture(scope="session")
def api_url():
    """Get API URL from environment or default to test compose."""
    return os.getenv("APEX_API_URL", "http://localhost:8001")


@pytest.fixture(scope="session")
async def test_client(api_url):
    """Async HTTP client for E2E tests."""
    async with AsyncClient(base_url=api_url, timeout=30.0) as client:
        yield client


@pytest.fixture
def sample_project_data():
    """Sample project data for E2E tests."""
    return {
        "account_id": "test_account",
        "name": "E2E Test Project",
        "customer": "Test Customer",
        "description": "End-to-end test project",
        "created_by": "test_user",
    }


@pytest.fixture
def sample_payload():
    """Sample project payload for testing."""
    return {
        "module": "signage.single_pole",
        "config": {
            "request": {
                "sign": {"height_ft": 10.0, "width_ft": 8.0},
                "site": {"v_design_mph": 90},
            },
            "selected": {
                "pole": {"name": "4x6", "material": "steel"},
                "foundation": {"depth_ft": 6.0},
            },
            "loads": {"moment_kip_ft": 150.0},
        },
        "files": [],
        "cost_snapshot": {"total": 5000.0},
    }


@pytest.fixture
async def cleanup_db(test_client):
    """Cleanup database after each test."""
    yield
    
    # Cleanup logic: delete test projects
    # In production, would truncate test tables or use transactions
    pass


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

