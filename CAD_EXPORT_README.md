# CAD Export Feature - DXF

**Version:** 1.0
**Last Updated:** 2025-11-02
**Author:** SignX-Studio Engineering Team

---

## Overview

The CAD Export feature provides fabrication-ready DXF drawings for sign structure foundations, including complete rebar schedules, anchor bolt layouts, and detailed dimensions.

**DXF (Drawing Exchange Format)** is the universal CAD interchange format supported by all major CAD systems including AutoCAD, BricsCAD, QCAD, LibreCAD, FreeCAD, DraftSight, and sign shop software like EnRoute, VCarve, and Aspire.

### Why DXF?

- ✅ **Universal Compatibility** - Works with ALL CAD systems
- ✅ **No License Required** - Open standard, no proprietary software needed
- ✅ **Industry Standard** - Preferred format for fabrication shops
- ✅ **Version Control** - Text-based format, easy to diff and track changes
- ✅ **Sign Shop Ready** - Direct import to CNC routers and plasma cutters

---

## Features

### Foundation Plan View
- **Top View:** Circular or rectangular foundation outline
- **Rebar Placement:** Vertical bars shown with standard symbols
- **Horizontal Reinforcement:** Spiral or tie locations indicated
- **Anchor Bolt Pattern:** Bolt circle with projection details
- **Dimensions:** Diameter, depth, bolt circle, spacing

### Foundation Section View
- **Side Cut:** Cross-section through foundation centerline
- **Rebar Detail:** Vertical and horizontal bar placement
- **Development Lengths:** Proper embedment shown
- **Concrete Cover:** Clear dimension callouts
- **Anchor Embedment:** Bolt projection and embedment depths

### Rebar Schedule Table
- **Bar Mark:** Unique identifier for each bar type
- **Size:** Bar diameter (#3, #4, #5, etc.)
- **Quantity:** Number of bars required
- **Length:** Individual bar length (feet/inches)
- **Total Length:** Sum for material ordering
- **Total Weight:** Pounds or tons for cost estimation

### Title Block (AIA Standard)
- **Project Name:** Client/site identification
- **Drawing Number:** Unique drawing reference
- **Engineer:** PE stamp information
- **Scale:** Architectural scale notation
- **Date:** Drawing generation timestamp
- **Revision:** Version tracking

### AIA Standard Layers

All CAD drawings follow AIA CAD Layer Guidelines (2nd Edition):

| Layer Name | Description | Color |
|------------|-------------|-------|
| `A-ANNO-DIMS` | Dimension annotations | 7 (White) |
| `A-ANNO-TEXT` | Text and labels | 7 (White) |
| `S-DETL-CONC` | Concrete outlines | 3 (Green) |
| `S-DETL-RBAR` | Rebar placement | 1 (Red) |
| `S-DETL-ANCH` | Anchor bolt details | 5 (Blue) |
| `G-ANNO-TTLB` | Title block | 7 (White) |

---

## API Reference

### Endpoint 1: Export Foundation Plan (Envelope Response)

**POST** `/api/cad/export/foundation`

Returns JSON envelope with metadata and file embedded in `trace.data.artifacts`.

#### Request Body

```json
{
  "foundation_type": "direct_burial",
  "diameter_ft": 3.0,
  "depth_ft": 6.0,
  "fc_ksi": 3.0,
  "fy_ksi": 60.0,
  "cover_in": 3.0,
  "anchor_layout": {
    "num_bolts": 8,
    "bolt_diameter_in": 1.0,
    "bolt_circle_diameter_ft": 2.5,
    "projection_in": 12.0,
    "embedment_in": 18.0
  },
  "format": "dxf",
  "scale": "1/4\"=1'-0\"",
  "project_name": "Sample Project",
  "drawing_number": "FND-001",
  "engineer": "John Doe, P.E."
}
```

#### Response

```json
{
  "ok": true,
  "result": {
    "filename": "FND-001_foundation_plan.dxf",
    "format": "dxf",
    "file_size_bytes": 45632,
    "num_entities": 127,
    "layers": ["A-ANNO-DIMS", "S-DETL-CONC", "S-DETL-RBAR", ...],
    "warnings": []
  },
  "assumptions": [
    "Rebar design per ACI 318-19: 8 vertical bars, 12 horizontal bars",
    "Anchor bolts: 8 × ∅1.0\" on 2.5' BC",
    "Drawing scale: 1/4\"=1'-0\"",
    "Export format: DXF",
    "AIA standard layers used: 6"
  ],
  "confidence": 1.0,
  "trace": {
    "data": {
      "artifacts": [
        {
          "type": "cad_drawing",
          "format": "dxf",
          "filename": "FND-001_foundation_plan.dxf",
          "size_bytes": 45632,
          "base64_data": "48656c6c6f20576f726c64..."
        }
      ]
    }
  }
}
```

### Endpoint 2: Download Foundation Plan (Direct Binary)

**POST** `/api/cad/download/foundation`

Returns raw CAD file for direct download (no JSON envelope).

#### Request Body

Same as `/export/foundation` endpoint.

#### Response

Binary CAD file with HTTP headers:

```
Content-Type: application/dxf
Content-Disposition: attachment; filename="FND-001_foundation_plan.dxf"
X-File-Size: 45632
X-CAD-Format: DXF
X-Num-Entities: 127
```

---

## Usage Examples

### Example 1: Basic DXF Export (cURL)

```bash
curl -X POST http://localhost:8000/api/cad/export/foundation \
  -H "Content-Type: application/json" \
  -d '{
    "foundation_type": "direct_burial",
    "diameter_ft": 3.0,
    "depth_ft": 6.0,
    "format": "dxf",
    "project_name": "Test Foundation"
  }'
```

### Example 2: Direct Download (Python)

```python
import requests

request = {
    "foundation_type": "pier_and_grade_beam",
    "diameter_ft": 4.0,
    "depth_ft": 8.0,
    "fc_ksi": 4.0,
    "anchor_layout": {
        "num_bolts": 8,
        "bolt_diameter_in": 1.0,
        "bolt_circle_diameter_ft": 3.0,
        "projection_in": 12.0,
        "embedment_in": 18.0,
    },
    "format": "dxf",
    "scale": "1/2\"=1'-0\"",
    "project_name": "Main Street Sign",
    "drawing_number": "FND-MS-001",
    "engineer": "Jane Smith, P.E.",
}

response = requests.post(
    "http://localhost:8000/api/cad/download/foundation",
    json=request,
)

# Save DXF file
with open("foundation_plan.dxf", "wb") as f:
    f.write(response.content)

print(f"Downloaded: {response.headers['Content-Disposition']}")
print(f"File size: {response.headers['X-File-Size']} bytes")
```

### Example 3: Extract from Envelope (JavaScript)

```javascript
const response = await fetch('/api/cad/export/foundation', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    foundation_type: 'direct_burial',
    diameter_ft: 3.0,
    depth_ft: 6.0,
    format: 'dxf',
  }),
});

const envelope = await response.json();

// Extract file from artifacts
const artifact = envelope.trace.data.artifacts[0];
const filename = artifact.filename;
const hexData = artifact.base64_data;

// Convert hex to binary
const bytes = new Uint8Array(hexData.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));

// Download file
const blob = new Blob([bytes], { type: 'application/dxf' });
const url = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = filename;
a.click();
```

---

## Drawing Scales

The following architectural scales are supported:

| Scale | Description | Use Case |
|-------|-------------|----------|
| `1/4"=1'-0"` | Quarter-inch scale | Small foundations (≤5 ft diameter) |
| `1/2"=1'-0"` | Half-inch scale | Medium foundations (5-8 ft) |
| `1"=1'-0"` | One-inch scale | Large foundations (>8 ft) |
| `3"=1'-0"` | Three-inch scale | Detail views, connections |

**Note:** AutoCAD/BricsCAD will respect the scale annotation in the title block. Dimensions are shown in architectural format (e.g., `3'-6"`).

---

## Foundation Types

Supported foundation types from `FoundationType` enum:

- `direct_burial` - Direct burial pole foundation
- `pier_and_grade_beam` - Pier with grade beam
- `drilled_shaft` - Drilled shaft/caisson
- `spread_footing` - Spread footing with base plate
- `mat_foundation` - Mat/raft foundation

---

## Rebar Design Integration

The CAD export automatically integrates with the `ConcreteRebarService` to:

1. **Calculate Development Lengths** (ACI 318-19 Section 25.4.2)
2. **Design Rebar Schedule** (vertical, horizontal, spiral reinforcement)
3. **Compute Material Quantities** (concrete CY, rebar tons)
4. **Apply Code Minimums** (minimum steel ratio, spacing, cover)

All rebar calculations are **deterministic** and **PE-stampable**.

---

## File Size Guidelines

Typical DXF file sizes:

| Drawing Complexity | File Size | Entities |
|--------------------|-----------|----------|
| Basic (no anchors) | ~30 KB | 50-80 |
| Standard (with anchors) | ~45 KB | 100-150 |
| Complex (large schedule) | ~70 KB | 200+ |

**Note:** DWG files are typically 30-50% smaller than equivalent DXF files.

---

## Validation & Error Handling

### Input Validation

- **Diameter:** 0.1 ft - 10 ft
- **Depth:** 0.5 ft - 20 ft
- **Concrete Strength:** 2.5 ksi - 10 ksi
- **Rebar Yield:** 40 ksi - 80 ksi
- **Anchor Bolts:** 4-12 bolts per foundation
- **Bolt Diameter:** 0.5" - 3.0"

### Error Responses

**400 Bad Request:** Invalid foundation type or validation error
```json
{
  "detail": "Invalid foundation type: invalid_type. Valid types: [...]"
}
```

**422 Unprocessable Entity:** Pydantic validation error
```json
{
  "detail": [
    {
      "loc": ["body", "diameter_ft"],
      "msg": "Input should be greater than 0",
      "type": "greater_than"
    }
  ]
}
```

**500 Internal Server Error:** CAD export failure
```json
{
  "detail": "CAD export failed: ezdxf error message"
}
```

---

## Testing

### Run Integration Tests

```bash
cd services/api
pytest tests/integration/test_cad_export_route.py -v
```

### Test Coverage

- ✅ Basic DXF export
- ✅ Export with anchor bolts
- ✅ Different drawing scales
- ✅ Invalid foundation type validation
- ✅ Invalid diameter validation
- ✅ DWG format (placeholder)
- ✅ Direct download endpoint
- ✅ Determinism (multiple calls)
- ✅ Confidence scoring
- ✅ Missing required fields
- ✅ Anchor bolt validation

---

## Roadmap

### Phase 1: DXF Implementation ✅
- [x] Foundation plan view
- [x] Foundation section view
- [x] Rebar schedule table
- [x] Anchor bolt layout
- [x] AIA standard layers
- [x] Title block
- [x] API endpoints
- [x] Integration tests

### Phase 2: Format Conversion (Planned)
- [ ] DWG export (ezdxf → ODA File Converter)
- [ ] AI export (DXF → Illustrator SDK)
- [ ] CDR export (DXF → CorelDRAW SDK)

### Phase 3: Advanced Features (Future)
- [ ] 3D foundation models (DXF 3DSOLID)
- [ ] Reinforcement cage isometric views
- [ ] BOM extraction for estimating
- [ ] Multi-sheet drawings (plan, section, details)
- [ ] Custom layer standards (client-specific)

---

## Dependencies

**Required:**
- `ezdxf==1.3.0` - DXF file generation

**Optional (for format conversion):**
- ODA File Converter - DWG export
- Adobe Illustrator SDK - AI export
- CorelDRAW Automation - CDR export

---

## Compliance & Standards

- **AIA CAD Layer Guidelines** (2nd Edition)
- **ACI 318-19** (Rebar design calculations)
- **ANSI Y14.5** (Dimensioning and tolerancing)
- **ISO 128** (Technical drawing standards)

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-org/SignX-Studio/issues
- API Docs: http://localhost:8000/docs
- Swagger UI: http://localhost:8000/docs#/cad-export

---

**Document Version:** 1.0
**Last Updated:** 2025-11-02
**Maintained By:** SignX-Studio Engineering Team
