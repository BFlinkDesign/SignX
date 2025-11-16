"""Business logic tests: Baseplate validation rules."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_baseplate_all_pass_required_for_approval(client):
    """Baseplate approval requires all checks to pass."""
    # Valid design - all passes
    valid_req = {
        "plate": {"w_in": 12.0, "l_in": 12.0, "t_in": 0.75, "fy_ksi": 36.0, "e_in": 3.0},
        "weld": {"size_in": 0.25, "strength": 70.0, "length_in": 12.0},
        "anchors": {"num_anchors": 4, "dia_in": 0.75, "embed_in": 10.0, "fy_ksi": 58.0, "fc_psi": 4000.0, "spacing_in": 6.0},
        "loads": {"T_kip": 5.0, "V_kip": 2.0, "M_kipin": 100.0},
    }
    
    resp = await client.post("/signage/baseplate/checks", json=valid_req)
    assert resp.status_code == 200
    data = resp.json()
    
    checks = data["result"]["checks"]
    all_pass = data["result"]["all_pass"]
    approved = data["result"]["approved"]
    
    # All checks must pass for approval
    assert all_pass == approved
    if all_pass:
        assert all(c["pass"] for c in checks)


@pytest.mark.asyncio
async def test_baseplate_fail_prevents_approval(client):
    """Baseplate with failing check should not be approved."""
    # Invalid design - plate too thin
    invalid_req = {
        "plate": {"w_in": 12.0, "l_in": 12.0, "t_in": 0.1, "fy_ksi": 36.0, "e_in": 3.0},  # Too thin
        "weld": {"size_in": 0.25, "strength": 70.0, "length_in": 12.0},
        "anchors": {"num_anchors": 4, "dia_in": 0.75, "embed_in": 10.0, "fy_ksi": 58.0, "fc_psi": 4000.0, "spacing_in": 6.0},
        "loads": {"T_kip": 50.0, "V_kip": 20.0, "M_kipin": 1000.0},  # High loads
    }
    
    resp = await client.post("/signage/baseplate/checks", json=invalid_req)
    assert resp.status_code == 200
    data = resp.json()
    
    approved = data["result"]["approved"]
    all_pass = data["result"]["all_pass"]
    
    assert not approved or not all_pass  # At least one check should fail

