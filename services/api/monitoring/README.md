# APEX Database Monitoring

## Setup

### 1. Prometheus Postgres Exporter

```bash
# Already configured in compose.yaml
docker compose -f ../../infra/compose.yaml up -d postgres_exporter

# Verify metrics endpoint
curl http://localhost:9187/metrics | grep postgres
```

### 2. Grafana Dashboard

```bash
# Access dashboard
open http://localhost:3001

# Login: admin/admin (change in production!)
```

### 3. Key Metrics

- **Slow Queries**: Top 10 from `pg_stat_statements` (>100ms)
- **Index Hit Rate**: Should be >95% for good performance
- **Connection Pool**: Active, idle, waiting connections
- **Query Timeouts**: Statement timeouts (30s limit)

### 4. Materialized View Refresh

```bash
# Add to cron (every 5 minutes)
*/5 * * * * docker compose -f ../../infra/compose.yaml exec db psql -U apex apex -f /backups/refresh_stats_view.sql
```

## Alerting (Future)

Set alerts on:
- Index hit rate <90%
- Query count >1000/min
- Avg query time >100ms
- Connection pool >80% usage

