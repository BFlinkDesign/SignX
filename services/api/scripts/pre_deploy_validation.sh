#!/bin/bash
# Pre-deployment validation: Run before production deployments

set -e

echo "=== APEX Pre-Deployment Validation ==="
echo "Starting at $(date)"

ERRORS=0

# Check 1: Latest backup recent
echo "1. Checking latest backup..."
LATEST_BACKUP=$(find /backups -name "apex_full_*.dump" -mtime -1 | head -1)
if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ No backup in last 24 hours"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ Latest backup: $(basename $LATEST_BACKUP)"
fi

# Check 2: All migrations applied
echo "2. Checking migrations..."
cd services/api
CURRENT=$(alembic current | grep "Rev:" | awk '{print $2}')
HEAD=$(alembic heads | grep "Rev:" | awk '{print $2}')
if [ "$CURRENT" != "$HEAD" ]; then
    echo "❌ Migrations not at head: current=$CURRENT, head=$HEAD"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ Migrations at head: $HEAD"
fi

# Check 3: Indexes exist
echo "3. Checking indexes..."
INDEX_COUNT=$(psql -U apex apex -t -c "
    SELECT COUNT(*) FROM pg_indexes 
    WHERE schemaname = 'public' 
      AND tablename IN ('projects', 'project_payloads', 'project_events')
")
if [ "$INDEX_COUNT" -lt 10 ]; then
    echo "❌ Too few indexes: $INDEX_COUNT"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ Indexes found: $INDEX_COUNT"
fi

# Check 4: Constraints valid
echo "4. Checking constraints..."
VIOLATIONS=$(psql -U apex apex -t -f scripts/check_referential_integrity.sql | grep "FAIL" || true)
if [ -n "$VIOLATIONS" ]; then
    echo "❌ Constraint violations detected"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ Constraints valid"
fi

# Check 5: Monitoring accessible
echo "5. Checking monitoring..."
if ! curl -fsS http://localhost:9187/metrics > /dev/null 2>&1; then
    echo "❌ Prometheus exporter not responding"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ Monitoring accessible"
fi

# Check 6: Dashboards responding
if ! curl -fsS http://localhost:3001/api/health > /dev/null 2>&1; then
    echo "❌ Grafana not responding"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ Dashboards responding"
fi

# Summary
echo ""
if [ $ERRORS -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED - Ready for deployment"
    exit 0
else
    echo "❌ $ERRORS checks failed - DO NOT DEPLOY"
    exit 1
fi

