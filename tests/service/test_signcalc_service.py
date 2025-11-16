from __future__ import annotations

import importlib.util
import os

from fastapi.testclient import TestClient


def _load_app():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "services", "signcalc-service"))
    main_path = os.path.join(base_dir, "main.py")
    spec = importlib.util.spec_from_file_location("signcalc_service.main", main_path)
    assert spec and spec.loader, "Unable to load signcalc-service main module"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[assignment]
    return mod.app


def test_sign_design_roundtrip():
    app = _load_app()
    c = TestClient(app)
    req = {
        "schema_version": "sign-1.0",
        "jurisdiction": "US",
        "standard": {"code": "ASCE7", "version": "16", "importance": "II"},
        "site": {"lat": 39.1, "lon": -94.6, "elevation_m": 300, "exposure": "C", "topography": "none", "soil_bearing_psf": 1500, "frost_depth_in": 36},
        "sign": {"width_ft": 12, "height_ft": 8, "centroid_height_ft": 20, "gross_weight_lbf": 450},
        "support_options": ["pipe", "W", "tube"],
        "embed": {"type": "direct"},
        "constraints": {},
    }
    r = c.post("/v1/signs/design", json=req)
    assert r.status_code == 200
    data = r.json()
    assert 0.0 <= data["confidence"] <= 1.0
    assert "result" in data and "selected" in data["result"]


