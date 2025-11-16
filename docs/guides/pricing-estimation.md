# Pricing & Estimation Guide

Complete guide to pricing calculations and cost estimation.

## Overview

Pricing calculations are:
- **Instant** - Real-time cost calculation
- **Versioned** - Pricing table versioning (v1, v2, ...)
- **Deterministic** - Same inputs = same output
- **Configurable** - YAML-based pricing tables

## Get Pricing Estimate

Calculate cost for a sign design:

```bash
curl -X POST http://localhost:8000/projects/proj_abc123/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "height_ft": 24.0,
    "addons": ["calc_packet", "hard_copies"]
  }'
```

**Response:**
```json
{
  "result": {
    "base_price": 2500.00,
    "addons": {
      "calc_packet": 150.00,
      "hard_copies": 50.00
    },
    "total": 2700.00,
    "version": "v1",
    "currency": "USD"
  },
  "assumptions": ["Pricing version v1", "Height: 24.0 ft"],
  "confidence": 0.95
}
```

## Pricing Structure

### Base Price

Base price determined by height bracket:

| Height Range (ft) | Base Price ($) |
|-------------------|----------------|
| 0-15 | 1500.00 |
| 15-20 | 2000.00 |
| 20-25 | 2500.00 |
| 25-30 | 3000.00 |
| 30+ | 3500.00 |

### Add-ons

Available add-on services:

| Add-on | Price ($) | Description |
|--------|-----------|-------------|
| `calc_packet` | 150.00 | Complete calculation packet |
| `hard_copies` | 50.00 | Printed hard copies |
| `rush_delivery` | 300.00 | Expedited delivery |
| `peer_review` | 500.00 | Professional peer review |

### Total Calculation

```
total = base_price + sum(addon_prices)
```

## Parameters

### Height

Sign height in feet (determines base price bracket):

```json
{
  "height_ft": 24.0
}
```

### Add-ons

Array of add-on service identifiers:

```json
{
  "addons": ["calc_packet", "hard_copies"]
}
```

**Valid add-ons:**
- `calc_packet` - Calculation packet
- `hard_copies` - Hard copies
- `rush_delivery` - Rush delivery
- `peer_review` - Peer review

## Pricing Versioning

Pricing tables are versioned. Current version is `v1`.

### Version Check

Check available pricing version:

```bash
curl http://localhost:8000/projects/proj_abc123/estimate \
  -G --data-urlencode "version=v1"
```

### Version Validation

If invalid version requested:
- Response: `409 Conflict`
- Message: "Unknown pricing version"
- Default: Uses latest version

## Pricing Configuration

### Location

Pricing table: `services/api/config/pricing_v1.yaml`

### Structure

```yaml
version: "v1"
effective_date: "2025-01-01"
base_rates:
  - height_max_ft: 15
    price: 1500.00
  - height_max_ft: 20
    price: 2000.00
  - height_max_ft: 25
    price: 2500.00
addons:
  calc_packet: 150.00
  hard_copies: 50.00
  rush_delivery: 300.00
  peer_review: 500.00
```

### Updating Pricing

1. Edit `pricing_v1.yaml` or create `pricing_v2.yaml`
2. Restart API service
3. Pricing automatically loaded on startup

## Usage Examples

### Basic Estimate

```bash
# Simple estimate by height
curl -X POST http://localhost:8000/projects/$PROJECT_ID/estimate \
  -H "Content-Type: application/json" \
  -d '{"height_ft": 20.0}'
```

**Result:** `$2000.00` (base price only)

### With Add-ons

```bash
# Estimate with add-ons
curl -X POST http://localhost:8000/projects/$PROJECT_ID/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "height_ft": 24.0,
    "addons": ["calc_packet", "hard_copies"]
  }'
```

**Result:** `$2700.00` ($2500 base + $200 addons)

### All Add-ons

```bash
# Complete estimate
curl -X POST http://localhost:8000/projects/$PROJECT_ID/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "height_ft": 30.0,
    "addons": ["calc_packet", "hard_copies", "rush_delivery", "peer_review"]
  }'
```

**Result:** `$4450.00` ($3000 base + $1000 addons)

## Cost Snapshot

When saving project payload, include cost snapshot:

```json
{
  "cost_snapshot": {
    "base": 2500.00,
    "addons": {
      "calc_packet": 150.00,
      "hard_copies": 50.00
    },
    "total": 2700.00,
    "version": "v1",
    "estimated_at": "2025-01-01T00:00:00Z"
  }
}
```

**Benefits:**
- Historical pricing preserved
- Audit trail for pricing changes
- Quote accuracy maintained

## Integration with Workflow

### Step 1: Get Estimate

```bash
PRICING=$(curl -s -X POST http://localhost:8000/projects/$PROJECT_ID/estimate \
  -H "Content-Type: application/json" \
  -d '{"height_ft": 24.0, "addons": ["calc_packet"]}')
```

### Step 2: Include in Payload

```bash
curl -X POST http://localhost:8000/projects/$PROJECT_ID/payload \
  -H "Content-Type: application/json" \
  -d "{
    \"module\": \"signage.single_pole\",
    \"config\": {...},
    \"cost_snapshot\": $(echo $PRICING | jq '.result')
  }"
```

### Step 3: Generate Report

Report includes pricing in cost summary section.

## Pricing Accuracy

- **Confidence**: 0.95 (high)
- **Assumptions**: Listed in response
- **Version**: Tracked in response

## Best Practices

### 1. Get Estimate Early

Calculate pricing during design phase:
- Before finalizing design
- Before customer quote
- After design changes

### 2. Save Cost Snapshot

Always include `cost_snapshot` in payload:
- Preserves historical pricing
- Enables pricing audits
- Supports reporting

### 3. Version Awareness

Check pricing version in responses:
- Monitor for version changes
- Update integrations if needed
- Handle version conflicts

### 4. Add-on Selection

Only include applicable add-ons:
- Don't add unnecessary services
- Validate add-on availability
- Check add-on requirements

## Error Handling

### Invalid Height

```json
{
  "result": null,
  "assumptions": ["Invalid height value"],
  "confidence": 0.1
}
```

### Invalid Add-on

```json
{
  "result": {
    "base_price": 2500.00,
    "addons": {},
    "total": 2500.00,
    "errors": ["Unknown add-on: invalid_addon"]
  }
}
```

## Next Steps

- [**Sign Design Workflow**](sign-design-workflow.md) - Complete workflow
- [**Project Management**](project-management.md) - Save estimates
- [**API Reference**](../reference/api-endpoints.md) - Endpoint details

