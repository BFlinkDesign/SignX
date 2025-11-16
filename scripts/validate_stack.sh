#!/bin/bash
# CalcuSign Stack Validation Script
# Validates all services are healthy and responsive

set -e

echo "🔍 CalcuSign Stack Validation"
echo "=============================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAILED=0

# Function to check service health
check_service() {
    local name=$1
    local url=$2
    local expected=$3
    
    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $name${NC}"
        return 0
    else
        echo -e "${RED}❌ $name - FAILED${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Check compose stack status
echo "📊 Docker Compose Status:"
echo "--------------------------"
docker-compose -f infra/compose.yaml ps
echo ""

# Check PostgreSQL
echo "🔍 Checking PostgreSQL (port 5432)..."
if nc -z localhost 5432 2>/dev/null; then
    echo -e "${GREEN}✅ PostgreSQL is accepting connections${NC}"
else
    echo -e "${RED}❌ PostgreSQL not reachable${NC}"
    FAILED=$((FAILED + 1))
fi

# Check Redis
echo "🔍 Checking Redis (port 6379)..."
if check_service "Redis" "http://localhost:6379" "200"; then
    : # Already printed
fi

# Check OpenSearch
echo "🔍 Checking OpenSearch (port 9200)..."
if curl -sf http://localhost:9200/_cluster/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ OpenSearch healthy${NC}"
    
    # Get cluster health details
    HEALTH=$(curl -s http://localhost:9200/_cluster/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    echo -e "   Status: ${YELLOW}$HEALTH${NC}"
else
    echo -e "${RED}❌ OpenSearch not reachable${NC}"
    FAILED=$((FAILED + 1))
fi

# Check MinIO
echo "🔍 Checking MinIO (port 9000)..."
if curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo -e "${GREEN}✅ MinIO healthy${NC}"
else
    echo -e "${RED}❌ MinIO not reachable${NC}"
    FAILED=$((FAILED + 1))
fi

# Check API
echo "🔍 Checking API (port 8000)..."
if check_service "API" "http://localhost:8000/health" "200"; then
    # Get API health details
    RESPONSE=$(curl -s http://localhost:8000/health)
    echo "   $RESPONSE" | grep -q "ok" && echo -e "${GREEN}   API response: OK${NC}"
fi

# Check Worker
echo "🔍 Checking Worker health..."
WORKER_HEALTH=$(docker-compose -f infra/compose.yaml exec -T worker python -c "from apex.worker.app import ping; import sys; sys.exit(0 if ping().get('status')=='ok' else 1)" 2>/dev/null || echo "FAIL")
if [ "$WORKER_HEALTH" = "FAIL" ]; then
    echo -e "${YELLOW}⚠️  Worker health check failed (may be starting)${NC}"
else
    echo -e "${GREEN}✅ Worker healthy${NC}"
fi

# Check Postgres Exporter
echo "🔍 Checking Postgres Exporter (port 9187)..."
if check_service "Postgres Exporter" "http://localhost:9187/metrics" "200"; then
    METRICS=$(curl -s http://localhost:9187/metrics | grep -c "^pg_" || echo "0")
    echo "   Metrics available: $METRICS"
fi

# Check Grafana
echo "🔍 Checking Grafana (port 3001)..."
if check_service "Grafana" "http://localhost:3001/api/health" "200"; then
    echo -e "${GREEN}   Grafana dashboard: http://localhost:3001${NC}"
fi

# Check OpenSearch Dashboards
echo "🔍 Checking OpenSearch Dashboards (port 5601)..."
if check_service "OpenSearch Dashboards" "http://localhost:5601/api/status" "200"; then
    echo -e "${GREEN}   OpenSearch UI: http://localhost:5601${NC}"
fi

echo ""
echo "=============================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All services healthy${NC}"
    exit 0
else
    echo -e "${RED}❌ $FAILED service(s) failed health checks${NC}"
    echo ""
    echo "Debugging tips:"
    echo "  docker-compose -f infra/compose.yaml logs api"
    echo "  docker-compose -f infra/compose.yaml logs worker"
    echo "  docker-compose -f infra/compose.yaml logs db"
    echo "  docker-compose -f infra/compose.yaml ps"
    exit 1
fi

