# JWT Authentication Integration Guide

## Overview

JWT authentication is implemented in `auth.py` but needs to be wired to protected routes.

## Usage

### 1. Basic Route Protection

Add `get_current_user` dependency to any route that requires authentication:

```python
from ..auth import get_current_user, TokenData
from fastapi import Depends

@router.post("/projects")
async def create_project(
    req: ProjectCreateRequest,
    user: TokenData = Depends(get_current_user),  # Add this
) -> ResponseEnvelope:
    # Now you have access to:
    # - user.user_id
    # - user.account_id
    # - user.email
    # - user.roles
    project = await create_project_internal(req, created_by=user.user_id)
    return ...
```

### 2. Role-Based Access Control (RBAC)

For routes that require specific roles:

```python
from ..auth import require_role

@router.delete("/projects/{id}")
async def delete_project(
    project_id: str,
    user: TokenData = Depends(require_role(["admin"])),  # Only admins
) -> ResponseEnvelope:
    # Admin-only operation
    ...
```

### 3. Mock Authentication for Development

If you want to bypass JWT during development, use `MockAuth`:

```python
from ..auth import MockAuth

@router.post("/projects")
async def create_project(
    req: ProjectCreateRequest,
    user: TokenData = Depends(MockAuth.get_mock_user if settings.ENV == "dev" else get_current_user),
) -> ResponseEnvelope:
    ...
```

## Configuration

Set JWT secret key via environment variable:

```bash
APEX_JWT_SECRET_KEY=your-secret-key-here
```

If not set, a random key is generated (insecure for production!).

## Token Generation

### For Testing/Development

Use the helper function:

```python
from ..auth import create_mock_token

token = create_mock_token()
# Use in Authorization header: "Bearer <token>"
```

### For Production

Generate tokens from your auth service or use a proper JWT library.

## Which Routes Need Protection?

### High Priority (Auth Required)
- `POST /projects` - Create project
- `PUT /projects/{id}` - Update project
- `DELETE /projects/{id}` - Delete project
- `POST /projects/{id}/payload` - Save payload
- `POST /projects/{id}/submit` - Submit project

### Medium Priority (Optional Auth)
- `GET /projects` - List projects (filter by account_id if authenticated)
- `GET /projects/{id}` - View project (check ownership)

### Low Priority (Public OK)
- `POST /signage/site/resolve` - Site resolution
- `POST /utilities/concrete/yards` - Calculator
- `GET /health` - Health check

## Example: Protected Route

```python
@router.post("/projects")
async def create_project(
    req: ProjectCreateRequest,
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Create a new project. Requires authentication."""
    logger.info("project.create", user_id=user.user_id, account_id=user.account_id)
    
    # Ensure account_id matches
    if req.account_id != user.account_id:
        raise HTTPException(
            status_code=403,
            detail="Account ID mismatch"
        )
    
    # Create project with authenticated user
    project = Project(
        project_id=str(uuid.uuid4()),
        account_id=user.account_id,
        name=req.name,
        created_by=user.user_id,  # Use authenticated user
        updated_by=user.user_id,
        status="draft",
    )
    
    db.add(project)
    await db.commit()
    
    return make_envelope(...)
```

## Migration Plan

1. **Phase 1**: Add auth to write operations (POST, PUT, DELETE)
2. **Phase 2**: Add optional auth to read operations (GET)
3. **Phase 3**: Add RBAC for admin endpoints
4. **Phase 4**: Implement account-level isolation

## Testing

Use `httpx` with bearer token:

```python
from httpx import AsyncClient

async def test_create_project():
    client = AsyncClient(base_url="http://test")
    
    # Get mock token
    from apex.api.auth import create_mock_token
    token = create_mock_token()
    
    response = await client.post(
        "/projects",
        json={"name": "Test", ...},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
```

## Security Notes

- ⚠️ Never log JWTs in production
- ⚠️ Use HTTPS in production
- ⚠️ Set `JWT_SECRET_KEY` in production
- ⚠️ Consider token refresh for long-lived sessions
- ⚠️ Validate audience/issuer if needed

