from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_pick_endpoint_ranks_with_reasoning_and_confidence(client, fixture_payload):
    resp = await client.post("/pick", json=fixture_payload)
    assert resp.status_code == 200
    assert resp.headers.get("x-trace")
    data = resp.json()

    assert data["schema_version"] == "1.0.0"
    assert isinstance(data["assumptions"], list)
    assert 0.0 <= float(data["confidence"]) <= 1.0

    ranked = data["result"]["ranked"]
    assert isinstance(ranked, list) and len(ranked) >= 3
    top = ranked[0]
    assert "id" in top and "score" in top and "contributions" in top
    assert top["id"] == "C"


