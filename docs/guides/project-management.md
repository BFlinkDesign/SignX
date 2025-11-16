# Project Management Guide

Complete guide to managing projects in SIGN X Studio Clone.

## Overview

Projects are the central entity in the system. Each project represents a sign design with:
- **Metadata**: Name, customer, site information
- **State**: Draft → Estimating → Submitted → Accepted/Rejected
- **Payload**: Design configuration and calculations
- **Audit Trail**: Immutable event log

## Creating a Project

### Basic Project Creation

```bash
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "demo",
    "name": "Main Street Sign",
    "customer": "Acme Corporation",
    "description": "Outdoor directional sign",
    "created_by": "engineer@example.com"
  }'
```

**Response:**
```json
{
  "result": {
    "project_id": "proj_abc123def456",
    "name": "Main Street Sign",
    "status": "draft",
    "etag": "xyz789"
  },
  "confidence": 0.95
}
```

### Project States

Projects progress through states:

1. **`draft`** - Initial creation, editable
2. **`estimating`** - Design in progress, pricing calculated
3. **`submitted`** - Submitted for engineering review
4. **`accepted`** - Approved, final state
5. **`rejected`** - Rejected, final state

## Reading Projects

### List Projects

```bash
# List all projects
curl http://localhost:8000/projects

# Search by name
curl "http://localhost:8000/projects?q=Main%20Street"

# Filter by status
curl "http://localhost:8000/projects?status=submitted"

# Pagination
curl "http://localhost:8000/projects?skip=20&limit=10"
```

### Get Single Project

```bash
curl http://localhost:8000/projects/proj_abc123def456
```

**Response includes:**
- Project metadata
- Current status
- Latest payload (if exists)
- ETag for optimistic locking

## Updating Projects

### Update Metadata

```bash
curl -X PUT http://localhost:8000/projects/proj_abc123def456 \
  -H "Content-Type: application/json" \
  -H "If-Match: xyz789" \
  -d '{
    "name": "Updated Name",
    "customer": "New Customer"
  }'
```

**Important**: Include `If-Match` header with current ETag to prevent concurrent modification conflicts.

### State Transitions

Valid transitions:
- `draft` → `estimating` (when design starts)
- `estimating` → `submitted` (when ready for review)
- `submitted` → `accepted` or `rejected` (final decision)

```bash
curl -X PUT http://localhost:8000/projects/proj_abc123def456 \
  -H "Content-Type: application/json" \
  -H "If-Match: xyz789" \
  -d '{}' \
  -G --data-urlencode "new_status=estimating"
```

Invalid transitions return `412 Precondition Failed`.

## Project Payloads

### Save Design Payload

```bash
curl -X POST http://localhost:8000/projects/proj_abc123def456/payload \
  -H "Content-Type: application/json" \
  -d '{
    "module": "signage.single_pole",
    "config": {
      "site": {...},
      "cabinets": {...},
      "support": {...},
      "foundation": {...}
    },
    "files": ["uploads/drawing.pdf"],
    "cost_snapshot": {...}
  }'
```

**Response:**
```json
{
  "result": {
    "payload_id": 1,
    "sha256": "abc123...",
    "duplicate": false
  }
}
```

### Payload Deduplication

If a payload with the same SHA256 already exists, the endpoint returns the existing payload (no duplicate created).

## Project Events

### View Audit Trail

```bash
curl http://localhost:8000/projects/proj_abc123def456/events
```

**Response:**
```json
{
  "result": {
    "events": [
      {
        "event_id": 1,
        "event_type": "project.created",
        "actor": "engineer@example.com",
        "timestamp": "2025-01-01T00:00:00Z",
        "data": {"name": "Main Street Sign"}
      },
      {
        "event_id": 2,
        "event_type": "payload.saved",
        "actor": "system",
        "timestamp": "2025-01-01T01:00:00Z",
        "data": {"module": "signage.single_pole", "sha256": "abc123..."}
      }
    ]
  }
}
```

## Submitting Projects

### Submit for Review

```bash
curl -X POST http://localhost:8000/projects/proj_abc123def456/submit \
  -H "Idempotency-Key: submit-123"
```

**Features:**
- Idempotent: Same `Idempotency-Key` returns same result
- State transition: `estimating` → `submitted`
- Enqueues PM dispatch task
- Sends email notification (if manager email available)

**Response:**
```json
{
  "result": {
    "project_id": "proj_abc123def456",
    "status": "submitted",
    "project_number": "PRJ-12345678",
    "pm_task_id": "task-abc",
    "idempotent": false
  }
}
```

## Best Practices

### 1. Always Use ETags

```python
# Get project with ETag
response = get_project(project_id)
etag = response["result"]["etag"]

# Update with ETag
update_project(project_id, changes, if_match=etag)
```

### 2. Handle Concurrent Updates

If `If-Match` header doesn't match:
- Response: `412 Precondition Failed`
- Solution: Re-fetch project and retry update

### 3. Use Idempotency Keys

For submission operations:
```bash
Idempotency-Key: submit-{project_id}-{timestamp}
```

### 4. Monitor Event Log

Regularly check events for:
- Unusual state transitions
- Missing payloads
- Submission failures

## Error Handling

### Common Errors

| Status | Code | Meaning | Solution |
|--------|------|---------|----------|
| 404 | Not Found | Project doesn't exist | Verify project_id |
| 412 | Precondition Failed | ETag mismatch or invalid transition | Re-fetch and retry |
| 422 | Unprocessable Entity | Validation error | Check request body |

### Example Error Response

```json
{
  "result": null,
  "assumptions": ["Invalid state transition"],
  "confidence": 0.1,
  "trace": {
    "data": {
      "error_id": "error-abc123",
      "error_type": "HTTPException"
    }
  }
}
```

## Next Steps

- [**Sign Design Workflow**](sign-design-workflow.md) - Complete design process
- [**File Management**](file-management.md) - Upload and attach files
- [**API Reference**](../reference/api-endpoints.md) - Complete API docs

