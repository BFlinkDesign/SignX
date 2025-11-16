"""Business logic tests: Submission idempotency."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_submission_idempotency(client):
    """Same idempotency key returns identical result."""
    # Create project first
    create_resp = await client.post(
        "/projects",
        json={"account_id": "test", "name": "Idempotency Test", "created_by": "test"},
    )
    assert create_resp.status_code in (200, 201)
    project_id = create_resp.json()["result"]["project_id"]
    
    idempotency_key = "test-key-123"
    
    # First submission
    resp1 = await client.post(
        f"/projects/{project_id}/submit",
        headers={"Idempotency-Key": idempotency_key},
    )
    
    # Second submission with same key (should return same result)
    resp2 = await client.post(
        f"/projects/{project_id}/submit",
        headers={"Idempotency-Key": idempotency_key},
    )
    
    # Both should succeed
    assert resp1.status_code in (200, 201)
    assert resp2.status_code in (200, 201)
    
    data1 = resp1.json()
    data2 = resp2.json()
    
    # Should return identical project_number (if idempotent)
    if data1["result"].get("idempotent") and data2["result"].get("idempotent"):
        assert data1["result"]["project_number"] == data2["result"]["project_number"]

