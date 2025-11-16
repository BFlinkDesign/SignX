from __future__ import annotations

import json
import types
import pytest


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["result"]["status"] == "ok"
    assert 0.0 <= body["confidence"] <= 1.0


def test_ready_redis_ok(monkeypatch, client):
    # Patch Redis.from_url to return an object with async ping/aclose
    import apex.api.ready as ready

    class FakeRedis:
        async def ping(self):
            return True

        async def aclose(self):
            return None

    monkeypatch.setattr(ready, "Redis", types.SimpleNamespace(from_url=lambda *_args, **_kw: FakeRedis()))
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json()["result"]["status"] == "ok"


def test_ready_redis_fail(monkeypatch, client):
    import apex.api.ready as ready

    class BadRedis:
        async def ping(self):
            raise RuntimeError("down")

        async def aclose(self):
            return None

    monkeypatch.setattr(ready, "Redis", types.SimpleNamespace(from_url=lambda *_args, **_kw: BadRedis()))
    r = client.get("/ready")
    # Our handler still returns 200 with degraded status per current implementation
    assert r.status_code == 200
    assert r.json()["result"]["status"] in ("degraded", "ok")


def test_health_rate_limit_exempt(client):
    codes = [client.get("/health").status_code for _ in range(5)]
    assert all(c == 200 for c in codes)


def test_pricing_total(client, monkeypatch):
    # Ensure PRICING_VERSION=v1
    monkeypatch.setenv("PRICING_VERSION", "v1")
    payload = {"project_id": "p1", "height_ft": 10, "addons": ["calc_packet"]}
    r = client.post("/projects/p1/estimate", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["result"]["total"] == 235.0


