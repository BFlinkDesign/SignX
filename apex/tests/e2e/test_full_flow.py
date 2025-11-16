from __future__ import annotations

import pytest


def test_project_create_pricing_flow(client):
    # Create project
    r = client.post("/projects", json={"name": "Test Sign", "notes": "E2E test"})
    assert r.status_code == 200
    proj = r.json()["result"]
    pid = proj["id"]
    
    # Get pricing
    r = client.post(f"/projects/{pid}/estimate", json={"project_id": pid, "height_ft": 20, "addons": []})
    assert r.status_code == 200
    assert r.json()["result"]["total"] > 0
    
    # Verify project exists
    r = client.get(f"/projects/{pid}")
    assert r.status_code == 200
    assert r.json()["result"]["id"] == pid

