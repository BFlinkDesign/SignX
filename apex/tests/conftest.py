from __future__ import annotations

import os
import sys
from pathlib import Path
import pytest
from starlette.testclient import TestClient


@pytest.fixture(scope="session")
def app():
    # Ensure services/api/src is on sys.path
    repo_root = Path(__file__).resolve().parents[1]
    svc_src = repo_root / "services" / "api" / "src"
    if str(svc_src) not in sys.path:
        sys.path.insert(0, str(svc_src))
    from apex.api.main import app as _app  # type: ignore

    # Make REDIS_URL invalid by default to avoid network in tests
    os.environ.setdefault("REDIS_URL", "redis://localhost:0")
    return _app


@pytest.fixture()
def client(app):
    return TestClient(app)


