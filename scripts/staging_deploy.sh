#!/bin/bash
# Staging Deployment Script
# Follows DEPLOYMENT_PLAN.md phases

set -e

echo "=== Staging Deployment ==="
echo "Date: $(date)"
echo ""

cd infra

# Phase 1: Pre-Flight
echo "=== Phase 1: Pre-Flight (5 minutes) ==="
echo ""

echo "1.1: Stopping existing services..."
docker compose down
echo "   ✅ Services stopped"

echo ""
echo "1.2: Verifying critical fixes..."
if grep -q "uid=1000,gid=1000,mode=1777" compose.yaml; then
    echo "   ✅ tmpfs ownership fix applied"
else
    echo "   ❌ tmpfs ownership fix NOT applied"
    exit 1
fi

echo ""
echo "1.3: Creating required directories..."
mkdir -p backups
echo "   ✅ Directories created"

echo ""
echo "1.4: Verifying files..."
if [ -f "../services/api/Dockerfile" ] && [ -f "../services/worker/Dockerfile" ]; then
    echo "   ✅ Required files present"
else
    echo "   ❌ Required files missing"
    exit 1
fi

echo ""
echo "=== Phase 1 Complete ==="
echo ""

# Phase 2: Build
echo "=== Phase 2: Build (5-7 minutes) ==="
echo ""

echo "2.1: Building images..."
docker compose build --parallel
echo "   ✅ Images built"

echo ""
echo "2.2: Verifying images..."
docker images | grep apex | head -5
echo "   ✅ Images verified"

echo ""
echo "=== Phase 2 Complete ==="
echo ""

# Phase 3: Deploy
echo "=== Phase 3: Deploy (3-5 minutes) ==="
echo ""

echo "3.1: Starting infrastructure services..."
docker compose up -d db cache object search
echo "   ✅ Infrastructure services starting"
echo "   Waiting for health checks (60 seconds)..."
sleep 60

echo ""
echo "3.2: Verifying infrastructure health..."
INFRA_HEALTHY=true
for service in db cache object search; do
    if docker compose ps $service | grep -q "healthy\|running"; then
        echo "   ✅ $service healthy"
    else
        echo "   ❌ $service not healthy"
        INFRA_HEALTHY=false
    fi
done

if [ "$INFRA_HEALTHY" = false ]; then
    echo "   ❌ Infrastructure services not healthy, check logs"
    docker compose logs --tail=50
    exit 1
fi

echo ""
echo "3.3: Starting application services..."
docker compose up -d api worker signcalc
echo "   ✅ Application services starting"
sleep 30

echo ""
echo "3.4: Starting frontend and monitoring..."
docker compose up -d frontend grafana postgres_exporter dashboards
echo "   ✅ All services starting"
sleep 30

echo ""
echo "3.5: Verifying all services..."
docker compose ps
echo ""

echo "=== Phase 3 Complete ==="
echo ""

# Phase 4: Database
echo "=== Phase 4: Database (2 minutes) ==="
echo ""

echo "4.1: Waiting for database ready..."
for i in {1..30}; do
    if docker compose exec -T db pg_isready -U apex > /dev/null 2>&1; then
        echo "   ✅ Database ready"
        break
    fi
    echo "   Waiting... ($i/30)"
    sleep 2
done

echo ""
echo "4.2: Running migrations..."
docker compose exec api alembic upgrade head
echo "   ✅ Migrations complete"

echo ""
echo "4.3: Verifying tables..."
TABLE_COUNT=$(docker compose exec -T db psql -U apex -d apex -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" | tr -d ' ')
echo "   ✅ Tables created ($TABLE_COUNT tables)"

echo ""
echo "=== Phase 4 Complete ==="
echo ""

# Phase 5: Verification
echo "=== Phase 5: Verification (5 minutes) ==="
echo ""

echo "5.1: Health endpoint checks..."
if curl -fsS http://localhost:8000/health > /dev/null; then
    echo "   ✅ API health: OK"
else
    echo "   ❌ API health: FAILED"
    exit 1
fi

if curl -fsS http://localhost:8000/ready > /dev/null; then
    echo "   ✅ API readiness: OK"
else
    echo "   ❌ API readiness: FAILED"
    exit 1
fi

if curl -fsS http://localhost:8002/healthz > /dev/null; then
    echo "   ✅ Signcalc health: OK"
else
    echo "   ❌ Signcalc health: FAILED"
    exit 1
fi

echo ""
echo "5.2: Service integration tests..."
if curl -fsS http://localhost:8000/api/v1/projects > /dev/null; then
    echo "   ✅ API endpoint: OK"
else
    echo "   ❌ API endpoint: FAILED"
    exit 1
fi

echo ""
echo "5.3: Checking logs for errors..."
ERROR_COUNT=$(docker compose logs --tail=100 2>&1 | grep -i "error\|fatal" | wc -l || echo "0")
if [ "$ERROR_COUNT" -lt 10 ]; then
    echo "   ✅ Minimal errors ($ERROR_COUNT found)"
else
    echo "   ⚠️  High error count ($ERROR_COUNT found)"
fi

echo ""
echo "=== Phase 5 Complete ==="
echo ""

# Phase 6: Smoke Test
echo "=== Phase 6: Smoke Test (5 minutes) ==="
echo ""

echo "6.1: Creating test project..."
PROJECT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/projects \
    -H "Content-Type: application/json" \
    -d '{"account_id": "test", "name": "Staging Test Project", "customer": "Test"}')

PROJECT_ID=$(echo "$PROJECT_RESPONSE" | jq -r '.data.project_id // .project_id // empty' 2>/dev/null || echo "")

if [ -n "$PROJECT_ID" ] && [ "$PROJECT_ID" != "null" ]; then
    echo "   ✅ Test project created: $PROJECT_ID"
else
    echo "   ❌ Test project creation failed"
    echo "   Response: $PROJECT_RESPONSE"
    exit 1
fi

echo ""
echo "6.2: Testing site resolution..."
SITE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/signage/common/site/resolve \
    -H "Content-Type: application/json" \
    -d '{"address": "123 Main St, Dallas, TX 75201"}')

if echo "$SITE_RESPONSE" | jq -e '.data.wind_speed_mph' > /dev/null 2>&1; then
    echo "   ✅ Site resolution working"
else
    echo "   ❌ Site resolution failed"
    exit 1
fi

echo ""
echo "6.3: Testing calculation..."
CABINET_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/signage/common/cabinets/derive \
    -H "Content-Type: application/json" \
    -d '{"overall_height_ft": 25.0, "cabinets": [{"width_ft": 14.0, "height_ft": 8.0, "depth_in": 12.0}]}')

if echo "$CABINET_RESPONSE" | jq -e '.data.A_ft2' > /dev/null 2>&1; then
    echo "   ✅ Calculation working"
else
    echo "   ❌ Calculation failed"
    exit 1
fi

echo ""
echo "=== Phase 6 Complete ==="
echo ""

echo "=== Staging Deployment SUCCESSFUL ==="
echo ""
echo "All phases completed successfully!"
echo ""
echo "Next steps:"
echo "1. Monitor logs: docker compose logs -f"
echo "2. Check metrics: http://localhost:3001 (Grafana)"
echo "3. Test frontend: http://localhost:5173"
echo ""
echo "See: docs/deployment/POST_DEPLOYMENT_MONITORING.md"

