# Deployment Execution Guide

**Date**: 2025-01-27  
**Status**: ✅ Ready for Execution

---

## Quick Start

### Option 1: PowerShell (Recommended for Windows)

```powershell
# Execute full deployment
.\scripts\execute_deployment.ps1
```

### Option 2: Bash (Linux/Mac/Git Bash)

```bash
# Execute full deployment
bash scripts/staging_deploy.sh
```

---

## Manual Step-by-Step Execution

### Priority 1: Pre-Deployment Check

```powershell
# PowerShell
bash scripts/pre_deploy_check.sh

# Or simplified check
cd infra
docker compose -f compose.yaml ps | Select-String "healthy"
```

**Expected Result**: ✅ Pre-deployment checks PASSED

---

### Priority 2: Setup Monitoring

#### Import Grafana Dashboard

```powershell
# PowerShell script
.\scripts\import_grafana_dashboard.ps1

# Or manual import
$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:admin"))
}
$dashboard = Get-Content "infra/monitoring/grafana/dashboards/apex-overview.json" -Raw
Invoke-RestMethod -Uri "http://localhost:3001/api/dashboards/db" -Method Post -Headers $headers -Body $dashboard
```

**Expected Result**: Dashboard imported successfully

---

### Priority 3: Deploy Services

#### Option A: Automated (Recommended)

```powershell
.\scripts\execute_deployment.ps1
```

#### Option B: Manual Step-by-Step

```powershell
# 1. Start infrastructure services
cd infra
docker compose up -d db cache object search

# 2. Wait for services to be healthy
Start-Sleep -Seconds 30

# 3. Run database migrations
docker exec apex-api-1 alembic upgrade head

# 4. Start application services
docker compose up -d api worker signcalc

# 5. Wait for services to start
Start-Sleep -Seconds 15

# 6. Verify health
curl http://localhost:8000/health

# 7. Check readiness
curl http://localhost:8000/ready
```

---

## Verification Checklist

After deployment, verify:

- [ ] **API Health**: `curl http://localhost:8000/health` returns 200 OK
- [ ] **API Readiness**: `curl http://localhost:8000/ready` shows all checks OK
- [ ] **Signcalc Health**: `curl http://localhost:8002/healthz` returns 200 OK
- [ ] **All Services Running**: `docker compose ps` shows all services running
- [ ] **Grafana Dashboard**: http://localhost:3001 shows metrics
- [ ] **Frontend**: http://localhost:5173 loads correctly

---

## Service URLs

After successful deployment:

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Signcalc**: http://localhost:8002

---

## Troubleshooting

### Services Not Starting

```powershell
# Check logs
docker compose logs --tail=50 api
docker compose logs --tail=50 worker

# Check service status
docker compose ps

# Restart specific service
docker compose restart api
```

### Database Migration Failed

```powershell
# Check database connection
docker compose exec db psql -U apex -d apex -c "\dt"

# Retry migration
docker compose exec api alembic upgrade head

# Check migration history
docker compose exec api alembic history
```

### Health Check Failing

```powershell
# Check API health endpoint directly
docker compose exec api curl http://localhost:8000/health

# Check database connection from API
docker compose exec api python -c "from apex.api.db import get_db; print(next(get_db()))"

# Check environment variables
docker compose exec api env | Select-String "DATABASE_URL|REDIS_URL"
```

---

## Post-Deployment Tasks

1. **Import Grafana Dashboard** (if not done during deployment)
   ```powershell
   .\scripts\import_grafana_dashboard.ps1
   ```

2. **Run Smoke Tests**
   ```powershell
   # Create test project
   curl -X POST http://localhost:8000/api/v1/projects -H "Content-Type: application/json" -d '{"account_id": "test", "name": "Test Project", "customer": "Test"}'
   
   # Test site resolution
   curl -X POST http://localhost:8000/api/v1/signage/common/site/resolve -H "Content-Type: application/json" -d '{"address": "123 Main St, Dallas, TX 75201"}'
   ```

3. **Monitor First Hour**
   - Watch Grafana dashboard
   - Check for errors in logs
   - Verify all endpoints responding

4. **Document Results**
   - Update `docs/deployment/DEPLOYMENT_EXECUTED.md`
   - Record any issues encountered
   - Note performance metrics

---

## Rollback Procedure

If deployment fails:

```powershell
# Stop all services
docker compose down

# Restore previous configuration (if needed)
# git checkout <previous-commit> compose.yaml

# Restore database (if needed)
# docker compose exec db psql -U apex -d apex < backup.sql

# Start previous version
docker compose up -d
```

See: `docs/deployment/ROLLBACK_PROCEDURE.md` for detailed steps.

---

## Success Criteria

✅ **All services healthy**
- All containers running
- Health endpoints responding
- No critical errors in logs

✅ **Monitoring operational**
- Grafana dashboard accessible
- Prometheus scraping metrics
- Dashboards displaying data

✅ **Smoke tests passing**
- Create project: Success
- Site resolution: Success
- Calculations: Success

---

**Last Updated**: 2025-01-27  
**Ready for**: Staging/Development Deployment

