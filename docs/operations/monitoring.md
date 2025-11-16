# Monitoring & Metrics Guide

Complete guide to monitoring SIGN X Studio Clone with Prometheus.

## Overview

The API exposes Prometheus metrics at `/metrics`. All metrics are prefixed with `apex_` for namespacing.

## Metrics Endpoint

```bash
curl http://localhost:8000/metrics
```

## Available Metrics

### HTTP Metrics (Auto-generated)

These are automatically provided by `prometheus-fastapi-instrumentator`:

#### Request Counters

- `http_requests_total{method, status, endpoint}` - Total HTTP requests
- `http_request_size_bytes{method, endpoint}` - Request size distribution
- `http_response_size_bytes{method, status, endpoint}` - Response size distribution

#### Request Duration

- `http_request_duration_seconds{method, status, endpoint}` - Request latency histogram

**Example:**
```prometheus
http_requests_total{method="POST",status="200",endpoint="/projects"} 42
http_request_duration_seconds_bucket{method="POST",endpoint="/projects",le="0.1"} 35
```

### Application Metrics

#### Abstain Responses

- `apex_abstain_total` - Count of abstain responses (low confidence)

```prometheus
# TYPE apex_abstain_total counter
apex_abstain_total 5
```

#### Materials Gateway

- `apex_materials_requests_total{status}` - Materials gateway requests by status
- `apex_materials_normalized_weights_total` - Requests where weights were normalized
- `apex_materials_imputed_qualitative_total` - Requests where qualitative was imputed

```prometheus
apex_materials_requests_total{status="200"} 120
apex_materials_normalized_weights_total 8
```

#### Celery Queue

- `apex_celery_queue_depth` - Depth of Celery default queue

```prometheus
# TYPE apex_celery_queue_depth gauge
apex_celery_queue_depth 3
```

#### Database Pool

- `apex_pg_pool_used` - Number of used connections in PostgreSQL pool

```prometheus
# TYPE apex_pg_pool_used gauge
apex_pg_pool_used 2
```

#### Cache Hit Ratio

- `apex_cache_hit_ratio` - Cache hit ratio (0-1), -1 if unknown

```prometheus
# TYPE apex_cache_hit_ratio gauge
apex_cache_hit_ratio 0.85
```

## Custom Transaction Metrics

### Database Transaction Metrics

**Status**: To be implemented (see [Transaction Metrics Stub](#transaction-metrics-stub))

Planned metrics:
- `apex_db_transactions_total{operation, status}` - Total transactions
- `apex_db_transaction_duration_seconds{operation}` - Transaction duration
- `apex_db_transaction_failures_total{operation}` - Transaction failures
- `apex_db_rollbacks_total{operation}` - Rollback count

### Search Metrics

**Status**: To be implemented

Planned metrics:
- `apex_search_requests_total{index}` - Search requests
- `apex_search_failures_total{index}` - Search failures
- `apex_search_fallback_total` - DB fallback count
- `apex_search_duration_seconds{index}` - Search latency

## Prometheus Configuration

### Basic Scrape Config

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'apex-api'
    scrape_interval: 15s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8000']
        labels:
          service: 'api'
          environment: 'production'
```

### Docker Compose Integration

If using Docker Compose with Prometheus:

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    ports:
      - "9090:9090"
```

## Grafana Dashboards

### Recommended Dashboards

1. **API Performance Dashboard**
   - Request rate (requests/sec)
   - Request latency (p50, p95, p99)
   - Error rate (4xx, 5xx)
   - Endpoint breakdown

2. **Database Dashboard**
   - Transaction rate
   - Transaction duration
   - Connection pool usage
   - Rollback rate

3. **Celery Dashboard**
   - Queue depth
   - Task completion rate
   - Task failures
   - Worker availability

4. **System Dashboard**
   - Cache hit ratio
   - Search performance
   - Service health

### Sample Queries

#### Request Rate

```promql
rate(http_requests_total[5m])
```

#### Error Rate

```promql
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

#### P95 Latency

```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

#### Celery Queue Depth

```promql
apex_celery_queue_depth
```

## Alerts

### Recommended Alerts

#### High Error Rate

```yaml
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
  for: 5m
  annotations:
    summary: "High error rate detected"
    description: "Error rate is {{ $value }}"
```

#### High Latency

```yaml
- alert: HighLatency
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
  for: 5m
  annotations:
    summary: "High API latency"
    description: "P95 latency is {{ $value }}s"
```

#### Database Pool Exhaustion

```yaml
- alert: DatabasePoolExhaustion
  expr: apex_pg_pool_used > 8
  for: 2m
  annotations:
    summary: "Database pool nearly exhausted"
```

#### Celery Queue Backlog

```yaml
- alert: CeleryQueueBacklog
  expr: apex_celery_queue_depth > 100
  for: 5m
  annotations:
    summary: "Celery queue backlog"
    description: "Queue depth: {{ $value }}"
```

## Logging

### Structured Logs

All logs use structured logging with `structlog`:

```json
{
  "event": "project.created",
  "project_id": "proj_abc123",
  "timestamp": "2025-01-01T00:00:00Z",
  "level": "info"
}
```

### Log Levels

- `DEBUG` - Detailed diagnostic information
- `INFO` - General informational messages
- `WARNING` - Warning messages (non-critical)
- `ERROR` - Error messages (recoverable)
- `CRITICAL` - Critical errors (unrecoverable)

### Log Aggregation

Logs can be exported to:
- **Stdout** (default)
- **OpenTelemetry** (via `OTEL_EXPORTER`)

## Transaction Metrics Stub

**Location**: `services/api/src/apex/api/metrics.py`

To implement transaction metrics, add:

```python
from prometheus_client import Counter, Histogram

DB_TRANSACTIONS_TOTAL = Counter(
    "apex_db_transactions_total",
    "Total database transactions",
    labelnames=("operation", "status")
)

DB_TRANSACTION_DURATION = Histogram(
    "apex_db_transaction_duration_seconds",
    "Database transaction duration",
    labelnames=("operation",)
)

DB_TRANSACTION_FAILURES = Counter(
    "apex_db_transaction_failures_total",
    "Failed database transactions",
    labelnames=("operation",)
)

DB_ROLLBACKS_TOTAL = Counter(
    "apex_db_rollbacks_total",
    "Database transaction rollbacks",
    labelnames=("operation",)
)
```

Then instrument the transaction decorator in `common/transactions.py`:

```python
from ..metrics import (
    DB_TRANSACTIONS_TOTAL,
    DB_TRANSACTION_DURATION,
    DB_TRANSACTION_FAILURES,
    DB_ROLLBACKS_TOTAL,
)

@asynccontextmanager
async def transaction(db: AsyncSession):
    operation = "unknown"  # Extract from context
    with DB_TRANSACTION_DURATION.labels(operation=operation).time():
        try:
            yield db
            await db.commit()
            DB_TRANSACTIONS_TOTAL.labels(operation=operation, status="success").inc()
        except Exception as e:
            await db.rollback()
            DB_ROLLBACKS_TOTAL.labels(operation=operation).inc()
            DB_TRANSACTIONS_TOTAL.labels(operation=operation, status="failure").inc()
            DB_TRANSACTION_FAILURES.labels(operation=operation).inc()
            raise
```

## Monitoring Checklist

- [ ] Prometheus scraping API metrics
- [ ] Grafana dashboards configured
- [ ] Alerts configured and tested
- [ ] Log aggregation set up
- [ ] Transaction metrics implemented
- [ ] Search metrics implemented
- [ ] SLO/SLI definitions documented

