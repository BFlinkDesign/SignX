# ETag Optimistic Locking

## Overview

APEX implements **optimistic locking** using HTTP ETags to prevent concurrent update conflicts. This ensures data consistency when multiple users edit the same project simultaneously.

## How It Works

1. **GET** request includes current ETag in response
2. Client stores ETag with project data
3. **PUT** request must include `If-Match` header with stored ETag
4. Server validates ETag matches current database state
5. If mismatch: **412 Precondition Failed** returned
6. If match: update proceeds, new ETag generated

## Usage Flow

### 1. Fetch Project (GET)

```bash
GET /projects/proj_abc123
```

**Response**:
```json
{
  "result": {
    "project_id": "proj_abc123",
    "name": "Main Street Sign",
    "status": "draft",
    "etag": "a1b2c3d4e5f6..."
  }
}
```

**Response Headers**:
```
ETag: a1b2c3d4e5f6...
```

### 2. Update Project (PUT)

```bash
PUT /projects/proj_abc123
If-Match: a1b2c3d4e5f6...
Content-Type: application/json

{
  "name": "Updated Main Street Sign"
}
```

**Response (Success)**:
```json
{
  "result": {
    "project_id": "proj_abc123",
    "name": "Updated Main Street Sign",
    "status": "draft",
    "etag": "f6e5d4c3b2a1..."  // New ETag
  }
}
```

### 3. Concurrent Update Conflict

**User A**:
```bash
PUT /projects/proj_abc123
If-Match: a1b2c3d4e5f6...  # Old ETag
```

**Response**:
```json
{
  "error": {
    "detail": "ETag mismatch: expected f6e5d4c3b2a1..., got a1b2c3d4e5f6..."
  }
}
```

**Response Headers**:
```
HTTP/1.1 412 Precondition Failed
ETag: f6e5d4c3b2a1...  # Current ETag
```

**User B** receives 412 → fetches latest project → retries update with new ETag

## ETag Generation

ETags are SHA256 hashes of project state:

```python
def compute_etag(project):
    content = f"{project.project_id}:{project.status}:{project.updated_at.isoformat()}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]
```

**Included in hash**:
- Project ID
- Status
- Updated timestamp

**ETag changes when**:
- Status transitions (draft → estimating → submitted)
- Any field updated (name, customer, description, etc.)
- Metadata modified

## Implementation Details

### Server-Side (FastAPI)

```python
@router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    if_match: str | None = Header(None, alias="If-Match"),
) -> ResponseEnvelope:
    """Update with optimistic locking."""
    
    # Fetch project
    project = await get_project(project_id)
    
    # Validate ETag
    if if_match and project.etag != if_match:
        raise HTTPException(
            status_code=412,
            detail=f"ETag mismatch",
            headers={"ETag": project.etag}
        )
    
    # Update project
    project.name = req.name
    project.updated_at = datetime.now(timezone.utc)
    project.etag = compute_etag(project)  # Generate new ETag
    
    # Save
    await db.commit()
    
    return make_envelope(result={"etag": project.etag})
```

### Client-Side (React/TypeScript)

```typescript
async function updateProject(id: string, data: ProjectData, etag: string) {
  try {
    const response = await fetch(`/projects/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'If-Match': etag,
      },
      body: JSON.stringify(data),
    });
    
    if (response.status === 412) {
      // ETag mismatch - fetch latest and retry
      const currentProject = await fetchProject(id);
      return updateProject(id, data, currentProject.etag);
    }
    
    const updated = await response.json();
    return updated.result;
  } catch (error) {
    console.error('Update failed:', error);
    throw error;
  }
}
```

## Error Handling

### 412 Precondition Failed

**When**: ETag mismatch

**Response Headers**:
```
HTTP/1.1 412 Precondition Failed
ETag: <current_etag>
Content-Type: application/json
```

**Response Body**:
```json
{
  "detail": "ETag mismatch: expected f6e5d4c3b2a1..., got a1b2c3d4e5f6..."
}
```

**Client Action**:
1. Parse current ETag from response header
2. Fetch latest project data
3. Show diff to user
4. Allow retry with new ETag

### 404 Not Found

**When**: Project doesn't exist

**Response**:
```
HTTP/1.1 404 Not Found
```

### 422 Unprocessable Entity

**When**: Invalid state transition

**Response**:
```json
{
  "detail": "Invalid transition: draft → accepted"
}
```

## Best Practices

### 1. Always Include If-Match

**Bad**:
```bash
PUT /projects/proj_abc123
# No If-Match header
```

**Good**:
```bash
PUT /projects/proj_abc123
If-Match: a1b2c3d4e5f6...
```

### 2. Handle 412 Gracefully

**Bad**:
```typescript
const result = await updateProject(id, data, etag);
// No error handling - may overwrite concurrent changes
```

**Good**:
```typescript
try {
  const result = await updateProject(id, data, etag);
} catch (error) {
  if (error.status === 412) {
    const current = await fetchProject(id);
    showConflictDialog(current);
  }
}
```

### 3. Refresh ETag After Updates

**Bad**:
```typescript
const project = await fetchProject(id);
await updateProject(id, data, project.etag);
// Still using old ETag for next update
```

**Good**:
```typescript
const project = await fetchProject(id);
const updated = await updateProject(id, data, project.etag);
// Store updated.etag for next update
projectState.setEtag(updated.etag);
```

## Database Schema

ETag stored in `projects` table:

```sql
ALTER TABLE projects ADD COLUMN etag VARCHAR(64);
CREATE INDEX idx_projects_etag ON projects(etag);
```

## Testing

### Manual Test

```bash
# 1. Create project
PROJECT_ID=$(curl -X POST /projects -d '{"name":"Test"}' | jq -r '.result.project_id')
ETAG=$(curl GET /projects/$PROJECT_ID | jq -r '.result.etag')

# 2. Update with valid ETag
curl -X PUT /projects/$PROJECT_ID \
  -H "If-Match: $ETAG" \
  -d '{"name":"Updated"}'
# Should succeed

# 3. Update with stale ETag
curl -X PUT /projects/$PROJECT_ID \
  -H "If-Match: $OLD_ETAG" \
  -d '{"name":"Concurrent"}'
# Should return 412
```

### Unit Tests

```python
async def test_etag_optimistic_locking():
    # Create project
    project = await create_project()
    etag = project.etag
    
    # Update with valid ETag
    updated = await update_project(project.id, {"name": "New"}, etag)
    assert updated.status_code == 200
    
    # Update with stale ETag
    conflict = await update_project(project.id, {"name": "Conflict"}, etag)
    assert conflict.status_code == 412
    assert "ETag mismatch" in conflict.json()["detail"]
```

## References

- [HTTP ETag Spec (RFC 7232)](https://tools.ietf.org/html/rfc7232)
- [Optimistic Locking Pattern](https://martinfowler.com/eaaCatalog/optimisticOfflineLock.html)
- `services/api/src/apex/api/common/etag.py` - ETag utilities
- `services/api/src/apex/api/routes/projects.py` - PUT endpoint implementation

