# OpenProject Dispatch Integration

Guide for dispatching CalcuSign projects to OpenProject for project management.

## Overview

OpenProject integration enables:
- Automatic ticket creation on project submission
- Status updates from OpenProject
- Cost tracking integration
- Resource assignment

## Authentication

### OAuth2 Flow

1. **Register Application**
   ```
   Redirect URI: https://api.example.com/auth/openproject/callback
   Scopes: api_v3
   ```

2. **Obtain Authorization Code**
   ```
   GET https://openproject.example.com/oauth/authorize?
     client_id=your-client-id&
     redirect_uri=https://api.example.com/auth/openproject/callback&
     response_type=code&
     scope=api_v3
   ```

3. **Exchange for Token**
   ```python
   response = httpx.post(
       "https://openproject.example.com/oauth/token",
       data={
           "grant_type": "authorization_code",
           "code": authorization_code,
           "client_id": CLIENT_ID,
           "client_secret": CLIENT_SECRET,
           "redirect_uri": REDIRECT_URI,
       }
   )
   access_token = response.json()["access_token"]
   ```

### API Key Alternative

```python
headers = {
    "Authorization": f"Basic {base64.b64encode(f'apikey:{API_KEY}'.encode()).decode()}",
    "Content-Type": "application/json"
}
```

## Ticket Creation

### Dispatch on Submission

```python
# services/api/src/apex/api/routes/submission.py
@router.post("/projects/{project_id}/submit")
async def submit_project(
    project_id: str,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
):
    # Submit project
    project = await submit_project_internal(project_id, db)
    
    # Dispatch to OpenProject
    ticket_id = await dispatch_to_openproject(project, db)
    
    # Store ticket reference
    await log_event(
        db,
        project_id,
        "project.dispatched",
        actor="system",
        data={"ticket_id": ticket_id, "system": "openproject"}
    )
    
    return make_envelope(...)
```

### Ticket Payload

```python
async def dispatch_to_openproject(project: Project, db: AsyncSession) -> str:
    payload = {
        "subject": f"Sign Design: {project.name}",
        "description": {
            "format": "markdown",
            "raw": f"""
# Project: {project.name}
- **Customer**: {project.customer}
- **Status**: {project.status}
- **Confidence**: {project.confidence:.2%}
- **Estimated Cost**: ${project.cost_snapshot.get('total', 0):,.2f}
            
## Design Summary
{format_project_summary(project)}
            """
        },
        "type": {
            "_links": {
                "self": {"href": "/api/v3/types/1"}  # Task type
            }
        },
        "status": {
            "_links": {
                "self": {"href": "/api/v3/statuses/1"}  # New status
            }
        },
        "customField": {
            "1": project.project_id,  # APEX Project ID
            "2": project.confidence,  # Confidence score
        },
        "_links": {
            "assignee": {
                "href": f"/api/v3/users/{project.assigned_user_id}"
            }
        }
    }
    
    response = await openproject_client.post(
        "/api/v3/work_packages",
        json=payload
    )
    
    ticket_id = response.json()["id"]
    return ticket_id
```

## Status Polling

### Poll Ticket Status

```python
@celery_app.task(name="openproject.sync_status", bind=True)
def sync_openproject_status(self):
    # Find projects with OpenProject tickets
    events = db.query(ProjectEvent).filter(
        ProjectEvent.event_type == "project.dispatched",
        ProjectEvent.data["system"].astext == "openproject"
    ).all()
    
    for event in events:
        ticket_id = event.data["ticket_id"]
        
        # Poll OpenProject
        ticket = await openproject_client.get(
            f"/api/v3/work_packages/{ticket_id}"
        )
        
        # Map OpenProject status to APEX
        op_status = ticket["status"]["name"]
        apex_status = map_openproject_status_to_apex(op_status)
        
        # Update if changed
        project = await get_project(event.project_id, db)
        if project.status != apex_status:
            await update_project_status(project.project_id, apex_status)
```

### Status Mapping

```python
OPENPROJECT_TO_APEX_STATUS = {
    "New": "submitted",
    "In Progress": "estimating",
    "Review": "estimating",
    "Closed": "accepted",
    "Rejected": "rejected",
}
```

## Circuit Breaker Configuration

### Implementation

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_openproject_api(endpoint: str, payload: dict):
    try:
        response = await httpx.post(
            f"{OPENPROJECT_API_URL}{endpoint}",
            json=payload,
            headers=OPENPROJECT_HEADERS,
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError:
        raise  # Counts as failure
```

### Circuit Breaker State

```python
# Check circuit state
if openproject_circuit.current_state == "open":
    # Fallback: Log to queue, retry later
    await dlq_push("openproject", payload)
    return None
```

## Error Handling

### Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60)
)
async def dispatch_to_openproject(project: Project) -> str:
    # Create ticket with retries
    ...
```

### Error Responses

OpenProject returns errors in this format:

```json
{
  "errorIdentifier": "urn:openproject-org:api:v3:errors:InvalidQuery",
  "message": "Invalid query",
  "_embedded": {
    "errors": [
      {
        "message": "Query is invalid",
        "attribute": "filters"
      }
    ]
  }
}
```

## Configuration

### Environment Variables

```bash
OPENPROJECT_API_URL=https://openproject.example.com
OPENPROJECT_CLIENT_ID=your-client-id
OPENPROJECT_CLIENT_SECRET=your-client-secret
OPENPROJECT_REDIRECT_URI=https://api.example.com/auth/openproject/callback
OPENPROJECT_SYNC_ENABLED=true
OPENPROJECT_SYNC_INTERVAL=300  # 5 minutes
```

---

**Next Steps:**
- [**Email Notifications**](email-notifications.md)
- [**API Reference**](../api/api-reference.md)

