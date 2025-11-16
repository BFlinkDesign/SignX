# Interactive API Reference

Complete API reference for SIGN X Studio Clone with Envelope pattern.

## Overview

All API endpoints return responses in the **Envelope** format, providing:
- Standardized structure
- Deterministic outputs (via `content_sha256`)
- Confidence scoring (0.0-1.0)
- Full traceability
- Warning messages in `assumptions`

## Authentication

### JWT Token Lifecycle

#### Obtain Token

```bash
curl -X POST https://api.example.com/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "your-client-id",
    "client_secret": "your-client-secret"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_token_here"
}
```

#### Use Token

```bash
curl https://api.example.com/projects \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

#### Refresh Token

```bash
curl -X POST https://api.example.com/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "refresh_token_here"
  }'
```

#### Revoke Token

```bash
curl -X POST https://api.example.com/auth/revoke \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"token": "token_to_revoke"}'
```

### API Key Alternative

```bash
curl https://api.example.com/projects \
  -H "X-Apex-Key: your-api-key"
```

### Scopes

- `read_projects` - View projects
- `write_projects` - Create/update projects
- `submit_projects` - Submit for review
- `admin` - Full access

## Rate Limits

- **Default**: 100 requests/minute per user
- **Burst**: 10 requests/second
- **Headers**:
  - `X-RateLimit-Limit: 100`
  - `X-RateLimit-Remaining: 95`
  - `X-RateLimit-Reset: 1640995200`

### Rate Limit Exceeded

**Response:** `429 Too Many Requests`
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

## Idempotency

For mutation endpoints, include `Idempotency-Key` header:

```bash
curl -X POST https://api.example.com/projects/proj_123/submit \
  -H "Idempotency-Key: unique-key-uuid-v4" \
  -H "Authorization: Bearer $TOKEN"
```

**Behavior:**
- First request: Process normally
- Duplicate request: Return cached response (200 OK)
- TTL: 24 hours

## Envelope Response Format

All responses follow this structure:

```typescript
interface Envelope<T> {
  model_version: string;        // "1.0"
  route: string;                // "/projects"
  request_id: string;           // UUID
  etag?: string;                // For optimistic locking
  timestamp: string;            // ISO 8601
  inputs: Record<string, any>;  // Request inputs
  assumptions: string[];        // Warnings/assumptions
  constants_version?: string;   // "pricing:v1:abc123"
  calculations?: Record<string, any>;
  checks?: Record<string, any>;
  artifacts?: string[];         // File references
  confidence: number;           // 0.0-1.0
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
  };
  content_sha256: string;      // Deterministic hash
  data: T;                      // Actual response data
}
```

### Confidence Scores

| Range | Meaning | Visual Indicator |
|-------|---------|------------------|
| 0.9-1.0 | High confidence | Green badge |
| 0.7-0.89 | Medium confidence | Yellow badge |
| 0.5-0.69 | Low confidence | Orange badge |
| 0.0-0.49 | Very low / Abstain | Red badge |

## Core Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "model_version": "1.0",
  "route": "/health",
  "request_id": "req_abc123",
  "timestamp": "2025-01-27T10:00:00Z",
  "inputs": {},
  "assumptions": [],
  "confidence": 1.0,
  "trace": {
    "data": {
      "inputs": {},
      "outputs": {}
    }
  },
  "content_sha256": "abc123...",
  "data": {
    "status": "ok",
    "service": "api",
    "version": "0.1.0"
  }
}
```

### Readiness Probe

```http
GET /ready
```

**Response:**
```json
{
  "data": {
    "status": "ready",
    "checks": {
      "database": "ok",
      "redis": "ok",
      "minio": "ok"
    }
  }
}
```

## Projects

### List Projects

```http
GET /projects?skip=0&limit=100&status=draft&q=search
```

**Query Parameters:**
- `skip` (int): Pagination offset (default: 0)
- `limit` (int): Results per page (max: 1000)
- `status` (string): Filter by status
- `q` (string): Text search

**Response:**
```json
{
  "data": {
    "projects": [
      {
        "project_id": "proj_abc123",
        "name": "Main Street Sign",
        "status": "draft",
        "created_at": "2025-01-27T10:00:00Z",
        "etag": "xyz789"
      }
    ],
    "total": 42,
    "search_fallback": false
  },
  "confidence": 0.95
}
```

### Create Project

```http
POST /projects
Content-Type: application/json
Authorization: Bearer $TOKEN

{
  "account_id": "demo",
  "name": "My Sign Project",
  "customer": "Acme Corp",
  "created_by": "user@example.com"
}
```

**Response:**
```json
{
  "model_version": "1.0",
  "route": "/projects",
  "request_id": "req_def456",
  "timestamp": "2025-01-27T10:05:00Z",
  "inputs": {
    "account_id": "demo",
    "name": "My Sign Project"
  },
  "assumptions": ["Created in draft status"],
  "confidence": 0.95,
  "trace": {
    "data": {
      "inputs": {"account_id": "demo", "name": "My Sign Project"},
      "outputs": {"project_id": "proj_abc123"}
    }
  },
  "content_sha256": "def456...",
  "data": {
    "project_id": "proj_abc123",
    "name": "My Sign Project",
    "status": "draft",
    "etag": "xyz789"
  }
}
```

### Get Project

```http
GET /projects/{project_id}
If-None-Match: xyz789
```

**Headers:**
- `If-None-Match`: Return 304 if etag matches

**Response:**
```json
{
  "etag": "xyz789",
  "data": {
    "project_id": "proj_abc123",
    "name": "My Sign Project",
    "status": "draft",
    "customer": "Acme Corp",
    "confidence": 0.85,
    "created_at": "2025-01-27T10:00:00Z",
    "updated_at": "2025-01-27T10:05:00Z"
  }
}
```

### Update Project

```http
PUT /projects/{project_id}
If-Match: xyz789
Content-Type: application/json

{
  "name": "Updated Name",
  "customer": "New Customer"
}
```

**Headers:**
- `If-Match`: Required for optimistic locking

**Response:** `412 Precondition Failed` if etag mismatch

### Submit Project

```http
POST /projects/{project_id}/submit
Idempotency-Key: unique-uuid-v4
```

**Response:**
```json
{
  "data": {
    "project_id": "proj_abc123",
    "status": "submitted",
    "submission_id": "sub_789",
    "idempotent": false
  },
  "confidence": 0.90
}
```

**Idempotent Response:**
```json
{
  "data": {
    "project_id": "proj_abc123",
    "status": "submitted",
    "submission_id": "sub_789",
    "idempotent": true
  }
}
```

## Sign Design Endpoints

### Resolve Site

```http
POST /signage/common/site/resolve
Content-Type: application/json

{
  "address": "123 Main St, Dallas, TX 75201",
  "exposure": "C"
}
```

**Response:**
```json
{
  "assumptions": [
    "Geocoded: 123 Main St, Dallas, TX 75201, USA",
    "Wind speed from asce7"
  ],
  "confidence": 0.90,
  "constants_version": "exposure:v1:def456",
  "data": {
    "wind_speed_mph": 115.0,
    "snow_load_psf": 5.0,
    "exposure": "C",
    "lat": 32.7767,
    "lon": -96.7970,
    "source": "asce7"
  },
  "content_sha256": "ghi789..."
}
```

### Derive Cabinets

```http
POST /signage/common/cabinets/derive
Content-Type: application/json

{
  "overall_height_ft": 25.0,
  "cabinets": [
    {
      "width_ft": 14.0,
      "height_ft": 8.0,
      "depth_in": 12.0,
      "weight_psf": 10.0,
      "z_offset_ft": 0.0
    }
  ]
}
```

**Response:**
```json
{
  "assumptions": [
    "Cabinet geometry calculated",
    "Weight estimation based on density"
  ],
  "confidence": 0.95,
  "calculations": {
    "area_ft2": 112.0,
    "volume_ft3": 11.2,
    "weight_estimate_lb": 1120.0
  },
  "data": {
    "A_ft2": 112.0,
    "z_cg_ft": 4.0,
    "weight_estimate_lb": 1120.0,
    "view_token": "cab_1234"
  },
  "trace": {
    "data": {
      "intermediates": {
        "area_per_cabinet": 112.0,
        "total_weight": 1120.0
      }
    },
    "ai_suggestion": {
      "suggested_pole": "6x0.25",
      "suggested_footing": {"diameter_ft": 3.0},
      "confidence": 0.75
    }
  }
}
```

### Pole Options

```http
POST /signage/common/poles/options
Content-Type: application/json

{
  "height_ft": 20.0,
  "material": "steel",
  "num_poles": 1,
  "loads": {
    "M_kipin": 1200.0
  },
  "prefs": {
    "family": ["pipe", "tube"],
    "sort_by": "weight"
  },
  "optimize": "pareto"
}
```

**Response:**
```json
{
  "assumptions": [
    "Material: steel",
    "Filtered 15/200 sections by strength"
  ],
  "confidence": 0.90,
  "data": {
    "options": [
      {
        "family": "pipe",
        "designation": "6x0.25",
        "weight_lbf": 8.17,
        "Sx_in3": 8.17,
        "cost": 125.50,
        "safety_factor": 2.1
      }
    ],
    "recommended": {...},
    "feasible_count": 15
  },
  "trace": {
    "pareto_frontier": [
      {
        "pole": "6x0.25",
        "cost": 125.50,
        "weight": 8.17,
        "safety_factor": 2.1,
        "is_dominated": false
      }
    ]
  }
}
```

### Solve Footing

```http
POST /signage/direct_burial/footing/solve
Content-Type: application/json

{
  "footing": {
    "diameter_ft": 3.0
  },
  "soil_psf": 3000.0,
  "num_poles": 1,
  "M_pole_kipft": 10.0
}
```

**Response:**
```json
{
  "assumptions": [
    "soil_bearing=3000psf, K=calib_v1",
    "Engineering review required for depth >5ft"
  ],
  "confidence": 0.85,
  "constants_version": "footing_calibration:v1:abc123",
  "checks": {
    "monotonic": true,
    "request_engineering": false
  },
  "data": {
    "min_depth_ft": 4.2,
    "min_depth_in": 50.4,
    "diameter_ft": 3.0,
    "concrete_yards": 1.47
  },
  "trace": {
    "data": {
      "intermediates": {
        "M_pole_kipft": 10.0,
        "volume_cf": 39.79
      }
    },
    "uncertainty": {
      "depth_min": 4.0,
      "depth_max": 4.5,
      "confidence_interval": 0.10
    }
  }
}
```

### Baseplate Checks

```http
POST /signage/baseplate/checks
Content-Type: application/json

{
  "plate": {
    "w_in": 12.0,
    "l_in": 12.0,
    "t_in": 0.75,
    "fy_ksi": 36.0,
    "e_in": 3.0
  },
  "weld": {...},
  "anchors": {...},
  "loads": {
    "T_kip": 5.0,
    "V_kip": 2.0,
    "M_kipin": 100.0
  }
}
```

**Response:**
```json
{
  "assumptions": [
    "Fy=36ksi, E70XX fillet, ACI breakout"
  ],
  "confidence": 0.92,
  "checks": {
    "all_pass": true,
    "approved": true,
    "plate_thickness": {"pass": true, "util": 0.69},
    "weld_strength": {"pass": true, "util": 0.64},
    "anchor_tension": {"pass": true, "util": 0.36},
    "anchor_shear": {"pass": true, "util": 0.25}
  },
  "data": {
    "all_pass": true,
    "approved": true,
    "checks": [...]
  },
  "trace": {
    "alternatives": [
      {
        "plate_thickness": 0.625,
        "util": 0.85,
        "cost": 125.00
      }
    ]
  }
}
```

## Report Generation

### Generate Report (Async)

```http
POST /projects/{project_id}/report
```

**Response:**
```json
{
  "data": {
    "task_id": "task_abc123",
    "status": "pending"
  }
}
```

### Poll Task Status

```http
GET /tasks/{task_id}
```

**Response:**
```json
{
  "data": {
    "task_id": "task_abc123",
    "status": "processing",
    "progress": 45,
    "estimated_completion": "2025-01-27T10:10:00Z"
  }
}
```

**Completion:**
```json
{
  "data": {
    "task_id": "task_abc123",
    "status": "completed",
    "result": {
      "pdf_ref": "blobs/ab/abc123.pdf",
      "sha256": "abc123...",
      "download_url": "/artifacts/blobs/ab/abc123.pdf"
    }
  }
}
```

## Error Responses

### Validation Error

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

### Abstain Response

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

## Webhooks

### Configure Webhook

```http
POST /webhooks
Content-Type: application/json

{
  "url": "https://your-app.com/webhooks/apex",
  "events": ["project.submitted", "report.ready"],
  "secret": "webhook_secret"
}
```

### Webhook Payload

```json
{
  "event": "project.submitted",
  "timestamp": "2025-01-27T10:00:00Z",
  "project_id": "proj_abc123",
  "data": {
    "status": "submitted",
    "submission_id": "sub_789"
  }
}
```

**Verification:**
- Header: `X-Apex-Signature`
- HMAC-SHA256 of payload with webhook secret

---

**Next Steps:**
- [**Envelope Pattern Guide**](envelope-pattern.md) - Detailed Envelope structure
- [**Integration Guides**](../integrations/) - External system integration
- [**Troubleshooting**](../operations/troubleshooting.md) - Common issues

