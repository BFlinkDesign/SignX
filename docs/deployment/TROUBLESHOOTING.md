# Troubleshooting Guide

Common deployment and runtime issues with step-by-step solutions.

## Quick Diagnostic Commands

```bash
# Check all services status
docker compose ps

# Check logs for all services
docker compose logs --tail=50

# Check specific service logs
docker compose logs api --tail=100

# Check service health
curl http://localhost:8000/health
curl http://localhost:8000/ready

# Check resource usage
docker stats --no-stream

# Check disk space
docker system df
```

---

## Common Issues

### Issue 0: ConfigDict Errors (Pydantic Version Mismatch)

**Symptoms**:
- `TypeError: 'ConfigDict' object is not callable`
- `AttributeError: type object 'ConfigDict' has no attribute 'X'`
- Import errors with Pydantic
- Validation errors in API routes

**Diagnosis**:
```bash
# Check Pydantic version
docker compose exec api python -c "import pydantic; print(pydantic.__version__)"

# Expected: 2.x.x (Pydantic v2)
# Problem: If shows 1.x.x, version mismatch

# Check requirements
docker compose exec api cat requirements.txt | grep pydantic
```

**Root Cause**: Pydantic v1 vs v2 incompatibility. APEX uses Pydantic v2.

**Solution**:
```bash
# Verify Pydantic v2 in requirements
# In pyproject.toml or requirements.txt:
pydantic>=2.0.0,<3.0.0

# Rebuild container
docker compose build api worker
docker compose up -d api worker

# Or update dependencies
docker compose exec api pip install "pydantic>=2.0.0,<3.0.0"
```

**Verification**:
```bash
# Test import
docker compose exec api python -c "from pydantic import ConfigDict; print('OK')"
# Should print: OK
```

---

### Issue 1: Service Won't Start

**Symptoms**:
- Container exits immediately
- Status shows "restarting" or "exited"
- No logs or error messages

**Diagnosis**:
```bash
# Check service status
docker compose ps <service-name>

# Check logs
docker compose logs <service-name> --tail=100

# Check if port is already in use
netstat -ano | findstr ":8000"  # Windows
lsof -i :8000                    # Linux/Mac

# Check Docker daemon
docker ps
```

**Solutions**:

1. **Port Already in Use**
   ```bash
   # Find process using port
   netstat -ano | findstr ":8000"
   # Kill process or change port in compose.yaml
   ```

2. **Missing Environment Variables**
   ```bash
   # Check environment variables
   docker compose config | grep -A 10 <service-name>
   # Verify all required variables set
   ```

3. **Image Build Failed**
   ```bash
   # Rebuild image
   docker compose build <service-name>
   # Check build logs for errors
   ```

4. **Dependency Not Ready**
   ```bash
   # Check dependencies
   docker compose ps db cache object search
   # Wait for dependencies to be healthy
   ```

**Verification**:
```bash
docker compose ps <service-name>
# Should show: "running" or "healthy"
```

---

### Issue 2: Permission Denied Errors

**Symptoms**:
- "Permission denied: /tmp/file.txt"
- "Cannot write to /tmp"
- "Operation not permitted"
- "Permission denied" when accessing volumes

**Diagnosis**:
```bash
# Check tmpfs ownership
docker compose exec api ls -ld /tmp
# Expected: drwxrwxrwt ... 1000 1000 ... /tmp

# Test write permission
docker compose exec api touch /tmp/test.txt
# Should succeed

# Check process user
docker compose exec api ps aux | grep -E "PID|uvicorn"
# Should show user 1000 (appuser)

# Check file ownership
docker compose exec api ls -la /app
# Files should be owned by appuser (1000)
```

**Root Cause**: 
1. **tmpfs ownership mismatch** (root vs USER 1000:1000)
2. **Dockerfile COPY without --chown**

**Solution**:

**Fix 1: tmpfs ownership in compose.yaml**
```yaml
# Fix in compose.yaml (lines 51-52, 74-75)
tmpfs:
  - /tmp:uid=1000,gid=1000,mode=1777
  - /var/tmp:uid=1000,gid=1000,mode=1777
```

**Fix 2: Dockerfile ownership**
```dockerfile
# In Dockerfile, use --chown for all COPY commands:
COPY --chown=appuser:appuser src /app/src
COPY --chown=appuser:appuser pyproject.toml /app/pyproject.toml

# And create appuser before copying:
RUN groupadd -r appuser -g 1000 && \
    useradd -r -u 1000 -g appuser -d /app -s /bin/bash appuser && \
    chown -R appuser:appuser /app
```

**After Fix**:
```bash
# Rebuild and restart
docker compose build api worker
docker compose up -d api worker

# Verify fix
docker compose exec api ls -ld /tmp
# Should show: drwxrwxrwt ... 1000 1000 ... /tmp

docker compose exec api whoami
# Should show: appuser
```

---

### Issue 3: Connection Refused

**Symptoms**:
- "Connection refused" errors
- "Cannot connect to service"
- Service startup fails
- Health checks failing

**Diagnosis**:
```bash
# Check service is running
docker compose ps <service-name>
# Should show: "running" or "healthy"

# Check service startup order
docker compose ps --format "table {{.Name}}\t{{.Status}}"
# Dependencies should start before dependents

# Test connection from within network
docker compose exec api curl http://db:5432
docker compose exec api curl http://cache:6379

# Check DNS resolution
docker compose exec api nslookup db
docker compose exec api nslookup cache
```

**Root Cause**: 
1. **Service startup order** - Dependencies not ready
2. **Network issues** - Services not on same network
3. **Service not running** - Container crashed or exited

**Solution**:

**Fix 1: Startup Order**
```yaml
# In compose.yaml, ensure depends_on with healthcheck:
api:
  depends_on:
    db:
      condition: service_healthy
    cache:
      condition: service_healthy
```

**Fix 2: Wait for Dependencies**
```bash
# Manually wait for dependencies
docker compose up -d db cache object search
# Wait for health checks
sleep 60
docker compose ps  # Verify all healthy
docker compose up -d api worker  # Then start app services
```

**Fix 3: Restart Failed Service**
```bash
# Check logs
docker compose logs <service-name> --tail=50

# Restart service
docker compose restart <service-name>

# Or recreate
docker compose up -d --force-recreate <service-name>
```

**Verification**:
```bash
# Check all services healthy
docker compose ps
# All should be "running" or "healthy"

# Test connectivity
docker compose exec api curl http://localhost:8000/health
# Should return: {"status":"ok"}
```

---

### Issue 4: Port Already in Use

**Symptoms**:
- "Bind for 0.0.0.0:8000 failed: port is already allocated"
- "Address already in use"
- Service won't start

**Diagnosis**:
```bash
# Windows PowerShell
netstat -ano | findstr "8000"
# Note the PID

# Linux/Mac
lsof -i :8000
# Or
netstat -tulpn | grep 8000

# Identify process
# Windows:
tasklist | findstr "<PID>"

# Linux/Mac:
ps aux | grep <PID>
```

**Solution**:

**Option 1: Stop Conflicting Process**
```powershell
# Windows - Find and stop process
Get-NetTCPConnection -LocalPort 8000
$process = Get-Process -Id <PID>
Stop-Process -Id <PID> -Force

# Or kill by port
netstat -ano | findstr "8000"
taskkill /PID <PID> /F
```

**Option 2: Change APEX Port**
```yaml
# In compose.yaml, change port mapping:
api:
  ports:
    - "8001:8000"  # Use 8001 instead of 8000
```

**Option 3: Stop Conflicting Service**
```powershell
# Stop IIS (if using port 80/8000)
iisreset /stop

# Stop SQL Server (if using port 1433)
Stop-Service -Name "MSSQLSERVER"
```

**Verification**:
```bash
# Check port is free
netstat -ano | findstr "8000"
# Should return nothing

# Start services
docker compose up -d
```

---

### Issue 5: Database Connection Failed

**Symptoms**:
- "Connection refused"
- "FATAL: password authentication failed"
- "FATAL: database does not exist"
- API shows database check failed

**Diagnosis**:
```bash
# Check database is running
docker compose ps db
# Should show: "healthy"

# Test database connection
docker compose exec db pg_isready -U apex
# Expected: "accepting connections"

# Test connection from API container
docker compose exec api python -c "
import os
import psycopg2
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
print('Connected')
"

# Check connection string
docker compose exec api env | grep DATABASE_URL
```

**Solutions**:

1. **Database Not Running**
   ```bash
   docker compose up -d db
   # Wait for health check
   sleep 30
   docker compose ps db
   ```

2. **Wrong Credentials**
   ```bash
   # Check credentials in compose.yaml
   # Verify DATABASE_URL matches
   docker compose exec api env | grep DATABASE_URL
   ```

3. **Database Not Ready**
   ```bash
   # Wait for database initialization
   docker compose logs db | grep "database system is ready"
   ```

**Verification**:
```bash
curl http://localhost:8000/ready | jq '.checks.database'
# Expected: "ok"
```

---

### Issue 4: High Error Rate

**Symptoms**:
- API returns 5xx errors
- Error rate >5%
- Logs show repeated errors

**Diagnosis**:
```bash
# Count errors in last 5 minutes
docker compose logs --since 5m api | grep -i error | wc -l

# Categorize errors
docker compose logs --since 5m api | grep -i error | sort | uniq -c | sort -rn

# Check metrics (if Prometheus available)
curl http://localhost:9090/api/v1/query?query=rate\(http_requests_total{status=~\"5..\"}\[5m\]\)
```

**Solutions**:

1. **Database Connection Pool Exhausted**
   ```bash
   # Check connection pool usage
   docker compose exec db psql -U apex -d apex -c "
   SELECT count(*) FROM pg_stat_activity WHERE datname='apex';
   "
   # If >80% of max_connections, restart or scale
   ```

2. **Out of Memory**
   ```bash
   # Check memory usage
   docker stats --no-stream
   # Restart service if memory >95%
   docker compose restart <service-name>
   ```

3. **Dependency Failure**
   ```bash
   # Check all dependencies
   curl http://localhost:8000/ready | jq '.checks'
   # Restart failed dependency
   docker compose restart <dependency-service>
   ```

**Verification**:
```bash
# Monitor error rate
docker compose logs -f api | grep ERROR
# Should decrease after fix
```

---

### Issue 5: Slow Performance

**Symptoms**:
- API response times >500ms
- Requests timing out
- High CPU usage

**Diagnosis**:
```bash
# Check API latency
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# Check database query performance
docker compose exec db psql -U apex -d apex -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"

# Check resource usage
docker stats --no-stream

# Check cache hit rate
docker compose exec cache redis-cli INFO stats | grep hit_rate
```

**Solutions**:

1. **Slow Database Queries**
   ```bash
   # Identify slow queries
   docker compose exec db psql -U apex -d apex -c "
   SELECT * FROM pg_stat_statements 
   WHERE mean_exec_time > 100
   ORDER BY mean_exec_time DESC;
   "
   # Add indexes or optimize queries
   ```

2. **Low Cache Hit Rate**
   ```bash
   # Check cache configuration
   docker compose exec cache redis-cli INFO stats
   # Improve cache strategy or increase TTL
   ```

3. **Resource Constraints**
   ```bash
   # Check resource limits
   docker compose config | grep -A 5 "resources:"
   # Increase limits if needed
   ```

**Verification**:
```bash
# Monitor latency
curl -w "Time: %{time_total}s\n" http://localhost:8000/health
# Should be <200ms
```

---

### Issue 6: Report Generation Fails

**Symptoms**:
- Report task stuck in "processing"
- Report task fails
- No PDF generated

**Diagnosis**:
```bash
# Check worker logs
docker compose logs worker --tail=100 | grep report

# Check Celery queue
docker compose exec cache redis-cli LLEN celery

# Check task status
curl http://localhost:8000/api/v1/tasks/{task_id}

# Check WeasyPrint dependencies
docker compose exec signcalc python -c "import weasyprint; print('OK')"
```

**Solutions**:

1. **Worker Not Running**
   ```bash
   docker compose ps worker
   docker compose up -d worker
   ```

2. **Redis Connection Failed**
   ```bash
   docker compose exec worker python -c "
   import redis
   r = redis.from_url('redis://cache:6379/0')
   print(r.ping())
   "
   ```

3. **WeasyPrint Dependencies Missing**
   ```bash
   # Check signcalc Dockerfile includes WeasyPrint deps
   # Rebuild if needed
   docker compose build signcalc
   ```

**Verification**:
```bash
# Generate test report
curl -X POST http://localhost:8000/api/v1/projects/{id}/report
# Should return task_id
# Poll task until completed
```

---

### Issue 7: File Upload Fails

**Symptoms**:
- Upload returns 403 Forbidden
- "Presigned URL expired"
- CORS errors in browser

**Diagnosis**:
```bash
# Check MinIO health
curl http://localhost:9000/minio/health/live

# Check MinIO access
docker compose exec object mc admin info local

# Test presigned URL generation
curl -X POST http://localhost:8000/api/v1/files/presign \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.pdf"}'

# Check CORS configuration
curl -X OPTIONS http://localhost:9000 \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: PUT"
```

**Solutions**:

1. **Presigned URL Expired**
   ```bash
   # Get new URL (URLs expire after 1 hour)
   curl -X POST http://localhost:8000/api/v1/files/presign \
     -d '{"filename": "test.pdf"}'
   ```

2. **MinIO Not Accessible**
   ```bash
   docker compose ps object
   docker compose restart object
   ```

3. **CORS Misconfiguration**
   ```bash
   # Check MinIO CORS settings
   # Update CORS policy if needed
   ```

**Verification**:
```bash
# Test file upload
# Should complete successfully
```

---

### Issue 8: Migration Fails

**Symptoms**:
- Alembic migration errors
- Schema inconsistency
- Migration timeout

**Diagnosis**:
```bash
# Check migration status
docker compose exec api alembic current

# Check migration history
docker compose exec api alembic history

# Check database schema
docker compose exec db psql -U apex -d apex -c "\dt"

# Check for migration locks
docker compose exec db psql -U apex -d apex -c "
SELECT * FROM alembic_version;
"
```

**Solutions**:

1. **Migration Locked**
   ```bash
   # Check for running migrations
   docker compose exec db psql -U apex -d apex -c "
   SELECT * FROM pg_locks WHERE locktype = 'advisory';
   "
   # Kill blocking process if needed
   ```

2. **Schema Conflict**
   ```bash
   # Review migration file
   # Check for conflicts
   # Manually resolve if needed
   ```

3. **Database Connection Issue**
   ```bash
   # Verify database accessible
   docker compose exec api alembic check
   ```

**Verification**:
```bash
# Run migration
docker compose exec api alembic upgrade head
# Should complete without errors
```

---

## Advanced Troubleshooting

### Performance Debugging

```bash
# Profile API requests
docker compose exec api python -m cProfile -s cumulative -o profile.stats script.py

# Database query analysis
docker compose exec db psql -U apex -d apex -c "EXPLAIN ANALYZE <query>"

# Memory profiling
docker compose exec api python -m memory_profiler script.py
```

### Network Debugging

```bash
# Test service-to-service communication
docker compose exec api curl http://db:5432
docker compose exec api curl http://cache:6379
docker compose exec api curl http://object:9000

# Check DNS resolution
docker compose exec api nslookup db
docker compose exec api nslookup cache
```

### Log Analysis

```bash
# Search logs for patterns
docker compose logs | grep -i "error\|warning\|fatal"

# Export logs for analysis
docker compose logs > deployment_logs.txt

# Filter by time
docker compose logs --since 1h
docker compose logs --until 30m
```

---

## Escalation

### When to Escalate

- Issue persists after trying all solutions
- Data corruption suspected
- Security issue detected
- System-wide outage

### How to Escalate

1. Document issue (symptoms, steps taken, logs)
2. Contact on-call engineer
3. Provide diagnostic information
4. Follow incident response procedures

---

**Last Updated**: 2025-01-27  
**Review Frequency**: Update as new issues discovered

