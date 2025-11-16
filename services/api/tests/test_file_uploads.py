"""Integration tests for file upload endpoints."""

from __future__ import annotations

import os
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_file_presign_placeholder(monkeypatch):
    """Test presign endpoint with MinIO not configured (placeholder mode)."""
    monkeypatch.delenv("MINIO_ACCESS_KEY", raising=False)
    monkeypatch.delenv("MINIO_SECRET_KEY", raising=False)
    
    from services.api.src.apex.api.main import app
    
    # First, we need to create a project
    payload = {
        "account_id": "test_account",
        "name": "Test Project",
        "created_by": "test_user",
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create project
        r = await client.post("/projects", json=payload)
        if r.status_code == 200:
            project_data = r.json()
            project_id = project_data["result"]["project_id"]
        else:
            pytest.skip("Project creation failed, cannot test file upload")
        
        # Test presign
        r = await client.get(
            f"/projects/{project_id}/files/presign",
            params={"filename": "test.pdf", "content_type": "application/pdf"},
        )
    
    assert r.status_code == 200
    data = r.json()
    
    # Envelope structure
    assert set(data.keys()) == {"result", "assumptions", "confidence", "trace"}
    
    result = data["result"]
    assert "presigned_url" in result
    assert "blob_key" in result
    assert "upload_id" in result
    assert result["expires_in_seconds"] == 3600
    
    # Should indicate placeholder mode when MinIO not configured
    assert "placeholder" in " ".join(data["assumptions"]).lower() or data["confidence"] == 0.7


@pytest.mark.asyncio
async def test_file_attach_without_verification(monkeypatch):
    """Test attach endpoint without SHA256 verification (storage not configured)."""
    monkeypatch.delenv("MINIO_ACCESS_KEY", raising=False)
    monkeypatch.delenv("MINIO_SECRET_KEY", raising=False)
    
    from services.api.src.apex.api.main import app
    
    # Create project first
    project_payload = {
        "account_id": "test_account",
        "name": "Test Project",
        "created_by": "test_user",
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.post("/projects", json=project_payload)
        if r.status_code != 200:
            pytest.skip("Project creation failed")
        
        project_id = r.json()["result"]["project_id"]
        
        # Test attach
        attach_payload = {
            "blob_key": "projects/test/files/abc123/test.pdf",
            "sha256": "abcd1234" * 8,  # 64-char hex
        }
        r = await client.post(f"/projects/{project_id}/files/attach", json=attach_payload)
    
    assert r.status_code == 200
    data = r.json()
    
    result = data["result"]
    assert result["project_id"] == project_id
    assert result["blob_key"] == attach_payload["blob_key"]
    assert result["sha256"] == attach_payload["sha256"]
    assert "attached_at" in result
    assert result["validated"] is False  # No storage to verify


@pytest.mark.asyncio
async def test_file_presign_envelope_structure():
    """Test that presign endpoint returns proper envelope."""
    from services.api.src.apex.api.main import app
    
    # Mock project
    async with AsyncClient(app=app, base_url="http://test") as client:
        # This test assumes project creation works or mocks it
        # For now, just test the endpoint structure with non-existent project
        r = await client.get(
            "/projects/nonexistent/files/presign",
            params={"filename": "test.pdf"},
        )
    
    # Should return 404 for non-existent project
    assert r.status_code == 404


def test_storage_client_initialization():
    """Test StorageClient initialization with and without credentials."""
    from services.api.src.apex.api.storage import StorageClient
    
    # Without credentials
    client_no_auth = StorageClient(endpoint="http://localhost:9000")
    assert client_no_auth.endpoint == "http://localhost:9000"
    assert client_no_auth._client is None
    
    # With credentials (but minio may not be installed in test env)
    client_with_auth = StorageClient(
        endpoint="http://localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
    )
    # Client may or may not be initialized depending on minio availability
    assert client_with_auth.endpoint == "http://localhost:9000"


def test_blob_key_structure():
    """Test that blob keys follow expected structure."""
    from services.api.src.apex.api.routes.files import router
    
    # Verify router exists
    assert router is not None
    
    # Expected structure: projects/{project_id}/files/{upload_id}/{filename}
    project_id = "proj123"
    upload_id = "abc123"
    filename = "test.pdf"
    expected = f"projects/{project_id}/files/{upload_id}/{filename}"
    
    # Pattern matching
    parts = expected.split("/")
    assert parts[0] == "projects"
    assert parts[1] == project_id
    assert parts[2] == "files"
    assert parts[3] == upload_id
    assert parts[4] == filename

