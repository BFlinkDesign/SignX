# API Integration Guide

Complete guide for integrating external APIs and services.

## Overview

SIGN X Studio Clone integrates with several external services:
- **Google Geocoding API** - Address geocoding
- **OpenWeatherMap** - Weather data
- **ASCE 7-16 Maps** - Wind speed lookup
- **PM Systems** - Project management (Smartsheet, Asana, etc.)
- **Email Services** - Notifications (SendGrid, SES)

## Site Resolution Integration

### Geocoding

The system uses geocoding to convert addresses to coordinates.

#### Google Geocoding API

**Setup:**
```bash
export GOOGLE_MAPS_API_KEY=your-api-key-here
```

**Usage:**
```bash
curl -X POST http://localhost:8000/signage/common/site/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "address": "123 Main St, Dallas, TX 75201"
  }'
```

**Response:**
```json
{
  "result": {
    "lat": 32.7767,
    "lon": -96.7970,
    "address_resolved": "123 Main St, Dallas, TX 75201, USA",
    "wind_speed_mph": 115.0,
    "source": "asce7"
  }
}
```

#### Fallback Providers

If Google API fails:
- Falls back to OpenStreetMap Nominatim
- Returns lower confidence
- Logs fallback event

### Wind Data Integration

#### ASCE 7-16 Map Lookup

**Primary Method:**
- Digitized ASCE 7-16 wind speed map
- Keyed by rounded `(lat, lon)`
- Deterministic results
- No API calls required

**Usage:**
```python
from apex.api.utils.wind_data import resolve_wind_speed

wind_data = await resolve_wind_speed(lat=32.7767, lon=-96.7970)
# Returns: {"wind_speed_mph": 115.0, "source": "asce7"}
```

#### OpenWeatherMap Fallback

**Setup:**
```bash
export OPENWEATHER_API_KEY=your-api-key-here
```

**Usage:**
- Only used when "live" flag set
- Caches results in Redis (TTL: 7 days)
- Fallback if ASCE map unavailable

**Configuration:**
```python
# In wind_data.py
USE_LIVE_WEATHER = os.getenv("USE_LIVE_WEATHER", "false").lower() == "true"
```

### Snow Load Data

Snow load lookup:

```python
from apex.api.utils.wind_data import fetch_snow_load

snow_load = fetch_snow_load(lat=32.7767, lon=-96.7970)
# Returns: 5.0 (psf) or None if unavailable
```

## Project Management Integration

### PM System Dispatch

Projects are dispatched to PM systems (Smartsheet, Asana, etc.) via Celery tasks.

#### Task Configuration

**Location**: `services/worker/src/apex/worker/tasks.py`

```python
@celery_app.task(name="projects.submit.dispatch", bind=True)
def dispatch_to_pm(self, project_id: str, project_data: dict, idempotency_key: str | None = None):
    # Dispatch to PM system
    ...
```

#### PM System Setup

**Environment Variables:**
```bash
APEX_PM_URL=http://pm-system.local/submit
APEX_PM_API_KEY=your-api-key
```

#### Task Execution

**Automatic Dispatch:**
```bash
# Submit project (automatically dispatches)
curl -X POST http://localhost:8000/projects/proj_abc123/submit \
  -H "Idempotency-Key: submit-123"
```

**What Happens:**
1. Project state: `estimating` → `submitted`
2. Celery task enqueued
3. Task dispatches to PM system
4. Project number assigned
5. Event logged

#### PM System Response

Expected PM system response:

```json
{
  "project_number": "PRJ-12345678",
  "pm_ref": "smartsheet-abc123",
  "status": "created"
}
```

#### Circuit Breaker

PM dispatch includes circuit breaker:
- **Failure threshold**: 3 consecutive failures
- **Circuit opens**: Stops dispatching
- **DLQ**: Failed payloads go to dead letter queue
- **Recovery**: Automatic after cooldown

**Monitoring:**
```prometheus
# Circuit breaker state
apex_pm_circuit_breaker_state{state="open"} 1

# PM dispatch failures
apex_pm_dispatch_failures_total 5
```

## Email Integration

### Email Notification

Email notifications sent via Celery tasks.

#### Task Configuration

**Location**: `services/worker/src/apex/worker/tasks.py`

```python
@celery_app.task(name="projects.email.send", bind=True)
def send_email(self, to: str, subject: str, template: str, context: dict):
    # Send email
    ...
```

#### Email Service Setup

**SendGrid:**
```bash
export SENDGRID_API_KEY=your-api-key
export APEX_EMAIL_URL=https://api.sendgrid.com/v3/mail/send
```

**AWS SES:**
```bash
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export APEX_EMAIL_URL=https://email.us-east-1.amazonaws.com
```

#### Email Templates

**Location**: `services/worker/src/apex/worker/templates/`

**Template Structure:**
```html
<!-- project_submitted.html -->
<h1>Project {{ project_name }} Submitted</h1>
<p>Project ID: {{ project_id }}</p>
<p>Project Number: {{ project_number }}</p>
```

#### Sending Emails

**Automatic (on submission):**
```bash
# Submit project (automatically sends email if manager_email available)
curl -X POST http://localhost:8000/projects/proj_abc123/submit
```

**Manual:**
```python
from apex.api.utils.celery_client import enqueue_email

task_id = enqueue_email(
    to="manager@example.com",
    subject="Project Submitted",
    template="project_submitted",
    context={"project_id": "proj_abc123", "project_name": "Main Street Sign"}
)
```

## OpenSearch Integration

### Indexing Projects

Projects automatically indexed in OpenSearch on create/update.

#### Automatic Indexing

```python
# In projects.py create_project()
await index_project(project_id, project_doc)
```

#### Search with Fallback

```python
from apex.api.utils.search import search_projects

# Try OpenSearch, fallback to DB
projects, used_fallback = await search_projects(query, db_fallback)
```

#### Fallback Behavior

If OpenSearch unavailable:
- Automatically falls back to database
- Response includes `search_fallback: true`
- Logs warning (not error)

**Monitoring:**
```prometheus
apex_search_fallback_total 3
apex_search_requests_total{status="success"} 120
```

## External Service Configuration

### Environment Variables

| Service | Variable | Description |
|---------|----------|-------------|
| Google Maps | `GOOGLE_MAPS_API_KEY` | Geocoding API key |
| OpenWeather | `OPENWEATHER_API_KEY` | Weather API key |
| PM System | `APEX_PM_URL` | PM system endpoint |
| Email | `APEX_EMAIL_URL` | Email service endpoint |
| SendGrid | `SENDGRID_API_KEY` | SendGrid API key |
| AWS SES | `AWS_ACCESS_KEY_ID` | AWS credentials |

### Service Health Checks

#### Check Service Availability

```bash
# Check geocoding
curl http://localhost:8000/signage/common/site/resolve \
  -H "Content-Type: application/json" \
  -d '{"address": "123 Main St, Dallas, TX"}'

# Check OpenSearch
curl http://localhost:8000/projects?q=test

# Check PM dispatch (via task status)
curl http://localhost:5555/api/tasks/projects.submit.dispatch  # Flower
```

## Error Handling

### Retry Logic

External service calls include retry logic:

```python
# Celery tasks
@celery_app.task(bind=True, max_retries=5, autoretry_for=(Exception,))
def external_service_call(self):
    # Auto-retries on failure
    ...
```

### Circuit Breakers

Circuit breakers protect against cascading failures:

```python
# PM dispatch circuit breaker
if not breaker_allow("pm"):
    dlq_push("pm", payload)
    raise Ignore()
```

### Abstain Responses

If external service fails:

```json
{
  "result": null,
  "assumptions": ["Geocoding failed; using default wind speed"],
  "confidence": 0.5,
  "trace": {
    "data": {
      "geocode_error": "API key invalid"
    }
  }
}
```

## Best Practices

### 1. API Key Management

- Store keys in environment variables
- Never commit keys to repository
- Rotate keys regularly
- Use separate keys for dev/prod

### 2. Caching

External API results are cached:
- Geocoding: 30 days
- Wind data: 7 days
- Cache key: `(lat, lon)` rounded

### 3. Fallback Handling

Always handle service failures:
- Provide fallback values
- Lower confidence scores
- Log fallback events
- Monitor fallback rates

### 4. Rate Limiting

Respect external API rate limits:
- Use caching to reduce calls
- Implement exponential backoff
- Monitor API usage

## Monitoring Integration

### Metrics

External service metrics:

```prometheus
# Geocoding
apex_geocode_requests_total{provider="google"} 100
apex_geocode_failures_total{provider="google"} 2

# PM Dispatch
apex_pm_dispatch_total{status="success"} 50
apex_pm_dispatch_failures_total 5

# Email
apex_email_sent_total{provider="sendgrid"} 30
apex_email_failures_total 1

# Search
apex_search_requests_total{index="projects"} 200
apex_search_fallback_total 5
```

### Alerts

Configure alerts for:
- High failure rates
- Circuit breaker opens
- Service unavailability
- Rate limit exceeded

## Next Steps

- [**Monitoring Guide**](../operations/monitoring.md) - Monitor integrations
- [**Troubleshooting**](../operations/troubleshooting.md) - Debug issues
- [**API Reference**](../reference/api-endpoints.md) - API details

