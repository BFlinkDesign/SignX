# CalcuSign Monitoring

Synthetic monitoring and uptime checks for CalcuSign API.

## Scripts

### `synthetic.py`
Runs key scenarios every 5 minutes:
- Health check
- Create project
- Derive cabinet
- Get pole options

**Usage**:
```bash
# Set API URL and webhook for alerts
export APEX_API_URL=http://localhost:8000
export MONITORING_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Run monitoring
python monitoring/synthetic.py
```

**Cron Setup**:
```cron
*/5 * * * * cd /path/to/calcusign && /usr/bin/python3 monitoring/synthetic.py >> /var/log/calcusign_monitoring.log 2>&1
```

### `uptime_check.py`
Continuous uptime monitoring: GET /health every 1 minute.

**Usage**:
```bash
export APEX_API_URL=http://localhost:8000
export UPTIME_CHECK_INTERVAL=60  # seconds

python monitoring/uptime_check.py
```

## Alerting

Alerts are sent to Slack/Discord webhooks when scenarios fail:
- Status code != 200
- Timeout errors
- Connection errors

## Metrics

Each check logs:
- Scenario name
- Status (success/failure/error)
- Status code
- Duration (ms)
- Timestamp

## Deployment

1. Install dependencies: `httpx`, `structlog`
2. Configure webhook URL
3. Set up cron job (for synthetic.py)
4. Run as systemd service (for uptime_check.py)

## Example Alert

```
⚠️ CalcuSign Monitoring Alert: 1 scenario(s) failed

• derive_cabinet: failure (status_code: 500)
```

