# Deployment Execution Plan

Step-by-step deployment execution plan with time estimates.

## Overview

**Total Estimated Time**: 25-30 minutes  
**Deployment Type**: Blue-Green (if supported) or Rolling  
**Rollback Window**: 30 minutes after deployment

## Prerequisites

Before starting, ensure:
- ✅ All items in [PRE_DEPLOYMENT_CHECKLIST.md](PRE_DEPLOYMENT_CHECKLIST.md) completed
- ✅ Critical fixes applied (see [PRODUCTION_FIXES_REQUIRED.md](PRODUCTION_FIXES_REQUIRED.md))
- ✅ Backup of current state (if upgrading)
- ✅ Team notified of deployment window

---

## Phase 1: Pre-Flight (5 minutes)

**Objective**: Prepare environment and verify readiness

### Step 1.1: Stop Running Services (1 minute)

```bash
# Navigate to infra directory
cd infra

# Stop all running containers
docker compose down

# Verify all stopped
docker compose ps
# Should show: "No services found" or empty list
```

**Verification**: `docker compose ps` shows no running services

### Step 1.2: Apply Critical Fixes (2 minutes)

If not already applied:

```bash
# Verify tmpfs ownership fix
grep -A 2 "tmpfs:" compose.yaml | grep "uid=1000"
# Should show: /tmp:uid=1000,gid=1000,mode=1777

# If not applied, edit compose.yaml:
# - Line 51-52: api service tmpfs
# - Line 74-75: worker service tmpfs
```

**Verification**: tmpfs lines contain `uid=1000,gid=1000,mode=1777`

### Step 1.3: Create Required Directories (30 seconds)

```bash
# Create backups directory
mkdir -p backups
chmod 755 backups

# Verify
test -d backups && echo "✅ Backups directory exists" || echo "❌ Missing"
```

### Step 1.4: Verify All Files Present (1 minute)

```bash
# Check critical files
test -f compose.yaml && echo "✅ compose.yaml" || echo "❌ Missing"
test -f ../services/api/Dockerfile && echo "✅ API Dockerfile" || echo "❌ Missing"
test -f ../services/worker/Dockerfile && echo "✅ Worker Dockerfile" || echo "❌ Missing"
test -f ../services/api/monitoring/postgres_exporter.yml && echo "✅ Exporter config" || echo "❌ Missing"
test -f ../services/api/monitoring/grafana_dashboard.json && echo "✅ Grafana dashboard" || echo "❌ Missing"
```

### Step 1.5: Review Agent Reports (30 seconds)

```bash
# Review final validation report
cat ../docs/deployment/FINAL_VALIDATION_REPORT.md | grep -A 5 "Agent Status"
```

**Check**: All agents show ✅ Ready or acceptable status

---

## Phase 2: Build (5-7 minutes)

**Objective**: Build all Docker images

### Step 2.1: Clean Build (Optional, 1 minute)

```bash
# Remove old images (optional, saves space)
docker compose down --rmi all

# Or keep images and rebuild
docker compose build --no-cache
```

**Decision**: Use `--no-cache` for clean build or incremental for speed

### Step 2.2: Build All Images (4-5 minutes)

```bash
# Build all images in parallel
docker compose build --parallel

# Monitor build output for errors
# Each service should show: "Successfully built" or "Successfully tagged"
```

**Expected Output**:
```
[+] Building api (Dockerfile)                      ... done
[+] Building worker (Dockerfile)                   ... done
[+] Building signcalc (Dockerfile)                ... done
[+] Building frontend (Dockerfile)                 ... done
```

### Step 2.3: Verify Build Success (1 minute)

```bash
# Check all images built
docker images | grep apex

# Should show:
# apex-api:dev
# apex-worker:dev
# apex-signcalc:dev
# apex-frontend:dev
```

**Verification**: All images present and tagged correctly

---

## Phase 3: Deploy (3-5 minutes)

**Objective**: Start all services

### Step 3.1: Start Infrastructure Services (2 minutes)

```bash
# Start infrastructure first (db, cache, object, search)
docker compose up -d db cache object search

# Wait for health checks
sleep 30

# Verify infrastructure healthy
docker compose ps db cache object search
# All should show: "healthy" or "running"
```

**Verification**: All infrastructure services show "healthy"

### Step 3.2: Start Application Services (2 minutes)

```bash
# Start application services
docker compose up -d api worker signcalc

# Wait for health checks
sleep 30

# Verify services started
docker compose ps api worker signcalc
```

### Step 3.3: Start Frontend and Monitoring (1 minute)

```bash
# Start remaining services
docker compose up -d frontend grafana postgres_exporter dashboards

# Wait for health checks
sleep 30
```

### Step 3.4: Verify All Services (1 minute)

```bash
# Check all services
docker compose ps

# All services should show:
# - Status: "running" or "healthy"
# - No "unhealthy" or "restarting" services
```

**Verification**: All services running, no errors in status

---

## Phase 4: Database (2 minutes)

**Objective**: Run migrations and verify database

### Step 4.1: Wait for Database Ready (30 seconds)

```bash
# Wait for database to be fully ready
docker compose exec db pg_isready -U apex
# Should return: "accepting connections"
```

### Step 4.2: Run Migrations (1 minute)

```bash
# Run migrations
docker compose exec api alembic upgrade head

# Expected output:
# INFO  [alembic.runtime.migration] Running upgrade ... -> ..., ...
# INFO  [alembic.runtime.migration] Context: ...
# INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

**Verification**: Migrations complete without errors

### Step 4.3: Verify Tables Created (30 seconds)

```bash
# Verify tables exist
docker compose exec db psql -U apex -d apex -c "\dt"

# Should show tables:
# - projects
# - project_payloads
# - project_events
# - etc.
```

---

## Phase 5: Verification (5 minutes)

**Objective**: Verify all services functional

### Step 5.1: Health Endpoint Checks (2 minutes)

```bash
# API health
curl http://localhost:8000/health
# Expected: {"status":"ok","service":"api","version":"0.1.0"}

# API readiness
curl http://localhost:8000/ready
# Expected: {"status":"ready","checks":{"database":"ok",...}}

# Signcalc health
curl http://localhost:8002/healthz
# Expected: {"status":"ok"}

# Frontend health
curl http://localhost:5173/health  # If configured
# Expected: 200 OK

# Grafana health
curl http://localhost:3001/api/health
# Expected: {"commit":"...","database":"ok",...}
```

### Step 5.2: Service Integration Tests (2 minutes)

```bash
# Test API → Database
curl http://localhost:8000/api/v1/projects
# Expected: [] or list of projects

# Test API → Redis
curl http://localhost:8000/ready | jq '.checks.redis'
# Expected: "ok"

# Test API → MinIO
curl http://localhost:8000/ready | jq '.checks.object_storage'
# Expected: "ok"

# Test API → OpenSearch
curl http://localhost:8000/ready | jq '.checks.search'
# Expected: "ok"
```

### Step 5.3: Check Logs for Errors (1 minute)

```bash
# Check all service logs
docker compose logs --tail=50 | grep -i error

# Should show minimal or no errors
# Expected: No critical errors (warnings OK)
```

**Verification**: No critical errors in logs

---

## Phase 6: Smoke Test (5 minutes)

**Objective**: Verify end-to-end workflow

### Step 6.1: Create Test Project (1 minute)

```bash
# Create project via API
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "test",
    "name": "Smoke Test Project",
    "customer": "Test Customer"
  }'

# Expected: 201 Created with project_id
# Save project_id for next steps
```

### Step 6.2: Run Calculation (2 minutes)

```bash
# Test site resolution
curl -X POST http://localhost:8000/api/v1/signage/common/site/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "address": "123 Main St, Dallas, TX 75201"
  }'

# Expected: 200 OK with wind data

# Test cabinet derive
curl -X POST http://localhost:8000/api/v1/signage/common/cabinets/derive \
  -H "Content-Type: application/json" \
  -d '{
    "overall_height_ft": 25.0,
    "cabinets": [{"width_ft": 14.0, "height_ft": 8.0, "depth_in": 12.0}]
  }'

# Expected: 200 OK with derived dimensions
```

### Step 6.3: Generate Report (2 minutes)

```bash
# Request report generation
curl -X POST http://localhost:8000/api/v1/projects/{project_id}/report

# Expected: 202 Accepted with task_id

# Poll task status
curl http://localhost:8000/api/v1/tasks/{task_id}

# Expected: Eventually returns completed with pdf_ref
```

**Verification**: End-to-end workflow completes successfully

---

## Post-Deployment

### Immediate Actions (5 minutes)

1. **Monitor Logs**:
   ```bash
   docker compose logs -f
   ```

2. **Check Metrics**:
   - Grafana: http://localhost:3001
   - Verify dashboards loading

3. **Notify Team**:
   - Deployment complete
   - Services accessible
   - Any known issues

### First Hour Monitoring

See [POST_DEPLOYMENT_MONITORING.md](POST_DEPLOYMENT_MONITORING.md) for detailed monitoring plan.

---

## Deployment Timeline Summary

| Phase | Duration | Critical Path |
|-------|----------|---------------|
| Pre-Flight | 5 min | ✅ Required |
| Build | 5-7 min | ✅ Required |
| Deploy | 3-5 min | ✅ Required |
| Database | 2 min | ✅ Required |
| Verification | 5 min | ✅ Required |
| Smoke Test | 5 min | ⚠️ Recommended |
| **Total** | **25-30 min** | |

---

## Rollback Procedure

If deployment fails at any phase:

See [ROLLBACK_PROCEDURE.md](ROLLBACK_PROCEDURE.md) for complete rollback steps.

**Quick Rollback** (< 2 minutes):
```bash
# Stop all services
docker compose down

# If database migration failed
docker compose exec db psql -U apex -d apex -c "ROLLBACK;"

# Restore previous version
git checkout <previous-tag>
docker compose up -d
```

---

**Last Updated**: 2025-01-27  
**Next Review**: Before each deployment

