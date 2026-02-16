# SIGNX_MANIFEST.md — SignX-Takeoff Discovery & Build Manifest

**Generated:** 2026-02-15
**Author:** Claude Opus 4.6 for Brady @ Eagle Sign Co.

---

## What Was Built

**SignX-Takeoff** — A unified channel letter takeoff and estimation tool that takes peripheral feet (PF) input and outputs KeyedIn-ready quote line items with full ABC formula traceability.

### Files Created

| File | Purpose | Size |
|------|---------|------|
| `app.py` | FastAPI server — serves UI, handles PDF upload, runs estimates | Core |
| `abc_engine.py` | ABC formula engine — Section 4B/4C/4A, 10B, LED sizing, BOM | Core |
| `extract_pf_from_pdf.py` | PyMuPDF PDF parser — extracts PF from vector bezier curves | Core |
| `warehouse.py` | Warehouse benchmark — compares estimates vs 2,443 historical jobs | Core |
| `static/index.html` | Web UI — dark theme, drag-drop PDF, all calculations, export | Frontend |
| `requirements.txt` | Python dependencies (fastapi, uvicorn, PyMuPDF, python-multipart) | Config |
| `run.bat` | One-click Windows launcher | Util |

### How to Run

```bash
cd C:\Users\Brady.EAGLE\Desktop\SIGNX\signx-takeoff
python app.py
# Open http://localhost:8765
```

Or double-click `run.bat`.

---

## Discovery Results

### Files Found (existing assets used as reference)

| Asset | Status | Location | Notes |
|-------|--------|----------|-------|
| `extract_pf_from_pdf.py` | **CREATED** (was never written) | `signx-takeoff/` | PyMuPDF bezier curve length calculator. VBA macro logic from `Module1 Sign Takeoff.bas` used as reference. |
| ABC Labor Formulas | FOUND | `data/abc-estimating/LABOR_FORMULAS_COMPLETE.txt` | 342 formulas from ABC v3.3.0.0. Machine-readable reference. |
| `abc-labor-rates-complete.md` | FOUND | `C:\Scripts\Modern Labor Standards\abc pricing guide\` | **Primary source** — clean markdown with Section 4B/4C/10B rates used verbatim. |
| `eagle-rates-fab-cheat-sheet.md` | FOUND | Same directory | Real Eagle part numbers (307-xxxx, 202-xxxx, 214-xxxx, etc.) |
| Work Code Reference | FOUND | `Keyedin/warehouse/.../local_ref_work_codes.csv` | 50+ work codes with departments |
| Sign Type Reference | FOUND | `data/abc-estimating/SIGN_TYPE_REFERENCE.txt` | Channel letter LABOR codes 162-181 |
| `ChannelLetterCalculator.csv` | FOUND | `data/abc-estimating/` | Excel-formula CSV (UTF-16), font multipliers (Block=0.44, Serif=0.48, Script=0.55) |
| `so_contracts_parsed.csv` | FOUND | `C:\Scripts\signx-warehouse\warehouse\raw\` | 25,400 rows, `billing` column = revenue. 2,443 channel letter jobs identified. |
| `abcsignc.mdb` | FOUND | `data/abc-estimating/` | Original ABC Access database (2.5MB). Not programmatically accessed yet. |
| Module1 Sign Takeoff.bas | FOUND | `CorelDraw Macros/` | VBA macro with perimeter via `seg.Length`. Reference for PDF parser algorithm. |
| ABC Pricing Guide JSON | FOUND | `C:\Scripts\keyedin-capture\reports\ABC_PRICING_GUIDE_2026_v2.json` | 148KB JSON with dept breakdowns, GM data across all sign types |
| `eagle_warehouse.db` | FOUND | `signx-warehouse/warehouse/production/` | 211MB SQLite warehouse database |
| Footage Chart PDF | FOUND | `Eagle Data/BOT TRAINING/Estimating/Footage Chart.pdf` | Original footage chart (scanned) |
| Part Numbers | FOUND | `eagle-rates-fab-cheat-sheet.md` | 100+ real Eagle Sign part numbers by category |

### Files NOT Found

| Expected Asset | Status | Notes |
|----------------|--------|-------|
| `work_code_map.json` | Not as JSON | Exists as CSV. Encoded directly in `abc_engine.py`. |
| `sign_type_recipes.json` | Not found | Partial data in SIGN_TYPE_REFERENCE.txt. Channel letter recipe built into engine. |
| `abc_translation.json` | Not found | ABC mapping built directly into `abc_engine.py` from `abc-labor-rates-complete.md`. |
| `gap_register.json` | Not found | Gap analysis was discussion-only, never serialized. |
| `decision_tree.json` | Not found | Decision logic embedded in `eagle_analyzer_v1/eagle_pricing_guide.py`. |
| Domain JSONL files | Not found | `standards.jsonl`, `business-rules.jsonl`, etc. were planned but never created. Only `.beads/` tracking JSONL exists. |

### Duplicates Identified

| Data | Locations | Recommendation |
|------|-----------|----------------|
| Warehouse raw data | `C:\Scripts\signx-warehouse\` (1.3GB), `C:\Scripts\SignX\Keyedin\warehouse\` (330MB), `C:\Scripts\merge-staging\` (331MB) | Use `C:\Scripts\signx-warehouse\` as canonical. |
| ABC .mdb database | `data/abc-estimating/abcsignc.mdb`, `data/legacy-databases/abcsignc.mdb` | Both 2.5MB, identical. Keep `abc-estimating/` version. |
| SIGNX repo | `C:\Users\Brady.EAGLE\Desktop\SIGNX\` (GitHub clone), `C:\Scripts\SignX\` (5.3GB local) | Desktop is clean GitHub clone. `C:\Scripts\SignX\` has more local data. |

---

## ABC Formulas Implemented

### Section 4B: Pan Channel Letters (Face-Lit) — per PF

| Height | 0210 Sheet | 0270 Mount | 0410 Paint | Constant |
|--------|-----------|-----------|-----------|----------|
| 7"-11" | 0.149 | 0.024 | 0.022 | 1.50 hrs |
| 12"-24" | 0.102 | 0.021 | 0.017 | 1.50 hrs |
| 25"-54" | 0.069 | 0.025 | 0.025 | 1.50 hrs |
| 55"-120" | 0.102 | 0.021 | 0.017 | 1.50 hrs |

### Section 4C: Reverse Channel (Halo) — per PF

| Height | 0210 Sheet | 0270 Mount | 0410 Paint | Constant |
|--------|-----------|-----------|-----------|----------|
| 7"-11" | 0.164 | 0.026 | 0.024 | 1.50 hrs |
| 12"-24" | 0.112 | 0.023 | 0.019 | 1.50 hrs |
| 25"-54" | 0.076 | 0.028 | 0.028 | 1.50 hrs |

### Section 10B: Install — per PF (CREW-hours)

| Height | 0-35' | Over 35' |
|--------|-------|----------|
| 7"-11" | 0.051 | 0.066 |
| 12"-24" | 0.036 | 0.047 |
| 25"-54" | 0.032 | 0.042 |

### Additional Formulas

- 0110 Design: 1.00 hr standard
- 0200 Fab Layout: 1.50 hrs constant
- 0310 LED Wire: PF x 0.015
- 0610 Load/Unload: 1.0 + 0.5 per additional unit
- 0620 Travel: (miles / 50) x 2 x crew
- 0625 Removal: Install crew-hrs x 0.65 x 2
- 0282 Freight: 0.5 per pallet

### LED Sizing

- Face-lit: Modules = PF x 1.2 x 1.05
- Halo: Modules = PF x 1.0 x 1.05
- Watts = Modules x 0.72
- PS sizing: <=80W->100W, 81-120->150W, 121-160->200W, 161-200->2x100W

### Material BOM (with real Eagle part numbers)

| Item | Part # | Formula |
|------|--------|---------|
| Face Acrylic 3/16" | 217-0485 | Face SF x 1.15 |
| Return Coil .040" | 205-0111 | PF x depth/12 x 1.05 |
| Back Aluminum .040" | 205-0180 | Face SF x 1.10 |
| Trim Cap 1" | 202-0710 | PF x 1.05 |
| LED Modules | 307-0261 | Per LED sizing |
| Power Supply | 307-0265/0264/0170 | Per LED sizing |
| Wire 18AWG | 307-0100 | Raceway LF + 20 |
| Hardware | 214-0000 | Raceway LF x 10 SF @ $0.58/SF |

---

## Warehouse Benchmark Stats

- **Source:** `so_contracts_parsed.csv` (25,400 total rows)
- **Channel letter jobs matched:** 2,443
- **Revenue column used:** `billing` (NOT `quoted_price`)
- **Average labor hours:** 12.5 hrs
- **Median labor hours:** 7.7 hrs
- **Average revenue:** $3,793.81
- **Average gross margin:** 45.2%
- **Confidence:** HIGH (2,443 samples)

---

## Validation Status

| Test Case | Expected | Result | Status |
|-----------|----------|--------|--------|
| 10 block letters @ 12" | 42.0 PF | 42.0 PF | PASS |
| 0210 Sheet (12-24" face-lit) | 1.50 + PF x 0.102 | 5.78 hrs | PASS |
| 0640 Install (12-24" 0-35') | 1.50 + PF x 0.036 | 3.01 crew-hrs | PASS |
| LED modules (face-lit 42 PF) | 42 x 1.2 x 1.05 = 53 | 53 modules | PASS |
| Warehouse benchmark loads | 2,443 jobs | 2,443 jobs | PASS |
| Server starts | Port 8765 | Starts clean | PASS |
| Ames Municipal PF validation | 78.64 ft (from CorelDRAW) | Pending PDF test | NEEDS PDF |
| Guthrie County PF validation | 133.92 ft | Pending PDF test | NEEDS PDF |

---

## What Was NOT Built (per scope)

- Structural engineering (ASCE 7-22, foundations, poles) — Sprint 2
- Shop drawing generation (ezdxf) — Sprint 3
- Monument/pylon/cabinet estimation — channel letters only
- KeyedIn browser automation (auto-entry) — output formatted for manual entry
- CorelDRAW VBA integration — separate workflow
- Machine learning cost prediction — see SignX-Intel module
