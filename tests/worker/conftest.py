"""Pytest fixtures for Celery worker tests."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from celery import Celery
from celery.result import AsyncResult


@pytest.fixture(scope="session")
def worker_src_path():
    """Get the worker source path for imports."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / "services" / "worker" / "src"


@pytest.fixture
def mock_celery_app(monkeypatch):
    """Mock Celery app for testing."""
    app = Celery("test-app")
    app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        broker_url="memory://",
        result_backend="cache+memory://",
    )
    return app


@pytest.fixture
def artifacts_dir():
    """Create temporary artifacts directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


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
def sample_project_data():
    """Sample project data for PM dispatch testing."""
    return {
        "project_id": "proj_test123",
        "name": "Test Sign Project",
        "customer": "Test Customer",
        "status": "submitted",
    }


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis for idempotency testing."""
    cache: dict[str, Any] = {}

    def get(key: str):
        return cache.get(key)

    def set(key: str, value: str):
        cache[key] = value
        return True

    def exists(key: str):
        return key in cache

    mock_redis_instance = MagicMock()
    mock_redis_instance.get = get
    mock_redis_instance.set = set
    mock_redis_instance.exists = exists
    return mock_redis_instance


@pytest.fixture
def env_vars(monkeypatch, artifacts_dir):
    """Set environment variables for testing."""
    monkeypatch.setenv("MINIO_BUCKET", str(artifacts_dir))
    monkeypatch.setenv("REDIS_URL", "redis://localhost:0")


@pytest.fixture
def mock_report_generation(monkeypatch):
    """Mock report generation for testing."""
    import sys
    from pathlib import Path

    # Add services/api to path
    repo_root = Path(__file__).resolve().parent.parent.parent
    api_path = repo_root / "services" / "api" / "src"
    if str(api_path) not in sys.path:
        sys.path.insert(0, str(api_path))

    # Mock the generate_report_from_payload function
    async def mock_generate_report(*args, **kwargs):
        return {
            "sha256": "test_sha256_hash",
            "pdf_ref": "blobs/test/test_hash.pdf",
            "cached": False,
        }

    monkeypatch.setattr(
        "apex.api.utils.report.generate_report_from_payload",
        mock_generate_report,
    )


@pytest.fixture
def tasks_module(worker_src_path):
    """Import and return the tasks module."""
    if str(worker_src_path) not in sys.path:
        sys.path.insert(0, str(worker_src_path))

    from apex.worker import tasks

    return tasks

