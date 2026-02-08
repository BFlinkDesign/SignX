from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_pricing_estimate_envelope_and_total(monkeypatch):
    # Ensure pricing version v1
    monkeypatch.setenv("APEX_PRICING_VERSION", "v1")

    from services.api.src.apex.api.main import app

    payload = {"height_ft": 24.0, "addons": ["calc_packet", "hard_copies", "unknown_addon"]}

    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.post("/projects/proj123/estimate", json=payload)

    assert r.status_code == 200
    data = r.json()

    # Envelope shape
    assert set(data.keys()) == {"result", "assumptions", "confidence", "trace"}
    assert 0.0 <= float(data["confidence"]) <= 1.0
    assert isinstance(data["assumptions"], list)

    result = data["result"]
    assert result["pricing_version"] == "v1"
    items = result["line_items"]
    # Base + 2 addons
    assert len(items) == 3
    total = result["total_usd"]
    # v1: base 200 (<=25ft) + 35 + 30 = 265
    assert total == 200 + 35 + 30
    # Unknown addon is ignored but mentioned in assumptions
    assert any("ignored_unknown_addons" in a for a in data["assumptions"])


