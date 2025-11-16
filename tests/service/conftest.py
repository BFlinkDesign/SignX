from __future__ import annotations

import json
import os
import importlib.util
from typing import Dict, Any

import pytest
from httpx import AsyncClient


def _load_app():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "services", "materials-service"))
    main_path = os.path.join(base_dir, "main.py")
    spec = importlib.util.spec_from_file_location("materials_service.main", main_path)
    assert spec and spec.loader, "Unable to load materials-service main module"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[assignment]
    return mod.app


@pytest.fixture
def fixture_payload() -> Dict[str, Any]:
    fixtures_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "e2e", "fixtures", "materials_request.json")
    )
    with open(fixtures_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
async def client():
    app = _load_app()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


