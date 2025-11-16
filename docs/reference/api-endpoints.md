# API Endpoints Reference

Complete reference for all API endpoints.

## Base URL

All endpoints are under `/` (root). Default port: `8000`

```
http://localhost:8000
```

## Authentication

Currently, the API uses API key authentication via header:

```
X-Apex-Key: your-api-key-here
```

For development, authentication may be disabled.

## Response Format

All endpoints return a standardized envelope:

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
      "dirty": false
    },
    "model_config": {
      "provider": "none",
      "model": "none"
    }
  }
}
```

## Core Endpoints

### Health Check

```http
GET /health
```

Returns service health status.

**Response:**
```json
{
  "result": {
    "service": "api",
    "status": "ok",
    "version": "0.1.0"
  }
}
```

### Readiness Probe

```http
GET /ready
```

Deep health check including dependencies (Redis, database).

**Response:**
```json
{
  "result": {
    "status": "ready",
    "checks": {
      "redis": "ok",
      "database": "ok"
    }
  }
}
```

### Metrics

```http
GET /metrics
```

Prometheus metrics in Prometheus format.

### API Documentation

```http
GET /docs
```

Interactive API documentation (Swagger UI).

### OpenAPI Schema

```http
GET /openapi.json
```

OpenAPI 3.0 schema definition.

## Projects

### List Projects

```http
GET /projects?skip=0&limit=100&status=draft&q=search
```

**Query Parameters:**
- `skip` (int): Number of results to skip (default: 0)
- `limit` (int): Maximum results (default: 100, max: 1000)
- `status` (string): Filter by status (`draft`, `estimating`, `submitted`, etc.)
- `q` (string): Text search query

**Response:**
```json
{
  "result": {
    "projects": [...],
    "total": 42,
    "search_fallback": false
  }
}
```

### Create Project

```http
POST /projects
Content-Type: application/json

{
  "account_id": "demo",
  "name": "My Sign Project",
  "customer": "Acme Corp",
  "description": "Outdoor sign design",
  "created_by": "user@example.com"
}
```

**Response:**
```json
{
  "result": {
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
```

**Response:**
```json
{
  "result": {
    "project_id": "proj_abc123",
    "name": "My Sign Project",
    "status": "draft",
    "customer": "Acme Corp",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z",
    "etag": "xyz789"
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
- `If-Match`: ETag for optimistic locking

### Get Project Events

```http
GET /projects/{project_id}/events?skip=0&limit=100
```

Returns audit trail for project.

### Submit Project

```http
POST /projects/{project_id}/submit
Idempotency-Key: unique-key-123
```

**Headers:**
- `Idempotency-Key`: Unique key for idempotent submission

**Response:**
```json
{
  "result": {
    "project_id": "proj_abc123",
    "status": "submitted",
    "project_number": "PRJ-12345678",
    "pm_task_id": "task-abc",
    "idempotent": false
  }
}
```

### Generate Report

```http
POST /projects/{project_id}/report
```

Generates PDF report (cached by payload SHA256).

**Response:**
```json
{
  "result": {
    "project_id": "proj_abc123",
    "sha256": "abc123...",
    "pdf_ref": "blobs/ab/abc123.pdf",
    "cached": false,
    "download_url": "/artifacts/blobs/ab/abc123.pdf"
  }
}
```

## Sign Design

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
  "result": {
    "wind_speed_mph": 115.0,
    "snow_load_psf": 5.0,
    "exposure": "C",
    "lat": 32.7767,
    "lon": -96.7970,
    "source": "asce7",
    "address_resolved": "123 Main St, Dallas, TX 75201, USA"
  }
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
  "result": {
    "A_ft2": 112.0,
    "z_cg_ft": 4.0,
    "weight_estimate_lb": 1120.0,
    "view_token": "cab_1234"
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
  }
}
```

**Response:**
```json
{
  "result": {
    "options": [
      {
        "family": "pipe",
        "designation": "6x0.25",
        "weight_lbf": 8.17,
        "Sx_in3": 8.17,
        "Ix_in4": 28.1,
        "fy_psi": 36000
      }
    ],
    "recommended": {...},
    "feasible_count": 15
  }
}
```

## Foundation Design

### Direct Burial - Solve Footing

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
  "result": {
    "min_depth_ft": 4.2,
    "min_depth_in": 50.4,
    "diameter_ft": 3.0,
    "concrete_yards": 1.47,
    "monotonic": true
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
  "weld": {
    "size_in": 0.25,
    "strength": 70.0,
    "length_in": 12.0
  },
  "anchors": {
    "num_anchors": 4,
    "dia_in": 0.75,
    "embed_in": 10.0,
    "fy_ksi": 58.0,
    "fc_psi": 4000.0,
    "spacing_in": 6.0
  },
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
  "result": {
    "all_pass": true,
    "approved": true,
    "checks": [
      {
        "check": "plate_thickness",
        "pass": true,
        "demand": 0.52,
        "capacity": 0.75,
        "util": 0.69
      },
      ...
    ]
  }
}
```

## Utilities

### Concrete Yardage Calculator

```http
POST /signage/common/concrete/yards
Content-Type: application/json

{
  "diameter_ft": 3.0,
  "depth_ft": 4.0
}
```

**Response:**
```json
{
  "result": {
    "concrete_yards": 1.05,
    "volume_cf": 28.27,
    "diameter_ft": 3.0,
    "depth_ft": 4.0
  }
}
```

## Files

### Presign Upload URL

```http
POST /files/presign
Content-Type: application/json

{
  "filename": "drawing.pdf",
  "content_type": "application/pdf"
}
```

### Attach File to Project

```http
POST /files/attach
Content-Type: application/json

{
  "project_id": "proj_abc123",
  "blob_key": "uploads/abc123.pdf",
  "sha256": "abc123..."
}
```

## Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `404` - Not Found
- `412` - Precondition Failed (ETag mismatch)
- `422` - Unprocessable Entity (validation error)
- `429` - Too Many Requests (rate limit)
- `500` - Internal Server Error

## Error Response

```json
{
  "result": null,
  "assumptions": ["Error description"],
  "confidence": 0.1,
  "trace": {
    "data": {
      "error_id": "error-abc123",
      "error_type": "ValueError"
    }
  }
}
```

Error responses include `error_id` in headers:
- `X-Error-ID`: Unique error identifier
- `X-Trace-ID`: Request trace identifier

