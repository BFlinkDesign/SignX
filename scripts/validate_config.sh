#!/bin/bash
# Configuration Validation Script
# Validates all configuration files before deployment

set -e

echo "=== Configuration Validation ==="
echo ""

ERRORS=0
WARNINGS=0

# Check compose.yaml syntax
echo "1. Validating compose.yaml syntax..."
cd infra
if docker compose config > /dev/null 2>&1; then
    echo "   ✅ compose.yaml syntax valid"
else
    echo "   ❌ compose.yaml syntax invalid"
    docker compose config
    ERRORS=$((ERRORS + 1))
fi

# Check tmpfs ownership fix
echo ""
echo "2. Checking tmpfs ownership fix..."
if grep -q "uid=1000,gid=1000,mode=1777" compose.yaml; then
    echo "   ✅ tmpfs ownership fixed"
else
    echo "   ❌ tmpfs ownership NOT fixed (Critical)"
    echo "   Fix required: Add uid=1000,gid=1000,mode=1777 to tmpfs mounts"
    ERRORS=$((ERRORS + 1))
fi

# Check Dockerfile ownership fix
echo ""
echo "3. Checking Dockerfile ownership fix..."
cd ../services/api
if grep -q "COPY --chown" Dockerfile; then
    echo "   ✅ API Dockerfile ownership fixed"
else
    echo "   ❌ API Dockerfile ownership NOT fixed (Critical)"
    ERRORS=$((ERRORS + 1))
fi

cd ../worker
if grep -q "COPY --chown" Dockerfile; then
    echo "   ✅ Worker Dockerfile ownership fixed"
else
    echo "   ❌ Worker Dockerfile ownership NOT fixed (Critical)"
    ERRORS=$((ERRORS + 1))
fi

# Check required files exist
echo ""
echo "4. Checking required files..."
cd ../../

FILES=(
    "services/api/Dockerfile"
    "services/worker/Dockerfile"
    "services/api/monitoring/postgres_exporter.yml"
    "services/api/monitoring/grafana_dashboard.json"
    "infra/compose.yaml"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file exists"
    else
        echo "   ❌ $file MISSING"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check backups directory
echo ""
echo "5. Checking backups directory..."
if [ -d "infra/backups" ]; then
    echo "   ✅ backups directory exists"
else
    echo "   ⚠️  backups directory missing (recommended)"
    WARNINGS=$((WARNINGS + 1))
fi

# Check environment variables
echo ""
echo "6. Checking critical environment variables..."
cd infra
ENV_VARS=$(docker compose config 2>/dev/null | grep -E "DATABASE_URL|REDIS_URL|MINIO_URL" | wc -l)
if [ "$ENV_VARS" -ge 3 ]; then
    echo "   ✅ Critical environment variables configured"
else
    echo "   ⚠️  Some environment variables may be missing"
    WARNINGS=$((WARNINGS + 1))
fi

# Summary
echo ""
echo "=== Validation Summary ==="
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"

if [ $ERRORS -eq 0 ]; then
    echo ""
    echo "✅ Configuration validation PASSED"
    exit 0
else
    echo ""
    echo "❌ Configuration validation FAILED"
    echo "Fix errors before deploying"
    exit 1
fi

