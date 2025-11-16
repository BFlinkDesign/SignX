# Production Deployment Checklist

**Purpose**: Comprehensive checklist for production deployment readiness  
**Last Updated**: 2025-01-27  
**Use Before**: Every production deployment

---

## Pre-Deployment Verification

### Agent 1-5 Success Criteria Verification

#### ✅ Agent 1: Frontend

- [ ] Frontend build completes without errors
- [ ] Envelope pattern integrated in UI
- [ ] Real-time features operational
- [ ] All UI components render correctly
- [ ] No console errors in browser
- [ ] Bundle size optimized (< 2MB)

**Verification**:
```bash
cd apex/apps/ui-web
npm run build
# Check dist/ folder size
```

---

#### ✅ Agent 2: Backend

- [ ] All API endpoints return envelope responses
- [ ] Solver integrations functional
- [ ] Database transactions working
- [ ] Error handling with proper HTTP codes
- [ ] API documentation complete (Swagger)
- [ ] Rate limiting configured

**Verification**:
```bash
curl http://localhost:8000/docs  # Swagger UI
curl http://localhost:8000/health  # Health check
curl http://localhost:8000/api/v1/projects  # Endpoint test
```

---

#### ✅ Agent 3: Database

- [ ] All migrations applied successfully
- [ ] Indexes created and optimized
- [ ] Backup procedures tested
- [ ] Connection pooling configured
- [ ] Query performance acceptable (< 100ms for common queries)
- [ ] Database monitoring enabled (postgres_exporter)

**Verification**:
```bash
docker exec apex-api-1 alembic current  # Check migrations
docker exec apex-db-1 psql -U apex -d apex -c "\di+"  # List indexes
curl http://localhost:9187/metrics | grep pg_stat  # Database metrics
```

---

#### ✅ Agent 4: Solvers

- [ ] All solver services operational
- [ ] Calculation determinism verified
- [ ] Performance benchmarks met
- [ ] Error handling for edge cases
- [ ] Confidence scores accurate
- [ ] Solver caching working

**Verification**:
```bash
curl http://localhost:8002/healthz  # Signcalc health
# Run deterministic tests
python scripts/validate_accuracy.py
```

---

#### ✅ Agent 5: Testing

- [ ] Contract tests passing
- [ ] Unit tests coverage > 80%
- [ ] E2E tests passing
- [ ] Load tests successful
- [ ] CI/CD gates configured
- [ ] Test documentation complete

**Verification**:
```bash
cd services/api
python -m pytest tests/ --cov=apex --cov-report=term-missing
python -m pytest tests/contract/ -v
```

---

## Environment Configuration

### Environment Variables Validation

- [ ] `.env.production` file created
- [ ] All required variables set
- [ ] No default/placeholder values
- [ ] Secrets properly configured
- [ ] Database credentials validated
- [ ] External API keys configured
- [ ] Redis connection string valid
- [ ] MinIO credentials set
- [ ] OpenSearch connection configured

**Required Variables**:
```bash
# Database
DATABASE_URL=postgresql://apex:password@db:5432/apex

# Redis
REDIS_URL=redis://cache:6379/0
CELERY_BROKER_URL=redis://cache:6379/0
CELERY_RESULT_BACKEND=redis://cache:6379/1

# Object Storage
MINIO_ENDPOINT=object:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Search
OPENSEARCH_URL=http://search:9200

# External APIs (if configured)
GOOGLE_GEOCODING_API_KEY=<set-if-used>
OPENWEATHER_API_KEY=<set-if-used>
```

**Verification**:
```bash
# Check all required vars are set
docker compose -f infra/compose.yaml config | grep -E "DATABASE_URL|REDIS_URL|MINIO"

# Validate no placeholders
grep -r "PLACEHOLDER\|TODO\|FIXME" .env.production
```

---

### SSL/TLS Configuration (If Applicable)

- [ ] SSL certificates obtained
- [ ] Certificate chain valid
- [ ] Private key secured
- [ ] Certificate expiration monitored
- [ ] Auto-renewal configured (Let's Encrypt)
- [ ] HTTPS enforced in production
- [ ] TLS 1.2+ only

**Verification**:
```bash
# Test SSL (if configured)
openssl s_client -connect yourdomain.com:443 -showcerts

# Check certificate expiration
openssl x509 -in cert.pem -noout -dates
```

---

## Backup Procedures

### Backup Configuration

- [ ] Automated backup schedule configured
- [ ] Backup retention policy defined
- [ ] Backup storage location secure
- [ ] Backup restoration tested
- [ ] Point-in-time recovery available
- [ ] Backup verification automated

**Verification**:
```bash
# Test backup
./scripts/verify_backup.sh

# Verify backup schedule (cron/systemd)
# Check backup storage
ls -lh infra/backups/
```

---

### Backup Restoration Test

- [ ] Restore procedure documented
- [ ] Test restore completed successfully
- [ ] Data integrity verified after restore
- [ ] Restoration time acceptable (< RTO)
- [ ] Team trained on restore procedure

**Verification**:
```bash
# Test restore in staging
docker compose exec db pg_restore -U apex -d apex test_backup.sql
# Verify data integrity
```

---

## Monitoring & Observability

### Dashboard Configuration

- [ ] Grafana dashboards imported
- [ ] All metrics displaying correctly
- [ ] Alert rules configured
- [ ] Alert delivery tested
- [ ] SLO/SLA dashboards visible
- [ ] Business metrics tracked

**Verification**:
```bash
# Import dashboard
curl -X POST http://localhost:3001/api/dashboards/db \
  -H "Content-Type: application/json" \
  -u admin:admin \
  -d @infra/monitoring/grafana/dashboards/apex-overview.json

# Verify metrics
curl http://localhost:9090/api/v1/targets
```

---

### Alert Configuration

- [ ] Critical alerts configured
- [ ] Warning alerts configured
- [ ] Alert thresholds appropriate
- [ ] Alert notification channels set
- [ ] Runbooks linked to alerts
- [ ] Alert testing completed

**Alerts to Configure**:
- API error rate > 5%
- Database connection pool exhausted
- Disk usage > 90%
- Service down
- P95 latency > 250ms

---

## Security Checklist

### Security Hardening

- [ ] Docker security options enabled
- [ ] Non-root user in containers
- [ ] Secrets not in code/images
- [ ] Network policies configured
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] Input validation on all endpoints

**Verification**:
```bash
# Check security options
docker inspect apex-api-1 | grep -A 5 SecurityOpt

# Verify non-root user
docker exec apex-api-1 whoami  # Should be appuser
```

---

### Vulnerability Scanning

- [ ] Container images scanned
- [ ] Dependencies audited
- [ ] Critical vulnerabilities addressed
- [ ] Security patches applied
- [ ] CVE tracking configured

**Verification**:
```bash
# Scan images
docker scan apex-api:dev
docker scan apex-worker:dev

# Audit dependencies
pip-audit
npm audit  # For frontend
```

---

## Rollback Preparation

### Rollback Plan

- [ ] Rollback procedure documented
- [ ] Database snapshot before deployment
- [ ] Previous Docker images tagged
- [ ] Configuration backups created
- [ ] Rollback testing completed
- [ ] Team trained on rollback

**Verification**:
```bash
# Create snapshot
docker compose exec db pg_dump -U apex apex > backup_pre_deploy.sql

# Tag current images
docker tag apex-api:dev apex-api:pre-deploy
docker tag apex-worker:dev apex-worker:pre-deploy

# Verify rollback plan
cat docs/deployment/ROLLBACK_PROCEDURES.md
```

---

## Infrastructure Readiness

### Resource Requirements

- [ ] CPU capacity sufficient
- [ ] Memory allocation adequate
- [ ] Disk space available (> 20GB free)
- [ ] Network bandwidth sufficient
- [ ] Docker resources allocated
- [ ] No resource contention

**Verification**:
```bash
# Check resources
docker system df
docker stats --no-stream

# Disk space
df -h
```

---

### Service Dependencies

- [ ] Database service healthy
- [ ] Redis service healthy
- [ ] MinIO service healthy
- [ ] OpenSearch service healthy
- [ ] All dependencies documented
- [ ] Startup order verified

**Verification**:
```bash
docker compose ps
# All services should be "running" or "healthy"
```

---

## Deployment Execution

### Pre-Deployment

- [ ] Pre-deployment checklist completed
- [ ] Stakeholder notification sent
- [ ] Maintenance window scheduled
- [ ] Team on standby
- [ ] Communication channels open
- [ ] Monitoring dashboards ready

---

### Deployment Steps

- [ ] Backup created ✅
- [ ] Configuration validated ✅
- [ ] Images built ✅
- [ ] Infrastructure services started ✅
- [ ] Database migrations run ✅
- [ ] Application services started ✅
- [ ] Health checks passing ✅
- [ ] Smoke tests passing ✅

---

### Post-Deployment

- [ ] All services healthy
- [ ] Monitoring operational
- [ ] Error logs reviewed
- [ ] Performance metrics acceptable
- [ ] User acceptance testing passed
- [ ] Deployment documented
- [ ] Stakeholders notified

---

## Communication & Notification

### Stakeholder Notification

- [ ] Deployment window communicated
- [ ] Expected downtime (if any) announced
- [ ] Rollback plan shared
- [ ] Emergency contact information provided
- [ ] Post-deployment status update sent

**Template**:
```
Subject: Production Deployment - [Date] [Time]

Dear Team,

We will be deploying version [VERSION] to production on [DATE] at [TIME].

Expected impact:
- Brief service interruption: [DURATION]
- New features: [LIST]
- Breaking changes: [LIST]

Rollback plan: Available if needed

Post-deployment: Status update will be sent within 1 hour

For questions: [CONTACT]
```

---

## Sign-Off

### Team Sign-Off

- [ ] **Deployment Lead**: _________________ Date: ________
- [ ] **Database Admin**: _________________ Date: ________
- [ ] **DevOps Engineer**: _________________ Date: ________
- [ ] **Security Team**: _________________ Date: ________
- [ ] **Product Owner**: _________________ Date: ________

---

### Final Approval

**Status**: 🟢 GO / 🟡 CONDITIONAL / 🔴 NO-GO

**Approved By**: _________________  
**Date**: ________  
**Time**: ________

---

## Post-Deployment Monitoring (First 24 Hours)

### First Hour

- [ ] Error rate < 0.1%
- [ ] API latency P95 < 250ms
- [ ] No critical alerts
- [ ] All endpoints responding
- [ ] Database connections stable

### First 4 Hours

- [ ] Performance metrics normal
- [ ] No user-reported issues
- [ ] Resource usage acceptable
- [ ] No unexpected errors

### First 24 Hours

- [ ] All checks passing
- [ ] User feedback positive
- [ ] No rollback needed
- [ ] Deployment declared successful

---

**Document Version**: 1.0  
**Last Reviewed**: 2025-01-27  
**Next Review**: Before next production deployment

