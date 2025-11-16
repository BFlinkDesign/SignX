# APEX Database Deployment Procedure

## Pre-Deployment Checklist

- [ ] All migrations tested in staging
- [ ] Backup recent (<24hrs)
- [ ] Monitoring dashboards accessible
- [ ] Alerts configured
- [ ] Rollback plan ready

## Deployment Steps

### 1. Backup Current State

```bash
./services/api/backups/dump.sh
ls -lh /backups/apex_full_*.dump | head -1
```

### 2. Maintenance Window

```bash
# Notify stakeholders
# Stop non-critical services (optional)
# Set maintenance mode in API
```

### 3. Apply Migrations

```bash
cd services/api
alembic upgrade head
alembic current
```

### 4. Validate Schema

```bash
# Check indexes
psql -U apex apex -c "\d+ projects"

# Check constraints
psql -U apex apex -c "SELECT conname, contype FROM pg_constraint WHERE conrelid = 'projects'::regclass;"

# Check foreign keys
psql -U apex apex -f scripts/check_referential_integrity.sql
```

### 5. Smoke Tests

```bash
# Create test project
curl -X POST http://localhost:8000/projects -H "Content-Type: application/json" -d '{"name":"Deploy Test","account_id":"acc_001","created_by":"deployer"}'

# Query it back
curl http://localhost:8000/projects/proj_test_001

# Verify envelope fields
curl http://localhost:8000/projects/proj_test_001 | jq '.result.confidence'
```

### 6. Performance Verification

```bash
# Run benchmark queries
psql -U apex apex <<EOF
\timing on
SELECT COUNT(*) FROM projects WHERE status = 'draft';
SELECT * FROM project_stats WHERE account_id = 'acc_test';
EOF

# Verify index usage
psql -U apex apex -c "EXPLAIN ANALYZE SELECT * FROM projects WHERE status = 'estimating' ORDER BY created_at DESC LIMIT 100"
```

### 7. End Maintenance Window

```bash
# Resume normal traffic
# Monitor dashboards for 30 minutes
# Verify no alerts firing
```

## Rollback Procedure

If issues detected within 30 minutes:

```bash
# Stop services
docker compose -f infra/compose.yaml stop api worker

# Restore backup
pg_restore -h localhost -U apex -d apex --clean --if-exists /backups/apex_full_YYYYMMDD.dump

# Restart services
docker compose -f infra/compose.yaml start api worker

# Notify stakeholders
```

## Post-Deployment Validation

**First 1 hour:**
- Monitor slow queries
- Check error rates
- Verify envelope fields populated
- Confirm index hit rate >95%

**First 24 hours:**
- Run integrity checks
- Verify backup successful
- Check cache hit rate >99%
- Review monitoring dashboards

## Success Criteria

✅ All migrations applied  
✅ No integrity violations  
✅ Query performance <50ms  
✅ Index hit rate >95%  
✅ Zero rollback required  
✅ Monitoring operational

