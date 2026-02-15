# SignX/APEX Deployment Security Checklist

Use this checklist before deploying to production or when conducting security reviews.

## Pre-Deployment Checklist

### Environment Configuration

- [ ] **JWT_SECRET_KEY** is set and at least 32 characters
- [ ] **DATABASE_URL** uses SSL (`sslmode=require`)
- [ ] **REDIS_URL** includes password authentication
- [ ] **CORS_ALLOW_ORIGINS** does not contain wildcards (`*`)
- [ ] **DEBUG** mode is disabled
- [ ] **ENV** is set to `production`
- [ ] All default passwords have been changed
- [ ] Sensitive environment variables are not logged

### Authentication & Authorization

- [ ] Supabase Auth is configured with production keys
- [ ] Duo 2FA is configured for PE stamp operations
- [ ] Password policy is enforced (12+ characters, complexity)
- [ ] Account lockout is enabled (5 attempts, 15 min)
- [ ] Session timeout is configured (30 min idle)
- [ ] OAuth redirect URLs are production URLs only
- [ ] JWT token expiration is appropriately short (15 min access, 7 day refresh)

### Container Security

- [ ] Docker images use specific version tags (no `latest`)
- [ ] Containers run as non-root user
- [ ] `no-new-privileges` security option is set
- [ ] Read-only filesystem where possible
- [ ] Resource limits are configured (CPU, memory)
- [ ] No unnecessary ports are exposed
- [ ] Container images have been scanned for CVEs

### Network Security

- [ ] TLS 1.3 is required for all connections
- [ ] HSTS header is enabled with preload
- [ ] All internal services use private network
- [ ] Database is not exposed to public internet
- [ ] Redis is not exposed to public internet
- [ ] Firewall rules are properly configured

### Database Security

- [ ] Database user has minimal required permissions
- [ ] Database connections use SSL
- [ ] Connection pooling is configured
- [ ] Query timeout is set (30-60 seconds)
- [ ] Backup encryption is enabled
- [ ] Point-in-time recovery is enabled

### Monitoring & Logging

- [ ] Structured logging is enabled
- [ ] Security events are logged (auth, access control)
- [ ] Log retention meets compliance requirements (7 years)
- [ ] Error messages do not leak sensitive information
- [ ] Sentry or equivalent error tracking is configured
- [ ] Health check endpoints are available
- [ ] Alerting is configured for security events

### Secrets Management

- [ ] No secrets are hardcoded in code
- [ ] No secrets in git history
- [ ] Secrets are rotated regularly
- [ ] Service accounts use least privilege
- [ ] API keys are scoped appropriately

### CI/CD Security

- [ ] Semgrep SAST is running on all PRs
- [ ] Gitleaks is checking for secrets
- [ ] Dependency scanning is enabled
- [ ] Container scanning is enabled
- [ ] Branch protection is enabled on main
- [ ] Code review is required for merges

## Post-Deployment Verification

### Smoke Tests

```bash
# Health check
curl -f https://api.signxstudio.com/health

# Readiness check
curl -f https://api.signxstudio.com/ready

# Version check
curl https://api.signxstudio.com/version
```

### Security Headers Check

```bash
# Check security headers
curl -I https://api.signxstudio.com/health | grep -i "strict-transport\|x-content-type\|x-frame\|x-xss"
```

Expected headers:
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`

### Authentication Tests

- [ ] Invalid credentials return 401
- [ ] Account lockout activates after 5 failures
- [ ] JWT tokens expire as configured
- [ ] MFA is required for sensitive operations

### Authorization Tests

- [ ] Unauthorized users cannot access protected resources
- [ ] Users cannot access other organizations' data
- [ ] Role restrictions are enforced

### Rate Limiting Tests

- [ ] Rate limits are enforced (429 response)
- [ ] Auth endpoints have stricter limits

## Periodic Security Tasks

### Weekly

- [ ] Review dependency scan results
- [ ] Check for new CVEs in used components
- [ ] Review failed login attempts

### Monthly

- [ ] Rotate API keys and tokens
- [ ] Review audit logs for anomalies
- [ ] Update security patches
- [ ] Review access permissions

### Quarterly

- [ ] Conduct internal security review
- [ ] Run DAST scan
- [ ] Review and update this checklist
- [ ] Security training refresher

### Annually

- [ ] External penetration test
- [ ] Security audit
- [ ] Disaster recovery test
- [ ] Compliance review

## Emergency Contacts

| Role | Contact |
|------|---------|
| Security Lead | security@signxstudio.com |
| On-Call Engineer | oncall@signxstudio.com |
| CTO | [TBD] |

## Incident Response

If you discover a security incident:

1. **Do not panic**
2. Document what you observed
3. Contact Security Lead immediately
4. Do not attempt to fix without coordination
5. Preserve evidence (logs, screenshots)
6. Follow incident response procedures

See `/docs/security/SECURITY_ARCHITECTURE.md` Section 7 for full incident response procedures.
