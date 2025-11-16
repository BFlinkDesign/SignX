# Rollback Procedures

**Purpose**: Complete rollback procedures for failed deployments  
**Last Updated**: 2025-01-27  
**Use When**: Deployment fails or causes critical issues

---

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

---

## Rollback Strategies

### Strategy 1: Database Snapshot Restore

**Use When**: Database changes need to be reverted

#### Step 1: Locate Backup

```bash
# List available backups
ls -lh infra/backups/

# Identify pre-deployment backup
# Format: backup_YYYYMMDD_HHMMSS.sql
```

#### Step 2: Stop Services

```bash
cd infra
docker compose down
```

#### Step 3: Restore Database

```bash
# Restore from backup
docker compose up -d db
sleep 30  # Wait for database ready

docker compose exec -T db psql -U apex apex < infra/backups/backup_PREDEPLOYMENT.sql

# Verify restore
docker compose exec db psql -U apex -d apex -c "SELECT COUNT(*) FROM projects;"
```

#### Step 4: Restore Migration State

```bash
# If migration was run, rollback Alembic version
docker compose up -d api
docker compose exec api alembic downgrade -1

# Or downgrade to specific version
docker compose exec api alembic downgrade <previous-version>

# Verify
docker compose exec api alembic current
```

#### Step 5: Restart Services

```bash
docker compose up -d
sleep 60  # Wait for health checks

# Verify all services
docker compose ps
```

**Verification**:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
docker compose exec db psql -U apex -d apex -c "SELECT version FROM alembic_version;"
```

---

### Strategy 2: Docker Image Rollback

**Use When**: Application code changes need to be reverted

#### Step 1: Identify Previous Images

```bash
# List available images
docker images | grep apex

# Note previous version tags
# Example: apex-api:pre-deploy, apex-api:v0.1.0
```

#### Step 2: Stop Services

```bash
cd infra
docker compose down
```

#### Step 3: Update Image Tags

```yaml
# Option A: Edit compose.yaml to use previous image
api:
  image: apex-api:pre-deploy  # Previous version

# Option B: Rebuild from previous commit
git checkout <previous-commit>
docker compose build api worker signcalc
git checkout main  # Return to current
```

#### Step 4: Restart with Previous Images

```bash
# Option A: Use tagged images
docker compose up -d

# Option B: Rebuild and start
docker compose build --no-cache api worker
docker compose up -d
```

#### Step 5: Verify Rollback

```bash
# Check images in use
docker compose ps --format "table {{.Name}}\t{{.Image}}"

# Verify functionality
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/projects
```

**Verification**:
```bash
# Confirm image version
docker compose exec api cat /app/src/apex/__init__.py | grep __version__
# Or check commit hash if injected
```

---

### Strategy 3: Configuration Restore

**Use When**: Configuration changes caused the failure

#### Step 1: Backup Current Configuration

```bash
# Backup current compose.yaml
cp infra/compose.yaml infra/compose.yaml.broken

# Backup environment variables (if changed)
docker compose config > infra/compose.backup.yaml
```

#### Step 2: Restore Previous Configuration

```bash
# Option A: Git checkout
cd infra
git checkout HEAD -- compose.yaml

# Option B: Restore from backup
cp infra/compose.yaml.backup infra/compose.yaml

# Option C: Manual revert
# Edit compose.yaml to remove problematic changes
```

#### Step 3: Validate Configuration

```bash
# Validate syntax
docker compose config > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Configuration valid"
else
    echo "❌ Configuration invalid"
    exit 1
fi
```

#### Step 4: Apply Configuration

```bash
# Recreate services with restored config
docker compose down
docker compose up -d
```

#### Step 5: Verify Services

```bash
# Wait for health checks
sleep 60

# Check all services
docker compose ps

# Verify functionality
curl http://localhost:8000/health
```

**Verification**:
```bash
# Confirm configuration restored
docker compose config | grep -A 5 "api:"
# Compare with expected values
```

---

### Strategy 4: Service Restart Sequence

**Use When**: Services need orderly restart without full rollback

#### Step 1: Stop Application Services

```bash
cd infra

# Stop application services first
docker compose stop api worker signcalc frontend

# Keep infrastructure running
# db, cache, object, search remain running
```

#### Step 2: Clear Caches (Optional)

```bash
# Clear Redis cache (if safe)
docker compose exec cache redis-cli FLUSHDB

# Clear application caches
docker compose exec api python -c "
from apex.api.cache import cache
cache.clear()
"
```

#### Step 3: Restart in Correct Order

```bash
# Start infrastructure (if stopped)
docker compose start db cache object search

# Wait for infrastructure healthy
sleep 30

# Start application services
docker compose start api worker signcalc frontend

# Wait for application ready
sleep 30
```

#### Step 4: Verify Restart

```bash
# Check all services
docker compose ps

# Verify health
curl http://localhost:8000/health
curl http://localhost:8000/ready

# Check logs for errors
docker compose logs --tail=50 api | grep -i error
```

**Verification**:
```bash
# Confirm all services healthy
docker compose ps --format "table {{.Name}}\t{{.Status}}"
# All should show: "running" or "healthy"

# Test functionality
curl http://localhost:8000/api/v1/projects
```

---

## Full Rollback Procedure

**Use When**: Complete rollback needed (code + database + config)

### Phase 1: Assessment (2 minutes)

```bash
# 1. Document current state
docker compose ps > rollback_state.txt
docker compose logs --tail=100 > rollback_logs.txt

# 2. Identify what needs rollback
# - Database migrations?
# - Code changes?
# - Configuration changes?

# 3. Locate backups
ls -lh infra/backups/
```

### Phase 2: Backup Current State (2 minutes)

```bash
# 1. Backup database
docker compose exec db pg_dump -U apex apex > backup_before_rollback_$(date +%Y%m%d_%H%M%S).sql

# 2. Backup configuration
docker compose config > compose_before_rollback.yaml

# 3. Export environment
docker compose exec api env > env_backup.txt
```

### Phase 3: Stop All Services (1 minute)

```bash
docker compose down
```

### Phase 4: Restore Database (3 minutes)

```bash
# 1. Start database
docker compose up -d db
sleep 30

# 2. Restore backup
docker compose exec -T db psql -U apex apex < infra/backups/backup_PREDEPLOYMENT.sql

# 3. Verify restore
docker compose exec db psql -U apex -d apex -c "\dt"
```

### Phase 5: Restore Code (2 minutes)

```bash
# 1. Revert to previous commit
git log --oneline -10
git checkout <previous-working-commit>

# Or restore previous images
docker tag apex-api:pre-deploy apex-api:dev
docker tag apex-worker:pre-deploy apex-worker:dev
```

### Phase 6: Restore Configuration (1 minute)

```bash
# Restore compose.yaml
git checkout HEAD -- infra/compose.yaml
# Or manually revert
```

### Phase 7: Rebuild and Start (5 minutes)

```bash
# 1. Rebuild images
docker compose build api worker signcalc

# 2. Start services
docker compose up -d

# 3. Run migrations (if needed, but should match database state)
docker compose exec api alembic current
# Verify matches database state

# 4. Wait for health checks
sleep 60
```

### Phase 8: Verification (3 minutes)

```bash
# 1. All services healthy
docker compose ps

# 2. Health endpoints
curl http://localhost:8000/health
curl http://localhost:8000/ready

# 3. Functional test
curl http://localhost:8000/api/v1/projects

# 4. Database state
docker compose exec db psql -U apex -d apex -c "SELECT COUNT(*) FROM projects;"
```

**Total Time**: ~20 minutes

---

## Quick Rollback (< 5 minutes)

**Use When**: Recent deployment, no complex changes

```bash
# 1. Stop services
docker compose down

# 2. Restore previous images
docker tag apex-api:pre-deploy apex-api:dev
docker tag apex-worker:pre-deploy apex-worker:dev

# 3. Restart
docker compose up -d

# 4. Verify
sleep 60
curl http://localhost:8000/health
```

---

## Rollback Verification Checklist

### Immediate (< 5 minutes)

- [ ] All services running
- [ ] Health endpoints responding
- [ ] No critical errors in logs
- [ ] Database accessible

### Functional (10 minutes)

- [ ] API endpoints responding
- [ ] Database queries working
- [ ] Frontend accessible
- [ ] Basic workflow functional

### Full Verification (30 minutes)

- [ ] All workflows tested
- [ ] Performance acceptable
- [ ] No data loss
- [ ] Monitoring operational

---

## Post-Rollback Actions

### Immediate (15 minutes)

1. **Document Rollback**:
   - What was rolled back
   - Why it was rolled back
   - Time of rollback
   - State before/after

2. **Notify Team**:
   - Rollback completed
   - System restored
   - Next steps

3. **Monitor System**:
   - Watch logs for 30 minutes
   - Verify stability
   - Check for residual issues

### Short-Term (1-2 hours)

1. **Root Cause Analysis**:
   - Investigate failure
   - Review logs
   - Identify failure point

2. **Plan Fix**:
   - Determine fix needed
   - Create fix plan
   - Schedule re-deployment

---

## Rollback Scenarios

### Scenario 1: Database Migration Failed

**Symptoms**: Migration errors, schema inconsistent  
**Rollback**: Full rollback with database restore  
**Time**: 10-15 minutes

---

### Scenario 2: Application Code Issue

**Symptoms**: Service crashes, errors in logs  
**Rollback**: Docker image rollback  
**Time**: 5-10 minutes

---

### Scenario 3: Configuration Error

**Symptoms**: Services won't start, connection errors  
**Rollback**: Configuration restore  
**Time**: 3-5 minutes

---

### Scenario 4: Performance Degradation

**Symptoms**: Slow responses, high resource usage  
**Rollback**: Service restart sequence  
**Time**: 2-3 minutes

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-27  
**Test Frequency**: Quarterly rollback drills

