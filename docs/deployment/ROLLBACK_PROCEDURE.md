# Rollback Procedure

Complete rollback procedures for failed deployments.

## When to Rollback

### Immediate Rollback Triggers

**Critical Service Failure**:
- Service won't start after 3 retry attempts
- Database connection fails permanently
- Application crashes repeatedly
- Health checks consistently failing

**Data Issues**:
- Database migration fails irreversibly
- Data corruption detected
- Schema inconsistency errors

**Security Issues**:
- Security vulnerability discovered
- Unauthorized access detected
- Credential exposure

**Performance Degradation**:
- System unresponsive (>5 second response times)
- Resource exhaustion (OOM, CPU 100%)
- Cascading failures

### Decision Matrix

| Issue Type | Severity | Rollback Decision |
|------------|----------|-------------------|
| Service won't start | Critical | ✅ Immediate rollback |
| Migration failed | Critical | ✅ Immediate rollback |
| Data corruption | Critical | ✅ Immediate rollback |
| Security breach | Critical | ✅ Immediate rollback |
| High error rate (>10%) | High | ⚠️ Conditional (monitor 15 min) |
| Performance degraded | Medium | ⚠️ Conditional (monitor 30 min) |
| Minor feature broken | Low | ❌ No rollback (fix forward) |

---

## Quick Rollback (< 2 minutes)

**Use When**: Recent deployment, no data changes yet, simple revert

### Step 1: Stop All Services (30 seconds)

```bash
cd infra

# Stop all services immediately
docker compose down

# Verify all stopped
docker compose ps
# Should show: "No services found"
```

### Step 2: Revert Code Changes (30 seconds)

```bash
# Revert to previous commit (if code changed)
git log --oneline -5
# Identify previous working commit

git checkout <previous-commit-hash>
# Or
git checkout <previous-tag>

# If using branches
git checkout main  # or previous branch
git reset --hard HEAD~1
```

### Step 3: Restore Previous Images (30 seconds)

```bash
# If images were rebuilt, restore previous versions
docker images | grep apex

# Tag previous images or rebuild from previous commit
docker compose build

# Or use cached images
docker compose up -d
```

### Step 4: Restart Services (30 seconds)

```bash
# Start with previous version
docker compose up -d

# Verify services started
docker compose ps
```

**Verification**: All services running, health checks passing

---

## Full Rollback (< 5 minutes)

**Use When**: Complex changes, database migrations involved, data may be affected

### Step 1: Assess Current State (1 minute)

```bash
# Check current service status
docker compose ps

# Check recent logs for errors
docker compose logs --tail=100 | grep -i error

# Check database state
docker compose exec db psql -U apex -d apex -c "SELECT COUNT(*) FROM projects;"
```

### Step 2: Backup Current State (1 minute)

```bash
# Backup database (if possible)
docker compose exec db pg_dump -U apex apex > backup_rollback_$(date +%Y%m%d_%H%M%S).sql

# Export environment variables
docker compose config > compose_backup_$(date +%Y%m%d_%H%M%S).yaml
```

### Step 3: Stop Services (30 seconds)

```bash
docker compose down
```

### Step 4: Revert Database (if migrated) (2 minutes)

```bash
# Check migration history
docker compose exec db psql -U apex -d apex -c "SELECT * FROM alembic_version;"

# Rollback to previous migration
cd ../services/api
docker compose exec api alembic downgrade -1

# Or rollback to specific version
docker compose exec api alembic downgrade <previous-version>

# Verify rollback
docker compose exec db psql -U apex -d apex -c "SELECT * FROM alembic_version;"
```

**⚠️ WARNING**: Database rollback may cause data loss if schema changed

### Step 5: Revert Configuration (30 seconds)

```bash
cd infra

# Revert compose.yaml changes
git checkout HEAD -- compose.yaml

# Or manually revert critical fixes (if needed)
# Edit compose.yaml to restore previous state
```

### Step 6: Rebuild and Restart (2 minutes)

```bash
# Rebuild from previous state
docker compose build

# Start services
docker compose up -d

# Wait for health checks
sleep 60

# Verify
docker compose ps
```

---

## Data Recovery

### If Database Rollback Needed

**Option 1: Restore from Backup**

```bash
# List available backups
ls -lh infra/backups/

# Restore most recent backup
docker compose exec -T db psql -U apex apex < infra/backups/backup_YYYYMMDD.sql

# Verify restore
docker compose exec db psql -U apex -d apex -c "SELECT COUNT(*) FROM projects;"
```

**Option 2: Point-in-Time Recovery (if WAL enabled)**

```bash
# Stop database
docker compose stop db

# Restore WAL files (if configured)
# Process depends on WAL archiving setup

# Restart database
docker compose start db
```

**Option 3: Manual Data Fix**

```bash
# If only specific tables affected
docker compose exec db psql -U apex -d apex

# Manual SQL to fix data
-- Fix commands here
```

### If Volume Data Lost

```bash
# Check volume status
docker volume ls | grep apex

# If volumes corrupted, recreate
docker compose down -v  # ⚠️ WARNING: Deletes all data
docker compose up -d
```

---

## Rollback Verification

### Immediate Checks (< 1 minute)

```bash
# 1. All services running
docker compose ps
# All should show: "running" or "healthy"

# 2. Health endpoints responding
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# 3. No critical errors in logs
docker compose logs --tail=50 | grep -i "error\|fatal\|critical"
# Should show minimal errors
```

### Functional Verification (2 minutes)

```bash
# 1. API functional
curl http://localhost:8000/api/v1/projects
# Expected: 200 OK

# 2. Database accessible
docker compose exec db psql -U apex -d apex -c "SELECT 1;"
# Expected: 1

# 3. Frontend accessible
curl http://localhost:5173
# Expected: 200 OK

# 4. End-to-end test
# Create test project, run calculation, generate report
```

---

## Post-Rollback Actions

### Immediate (15 minutes)

1. **Document Rollback**:
   - What was rolled back
   - Why it was rolled back
   - What was the failure
   - Time of rollback

2. **Notify Team**:
   - Rollback completed
   - System restored to previous state
   - Any data loss or issues

3. **Monitor System**:
   - Watch logs for 15 minutes
   - Verify all services stable
   - Check for any residual issues

### Short-Term (1-2 hours)

1. **Root Cause Analysis**:
   - Investigate why deployment failed
   - Review logs and metrics
   - Identify failure point

2. **Plan Fix**:
   - Determine what needs fixing
   - Create fix plan
   - Schedule re-deployment

3. **Update Documentation**:
   - Document failure and resolution
   - Update deployment procedures
   - Add to known issues if applicable

### Long-Term (1 week)

1. **Post-Mortem**:
   - Full analysis of failure
   - Lessons learned
   - Process improvements

2. **Preventive Measures**:
   - Update deployment procedures
   - Add additional checks
   - Improve testing

---

## Rollback Decision Checklist

Before executing rollback, verify:

- [ ] Issue is confirmed (not false alarm)
- [ ] Rollback is appropriate (not fix-forward)
- [ ] Backup available (if data involved)
- [ ] Team notified
- [ ] Previous version accessible
- [ ] Rollback plan clear

---

## Emergency Contacts

**On-Call Engineer**: [Name] - [Phone] - [Email]  
**Engineering Lead**: [Name] - [Phone] - [Email]  
**Database Admin**: [Name] - [Phone] - [Email]

---

## Rollback Scenarios

### Scenario 1: Service Won't Start

**Symptoms**: Container restarts repeatedly  
**Cause**: Configuration error, dependency issue  
**Rollback**: Quick rollback to previous compose.yaml

### Scenario 2: Database Migration Failed

**Symptoms**: Migration errors, schema inconsistent  
**Cause**: Migration script error, constraint violation  
**Rollback**: Full rollback with database restore

### Scenario 3: Performance Degradation

**Symptoms**: Slow responses, high CPU/memory  
**Cause**: Resource limits too low, inefficient queries  
**Rollback**: Monitor first, rollback if critical

### Scenario 4: Security Vulnerability

**Symptoms**: Unauthorized access, exposed credentials  
**Cause**: Configuration error, dependency vulnerability  
**Rollback**: Immediate full rollback, security fix

---

**Last Updated**: 2025-01-27  
**Test Frequency**: Quarterly rollback drills

