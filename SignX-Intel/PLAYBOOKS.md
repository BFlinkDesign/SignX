# SignX-Intel Playbooks

> **Purpose**: Documented responses to common scenarios. Think of these as the team's collective muscle memory—automated decision-making for recurring situations.

---

## Table of Contents

1. [Development Playbooks](#development-playbooks)
2. [Operational Playbooks](#operational-playbooks)
3. [ML/Data Playbooks](#mldata-playbooks)
4. [Incident Response Playbooks](#incident-response-playbooks)
5. [Integration Playbooks](#integration-playbooks)

---

## Development Playbooks

### 🚀 PLAYBOOK: Adding a New API Endpoint

**Scenario**: Need to expose new functionality via API

**Steps**:

1. **Define the contract** (schema-first)
```python
# src/signx_intel/api/schemas/new_feature.py
from pydantic import BaseModel

class NewFeatureRequest(BaseModel):
    """Request schema with validation."""
    param1: str = Field(..., min_length=1, max_length=100)
    param2: int = Field(..., gt=0)

class NewFeatureResponse(BaseModel):
    """Response schema."""
    result: str
    confidence: float
```

2. **Implement the service logic**
```python
# src/signx_intel/services/new_feature_service.py
class NewFeatureService:
    async def process(self, request: NewFeatureRequest) -> NewFeatureResponse:
        # Business logic here
        pass
```

3. **Create the API route**
```python
# src/signx_intel/api/routes/new_feature.py
from fastapi import APIRouter, Depends

router = APIRouter()

@router.post("/new-feature", response_model=NewFeatureResponse)
async def new_feature(
    request: NewFeatureRequest,
    service: NewFeatureService = Depends(get_service),
    current_user: User = Depends(get_current_user)
):
    """
    Brief description of what this does.
    
    ## Business Value
    Why this endpoint exists
    
    ## Performance
    Expected latency: <200ms
    
    ## Rate Limits
    100 requests/hour per user
    """
    return await service.process(request)
```

4. **Add tests**
```python
# tests/test_new_feature.py
@pytest.mark.asyncio
async def test_new_feature():
    request = NewFeatureRequest(param1="test", param2=42)
    response = await client.post("/api/v1/new-feature", json=request.dict())
    assert response.status_code == 200
```

5. **Register the router**
```python
# src/signx_intel/api/main.py
app.include_router(new_feature.router, prefix="/api/v1", tags=["new-feature"])
```

6. **Update documentation**
- Add to README.md
- Update OpenAPI description
- Add example usage

**Success Criteria**:
- ✅ Tests pass
- ✅ OpenAPI docs generated
- ✅ Endpoints respond < 500ms p95
- ✅ Validation catches invalid inputs

---

### 🐛 PLAYBOOK: Fixing a Bug

**Scenario**: Bug reported in production or development

**Steps**:

1. **Reproduce the bug**
```python
# tests/test_bug_reproduction.py
def test_reproduce_bug_123():
    """Reproduce issue #123 where X fails when Y."""
    # Arrange
    setup_test_data()
    
    # Act
    result = function_with_bug(test_input)
    
    # Assert
    assert result.expected_value == actual_value  # This should fail now
```

2. **Write a test that fails** (shows the bug)

3. **Fix the bug** (make the test pass)
```python
# src/signx_intel/module/buggy_file.py
def function_with_bug(input):
    # OLD: return input * 2  # Wrong logic
    # NEW: Correct logic
    return input * 2 if input > 0 else 0
```

4. **Add regression protection**
```python
@pytest.mark.parametrize("input,expected", [
    (5, 10),    # Normal case
    (0, 0),     # Edge case that was broken
    (-5, 0),    # Negative case
])
def test_function_handles_edge_cases(input, expected):
    assert function_with_bug(input) == expected
```

5. **Check for similar bugs**
```bash
# Search codebase for same pattern
grep -r "similar_pattern" src/
```

6. **Document the fix**
```markdown
## Bug Fix: Issue #123

### Root Cause
Function didn't handle zero/negative inputs correctly.

### Fix
Added conditional check for input sign.

### Prevention
- Added parametrized tests for edge cases
- Added validation earlier in pipeline
```

**Success Criteria**:
- ✅ Test fails before fix, passes after
- ✅ No similar bugs in codebase
- ✅ Regression tests added
- ✅ Root cause documented

---

### ♻️ PLAYBOOK: Refactoring Complex Code

**Scenario**: Code has become too complex (>10 cyclomatic complexity, >50 lines, hard to test)

**Decision Matrix**:
```python
def should_refactor(file_path: str) -> tuple[bool, str]:
    metrics = analyze_code(file_path)
    
    if metrics.cyclomatic_complexity > 10:
        return True, "Complexity too high - extract functions"
    
    if metrics.duplication_score > 0.2:
        return True, "High duplication - extract common patterns"
    
    if metrics.test_coverage < 0.8:
        return True, "Low coverage - simplify to make testable"
    
    if metrics.function_length > 50:
        return True, "Function too long - break into smaller pieces"
    
    return False, "Code quality acceptable"
```

**Refactoring Process**:

1. **Add tests first** (safety net)
```python
# tests/test_complex_function.py
def test_complex_function_behavior():
    """Capture current behavior before refactoring."""
    # Test all paths through complex function
    pass
```

2. **Extract functions** (single responsibility)
```python
# BEFORE: One complex function
def process_order(order_id):
    # 100 lines of mixed concerns
    pass

# AFTER: Composed pipeline
async def process_order(order_id: str) -> ProcessedOrder:
    order = await fetch_order(order_id)
    validated = validate_order(order)
    enriched = await enrich_order(validated)
    predicted = await predict_costs(enriched)
    stored = await store_result(predicted)
    await notify_stakeholders(stored)
    return stored
```

3. **Extract services** (dependency injection)
```python
# AFTER: Testable service
class OrderProcessor:
    def __init__(
        self,
        fetcher: OrderFetcher,
        validator: OrderValidator,
        predictor: CostPredictor,
        notifier: Notifier
    ):
        self.fetcher = fetcher
        self.validator = validator
        self.predictor = predictor
        self.notifier = notifier
    
    async def process(self, order_id: str) -> ProcessedOrder:
        # Each dependency is mockable
        pass
```

4. **Verify tests still pass**

5. **Measure improvement**
```python
# Before: Complexity 15, 120 lines, 60% coverage
# After:  Complexity 4, 30 lines, 95% coverage
```

**Success Criteria**:
- ✅ All tests pass
- ✅ Complexity < 10
- ✅ Functions < 50 lines
- ✅ Test coverage improved

---

## Operational Playbooks

### 🔥 PLAYBOOK: API Latency Spike

**Scenario**: API response times suddenly increase (p95 > 1s)

**Diagnosis**:

1. **Check Grafana dashboard**
   - Which endpoint is slow?
   - When did it start?
   - Traffic volume change?

2. **Check traces** (OpenTelemetry)
```bash
# Find slow traces
curl "http://localhost:16686/api/traces?service=signx-intel&limit=20&lookback=1h&minDuration=1s"
```

3. **Check database**
```sql
-- Long-running queries
SELECT pid, now() - query_start as duration, query
FROM pg_stat_activity
WHERE state = 'active'
AND now() - query_start > interval '1 second'
ORDER BY duration DESC;

-- Missing indexes
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE schemaname NOT IN ('pg_catalog', 'information_schema');
```

4. **Check external services**
```bash
# Circuit breaker status
curl http://localhost:8000/health/circuit-breakers
```

**Common Causes & Fixes**:

| Symptom | Cause | Fix |
|---------|-------|-----|
| Slow DB queries | Missing index | `CREATE INDEX idx_name ON table(column);` |
| External API timeout | Service down | Enable circuit breaker, use cache fallback |
| High CPU | Expensive computation | Move to background job, add caching |
| Memory spike | Memory leak | Restart service, investigate with profiler |

**Mitigation Steps**:

1. **Immediate** (< 5 minutes)
```bash
# Restart service if memory leak
docker-compose restart api

# Enable circuit breaker if external service down
# (automatic if configured)
```

2. **Short-term** (< 1 hour)
```python
# Add caching
@cache(ttl=3600)
async def expensive_operation():
    pass

# Add index
await db.execute("CREATE INDEX CONCURRENTLY idx_name ON table(column);")
```

3. **Long-term** (< 1 day)
- Profile code, optimize bottlenecks
- Add horizontal scaling (more API replicas)
- Optimize database queries

**Success Criteria**:
- ✅ p95 latency < 500ms
- ✅ No error rate increase
- ✅ Root cause identified and documented

---

### 📊 PLAYBOOK: Database Running Out of Space

**Scenario**: PostgreSQL disk usage > 80%

**Diagnosis**:

1. **Check disk usage**
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
```

2. **Check data growth rate**
```sql
SELECT 
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as records
FROM cost_records
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC
LIMIT 30;
```

**Actions**:

1. **Archive old data** (> 2 years)
```python
# Archive to data lake
async def archive_old_data():
    # Export to Parquet
    old_data = await db.execute(
        select(cost_records)
        .where(cost_records.c.created_at < datetime.now() - timedelta(days=730))
    )
    
    # Write to data lake
    writer = ParquetWriter("./data/archive")
    writer.write_cost_records(old_data)
    
    # Delete from database
    await db.execute(
        delete(cost_records)
        .where(cost_records.c.created_at < datetime.now() - timedelta(days=730))
    )
```

2. **Vacuum database**
```sql
VACUUM FULL cost_records;
REINDEX TABLE cost_records;
```

3. **Partition large tables**
```sql
-- Partition by year for large tables
CREATE TABLE cost_records_2024 PARTITION OF cost_records
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

4. **Set up automated archiving**
```python
# Schedule daily archival job
@scheduler.scheduled_job('cron', hour=2)
async def daily_archival():
    await archive_old_data()
```

**Prevention**:
- Set up disk space alerts (Grafana)
- Automated archival to data lake
- Table partitioning for large tables
- Regular VACUUM ANALYZE

---

### 🔐 PLAYBOOK: Suspected Security Breach

**Scenario**: Unusual access patterns detected

**Immediate Actions** (< 15 minutes):

1. **Confirm the breach**
```bash
# Check access logs
tail -f /var/log/signx-intel/access.log | grep "suspicious_pattern"

# Check failed auth attempts
SELECT user_id, ip_address, COUNT(*) as attempts
FROM auth_logs
WHERE success = FALSE
AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY user_id, ip_address
HAVING COUNT(*) > 10;
```

2. **Revoke compromised credentials**
```python
# Revoke API key
await api_key_repository.revoke(compromised_key_id)

# Force password reset
await user_repository.require_password_reset(user_id)
```

3. **Block suspicious IPs**
```python
# Add to rate limiter blocklist
await rate_limiter.block_ip(suspicious_ip, duration=timedelta(hours=24))
```

4. **Notify stakeholders**
```python
await telegram_bot.send_alert(
    channel="security",
    message=f"🚨 Security Event: Suspicious access from {ip_address}"
)
```

**Investigation** (< 1 hour):

1. **Audit logs**
```sql
-- What did they access?
SELECT endpoint, method, status_code, timestamp
FROM api_logs
WHERE ip_address = 'suspicious_ip'
AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp;

-- What data was exposed?
SELECT resource_type, resource_id, action
FROM audit_logs
WHERE user_id = 'compromised_user'
AND timestamp > NOW() - INTERVAL '24 hours';
```

2. **Check for data exfiltration**
```sql
-- Large exports?
SELECT user_id, endpoint, response_size_bytes, timestamp
FROM api_logs
WHERE response_size_bytes > 10000000  -- 10MB
AND timestamp > NOW() - INTERVAL '24 hours';
```

3. **Document timeline**
```markdown
## Security Incident Report

**Date**: 2024-11-03
**Detected**: 14:23 UTC
**Contained**: 14:38 UTC
**Resolved**: 15:15 UTC

### Timeline
- 14:15 - Unusual login from 192.168.1.100
- 14:20 - 50 failed auth attempts
- 14:23 - Alert triggered
- 14:30 - API key revoked
- 14:38 - IP blocked

### Impact
- 0 records exfiltrated (confirmed)
- 1 API key compromised (revoked)
- No system access gained

### Root Cause
Phishing attack, user clicked malicious link

### Remediation
- User password reset forced
- MFA enabled for all users
- Security training scheduled
```

**Success Criteria**:
- ✅ Breach contained < 30 minutes
- ✅ No data exfiltrated
- ✅ Root cause identified
- ✅ Preventive measures implemented

---

## ML/Data Playbooks

### 🤖 PLAYBOOK: Model Performance Degradation

**Scenario**: Production model MAPE increases from 12% to 18%

**Diagnosis**:

1. **Check model health dashboard**
```python
# Get current metrics
current_metrics = await model_registry.get_production_metrics("cost_predictor")

# Compare to baseline
baseline = await model_registry.get_baseline_metrics("cost_predictor")

degradation_pct = (current_metrics.mape - baseline.mape) / baseline.mape * 100
# 50% degradation → investigate
```

2. **Analyze prediction errors**
```python
# Find which predictions are most wrong
errors = await db.execute("""
    SELECT 
        project_id,
        predicted_cost,
        actual_cost,
        ABS(predicted_cost - actual_cost) / actual_cost as error_pct,
        drivers
    FROM cost_records
    WHERE predicted_cost IS NOT NULL
    AND actual_cost IS NOT NULL
    AND created_at > NOW() - INTERVAL '7 days'
    ORDER BY error_pct DESC
    LIMIT 100
""")

# Look for patterns
error_analysis = analyze_error_patterns(errors)
# e.g., "90% of high-error predictions have 'aluminum' material"
```

3. **Check for data drift**
```python
# Compare feature distributions
recent_features = await get_features(days=7)
training_features = load_training_features()

drift_report = calculate_distribution_drift(recent_features, training_features)
# KS test, Jensen-Shannon divergence, etc.
```

**Common Causes**:

| Symptom | Cause | Fix |
|---------|-------|-----|
| High errors on specific material | Material prices changed | Retrain with recent data |
| Consistent overestimation | Operational efficiency improved | Add new features, retrain |
| High errors on large projects | Not enough training data | Collect more data, use transfer learning |
| Random high errors | Data quality issues | Audit data pipeline |

**Remediation**:

1. **Immediate** (< 1 hour)
```python
# Rollback to previous model version
await model_registry.rollback_to_version("cost_predictor", "v20241101")

# Increase confidence threshold (serve fewer predictions)
CONFIDENCE_THRESHOLD = 0.8  # Was 0.7
```

2. **Short-term** (< 1 day)
```python
# Retrain on recent data
recent_data = await get_training_data(days=90)
new_model = await train_model(recent_data)

# A/B test
await model_registry.deploy_ab_test(
    model_a="cost_predictor_v20241101",
    model_b="cost_predictor_v20241103",
    traffic_split=0.9  # 90% old, 10% new
)
```

3. **Long-term** (< 1 week)
```python
# Add new features
def engineer_new_features(df):
    # Material price volatility
    df["material_price_volatility"] = calculate_price_volatility(df["material"])
    
    # Seasonal factors
    df["is_winter"] = df["install_month"].isin(["Dec", "Jan", "Feb"])
    
    return df

# Automated retraining
await setup_automated_retraining(
    trigger=lambda metrics: metrics.mape > baseline.mape * 1.2,
    frequency=timedelta(weeks=1)
)
```

**Success Criteria**:
- ✅ MAPE < 15% (within target)
- ✅ No bias in errors (balanced over/under)
- ✅ Confidence calibration correct
- ✅ Automated monitoring in place

---

### 📉 PLAYBOOK: Data Quality Issues

**Scenario**: Validation failures increasing, data quality SLA violated

**Detection**:

```python
# Automated quality checks
class DataQualityMonitor:
    async def check_quality(self) -> DataQualityReport:
        # Completeness
        completeness = await self.check_completeness()
        
        # Accuracy (via sampling)
        accuracy = await self.audit_sample(sample_size=100)
        
        # Freshness
        freshness = await self.check_freshness()
        
        # Consistency
        consistency = await self.check_consistency()
        
        report = DataQualityReport(
            completeness=completeness,
            accuracy=accuracy,
            freshness=freshness,
            consistency=consistency
        )
        
        if not report.passes_sla():
            await self.alert_data_owner(report)
        
        return report
```

**Common Issues**:

1. **Missing Data**
```python
# Find patterns in missing data
missing_analysis = df.isnull().sum() / len(df) * 100
# e.g., "material_cost missing in 30% of records"

# Root cause: PDF parser failing on certain formats
# Fix: Improve parser, add validation
```

2. **Incorrect Data**
```python
# Validation rules
def validate_cost_record(record: CostRecord) -> List[str]:
    errors = []
    
    # Breakdown should sum to total
    breakdown = (
        (record.labor_cost or 0) +
        (record.material_cost or 0) +
        (record.overhead_cost or 0)
    )
    if abs(breakdown - record.total_cost) / record.total_cost > 0.05:
        errors.append("Cost breakdown doesn't match total")
    
    # Realistic ranges
    cost_per_sqft = record.total_cost / record.drivers["sign_area_sqft"]
    if cost_per_sqft < 10 or cost_per_sqft > 500:
        errors.append("Cost per sqft outside realistic range")
    
    return errors
```

3. **Stale Data**
```python
# Check data freshness
latest_record = await db.execute(
    select(max(cost_records.c.created_at))
)
age = datetime.utcnow() - latest_record
if age > timedelta(hours=2):  # SLA: 2 hours
    await alert("Data pipeline stale")
```

**Remediation**:

```python
# 1. Quarantine bad data
await db.execute(
    update(cost_records)
    .where(cost_records.c.validation_status == "failed")
    .values(quarantined=True)
)

# 2. Fix data pipeline
# - Improve PDF parser
# - Add validation at ingestion
# - Set up data lineage tracking

# 3. Backfill corrected data
await reprocess_quarantined_records()

# 4. Prevent recurrence
await setup_data_quality_gates(
    validation_rules=ALL_VALIDATION_RULES,
    reject_on_fail=True
)
```

---

### 📦 PLAYBOOK: Training a New Model

**Scenario**: Need to train a model from scratch or retrain existing

**Process**:

1. **Prepare data**
```python
# Extract from database + data lake
df = await load_training_data(
    start_date=datetime(2022, 1, 1),
    end_date=datetime.now(),
    min_data_quality_score=0.9
)

# Feature engineering
features = engineer_features(df)

# Train/validation/test split
train, val, test = split_data(features, test_size=0.2, val_size=0.1)
```

2. **Train model**
```python
# Train with MLflow tracking
with mlflow.start_run(run_name="cost_predictor_v20241103"):
    # Log parameters
    mlflow.log_params({
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.1
    })
    
    # Train
    model = XGBRegressor(**params)
    model.fit(train.X, train.y)
    
    # Evaluate
    val_pred = model.predict(val.X)
    metrics = {
        "val_mae": mean_absolute_error(val.y, val_pred),
        "val_rmse": np.sqrt(mean_squared_error(val.y, val_pred)),
        "val_r2": r2_score(val.y, val_pred)
    }
    mlflow.log_metrics(metrics)
    
    # SHAP analysis
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(val.X)
    mlflow.log_artifact("shap_summary.png")
    
    # Save model
    mlflow.sklearn.log_model(model, "model")
```

3. **Validate model**
```python
# Test set evaluation
test_pred = model.predict(test.X)
test_metrics = calculate_metrics(test.y, test_pred)

# Check improvement over baseline
baseline_metrics = load_baseline_metrics()
improvement = (baseline_metrics["mae"] - test_metrics["mae"]) / baseline_metrics["mae"]

if improvement < 0.05:  # Less than 5% improvement
    print("⚠️  Model not significantly better than baseline")
    # Don't deploy
```

4. **Deploy model**
```python
# A/B test deployment
await model_registry.deploy_ab_test(
    model_name="cost_predictor",
    model_version="v20241103",
    traffic_pct=0.1,  # 10% of traffic
    rollback_on_error=True
)

# Monitor for 24 hours
# If metrics stable → increase to 50%
# If metrics stable → increase to 100%
```

**Success Criteria**:
- ✅ MAE < 15% (target)
- ✅ R² > 0.85
- ✅ No bias (balanced over/under prediction)
- ✅ Explainability (SHAP values make sense)
- ✅ Performance in production matches validation

---

## Incident Response Playbooks

### 🚨 PLAYBOOK: Service Down

**Scenario**: API not responding, health check failing

**Immediate Response** (< 5 minutes):

1. **Check service status**
```bash
# Docker
docker-compose ps
docker-compose logs api

# Kubernetes
kubectl get pods -l app=signx-intel
kubectl logs -f deployment/signx-intel-api
```

2. **Check dependencies**
```bash
# Database
docker-compose exec postgres pg_isready

# Redis
docker-compose exec redis redis-cli ping
```

3. **Restart if necessary**
```bash
docker-compose restart api
# or
kubectl rollout restart deployment/signx-intel-api
```

**Investigation** (< 30 minutes):

1. **Check logs for errors**
```bash
# Find crash reason
docker-compose logs api | grep -i "error\|exception\|fatal"

# Check resource usage
docker stats
```

2. **Common causes**:
   - Out of memory → Increase memory limits
   - Database connection exhausted → Check connection pooling
   - Unhandled exception → Fix bug, deploy patch
   - External dependency down → Enable circuit breaker

**Communication**:
```markdown
## Incident Report: API Downtime

**Status**: RESOLVED
**Duration**: 12 minutes (14:23 - 14:35 UTC)
**Impact**: API unavailable, 0 predictions served

### Timeline
- 14:23 - Service crashed (OOM error)
- 14:25 - Alert received
- 14:27 - Investigation started
- 14:30 - Root cause identified (memory leak)
- 14:32 - Service restarted with increased memory
- 14:35 - Service healthy

### Root Cause
Memory leak in feature caching logic

### Fix
- Immediate: Restarted with 2GB memory (was 1GB)
- Permanent: Fixed memory leak in commit abc123
- Prevention: Added memory usage alerts

### Action Items
- [ ] Deploy permanent fix to production
- [ ] Add memory leak detection to CI/CD
- [ ] Review all caching logic for similar issues
```

---

## Integration Playbooks

### 🔗 PLAYBOOK: Integrating a New External System

**Scenario**: Need to connect to a new CRM/ERP/API

**Process**:

1. **Design the interface**
```python
# src/signx_intel/connectors/new_system.py

from abc import ABC, abstractmethod

class ExternalSystemConnector(ABC):
    """Abstract interface for external systems."""
    
    @abstractmethod
    async def fetch_orders(self, since: datetime) -> List[Order]:
        """Pull orders from external system."""
        pass
    
    @abstractmethod
    async def push_prediction(self, order_id: str, prediction: CostPrediction):
        """Push prediction to external system."""
        pass

class NewSystemConnector(ExternalSystemConnector):
    """Concrete implementation for NewSystem."""
    
    def __init__(self, api_key: str, base_url: str):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"}
        )
    
    async def fetch_orders(self, since: datetime) -> List[Order]:
        response = await self.client.get(
            "/orders",
            params={"modified_since": since.isoformat()}
        )
        return [Order.parse_obj(item) for item in response.json()]
    
    async def push_prediction(self, order_id: str, prediction: CostPrediction):
        await self.client.post(
            f"/orders/{order_id}/cost_estimate",
            json={
                "amount": float(prediction.cost),
                "confidence": prediction.confidence,
                "source": "signx_intel"
            }
        )
```

2. **Add resilience**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=4, max=10)
)
async def fetch_orders_with_retry(self, since: datetime):
    """Fetch with automatic retry."""
    return await self.fetch_orders(since)
```

3. **Add observability**
```python
@tracer.start_as_current_span("fetch_orders_from_new_system")
async def fetch_orders(self, since: datetime):
    logger.info("fetching_orders", since=since.isoformat())
    orders = await self.client.get(...)
    logger.info("orders_fetched", count=len(orders))
    return orders
```

4. **Test thoroughly**
```python
# tests/test_new_system_connector.py

@pytest.mark.asyncio
async def test_fetch_orders():
    connector = NewSystemConnector(api_key="test", base_url="http://mock")
    orders = await connector.fetch_orders(datetime.now())
    assert len(orders) > 0

@pytest.mark.asyncio
async def test_push_prediction():
    connector = NewSystemConnector(api_key="test", base_url="http://mock")
    prediction = CostPrediction(cost=Decimal("1000"), confidence=0.9)
    await connector.push_prediction("order-123", prediction)
    # Verify webhook called
```

5. **Deploy incrementally**
```python
# Start with manual sync
await connector.fetch_orders(since=datetime(2024, 1, 1))

# Then add scheduled sync
@scheduler.scheduled_job('cron', hour='*/1')  # Every hour
async def sync_orders():
    await connector.fetch_orders(since=last_sync_time)

# Finally add real-time webhooks
@app.post("/webhooks/new-system/order-created")
async def handle_order_created(event: OrderCreatedEvent):
    await process_new_order(event.order_id)
```

**Success Criteria**:
- ✅ Data syncs correctly
- ✅ Errors handled gracefully (retry, fallback)
- ✅ Observable (logs, metrics, traces)
- ✅ Tested (unit + integration)
- ✅ Documented (API docs, runbook)

---

### 🤝 PLAYBOOK: Breaking API Changes

**Scenario**: Need to make a breaking change to API

**Strategy**: Use API versioning

1. **Version the endpoint**
```python
# Keep v1 (deprecated but working)
@router.post("/api/v1/predict")
async def predict_v1(request: PredictionRequestV1):
    """Deprecated: Use /api/v2/predict instead."""
    # Old logic
    pass

# Add v2 (new schema)
@router.post("/api/v2/predict")
async def predict_v2(request: PredictionRequestV2):
    """New prediction endpoint with enhanced features."""
    # New logic
    pass
```

2. **Add deprecation warnings**
```python
@router.post("/api/v1/predict")
async def predict_v1(
    request: PredictionRequestV1,
    response: Response
):
    # Add deprecation header
    response.headers["X-API-Deprecated"] = "true"
    response.headers["X-API-Sunset"] = "2025-01-01"
    response.headers["X-API-Replacement"] = "/api/v2/predict"
    
    logger.warning("deprecated_api_used", 
                  endpoint="/api/v1/predict",
                  user_id=request.user_id)
    
    return await predict_v1_logic(request)
```

3. **Communicate the change**
```markdown
## API Change Notice

**Endpoint**: POST /api/v1/predict
**Status**: Deprecated
**Sunset Date**: 2025-01-01
**Replacement**: POST /api/v2/predict

### What Changed
- Request schema now requires `project_id`
- Response includes `confidence_interval` (new field)
- Response includes `feature_importance` (new field)

### Migration Guide
```python
# Old (v1)
response = await client.post("/api/v1/predict", json={
    "drivers": {"sign_height_ft": 25}
})

# New (v2)
response = await client.post("/api/v2/predict", json={
    "project_id": "uuid-here",  # Required
    "drivers": {"sign_height_ft": 25}
})
```

### Timeline
- 2024-11-03: v2 available
- 2024-12-01: v1 deprecated warnings
- 2025-01-01: v1 removed
```

4. **Monitor migration**
```python
# Track v1 vs v2 usage
v1_usage = Counter("api_v1_predict_calls")
v2_usage = Counter("api_v2_predict_calls")

# Alert when v1 still used near sunset
if datetime.now() > datetime(2024, 12, 15):
    if v1_usage.value > 0:
        await alert(f"⚠️  v1 API still used: {v1_usage.value} calls/day")
```

**Success Criteria**:
- ✅ No users break (v1 still works)
- ✅ Migration path clear (docs + warnings)
- ✅ Sunset timeline communicated (90+ days notice)
- ✅ v1 removed only after zero usage

---

*Playbooks are living documents. Update them as you learn.*

