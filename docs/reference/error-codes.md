# Error Codes Reference

Complete reference for API error handling.

## HTTP Status Codes

| Code | Status | Meaning | Retryable |
|------|--------|---------|-----------|
| 200 | OK | Success | No |
| 201 | Created | Resource created | No |
| 400 | Bad Request | Invalid request | No |
| 404 | Not Found | Resource not found | No |
| 412 | Precondition Failed | ETag mismatch or invalid transition | No |
| 422 | Unprocessable Entity | Validation error | No |
| 429 | Too Many Requests | Rate limit exceeded | Yes |
| 500 | Internal Server Error | Server error | Yes |

## Error Response Format

All errors return the standard envelope:

```json
{
  "result": null,
  "assumptions": ["Error description"],
  "confidence": 0.1,
  "trace": {
    "data": {
      "error_id": "error-abc123",
      "error_type": "HTTPException",
      "path": "/projects/invalid",
      "method": "GET"
    },
    ...
  }
}
```

## Error Headers

Error responses include headers:

- `X-Error-ID`: Unique error identifier
- `X-Trace-ID`: Request trace identifier

```bash
curl -v http://localhost:8000/projects/invalid

# Response headers:
# X-Error-ID: error-abc123
# X-Trace-ID: trace-xyz789
```

## Common Errors

### 400 Bad Request

**Cause**: Malformed request

**Example:**
```json
{
  "result": null,
  "assumptions": ["Invalid request format"],
  "confidence": 0.1
}
```

**Solution**: Check request body format

### 404 Not Found

**Cause**: Resource doesn't exist

**Example:**
```bash
curl http://localhost:8000/projects/nonexistent
```

**Response:**
```json
{
  "result": null,
  "assumptions": ["Project not found"],
  "confidence": 0.1
}
```

**Solution**: Verify resource ID

### 412 Precondition Failed

**Cause**: ETag mismatch or invalid state transition

**Example:**
```bash
curl -X PUT http://localhost:8000/projects/proj_abc123 \
  -H "If-Match: wrong-etag" \
  -d '{"name": "Updated"}'
```

**Response:**
```json
{
  "result": null,
  "assumptions": ["ETag mismatch"],
  "confidence": 0.1
}
```

**Solution**: 
1. Re-fetch resource to get current ETag
2. Retry update with correct ETag

**State Transition Error:**
```json
{
  "result": null,
  "assumptions": ["Invalid state transition: submitted → draft"],
  "confidence": 0.1
}
```

### 422 Unprocessable Entity

**Cause**: Validation error

**Example:**
```bash
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{}'  # Missing required fields
```

**Response:**
```json
{
  "result": null,
  "assumptions": ["Validation error: name is required"],
  "confidence": 0.1,
  "trace": {
    "data": {
      "validation_errors": [
        {
          "field": "name",
          "message": "Field required"
        }
      ]
    }
  }
}
```

**Solution**: Fix validation errors in request

### 429 Too Many Requests

**Cause**: Rate limit exceeded

**Response:**
```json
{
  "result": null,
  "assumptions": ["Rate limit exceeded"],
  "confidence": 0.1
}
```

**Headers:**
```
Retry-After: 60
```

**Solution**: Wait for Retry-After seconds

### 500 Internal Server Error

**Cause**: Unexpected server error

**Response:**
```json
{
  "result": null,
  "assumptions": ["An unexpected error occurred. The service abstains."],
  "confidence": 0.1,
  "trace": {
    "data": {
      "error_id": "error-abc123",
      "error_type": "ValueError"
    }
  }
}
```

**Solution**: 
1. Check error_id in logs
2. Contact support with error_id
3. Retry if transient error

## Error Types

### ValidationError

**HTTP**: 422  
**Cause**: Input validation failed

```json
{
  "error_type": "ValidationError",
  "validation_errors": [...]
}
```

### NotFoundError

**HTTP**: 404  
**Cause**: Resource not found

```json
{
  "error_type": "NotFoundError",
  "resource_type": "project",
  "resource_id": "proj_abc123"
}
```

### PreconditionFailedError

**HTTP**: 412  
**Cause**: ETag or state transition failed

```json
{
  "error_type": "PreconditionFailedError",
  "reason": "ETag mismatch"
}
```

### RateLimitError

**HTTP**: 429  
**Cause**: Rate limit exceeded

```json
{
  "error_type": "RateLimitError",
  "limit": 60,
  "window": "minute"
}
```

### InternalServerError

**HTTP**: 500  
**Cause**: Unexpected error

```json
{
  "error_type": "InternalServerError",
  "error_id": "error-abc123"
}
```

## Error Handling

### Client-Side Handling

```python
import httpx

try:
    response = httpx.post("http://localhost:8000/projects", json=data)
    response.raise_for_status()
    result = response.json()["result"]
except httpx.HTTPStatusError as e:
    if e.response.status_code == 422:
        errors = e.response.json()["trace"]["data"].get("validation_errors", [])
        # Handle validation errors
    elif e.response.status_code == 429:
        retry_after = e.response.headers.get("Retry-After")
        # Wait and retry
    else:
        error_id = e.response.headers.get("X-Error-ID")
        # Log error_id for support
```

### Retry Logic

For retryable errors (429, 500):

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_status_code(429, 500)
)
def api_call():
    ...
```

## Error Monitoring

### Logs

All errors are logged with:

- Error ID
- Trace ID
- Error type
- Stack trace
- Request context

```json
{
  "event": "error",
  "error_id": "error-abc123",
  "trace_id": "trace-xyz789",
  "error_type": "ValueError",
  "error_message": "Invalid value",
  "path": "/projects/proj_abc123",
  "method": "POST"
}
```

### Metrics

Error metrics in Prometheus:

```prometheus
# Error rate by status code
rate(http_requests_total{status=~"4..|5.."}[5m])

# Error rate by endpoint
rate(http_requests_total{status=~"5..",endpoint="/projects"}[5m])
```

## Troubleshooting

### Common Issues

1. **429 Rate Limit**
   - Reduce request rate
   - Use Retry-After header
   - Request rate limit increase

2. **422 Validation Errors**
   - Check request schema
   - Verify required fields
   - Validate data types

3. **412 Precondition Failed**
   - Re-fetch resource
   - Use correct ETag
   - Check state machine rules

4. **500 Internal Error**
   - Check error_id in logs
   - Verify service health
   - Check dependencies

## Next Steps

- [**API Endpoints**](api-endpoints.md) - See error handling in endpoints
- [**Troubleshooting Guide**](../operations/troubleshooting.md) - Common issues

