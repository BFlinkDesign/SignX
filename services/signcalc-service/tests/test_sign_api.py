from __future__ import annotations

import importlib.util
import json
import os
import pytest
from httpx import AsyncClient


def _load_app():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    main_path = os.path.join(base_dir, "main.py")
    spec = importlib.util.spec_from_file_location("signcalc_service.main", main_path)
    assert spec and spec.loader, "Unable to load signcalc-service main module"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[assignment]
    return mod.app


@pytest.mark.asyncio
async def test_schemas_and_packs():
    app = _load_app()
    async with AsyncClient(app=app, base_url="http://test") as client:
        s = await client.get("/schemas/sign-1.0.json")
        assert s.status_code == 200
        p = await client.get("/packs")
        assert p.status_code == 200
        data = p.json()
        assert "packs" in data and len(data["packs"]) >= 3


def _fixture(path: str) -> dict:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures"))
    with open(os.path.join(root, path), "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_design_us_small_deterministic():
    app = _load_app()
    req = _fixture("req_small.json")
    async with AsyncClient(app=app, base_url="http://test") as client:
        r1 = await client.post("/v1/signs/design", json=req)
        r2 = await client.post("/v1/signs/design", json=req)
    assert r1.status_code == 200 and r2.status_code == 200
    d1, d2 = r1.json(), r2.json()
    assert d1["trace"]["standards_pack_sha256"] == d2["trace"]["standards_pack_sha256"]
    assert d1["trace"]["data_sha256"] == d2["trace"]["data_sha256"]
    sel = d1["result"]["selected"]
    assert sel["foundation"]["depth_in"] >= 36.0
    assert d1["result"]["reports"]["pdf_ref"].endswith(".pdf")
    assert d1["result"]["reports"]["dxf_ref"].endswith(".dxf")


@pytest.mark.asyncio
async def test_design_eu_basic():
    app = _load_app()
    req = _fixture("req_small.json")
    req["jurisdiction"] = "EU"
    req["standard"]["code"] = "EN1991"
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.post("/v1/signs/design", json=req)
    assert r.status_code == 200
    d = r.json()
    assert "qb_pa" in d["result"]["loads"] or "qz_psf" in d["result"]["loads"]


