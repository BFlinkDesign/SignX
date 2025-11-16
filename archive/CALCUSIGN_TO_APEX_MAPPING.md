# Calcusign → APEX Feature Mapping

## Workflow Alignment

Calcusign's multi-tab linear workflow maps cleanly to APEX's deterministic engineering pipeline.

---

## Tab 1: Login & Tool Suite
**Calcusign**: Login via calcusign.com, choose tool (Pylons/Blade/Wall/Awnings)

**APEX**: 
- ✅ Service authentication (via API gateway)
- ✅ Service discovery for signs-service vs signcalc-service vs agent-cad
- 🔄 Add UI-web orchestrator tab selection

---

## Tab 2: Overview (Project Setup)
**Calcusign**: 
- Project Name, Manager, Manager Email (pedigree)
- Project Notes text area
- File Upload (artwork, brand books, plans) → "Project files" bundle

**APEX Gaps**:
- ❌ Missing: `project_name`, `project_manager`, `manager_email` fields
- ❌ Missing: File upload → blob storage → refs in `provenance`
- ✅ Present: `provenance` dict for passthrough

**Action**: Add to `SignDesignRequest`:
```python
class Project(BaseModel):
    name: str
    manager: str
    manager_email: EmailStr
    notes: Optional[str] = None

class SignDesignRequest(BaseModel):
    project: Optional[Project] = None
    provenance: Dict[str, Any] | None = None
```

---

## Tab 3: Site Detail (Environmental)
**Calcusign**: 
- Site Name, Address
- **"Get Wind Speed"** button → Google + wind API → auto-fetch V & snow

**APEX**: 
- ✅ `site.lat`, `site.lon` (from geocoding)
- ✅ `site.exposure`, `topography`
- ❌ **Missing: "Get Wind Speed" API integration**

**Action**: Add wind API integration to `/v1/signs/design`:
```python
# If site.address provided, geocode & fetch wind
# If V_basic not provided in request, call wind API
# Update assumptions: "Wind speed from OpenWeatherMap API for address X"
```

**Options**:
- OpenWeatherMap wind data
- NOAA ASOS weather station nearest-neighbor
- ASCE 7-16 wind speed map digitization

---

## Tab 4: Cabinet (Sign Dimensions)
**Calcusign**: 
- Overall Height, Cabinet Width, Cabinet Height
- 2D drawing updates in real-time
- Depth (calculation-only)
- PSF of Cabinet (default 10)

**APEX**: 
- ✅ `sign.width_ft`, `sign.height_ft`, `centroid_height_ft`
- ✅ `sign.gross_weight_lbf` (~total weight)
- 🔄 **Partial**: Missing `depth_ft` and `psf` breakdown

**Action**: Add to `SignGeom`:
```python
class SignGeom(BaseModel):
    width_ft: float
    height_ft: float
    depth_ft: Optional[float] = 0.25  # default 3" cabinet
    centroid_height_ft: float
    psf: float = 10.0  # default
    gross_weight_lbf: float  # computed or explicit
```

---

## Tab 5: Supports (Foundation Type)
**Calcusign**: 
- Foundation Type: Direct Burial vs Base Plate
- Pole Material: Steel vs Aluminum (locked for >15 ft)
- Add Extra Supports, Single vs per-support footings, Match Plates

**APEX**: 
- ✅ `embed.type: "direct" | "baseplate"`
- ❌ **Missing: Material lock rule** (aluminum limit 15 ft)
- ❌ **Missing: Multi-pole support**

**Action**: Add to `SignDesignRequest`:
```python
class SignDesignRequest(BaseModel):
    support_options: List[Literal["pipe", "W", "tube"]]
    material: Literal["steel", "aluminum"] = "steel"
    num_supports: Literal[1, 2, 3, 4] = 1
    
# In main.py validation:
if req.material == "aluminum" and req.sign.centroid_height_ft > 15.0:
    raise HTTPException(
        422, 
        detail="Aluminum supports limited to 15 ft height per industry practice"
    )
```

---

## Tab 6: Pole (Smart Filtering)
**Calcusign Key Feature**: 
- Pole Shape, Steel Type, Sort Order
- **Dynamic dropdown**: Only shows sizes that work for project (pre-filtered)
- Starts at absolute minimum ("value engineered")

**APEX**: 
- ✅ Support selection (pipe/W/tube)
- ✅ Sorted by weight ascending (value-optimized)
- ✅ Filtered to passing sections only
- ✅ Returns minimum passing section

**Status**: ✅ **Already Implemented Correctly**

The `catalogs_for_order()` → `check_section()` loop in `main.py` does this:
1. Load catalogs for requested families
2. Sort ascending by weight
3. Check each section (bending + deflection)
4. Return first passing section

**Enhancement**: Add `sort_by` parameter:
```python
support_options: ["pipe", "W", "tube"]
sort_by: Literal["weight", "modulus", "size"] = "weight"
```

---

## Tab 7: Footings (Dynamic Depth)
**Calcusign**: 
- Footing Shape: Round vs Square
- Diameter input → **Minimum Depth auto-recalculates**
- Spread Footing option

**APEX**: 
- ✅ Foundation shape (cyl/rect)
- ✅ `design_embed()` returns dia + depth
- 🔄 **Partial**: Depth doesn't auto-recalc from dia

**Status**: Already deterministic, but depth is a function of M, not dia. 

**Action**: Add constraint-based iteration:
```python
# If user provides max_dia, iterate depth until passing
# If user provides max_embed, iterate dia until passing
# Update assumptions: "Depth constrained by auger max 48-in"
```

---

## Tab 8: Complete Project
### Path 1: Estimation (Free PDF)
**Calcusign**: 
- **"Download PDF of project"** → 4-page instant output:
  1. Cover: Project name, address, plot plan
  2. Elevation: Dimensions, pole/footing sizes
  3. Design Output: Max torques, concrete yards, key data
  4. General Notes

**APEX**: 
- ✅ `render_pdf()` via WeasyPrint
- ❌ **Missing: formatted 4-page template** with cover/elevation/summary/notes

**Action**: Create `apex_signcalc/templates/report.html`:
```html
<!DOCTYPE html>
<html><head><title>{{ project.name }}</title></head>
<body>
  <div class="cover">
    <h1>{{ project.name }}</h1>
    <p>{{ site.address }}</p>
  </div>
  <div class="page-break"></div>
  <div class="elevation">
    <h2>Elevation Drawing</h2>
    <p>Pole: {{ selected.support.designation }}</p>
    <p>Footing: {{ foundation.dia_in }}" dia × {{ foundation.depth_in }}" deep</p>
  </div>
  ...
</body></html>
```

### Path 2: Formal Engineering (Paid)
**Calcusign**: 
- Send to engineering → project mgmt software
- Add-ons: Calculation Packet ($35), Hard Copies
- 3-day turnaround

**APEX**: 
- ✅ Already returns canonical envelope
- ❌ **Missing: pricing model & add-on selection**

**Future**: Add `use_case` enum to request:
```python
use_case: Literal["estimate", "engineering", "permit"]
```

---

## Missing APEX Features

1. **Wind API Integration** (Tab 3)
   - Geocode address → lat/lon
   - Fetch V_basic from OpenWeatherMap/NOAA
   - Auto-populate site data

2. **Material Lock Rules** (Tab 5)
   - Aluminum max 15 ft
   - Multi-pole support count

3. **Formatted PDF Template** (Tab 8)
   - 4-page layout: cover/elevation/design/notes
   - Concrete yards calc
   - Max torques summary

4. **File Upload → Blobs** (Tab 2)
   - POST `/v1/upload`
   - Store in artifacts/blobs
   - Return blob_ref for provenance

5. **Concrete Yards Calculator**
   ```python
   def concrete_yards(dia_ft: float, depth_ft: float) -> float:
       cy = pi * (dia_ft/2)**2 * depth_ft / 27.0
       return round(cy, 2)
   ```

---

## APEX Advantages

✅ **Already Better**:
- Standards pack SHA256 for auditability
- Multi-jurisdiction (US/EU)
- Abstain paths with reasons
- Blob_refs for artifacts
- Deterministic output hashes
- Full trace in envelope

✅ **Architecture**:
- Agent-based pipeline (wind → member → foundation → report)
- FSQueue idempotency
- Containerized with healthchecks
- No hardcoded secrets

---

## Next Actions

1. Add wind API integration endpoint
2. Create PDF template with 4-page layout
3. Add concrete yards calculator
4. Add file upload endpoint
5. Add material lock validation
6. Wire into orchestrator DAG

**Priority**: PDF template + concrete calc for "estimation" output parity.

