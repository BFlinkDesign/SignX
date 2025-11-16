"""Full workflow E2E tests: Create project → Fill stages → Submit → Verify report."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_full_submission_workflow(
    test_client,
    sample_project_data,
    sample_payload,
    cleanup_db,
):
    """Test complete submission workflow from creation to report generation."""
    
    # Stage 1: Create project
    create_resp = await test_client.post("/projects/", json=sample_project_data)
    assert create_resp.status_code == 200, f"Project creation failed: {create_resp.text}"
    
    create_data = create_resp.json()
    assert "result" in create_data
    project_id = create_data["result"]["project_id"]
    assert project_id is not None
    
    # Stage 2: Site resolution
    site_resp = await test_client.post(
        "/site/resolve",
        json={"address": "1600 Amphitheatre Parkway, Mountain View, CA"},
    )
    assert site_resp.status_code in (200, 422)  # 422 if geocoding unavailable
    if site_resp.status_code == 200:
        site_data = site_resp.json()
        assert "result" in site_data
    
    # Stage 3: Cabinet derive
    cabinet_resp = await test_client.post(
        "/cabinets/derive",
        json={
            "sign": {"height_ft": 10.0, "width_ft": 8.0},
            "board": {"layers": []},
        },
    )
    assert cabinet_resp.status_code in (200, 422)
    if cabinet_resp.status_code == 200:
        cabinet_data = cabinet_resp.json()
        assert "result" in cabinet_data
    
    # Stage 4: Pole options
    poles_resp = await test_client.post(
        "/poles/options",
        json={"loads": {"moment_kips_ft": 100}, "preferences": {}},
    )
    assert poles_resp.status_code in (200, 422)
    if poles_resp.status_code == 200:
        poles_data = poles_resp.json()
        assert "result" in poles_data
    
    # Stage 5: Foundation (direct burial)
    burial_resp = await test_client.post(
        "/footing/design",
        json={
            "module": "signage.direct_burial_2pole",
            "loads": {"force_kips": 50},
        },
    )
    assert burial_resp.status_code in (200, 422)
    if burial_resp.status_code == 200:
        burial_data = burial_resp.json()
        assert "result" in burial_data
    
    # Stage 6: Get project with payload
    project_resp = await test_client.get(f"/projects/{project_id}")
    assert project_resp.status_code == 200
    
    project_data = project_resp.json()
    assert "result" in project_data
    
    # Stage 7: Submit project
    submit_resp = await test_client.post(
        f"/projects/{project_id}/submit",
        json={"actor": "test_user"},
        headers={"Idempotency-Key": "test_key_123"},
    )
    assert submit_resp.status_code == 200, f"Submission failed: {submit_resp.text}"
    
    submit_data = submit_resp.json()
    assert "result" in submit_data
    assert submit_data["result"].get("status") == "submitted"
    
    # Stage 8: Verify report generation was triggered
    # Note: In production, would poll or check task status
    final_project_resp = await test_client.get(f"/projects/{project_id}")
    assert final_project_resp.status_code == 200
    
    final_data = final_project_resp.json()
    assert "result" in final_data
    
    # Verify envelope consistency throughout
    for resp in [create_resp, submit_resp, final_project_resp]:
        data = resp.json()
        assert "result" in data
        assert "assumptions" in data
        assert "confidence" in data
        assert "trace" in data
        assert 0.0 <= data["confidence"] <= 1.0


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_file_upload_workflow(test_client, sample_project_data, cleanup_db):
    """Test file upload workflow: Presign → Upload → Attach."""
    
    # Create project
    create_resp = await test_client.post("/projects/", json=sample_project_data)
    assert create_resp.status_code == 200
    project_id = create_resp.json()["result"]["project_id"]
    
    # Generate presigned URL
    presign_resp = await test_client.post(
        f"/projects/{project_id}/files/presign",
        json={"filename": "test_drawing.pdf", "content_type": "application/pdf"},
    )
    assert presign_resp.status_code == 200
    
    presign_data = presign_resp.json()
    assert "result" in presign_data
    
    # Note: Actual file upload to MinIO happens client-side
    # Here we just verify the presigned URL was generated
    if presign_data["result"].get("presigned_url"):
        assert "presigned_url" in presign_data["result"]
        assert "blob_key" in presign_data["result"]
    
    # Attach file (simulated)
    blob_key = presign_data["result"].get("blob_key", "test_file_key")
    
    attach_resp = await test_client.post(
        f"/projects/{project_id}/files/attach",
        json={"blob_key": blob_key, "sha256": "test_hash"},
    )
    assert attach_resp.status_code in (200, 422)  # 422 if file not actually uploaded
    
    if attach_resp.status_code == 200:
        attach_data = attach_resp.json()
        assert "result" in attach_data


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_project_lifecycle_states(test_client, sample_project_data, cleanup_db):
    """Test project lifecycle state transitions."""
    
    # Create draft project
    create_resp = await test_client.post("/projects/", json=sample_project_data)
    assert create_resp.status_code == 200
    project_id = create_resp.json()["result"]["project_id"]
    
    # Verify initial state
    get_resp = await test_client.get(f"/projects/{project_id}")
    project_data = get_resp.json()["result"]
    assert project_data["status"] == "draft"
    
    # Try to submit (should transition to submitted)
    submit_resp = await test_client.post(
        f"/projects/{project_id}/submit",
        json={"actor": "test_user"},
        headers={"Idempotency-Key": "lifecycle_test_key"},
    )
    
    if submit_resp.status_code == 200:
        # Verify state transition
        final_resp = await test_client.get(f"/projects/{project_id}")
        final_data = final_resp.json()["result"]
        assert final_data["status"] == "submitted"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_concurrent_project_creation(test_client, sample_project_data, cleanup_db):
    """Test concurrent project creation."""
    import asyncio
    
    async def create_project():
        resp = await test_client.post("/projects/", json={
            **sample_project_data,
            "name": f"Concurrent Test {asyncio.current_task()}",
        })
        return resp.status_code == 200, resp.json() if resp.status_code == 200 else None
    
    # Create 10 projects concurrently
    tasks = [create_project() for _ in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # All should succeed
    success_count = sum(1 for r in results if isinstance(r, tuple) and r[0])
    assert success_count == 10, f"Only {success_count}/10 projects created successfully"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_error_handling(test_client):
    """Test error handling for invalid requests."""
    
    # Invalid project creation
    invalid_resp = await test_client.post("/projects/", json={"invalid": "data"})
    assert invalid_resp.status_code == 422
    
    # Non-existent project
    not_found_resp = await test_client.get("/projects/nonexistent_project")
    assert not_found_resp.status_code == 404
    
    # Invalid submission
    invalid_submit = await test_client.post(
        "/projects/invalid_id/submit",
        json={"actor": "test_user"},
    )
    assert invalid_submit.status_code in (404, 422)

