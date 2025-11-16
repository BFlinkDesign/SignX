# Security Hardening Guide

Complete security documentation for SIGN X Studio Clone production deployments.

## Table of Contents

1. [OWASP Top 10 Mitigation](#owasp-top-10-mitigation)
2. [Penetration Testing](#penetration-testing)
3. [Security Audit Logs](#security-audit-logs)
4. [Compliance Documentation](#compliance-documentation)
5. [Vulnerability Scanning](#vulnerability-scanning)
6. [Rate Limiting & DDoS](#rate-limiting--ddos)

## OWASP Top 10 Mitigation

### A01:2021 – Broken Access Control

**Mitigation:**

#### API Authentication

```python
# services/api/src/apex/api/auth.py
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-Apex-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # Validate against database or secrets manager
    if not await validate_api_key(api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return api_key
```

#### Project-Level Authorization

```python
# services/api/src/apex/api/routes/projects.py
@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> ResponseEnvelope:
    project = await require_project(project_id, db)
    
    # Verify user has access to this project
    if not await verify_project_access(api_key, project_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return make_envelope(result=project)
```

#### JWT Token Rotation

```python
# Token rotation policy
TOKEN_EXPIRY = 3600  # 1 hour
TOKEN_REFRESH_THRESHOLD = 300  # Refresh if < 5 minutes remaining

def rotate_token(old_token: str) -> str:
    payload = verify_jwt(old_token)
    if payload["exp"] - time.time() < TOKEN_REFRESH_THRESHOLD:
        return generate_new_token(payload["sub"])
    return old_token
```

### A02:2021 – Cryptographic Failures

**Mitigation:**

#### Encryption at Rest

**PostgreSQL:**
```sql
-- Enable encryption
ALTER DATABASE apex SET encryption_key = '${ENCRYPTION_KEY}';
```

**MinIO/S3:**
```yaml
# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

#### TLS in Transit

```yaml
# Kubernetes Ingress TLS
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: apex-api
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - api.example.com
      secretName: apex-api-tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: apex-api
                port:
                  number: 80
```

### A03:2021 – Injection

**Mitigation:**

#### Parameterized Queries

```python
# SQLAlchemy parameterized queries (automatic)
from sqlalchemy import text

# Safe
result = await db.execute(
    text("SELECT * FROM projects WHERE project_id = :id"),
    {"id": project_id}
)

# NEVER do this:
# result = await db.execute(f"SELECT * FROM projects WHERE project_id = '{project_id}'")
```

#### Input Validation

```python
# Pydantic v2 validation
from pydantic import BaseModel, Field, validator

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    account_id: str = Field(..., pattern=r"^[a-z0-9-]+$")
    
    @validator('name')
    def validate_name(cls, v):
        # Sanitize input
        return v.strip()
```

### A04:2021 – Insecure Design

**Mitigation:**

#### Threat Modeling

Document threat model:
- **Threat**: Unauthorized project access
- **Mitigation**: API key validation, project-level ACLs
- **Verification**: Penetration testing

#### Security by Design

- All endpoints require authentication
- Rate limiting on all public endpoints
- Input validation on all inputs
- Output encoding on all outputs

### A05:2021 – Security Misconfiguration

**Mitigation:**

#### Secure Defaults

```python
# Environment validation
def validate_prod_requirements():
    if settings.ENV == "prod":
        required_vars = [
            "DATABASE_URL",
            "REDIS_URL",
            "MINIO_SECRET_KEY",
        ]
        missing = [v for v in required_vars if not getattr(settings, v, None)]
        if missing:
            raise RuntimeError(f"Missing required env vars: {missing}")
```

#### Security Headers

```python
# services/api/src/apex/api/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response
```

### A06:2021 – Vulnerable Components

**Mitigation:**

#### Dependency Scanning

```yaml
# .github/workflows/security-scan.yml
name: Security Scan
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
```

#### Dependabot

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/services/api"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
```

### A07:2021 – Authentication Failures

**Mitigation:**

#### Session Timeout

```python
# Session management
SESSION_TIMEOUT = 3600  # 1 hour
SESSION_INACTIVITY_TIMEOUT = 900  # 15 minutes

async def check_session(session_id: str):
    session = await get_session(session_id)
    if time.time() - session.last_activity > SESSION_INACTIVITY_TIMEOUT:
        await revoke_session(session_id)
        raise HTTPException(status_code=401, detail="Session expired")
    
    session.last_activity = time.time()
    await update_session(session)
```

### A08:2021 – Software and Data Integrity

**Mitigation:**

#### SHA256 Verification

```python
# File integrity verification
async def verify_file_hash(file_path: Path, expected_hash: str):
    actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
    if actual_hash != expected_hash:
        raise HTTPException(status_code=422, detail="File hash mismatch")
```

#### Code Signing

```bash
# Sign container images
cosign sign --key cosign.key registry.example.com/apex-api:v0.1.0

# Verify on pull
cosign verify --key cosign.pub registry.example.com/apex-api:v0.1.0
```

### A09:2021 – Security Logging Failures

**Mitigation:**

See [Security Audit Logs](#security-audit-logs) section.

### A10:2021 – Server-Side Request Forgery

**Mitigation:**

#### URL Validation

```python
# Validate external URLs
from urllib.parse import urlparse

ALLOWED_DOMAINS = ["api.example.com", "storage.example.com"]

def validate_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc in ALLOWED_DOMAINS
```

## Penetration Testing

### OWASP ZAP Scan

#### Automated Scanning

```bash
#!/bin/bash
# scripts/pen-test-zap.sh

# Start ZAP daemon
docker run -d --name zap -p 8080:8080 \
  owasp/zap2docker-stable zap.sh -daemon \
  -host 0.0.0.0 -port 8080

# Run spider scan
docker exec zap zap-cli quick-scan \
  --self-contained \
  --start-options '-config api.disablekey=true' \
  http://api.example.com

# Generate report
docker exec zap zap-cli report -o /zap/report.html -f html
docker cp zap:/zap/report.html ./pen-test-report-$(date +%Y%m%d).html
```

#### ZAP Baseline Scan

```yaml
# .github/workflows/zap-scan.yml
name: OWASP ZAP Scan
on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly
jobs:
  zap-scan:
    runs-on: ubuntu-latest
    steps:
      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.10.0
        with:
          target: 'https://api.example.com'
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a'
```

### Manual Testing Checklist

1. **Authentication Bypass**
   - [ ] Test API without authentication
   - [ ] Test with invalid API keys
   - [ ] Test session hijacking

2. **Authorization Testing**
   - [ ] Access other users' projects
   - [ ] Elevate privileges
   - [ ] Bypass project-level ACLs

3. **Input Validation**
   - [ ] SQL injection in project names
   - [ ] XSS in user inputs
   - [ ] Command injection in file uploads

4. **Error Handling**
   - [ ] Information disclosure in errors
   - [ ] Stack traces exposed
   - [ ] Sensitive data in logs

## Security Audit Logs

### Audit Log Structure

```python
# services/api/src/apex/api/audit.py
from sqlalchemy import Column, String, DateTime, JSON, Text
from datetime import datetime, timezone

class SecurityAuditLog(Base):
    __tablename__ = "security_audit_logs"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))
    event_type = Column(String(100))  # login, access_denied, etc.
    actor = Column(String(255))  # API key or user ID
    resource_type = Column(String(50))  # project, file, etc.
    resource_id = Column(String(255))
    action = Column(String(100))  # read, write, delete
    ip_address = Column(String(45))
    user_agent = Column(Text)
    details = Column(JSON)  # Additional context
    success = Column(Boolean)
```

### Logging Security Events

```python
async def log_security_event(
    db: AsyncSession,
    event_type: str,
    actor: str,
    resource_type: str,
    resource_id: str,
    action: str,
    success: bool,
    request: Request,
    details: dict | None = None,
):
    audit_log = SecurityAuditLog(
        event_type=event_type,
        actor=actor,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        success=success,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        details=details,
    )
    db.add(audit_log)
    await db.commit()
```

### Querying Audit Logs

#### Suspicious Patterns

```sql
-- Multiple failed login attempts
SELECT actor, COUNT(*) as attempts, MIN(timestamp) as first_attempt, MAX(timestamp) as last_attempt
FROM security_audit_logs
WHERE event_type = 'login_attempt' AND success = false
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY actor
HAVING COUNT(*) > 5;

-- Unusual access patterns
SELECT actor, resource_type, COUNT(*) as accesses
FROM security_audit_logs
WHERE timestamp > NOW() - INTERVAL '1 day'
  AND action = 'read'
GROUP BY actor, resource_type
HAVING COUNT(*) > 1000;

-- Access outside business hours
SELECT actor, resource_id, timestamp
FROM security_audit_logs
WHERE EXTRACT(HOUR FROM timestamp) NOT BETWEEN 8 AND 18
  AND action IN ('write', 'delete')
ORDER BY timestamp DESC;
```

## Compliance Documentation

### GDPR Compliance

#### Data Handling

```python
# Right to erasure
async def delete_user_data(user_id: str, db: AsyncSession):
    # Delete all user's projects
    projects = await db.execute(
        select(Project).where(Project.created_by == user_id)
    )
    for project in projects.scalars():
        await delete_project(project.project_id, db)
    
    # Anonymize audit logs
    await db.execute(
        update(SecurityAuditLog)
        .where(SecurityAuditLog.actor == user_id)
        .values(actor="<deleted>")
    )
    await db.commit()
```

#### Data Export

```python
# Right to data portability
async def export_user_data(user_id: str, db: AsyncSession) -> dict:
    projects = await db.execute(
        select(Project).where(Project.created_by == user_id)
    )
    
    return {
        "user_id": user_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "projects": [p.model_dump() for p in projects.scalars()],
    }
```

### CCPA Compliance

Similar procedures as GDPR, with specific California requirements documented.

## Vulnerability Scanning

### Trivy Container Scanning

```bash
#!/bin/bash
# scripts/scan-containers.sh

# Scan API image
trivy image --severity HIGH,CRITICAL \
  --format sarif \
  --output trivy-api.sarif \
  registry.example.com/apex-api:v0.1.0

# Scan worker image
trivy image --severity HIGH,CRITICAL \
  --format sarif \
  --output trivy-worker.sarif \
  registry.example.com/apex-worker:v0.1.0
```

### Automated Scanning in CI

```yaml
# .github/workflows/vulnerability-scan.yml
name: Vulnerability Scan
on: [push]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build image
        run: docker build -t apex-api:test .
      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'apex-api:test'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
      - name: Upload results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

## Rate Limiting & DDoS

### Per-User Quotas

```python
# services/api/src/apex/api/rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# Per-endpoint limits
@router.post("/projects")
@limiter.limit("10/minute")  # 10 requests per minute
async def create_project(...):
    ...

@router.post("/signage/common/cabinets/derive")
@limiter.limit("100/minute")  # Higher limit for calculations
async def derive_cabinets(...):
    ...
```

### DDoS Mitigation (Cloudflare)

#### Cloudflare Configuration

```yaml
# infra/dns/cloudflare-rules.yaml
rules:
  - name: "Rate Limit API"
    priority: 1
    action: "challenge"
    expression: "(http.request.uri.path contains \"/api/\") and (rate(1h) > 1000)"
  
  - name: "Block Suspicious IPs"
    priority: 2
    action: "block"
    expression: "(ip.geoip.country in {\"CN\" \"RU\"}) and (not ip.geoip.country in {\"US\" \"CA\"})"
```

### WAF Rules

```yaml
# Cloudflare WAF rules
rules:
  - id: "100001"
    description: "Block SQL injection attempts"
    expression: "(http.request.body contains \"' OR '1'='1\") or (http.request.body contains \"DROP TABLE\")"
    action: "block"
  
  - id: "100002"
    description: "Block XSS attempts"
    expression: "(http.request.body contains \"<script>\") or (http.request.body contains \"javascript:\")"
    action: "block"
```

---

**Next Steps:**
- [**Disaster Recovery**](../operations/disaster-recovery.md) - DR procedures
- [**Performance Tuning**](../performance/performance-tuning.md) - Optimization guides

