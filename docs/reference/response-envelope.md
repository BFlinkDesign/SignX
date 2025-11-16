# Response Envelope Schema

Complete reference for the API response envelope format.

## Overview

All API endpoints return a standardized envelope format:

```json
{
  "result": <response_data>,
  "assumptions": ["assumption1", "assumption2"],
  "confidence": 0.95,
  "trace": {
    "data": {
      "inputs": {},
      "intermediates": {},
      "outputs": {}
    },
    "code_version": {
      "git_sha": "abc123",
      "dirty": false,
      "build_id": "build-123"
    },
    "model_config": {
      "provider": "none",
      "model": "none",
      "temperature": 0.0,
      "max_tokens": 1024,
      "seed": null
    }
  }
}
```

## Fields

### `result`

The actual response data. Can be:
- Object (for single resources)
- Array (for lists)
- `null` (for errors or abstain responses)

**Example:**
```json
{
  "result": {
    "project_id": "proj_abc123",
    "name": "My Sign",
    "status": "draft"
  }
}
```

### `assumptions`

Array of strings describing assumptions made during processing.

**Example:**
```json
{
  "assumptions": [
    "soil_bearing=3000psf, K=calib_v1",
    "OpenSearch indexing deferred"
  ]
}
```

### `confidence`

Confidence score from 0.0 to 1.0:
- `1.0` - Highest confidence (deterministic calculation)
- `0.9-0.99` - High confidence
- `0.7-0.89` - Medium confidence
- `0.5-0.69` - Low confidence
- `0.0-0.49` - Very low confidence (abstain)

**Example:**
```json
{
  "confidence": 0.95
}
```

### `trace`

Traceability information.

#### `trace.data`

Inputs, intermediates, and outputs:

```json
{
  "inputs": {
    "diameter_ft": 3.0,
    "soil_psf": 3000.0
  },
  "intermediates": {
    "M_pole_kipft": 10.0,
    "volume_cf": 39.79
  },
  "outputs": {
    "min_depth_ft": 4.2,
    "concrete_yards": 1.47
  }
}
```

#### `trace.code_version`

Code version information:

```json
{
  "git_sha": "abc123def456",
  "dirty": false,
  "build_id": "build-123"
}
```

#### `trace.model_config`

Model configuration (for LLM-based operations):

```json
{
  "provider": "openai",
  "model": "gpt-4",
  "temperature": 0.0,
  "max_tokens": 1024,
  "seed": 42
}
```

## Success Response Example

```json
{
  "result": {
    "project_id": "proj_abc123",
    "name": "Main Street Sign",
    "status": "draft",
    "etag": "xyz789"
  },
  "assumptions": [
    "Created in draft status"
  ],
  "confidence": 0.95,
  "trace": {
    "data": {
      "inputs": {
        "account_id": "demo",
        "name": "Main Street Sign"
      },
      "intermediates": {
        "indexed": true
      },
      "outputs": {
        "project_id": "proj_abc123"
      }
    },
    "code_version": {
      "git_sha": "abc123",
      "dirty": false,
      "build_id": "build-123"
    },
    "model_config": {
      "provider": "none",
      "model": "none",
      "temperature": 0.0,
      "max_tokens": 1024,
      "seed": null
    }
  }
}
```

## Error Response Example

```json
{
  "result": null,
  "assumptions": [
    "An unexpected error occurred. The service abstains."
  ],
  "confidence": 0.1,
  "trace": {
    "data": {
      "inputs": {
        "path": "/projects/invalid",
        "method": "GET"
      },
      "intermediates": {
        "error": "ValueError",
        "error_id": "error-abc123",
        "trace_id": "trace-xyz789"
      },
      "outputs": {}
    },
    "code_version": {
      "git_sha": "abc123",
      "dirty": false
    },
    "model_config": {
      "provider": "none",
      "model": "none",
      "temperature": 0.0,
      "max_tokens": 1024,
      "seed": null
    }
  }
}
```

## Abstain Response

When service cannot determine result:

```json
{
  "result": null,
  "assumptions": [
    "Geocoding failed; using default wind speed"
  ],
  "confidence": 0.5,
  "trace": {
    "data": {
      "inputs": {
        "address": "Invalid Address"
      },
      "intermediates": {
        "geocode_error": "Address not found"
      },
      "outputs": {}
    },
    ...
  }
}
```

## Validation

### Pydantic Schema

```python
from apex.api.schemas import ResponseEnvelope

# Validate response
envelope = ResponseEnvelope(
    result={"key": "value"},
    assumptions=["assumption"],
    confidence=0.95,
    trace=TraceModel(...)
)
```

### JSON Schema

Get JSON schema:

```bash
curl http://localhost:8000/schemas/envelope.v1.json
```

## Best Practices

### 1. Always Include Assumptions

List all assumptions made:
- Default values used
- Data sources
- Calculation methods
- Constraints applied

### 2. Set Appropriate Confidence

- Deterministic calculations: `0.95+`
- With external API: `0.85-0.9`
- With fallback: `0.7-0.8`
- Abstain: `0.1-0.5`

### 3. Include Trace Data

Always populate trace:
- `inputs`: Request parameters
- `intermediates`: Calculated values
- `outputs`: Response data

### 4. Round Floats

Round floating-point numbers for determinism:
```python
round(value, 2)  # Two decimal places
```

## Next Steps

- [**API Endpoints**](api-endpoints.md) - See envelope in action
- [**Error Codes**](error-codes.md) - Error handling

