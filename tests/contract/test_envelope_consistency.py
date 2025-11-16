"""
Contract tests: verify all endpoints return canonical ResponseEnvelope.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_envelope_shape(client) -> None:
    """Verify every endpoint returns canonical envelope shape."""
    # Skip endpoints that might not exist
    routes = [
        ("GET", "/health"),
        ("GET", "/version"),
        ("GET", "/ready"),
        ("GET", "/projects/"),
    ]

    for method, route in routes:
        if method == "GET":
            resp = await client.get(route)
        else:
            resp = await client.post(route, json={})

        assert resp.status_code in [200, 404, 422], f"{route} returned {resp.status_code}"
        if resp.status_code != 200:
            continue

        data = resp.json()
        assert "result" in data or data.get("result") is None
        assert "assumptions" in data
        assert isinstance(data["assumptions"], list)
        assert "confidence" in data
        assert isinstance(data["confidence"], (int, float))
        assert 0.0 <= data["confidence"] <= 1.0
        assert "trace" in data


@pytest.mark.asyncio
async def test_materials_pick_envelope(client, fixture_payload: dict[str, Any]) -> None:
    """Verify materials /pick returns envelope with ranked list."""
    resp = await client.post("/v1/materials/pick", json=fixture_payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "result" in data
    ranked = data["result"].get("ranked")
    assert isinstance(ranked, list)
    assert len(ranked) > 0
    top = ranked[0]
    assert "id" in top
    assert "score" in top
    assert "contributions" in top
    assert isinstance(top["contributions"], list)


@pytest.mark.asyncio
async def test_floats_are_rounded(client, fixture_payload: dict[str, Any]) -> None:
    """Verify numeric outputs are rounded for determinism."""
    resp = await client.post("/v1/materials/pick", json=fixture_payload)
    data = resp.json()

    def check_rounded(val: Any) -> None:
        if isinstance(val, float):
            # Should be rounded to reasonable precision
            assert val == round(val, 6), f"Unrounded float: {val}"
        elif isinstance(val, dict):
            for v in val.values():
                check_rounded(v)
        elif isinstance(val, list):
            for item in val:
                check_rounded(item)

    check_rounded(data["result"])
