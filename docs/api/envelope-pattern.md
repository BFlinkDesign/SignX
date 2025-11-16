# Envelope Pattern Guide

Complete guide to understanding and using the Envelope response pattern.

## Overview

The Envelope pattern provides:
- **Determinism**: Same inputs → same outputs (via `content_sha256`)
- **Traceability**: Complete audit trail
- **Confidence Scoring**: Quantified uncertainty
- **Warning System**: Actionable assumptions
- **Version Tracking**: Constants and calculations tracked

## Structure

```typescript
interface Envelope<T> {
  // Metadata
  model_version: string;        // API version
  route: string;                // Endpoint path
  request_id: string;           // Unique request ID
  etag?: string;                // Optimistic locking
  timestamp: string;            // ISO 8601
  
  // Input/Output
  inputs: Record<string, any>;  // Request inputs
  data: T;                      // Response data
  
  // Confidence & Warnings
  assumptions: string[];        // Warnings, assumptions, notes
  confidence: number;           // 0.0-1.0
  
  // Traceability
  constants_version?: string;   // Pack versions used
  calculations?: Record<string, any>;
  checks?: Record<string, any>;
  artifacts?: string[];         // File references
  
  trace: {
    data: {
      inputs: Record<string, any>;
      intermediates: Record<string, any>;
      outputs: Record<string, any>;
    };
    pack_metadata?: Array<{
      name: string;
      version: string;
      sha256: string;
      refs: string[];
    }>;
    validation_errors?: Array<{
      field: string;
      message: string;
    }>;
    pareto_frontier?: Array<...>;
    ai_suggestion?: {...};
    uncertainty?: {...};
  };
  
  // Determinism
  content_sha256: string;      // SHA256 of rounded response
}
```

## Determinism Guarantees

### Rounded Floats

All floating-point numbers are rounded to 3 decimal places:

```python
# Before
result = {"depth_ft": 4.23456789}

# After (in Envelope)
{
  "data": {
    "depth_ft": 4.235  # Rounded to 3 decimals
  }
}
```

### Content SHA256

Deterministic hash of the response (excluding metadata):

```python
def envelope_sha(envelope: Envelope) -> str:
    # Sort keys, round floats, exclude metadata
    payload = {
        "data": round_floats(envelope.data),
        "assumptions": sorted(envelope.assumptions),
        "confidence": round(envelope.confidence, 3),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
```

**Use Cases:**
- Response caching
- Change detection
- Verification

### Deterministic Sorting

Lists are sorted deterministically (seeded by `request_id`):

```python
import random

random.seed(hash(request_id))
sorted_list = sorted(items, key=lambda x: random.random())
```

## Confidence Scoring

### Calculation Formula

```python
def calc_confidence(assumptions: list[str]) -> float:
    base_confidence = 1.0
    
    # Penalties
    if any("warning" in a.lower() for a in assumptions):
        base_confidence -= 0.1
    if any("review required" in a.lower() for a in assumptions):
        base_confidence -= 0.3
    if any("abstain" in a.lower() for a in assumptions):
        base_confidence = 0.0
    if any("failed" in a.lower() for a in assumptions):
        base_confidence -= 0.2
    
    return max(0.0, min(1.0, base_confidence))
```

### Confidence Levels

| Range | Meaning | Actions |
|-------|---------|---------|
| 0.9-1.0 | High | Proceed normally |
| 0.7-0.89 | Medium | Review assumptions |
| 0.5-0.69 | Low | Consider alternatives |
| 0.0-0.49 | Very Low | Engineering review required |

### Example Scenarios

**High Confidence (0.95):**
```json
{
  "assumptions": ["Standard configuration", "All checks pass"],
  "confidence": 0.95,
  "checks": {"all_pass": true}
}
```

**Medium Confidence (0.75):**
```json
{
  "assumptions": [
    "Using default wind speed (geocoding failed)",
    "Conservative soil bearing assumed"
  ],
  "confidence": 0.75
}
```

**Low Confidence (0.45):**
```json
{
  "assumptions": [
    "Engineering review required for depth >5ft",
    "Unusual configuration detected"
  ],
  "confidence": 0.45,
  "checks": {"request_engineering": true}
}
```

## Constants Versioning

### Pack Metadata

Tracks which calculation packs were used:

```json
{
  "constants_version": "pricing:v1:abc123,exposure:v1:def456",
  "trace": {
    "pack_metadata": [
      {
        "name": "pricing",
        "version": "v1",
        "sha256": "abc123...",
        "refs": ["/config/pricing_v1.yaml"]
      },
      {
        "name": "exposure",
        "version": "v1",
        "sha256": "def456...",
        "refs": ["/config/exposure_factors.yaml"]
      }
    ]
  }
}
```

**Use Cases:**
- Audit trail
- Reproducibility
- Version upgrades

## Handling Assumptions

### Common Assumptions

1. **Defaults Used**
   ```
   "Using default wind speed (geocoding failed)"
   ```

2. **Warnings**
   ```
   "Warning: Pole height >40ft is uncommon"
   ```

3. **Review Required**
   ```
   "Engineering review required for depth >5ft"
   ```

4. **Abstain**
   ```
   "Cannot solve: No feasible poles for given loads"
   ```

### Frontend Display

```typescript
function displayAssumptions(assumptions: string[]) {
  assumptions.forEach(assumption => {
    if (assumption.includes("Warning:")) {
      showSnackbar(assumption, "warning");
    } else if (assumption.includes("required")) {
      showBanner(assumption, "error");
    }
  });
}
```

## Trace Data

### Inputs/Intermediates/Outputs

```json
{
  "trace": {
    "data": {
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
  }
}
```

### Validation Errors

```json
{
  "trace": {
    "validation_errors": [
      {
        "field": "height_ft",
        "message": "Must be between 10 and 50 feet"
      }
    ]
  }
}
```

## ETag & Optimistic Locking

### Usage

```bash
# GET resource
GET /projects/proj_123
# Response includes: "etag": "xyz789"

# Update with ETag
PUT /projects/proj_123
If-Match: xyz789
{
  "name": "Updated"
}

# If etag doesn't match:
# Response: 412 Precondition Failed
```

### ETag Generation

```python
def compute_etag(project: Project) -> str:
    state = {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "updated_at": project.updated_at.isoformat()
    }
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()[:16]
```

## Content SHA256 for Caching

### Client-Side Caching

```typescript
const cacheKey = `api:${route}:${content_sha256}`;

if (localStorage.getItem(cacheKey)) {
  return JSON.parse(localStorage.getItem(cacheKey));
}

const response = await fetch(endpoint);
const envelope = await response.json();

// Cache for 24 hours
localStorage.setItem(cacheKey, JSON.stringify(envelope.data));
setTimeout(() => localStorage.removeItem(cacheKey), 86400000);

return envelope.data;
```

### Server-Side Verification

```python
# Verify response integrity
expected_sha = envelope_sha(envelope.model_dump())
if envelope.content_sha256 != expected_sha:
    raise ValueError("Content SHA256 mismatch")
```

## Example: Full Envelope

```json
{
  "model_version": "1.0",
  "route": "/signage/direct_burial/footing/solve",
  "request_id": "req_abc123def456",
  "timestamp": "2025-01-27T10:00:00Z",
  "inputs": {
    "footing": {"diameter_ft": 3.0},
    "soil_psf": 3000.0,
    "num_poles": 1,
    "M_pole_kipft": 10.0
  },
  "assumptions": [
    "soil_bearing=3000psf, K=calib_v1",
    "Engineering review required for depth >5ft"
  ],
  "constants_version": "footing_calibration:v1:abc123",
  "calculations": {
    "volume_cf": 39.79,
    "concrete_yards": 1.47
  },
  "checks": {
    "monotonic": true,
    "request_engineering": false
  },
  "confidence": 0.85,
  "trace": {
    "data": {
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
    },
    "pack_metadata": [
      {
        "name": "footing_calibration",
        "version": "v1",
        "sha256": "abc123...",
        "refs": ["/config/footing_calibration_v1.yaml"]
      }
    ],
    "uncertainty": {
      "depth_min": 4.0,
      "depth_max": 4.5,
      "confidence_interval": 0.10
    }
  },
  "content_sha256": "def456ghi789...",
  "data": {
    "min_depth_ft": 4.2,
    "min_depth_in": 50.4,
    "diameter_ft": 3.0,
    "concrete_yards": 1.47
  }
}
```

---

**Next Steps:**
- [**API Reference**](api-reference.md) - All endpoints
- [**Troubleshooting**](../operations/troubleshooting.md) - Common issues

