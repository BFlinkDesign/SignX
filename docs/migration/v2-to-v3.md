# Migration Guide: v2 to v3

Migration guide for upgrading from API v2 to v3 (Envelope pattern).

## Overview

v3 introduces the Envelope response pattern with:
- Standardized response structure
- Deterministic outputs (content_sha256)
- Confidence scoring
- Enhanced traceability

## Breaking Changes

### Response Format

**v2 (Before):**
```json
{
  "data": {
    "project_id": "proj_123",
    "name": "My Project"
  }
}
```

**v3 (After):**
```json
{
  "model_version": "1.0",
  "route": "/projects",
  "request_id": "req_abc123",
  "timestamp": "2025-01-27T10:00:00Z",
  "inputs": {...},
  "assumptions": [],
  "confidence": 0.95,
  "trace": {...},
  "content_sha256": "abc123...",
  "data": {
    "project_id": "proj_123",
    "name": "My Project"
  }
}
```

### Deprecated Endpoints

| Endpoint | Status | Replacement |
|----------|--------|-------------|
| `/api/v2/projects` | Deprecated | `/projects` |
| `/api/v2/calculate` | Removed | `/signage/common/cabinets/derive` |

**Deprecation Schedule:**
- v2 endpoints available until: **2025-06-01**
- Deprecation notice added: **2025-01-01**
- Migration deadline: **2025-05-01**

## Frontend Migration

### Update API Client

**Before (v2):**
```typescript
// src/api/client.ts
interface ApiResponse<T> {
  data: T;
}

async function fetchProjects(): Promise<Project[]> {
  const response = await fetch('/api/v2/projects');
  const json: ApiResponse<Project[]> = await response.json();
  return json.data;
}
```

**After (v3):**
```typescript
// src/api/client.ts
interface Envelope<T> {
  model_version: string;
  route: string;
  request_id: string;
  timestamp: string;
  inputs: Record<string, any>;
  assumptions: string[];
  confidence: number;
  trace: {...};
  content_sha256: string;
  data: T;
}

async function fetchProjects(): Promise<Project[]> {
  const response = await fetch('/projects');
  const envelope: Envelope<Project[]> = await response.json();
  
  // Handle assumptions/warnings
  if (envelope.assumptions.length > 0) {
    envelope.assumptions.forEach(assumption => {
      if (assumption.includes('Warning:')) {
        showSnackbar(assumption, 'warning');
      }
    });
  }
  
  // Display confidence
  displayConfidenceBadge(envelope.confidence);
  
  return envelope.data;
}
```

### Parse Envelope

```typescript
// src/api/envelope.ts
export function parseEnvelope<T>(envelope: Envelope<T>): {
  data: T;
  confidence: number;
  assumptions: string[];
  warnings: string[];
} {
  return {
    data: envelope.data,
    confidence: envelope.confidence,
    assumptions: envelope.assumptions,
    warnings: envelope.assumptions.filter(a => 
      a.toLowerCase().includes('warning') || 
      a.toLowerCase().includes('review required')
    ),
  };
}
```

### Handle Confidence

```typescript
// src/components/ConfidenceBadge.tsx
function ConfidenceBadge({ confidence }: { confidence: number }) {
  const color = 
    confidence >= 0.9 ? 'green' :
    confidence >= 0.7 ? 'yellow' :
    confidence >= 0.5 ? 'orange' : 'red';
  
  return (
    <Badge color={color}>
      Confidence: {(confidence * 100).toFixed(0)}%
    </Badge>
  );
}
```

## Backend Migration

### Migrate Routes

**Before:**
```python
@router.post("/projects")
async def create_project(req: ProjectCreate) -> dict:
    project = Project(...)
    db.add(project)
    await db.commit()
    return {"data": project.model_dump()}
```

**After:**
```python
@router.post("/projects")
async def create_project(
    req: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    project = Project(...)
    db.add(project)
    await db.commit()
    
    return make_envelope(
        result=project.model_dump(),
        assumptions=["Created in draft status"],
        confidence=0.95,
        inputs=req.model_dump(),
        outputs={"project_id": project.project_id},
    )
```

### Update Tests

**Before:**
```python
def test_create_project():
    response = client.post("/projects", json={"name": "Test"})
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Test"
```

**After:**
```python
def test_create_project():
    response = client.post("/projects", json={"name": "Test"})
    assert response.status_code == 200
    envelope = response.json()
    assert envelope["data"]["name"] == "Test"
    assert "confidence" in envelope
    assert 0.0 <= envelope["confidence"] <= 1.0
    assert "content_sha256" in envelope
```

## Deprecation Warnings

### API Response Headers

v2 endpoints return deprecation warnings:

```
X-API-Deprecated: true
X-API-Deprecation-Date: 2025-06-01
X-API-Sunset-Date: 2025-06-01
Link: </projects>; rel="successor-version"
```

### Migration Script

```python
# scripts/migrate_v2_to_v3.py
async def migrate_client(client_config: dict):
    """
    Migrate client configuration from v2 to v3.
    """
    # Update base URL
    if "api/v2" in client_config["base_url"]:
        client_config["base_url"] = client_config["base_url"].replace(
            "/api/v2", ""
        )
    
    # Update response parsing
    client_config["response_parser"] = "envelope"  # Was "data"
    
    return client_config
```

## Testing Migration

### Checklist

- [ ] Update API client to parse Envelope
- [ ] Handle assumptions/warnings in UI
- [ ] Display confidence scores
- [ ] Update error handling for new structure
- [ ] Test all endpoints return Envelope
- [ ] Verify content_sha256 deterministic
- [ ] Test idempotency with new headers
- [ ] Update tests for Envelope structure

### Validation

```bash
# Test all endpoints return Envelope
pytest tests/contract/test_envelope_structure.py

# Test determinism
pytest tests/contract/test_determinism.py

# Test migration
pytest tests/migration/test_v2_to_v3.py
```

---

**Next Steps:**
- [**API Reference**](../api/api-reference.md) - v3 endpoint documentation
- [**Envelope Pattern**](../api/envelope-pattern.md) - Pattern guide

