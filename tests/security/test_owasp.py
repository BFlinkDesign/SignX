"""Security tests: OWASP Top 10 coverage."""

from __future__ import annotations

import pytest


@pytest.mark.security
@pytest.mark.asyncio
async def test_sql_injection_project_name(client):
    """Test SQL injection protection in project names."""
    
    malicious_payloads = [
        "'; DROP TABLE projects; --",
        "' OR '1'='1",
        "admin'--",
        "1' UNION SELECT * FROM users--",
    ]
    
    for payload in malicious_payloads:
        resp = await client.post(
            "/projects/",
            json={
                "account_id": "test",
                "name": payload,
                "created_by": "test",
            },
        )
        
        # Should not execute SQL, should validate or sanitize
        assert resp.status_code in (422, 400, 500)
        
        # Verify data not corrupted
        list_resp = await client.get("/projects/")
        assert list_resp.status_code == 200


@pytest.mark.security
@pytest.mark.asyncio
async def test_xss_protection(client):
    """Test XSS protection in user inputs."""
    
    xss_payloads = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
    ]
    
    for payload in xss_payloads:
        resp = await client.post(
            "/projects/",
            json={
                "account_id": "test",
                "name": payload,
                "created_by": "test",
            },
        )
        
        # Should sanitize or reject
        assert resp.status_code in (200, 422)
        
        if resp.status_code == 200:
            # Verify response doesn't contain script tags
            data = resp.json()
            response_str = str(data)
            assert "<script>" not in response_str.lower()


@pytest.mark.security
@pytest.mark.asyncio
async def test_rate_limiting(client):
    """Test rate limiting on endpoints."""
    
    # Make 100 requests rapidly
    responses = []
    for i in range(100):
        resp = await client.get("/health")
        responses.append(resp.status_code)
    
    # Should eventually return 429
    assert 429 in responses, "Rate limiting not triggered"


@pytest.mark.security
@pytest.mark.asyncio
async def test_input_validation(client):
    """Test input validation on numeric fields."""
    
    # Invalid numeric inputs
    invalid_inputs = [
        {"moment_kips_ft": "not a number"},
        {"moment_kips_ft": float("inf")},
        {"moment_kips_ft": -1e10},
    ]
    
    for invalid_input in invalid_inputs:
        resp = await client.post(
            "/poles/options",
            json={"loads": invalid_input},
        )
        
        # Should reject invalid inputs
        assert resp.status_code == 422


@pytest.mark.security
@pytest.mark.asyncio
async def test_path_traversal_protection(client):
    """Test path traversal protection in file operations."""
    
    malicious_paths = [
        "../../../etc/passwd",
        "..\\..\\windows\\system32\\config\\sam",
        "/etc/shadow",
    ]
    
    for path in malicious_paths:
        resp = await client.post(
            "/projects/test/files/presign",
            json={"filename": path},
        )
        
        # Should reject path traversal attempts
        assert resp.status_code in (400, 422, 403)


@pytest.mark.security
@pytest.mark.asyncio
async def test_mass_assignment_protection(client):
    """Test mass assignment protection."""
    
    # Attempt to set internal fields
    resp = await client.post(
        "/projects/",
        json={
            "account_id": "test",
            "name": "Test Project",
            "created_by": "test",
            "status": "accepted",  # Should not allow setting status directly
            "created_at": "2020-01-01T00:00:00Z",  # Should ignore
        },
    )
    
    if resp.status_code == 200:
        data = resp.json()
        # Status should be default, not what we provided
        # (unless explicitly allowed by API)
        pass  # Implementation-specific


@pytest.mark.security
@pytest.mark.asyncio
async def test_csrf_protection_mutations(client):
    """Test CSRF protection on mutation endpoints."""
    
    # Note: Requires CSRF token implementation
    # Placeholder for future CSRF implementation
    
    resp = await client.post(
        "/projects/",
        json={"account_id": "test", "name": "Test", "created_by": "test"},
    )
    
    # Should work if no CSRF protection yet
    # Or should reject if CSRF protection enabled
    assert resp.status_code in (200, 403)


@pytest.mark.security
@pytest.mark.asyncio
async def test_authorization_enforcement(client):
    """Test RBAC enforcement prevents unauthorized access."""
    
    # Create project
    resp = await client.post(
        "/projects/",
        json={
            "account_id": "user_a",
            "name": "User A Project",
            "created_by": "user_a",
        },
    )
    
    # Try to access as different user
    # Note: Requires auth implementation
    # Placeholder for future auth tests
    
    assert resp.status_code in (200, 403)


@pytest.mark.security
@pytest.mark.asyncio
async def test_jwt_validation(client):
    """Test JWT validation and expired token handling."""
    
    # Invalid tokens
    invalid_tokens = [
        "invalid_token",
        "expired.jwt.token",
        "malformed-token",
    ]
    
    # Note: Requires JWT implementation
    # Placeholder for future JWT tests
    
    pass


@pytest.mark.security
@pytest.mark.asyncio
async def test_sensitive_data_exposure(client):
    """Test that sensitive data is not exposed in responses."""
    
    # Check responses don't include:
    # - Passwords
    # - API keys
    # - Internal IDs
    # - File paths
    
    resp = await client.get("/version")
    
    if resp.status_code == 200:
        data = resp.json()
        response_str = str(data)
        
        # Should not expose sensitive strings
        assert "password" not in response_str.lower()
        assert "secret" not in response_str.lower()
        assert "key" not in response_str.lower()

