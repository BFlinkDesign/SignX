# SignX Production-Readiness Guide

A systematic 7-step path to transform your SignX development environment into a bulletproof production deployment. Tailored specifically for the SignX stack: FastAPI + React + PostgreSQL + Redis + Docker.

**Timeline**: 2-5 days depending on complexity
**Prerequisite**: Git version control - branch off main for prod-ready changes

---

## Step 1: Full Code Audit for Placeholders & Fakes (1-2 Hours)

Sweep for dev artifacts that could expose internals or fail in production.

### Manual Audit Commands

```bash
# Search for common placeholder patterns
grep -rn "TODO\|FIXME\|XXX\|HACK" services/ modules/ platform/ --include="*.py"
grep -rn "mock\|dummy\|placeholder\|fake\|sample" services/ --include="*.py"
grep -rn "localhost:8000\|127.0.0.1" services/ --include="*.py" --include="*.ts"

# Check for hardcoded secrets (should be caught by Gitleaks)
grep -rn "sk-\|api_key.*=.*['\"]" services/ --include="*.py"
grep -rn "password.*=.*['\"]" services/ --include="*.py"

# Check for test data in production paths
grep -rn "test_user\|admin123\|sample_data" services/ --include="*.py"

# Find incomplete stub functions
grep -rn "pass$\|NotImplementedError\|raise NotImplemented" services/ --include="*.py"
```

### AI-Assisted Audit (Claude Code / Cursor)

```text
Audit the SignX codebase for production blockers:

1. Scan services/, modules/, and platform/ for:
   - TODOs, FIXMEs, incomplete stubs
   - Hardcoded API keys or secrets
   - Mock data (fake_user, sample_project, test_quote)
   - Localhost URLs that should be environment variables

2. Check infra/compose.yaml for:
   - Hardcoded credentials (replace with ${ENV_VAR})
   - Missing health checks
   - Insecure port exposures

3. Output a prioritized markdown report with:
   - File:line references
   - Severity (high/medium/low)
   - Suggested fixes with code patches

Focus on: services/api/, services/worker/, modules/quoting/
```

### Automated Security Scans (Already Configured)

```bash
# Run the full security pipeline locally
semgrep ci --config=auto
gitleaks detect --source .
pip install safety && safety check
```

**Output**: Prioritized list. Fix high-severity items first (exposed API keys, SQL injection vectors).

---

## Step 2: Replace Fakes with Real Integrations (4-8 Hours)

Pivot from mocks to live services for production data flows.

### Core Integration Points

| Component | Dev Mock | Production Integration |
|-----------|----------|----------------------|
| **Database** | SQLite/in-memory | PostgreSQL via `DATABASE_URL` |
| **Cache** | Dict cache | Redis via `REDIS_URL` |
| **Auth** | Mock JWT | Supabase Auth (APEX_SUPABASE_URL) |
| **Storage** | Local filesystem | MinIO via `MINIO_URL` |
| **Search** | Array filter | OpenSearch with DB fallback |
| **AI/ML** | Hardcoded responses | Gemini/Claude APIs |

### Database Validation

```bash
# Verify Alembic migrations are complete
cd services/api
alembic history --verbose
alembic check  # Should show no pending migrations

# Test migration rollback
alembic downgrade -1
alembic upgrade head
```

### AI Integration Checklist

```python
# Replace hardcoded responses in modules/intelligence/
# Before (mock):
def estimate_cost(project_data):
    return {"cost": 8000, "confidence": 0.85}  # FAKE

# After (real):
async def estimate_cost(project_data):
    response = await ml_client.predict(
        model="cost_prediction_v1",
        features=extract_features(project_data)
    )
    return {
        "cost": response.prediction,
        "confidence": response.confidence,
        "model_version": response.model_id
    }
```

### Environment Variable Audit

```bash
# Required production variables (from compose.yaml)
cat > .env.production.example << 'EOF'
# Database
DATABASE_URL=postgresql://user:pass@host:5432/signx

# Redis
REDIS_URL=redis://host:6379/0
CELERY_BROKER_URL=redis://host:6379/0

# Object Storage
MINIO_URL=https://s3.your-domain.com
MINIO_ACCESS_KEY=<from-secrets-manager>
MINIO_SECRET_KEY=<from-secrets-manager>
MINIO_BUCKET=signx-uploads

# Authentication
APEX_SUPABASE_URL=https://your-project.supabase.co
APEX_SUPABASE_KEY=<from-secrets-manager>
APEX_SUPABASE_SERVICE_KEY=<from-secrets-manager>

# AI Services
GEMINI_API_KEY=<from-secrets-manager>
ANTHROPIC_API_KEY=<from-secrets-manager>

# Security
CORS_ALLOW_ORIGINS=https://your-domain.com
APEX_RATE_LIMIT_PER_MIN=60
EOF
```

---

## Step 3: Security & Compliance Hardening (2-4 Hours)

SignX already has solid security foundations. Verify and strengthen.

### Existing Security Tools (`.github/workflows/security-scan.yml`)

| Tool | Purpose | Status |
|------|---------|--------|
| **Semgrep** | SAST code scanning | ✅ Configured |
| **Gitleaks** | Secret detection | ✅ Configured |
| **Safety** | Python dependency audit | ✅ Configured |
| **Trivy** | Container vulnerability scan | ✅ In CI |

### Local Security Audit

```bash
# Run full security suite locally before deploying
make lint  # Ruff checks

# Python dependency vulnerabilities
pip install pip-audit
pip-audit

# Container security
docker pull aquasec/trivy
trivy image apex-api:dev --severity HIGH,CRITICAL
```

### API Security Checklist

```python
# Verify in services/api/src/apex/api/

# 1. Rate limiting is enabled
# Check deps.py for APEX_RATE_LIMIT_PER_MIN usage

# 2. CORS is properly configured
# CORS_ALLOW_ORIGINS should NOT be "*" in production

# 3. Input validation with Pydantic
# All routes should use typed schemas

# 4. Authentication middleware
# Verify Supabase JWT validation on protected routes
```

### Envelope Pattern Security

All API responses must follow the secure envelope pattern:

```python
# Correct envelope response (services/api/src/apex/api/schemas.py)
{
    "ok": true,
    "result": {...},
    "meta": {
        "timestamp": "2025-12-11T...",
        "request_id": "uuid",
        "version": "1.0.0"
    }
}

# Error responses should NOT leak stack traces
{
    "ok": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "User-safe message",
        "details": {...}  # No internal paths/stack traces
    }
}
```

---

## Step 4: Comprehensive Testing Suite (4-6 Hours)

SignX has a test pyramid structure. Ensure full coverage.

### Test Categories

| Type | Location | Command | Coverage Target |
|------|----------|---------|-----------------|
| **Unit** | `tests/unit/` | `pytest tests/unit/ -v` | 80%+ |
| **Integration** | `tests/service/` | `pytest tests/service/ -v` | Key flows |
| **Contract** | `tests/contract/` | `pytest tests/contract/ -v` | All endpoints |
| **E2E** | `tests/e2e/` | `pytest tests/e2e/ -v` | Critical paths |
| **Performance** | `tests/perf/` | `k6 run tests/perf/k6_smoke.js` | <500ms p95 |

### Run Full Test Suite

```bash
# Install test dependencies
cd services/api
pip install pytest pytest-cov pytest-asyncio httpx

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html --cov-fail-under=80

# Run contract tests (requires running services)
cd infra && docker-compose up -d
pytest tests/contract/ -v
```

### Critical Test Cases for SignX

```python
# tests/unit/test_quote_calculation.py
def test_quote_determinism():
    """Same inputs must always produce same outputs"""
    input_data = {...}
    result1 = calculate_quote(input_data)
    result2 = calculate_quote(input_data)
    assert result1 == result2

# tests/contract/test_envelope_schema.py
def test_all_endpoints_return_envelope():
    """Every API response must follow envelope pattern"""
    response = client.get("/api/v1/health")
    assert "ok" in response.json()
    assert "result" in response.json() or "error" in response.json()

# tests/e2e/test_quote_workflow.py
async def test_complete_quote_flow():
    """Customer can get quote, accept, and trigger production"""
    quote = await create_quote(...)
    assert quote["ok"]

    accepted = await accept_quote(quote["result"]["quote_id"])
    assert accepted["ok"]

    # Verify event propagation
    work_order = await get_work_order(quote["result"]["quote_id"])
    assert work_order["ok"]
```

### Load Testing with k6

```javascript
// tests/perf/k6_smoke.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% under 500ms
    http_req_failed: ['rate<0.01'],    // <1% error rate
  },
};

export default function () {
  const res = http.post('http://localhost:8000/api/v1/quoting/instant', JSON.stringify({
    customer_name: 'Test Customer',
    sign_type: 'monument',
    approximate_size: '10ft x 4ft'
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  check(res, {
    'status is 200': (r) => r.status === 200,
    'has quote_id': (r) => r.json().result?.quote_id !== undefined,
  });

  sleep(1);
}
```

---

## Step 5: Performance & Scalability Tuning (2-3 Hours)

Optimize for production traffic patterns.

### Redis Caching Strategy

```python
# services/api/src/apex/api/deps.py
from functools import lru_cache
from redis import Redis

@lru_cache()
def get_redis():
    return Redis.from_url(settings.REDIS_URL)

# Cache quote calculations (TTL: 5 minutes)
async def get_cached_quote(project_hash: str):
    redis = get_redis()
    cached = redis.get(f"quote:{project_hash}")
    if cached:
        return json.loads(cached)

    quote = await calculate_quote(...)
    redis.setex(f"quote:{project_hash}", 300, json.dumps(quote))
    return quote
```

### Async Task Offloading

```python
# services/worker/src/apex/worker/tasks.py
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def process_heavy_calculation(self, project_id: str):
    """Offload expensive calculations to Celery worker"""
    try:
        result = run_structural_analysis(project_id)
        return {"status": "success", "result": result}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
```

### Database Connection Pooling

```python
# services/api/src/apex/api/database.py
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
)
```

### Performance Benchmarks

```bash
# Run k6 load test
k6 run tests/perf/k6_smoke.js

# Target metrics:
# - p95 latency: <500ms
# - Throughput: 100 req/s
# - Error rate: <0.1%
```

---

## Step 6: Monitoring & Observability Setup (1-2 Hours)

Track production health and debug issues.

### Health Endpoints (Already Configured)

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/health` | Liveness probe | `{"ok": true, "status": "healthy"}` |
| `/ready` | Readiness probe | `{"ok": true, "services": {...}}` |

### Structured Logging

```python
# services/api/src/apex/api/logging.py
import structlog

logger = structlog.get_logger()

# Log with context
logger.info(
    "quote_generated",
    quote_id=quote.id,
    customer_id=customer.id,
    sign_type=request.sign_type,
    cost=quote.estimated_cost,
    confidence=quote.confidence
)
```

### Error Tracking (Sentry)

```python
# services/api/src/apex/api/main.py
import sentry_sdk

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        environment=settings.ENV,
    )
```

### Monitoring Stack (Already in Docker Compose)

- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: Metrics collection
- **MinIO Console**: http://localhost:9001
- **OpenSearch Dashboards**: http://localhost:5601

---

## Step 7: Final Deploy & Rollout (1-2 Hours)

### Pre-Deployment Checklist

```bash
# 1. All tests pass
make all

# 2. Security scans clean
semgrep ci --config=auto
gitleaks detect --source .

# 3. Build production images
docker build -t signx-api:prod services/api/
docker build -t signx-worker:prod services/worker/

# 4. Verify environment variables
cat .env.production | grep -v "^#" | while read line; do
  key=$(echo $line | cut -d= -f1)
  if [ -z "${!key}" ]; then
    echo "WARNING: $key not set"
  fi
done
```

### CI/CD Pipeline (`.github/workflows/ci.yml`)

The existing CI pipeline includes:

1. **Lint & Type Check**: Ruff + Mypy
2. **Unit Tests**: pytest with 80% coverage gate
3. **Docker Build**: Multi-stage optimized images
4. **Contract Tests**: OpenAPI + Envelope validation
5. **E2E Tests**: Full workflow validation
6. **Performance**: k6 smoke tests
7. **Security**: SBOM generation + Trivy scan

### Deployment Commands

```bash
# Deploy to staging first
docker-compose -f infra/compose.staging.yaml up -d

# Verify health
curl -f http://staging.signx.io/health
curl -f http://staging.signx.io/ready

# Run smoke test
python scripts/smoke.py --env staging

# Deploy to production (after staging validation)
docker-compose -f infra/compose.production.yaml up -d
```

### Rollback Strategy

```bash
# Tag current version before deploy
docker tag signx-api:prod signx-api:rollback-$(date +%Y%m%d)

# If issues detected, rollback
docker-compose down
docker tag signx-api:rollback-YYYYMMDD signx-api:prod
docker-compose up -d
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Placeholder count** | 0 | `grep -rn "TODO\|FIXME" services/` |
| **Test coverage** | 80%+ | `pytest --cov-fail-under=80` |
| **Security issues** | 0 critical | Semgrep + Trivy |
| **Deploy time** | <5 minutes | CI/CD pipeline |
| **API latency (p95)** | <500ms | k6 load test |
| **Error rate** | <0.1% | Monitoring |

---

## Quick Reference: SignX Commands

```bash
# Development
make up              # Start all services
make health          # Health check
make lint            # Run linter
make test            # Run tests
make all             # lint + test

# Frontend
cd apex/apps/ui-web
npm run validate     # typecheck + lint + build

# Database
cd services/api
alembic upgrade head # Apply migrations
alembic downgrade -1 # Rollback

# Security
semgrep ci --config=auto
gitleaks detect --source .
pip-audit

# Performance
k6 run tests/perf/k6_smoke.js
```

---

## Summary

The SignX codebase already has strong foundations:
- Comprehensive CI/CD with security scanning
- Envelope pattern for consistent API responses
- Docker Compose orchestration with health checks
- Test pyramid with contract and E2E tests

**Focus Areas for Production**:
1. Replace any remaining mocks with real integrations
2. Verify all environment variables are properly managed
3. Ensure 80%+ test coverage
4. Run full security scan before deploy
5. Monitor first 24h post-deployment closely

**Estimated Timeline**: 2-3 days for a thorough production-ready deployment.
