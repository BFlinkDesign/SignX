# Admin Training Guide

Complete training program for system administrators of SIGN X Studio Clone.

## Overview

**Total Duration**: 4 hours (6 modules)  
**Format**: Instructor-led with hands-on practice  
**Prerequisites**: System administration experience, database knowledge

## Module 1: System Architecture Overview (30 minutes)

### Objectives

- Understand system components
- Know service dependencies
- Access monitoring dashboards

### Content

#### 1.1 System Components (15 min)

**Services:**
- API Service (FastAPI)
- Worker Service (Celery)
- Database (PostgreSQL)
- Cache (Redis)
- Storage (MinIO/S3)
- Search (OpenSearch)

**Architecture Diagram:**
```
Client → API Service → Database
              ↓
         Worker Service → Redis
              ↓
         MinIO/S3
```

#### 1.2 Monitoring Access (15 min)

**Dashboards:**
- Grafana: https://grafana.example.com
- Prometheus: https://prometheus.example.com
- Log Aggregation: https://logs.example.com

**Key Metrics:**
- API latency (P95)
- Error rate
- Database connection pool
- Cache hit rate
- Worker queue depth

**Hands-On:**
- Access Grafana
- Navigate dashboards
- Review key metrics

## Module 2: User Management (45 minutes)

### Objectives

- Create and manage user accounts
- Configure roles and permissions
- Handle user data requests (GDPR)

### Content

#### 2.1 User Accounts (20 min)

**Creating Users:**
```bash
# Via API
curl -X POST https://api.example.com/admin/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "email": "user@example.com",
    "name": "John Doe",
    "role": "engineer"
  }'
```

**User Roles:**
- `admin` - Full system access
- `engineer` - Create/submit projects
- `viewer` - Read-only access
- `support` - Support access

#### 2.2 Permissions (15 min)

**Permission Model:**
- Project-level access control
- Role-based restrictions
- API key management

**Configuring Permissions:**
```python
# Permission matrix
PERMISSIONS = {
    "admin": ["read", "write", "delete", "admin"],
    "engineer": ["read", "write", "submit"],
    "viewer": ["read"],
}
```

**Hands-On:**
- Create test user
- Assign role
- Verify permissions

#### 2.3 GDPR Data Requests (10 min)

**Right to Erasure:**
```bash
# Delete user data
curl -X DELETE https://api.example.com/users/user_123/data \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Data Export:**
```bash
# Export user data
curl https://api.example.com/users/user_123/export \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  > user_export.json
```

**Hands-On:**
- Process deletion request
- Verify data anonymized
- Export user data

## Module 3: System Configuration (60 minutes)

### Objectives

- Configure constants packs
- Manage pricing versions
- Update system settings

### Content

#### 3.1 Constants Packs (20 min)

**Packs Location:**
```
services/api/config/packs/constants/
├── pricing_v1.yaml
├── exposure_factors.yaml
└── footing_calibration_v1.yaml
```

**Updating Packs:**
1. Edit YAML file
2. Restart API service
3. Verify version in responses

**Version Tracking:**
- Each pack has version
- SHA256 computed at startup
- Included in Envelope responses

**Hands-On:**
- View current packs
- Update pricing table
- Restart service
- Verify update

#### 3.2 Pricing Configuration (20 min)

**Pricing Structure:**
```yaml
# config/pricing_v1.yaml
version: "v1"
effective_date: "2025-01-01"
base_rates:
  - height_max_ft: 15
    price: 1500.00
  - height_max_ft: 20
    price: 2000.00
addons:
  calc_packet: 150.00
  hard_copies: 50.00
```

**Updating Pricing:**
1. Create new version (pricing_v2.yaml)
2. Update effective_date
3. Deploy and verify

**Hands-On:**
- Review current pricing
- Create new pricing version
- Test pricing endpoint

#### 3.3 Environment Configuration (20 min)

**Key Settings:**
- Database connection
- Redis URL
- MinIO credentials
- Rate limits
- CORS origins

**Updating Settings:**
```bash
# Via environment variables
export APEX_RATE_LIMIT_PER_MIN=120

# Or via config file
# .env
APEX_RATE_LIMIT_PER_MIN=120
```

**Hands-On:**
- Review current settings
- Update rate limit
- Restart service
- Verify change

## Module 4: Monitoring and Alerting (60 minutes)

### Objectives

- Use monitoring dashboards
- Configure alerts
- Respond to incidents

### Content

#### 4.1 Dashboard Usage (20 min)

**Executive Dashboard:**
- Projects created/day
- User adoption
- System uptime
- Business metrics

**Operations Dashboard:**
- API latency
- Error rate
- Database performance
- Cache hit rate

**Engineering Dashboard:**
- Solver performance
- Calculation times
- Confidence distributions
- Error patterns

**Hands-On:**
- Navigate dashboards
- Apply filters
- Drill down into metrics

#### 4.2 Alert Configuration (20 min)

**Alert Types:**
- Critical: System down, data loss
- Warning: Performance degradation
- Info: Capacity thresholds

**Configuring Alerts:**
```yaml
# prometheus/alerts.yml
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
  for: 5m
  annotations:
    summary: "High error rate detected"
```

**Hands-On:**
- Review existing alerts
- Create test alert
- Verify alert fires

#### 4.3 Incident Response (20 min)

**Incident Workflow:**
1. Alert received (PagerDuty/Slack)
2. Check dashboard for details
3. Review runbooks
4. Execute resolution steps
5. Verify fix
6. Document incident

**Common Incidents:**
- API down → Check health, restart service
- High latency → Check database, scale workers
- High error rate → Check logs, review changes

**Hands-On:**
- Simulate incident
- Follow runbook
- Resolve issue
- Document resolution

## Module 5: Backup and Recovery (30 minutes)

### Objectives

- Perform backups
- Test restore procedures
- Understand DR plan

### Content

#### 5.1 Backup Procedures (15 min)

**Daily Backups:**
```bash
# Automated backup script
./scripts/backup.sh

# Manual backup
pg_dump -h prod-db -U apex_admin apex | \
  gzip > backup-$(date +%Y%m%d).sql.gz
```

**Backup Verification:**
- Automated daily restore tests
- Quarterly DR drills
- Verify backup integrity

**Hands-On:**
- Run backup script
- Verify backup created
- Check backup integrity

#### 5.2 Restore Procedures (15 min)

**Restore from Backup:**
```bash
# Restore database
gunzip < backup-20250127.sql.gz | \
  psql -h test-db -U apex_admin apex

# Verify restore
psql -h test-db -U apex_admin apex -c \
  "SELECT COUNT(*) FROM projects;"
```

**Point-in-Time Recovery:**
- WAL archiving enabled
- Restore to specific timestamp
- Verify data integrity

**Hands-On:**
- Restore test backup
- Verify data
- Test PITR

## Module 6: Troubleshooting and Support (45 minutes)

### Objectives

- Troubleshoot common issues
- Escalate problems
- Document solutions

### Content

#### 6.1 Diagnostic Tools (15 min)

**Health Checks:**
```bash
# API health
curl http://api.example.com/health

# Readiness
curl http://api.example.com/ready

# Metrics
curl http://api.example.com/metrics
```

**Log Access:**
```bash
# API logs
docker compose logs api --tail=100

# Worker logs
docker compose logs worker --tail=100

# Database logs
docker compose logs db --tail=100
```

**Database Queries:**
```sql
-- Check connections
SELECT count(*) FROM pg_stat_activity;

-- Slow queries
SELECT query, mean_exec_time 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
```

**Hands-On:**
- Run health checks
- Review logs
- Query database

#### 6.2 Common Issues (20 min)

**Issue 1: API Down**
- Check service status
- Review logs
- Restart service

**Issue 2: Slow Performance**
- Check database connections
- Review slow queries
- Scale services

**Issue 3: High Error Rate**
- Review error logs
- Check dependencies
- Rollback if needed

**Hands-On:**
- Troubleshoot simulated issue
- Follow runbook
- Resolve problem

#### 6.3 Escalation Procedures (10 min)

**When to Escalate:**
- P0 issues (system down)
- P1 issues (major feature broken)
- Unknown issues after troubleshooting

**Escalation Path:**
1. Tier 1: Support team
2. Tier 2: On-call engineer
3. Tier 3: Engineering lead
4. Tier 4: Management

**Hands-On:**
- Practice escalation
- Contact on-call
- Document escalation

## Advanced Topics

### Performance Tuning

**Database Optimization:**
- Index management
- Query optimization
- Connection pool tuning

**Caching Strategy:**
- Cache warming
- Invalidation patterns
- TTL configuration

### Security Management

**Access Control:**
- API key rotation
- User permission reviews
- Audit log analysis

**Vulnerability Management:**
- Regular scans
- Patch deployment
- Security updates

## Certification

### Training Completion Criteria

- [ ] Complete all 6 modules
- [ ] Pass admin quiz (85%+ score)
- [ ] Perform backup and restore
- [ ] Resolve simulated incident
- [ ] Configure alert

### Post-Training Support

- **Week 1**: Daily check-ins
- **Week 2-4**: Weekly office hours
- **Ongoing**: Documentation updates

---

**Next Steps:**
- [**Developer Onboarding**](developer-onboarding.md)
- [**Operational Runbooks**](../operations/operational-runbooks.md)

