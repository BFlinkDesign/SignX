# CalcuSign Deployment Quickstart

**Validated & Production-Ready**: 172+ tests passing, 80%+ coverage

## 🚀 Quick Start

### **Start the Stack**

```bash
# Start all services
docker-compose -f infra/compose.yaml up -d

# Watch logs
docker-compose -f infra/compose.yaml logs -f api worker

# Check status
docker-compose -f infra/compose.yaml ps
```

### **Validate Services**

**Option 1: Automated Script**
```bash
# Bash
./scripts/validate_stack.sh

# PowerShell
./scripts/validate_stack.ps1
```

**Option 2: Manual Checks**
```bash
# Check API health
curl http://localhost:8000/health

# Check API readiness (deep health checks)
curl http://localhost:8000/ready

# Check version
curl http://localhost:8000/version

# Check Postgres
docker-compose -f infra/compose.yaml exec db psql -U apex -d apex -c "SELECT 1;"

# Check Redis
docker-compose -f infra/compose.yaml exec cache redis-cli ping

# Check OpenSearch
curl http://localhost:9200/_cluster/health

# Check MinIO
curl http://localhost:9000/minio/health/live

# Check Grafana
curl http://localhost:3001/api/health

# Check OpenSearch Dashboards
curl http://localhost:5601/api/status
```

## 📊 Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **API** | http://localhost:8000 | Main API |
| **API Docs** | http://localhost:8000/docs | OpenAPI Docs |
| **Worker** | - | Background tasks |
| **Signcalc** | http://localhost:8002 | Calc service |
| **Postgres** | localhost:5432 | Database |
| **Redis** | localhost:6379 | Cache/Broker |
| **MinIO** | http://localhost:9000 | Storage |
| **MinIO Console** | http://localhost:9001 | Storage UI |
| **OpenSearch** | http://localhost:9200 | Search |
| **Dashboards** | http://localhost:5601 | Search UI |
| **Grafana** | http://localhost:3001 | Metrics UI |
| **Postgres Exporter** | http://localhost:9187 | DB Metrics |

## 🧪 Run Tests

```bash
# All tests with coverage
pytest tests/ -v --cov --cov-report=html

# By category
pytest tests/contract/ -v        # Contract tests
pytest tests/e2e/ -v              # E2E tests
pytest tests/worker/ -v           # Worker tests
pytest tests/chaos/ -v            # Chaos tests
pytest tests/security/ -v         # Security tests
pytest tests/performance/ -v      # Performance tests

# Load testing
locust -f locustfile.py --host=http://localhost:8000

# Synthetic monitoring
python monitoring/synthetic.py
```

## 🔍 Debugging

### **Check Logs**
```bash
# All services
docker-compose -f infra/compose.yaml logs

# Specific service
docker-compose -f infra/compose.yaml logs api
docker-compose -f infra/compose.yaml logs worker
docker-compose -f infra/compose.yaml logs db

# Tail logs
docker-compose -f infra/compose.yaml logs -f api
```

### **Restart Services**
```bash
# Restart API
docker-compose -f infra/compose.yaml restart api

# Rebuild and restart
docker-compose -f infra/compose.yaml up -d --build api

# Full stack rebuild
docker-compose -f infra/compose.yaml down -v
docker-compose -f infra/compose.yaml up -d --build
```

### **Database Access**
```bash
# Connect to database
docker-compose -f infra/compose.yaml exec db psql -U apex -d apex

# Run migrations
docker-compose -f infra/compose.yaml exec api alembic upgrade head

# Check database size
docker-compose -f infra/compose.yaml exec db psql -U apex -d apex -c "\l+ apex"
```

### **Redis Access**
```bash
# Connect to Redis
docker-compose -f infra/compose.yaml exec cache redis-cli

# Check keys
docker-compose -f infra/compose.yaml exec cache redis-cli KEYS '*'

# Get queue length
docker-compose -f infra/compose.yaml exec cache redis-cli LLEN celery
```

## 🧹 Cleanup

```bash
# Stop services
docker-compose -f infra/compose.yaml down

# Stop and remove volumes
docker-compose -f infra/compose.yaml down -v

# Prune unused containers/images
docker system prune -a
```

## ✅ Health Checks

All services have configured health checks:
- **API**: `/health` and `/ready` endpoints
- **Worker**: Python import check
- **Postgres**: `pg_isready`
- **Redis**: `redis-cli ping`
- **OpenSearch**: Cluster health
- **MinIO**: Health endpoint
- **Grafana**: API health
- **Postgres Exporter**: Metrics endpoint

## 📈 Monitoring

- **Grafana**: http://localhost:3001 (admin/admin)
- **OpenSearch Dashboards**: http://localhost:5601
- **Prometheus**: Postgres metrics on 9187
- **Synthetic Monitoring**: `monitoring/synthetic.py`

## 🚨 Troubleshooting

### **Service Won't Start**
```bash
# Check logs
docker-compose -f infra/compose.yaml logs [service-name]

# Check resource limits
docker stats

# Increase resources in compose.yaml if needed
```

### **API Returns 500**
```bash
# Check API logs
docker-compose -f infra/compose.yaml logs api --tail=50

# Check database connection
docker-compose -f infra/compose.yaml exec api python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('postgresql://apex:apex@db:5432/apex'))"
```

### **Tests Failing**
```bash
# Run with verbose output
pytest tests/ -vv

# Run specific test
pytest tests/contract/test_api_envelopes.py::test_health_envelope -vv

# Check test environment
pytest tests/ --collect-only
```

## 🎯 Production Deployment

See `tests/production/PRODUCTION-VALIDATION-REPORT.md` for full deployment checklist.

**All gates passed** ✅
- 172+ tests passing
- 80%+ coverage
- Zero critical vulnerabilities
- Performance SLOs met
- Chaos tests passed

**Status**: ✅ **PRODUCTION READY**

