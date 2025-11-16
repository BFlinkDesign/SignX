# Pre-Deployment Checklist

Complete verification checklist before production deployment.

## Infrastructure Verification

### Docker Environment
- [ ] Docker Desktop running and healthy
- [ ] Docker version: `docker --version` (minimum 20.10+)
- [ ] Docker Compose version: `docker compose version` (minimum 2.0+)
- [ ] Docker daemon responsive: `docker ps`

### Port Availability
Check all required ports are available:
- [ ] Port 8000: API service
- [ ] Port 5173: Frontend (dev server)
- [ ] Port 8002: Signcalc service
- [ ] Port 5432: PostgreSQL
- [ ] Port 6379: Redis
- [ ] Port 9200: OpenSearch
- [ ] Port 9000: MinIO API
- [ ] Port 9001: MinIO Console
- [ ] Port 5601: OpenSearch Dashboards
- [ ] Port 3001: Grafana
- [ ] Port 9187: Postgres Exporter

**Command**: `netstat -ano | findstr ":8000"` (Windows) or `lsof -i :8000` (Linux/Mac)

### System Resources
- [ ] Minimum 8GB RAM available
- [ ] 20GB disk space available
- [ ] CPU: 4+ cores recommended
- [ ] Docker Desktop allocated sufficient resources:
  - Memory: 4GB minimum
  - CPUs: 2 minimum
  - Disk: 20GB available

**Command**: `docker system df` (check disk usage)

### Network Configuration
- [ ] No firewall blocking Docker ports
- [ ] Docker network can reach internet (for image pulls)
- [ ] DNS resolution working: `docker run --rm alpine nslookup google.com`

---

## File Verification

### Dockerfiles
- [ ] `services/api/Dockerfile` exists and valid
- [ ] `services/worker/Dockerfile` exists and valid
- [ ] `services/signcalc-service/Dockerfile` exists and valid
- [ ] `apex/apps/ui-web/Dockerfile` exists and valid

**Command**: `docker build --dry-run services/api` (if available) or manual review

### Compose Configuration
- [ ] `infra/compose.yaml` exists
- [ ] YAML syntax valid: `docker compose config` (no errors)
- [ ] All service definitions complete
- [ ] All environment variables defined

**Command**: `cd infra && docker compose config > /dev/null && echo "Valid" || echo "Invalid"`

### Monitoring Configurations
- [ ] `services/api/monitoring/postgres_exporter.yml` exists
- [ ] `services/api/monitoring/grafana_dashboard.json` exists
- [ ] Config files have valid syntax

**Command**: 
```bash
test -f services/api/monitoring/postgres_exporter.yml && echo "OK" || echo "MISSING"
test -f services/api/monitoring/grafana_dashboard.json && echo "OK" || echo "MISSING"
```

### Directory Structure
- [ ] `infra/backups/` directory exists: `mkdir -p infra/backups`
- [ ] `services/api/src/` contains application code
- [ ] `services/worker/src/` contains worker code
- [ ] `services/signcalc-service/` contains solver code
- [ ] `apex/apps/ui-web/` contains frontend code

---

## Configuration Verification

### Critical Fixes Applied
- [ ] **tmpfs ownership fixed** in `infra/compose.yaml`:
  ```yaml
  tmpfs:
    - /tmp:uid=1000,gid=1000,mode=1777
  ```
  (Lines 51-52 for api, 74-75 for worker)

- [ ] **Dockerfile ownership fixed**:
  - `services/api/Dockerfile` uses `COPY --chown=appuser:appuser`
  - `services/worker/Dockerfile` uses `COPY --chown=appuser:appuser`
  - Explicit user creation in Dockerfiles

### Environment Variables
- [ ] All required environment variables set in compose.yaml
- [ ] OpenSearch password: `StrongDevPassword123!@#` (dev) or secret (prod)
- [ ] Database credentials configured
- [ ] Redis URL configured
- [ ] MinIO credentials configured
- [ ] CORS origins configured
- [ ] Rate limits configured

### Security Settings
- [ ] `no-new-privileges:true` set for api and worker
- [ ] `read_only: true` set for api and worker
- [ ] tmpfs ownership matches USER directive
- [ ] No secrets hardcoded in compose.yaml (production)

---

## Service-Specific Checks

### Frontend Service
- [ ] Dockerfile exists: `apex/apps/ui-web/Dockerfile`
- [ ] nginx.conf exists (if using nginx)
- [ ] Build context correct in compose.yaml
- [ ] Environment variables set (VITE_API_BASE, etc.)

### Signcalc Service
- [ ] Dockerfile includes WeasyPrint dependencies
- [ ] All Python dependencies listed
- [ ] Health check endpoint configured: `/healthz`

### API Service
- [ ] Python base image: `python:3.11-slim` (not pinned SHA)
- [ ] All dependencies in `pyproject.toml`
- [ ] Health check configured: `/health` and `/ready`
- [ ] Port 8000 exposed

### Worker Service
- [ ] Python base image: `python:3.11-slim` (not pinned SHA)
- [ ] Celery configured correctly
- [ ] Redis connection configured
- [ ] Health check configured

### Database Service
- [ ] Image specified: `pgvector/pgvector:pg16`
- [ ] PostgreSQL extensions enabled (pgvector, pg_stat_statements)
- [ ] Connection parameters configured
- [ ] Volume mounts configured (data, backups)

---

## Test Readiness

### Agent Reports
- [ ] **Agent 1 (Frontend)**: No critical errors, build succeeds
- [ ] **Agent 2 (Backend)**: All API endpoints functional, no critical errors
- [ ] **Agent 3 (Database)**: Migrations ready, schema validated
- [ ] **Agent 4 (Solvers)**: All solvers tested, performance acceptable
- [ ] **Agent 5 (Testing)**: Infrastructure services healthy, tests passing
- [ ] **Agent 6 (Documentation)**: All docs complete

**Status**: Review `docs/deployment/FINAL_VALIDATION_REPORT.md`

### Database Readiness
- [ ] Migrations tested: `alembic upgrade head` (dry-run)
- [ ] Schema validated
- [ ] Seed data ready (if applicable)
- [ ] Backup strategy defined

### Test Data
- [ ] Test project data prepared (if needed)
- [ ] Sample calculations validated
- [ ] Test users configured (if needed)

---

## Build Verification

### Image Builds
- [ ] All images build successfully:
  ```bash
  cd infra
  docker compose build --parallel
  ```
- [ ] No build errors or warnings
- [ ] All dependencies installed correctly
- [ ] Image sizes reasonable (<500MB per service)

### Image Tags
- [ ] Images tagged correctly
- [ ] Version labels set
- [ ] Git SHA in image metadata (if configured)

---

## Pre-Deployment Commands

Run these commands to verify readiness:

```bash
# 1. Navigate to infra directory
cd infra

# 2. Validate compose.yaml
docker compose config > /dev/null && echo "✅ Compose valid" || echo "❌ Compose invalid"

# 3. Check for port conflicts
netstat -ano | findstr ":8000 :5173 :5432 :6379"  # Windows
# or
lsof -i :8000,5173,5432,6379  # Linux/Mac

# 4. Verify file existence
test -f ../services/api/Dockerfile && echo "✅ API Dockerfile" || echo "❌ Missing"
test -f ../services/worker/Dockerfile && echo "✅ Worker Dockerfile" || echo "❌ Missing"
test -d ../services/api/monitoring && echo "✅ Monitoring configs" || echo "❌ Missing"

# 5. Check disk space
docker system df

# 6. Verify Docker daemon
docker ps

# 7. Validate fixes applied
grep -A 1 "tmpfs:" compose.yaml | grep "uid=1000" && echo "✅ tmpfs fixed" || echo "❌ tmpfs not fixed"
```

---

## Checklist Summary

### Critical Items (Must Complete)
- [ ] All critical fixes applied (tmpfs, Dockerfile ownership)
- [ ] All required files exist
- [ ] All ports available
- [ ] Docker environment healthy
- [ ] Compose.yaml syntax valid

### Important Items (Should Complete)
- [ ] Backups directory created
- [ ] Resource limits configured
- [ ] Environment variables verified
- [ ] Agent reports reviewed
- [ ] Database migrations ready

### Nice-to-Have (Optional)
- [ ] Path corrections applied
- [ ] postgres_exporter config reviewed
- [ ] All documentation reviewed
- [ ] Test data prepared

---

## Go/No-Go Decision

**If all Critical Items checked**: ✅ **GO**  
**If any Critical Item unchecked**: ❌ **NO-GO**

**If all Important Items checked**: ✅ **Strong GO**  
**If Important Items incomplete**: 🟡 **Conditional GO** (document issues)

---

**Last Updated**: 2025-01-27  
**Next Review**: Before each deployment

