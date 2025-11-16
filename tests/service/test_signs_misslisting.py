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
async def test_signs_missing_listing_evidence_flags_compliance():
    app = _load_signs_app()
    body = {
        "naics_code": "339950",
        "use_case": "cabinet",
        "illumination": "internal-LED",
        "electrical": {"primary_voltage": 120.0, "phase": "single", "available_circuit_A": 15.0},
        "environment": "outdoor",
        "dimensions": {"w_mm": 1000.0, "h_mm": 500.0, "d_mm": 150.0},
        "mounting": {"type": "wall", "params": {}},
        "jurisdiction": {"country": "US"},
        "labels_required": True,
        "traffic_control_context": False,
        "provenance": {},
    }
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.post("/v1/signs/spec", json=body)

    assert r.status_code == 200
    data = r.json()
    comp = data["result"]["compliance"]
    assert any((c.get("source") == "UL 879/879A" and c.get("satisfied") is False) for c in comp)


