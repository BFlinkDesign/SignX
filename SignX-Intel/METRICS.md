# SignX-Intel Metrics

> **Philosophy**: "If you can't measure it, you can't improve it." Every important capability must be quantified, monitored, and dashboarded.

---

## Table of Contents

1. [Metric Categories](#metric-categories)
2. [Business Metrics](#business-metrics)
3. [Engineering Metrics](#engineering-metrics)
4. [ML/AI Metrics](#mlai-metrics)
5. [Data Quality Metrics](#data-quality-metrics)
6. [Operational Metrics](#operational-metrics)
7. [Cost Metrics](#cost-metrics)
8. [Dashboards & Alerts](#dashboards--alerts)

---

## Metric Categories

### The Four Golden Signals (SRE)

Every service should measure:

1. **Latency**: How long does it take?
2. **Traffic**: How much demand?
3. **Errors**: What's failing?
4. **Saturation**: How full are we?

### Business Impact Metrics

Every feature should measure:

1. **Adoption**: Who's using it?
2. **Value**: What benefit delivered?
3. **Cost**: What's it costing?
4. **Quality**: How well does it work?

---

## Business Metrics

### Cost Prediction Accuracy

**What**: How close are ML predictions to actual costs?

**Why**: Core value proposition; inaccurate predictions = lost money

**Metric Definition**:
```python
# Mean Absolute Percentage Error (MAPE)
MAPE = mean(abs((actual - predicted) / actual)) * 100

# Target: < 15%
# Alert: > 20%
```

**How to Measure**:
```sql
SELECT 
    AVG(ABS(actual_cost - predicted_cost) / actual_cost) * 100 as mape,
    COUNT(*) as prediction_count,
    DATE_TRUNC('day', cost_date) as date
FROM cost_records
WHERE predicted_cost IS NOT NULL
  AND actual_cost IS NOT NULL
  AND cost_date > NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', cost_date)
ORDER BY date DESC;
```

**Dashboard Chart**: Time series line chart
- X-axis: Date
- Y-axis: MAPE %
- Target line: 15%
- Alert threshold: 20%

**Interpretation**:
- MAPE < 10%: Excellent
- MAPE 10-15%: Good (target)
- MAPE 15-20%: Acceptable (investigate)
- MAPE > 20%: Poor (action required)

---

### Time Savings from Automation

**What**: Hours saved per week through automated estimating

**Why**: Quantifies ROI of the system

**Metric Definition**:
```python
time_saved_per_prediction = 30  # minutes (manual estimate time)
predictions_per_week = count_predictions(days=7)
hours_saved = (predictions_per_week * time_saved_per_prediction) / 60

# Target: > 20 hours/week
```

**How to Measure**:
```sql
SELECT 
    COUNT(*) as predictions_per_week,
    COUNT(*) * 0.5 as hours_saved  -- 30 min = 0.5 hrs
FROM cost_records
WHERE predicted_cost IS NOT NULL
  AND created_at > NOW() - INTERVAL '7 days';
```

**Dashboard Chart**: Single stat + trend
- Big number: Hours saved this week
- Sparkline: Trend over 8 weeks
- Target: 20 hours/week

**Business Value Calculation**:
```python
hours_saved_per_week = 20
hourly_rate = 75  # Cost of estimator
annual_savings = hours_saved_per_week * 52 * hourly_rate
# = $78,000/year
```

---

### Revenue Protected

**What**: Dollar value of estimation errors caught before becoming losses

**Why**: Demonstrates financial value of the system

**Metric Definition**:
```python
# Projects where ML caught a significant underestimate
protected_revenue = sum(
    (manual_estimate - ml_estimate)
    for project in projects
    if manual_estimate < ml_estimate * 0.85  # 15%+ underestimate
)

# Target: > $50k/month
```

**How to Measure**:
```sql
-- Find cases where ML caught underestimates
SELECT 
    SUM(predicted_cost - manual_estimate) as revenue_protected,
    COUNT(*) as underestimate_count
FROM cost_records
WHERE manual_estimate IS NOT NULL
  AND predicted_cost > manual_estimate * 1.15  -- ML was 15%+ higher
  AND cost_date > NOW() - INTERVAL '30 days';
```

**Dashboard Chart**: Bar chart by month
- X-axis: Month
- Y-axis: $ Revenue protected
- Color: Green (good catch!)

---

### Prediction Confidence Distribution

**What**: Distribution of confidence scores across predictions

**Why**: Low confidence = need more data or features

**Metric Definition**:
```python
confidence_distribution = {
    "high": count(confidence >= 0.8),
    "medium": count(0.6 <= confidence < 0.8),
    "low": count(confidence < 0.6)
}

# Target: 80% high confidence
```

**How to Measure**:
```sql
SELECT 
    CASE 
        WHEN confidence_score >= 0.8 THEN 'high'
        WHEN confidence_score >= 0.6 THEN 'medium'
        ELSE 'low'
    END as confidence_bucket,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM cost_records
WHERE predicted_cost IS NOT NULL
  AND confidence_score IS NOT NULL
  AND created_at > NOW() - INTERVAL '30 days'
GROUP BY confidence_bucket;
```

**Dashboard Chart**: Pie chart or donut chart
- Segments: High (>80%), Medium (60-80%), Low (<60%)
- Colors: Green, Yellow, Red

---

### User Adoption Rate

**What**: % of projects using ML predictions vs. manual estimates

**Why**: Indicates user trust and system value

**Metric Definition**:
```python
adoption_rate = (
    projects_with_ml_prediction / total_projects
) * 100

# Target: > 70%
```

**How to Measure**:
```sql
WITH project_stats AS (
    SELECT 
        COUNT(*) as total_projects,
        SUM(CASE WHEN predicted_cost IS NOT NULL THEN 1 ELSE 0 END) as ml_projects
    FROM cost_records
    WHERE created_at > NOW() - INTERVAL '30 days'
)
SELECT 
    total_projects,
    ml_projects,
    (ml_projects::float / total_projects * 100) as adoption_rate_pct
FROM project_stats;
```

**Dashboard Chart**: Gauge chart
- Range: 0-100%
- Zones: 
  - 0-50% Red (low adoption)
  - 50-80% Yellow (growing)
  - 80-100% Green (high adoption)

---

## Engineering Metrics

### API Response Time (Latency)

**What**: Time to respond to API requests

**Why**: User experience; slow = frustration

**Metric Definition**:
```python
# Percentiles (not averages - outliers matter!)
p50_latency: float  # Median
p95_latency: float  # 95th percentile (SLO)
p99_latency: float  # 99th percentile (worst case)

# Targets:
# p50 < 200ms
# p95 < 500ms
# p99 < 1000ms
```

**How to Measure**:
```python
from prometheus_client import Histogram

api_latency = Histogram(
    'http_request_duration_seconds',
    'API request latency',
    ['method', 'endpoint', 'status'],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
)

@app.middleware("http")
async def track_latency(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    api_latency.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).observe(duration)
    
    return response
```

**Dashboard Chart**: Multi-line time series
- X-axis: Time
- Y-axis: Latency (ms)
- Lines: p50, p95, p99
- Thresholds: 500ms (p95), 1000ms (p99)

**Query (Prometheus)**:
```promql
# p95 latency by endpoint
histogram_quantile(0.95, 
    rate(http_request_duration_seconds_bucket[5m])
)
```

---

### Error Rate

**What**: % of requests that fail

**Why**: Reliability; errors = broken user experience

**Metric Definition**:
```python
error_rate = (
    failed_requests / total_requests
) * 100

# Target: < 0.1% (99.9% success)
# Alert: > 1.0%
```

**How to Measure**:
```python
from prometheus_client import Counter

requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

requests_failed = Counter(
    'http_requests_failed_total',
    'Failed HTTP requests',
    ['method', 'endpoint', 'error_type']
)
```

**Dashboard Chart**: Stacked area chart
- X-axis: Time
- Y-axis: Requests/sec
- Areas: Success (green), 4xx (yellow), 5xx (red)

**Query (Prometheus)**:
```promql
# Error rate (5xx)
sum(rate(http_requests_total{status=~"5.."}[5m])) /
sum(rate(http_requests_total[5m])) * 100
```

---

### Database Query Performance

**What**: Database query execution time

**Why**: Database bottlenecks = API slowness

**Metric Definition**:
```python
slow_query_threshold = 1.0  # seconds
slow_query_count = count(query_time > slow_query_threshold)

# Target: < 10 slow queries/hour
```

**How to Measure**:
```sql
-- Enable query logging
ALTER DATABASE cost_intelligence SET log_min_duration_statement = 1000;

-- Find slow queries
SELECT 
    query,
    mean_exec_time,
    calls,
    total_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 1000  -- >1 second
ORDER BY mean_exec_time DESC
LIMIT 20;
```

**Dashboard Chart**: Table of slow queries
- Columns: Query, Avg Time, Call Count, Total Time
- Sort: By avg time DESC

---

### Test Coverage

**What**: % of code covered by automated tests

**Why**: Tests prevent regressions; coverage = safety net

**Metric Definition**:
```python
coverage_pct = (
    lines_covered / total_lines
) * 100

# Targets:
# Overall: > 80%
# Core logic (cost predictions): 100%
# API routes: > 90%
```

**How to Measure**:
```bash
# Run pytest with coverage
pytest --cov=src/signx_intel --cov-report=term-missing

# Generate HTML report
pytest --cov=src/signx_intel --cov-report=html

# Enforce minimum in CI/CD
pytest --cov=src/signx_intel --cov-fail-under=80
```

**Dashboard Chart**: Gauge chart per module
- Overall coverage gauge
- Per-module breakdown (table)

---

### Deployment Frequency

**What**: How often we deploy to production

**Why**: High frequency = faster iteration, better DORA metrics

**Metric Definition**:
```python
deployments_per_week = count(deployments, days=7)

# Target: > 5 deployments/week (daily+)
```

**How to Measure**:
```bash
# Git tags mark deployments
git tag -l "v*" --sort=-creatordate | head -10

# Count deployments this week
git log --since="7 days ago" --grep="deploy" --oneline | wc -l
```

**Dashboard Chart**: Bar chart
- X-axis: Week
- Y-axis: Deployment count
- Target line: 5/week

---

### Mean Time to Recovery (MTTR)

**What**: Average time from incident to resolution

**Why**: Incidents happen; fast recovery = resilience

**Metric Definition**:
```python
mttr = mean(
    resolution_time - detection_time
    for incident in incidents
)

# Target: < 30 minutes
```

**How to Measure**:
```sql
-- Track incidents
CREATE TABLE incidents (
    id UUID PRIMARY KEY,
    title VARCHAR(500),
    severity VARCHAR(20),  -- critical, major, minor
    detected_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    duration_minutes INT GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (resolved_at - detected_at)) / 60
    ) STORED
);

-- Calculate MTTR
SELECT 
    AVG(duration_minutes) as mttr_minutes,
    COUNT(*) as incident_count
FROM incidents
WHERE detected_at > NOW() - INTERVAL '30 days'
  AND resolved_at IS NOT NULL;
```

**Dashboard Chart**: Line chart over time
- X-axis: Week
- Y-axis: MTTR (minutes)
- Target: < 30 minutes

---

## ML/AI Metrics

### Model Accuracy (R²)

**What**: How well does the model explain variance in cost?

**Why**: R² = goodness of fit

**Metric Definition**:
```python
R² = 1 - (SS_residual / SS_total)

# Target: > 0.85
# Alert: < 0.75
```

**How to Measure**:
```python
from sklearn.metrics import r2_score

y_true = actual_costs
y_pred = predicted_costs
r2 = r2_score(y_true, y_pred)

# Track in MLflow
mlflow.log_metric("r2_score", r2)
```

**Dashboard Chart**: Single stat + trend
- Big number: Current R²
- Sparkline: Trend over training runs
- Baseline: Previous model R²

---

### Model Drift Detection

**What**: Are prediction patterns changing over time?

**Why**: Drift = model degradation

**Metric Definition**:
```python
# Statistical tests for distribution shift
# KS test (Kolmogorov-Smirnov)
ks_statistic, p_value = ks_2samp(
    training_distribution,
    production_distribution
)

# Alert if p < 0.05 (significant drift)
```

**How to Measure**:
```python
from scipy.stats import ks_2samp

# Compare feature distributions
def detect_drift(feature_name: str) -> DriftReport:
    # Training data
    train_values = load_training_features()[feature_name]
    
    # Recent production data
    prod_values = load_production_features(days=7)[feature_name]
    
    # Statistical test
    ks_stat, p_value = ks_2samp(train_values, prod_values)
    
    return DriftReport(
        feature=feature_name,
        ks_statistic=ks_stat,
        p_value=p_value,
        drift_detected=p_value < 0.05
    )
```

**Dashboard Chart**: Heatmap
- Rows: Features
- Columns: Weeks
- Color: Green (no drift), Red (drift detected)

---

### Feature Importance Stability

**What**: Do important features stay important?

**Why**: Changing importance = model instability

**Metric Definition**:
```python
# Correlation of SHAP values across time
feature_importance_correlation = correlation(
    shap_values_this_week,
    shap_values_last_week
)

# Target: > 0.9 (stable)
# Alert: < 0.7 (unstable)
```

**How to Measure**:
```python
import shap

# This week's importance
current_shap = calculate_shap_importance(current_model, recent_data)

# Last week's importance
previous_shap = load_previous_shap_values()

# Correlation
correlation = np.corrcoef(current_shap, previous_shap)[0, 1]

if correlation < 0.7:
    logger.warning("feature_importance_unstable", correlation=correlation)
```

**Dashboard Chart**: Line chart
- X-axis: Feature
- Y-axis: SHAP importance
- Multiple lines: This week, last week, 2 weeks ago

---

### Prediction Calibration

**What**: Does 80% confidence = 80% accuracy?

**Why**: Confidence should match actual performance

**Metric Definition**:
```python
# Calibration curve
# For predictions with confidence 0.8-0.9:
# What % are within ±15% of actual?
actual_accuracy = calculate_accuracy(
    predictions_with_confidence_0.8_to_0.9
)

# Well-calibrated if actual ≈ 0.85
```

**How to Measure**:
```python
def calculate_calibration_curve(predictions):
    """Calculate calibration curve."""
    
    # Bin by confidence
    bins = np.linspace(0, 1, 11)  # 0-10%, 10-20%, ..., 90-100%
    
    calibration = []
    for i in range(len(bins) - 1):
        low, high = bins[i], bins[i+1]
        
        # Predictions in this confidence bin
        mask = (predictions['confidence'] >= low) & (predictions['confidence'] < high)
        subset = predictions[mask]
        
        if len(subset) > 0:
            # What % are actually correct?
            actual_accuracy = (
                abs(subset['predicted'] - subset['actual']) / subset['actual'] < 0.15
            ).mean()
            
            expected_confidence = (low + high) / 2
            
            calibration.append({
                'expected': expected_confidence,
                'actual': actual_accuracy,
                'count': len(subset)
            })
    
    return calibration
```

**Dashboard Chart**: Scatter plot
- X-axis: Predicted confidence
- Y-axis: Actual accuracy
- Diagonal line: Perfect calibration
- Points: Actual calibration

---

### Training Data Freshness

**What**: Age of most recent training data

**Why**: Stale data = stale predictions

**Metric Definition**:
```python
data_age_days = (
    datetime.now() - most_recent_training_record.date
).days

# Target: < 30 days
# Alert: > 60 days
```

**How to Measure**:
```sql
SELECT 
    MAX(created_at) as most_recent_data,
    EXTRACT(DAY FROM NOW() - MAX(created_at)) as data_age_days
FROM cost_records
WHERE used_for_training = TRUE;
```

**Dashboard Chart**: Single stat with color
- Green: < 30 days
- Yellow: 30-60 days
- Red: > 60 days

---

## Data Quality Metrics

### Data Completeness

**What**: % of required fields populated

**Why**: Missing data = poor predictions

**Metric Definition**:
```python
completeness = (
    non_null_fields / total_required_fields
) * 100

# Target: > 95%
# Alert: < 90%
```

**How to Measure**:
```sql
SELECT 
    COUNT(*) as total_records,
    
    -- Required fields
    SUM(CASE WHEN total_cost IS NOT NULL THEN 1 ELSE 0 END) as has_total_cost,
    SUM(CASE WHEN drivers IS NOT NULL AND drivers != '{}' THEN 1 ELSE 0 END) as has_drivers,
    
    -- Completeness %
    (SUM(CASE WHEN total_cost IS NOT NULL THEN 1 ELSE 0 END)::float / COUNT(*) * 100) as total_cost_completeness,
    (SUM(CASE WHEN drivers IS NOT NULL AND drivers != '{}' THEN 1 ELSE 0 END)::float / COUNT(*) * 100) as drivers_completeness
    
FROM cost_records
WHERE created_at > NOW() - INTERVAL '30 days';
```

**Dashboard Chart**: Horizontal bar chart
- Bars: Required fields
- Value: % complete
- Threshold line: 95%

---

### Data Accuracy (Audit Sample)

**What**: % of records matching manual audit

**Why**: Validates automated extraction

**Metric Definition**:
```python
# Manual audit of sample
accuracy = (
    correct_records / audited_records
) * 100

# Target: > 90%
# Process: Audit 100 random records weekly
```

**How to Measure**:
```python
async def audit_data_quality(sample_size: int = 100):
    """Manual audit of randomly selected records."""
    
    # Random sample
    records = await db.execute(
        select(cost_records)
        .order_by(func.random())
        .limit(sample_size)
    )
    
    audit_results = []
    for record in records:
        # Manual review (human checks PDF vs. database)
        is_correct = await human_audit(record)
        audit_results.append(is_correct)
    
    accuracy = sum(audit_results) / len(audit_results) * 100
    
    await log_metric("data_accuracy_pct", accuracy)
    
    return accuracy
```

**Dashboard Chart**: Single stat + trend
- Big number: Current accuracy %
- Trend: Last 12 weeks
- Target: 90%

---

### Data Freshness

**What**: Time since last data ingestion

**Why**: Stale data = outdated intelligence

**Metric Definition**:
```python
freshness_minutes = (
    datetime.now() - last_record.created_at
).total_seconds() / 60

# Target: < 60 minutes
# Alert: > 120 minutes
```

**How to Measure**:
```sql
SELECT 
    MAX(created_at) as most_recent_record,
    EXTRACT(EPOCH FROM (NOW() - MAX(created_at))) / 60 as minutes_since_last
FROM cost_records;
```

**Dashboard Chart**: Gauge
- Range: 0-180 minutes
- Zones:
  - 0-60: Green (fresh)
  - 60-120: Yellow (aging)
  - 120+: Red (stale)

---

### Data Validation Failure Rate

**What**: % of records failing validation

**Why**: High failure rate = data quality issues

**Metric Definition**:
```python
validation_failure_rate = (
    failed_validations / total_records
) * 100

# Target: < 5%
# Alert: > 10%
```

**How to Measure**:
```python
from pydantic import ValidationError

validation_failures = Counter(
    'data_validation_failures_total',
    'Data validation failures',
    ['validation_rule']
)

async def ingest_record(raw_data: dict):
    try:
        # Validate
        record = CostRecord(**raw_data)
        await db.insert(record)
    
    except ValidationError as e:
        # Track failure
        for error in e.errors():
            validation_failures.labels(
                validation_rule=error['loc'][0]
            ).inc()
        
        # Quarantine
        await quarantine(raw_data, reason=str(e))
```

**Dashboard Chart**: Bar chart
- X-axis: Validation rule
- Y-axis: Failure count
- Sort: By count DESC

---

## Operational Metrics

### System Resource Usage

**What**: CPU, memory, disk usage

**Why**: Prevents capacity issues

**Metric Definition**:
```python
cpu_usage_pct: float  # 0-100%
memory_usage_pct: float  # 0-100%
disk_usage_pct: float  # 0-100%

# Alerts:
# CPU > 80%
# Memory > 85%
# Disk > 80%
```

**How to Measure**:
```python
from prometheus_client import Gauge

cpu_usage = Gauge('system_cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('system_memory_usage_percent', 'Memory usage percentage')
disk_usage = Gauge('system_disk_usage_percent', 'Disk usage percentage')

import psutil

@scheduler.scheduled_job('interval', seconds=30)
def collect_system_metrics():
    cpu_usage.set(psutil.cpu_percent())
    memory_usage.set(psutil.virtual_memory().percent)
    disk_usage.set(psutil.disk_usage('/').percent)
```

**Dashboard Chart**: Three gauges
- CPU, Memory, Disk
- Color zones: Green (0-70%), Yellow (70-85%), Red (85-100%)

---

### Cache Hit Rate

**What**: % of requests served from cache

**Why**: High hit rate = fast responses, low cost

**Metric Definition**:
```python
cache_hit_rate = (
    cache_hits / (cache_hits + cache_misses)
) * 100

# Target: > 80%
```

**How to Measure**:
```python
from prometheus_client import Counter

cache_hits = Counter('cache_hits_total', 'Cache hits')
cache_misses = Counter('cache_misses_total', 'Cache misses')

async def get_prediction(spec: SignSpec):
    cache_key = f"prediction:{spec.hash()}"
    
    # Try cache
    cached = await redis.get(cache_key)
    if cached:
        cache_hits.inc()
        return CostPrediction.parse_raw(cached)
    
    # Cache miss
    cache_misses.inc()
    
    # Compute
    prediction = await compute_prediction(spec)
    
    # Store in cache
    await redis.set(cache_key, prediction.json(), ex=3600)
    
    return prediction
```

**Dashboard Chart**: Line chart over time
- X-axis: Time
- Y-axis: Hit rate %
- Target line: 80%

---

### Queue Depth

**What**: Number of background jobs waiting

**Why**: High queue = backlog, slow processing

**Metric Definition**:
```python
queue_depth = count(jobs_in_queue)

# Target: < 100
# Alert: > 500
```

**How to Measure**:
```python
from prometheus_client import Gauge

queue_depth_gauge = Gauge(
    'background_queue_depth',
    'Number of jobs in queue',
    ['queue_name']
)

# Update gauge
@scheduler.scheduled_job('interval', seconds=60)
async def monitor_queues():
    for queue_name in ['predictions', 'training', 'exports']:
        depth = await get_queue_depth(queue_name)
        queue_depth_gauge.labels(queue_name=queue_name).set(depth)
```

**Dashboard Chart**: Stacked area chart
- X-axis: Time
- Y-axis: Queue depth
- Areas: Different queues (predictions, training, etc.)

---

## Cost Metrics

### Infrastructure Cost

**What**: Monthly cloud/infrastructure spend

**Why**: Track operational costs

**Metric Definition**:
```python
monthly_cost = sum([
    postgres_cost,
    redis_cost,
    compute_cost,
    storage_cost,
    network_cost
])

# Track trend, optimize if increasing
```

**How to Measure**:
```python
# For Docker/on-prem: Allocated resources × unit cost
# For cloud: AWS/GCP billing API

costs = {
    "postgres": {
        "cpu_cores": 2,
        "memory_gb": 8,
        "storage_gb": 100,
        "monthly_cost": 45.00
    },
    "redis": {
        "memory_gb": 4,
        "monthly_cost": 20.00
    },
    "compute": {
        "instances": 3,
        "monthly_cost_per_instance": 30.00,
        "monthly_cost": 90.00
    }
}

total_monthly = sum(c["monthly_cost"] for c in costs.values())
```

**Dashboard Chart**: Stacked bar chart by month
- X-axis: Month
- Y-axis: Cost ($)
- Segments: Database, Cache, Compute, Storage

---

### Cost Per Prediction

**What**: Infrastructure cost / predictions served

**Why**: Unit economics

**Metric Definition**:
```python
cost_per_prediction = monthly_infrastructure_cost / monthly_predictions

# Target: < $0.10/prediction
```

**How to Measure**:
```python
monthly_cost = 200.00  # Infrastructure
monthly_predictions = 5000

cost_per_prediction = monthly_cost / monthly_predictions
# = $0.04/prediction
```

**Dashboard Chart**: Line chart
- X-axis: Month
- Y-axis: $/prediction
- Trend: Should decrease over time (economies of scale)

---

## Dashboards & Alerts

### Primary Dashboard: Business Health

**Audience**: Brady, management

**Metrics**:
1. Predictions today (big number)
2. Accuracy trend (MAPE) (line chart)
3. Time saved this week (hours) (big number)
4. Revenue protected this month (dollars) (big number)
5. User adoption rate (gauge)
6. Top cost drivers (bar chart)

**Refresh**: Real-time (30s)

---

### Engineering Dashboard: System Health

**Audience**: Development team

**Metrics**:
1. API latency p95 (line chart)
2. Error rate (line chart)
3. Database performance (table of slow queries)
4. Cache hit rate (line chart)
5. System resources (CPU/memory/disk gauges)
6. Deployment frequency (bar chart)

**Refresh**: Real-time (10s)

---

### ML Dashboard: Model Health

**Audience**: ML engineers

**Metrics**:
1. Model accuracy (R², MAPE) (big numbers)
2. Confidence distribution (pie chart)
3. Feature importance (bar chart)
4. Data drift detection (heatmap)
5. Prediction calibration (scatter plot)
6. Training data freshness (single stat)

**Refresh**: Hourly

---

### Alert Configuration

```yaml
alerts:
  # Business-critical
  - name: high_prediction_error
    condition: mape > 20
    severity: critical
    channel: telegram
    message: "⚠️ Model accuracy degraded: MAPE {mape}%"
  
  - name: service_down
    condition: health_check_failed
    severity: critical
    channel: telegram + pagerduty
    message: "🚨 API DOWN - immediate action required"
  
  # Important
  - name: slow_api
    condition: p95_latency > 1000ms
    severity: warning
    channel: telegram
    message: "⚠️ API slow: p95 {latency}ms"
  
  - name: low_confidence_predictions
    condition: pct_low_confidence > 30
    severity: warning
    channel: slack
    message: "📊 {pct}% predictions have low confidence"
  
  # Operational
  - name: disk_space_low
    condition: disk_usage > 80%
    severity: warning
    channel: slack
    message: "💾 Disk usage {usage}% - archival needed"
  
  - name: data_pipeline_stale
    condition: data_age > 120min
    severity: warning
    channel: slack
    message: "⏰ Data pipeline stale: {age} min since last record"
```

---

### Metric Collection Strategy

**1. Application Metrics** (Prometheus)
```python
# Instrument code directly
from prometheus_client import Counter, Histogram, Gauge

predictions_total = Counter(...)
api_latency = Histogram(...)
```

**2. Database Metrics** (PostgreSQL + Prometheus exporter)
```bash
# postgres_exporter
docker run -d \
  -e DATA_SOURCE_NAME="postgresql://..." \
  -p 9187:9187 \
  prometheuscommunity/postgres-exporter
```

**3. System Metrics** (node_exporter)
```bash
# Collect OS-level metrics
docker run -d \
  -p 9100:9100 \
  prom/node-exporter
```

**4. Custom Business Metrics** (Scheduled jobs)
```python
@scheduler.scheduled_job('cron', hour='*/1')  # Hourly
async def collect_business_metrics():
    # Calculate MAPE
    mape = await calculate_mape()
    await push_metric("cost_prediction_mape", mape)
    
    # Calculate time savings
    time_saved = await calculate_time_savings()
    await push_metric("automation_hours_saved", time_saved)
```

---

### Visualization Tools

**Grafana**: Primary dashboards
- Connect to Prometheus data source
- Pre-built dashboard JSON configs
- Alerting via Telegram/Slack

**Jupyter Notebooks**: Deep analysis
- Ad-hoc queries
- Statistical analysis
- Model debugging

**MLflow UI**: Experiment tracking
- Model performance comparison
- Hyperparameter tuning results
- SHAP visualizations

---

*"In God we trust. All others must bring data." - W. Edwards Deming*

Measure everything. Improve continuously.

