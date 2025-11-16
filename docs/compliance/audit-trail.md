# Audit Trail Documentation

Complete documentation for audit logging and compliance reporting.

## Overview

SIGN X Studio Clone maintains immutable audit trails for:
- Project lifecycle events
- User actions
- System changes
- Compliance requirements

## ProjectEvent Schema

### Database Schema

```sql
CREATE TABLE project_events (
    event_id SERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    actor VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    data JSONB,
    
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

CREATE INDEX idx_events_project_time ON project_events(project_id, timestamp DESC);
CREATE INDEX idx_events_actor ON project_events(actor, timestamp DESC);
CREATE INDEX idx_events_type ON project_events(event_type, timestamp DESC);
```

### Event Types

| Event Type | Description | Data Schema |
|------------|-------------|-------------|
| `project.created` | Project created | `{name, customer, created_by}` |
| `project.updated` | Project metadata updated | `{changes, previous_values}` |
| `project.status_changed` | Status transition | `{from_status, to_status, reason}` |
| `project.submitted` | Project submitted | `{submission_id, idempotency_key, pm_task_id}` |
| `project.accepted` | Project approved | `{approved_by, approval_notes}` |
| `project.rejected` | Project rejected | `{rejected_by, rejection_reason}` |
| `payload.saved` | Design payload saved | `{payload_id, module, sha256}` |
| `report.generated` | PDF report generated | `{pdf_ref, sha256, task_id}` |
| `file.uploaded` | File uploaded | `{file_key, sha256, size_bytes}` |
| `user.data_deleted` | GDPR deletion | `{gdpr_request, anonymized_fields}` |

## Querying Audit Logs

### By Project

```sql
SELECT 
    event_type,
    actor,
    timestamp,
    data
FROM project_events
WHERE project_id = 'proj_abc123'
ORDER BY timestamp DESC;
```

### By User

```sql
SELECT 
    project_id,
    event_type,
    timestamp,
    data
FROM project_events
WHERE actor = 'user@example.com'
ORDER BY timestamp DESC
LIMIT 100;
```

### By Event Type

```sql
SELECT 
    project_id,
    actor,
    timestamp,
    data
FROM project_events
WHERE event_type = 'project.submitted'
  AND timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;
```

## Suspicious Pattern Detection

### Multiple Failed Submissions

```sql
SELECT 
    actor,
    project_id,
    COUNT(*) as attempts,
    MIN(timestamp) as first_attempt,
    MAX(timestamp) as last_attempt
FROM project_events
WHERE event_type = 'project.submitted'
  AND data->>'success' = 'false'
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY actor, project_id
HAVING COUNT(*) > 5;
```

### Unusual Access Patterns

```sql
SELECT 
    actor,
    COUNT(DISTINCT project_id) as projects_accessed,
    COUNT(*) as total_events
FROM project_events
WHERE timestamp > NOW() - INTERVAL '1 day'
  AND actor != 'system'
GROUP BY actor
HAVING COUNT(DISTINCT project_id) > 100  -- Threshold
   OR COUNT(*) > 1000;
```

### Access Outside Business Hours

```sql
SELECT 
    actor,
    project_id,
    event_type,
    timestamp
FROM project_events
WHERE EXTRACT(HOUR FROM timestamp) NOT BETWEEN 8 AND 18
  AND event_type IN ('project.updated', 'project.submitted')
  AND actor != 'system'
ORDER BY timestamp DESC;
```

## Compliance Reports

### GDPR Deletion Log

```sql
SELECT 
    event_id,
    project_id,
    actor,
    timestamp,
    data->>'gdpr_request' as gdpr_request,
    data->>'anonymized_fields' as anonymized_fields
FROM project_events
WHERE event_type = 'user.data_deleted'
ORDER BY timestamp DESC;
```

### Project Lifecycle Report

```sql
WITH project_timeline AS (
    SELECT 
        project_id,
        MAX(CASE WHEN event_type = 'project.created' THEN timestamp END) as created_at,
        MAX(CASE WHEN event_type = 'project.submitted' THEN timestamp END) as submitted_at,
        MAX(CASE WHEN event_type = 'project.accepted' THEN timestamp END) as accepted_at
    FROM project_events
    GROUP BY project_id
)
SELECT 
    project_id,
    created_at,
    submitted_at,
    accepted_at,
    EXTRACT(EPOCH FROM (submitted_at - created_at))/3600 as hours_to_submit,
    EXTRACT(EPOCH FROM (accepted_at - submitted_at))/3600 as hours_to_accept
FROM project_timeline
WHERE created_at > NOW() - INTERVAL '30 days';
```

## Immutability Guarantee

### Append-Only Table

The `project_events` table is append-only:
- No UPDATE statements allowed
- No DELETE statements allowed
- Only INSERT operations

### Database Constraints

```sql
-- Prevent updates
CREATE TRIGGER prevent_event_update
BEFORE UPDATE ON project_events
FOR EACH ROW
EXECUTE FUNCTION raise_exception();

-- Prevent deletes
CREATE TRIGGER prevent_event_delete
BEFORE DELETE ON project_events
FOR EACH ROW
EXECUTE FUNCTION raise_exception();
```

### Application-Level Protection

```python
# services/api/src/apex/api/common/helpers.py
async def log_event(
    db: AsyncSession,
    project_id: str,
    event_type: str,
    actor: str,
    data: dict,
) -> ProjectEvent:
    event = ProjectEvent(
        project_id=project_id,
        event_type=event_type,
        actor=actor,
        data=data,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.flush()
    return event  # No update/delete methods exposed
```

## CSV Export

### Export Audit Log

```python
@router.get("/admin/audit-export")
async def export_audit_log(
    project_id: str | None = None,
    actor: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    admin_token: str = Header(..., alias="X-Admin-Token"),
):
    await verify_admin(admin_token)
    
    query = select(ProjectEvent)
    if project_id:
        query = query.where(ProjectEvent.project_id == project_id)
    if actor:
        query = query.where(ProjectEvent.actor == actor)
    if start_date:
        query = query.where(ProjectEvent.timestamp >= start_date)
    if end_date:
        query = query.where(ProjectEvent.timestamp <= end_date)
    
    events = await db.execute(query.order_by(ProjectEvent.timestamp))
    
    # Generate CSV
    csv_lines = ["event_id,project_id,event_type,actor,timestamp,data\n"]
    for event in events.scalars():
        csv_lines.append(
            f"{event.event_id},{event.project_id},{event.event_type},"
            f"{event.actor},{event.timestamp.isoformat()},"
            f"{json.dumps(event.data)}\n"
        )
    
    return Response(
        content="".join(csv_lines),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"}
    )
```

## Retention Policy

### Event Retention

- **Indefinite**: All events retained for compliance
- **Archival**: Events older than 7 years moved to cold storage
- **Query Performance**: Index on `(project_id, timestamp)` for fast lookups

### Archive Old Events

```python
# Script: scripts/archive_old_events.py
async def archive_old_events(cutoff_date: date):
    # Query old events
    old_events = await db.execute(
        select(ProjectEvent).where(
            ProjectEvent.timestamp < cutoff_date
        )
    )
    
    # Export to S3
    for event in old_events.scalars():
        s3_key = f"audit-archive/{event.project_id}/{event.event_id}.json"
        await s3_client.put_object(
            Bucket="apex-audit-archive",
            Key=s3_key,
            Body=json.dumps({
                "event_id": event.event_id,
                "project_id": event.project_id,
                "event_type": event.event_type,
                "actor": event.actor,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data,
            })
        )
    
    # Delete from primary table (after verification)
    # Note: Keep metadata row with reference to S3 location
```

---

**Next Steps:**
- [**GDPR/CCPA Compliance**](gdpr-ccpa.md)
- [**Security Hardening**](../security/security-hardening.md)

