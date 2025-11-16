"""Pytest fixtures for API tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.fixture(scope="session")
def app():
    """Load the FastAPI app for testing."""
    # Ensure services/api/src is on sys.path
    repo_root = Path(__file__).resolve().parent.parent
    svc_src = repo_root / "services" / "api" / "src"
    if str(svc_src) not in sys.path:
        sys.path.insert(0, str(svc_src))
    
    # Set test environment variables
    os.environ.setdefault("REDIS_URL", "redis://localhost:0")
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    os.environ.setdefault("OPENSEARCH_URL", "http://localhost:9200")
    
    from apex.api.main import app as _app  # type: ignore
    return _app


@pytest.fixture
async def client(app):
    """Async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

