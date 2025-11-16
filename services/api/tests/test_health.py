import asyncio

import pytest
from httpx import AsyncClient
from fastapi import FastAPI

from apex.api.main import app as fastapi_app


@pytest.mark.asyncio
async def test_health_envelope():
    app: FastAPI = fastapi_app
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == {"result", "assumptions", "confidence", "trace"}
        assert data["result"]["status"] == "ok"
        assert isinstance(data["assumptions"], list)
        assert isinstance(data["confidence"], float)
        trace = data["trace"]
        assert set(trace.keys()) == {"data", "code_version", "model_config"}
        assert set(trace["data"].keys()) == {"inputs", "intermediates", "outputs"}


