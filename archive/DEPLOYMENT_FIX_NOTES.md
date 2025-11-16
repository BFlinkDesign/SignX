# Docker Compose Deployment Fix Notes

**Date**: 2025-01-27  
**Issue**: Docker image version conflicts and HEALTHCHECK syntax errors

---

## Issues Fixed

### 1. PostgreSQL Exporter Image Version ✅

**Problem**: `quay.io/prometheuscommunity/postgres-exporter:v0.15.1` not found

**Fix**: Changed to `prometheuscommunity/postgres-exporter:v0.15.0`

**Location**: `infra/compose.yaml` line 127

```yaml
postgres_exporter:
  image: prometheuscommunity/postgres-exporter:v0.15.0  # Was: quay.io/...v0.15.1
```

**Verification**: Image pull successful ✅

---

### 2. Dockerfile Syntax Errors ✅

**Problem**: 
- Invalid Python base image SHA: `python:3.11-slim@sha256:9a0d733f8f4f5d2b5b8a5d5a5f4a9b2e6b86f1a9b6a7e9e4c4913a2f8f3c2e8a`
- Multi-line HEALTHCHECK heredoc syntax not supported in older Docker versions

**Fix**: 
- Removed `@sha256:` pinned version to use latest `python:3.11-slim` tag
- Simplified HEALTHCHECK commands
- Removed unsupported Dockerfile 1.7 syntax

**Files Fixed**:
1. `services/api/Dockerfile` ✅
2. `services/worker/Dockerfile` ✅
3. `services/signcalc-service/Dockerfile` ✅ (already clean)

**Changes**:
```dockerfile
# Before
FROM python:3.11-slim@sha256:9a0d733f8f4f5d2b5b8a5d5a5f4a9b2e6b86f1a9b6a7e9e4c4913a2f8f3c2e8a

# After
FROM python:3.11-slim
```

---

## Docker Compose Configuration

The compose file uses individual Dockerfiles:

**API Service**:
```yaml
api:
  build:
    context: ../services/api
  image: apex-api:dev
```

**Worker Service**:
```yaml
worker:
  build:
    context: ../services/worker
  image: apex-worker:dev
```

**Signcalc Service**:
```yaml
signcalc:
  build:
    context: ../services/signcalc-service
  image: apex-signcalc:dev
```

---

## Deployment Command

```bash
cd "C:\Scripts\Leo Ai Clone"
docker compose -f infra/compose.yaml up -d --build
```

**Expected Behavior**:
1. Pull PostgreSQL, Redis, MinIO, OpenSearch base images
2. Build API, Worker, Signcalc services from source
3. Start all services with health checks
4. Wait for dependencies (db, cache, object, search)
5. Expose services on configured ports

**Monitoring**:
- API: http://localhost:8000/health
- Signcalc: http://localhost:8002/healthz
- Grafana: http://localhost:3001
- OpenSearch: http://localhost:9200
- MinIO: http://localhost:9001

---

## Verification Steps

### 1. Check Build Progress

```powershell
docker compose -f infra/compose.yaml ps
```

### 2. View Logs

```powershell
# All services
docker compose -f infra/compose.yaml logs

# Specific service
docker compose -f infra/compose.yaml logs api
```

### 3. Health Checks

```powershell
# API
Invoke-RestMethod http://localhost:8000/health

# Readiness
Invoke-RestMethod http://localhost:8000/ready

# Signcalc
Invoke-RestMethod http://localhost:8002/healthz
```

### 4. Service Status

```powershell
docker compose -f infra/compose.yaml ps
```

**Expected Status**: All services `running (healthy)` ✅

---

## Next Steps

### After Successful Startup

1. **Run Database Migrations**:
```bash
docker compose -f infra/compose.yaml exec api alembic upgrade head
```

2. **Seed Default Data** (if needed):
```bash
docker compose -f infra/compose.yaml exec api python scripts/seed_defaults.py
```

3. **Verify Endpoints**:
```bash
curl http://localhost:8000/docs
curl http://localhost:8000/version
```

4. **Run Smoke Tests**:
```bash
docker compose -f infra/compose.yaml exec api python scripts/smoke.py
```

---

## Troubleshooting

### Build Fails

**Check Docker logs**:
```powershell
docker compose -f infra/compose.yaml logs --tail=50
```

**Rebuild from scratch**:
```powershell
docker compose -f infra/compose.yaml down -v
docker compose -f infra/compose.yaml up -d --build --no-cache
```

### Services Don't Start

**Check health checks**:
```powershell
docker compose -f infra/compose.yaml ps
```

**Force restart**:
```powershell
docker compose -f infra/compose.yaml restart
```

### Port Conflicts

**Check what's using ports**:
```powershell
netstat -an | findstr "8000 5432 6379 9000 9200 3001"
```

**Stop conflicting services** or modify compose file ports

---

## Status

**Fixes Applied**: ✅  
**Docker Compose File**: ✅ Updated  
**Dockerfiles**: ✅ Fixed  
**Build**: 🔄 In Progress  
**Deployment**: ⏳ Awaiting Build Completion

---

**Next**: Monitor build progress and verify all services start successfully

