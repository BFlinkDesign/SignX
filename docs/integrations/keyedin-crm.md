# KeyedIn CRM Integration Guide

Complete guide for integrating SIGN X Studio Clone with KeyedIn CRM.

## Overview

KeyedIn CRM integration enables:
- Automatic project creation from KeyedIn opportunities
- Bi-directional status synchronization
- Cost estimation updates
- Submission notifications

## Webhook Setup

### Configure Webhook in KeyedIn

1. **Navigate to Webhooks**
   - KeyedIn Admin → Integrations → Webhooks

2. **Create Webhook**
   ```
   URL: https://api.example.com/webhooks/keyedin
   Method: POST
   Events: Opportunity Created, Opportunity Updated
   ```

3. **Authentication**
   - Header: `X-KeyedIn-Token`
   - Value: Your webhook secret

### Webhook Payload

KeyedIn sends this when opportunity is created:

```json
{
  "event": "opportunity.created",
  "timestamp": "2025-01-27T10:00:00Z",
  "opportunity": {
    "id": "opp_123",
    "name": "Main Street Sign Project",
    "customer": {
      "id": "cust_456",
      "name": "Acme Corporation"
    },
    "estimated_value": 5000.00,
    "stage": "prospecting"
  }
}
```

### Webhook Handler

```python
# services/api/src/apex/api/routes/webhooks.py
@router.post("/webhooks/keyedin")
async def keyedin_webhook(
    payload: dict,
    token: str = Header(..., alias="X-KeyedIn-Token"),
    db: AsyncSession = Depends(get_db),
):
    # Verify token
    if token != settings.KEYEDIN_WEBHOOK_SECRET:
        raise HTTPException(status_code=401)
    
    event = payload.get("event")
    opportunity = payload.get("opportunity")
    
    if event == "opportunity.created":
        # Create project in APEX
        project = await create_project_from_keyedin(opportunity, db)
        
        # Link in KeyedIn (custom field)
        await update_keyedin_custom_field(
            opportunity["id"],
            "apex_project_id",
            project.project_id
        )
    
    return {"status": "ok"}
```

## Data Mapping

### KeyedIn → APEX

```python
def map_keyedin_to_apex(opportunity: dict) -> dict:
    return {
        "account_id": opportunity["customer"]["id"],
        "name": opportunity["name"],
        "customer": opportunity["customer"]["name"],
        "estimated_value": opportunity.get("estimated_value"),
        "keyedin_opportunity_id": opportunity["id"],
        "created_by": "keyedin-sync",
    }
```

### APEX → KeyedIn

```python
async def sync_to_keyedin(project: Project):
    payload = {
        "opportunity_id": project.keyedin_opportunity_id,
        "custom_fields": {
            "apex_status": project.status,
            "apex_confidence": project.confidence,
            "apex_estimated_cost": project.cost_snapshot.get("total"),
            "apex_project_id": project.project_id,
        }
    }
    
    await keyedin_api_client.update_opportunity(payload)
```

## Bi-Directional Sync Strategy

### Status Synchronization

```
KeyedIn Stage          →  APEX Status
─────────────────────────────────────
prospecting           →  draft
qualification         →  estimating
proposal              →  estimating
negotiation           →  submitted
closed_won            →  accepted
closed_lost            →  rejected
```

### Sync Implementation

```python
# Periodic sync job (Celery)
@celery_app.task(name="keyedin.sync", bind=True)
def sync_keyedin_projects(self):
    # Find projects with KeyedIn links
    projects = db.query(Project).filter(
        Project.keyedin_opportunity_id.isnot(None)
    ).all()
    
    for project in projects:
        # Check KeyedIn status
        opportunity = await keyedin_api_client.get_opportunity(
            project.keyedin_opportunity_id
        )
        
        # Update if changed
        if opportunity["stage"] != project.status:
            await update_project_status(
                project.project_id,
                map_keyedin_stage_to_apex(opportunity["stage"])
            )
```

## Error Handling

### Retry with Exponential Backoff

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60)
)
async def call_keyedin_api(endpoint: str, payload: dict):
    try:
        response = await httpx.post(
            f"{KEYEDIN_API_URL}{endpoint}",
            json=payload,
            headers={"Authorization": f"Bearer {KEYEDIN_TOKEN}"},
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error("keyedin.api_error", endpoint=endpoint, error=str(e))
        raise
```

### Dead Letter Queue

Failed webhooks go to DLQ:

```python
@router.post("/webhooks/keyedin")
async def keyedin_webhook(...):
    try:
        # Process webhook
        ...
    except Exception as e:
        # Push to DLQ
        await dlq_push("keyedin", {
            "payload": payload,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        raise
```

## Testing

### Local Testing

```bash
# Start ngrok tunnel
ngrok http 8000

# Update KeyedIn webhook URL to ngrok URL
# Trigger test opportunity creation in KeyedIn
# Verify webhook received
```

### Webhook Verification

```python
# Verify webhook signature (if KeyedIn provides)
def verify_keyedin_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(
        settings.KEYEDIN_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

## Configuration

### Environment Variables

```bash
KEYEDIN_API_URL=https://api.keyedin.com/v1
KEYEDIN_API_KEY=your-api-key
KEYEDIN_WEBHOOK_SECRET=webhook-secret
KEYEDIN_SYNC_ENABLED=true
KEYEDIN_SYNC_INTERVAL=300  # 5 minutes
```

---

**Next Steps:**
- [**OpenProject Integration**](openproject-dispatch.md)
- [**Email Notifications**](email-notifications.md)

