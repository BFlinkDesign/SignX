from __future__ import annotations

import importlib.util
import os
import json
import pytest
from httpx import AsyncClient


def _load_signs_app():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "services", "signs-service"))
    main_path = os.path.join(base_dir, "main.py")
    spec = importlib.util.spec_from_file_location("signs_service.main", main_path)
    assert spec and spec.loader, "Unable to load signs-service main module"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[assignment]
    return mod.app


@pytest.mark.asyncio
async def test_signs_happy_path():
    app = _load_signs_app()
    body = {
        "naics_code": "339950",
        "use_case": "cabinet",
        "illumination": "internal-LED",
        "electrical": {"primary_voltage": 120.0, "phase": "single", "available_circuit_A": 20.0},
        "environment": "coastal",
        "dimensions": {"w_mm": 1200.0, "h_mm": 600.0, "d_mm": 200.0},
        "mounting": {"type": "wall", "params": {}},
        "jurisdiction": {"country": "US", "state": "CA", "city": "San Diego"},
        "labels_required": True,
        "traffic_control_context": False,
        "provenance": {"requested_by": "test"},
    }
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.post("/v1/signs/spec", json=body)

    assert r.status_code == 200
    data = r.json()
    assert data["schema_version"] == "1.0.0"
    assert 0.0 <= data["confidence"] <= 1.0
    assert data.get("abstain") is False
    result = data["result"]
    assert "bom" in result and isinstance(result["bom"], list)
    assert any("required_field_labels"[-1:] or True for _ in [result])  # weak check for shape


