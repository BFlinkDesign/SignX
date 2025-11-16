# APEX API Endpoints Reference

Complete list of all 40+ endpoints with idempotency and caching status.

## System Endpoints

### Health & Status
- `GET /health` - Service health check
- `GET /ready` - Readiness probe (with checks)
- `GET /version` - API version
- `GET /metrics` - Prometheus metrics
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc
- `GET /openapi.json` - OpenAPI schema

## Projects (8 endpoints)

### CRUD Operations
- `POST /projects` - Create project ✅ Idempotent
- `GET /projects` - List projects (pagination: 50/500) ✅ Cached
- `GET /projects/{id}` - Get project details
- `PUT /projects/{id}` - Update project (with etag) ✅ Idempotent
- `DELETE /projects/{id}` - Delete project ✅ Idempotent

### Payloads
- `POST /projects/{id}/payload` - Save design payload ✅ Idempotent
- `GET /projects/{id}/payload` - Get latest payload

### Submission
- `POST /projects/{id}/submit` - Submit for approval ✅ Idempotent (24h TTL)
  - Returns: `{"task_id": "...", "status": "submitted"}`

## Site & Environmental (1 endpoint)

- `POST /signage/common/site/resolve` - Resolve address → wind/snow
  - Input: `{address: str, exposure?: str}`
  - Output: `{wind_speed_mph, snow_load_psf, lat, lon, source}`

## Cabinet Design (1 endpoint)

- `POST /signage/common/cabinets/derive` - Derive load parameters
  - Input: `{overall_height_ft, cabinets: [{width_ft, height_ft}]}`
  - Output: `{a_ft2, z_cg_ft, weight_estimate_lb, mu_kipft}`

## Pole Selection (1 endpoint)

- `POST /signage/common/poles/options` - Filter feasible poles ⭐ **1hr Cached**
  - Input: `{loads: {M_kipin}, prefs: {family, steel_grade}, material, height_ft}`
  - Output: `{options: [...], recommended: {...}, feasible_count}`

## Direct Burial Foundation (3 endpoints)

- `POST /signage/direct_burial/footing/solve` - Compute footing depth
- `POST /signage/direct_burial/footing/design` - Complete design
- `POST /signage/direct_burial/assist` - Request engineering assist

## Base Plate Foundation (3 endpoints)

- `POST /signage/baseplate/checks` - Run design checks
- `POST /signage/baseplate/design` - Auto-design baseplate
- `POST /signage/baseplate/assist` - Request engineering assist

## Pricing (1 endpoint)

- `POST /projects/{id}/pricing/estimate` - Cost estimation
  - Input: `{addons: [{type, quantity}]}`
  - Output: `{total_cost, line_items: [...]}`

## BOM (2 endpoints)

- `GET /projects/{id}/bom` - Get current BOM
- `POST /projects/{id}/bom` - Regenerate BOM
  - Output: `{items: [{item, description, quantity, unit}], total_items}`

## Tasks (2 endpoints) ⭐ NEW

- `GET /tasks/{task_id}` - Get task status
  - States: PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED
  - Output: `{task_id, state, result?, error?}`
- `DELETE /tasks/{task_id}` - Cancel pending/started task

## Files & Storage (2 endpoints)

- `GET /projects/{id}/files/presign` - Get presigned upload URL
  - Output: `{url, expires_in}`
- `POST /projects/{id}/files/attach` - Attach file to project ✅ Idempotent

## Signcalc Gateway (2 endpoints)

- `POST /signcalc/v1/*` - Proxy to signcalc-service
- `GET /signcalc/schemas/*` - Schema export

## Utilities (1 endpoint)

- `POST /utilities/concrete/yards` - Concrete calculator
  - Input: `{diameter_ft, depth_ft}`
  - Output: `{cubic_yards}`

## Materials Gateway (3 endpoints)

- `POST /materials/pick` - Material selection
- `POST /materials/batch` - Batch material selection
- `GET /materials/contract` - Contract schema

---

## Idempotency Support

Endpoints marked with ✅ Idempotent support the `Idempotency-Key` header:
- All mutations (POST, PUT, PATCH, DELETE)
- 24-hour Redis TTL
- Automatic duplicate detection
- Instant cached response

**Usage**:
```bash
curl -X POST /projects -H "Idempotency-Key: unique-key-123" -d '{...}'
# First call: 201 Created
# Duplicate call: 200 OK (cached)
```

## Caching Support

Endpoints marked with ⭐ **Cached** use Redis with configurable TTL:
- Query results cached for 1 hour
- Automatic invalidation on TTL expiry
- Graceful degradation if Redis unavailable

## Authentication

All mutation endpoints can be protected with JWT:
```bash
curl -X POST /projects \
  -H "Authorization: Bearer <token>" \
  -d '{...}'
```

## Rate Limiting

- Default: **100 requests/minute per user**
- Configurable via env: `APEX_RATE_LIMIT_PER_MIN`
- Based on IP or JWT user_id

## Error Format

All errors return APEX Envelope:
```json
{
  "result": null,
  "errors": [{"field": "path.to.field", "message": "...", "type": "..."}],
  "assumptions": ["..."],
  "confidence": 0.0,
  "trace": {...}
}
```

## Response Format

All responses return APEX Envelope:
```json
{
  "result": {...},
  "assumptions": ["..."],
  "confidence": 0.95,
  "trace": {
    "data": {"inputs": {...}, "intermediates": {...}, "outputs": {...}},
    "code_version": {"git_sha": "...", "dirty": false},
    "model_config": {"provider": "none", "model": "none"}
  }
}
```

---

**Total Endpoints**: 40+
**Idempotent**: All mutations
**Cached**: Query endpoints
**Protected**: All mutations (JWT optional)
**Audited**: All mutations (via ProjectEvent)

