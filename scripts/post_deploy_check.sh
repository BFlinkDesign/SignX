#!/bin/bash
# Post-Deployment Validation Script
# Validates all services after deployment

set -e

echo "=== Post-Deployment Validation ==="
echo ""

FAILED=0

# Check all services running
echo "1. Checking service status..."
cd infra
SERVICES=$(docker compose ps --format json | jq -r '.[] | select(.State != "running" and .State != "healthy") | .Name' 2>/dev/null || echo "")

if [ -z "$SERVICES" ]; then
    echo "   ✅ All services running/healthy"
else
    echo "   ❌ Some services not healthy:"
    echo "$SERVICES"
    FAILED=$((FAILED + 1))
fi

# Health endpoint checks
echo ""
echo "2. Checking health endpoints..."

# API health
if curl -fsS http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ API health check passed"
else
    echo "   ❌ API health check failed"
    FAILED=$((FAILED + 1))
fi

# API readiness
if curl -fsS http://localhost:8000/ready > /dev/null 2>&1; then
    RESPONSE=$(curl -s http://localhost:8000/ready)
    if echo "$RESPONSE" | jq -e '.checks.database == "ok"' > /dev/null 2>&1; then
        echo "   ✅ API readiness check passed (database OK)"
    else
        echo "   ⚠️  API readiness check: dependencies may have issues"
    fi
else
    echo "   ❌ API readiness check failed"
    FAILED=$((FAILED + 1))
fi

# Signcalc health
if curl -fsS http://localhost:8002/healthz > /dev/null 2>&1; then
    echo "   ✅ Signcalc health check passed"
else
    echo "   ❌ Signcalc health check failed"
    FAILED=$((FAILED + 1))
fi

# Database connectivity
echo ""
echo "3. Checking database connectivity..."
if docker compose exec -T db pg_isready -U apex > /dev/null 2>&1; then
    echo "   ✅ Database accepting connections"
    
    # Check tables exist
    TABLE_COUNT=$(docker compose exec -T db psql -U apex -d apex -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ')
    if [ "$TABLE_COUNT" -gt 0 ]; then
        echo "   ✅ Database tables exist ($TABLE_COUNT tables)"
    else
        echo "   ⚠️  No tables found (migrations may not have run)"
    fi
else
    echo "   ❌ Database not accepting connections"
    FAILED=$((FAILED + 1))
fi

# Redis connectivity
echo ""
echo "4. Checking Redis connectivity..."
if docker compose exec -T cache redis-cli ping > /dev/null 2>&1; then
    echo "   ✅ Redis responding"
else
    echo "   ❌ Redis not responding"
    FAILED=$((FAILED + 1))
fi

# MinIO connectivity
echo ""
echo "5. Checking MinIO connectivity..."
if curl -fsS http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo "   ✅ MinIO health check passed"
else
    echo "   ❌ MinIO health check failed"
    FAILED=$((FAILED + 1))
fi

# OpenSearch connectivity
echo ""
echo "6. Checking OpenSearch connectivity..."
if curl -fsS "http://localhost:9200/_cluster/health?wait_for_status=yellow&timeout=1s" > /dev/null 2>&1; then
    echo "   ✅ OpenSearch health check passed"
else
    echo "   ❌ OpenSearch health check failed"
    FAILED=$((FAILED + 1))
fi

# Grafana connectivity
echo ""
echo "7. Checking Grafana connectivity..."
if curl -fsS http://localhost:3001/api/health > /dev/null 2>&1; then
    echo "   ✅ Grafana health check passed"
else
    echo "   ⚠️  Grafana health check failed (non-critical)"
fi

# Test API endpoint
echo ""
echo "8. Testing API functionality..."
if curl -fsS http://localhost:8000/api/v1/projects > /dev/null 2>&1; then
    echo "   ✅ API endpoint responding"
else
    echo "   ❌ API endpoint not responding"
    FAILED=$((FAILED + 1))
fi

# Check for errors in logs
echo ""
echo "9. Checking for critical errors in logs..."
ERROR_COUNT=$(docker compose logs --tail=100 2>&1 | grep -i "error\|fatal\|critical" | wc -l || echo "0")
if [ "$ERROR_COUNT" -lt 10 ]; then
    echo "   ✅ Minimal errors in logs ($ERROR_COUNT found)"
else
    echo "   ⚠️  High error count in logs ($ERROR_COUNT found)"
    echo "   Review logs: docker compose logs --tail=100"
fi

# Summary
echo ""
echo "=== Post-Deployment Validation Summary ==="
if [ $FAILED -eq 0 ]; then
    echo "✅ All checks passed"
    echo ""
    echo "Deployment successful! Proceed to monitoring phase."
    exit 0
else
    echo "❌ $FAILED check(s) failed"
    echo ""
    echo "Review failures above and fix before proceeding"
    exit 1
fi

