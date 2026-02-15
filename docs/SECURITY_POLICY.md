# APEX Security Policy

**Document Version:** 1.0.0
**Last Updated:** 2026-01-22
**Classification:** CONFIDENTIAL

---

## 1. Overview

This document outlines the security policies and practices for the APEX structural engineering calculation platform. Given the professional liability and compliance requirements (PE certification), security is a top priority.

---

## 2. Security Principles

### 2.1 Defense in Depth

Multiple layers of security controls:
1. Network perimeter (WAF, DDoS protection)
2. Network segmentation (VPC, subnets, security groups)
3. Application security (input validation, authentication)
4. Data security (encryption at rest and in transit)
5. Monitoring and alerting

### 2.2 Principle of Least Privilege

- Service accounts have minimum required permissions
- Database users have role-specific access
- API tokens are scoped to specific operations
- Container processes run as non-root

### 2.3 Zero Trust

- All network traffic is encrypted (TLS 1.2+)
- All requests are authenticated
- Service-to-service communication uses mTLS where possible
- No implicit trust based on network location

---

## 3. Authentication and Authorization

### 3.1 User Authentication

| Method | Use Case | Implementation |
|--------|----------|----------------|
| OAuth 2.0 / OIDC | Primary user auth | Supabase Auth |
| API Keys | Service integration | Hashed, rotated quarterly |
| MFA | Admin accounts | Required for all admins |

### 3.2 Session Management

```yaml
Session Configuration:
  - Session timeout: 24 hours
  - Idle timeout: 2 hours
  - Concurrent sessions: Limited to 5
  - Session binding: IP + User-Agent
  - Token rotation: On refresh
```

### 3.3 Authorization Model

Role-Based Access Control (RBAC):

| Role | Permissions |
|------|-------------|
| Viewer | Read projects, view calculations |
| Engineer | Create/edit projects, run calculations |
| Lead Engineer | All Engineer + approve submissions |
| Admin | All Lead + user management |
| Super Admin | System configuration, audit access |

---

## 4. Data Security

### 4.1 Encryption at Rest

| Data Type | Encryption Method | Key Management |
|-----------|-------------------|----------------|
| PostgreSQL | AES-256 (RDS) | AWS KMS |
| Redis | AES-256 | AWS KMS |
| S3 Objects | AES-256-GCM | AWS KMS |
| Backups | AES-256 | Separate KMS key |

### 4.2 Encryption in Transit

```yaml
TLS Configuration:
  - Minimum version: TLS 1.2
  - Preferred version: TLS 1.3
  - Certificate: ACM or DigiCert EV
  - HSTS: Enabled (max-age=31536000)
  - Certificate transparency: Required
```

### 4.3 Data Classification

| Classification | Examples | Handling |
|----------------|----------|----------|
| Public | Marketing content | No restrictions |
| Internal | System documentation | Access controlled |
| Confidential | Project data | Encrypted, audit logged |
| Restricted | Credentials, PII | Encrypted, access logged, MFA required |

---

## 5. Network Security

### 5.1 Network Architecture

```
Internet
    |
   WAF (AWS WAF / Cloudflare)
    |
   ALB (TLS termination)
    |
   VPC
   ├── Public Subnet (NAT Gateway)
   └── Private Subnet
       ├── Application Tier (Kubernetes)
       └── Data Tier (RDS, ElastiCache)
```

### 5.2 Firewall Rules

**Ingress (Public):**
| Source | Destination | Port | Protocol |
|--------|-------------|------|----------|
| Internet | ALB | 443 | HTTPS |
| Internet | ALB | 80 | HTTP (redirect) |

**Ingress (Internal):**
| Source | Destination | Port | Protocol |
|--------|-------------|------|----------|
| ALB | API pods | 8000 | HTTP |
| API pods | Database | 5432 | PostgreSQL |
| API pods | Redis | 6379 | Redis |
| Prometheus | All pods | */metrics | HTTP |

### 5.3 WAF Rules

```yaml
WAF Configuration:
  Rate Limiting:
    - Global: 1000 requests/5min per IP
    - Login: 10 requests/min per IP
    - API: 100 requests/min per user

  Blocked Patterns:
    - SQL Injection (OWASP CRS)
    - XSS (OWASP CRS)
    - Path Traversal
    - Known malicious IPs (managed list)

  Geo Restrictions:
    - Optional: Block non-approved countries
```

---

## 6. Container Security

### 6.1 Image Security

```dockerfile
# Security requirements for all Dockerfiles:
# 1. Use specific version tags, not 'latest'
FROM python:3.11-slim-bookworm

# 2. Run as non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

# 3. Use read-only filesystem where possible
# 4. No shell in production images (optional)
# 5. Scan images before deployment
```

### 6.2 Image Scanning

| Tool | Stage | Severity Threshold |
|------|-------|-------------------|
| Trivy | CI/CD | CRITICAL blocks merge |
| Snyk | Continuous | HIGH generates alert |

### 6.3 Runtime Security

```yaml
Pod Security Standards:
  - runAsNonRoot: true
  - readOnlyRootFilesystem: true
  - allowPrivilegeEscalation: false
  - capabilities:
      drop: ["ALL"]
```

---

## 7. Secrets Management

### 7.1 Secret Storage

| Environment | Method | Rotation |
|-------------|--------|----------|
| Development | .env files (gitignored) | N/A |
| Staging | AWS Secrets Manager | 90 days |
| Production | HashiCorp Vault | 30 days |

### 7.2 Secret Types and Rotation

| Secret Type | Rotation Frequency | Automation |
|-------------|-------------------|------------|
| Database passwords | 30 days | Vault dynamic secrets |
| API keys | 90 days | Manual with notification |
| TLS certificates | 90 days | cert-manager auto-renewal |
| Encryption keys | 365 days | KMS auto-rotation |

### 7.3 Secret Access

```
Secrets Access Flow:
1. Pod starts with ServiceAccount
2. External Secrets Operator authenticates to Vault
3. Vault validates Kubernetes ServiceAccount
4. Vault returns secrets based on policy
5. Secrets mounted as environment variables or files
6. Secrets refreshed hourly
```

---

## 8. Audit and Compliance

### 8.1 Audit Logging

All security-relevant events are logged:

```json
{
  "timestamp": "2026-01-22T10:30:00.000Z",
  "event_type": "authentication",
  "action": "login_success",
  "user_id": "usr_123",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "session_id": "sess_456",
  "mfa_used": true
}
```

### 8.2 Audit Events

| Event Category | Examples | Retention |
|----------------|----------|-----------|
| Authentication | Login, logout, MFA | 2 years |
| Authorization | Permission changes | 2 years |
| Data Access | Project access, exports | 7 years |
| System | Config changes, deployments | 1 year |
| Security | Failed logins, blocked requests | 90 days |

### 8.3 Compliance Requirements

| Requirement | Implementation |
|-------------|----------------|
| Audit trail | All calculations logged with inputs/outputs |
| Data retention | 7 years for engineering calculations |
| Access control | Role-based, logged access |
| Integrity | Checksums on calculation results |
| Non-repudiation | Digital signatures on approvals |

---

## 9. Incident Response

### 9.1 Security Incident Classification

| Severity | Description | Response Time |
|----------|-------------|---------------|
| P0 - Critical | Active breach, data exfiltration | Immediate |
| P1 - High | Vulnerability being exploited | 1 hour |
| P2 - Medium | Vulnerability discovered | 24 hours |
| P3 - Low | Security improvement needed | 1 week |

### 9.2 Incident Response Procedure

1. **Detect** - Monitoring alerts or user report
2. **Contain** - Isolate affected systems
3. **Eradicate** - Remove threat
4. **Recover** - Restore from known good state
5. **Learn** - Post-mortem and improvements

### 9.3 Security Contacts

| Role | Contact | Availability |
|------|---------|--------------|
| Security On-Call | security-oncall@apex.example.com | 24/7 |
| Security Lead | security-lead@apex.example.com | Business hours |
| CISO | ciso@apex.example.com | Escalation only |

---

## 10. Vulnerability Management

### 10.1 Scanning Schedule

| Scan Type | Frequency | Tool |
|-----------|-----------|------|
| SAST (Code) | Every commit | Semgrep |
| SCA (Dependencies) | Every commit | Safety, Dependabot |
| Container scan | Every build | Trivy |
| DAST (Runtime) | Weekly | OWASP ZAP |
| Penetration test | Annually | External vendor |

### 10.2 Vulnerability Response SLA

| Severity | CVSS Score | Remediation SLA |
|----------|------------|-----------------|
| Critical | 9.0 - 10.0 | 24 hours |
| High | 7.0 - 8.9 | 7 days |
| Medium | 4.0 - 6.9 | 30 days |
| Low | 0.1 - 3.9 | 90 days |

---

## 11. Security Training

### 11.1 Required Training

| Role | Training | Frequency |
|------|----------|-----------|
| All employees | Security awareness | Annual |
| Developers | Secure coding (OWASP) | Annual |
| DevOps | Cloud security | Annual |
| Admins | Privileged access | Annual |

### 11.2 Phishing Simulations

- Conducted quarterly
- Results tracked per department
- Additional training for repeat failures

---

## 12. Third-Party Security

### 12.1 Vendor Assessment

All vendors with data access must:
- Complete security questionnaire
- Provide SOC 2 Type II or equivalent
- Sign data processing agreement
- Undergo annual review

### 12.2 Approved Vendors

| Category | Vendor | Security Certification |
|----------|--------|------------------------|
| Cloud | AWS | SOC 2, ISO 27001 |
| Auth | Supabase | SOC 2 |
| Monitoring | Sentry | SOC 2 |
| Error Tracking | Datadog | SOC 2 |

---

## 13. Security Checklist

### Pre-Deployment Checklist

- [ ] All tests passing
- [ ] No critical/high vulnerabilities in scan
- [ ] Secrets not in code
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] Logging configured
- [ ] Monitoring alerts set up
- [ ] Backup verified
- [ ] Rollback plan documented

### Periodic Review Checklist (Monthly)

- [ ] Review access logs for anomalies
- [ ] Verify backup restoration works
- [ ] Check certificate expiration dates
- [ ] Review and rotate service accounts
- [ ] Update dependencies with security patches
- [ ] Review WAF logs for blocked attacks
- [ ] Conduct access review for privileged accounts

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-22 | DevOps Team | Initial version |

**Next Review Date:** 2026-04-22
