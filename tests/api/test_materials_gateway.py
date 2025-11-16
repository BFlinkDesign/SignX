from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx
import pytest


def load_api_app(monkeypatch):
    # Ensure package import path
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "services", "api", "src"))
    if root not in sys.path:
        sys.path.insert(0, root)
    # Patch contract lock on startup
    import apex.api.main as api_main

    monkeypatch.setattr(api_main, "ensure_materials_contract", lambda: "testsha", raising=True)
    return api_main.app


class _DummyAC:
    def __init__(self, response: httpx.Response):
        self._resp = response

    async def __aenter__(self):  # type: ignore[no-untyped-def]
        return self

    async def __aexit__(self, *args):  # type: ignore[no-untyped-def]
        return False

    async def post(self, url: str, json: Any):  # type: ignore[no-untyped-def]
        return self._resp


@pytest.mark.asyncio
async def test_gateway_happy_path(monkeypatch):
    from httpx import AsyncClient

    app = load_api_app(monkeypatch)

    payload = {
        "result": {"ranked": [{"id": "C", "name": "Titanium", "score": 88.3, "contributions": [], "constraints_satisfied": True, "provenance": []}]},
        "assumptions": ["Normalized weights by factor 1/0.9 to sum to 1.0"],
        "confidence": 0.8,
        "abstain": False,
    }
    backend_resp = httpx.Response(200, json=payload, headers={"x-trace": "abc123:deadbeef"})
    # Patch backend HTTP call
    import apex.api.routes.materials as gw

    monkeypatch.setattr(gw.httpx, "AsyncClient", lambda timeout=20.0: _DummyAC(backend_resp), raising=True)

    fx_path = "tests/e2e/fixtures/materials_request.json"
    with open(fx_path, "r", encoding="utf-8") as f:
        body = json.load(f)

    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.post("/v1/materials/pick", json=body)

    assert r.status_code == 200
    assert r.headers.get("x-trace") == "abc123:deadbeef"
    data = r.json()
    assert data["result"]["ranked"][0]["id"] == "C"


@pytest.mark.asyncio
async def test_gateway_passes_422(monkeypatch):
    from httpx import AsyncClient
    app = load_api_app(monkeypatch)
    backend_resp = httpx.Response(422, content=b"invalid weights")
    import apex.api.routes.materials as gw

    monkeypatch.setattr(gw.httpx, "AsyncClient", lambda timeout=20.0: _DummyAC(backend_resp), raising=True)

    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.post("/v1/materials/pick", json={})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_gateway_maps_5xx_to_502(monkeypatch):
    from httpx import AsyncClient
    app = load_api_app(monkeypatch)
    backend_resp = httpx.Response(503, content=b"service down")
    import apex.api.routes.materials as gw

    monkeypatch.setattr(gw.httpx, "AsyncClient", lambda timeout=20.0: _DummyAC(backend_resp), raising=True)

    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.post("/v1/materials/pick", json={})
    assert r.status_code == 502

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import AsyncClient


def _mock_response(status_code: int, json_payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None):
    class R:
        def __init__(self):
            self.status_code = status_code
            self._json = json_payload or {}
            self.headers = headers or {}
            self.text = json.dumps(self._json)

        def json(self):  # type: ignore[no-untyped-def]
            return self._json

    return R()


@pytest.mark.asyncio
async def test_gateway_happy_path(monkeypatch):
    from services.api.src.apex.api.main import app

    async def fake_post(self, url, json):  # type: ignore[no-untyped-def]
        payload = {
            "schema_version": "1.0.0",
            "result": {"ranked": [{"id": "C", "name": "Ti", "score": 90.1, "contributions": [], "constraints_satisfied": True}]},
            "assumptions": ["Normalized weights"],
            "confidence": 0.8,
            "abstain": False,
            "trace": {"request_hash": "abc", "code_version": "git:abc", "model_config": {"scaler": "minmax_v1"}},
        }
        return _mock_response(200, payload, {"x-trace": "deadbeef:abc123"})

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post, raising=True)

    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.post("/v1/materials/pick", json={"hello": "world"})
        assert r.status_code == 200
        assert r.headers.get("x-trace") == "deadbeef:abc123"
        data = r.json()
        assert data["result"]["ranked"][0]["id"] == "C"


@pytest.mark.asyncio
async def test_gateway_422_passthrough(monkeypatch):
    from services.api.src.apex.api.main import app

    async def fake_post(self, url, json):  # type: ignore[no-untyped-def]
        return _mock_response(422, {"detail": "All weights are zero"})

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post, raising=True)

    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.post("/v1/materials/pick", json={})
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_gateway_5xx_to_502(monkeypatch):
    from services.api.src.apex.api.main import app

    async def fake_post(self, url, json):  # type: ignore[no-untyped-def]
        return _mock_response(503, {"detail": "backend down"})

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post, raising=True)

    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.post("/v1/materials/pick", json={})
        assert r.status_code == 502


