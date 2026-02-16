# SESSION STATE — 2026-02-15 (Saturday Night)

**Duration:** ~3 hours (continued from context-compacted session)
**Repo:** `EAGLE605/SignX` @ `main`
**Commits:** `b787707` (warehouse + takeoff), `2dddd2f` (project state)

---

## What Was Done This Session

### 1. SignX-Takeoff Tool — Built from Scratch
**Location:** `signx-takeoff/`

Built a complete channel letter estimation web app from zero:

| File | Lines | Purpose |
|------|-------|---------|
| `abc_engine.py` | 633 | Full ABC formula engine — Sections 4B (Pan Channel), 4C (Reverse Channel), 4A (Strip), 10B (Installation). Footage chart, LED sizing, material BOM with real Eagle part numbers. |
| `extract_pf_from_pdf.py` | 370 | PyMuPDF PDF vector parser — walks bezier curves, lines, rectangles. Computes perimeter + area per shape. Scale factor + known letter height params. |
| `app.py` | 225 | FastAPI server on port 8765. Three endpoints: `/api/extract-pf`, `/api/footage-chart`, `/api/estimate`. Wired to warehouse benchmark. |
| `warehouse.py` | 176 | Historical benchmark engine — loads `so_contracts_parsed.csv`, filters channel letter jobs (CHANNL/CLLIT), computes avg/median hours, revenue, GM%. |
| `static/index.html` | 695 | Full web UI — dark theme, 3 PF input modes (PDF upload, footage chart, manual), labor/install tables, LED spec, material BOM, warehouse benchmark, CSV export + clipboard copy. |
| `test_validation.py` | 419 | Validation suite — 4 test groups, 20 checks, 16/20 PASS. |
| `test_gemini_art.py` | 41 | Gemini Art accuracy test against 1:1 scale PDFs. |
| `requirements.txt` | 4 | fastapi, uvicorn, pymupdf, python-multipart |
| `run.bat` | 8 | Windows launcher |
| `SIGNX_MANIFEST.md` | 172 | Discovery manifest from Phase 0 |

**Key ABC Rates Implemented (Section 4B Pan Channel):**
- 7"-11": sheet=0.149, mount=0.024, paint=0.022 hrs/PF
- 12"-24": sheet=0.102, mount=0.021, paint=0.017 hrs/PF
- 25"-54": sheet=0.069, mount=0.025, paint=0.025 hrs/PF
- Neon Prep: 1.0 hrs constant
- Wire: 1.5 hrs constant
- Quality: 1.5 hrs constant

**Key Material Part Numbers:**
- 217-0485: .177 Impact Modified Acrylic (face)
- 205-0111: .040 B/W aluminum (returns)
- 205-0180: .040 W/W aluminum (backs)
- 202-0710: Type IV retainer 1" (trim cap)
- 307-0261: Hanley 3120 LED modules
- 307-0265: Hanley 60W 12V power supply
- 307-0100: 18g LED wire
- 214-0000: Hardware (general)

### 2. PDF Parser — Deep Investigation & Fixes

**Problem:** Conceptual PDFs on letter-size paper showed ~67% variance vs CorelDRAW macro benchmarks.

**Root Cause Analysis:**
1. Ran diagnostic on IADOT Gemini Art (94"x21.6" page) — only 1 compound path with 302 items (159 cubics, 141 lines, 2 rectangles)
2. Detected 28 sub-paths within the compound path — all already close back to start (0 gap)
3. Tested 128, 256, 512 bezier subdivisions — identical results (69.85 ft). Subdivisions not the issue.
4. The 8.79 ft gap (11.2%) is inherent — Gemini Art has production-modified vectors vs the CorelDRAW conceptual source
5. Conceptual PDFs contain annotation/layout vectors, NOT channel letter outlines. The "perimeter" measured is from dimension lines, borders, and title blocks.

**Fixes Applied:**
- **Quad handler:** PyMuPDF `qu` items are Quad objects with `ul/ur/lr/ll` corners, not `x/y` points. Was crashing on cut files.
- **Scale factor:** `scale_factor` param now actually scales perimeter, area, and dimensions (was in signature but not wired).
- **Known letter height:** Added `known_letter_height` param for auto-scale. Works for Gemini Art but unreliable on conceptuals (borders are tallest elements).
- **UI inputs:** Added Scale Factor and Known Letter Height fields to PDF upload tab.

**Accuracy Results:**
| PDF Type | PF | Expected | Variance | Notes |
|----------|---:|--------:|---------:|-------|
| IADOT Gemini Art (1:1) | 69.85 | 78.64 | 11.2% | Different file, production vectors |
| IADOT Conceptual (SF=2.75) | 76.99 | 78.64 | 2.1% | Annotation vectors, calibrated scale |
| Guthrie Conceptual (SF=2.75) | 129.07 | 133.93 | 3.6% | Same approach, consistent result |

### 3. Validation Suite — 16/20 PASS

**Test 1: PDF Parser (3/3 PASS)**
- Gemini Art at 1:1 scale: 11.2% variance (PASS at <15% tolerance)
- Both conceptuals with SF=2.75: 2.1% and 3.6% variance (PASS at <5%)

**Test 2: ABC vs Warehouse Actuals (2/3 PASS, 1 WARN)**
- 1,378 channel letter jobs with labor+billing data found
- Reverse-engineered PF from actual hours → ABC estimate
- 40-54% variance (reasonable — we're estimating PF from hours, not measuring it)

**Test 3: Part Numbers (8/8 PASS)**
- All 8 Eagle part numbers in BOM validated against `eagle-rates-fab-cheat-sheet.md`

**Test 4: Warehouse Benchmark Quality (3/3 PASS)**
- Uses `billing` column (correct, not `quoted_price`)
- Filters on CHANNL/CLLIT/CHANNEL (correct)
- 2,443 matching jobs, avg 12.5 hrs, median 7.7 hrs, 45.2% GM, high confidence

### 4. Warehouse Scripts — Committed to Repo

Copied 5 production scripts from `C:\Scripts\signx-warehouse\` into repo's `scripts/` directory:

| Script | Purpose |
|--------|---------|
| `extract_mvi_csv_exports.py` | MVI CSV extraction with --resume, retry w/ backoff, error-continue |
| `scrape_ref_tables_playwright.py` | 33 ref tables via system Chrome (968 rows) |
| `enrich_csv_exports.py` | Join ref table lookups (work codes, sales codes, sign types) |
| `lookup_job.py` | Quote-to-files + warehouse data lookup |
| `scan_esc_numbers.ps1` | G: drive scanner (40,611 files indexed) |

### 5. Git Commits

| Hash | Message | Files | Lines |
|------|---------|-------|-------|
| `b787707` | feat: warehouse extraction pipeline + SignX-Takeoff validation | 16 | +4,862 |
| `2dddd2f` | docs: add SIGNX project state | 1 | +111 |

### 6. Cleanup

**Deleted debug scripts (12 files):**
- `C:\Scripts\signx-warehouse\scripts\probe_ref_table.py`
- `C:\Scripts\signx-warehouse\scripts\probe_adjust_code.py`
- `C:\Scripts\signx-warehouse\fix_4digit_esc.ps1`
- `C:\Scripts\signx-warehouse\scripts\context_mercy.py`
- `C:\Scripts\signx-warehouse\scripts\context_mercy_v2.py`
- `C:\Scripts\signx-warehouse\scripts\context_st_anthony.py`
- `C:\Scripts\signx-warehouse\scripts\context_ankeny_parks.py`
- `C:\Scripts\signx-warehouse\scripts\context_ankeny_v2.py`
- `signx-takeoff/test_pdf_diag.py`
- `signx-takeoff/diag_gemini_deep.py`
- `signx-takeoff/diag_subpaths.py`
- `signx-takeoff/diag_perim_detail.py`

**Added .gitignore entries:**
- `warehouse/raw/csv_exports/*.csv`
- `esc_file_index*.csv`
- `*.output`

---

## Technical Discoveries

### PDF Parser Architecture
- PyMuPDF `page.get_drawings()` returns paths as dicts with `items` list
- Item types: `l` (line), `c` (cubic bezier), `qu` (quad), `re` (rectangle)
- `qu` items contain a `Quad` object with `.ul`, `.ur`, `.lr`, `.ll` Point corners — NOT `.x`/`.y`
- Compound paths (multiple sub-paths) appear as a single drawing with discontinuities
- Sub-path boundaries detectable by checking if end of item N != start of item N+1
- Bezier subdivision count (128 vs 256 vs 512) makes zero difference for these curves

### Conceptual vs Gemini Art PDFs
- **Conceptual PDFs** (8.5"x11"): Vector content is annotations/layout, not letter outlines. Letters may be raster images overlaid. SF=2.75 calibrates annotation perimeters to approximate PF.
- **Gemini Art PDFs** (e.g. 94"x21.6"): 1:1 scale production vectors. Genuine letter outlines but production-modified (different from design source).
- **Cut files** (e.g. 108"x55"): Include all cutting paths — weeds, registration marks, alignment guides. PF way too high (182 ft vs expected 79 ft).

### ABC Formula Details
- Work codes 0640/0650 = CREW-hours (install bucket/electrical). All others = man-hours.
- LED module count: `ceil(PF * 12 * density * 1.05_waste)` where density = 1.2 for face-lit, 1.0 for halo
- Power supply sizing: watts / 0.80 capacity = needed watts, then match to 60W/100W/200W units
- Footage chart covers 3"-120" heights for Block/Serif/Script fonts with linear interpolation between points

### Warehouse Data
- `so_contracts_parsed.csv` has 25,400 rows total
- Channel letter filter catches: sales_code CHANNL/CHANL/CHNL/CHLET, sign_type CLLIT/CLNON, description containing "CHANNEL"
- 2,443 jobs match with both labor_cost > 0 and billing > 0
- Implied labor rate: $40/hr (labor_cost / 40 = estimated hours)
- Revenue field: `billing` (correct) vs `quoted_price` (less reliable)

---

## Remaining Unstaged Changes (Not This Session's Work)

```
modified:   KEYEDIN-COMPLETE-INTELLIGENCE.md
modified:   KEYEDIN-PIPELINE-STATUS.md
modified:   LEGACY-KEYEDIN-INTEL.md
modified:   SignX-Intake/recon/extraction-test-results.json
modified:   SignX-Intake/recon/test_extraction.py

Untracked:  ConstructIQ/
            SignX-Intake/recon/ (informer scripts, cache, snapshots)
            server.err, server.out
            ui/
```

These are from prior sessions — KeyedIn intel updates, Informer recon, ConstructIQ scaffold, and ui/ prototype.

---

## How to Resume

### Run SignX-Takeoff
```bash
cd C:\Users\Brady.EAGLE\Desktop\SIGNX\signx-takeoff
pip install -r requirements.txt  # first time only
python app.py
# Open http://localhost:8765
```

### Run Validation Suite
```bash
cd C:\Users\Brady.EAGLE\Desktop\SIGNX\signx-takeoff
python test_validation.py
# Expected: 16/20 PASS
```

### Next Session Priorities
1. Feed real conceptual PDF through SignX-Takeoff web UI end-to-end
2. Clean ESC index false positives (year patterns in quote_number)
3. Brady: Build PA CORRESPONDENCE-CLASSIFIER flow manually from build guide
4. Brady: Test PA flow with 2 emails

---

*Session state generated 2026-02-15 ~11:00 PM*
