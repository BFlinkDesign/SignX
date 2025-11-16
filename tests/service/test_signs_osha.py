from __future__ import annotations

import importlib.util
import os
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
async def test_signs_osha_format_applied_for_wayfinding():
    app = _load_signs_app()
    body = {
        "naics_code": "339950",
        "use_case": "wayfinding",
        "illumination": "external",
        "electrical": {"primary_voltage": 120.0, "phase": "single", "available_circuit_A": 15.0},
        "environment": "indoor",
        "dimensions": {"w_mm": 300.0, "h_mm": 100.0, "d_mm": 10.0},
        "mounting": {"type": "suspended", "params": {}},
        "jurisdiction": {"country": "US"},
        "labels_required": True,
        "traffic_control_context": False,
        "provenance": {},
    }
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.post("/v1/signs/spec", json=body)

    assert r.status_code == 200
    data = r.json()
    gfx = data["result"]["graphics_spec"]
    assert gfx.get("format_standard") == "OSHA 29 CFR 1910.145"


