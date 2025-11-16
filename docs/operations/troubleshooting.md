# Troubleshooting Guide

Common issues and solutions for SIGN X Studio Clone.

## Quick Diagnostics

### Check Service Status

```bash
# Docker Compose
docker compose ps

# Kubernetes
kubectl get pods -n apex

# Health endpoints
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

### Check Logs

```bash
# API logs
docker compose logs api

# Worker logs
docker compose logs worker

# All services
docker compose logs

# Follow logs
docker compose logs -f api
```

## Envelope-Specific Issues

### Issue: "Derive failed" or Low Confidence

**Symptoms:**
- Canvas derive returns low confidence (<0.7)
- Warnings in assumptions array
- Form inputs not updated

**Diagnosis:**
```bash
# Check assumptions in response
curl -X POST http://localhost:8000/signage/common/cabinets/derive \
  -H "Content-Type: application/json" \
  -d '{"overall_height_ft": 25.0, "cabinets": [...]}' | \
  jq '.assumptions, .confidence'
```

**Solutions:**
1. **Review Warnings**
   - Check `assumptions` array for specific warnings
   - Common: "Pole height >40ft is uncommon"
   - Action: Adjust inputs or proceed with caution

2. **Input Validation**
   - Verify input ranges (height: 10-50ft, width: 5-30ft)
   - Check numeric values are valid (not NaN, not negative)
   - Action: Fix invalid inputs

3. **Review Solver Logs**
   ```bash
   docker compose logs api | grep derive | tail -20
   ```

### Issue: "Report not generating"

**Symptoms:**
- POST /projects/{id}/report returns task_id
- Task stuck in "processing" status
- No PDF generated

**Diagnosis:**
```bash
# Check Celery worker status
docker compose logs worker | grep report

# Check Redis queue
docker compose exec cache redis-cli LLEN celery

# Check task status
curl http://localhost:8000/tasks/{task_id}
```

**Solutions:**
1. **Check Celery Workers**
   ```bash
   docker compose ps worker
   docker compose logs worker --tail=50
   ```

2. **Check Redis Connection**
   ```bash
   docker compose exec cache redis-cli PING
   ```

3. **Check Worker Queue Depth**
   ```bash
   docker compose exec cache redis-cli LLEN celery
   # If >100: Scale workers
   docker compose up -d --scale worker=3
   ```

4. **Retry Task**
   ```bash
   # Manually retry
   curl -X POST http://localhost:8000/tasks/{task_id}/retry
   ```

### Issue: "Upload stuck" or Presigned URL Expired

**Symptoms:**
- File upload fails with 403 or 403 Forbidden
- Presigned URL returns expired error

**Diagnosis:**
```bash
# Check presigned URL expiry
curl -v "$PRESIGNED_URL" 2>&1 | grep -i expired

# Check MinIO status
curl http://localhost:9000/minio/health/live

# Verify CORS configuration
curl -X OPTIONS http://localhost:9000 \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: PUT"
```

**Solutions:**
1. **Get New Presigned URL**
   ```bash
   # Request new URL (presigned URLs expire after 1 hour)
   curl -X POST http://localhost:8000/files/presign \
     -H "Content-Type: application/json" \
     -d '{"filename": "file.pdf"}'
   ```

2. **Check CORS Configuration**
   ```yaml
   # MinIO CORS config
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: minio-cors
   data:
     cors.json: |
       {
         "CORSRules": [{
           "AllowedOrigins": ["http://localhost:5173", "https://app.example.com"],
           "AllowedMethods": ["GET", "PUT", "POST"],
           "AllowedHeaders": ["*"],
           "ExposeHeaders": ["ETag"],
           "MaxAgeSeconds": 3000
         }]
       }
   ```

3. **Verify MinIO Access**
   ```bash
   docker compose exec minio mc admin info local
   ```

### Issue: "Confidence score low" or Engineering Review Required

**Symptoms:**
- Confidence <0.5 in responses
- "Engineering review required" in assumptions
- Yellow/red confidence badge displayed

**Diagnosis:**
```bash
# Check confidence in response
curl http://localhost:8000/projects/proj_123 | jq '.confidence, .assumptions'
```

**Solutions:**
1. **Review Assumptions**
   - Check `assumptions` array for warnings
   - Common causes:
     - Unusual configuration (tiny cabinet + massive pole)
     - Depth >5ft requires review
     - No feasible poles found
   
2. **Adjust Design**
   - Modify inputs to address warnings
   - Re-run calculation
   - Confidence should improve

3. **Request Engineering Review**
   ```bash
   curl -X POST http://localhost:8000/signage/baseplate/request-engineering \
     -H "Content-Type: application/json" \
     -d '{"project_id": "proj_123", "reason": "High utilization ratios"}'
   ```

### Issue: "Idempotency key conflict"

**Symptoms:**
- Submission fails with "Idempotency-Key already used"
- Redis cache collision

**Diagnosis:**
```bash
# Check Redis cache
docker compose exec cache redis-cli GET "idem:submit-123:/projects/proj_123/submit"

# Check TTL
docker compose exec cache redis-cli TTL "idem:submit-123:/projects/proj_123/submit"
```

**Solutions:**
1. **Use Unique Key**
   ```typescript
   // Generate unique UUID
   const idempotencyKey = crypto.randomUUID();
   ```

2. **Clear Stale Keys** (if >24 hours old)
   ```bash
   # Keys automatically expire after 24 hours
   # Manually clear if needed
   docker compose exec cache redis-cli DEL "idem:submit-123:/projects/proj_123/submit"
   ```

3. **Re-use Key for Retry**
   ```typescript
   // Store in localStorage
   const storedKey = localStorage.getItem(`idem:${projectId}`);
   if (storedKey) {
     // Re-use for retry
     headers['Idempotency-Key'] = storedKey;
   }
   ```

## Common Issues

### Issue 1: Service Won't Start

**Symptoms:**
- Container exits immediately
- Status shows "restarting"

**Diagnosis:**
```bash
# Check logs
docker compose logs api

# Check environment
docker compose exec api env | grep APEX_

# Check health
docker compose exec api curl http://localhost:8000/health
```

**Solutions:**

1. **Missing Environment Variables**
   ```bash
   # Verify .env file exists
   ls -la .env
   
   # Check required variables
   grep APEX_DATABASE_URL .env
   ```

2. **Database Connection Failed**
   ```bash
   # Check database is running
   docker compose ps db
   
   # Test connection
   docker compose exec db psql -U apex -d apex -c "SELECT 1;"
   ```

3. **Port Already in Use**
   ```bash
   # Find process
   lsof -i :8000  # macOS/Linux
   netstat -ano | findstr :8000  # Windows
   
   # Kill process or change port
   ```

### Issue 2: Database Connection Errors

**Symptoms:**
- `Connection refused` errors
- `Timeout` errors
- `Authentication failed`

**Diagnosis:**
```bash
# Check database URL
echo $APEX_DATABASE_URL

# Test connection
psql $APEX_DATABASE_URL -c "SELECT 1;"
```

**Solutions:**

1. **Wrong Database URL**
   ```bash
   # Format: postgresql://user:pass@host:port/db
   export APEX_DATABASE_URL=postgresql://apex:apex@localhost:5432/apex
   ```

2. **Database Not Running**
   ```bash
   # Start database
   docker compose up -d db
   
   # Wait for health
   docker compose ps db
   ```

3. **Wrong Credentials**
   ```bash
   # Check .env file
   grep DATABASE_URL .env
   
   # Update if needed
   ```

### Issue 3: Migration Errors

**Symptoms:**
- `alembic: command not found`
- `Target database is not up to date`
- Migration conflicts

**Diagnosis:**
```bash
# Check current revision
alembic current

# Check migration history
alembic history

# Check database state
psql $APEX_DATABASE_URL -c "\dt"
```

**Solutions:**

1. **Install Alembic**
   ```bash
   pip install alembic
   ```

2. **Reset Migrations (Development Only)**
   ```bash
   # Rollback all
   alembic downgrade base
   
   # Re-apply
   alembic upgrade head
   ```

3. **Manual Migration Fix**
   ```bash
   # Edit migration file if needed
   # Then re-run
   alembic upgrade head
   ```

### Issue 4: Rate Limiting

**Symptoms:**
- `429 Too Many Requests`
- `Rate limit exceeded`

**Diagnosis:**
```bash
# Check rate limit settings
docker compose exec api env | grep RATE_LIMIT

# Check response headers
curl -v http://localhost:8000/projects 2>&1 | grep Retry-After
```

**Solutions:**

1. **Increase Rate Limit**
   ```bash
   # In .env
   APEX_RATE_LIMIT_PER_MIN=120
   
   # Restart service
   docker compose restart api
   ```

2. **Wait and Retry**
   ```bash
   # Check Retry-After header
   # Wait specified seconds
   sleep 60
   ```

3. **Use API Key**
   ```bash
   # API keys may have higher limits
   curl -H "X-Apex-Key: your-key" http://localhost:8000/projects
   ```

### Issue 5: File Upload Failures

**Symptoms:**
- `422 SHA256 mismatch`
- `403 Access denied`
- Presign URL expired

**Diagnosis:**
```bash
# Check MinIO
docker compose ps object

# Test MinIO connection
curl http://localhost:9000/minio/health/live

# Check credentials
docker compose exec api env | grep MINIO
```

**Solutions:**

1. **SHA256 Mismatch**
   ```bash
   # Re-calculate SHA256
   sha256sum file.pdf
   
   # Verify file wasn't corrupted
   ```

2. **MinIO Not Running**
   ```bash
   # Start MinIO
   docker compose up -d object
   
   # Check console
   open http://localhost:9001
   ```

3. **Expired Presign URL**
   ```bash
   # Get new presign URL
   # Upload immediately
   ```

### Issue 6: Search Failures

**Symptoms:**
- `search_fallback: true` in responses
- Slow search queries
- No search results

**Diagnosis:**
```bash
# Check OpenSearch
docker compose ps search

# Test OpenSearch
curl http://localhost:9200

# Check fallback rate
curl http://localhost:8000/metrics | grep search_fallback
```

**Solutions:**

1. **OpenSearch Not Running**
   ```bash
   # Start OpenSearch
   docker compose up -d search
   
   # Wait for health (may take 30+ seconds)
   docker compose logs search
   ```

2. **High Fallback Rate**
   ```bash
   # Check OpenSearch logs
   docker compose logs search
   
   # Re-index projects (if needed)
   # System auto-indexes on create/update
   ```

3. **Search Timeout**
   ```bash
   # Increase timeout in search.py
   # Default: 5 seconds
   ```

### Issue 7: Celery Tasks Not Processing

**Symptoms:**
- Tasks stuck in queue
- No worker logs
- Task failures

**Diagnosis:**
```bash
# Check worker status
docker compose ps worker

# Check queue depth
docker compose exec cache redis-cli LLEN celery

# Check worker logs
docker compose logs worker
```

**Solutions:**

1. **Worker Not Running**
   ```bash
   # Start worker
   docker compose up -d worker
   
   # Check logs
   docker compose logs -f worker
   ```

2. **Redis Connection Failed**
   ```bash
   # Check Redis URL
   docker compose exec worker env | grep REDIS
   
   # Test Redis
   docker compose exec cache redis-cli ping
   ```

3. **Task Failures**
   ```bash
   # Check task logs
   docker compose logs worker | grep ERROR
   
   # Check task status (if Flower enabled)
   open http://localhost:5555
   ```

## Performance Issues

### High Latency

**Diagnosis:**
```bash
# Check request duration
curl -w "@curl-format.txt" http://localhost:8000/projects

# Check metrics
curl http://localhost:8000/metrics | grep duration
```

**Solutions:**
1. Check database query performance
2. Verify cache is working
3. Check external API response times
4. Scale services horizontally

### High Memory Usage

**Diagnosis:**
```bash
# Check memory
docker stats

# Kubernetes
kubectl top pods -n apex
```

**Solutions:**
1. Increase memory limits
2. Check for memory leaks
3. Reduce connection pool size
4. Restart services

### Database Connection Pool Exhausted

**Diagnosis:**
```bash
# Check metrics
curl http://localhost:8000/metrics | grep pg_pool
```

**Solutions:**
1. Increase pool size
2. Reduce connection timeout
3. Check for connection leaks
4. Restart API service

## Debugging Techniques

### Enable Debug Logging

```bash
# Set log level
export APEX_LOG_LEVEL=DEBUG

# Restart service
docker compose restart api
```

### Database Query Debugging

```bash
# Enable SQL logging
# In db.py, set echo=True
_engine = create_async_engine(..., echo=True)
```

### Request Tracing

```bash
# Check trace IDs
curl -v http://localhost:8000/projects 2>&1 | grep trace

# Check error IDs
curl -v http://localhost:8000/projects/invalid 2>&1 | grep error
```

## Getting Help

### Collect Diagnostic Information

```bash
# Service status
docker compose ps > diagnostics.txt

# Environment variables
docker compose exec api env | grep APEX_ >> diagnostics.txt

# Logs (last 100 lines)
docker compose logs --tail=100 >> diagnostics.txt

# Health checks
curl http://localhost:8000/health >> diagnostics.txt
curl http://localhost:8000/ready >> diagnostics.txt
```

### Support Resources

- **Documentation**: See other guides in `docs/`
- **Logs**: Check service logs
- **Metrics**: Check `/metrics` endpoint
- **GitHub Issues**: Open issue with diagnostics

## Next Steps

- [**Monitoring Guide**](monitoring.md) - Monitor system health
- [**Runbooks**](runbooks.md) - Operational procedures

