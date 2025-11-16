# GDPR & CCPA Compliance Documentation

Complete compliance documentation for GDPR (EU) and CCPA (California) regulations.

## Overview

SIGN X Studio Clone handles personal data and must comply with:
- **GDPR**: General Data Protection Regulation (EU)
- **CCPA**: California Consumer Privacy Act (US)

## Data Retention Policies

### Project Data

| Data Type | Retention Period | Rationale |
|-----------|-----------------|-----------|
| **Projects** | 7 years | Engineering records requirement |
| **Project Events** | Indefinite | Audit trail |
| **Project Payloads** | 7 years | Design history |
| **Files (PDFs)** | 7 years | Engineering documentation |

### User Data

| Data Type | Retention Period | Rationale |
|-----------|-----------------|-----------|
| **Account Information** | Until deletion request | GDPR right to erasure |
| **Audit Logs** | 7 years | Compliance requirement |
| **Email Addresses** | Until deletion request | PII protection |

## Right to Erasure (GDPR Article 17)

### Implementation

```python
# services/api/src/apex/api/routes/users.py
@router.delete("/users/{user_id}/data")
async def delete_user_data(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(...),
):
    # Verify authorization (user or admin)
    await verify_deletion_authorization(user_id, authorization)
    
    # Anonymize projects
    await anonymize_user_projects(user_id, db)
    
    # Anonymize audit logs
    await anonymize_audit_logs(user_id, db)
    
    # Delete account
    await delete_user_account(user_id, db)
    
    # Log deletion
    await log_event(
        db,
        user_id,
        "user.data_deleted",
        actor=user_id,
        data={"gdpr_request": True, "timestamp": datetime.now(timezone.utc).isoformat()}
    )
    
    return make_envelope(
        data={"status": "deleted", "user_id": user_id},
        confidence=1.0
    )
```

### Anonymization

```python
async def anonymize_user_projects(user_id: str, db: AsyncSession):
    # Update projects
    await db.execute(
        update(Project)
        .where(Project.created_by == user_id)
        .values(
            created_by="<deleted>",
            customer="<redacted>",
            description=None  # Remove PII
        )
    )
    
    # Keep project structure (engineering value)
    # But remove identifiable information
```

### Audit Log Anonymization

```python
async def anonymize_audit_logs(user_id: str, db: AsyncSession):
    # Anonymize actor field
    await db.execute(
        update(ProjectEvent)
        .where(ProjectEvent.actor == user_id)
        .values(actor="<deleted>")
    )
    
    # Remove PII from data JSONB
    events = await db.execute(
        select(ProjectEvent).where(
            ProjectEvent.data["user_email"].astext == user_id
        )
    )
    
    for event in events.scalars():
        data = event.data
        if "user_email" in data:
            data["user_email"] = "<redacted>"
        if "customer" in data:
            data["customer"] = "<redacted>"
        event.data = data
    
    await db.commit()
```

## Data Portability (GDPR Article 20)

### Export User Data

```python
@router.get("/users/{user_id}/export")
async def export_user_data(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(...),
):
    # Verify authorization
    await verify_export_authorization(user_id, authorization)
    
    # Collect all user data
    export_data = {
        "user_id": user_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "projects": [],
        "events": [],
        "files": [],
    }
    
    # Export projects
    projects = await db.execute(
        select(Project).where(Project.created_by == user_id)
    )
    for project in projects.scalars():
        export_data["projects"].append({
            "project_id": project.project_id,
            "name": project.name,
            "status": project.status,
            "created_at": project.created_at.isoformat(),
            "cost_snapshot": project.cost_snapshot,
        })
    
    # Export events
    events = await db.execute(
        select(ProjectEvent).where(
            ProjectEvent.actor == user_id
        ).order_by(ProjectEvent.created_at)
    )
    for event in events.scalars():
        export_data["events"].append({
            "event_type": event.event_type,
            "timestamp": event.created_at.isoformat(),
            "data": event.data,
        })
    
    # Export file references
    # (Note: Actual files remain in storage)
    
    return make_envelope(
        data=export_data,
        confidence=1.0
    )
```

### Export Format

**JSON Format:**
```json
{
  "user_id": "user_123",
  "exported_at": "2025-01-27T10:00:00Z",
  "projects": [
    {
      "project_id": "proj_abc",
      "name": "Main Street Sign",
      "status": "submitted",
      "created_at": "2025-01-01T00:00:00Z",
      "cost_snapshot": {
        "total": 2500.00
      }
    }
  ],
  "events": [...]
}
```

**CSV Format (Alternative):**
```bash
curl https://api.example.com/users/user_123/export?format=csv \
  -H "Authorization: Bearer $TOKEN" \
  > user_data_export.csv
```

## Consent Management

### GDPR Cookie Banner

For frontend applications:

```typescript
// components/CookieConsent.tsx
function CookieConsent() {
  const [consent, setConsent] = useState<ConsentState | null>(null);
  
  useEffect(() => {
    // Check existing consent
    const stored = localStorage.getItem("cookie_consent");
    if (stored) {
      setConsent(JSON.parse(stored));
    }
  }, []);
  
  const handleAccept = (necessary: boolean, analytics: boolean) => {
    const newConsent = {
      necessary: true,  // Always required
      analytics: analytics,
      marketing: false,
      timestamp: new Date().toISOString(),
    };
    
    localStorage.setItem("cookie_consent", JSON.stringify(newConsent));
    
    // Send to backend
    fetch("/api/consent", {
      method: "POST",
      body: JSON.stringify(newConsent),
    });
    
    setConsent(newConsent);
  };
  
  if (consent) return null;
  
  return (
    <CookieBanner
      onAccept={handleAccept}
      onReject={() => handleAccept(true, false)}
    />
  );
}
```

### Consent Tracking

```python
# services/api/src/apex/api/routes/consent.py
@router.post("/consent")
async def record_consent(
    consent: ConsentModel,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Store consent
    consent_record = ConsentRecord(
        user_id=consent.user_id,
        necessary=consent.necessary,
        analytics=consent.analytics,
        marketing=consent.marketing,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        timestamp=datetime.now(timezone.utc),
    )
    db.add(consent_record)
    await db.commit()
    
    return make_envelope(data={"status": "recorded"}, confidence=1.0)
```

## Data Processing Records (GDPR Article 30)

### Processing Activities Log

```python
# Documented processing activities
PROCESSING_ACTIVITIES = {
    "project_creation": {
        "purpose": "Sign design project management",
        "data_categories": ["name", "customer", "email"],
        "recipients": ["internal_team", "pm_system"],
        "retention": "7 years",
        "security_measures": ["encryption_at_rest", "access_controls"],
    },
    "report_generation": {
        "purpose": "Engineering calculation reports",
        "data_categories": ["project_data", "calculations"],
        "recipients": ["project_owner"],
        "retention": "7 years",
        "security_measures": ["pdf_encryption", "access_logs"],
    },
}
```

## CCPA-Specific Requirements

### California Consumer Rights

1. **Right to Know** (What personal information is collected)
   - Provide data categories collected
   - Sources of personal information
   - Business purpose for collection

2. **Right to Delete**
   - Same as GDPR right to erasure
   - Exceptions: Legal requirements, business needs

3. **Right to Opt-Out** (Sale of personal information)
   - APEX does not sell personal information
   - No opt-out mechanism required

4. **Right to Non-Discrimination**
   - Cannot deny service for exercising rights

### CCPA Compliance

```python
# services/api/src/apex/api/routes/ccpa.py
@router.get("/ccpa/disclose")
async def disclose_personal_information(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    CCPA Section 1798.100: Right to know what personal information is collected
    """
    disclosure = {
        "categories_collected": [
            "Identifiers" (email, name),
            "Commercial information" (projects, costs),
            "Internet activity" (IP address, user agent),
        ],
        "sources": [
            "Directly from consumer",
            "Automatically via API usage",
        ],
        "business_purposes": [
            "Provide engineering calculation services",
            "Project management",
            "Communication",
        ],
        "categories_shared": [],  # Not shared with third parties
        "sold": False,  # Personal information not sold
    }
    
    return make_envelope(data=disclosure, confidence=1.0)
```

## Data Protection Measures

### Encryption

- **At Rest**: AES-256 encryption (PostgreSQL, MinIO)
- **In Transit**: TLS 1.3 (HTTPS)
- **Database**: Column-level encryption for PII

### Access Controls

- Role-based access control (RBAC)
- Audit logging for all data access
- Regular access reviews

### Data Minimization

- Collect only necessary data
- Regular data cleanup of old records
- Anonymization when possible

## Compliance Reports

### Generate Compliance Report

```python
@router.get("/admin/compliance-report")
async def generate_compliance_report(
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db),
    admin_token: str = Header(..., alias="X-Admin-Token"),
):
    # Verify admin
    await verify_admin(admin_token)
    
    report = {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "data_requests": {
            "deletions": await count_deletion_requests(start_date, end_date, db),
            "exports": await count_export_requests(start_date, end_date, db),
        },
        "data_retention": {
            "projects_retained": await count_projects_retained(db),
            "events_retained": await count_events_retained(db),
        },
        "consent_records": {
            "total": await count_consents(db),
            "opted_out": await count_opt_outs(db),
        },
    }
    
    return make_envelope(data=report, confidence=1.0)
```

## Privacy Policy

### Required Disclosures

1. **What Data We Collect**
   - Email address
   - Project information
   - Usage data

2. **How We Use Data**
   - Provide services
   - Improve platform
   - Compliance

3. **Data Sharing**
   - Not sold to third parties
   - Shared only with PM systems (KeyedIn, OpenProject) as configured

4. **User Rights**
   - Right to access
   - Right to deletion
   - Right to portability

---

**Next Steps:**
- [**Audit Trail Documentation**](audit-trail.md)
- [**Security Hardening**](../security/security-hardening.md)

