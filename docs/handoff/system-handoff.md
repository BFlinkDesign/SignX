# System Handoff Documentation

Complete system handoff documentation for SIGN X Studio Clone.

## System Inventory

### Services

| Service | Version | Location | Status |
|---------|---------|----------|--------|
| **API Service** | 1.0.0 | `services/api/` | Production |
| **Worker Service** | 1.0.0 | `services/worker/` | Production |
| **Signcalc Service** | 1.0.0 | `services/signcalc-service/` | Production |

### Infrastructure

| Component | Type | Location | Status |
|-----------|------|----------|--------|
| **Database** | PostgreSQL 15 | RDS (AWS) / Cloud SQL (GCP) | Production |
| **Cache** | Redis 7 | ElastiCache (AWS) / Memorystore (GCP) | Production |
| **Storage** | MinIO/S3 | S3 (AWS) / Cloud Storage (GCP) | Production |
| **Search** | OpenSearch 2.x | Managed OpenSearch | Production |

### External Services

- **SendGrid**: Email delivery
- **KeyedIn CRM**: Webhook integration
- **OpenProject**: Ticket dispatch
- **Status Page**: Status.io or similar

## Access Credentials

### Secrets Management

**Location**: HashiCorp Vault / AWS Secrets Manager

**Secrets Stored:**
- Database credentials
- API keys (SendGrid, etc.)
- OAuth tokens (OpenProject)
- Webhook secrets
- Admin tokens

**Access:**
- Vault: `vault.example.com`
- AWS Secrets Manager: `us-east-1` region

### Admin Access

**API Admin Token**:
- Location: Vault (path: `apex/admin-token`)
- Usage: Admin endpoints, system configuration

**Database Access**:
- Connection: `postgresql://apex_admin:...@prod-db:5432/apex`
- Read-only user: `apex_readonly`
- Admin user: `apex_admin`

## Key Contacts

### Development Team

- **Engineering Lead**: [Name] - [Email] - [Phone]
- **Backend Engineer**: [Name] - [Email]
- **Frontend Engineer**: [Name] - [Email]
- **DevOps Engineer**: [Name] - [Email]

### Operations Team

- **On-Call Primary**: [Name] - [Phone] - [Email]
- **On-Call Secondary**: [Name] - [Phone] - [Email]
- **Support Lead**: [Name] - [Email]

### Management

- **Product Owner**: [Name] - [Email]
- **CTO**: [Name] - [Email]
- **VP Engineering**: [Name] - [Email]

### Vendors

- **AWS Support**: support@aws.amazon.com
- **GCP Support**: gcp-support@google.com
- **SendGrid**: support@sendgrid.com

## Critical Procedures

### Deployment

**Standard Deployment:**
```bash
# 1. Merge to main branch
git checkout main
git merge staging
git push

# 2. CI/CD pipeline runs
# - Tests
# - Build images
# - Deploy to staging
# - Smoke tests

# 3. Manual approval
# - Review staging deployment
# - Approve production deployment

# 4. Production deployment
# - Blue-green deployment
# - Health checks
# - Smoke tests
```

**Emergency Deployment:**
- Hotfix branch
- Immediate deployment
- Rollback plan ready

### Rollback Procedure

**Automatic Rollback:**
- Triggered by health check failures
- Previous version restored automatically
- Team notified

**Manual Rollback:**
```bash
# 1. Identify version to rollback to
git tag -l

# 2. Deploy previous version
kubectl set image deployment/apex-api \
  api=apex-api:v0.9.0

# 3. Verify rollback
curl https://api.example.com/health
```

### Backup and Restore

**Daily Backups:**
- Automated: 2:00 AM EST daily
- Location: S3 bucket `apex-backups`
- Retention: 30 days

**Restore Procedure:**
```bash
# 1. Download backup
aws s3 cp s3://apex-backups/backup-20250127.sql.gz .

# 2. Restore to test database
gunzip < backup-20250127.sql.gz | \
  psql -h test-db -U apex_admin apex

# 3. Verify restore
psql -h test-db -U apex_admin apex -c \
  "SELECT COUNT(*) FROM projects;"

# 4. Restore to production (if needed)
```

### Incident Response

**P0 Incident:**
1. Page on-call engineer (<15 min)
2. Assess situation
3. Execute runbook
4. Deploy fix
5. Verify resolution
6. Post-mortem within 24 hours

**P1 Incident:**
1. Notify on-call (<1 hour)
2. Investigate
3. Deploy fix
4. Verify resolution
5. Post-mortem within 1 week

## System Configuration

### Environment Variables

**Production .env:**
```bash
# Database
APEX_DATABASE_URL=postgresql://apex_admin:...@prod-db:5432/apex

# Redis
APEX_REDIS_URL=redis://prod-redis:6379/0

# MinIO/S3
APEX_S3_BUCKET=apex-uploads
APEX_S3_ENDPOINT=https://s3.amazonaws.com

# Email
SENDGRID_API_KEY=SG.xxx

# Rate Limits
APEX_RATE_LIMIT_PER_MIN=100
```

**Location**: Vault / AWS Secrets Manager

### Configuration Files

**Constants Packs:**
- Location: `services/api/config/packs/constants/`
- Files: `pricing_v1.yaml`, `exposure_factors.yaml`, `footing_calibration_v1.yaml`
- Version tracking: SHA256 computed at startup

**Prometheus Config:**
- Location: `infra/monitoring/prometheus.yml`
- Alert rules: `infra/monitoring/alerts.yml`

## Monitoring and Alerting

### Dashboards

- **Grafana**: https://grafana.example.com
  - Executive dashboard
  - Operations dashboard
  - Engineering dashboard

- **Prometheus**: https://prometheus.example.com
  - Metrics querying
  - Alert rules

### Alert Channels

- **PagerDuty**: Critical alerts (P0/P1)
- **Slack**: #apex-oncall, #apex-support
- **Email**: Team notifications

### Key Metrics

- System uptime: Target 99.9%
- API latency: P95 <200ms
- Error rate: <1%
- Cache hit rate: >80%

## Documentation

### Location

- **User Docs**: `docs/getting-started/`, `docs/guides/`
- **API Docs**: `docs/api/`
- **Operations**: `docs/operations/`
- **Training**: `docs/training/`

### Documentation Site

- URL: https://docs.example.com
- Built with: MkDocs
- Auto-deployed: On documentation updates

## Support Procedures

### Support Tiers

1. **Tier 1**: Self-service (documentation)
2. **Tier 2**: Help desk (email, chat)
3. **Tier 3**: Engineering (on-call)
4. **Tier 4**: Vendor support

### Escalation Path

- P0: Immediate → On-call → Engineering Lead
- P1: <1 hour → On-call → Engineering Lead
- P2: <4 hours → Support team
- P3: <24 hours → Support team

## Disaster Recovery

### RTO/RPO

- **RTO**: <4 hours
- **RPO**: <15 minutes

### DR Procedures

**Full DR Test**: Quarterly

1. Restore backup to test environment
2. Verify data integrity
3. Test failover procedures
4. Document results

## Next Steps

### Week 1

- [ ] Intensive monitoring
- [ ] Daily standups
- [ ] Issue triage
- [ ] User support

### Month 1

- [ ] Performance optimization
- [ ] Process refinement
- [ ] Documentation updates
- [ ] Launch review

### Quarter 1

- [ ] Feature enhancements
- [ ] Integration improvements
- [ ] Capacity planning
- [ ] Technology refresh

---

**Status**: ✅ System Handoff Complete  
**Handoff Date**: 2025-01-27  
**Next Review**: Week 4

