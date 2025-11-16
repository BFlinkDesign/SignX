# Sign Design Workflow Guide

Complete step-by-step guide for designing a sign from start to finish.

## Workflow Overview

```
1. Create Project
   ↓
2. Resolve Site (geocoding + wind data)
   ↓
3. Design Cabinets (geometry calculations)
   ↓
4. Select Support (pole filtering)
   ↓
5. Design Foundation (direct burial or baseplate)
   ↓
6. Calculate Pricing
   ↓
7. Save Payload
   ↓
8. Generate Report
   ↓
9. Submit Project
```

## Step 1: Create Project

```bash
PROJECT_ID=$(curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "demo",
    "name": "Main Street Sign",
    "customer": "Acme Corp",
    "created_by": "engineer@example.com"
  }' | jq -r '.result.project_id')
```

## Step 2: Resolve Site

Get location and environmental data:

```bash
curl -X POST http://localhost:8000/signage/common/site/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "address": "123 Main St, Dallas, TX 75201",
    "exposure": "C"
  }'
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
    "source": "asce7"
  }
}
```

**Use this data for:**
- Wind load calculations
- Foundation design requirements
- Code compliance

## Step 3: Design Cabinets

Calculate cabinet geometry:

```bash
curl -X POST http://localhost:8000/signage/common/cabinets/derive \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
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

### Add Multiple Cabinets

```bash
curl -X POST http://localhost:8000/signage/common/cabinets/add \
  -H "Content-Type: application/json" \
  -d '{
    "existing_cabinets": [...],
    "cabinet": {
      "width_ft": 14.0,
      "height_ft": 8.0,
      "depth_in": 12.0,
      "weight_psf": 10.0,
      "z_offset_ft": 8.0
    }
  }'
```

## Step 4: Select Support Structure

Get pole options based on loads:

```bash
curl -X POST http://localhost:8000/signage/common/poles/options \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
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

**Material Constraints:**
- Aluminum supports limited to 15 ft height
- Automatic filtering based on strength requirements

## Step 5: Design Foundation

### Option A: Direct Burial

```bash
curl -X POST http://localhost:8000/signage/direct_burial/footing/solve \
  -H "Content-Type: application/json" \
  -d '{
    "footing": {
      "diameter_ft": 3.0
    },
    "soil_psf": 3000.0,
    "num_poles": 1,
    "M_pole_kipft": 10.0
  }'
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

### Option B: Baseplate

```bash
curl -X POST http://localhost:8000/signage/baseplate/checks \
  -H "Content-Type: application/json" \
  -d '{
    "plate": {...},
    "weld": {...},
    "anchors": {...},
    "loads": {...}
  }'
```

**Response includes:**
- Individual check results (plate, weld, anchors)
- Overall approval status
- Utilization ratios

## Step 6: Calculate Pricing

```bash
curl -X POST http://localhost:8000/projects/$PROJECT_ID/estimate \
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
    "version": "v1"
  }
}
```

## Step 7: Save Payload

Save complete design configuration:

```bash
curl -X POST http://localhost:8000/projects/$PROJECT_ID/payload \
  -H "Content-Type: application/json" \
  -d '{
    "module": "signage.single_pole",
    "config": {
      "request": {
        "site": {...},
        "cabinets": {...},
        "support": {...},
        "foundation": {...}
      },
      "selected": {
        "support": {...},
        "foundation": {...}
      },
      "loads": {...}
    },
    "files": ["uploads/drawing.pdf"],
    "cost_snapshot": {
      "base": 2500.00,
      "total": 2700.00
    }
  }'
```

**Features:**
- Automatic SHA256 computation
- Deduplication (same payload = no duplicate)
- Event logging

## Step 8: Generate Report

Generate PDF report (cached by payload SHA):

```bash
curl -X POST http://localhost:8000/projects/$PROJECT_ID/report
```

**Response:**
```json
{
  "result": {
    "sha256": "abc123...",
    "pdf_ref": "blobs/ab/abc123.pdf",
    "cached": false,
    "download_url": "/artifacts/blobs/ab/abc123.pdf"
  }
}
```

**Report Contents:**
1. Cover page (project metadata)
2. Elevation drawing
3. Design outputs (loads, foundation, safety factors)
4. General notes

## Step 9: Submit Project

Submit for engineering review:

```bash
curl -X POST http://localhost:8000/projects/$PROJECT_ID/submit \
  -H "Idempotency-Key: submit-$PROJECT_ID-$(date +%s)"
```

**What happens:**
1. State transition: `estimating` → `submitted`
2. PM dispatch task enqueued
3. Email notification sent (if manager email available)
4. Event logged with project_number

## Complete Example Script

```bash
#!/bin/bash

# 1. Create project
PROJECT_ID=$(curl -s -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"account_id":"demo","name":"Test Sign","created_by":"user@example.com"}' \
  | jq -r '.result.project_id')

echo "Created project: $PROJECT_ID"

# 2. Resolve site
SITE_DATA=$(curl -s -X POST http://localhost:8000/signage/common/site/resolve \
  -H "Content-Type: application/json" \
  -d '{"address":"123 Main St, Dallas, TX","exposure":"C"}')

WIND_SPEED=$(echo $SITE_DATA | jq -r '.result.wind_speed_mph')
echo "Wind speed: $WIND_SPEED mph"

# 3. Design cabinets
CABINET_DATA=$(curl -s -X POST http://localhost:8000/signage/common/cabinets/derive \
  -H "Content-Type: application/json" \
  -d '{"overall_height_ft":25.0,"cabinets":[{"width_ft":14.0,"height_ft":8.0}]}')

# 4. Select pole
POLE_DATA=$(curl -s -X POST http://localhost:8000/signage/common/poles/options \
  -H "Content-Type: application/json" \
  -d '{"height_ft":20.0,"material":"steel","loads":{"M_kipin":1200.0}}')

# 5. Design foundation
FOOTING_DATA=$(curl -s -X POST http://localhost:8000/signage/direct_burial/footing/solve \
  -H "Content-Type: application/json" \
  -d '{"footing":{"diameter_ft":3.0},"soil_psf":3000.0,"M_pole_kipft":10.0}')

# 6. Get pricing
PRICING=$(curl -s -X POST http://localhost:8000/projects/$PROJECT_ID/estimate \
  -H "Content-Type: application/json" \
  -d '{"height_ft":24.0}')

# 7. Save payload (combine all data)
PAYLOAD=$(curl -s -X POST http://localhost:8000/projects/$PROJECT_ID/payload \
  -H "Content-Type: application/json" \
  -d "{
    \"module\": \"signage.single_pole\",
    \"config\": {
      \"request\": $SITE_DATA,
      \"selected\": {\"support\": $POLE_DATA, \"foundation\": $FOOTING_DATA},
      \"loads\": {}
    },
    \"cost_snapshot\": $PRICING
  }")

# 8. Generate report
REPORT=$(curl -s -X POST http://localhost:8000/projects/$PROJECT_ID/report)
echo "Report: $(echo $REPORT | jq -r '.result.download_url')"

# 9. Submit
SUBMIT=$(curl -s -X POST http://localhost:8000/projects/$PROJECT_ID/submit \
  -H "Idempotency-Key: submit-$PROJECT_ID")
echo "Submitted: $(echo $SUBMIT | jq -r '.result.status')"
```

## Next Steps

- [**Foundation Design Guide**](foundation-design.md) - Detailed foundation design
- [**Pricing & Estimation**](pricing-estimation.md) - Pricing details
- [**Project Management**](project-management.md) - Project operations

