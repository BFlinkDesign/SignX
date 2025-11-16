# Error Codes Reference

Complete reference for all error codes in SIGN X Studio Clone.

## HTTP Status Codes

### 200 OK

**Description**: Request successful  
**Use Cases**: GET, PUT, POST (successful)  
**Example Response**:
```json
{
  "data": {...},
  "confidence": 0.95
}
```

### 201 Created

**Description**: Resource created successfully  
**Use Cases**: POST (create)  
**Example Response**:
```json
{
  "data": {
    "project_id": "proj_123",
    "status": "draft"
  }
}
```

### 304 Not Modified

**Description**: Resource not modified (ETag match)  
**Use Cases**: GET with If-None-Match header  
**Resolution**: Use cached response

### 400 Bad Request

**Description**: Invalid request  
**Common Causes**:
- Missing required fields
- Invalid data format
- Malformed JSON

**Example Response**:
```json
{
  "confidence": 0.0,
  "assumptions": ["Validation error: name is required"],
  "trace": {
    "validation_errors": [
      {
        "field": "name",
        "message": "Field required"
      }
    ]
  },
  "data": null
}
```

**Resolution**: Fix request format, include required fields

### 401 Unauthorized

**Description**: Authentication required  
**Common Causes**:
- Missing API key
- Invalid API key
- Expired token

**Example Response**:
```json
{
  "error": "Unauthorized",
  "detail": "Invalid API key"
}
```

**Resolution**: Provide valid API key or token

### 403 Forbidden

**Description**: Access denied  
**Common Causes**:
- Insufficient permissions
- Resource access denied
- Presigned URL expired

**Example Response**:
```json
{
  "error": "Forbidden",
  "detail": "Insufficient permissions"
}
```

**Resolution**: Request appropriate permissions or new URL

### 404 Not Found

**Description**: Resource not found  
**Common Causes**:
- Invalid project ID
- Resource doesn't exist
- Wrong endpoint

**Example Response**:
```json
{
  "error": "Not Found",
  "detail": "Project not found: proj_123"
}
```

**Resolution**: Verify resource ID, check endpoint

### 409 Conflict

**Description**: Resource conflict  
**Common Causes**:
- Duplicate resource
- State conflict
- Concurrent modification

**Example Response**:
```json
{
  "error": "Conflict",
  "detail": "Project already exists"
}
```

**Resolution**: Use different identifier or resolve conflict

### 412 Precondition Failed

**Description**: ETag mismatch (optimistic locking)  
**Common Causes**:
- Concurrent update
- Stale ETag

**Example Response**:
```json
{
  "error": "Precondition Failed",
  "detail": "ETag mismatch. Current ETag: xyz789"
}
```

**Resolution**: Get current resource, retry with updated ETag

### 422 Unprocessable Entity

**Description**: Validation error  
**Common Causes**:
- Invalid input values
- Out of range
- Business rule violation

**Example Response**:
```json
{
  "confidence": 0.0,
  "assumptions": ["Invalid input: height_ft must be between 10 and 50"],
  "trace": {
    "validation_errors": [
      {
        "field": "height_ft",
        "message": "Must be between 10 and 50 feet"
      }
    ]
  },
  "data": null
}
```

**Resolution**: Fix input values, verify ranges

### 429 Too Many Requests

**Description**: Rate limit exceeded  
**Common Causes**:
- Too many requests
- Burst limit exceeded

**Example Response**:
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

**Resolution**: Wait for retry_after seconds, reduce request rate

### 500 Internal Server Error

**Description**: Server error  
**Common Causes**:
- Application error
- Database error
- System failure

**Example Response**:
```json
{
  "error": "Internal Server Error",
  "detail": "An unexpected error occurred",
  "error_id": "err_abc123"
}
```

**Resolution**: Contact support with error_id

### 503 Service Unavailable

**Description**: Service temporarily unavailable  
**Common Causes**:
- Maintenance mode
- System overload
- Dependency failure

**Example Response**:
```json
{
  "error": "Service Unavailable",
  "detail": "Service temporarily unavailable",
  "retry_after": 300
}
```

**Resolution**: Wait and retry, check status page

## Validation Errors

### VAL_001: Field Required

**Description**: Required field missing  
**Example**:
```json
{
  "field": "name",
  "message": "Field required"
}
```

**Resolution**: Include required field in request

### VAL_002: Field Too Long

**Description**: Field exceeds maximum length  
**Example**:
```json
{
  "field": "name",
  "message": "Field exceeds maximum length of 255 characters"
}
```

**Resolution**: Reduce field length

### VAL_003: Invalid Format

**Description**: Field format invalid  
**Example**:
```json
{
  "field": "email",
  "message": "Invalid email format"
}
```

**Resolution**: Fix field format

### VAL_004: Out of Range

**Description**: Value outside valid range  
**Example**:
```json
{
  "field": "height_ft",
  "message": "Must be between 10 and 50 feet"
}
```

**Resolution**: Adjust value to valid range

## Solver Errors

### SOLV_001: No Feasible Solution

**Description**: No feasible poles found  
**Example Response**:
```json
{
  "confidence": 0.3,
  "assumptions": [
    "Cannot solve: No feasible poles for given loads",
    "Consider increasing pole height or reducing loads"
  ],
  "data": {
    "options": [],
    "recommended": null
  }
}
```

**Resolution**: Adjust inputs (reduce loads, increase height)

### SOLV_002: Invalid Input

**Description**: Invalid solver input  
**Example Response**:
```json
{
  "confidence": 0.0,
  "assumptions": ["Invalid input: diameter_ft must be positive"],
  "data": null
}
```

**Resolution**: Fix input values

### SOLV_003: Convergence Failed

**Description**: Solver didn't converge  
**Example Response**:
```json
{
  "confidence": 0.5,
  "assumptions": ["Solver convergence failed, using approximate solution"],
  "data": {...}
}
```

**Resolution**: Results approximate, consider engineering review

## System Errors

### SYS_001: Database Connection Failed

**Description**: Database unavailable  
**Resolution**: System will auto-recover, retry request

### SYS_002: Cache Unavailable

**Description**: Cache service down  
**Resolution**: System continues with degraded performance, retry request

### SYS_003: Storage Full

**Description**: Storage quota exceeded  
**Resolution**: Contact support to expand storage

## Task Errors

### TASK_001: Task Not Found

**Description**: Task ID invalid  
**Resolution**: Verify task ID, check task status endpoint

### TASK_002: Task Failed

**Description**: Task execution failed  
**Example Response**:
```json
{
  "data": {
    "task_id": "task_123",
    "status": "failed",
    "error": "Report generation failed: timeout"
  }
}
```

**Resolution**: Retry task or contact support

### TASK_003: Task Timeout

**Description**: Task exceeded timeout  
**Resolution**: Task cancelled, retry or contact support

## Error Response Format

All errors follow Envelope format:

```json
{
  "confidence": 0.0,
  "assumptions": ["Error description"],
  "trace": {
    "validation_errors": [...],
    "error_details": {...}
  },
  "data": null
}
```

## Error Handling Best Practices

### Client-Side

1. **Check HTTP Status**
   - 4xx: Client error (fix request)
   - 5xx: Server error (retry or contact support)

2. **Parse Error Response**
   - Check `assumptions` for details
   - Review `trace.validation_errors`
   - Display user-friendly message

3. **Retry Logic**
   - Retry on 5xx errors
   - Exponential backoff
   - Max 3 retries

### Server-Side

1. **Log Errors**
   - Include error_id
   - Include trace_id
   - Include full context

2. **Return Useful Messages**
   - User-friendly descriptions
   - Actionable guidance
   - Error IDs for support

---

**Related Documentation:**
- [**API Reference**](../api/api-reference.md) - Endpoint details
- [**Troubleshooting**](../operations/troubleshooting.md) - Issue resolution

