# CLAUDE.md — SignX-Takeoff
Read this first, every session.

---

## What This Is

**SignX-Takeoff** — Eagle Sign Co.'s unified sign estimation and bid management platform.
- ABC formula engine calibrated against 27,000+ historical warehouse jobs
- FastAPI server on port 8765
- Email intake pipeline via Win32com Outlook
- Structural engineering (ASCE 7-22, AISC 360, ACI 318-19)
- Customer intelligence, win probability ML, Notion bid pipeline integration

**Entry point:** `app.py` (port 8765)
**Stack:** Python 3.13 / FastAPI / SQLite / DuckDB / PyMuPDF / scikit-learn / Anthropic Haiku / Notion API

---

## How to Start

```bash
cd C:/Users/Brady.EAGLE/Desktop/SIGNX/signx-takeoff

# Standard
python app.py

# Or explicit uvicorn (reload mode)
python -m uvicorn app:app --port 8765 --reload

# Windows
run.bat
```

Open: http://localhost:8765

---

## Key Files

| File | Purpose |
|------|---------|
| `app.py` | FastAPI server — 30+ REST endpoints, Notion, SMS, email hooks |
| `abc_engine.py` | ABC estimation engine — 8 sign-type estimators, rate tables, calibration |
| `models.py` | Pydantic request/response models for all estimators |
| `led_catalog.py` | LED module database (Eagle Sign + LED Wizard 8 catalog) |
| `calibrate.py` | Auto-calibration vs DuckDB warehouse actuals |
| `warehouse.py` | Benchmark against so_contracts_parsed.csv (25,400 rows) |
| `extract_pf_from_pdf.py` | PyMuPDF PDF parser — Bezier curve PF extraction |
| `customer_intel.py` | Customer profiling, fuzzy matching, market benchmarks |
| `bid_scoring.py` | Win probability heuristic (6 factors, 18,972 quotes) |
| `bid_model.py` | ML win probability — scikit-learn LogisticRegression, 12 features |
| `mail_classifier.py` | Dual classifier: regex bid intake + Claude Haiku routing |
| `mail_processor.py` | Win32com Outlook poller (4 salesperson folders, every 60s) |
| `drawing_search.py` | G: drive drawing search — fuzzy folder matching |
| `project_files.py` | G: drive file scanner — dossier completeness |
| `data/calibration.json` | Calibration output (loaded on engine import) |
| `data/signx.duckdb` | Warehouse DuckDB — labor_rolled_up view, 27,000+ jobs |

---

## API Endpoints

### Estimation
```
POST /api/estimate               — Channel letters (CLLIT/CLNON)  <- primary
POST /api/estimate/monument      — Monuments (MONDF/MONSF)
POST /api/estimate/awning        — Awnings (AWNNON)
POST /api/estimate/removal       — Standalone removal (crew-based)
POST /api/estimate/pylon         — Pylon/pole signs (POLLIT)
POST /api/estimate/cabinet       — Cabinet signs
POST /api/estimate/directional   — Directional/wayfinding (DIRECT)
POST /api/estimate/dimensional   — Dimensional letters (GEMINI)
```

### Channel Letter Estimate — Primary Endpoint

```
POST /api/estimate
Content-Type: application/json

{
  "sign_type": "CLLIT",
  "pf": 42.0,
  "letter_height": 24,
  "construction_type": "RACEWAY",
  "font_type": "BLOCK",
  "mount_location": "WALL",
  "illuminated": true,
  "quantity": 1
}
```

Response includes: work codes, labor hours per code, BOM (part numbers + quantities), install hours, total hours.

### Other Endpoints
```
POST /api/extract-pf            — PDF upload → peripheral feet extraction
POST /api/footage-chart         — Footage chart interpolation
GET  /api/calibration           — Current calibration state
POST /api/calibrate             — Re-run calibration vs warehouse
GET  /api/led/catalog           — LED module catalog
POST /api/structural/wind       — Wind load (ASCE 7-22)
POST /api/structural/full-design — Full structural package
GET  /api/dossier               — Customer dossier (drawings + files)
GET  /api/notion/bids           — Notion bid pipeline
POST /api/notion/takeoff        — Push takeoff to Notion
POST /api/keyedin/format        — Format output for KeyedIn quote entry
GET  /api/intel/customer/{name} — Customer intelligence
GET  /api/intel/similar         — Similar historical jobs
POST /api/bid/score             — Win probability score
```

---

## Sign Types Supported

| Code | Name | Status | Estimator |
|------|------|--------|-----------|
| CLLIT | Channel Letter Illuminated | COMPLETE | `estimate()` |
| CLNON | Channel Letter Non-Illuminated | COMPLETE | `estimate()` |
| MONDF | Monument Double-Face | COMPLETE | `estimate_monument()` |
| MONSF | Monument Single-Face | COMPLETE | `estimate_monument()` |
| AWNNON | Awning Non-Illuminated | COMPLETE | `estimate_awning()` |
| AWNILL | Awning Illuminated (LED) | COMPLETE | `estimate_awning()` |
| DIRECT | Directional/Wayfinding | COMPLETE | `estimate_directional()` |
| GEMINI | Dimensional Letters | COMPLETE | `estimate_dimensional()` |
| POLLIT | Pole/Pylon Illuminated | COMPLETE | `estimate_pylon()` |
| CABINET | Cabinet/Box Signs | COMPLETE | `estimate_cabinet()` |
| REMOVAL | Standalone removal | COMPLETE | `estimate_removal()` |

---

## Known Gaps / Pending Work

- **Part number validation:** No live lookup against KeyedIn part catalog — engine outputs Eagle PN conventions (e.g., `307-0xxx`, `202-0xxx`) but does not validate them
- **Pylon/cabinet structural integration:** estimators exist but not yet wired to structural engine
- **Regression baselines:** refreshed 2026-03-02 (Sprint H) — re-run after any engine change
- **Opportunities (0 records):** Kimco Opportunities entity is empty — not yet in use by Eagle
- **NCRs (0 records):** Quality entity not yet populated in prototype
- **G: drive from bash:** `ls G:/...` returns nothing from MSYS bash — Python pathlib CAN access G: (PDF tests pass). This is MSYS path translation, not a drive access issue.
- **Mail poller Win32com:** `mail_processor.py` requires Windows + Outlook installed. Do not run on non-Windows.

---

## Test Commands

```bash
cd C:/Users/Brady.EAGLE/Desktop/SIGNX/signx-takeoff

# Ground truth validation (11 tests — PDF parser, ABC vs actuals, warehouse quality)
timeout 120 pytest test_validation.py --timeout=30 -v

# Full regression suite (70 tests — locked baseline values per sign type)
timeout 120 pytest test_regression.py --timeout=30 -v

# Phase 1 unit tests (32 tests)
timeout 120 pytest test_phase1.py --timeout=30 -v

# All tests
timeout 300 pytest --timeout=30 --timeout-method=thread -v

# Specific test
timeout 60 pytest test_regression.py -k "test_channel_face_lit" --timeout=30 -v
```

### Test File Summary

| File | Tests | Purpose |
|------|-------|---------|
| `test_validation.py` | 11 | Ground truth: PDF parser, ABC formula vs actuals, part numbers, warehouse quality |
| `test_regression.py` | 75 | Locked baseline: all sign types, exact hour values (abs=0.01 tolerance) |
| `test_phase1.py` | 32 | Unit tests: engine inputs, model validation, calibration (2 skip = warehouse schema guards) |
| `test_pylon_regression.py` | 13 | POLLIT/POLNON locked baselines (Sprint G) |
| `test_boundary.py` | ~15 | Edge cases: extreme PF values, missing fields, zero qty |
| `tests/test_estimators.py` | ~20 | Estimator-level unit tests |
| `tests/test_performance.py` | ~5 | Response time benchmarks |

---

## Current Status

- **Suite: 252 pass, 0 fail, 2 skip** (live run 2026-03-02, Sprint H complete)
- **Validation:** 11/11 pass (test_validation.py)
- **Regression:** 75/75 pass (test_regression.py, baselines updated 2026-03-02)
- **Phase 1:** 32/32 pass (2 skipped = DuckDB normalized-schema guards, intentional)
- **API:** All 30+ endpoints functional
- **Calibration:** Auto-calibration via DuckDB warehouse actuals
- **LED catalog:** Integrated (Eagle Sign + LED Wizard 8 catalog)
- **Structural:** ASCE 7-22 wind + AISC 360 + ACI 318-19 + Broms foundation

---

## Engine Conventions (CRITICAL)

```
ALL work codes = man-hours EXCEPT:
  0640 (crane/lift) = crew-hours
  0650 (service truck) = crew-hours

Revenue in warehouse = 'billing' column (NOT 'quoted_price')
Logo PF: use biggest coefficient row (0.051 per questionnaire)

Engine outputs ONLY: work codes, labor hours, part numbers, material quantities
NO $/hr rates, cost tables, or dollar conversions — KeyedIn handles all dollars
SignX boundary: output work codes + hours + part numbers ONLY. Never dollars.

New SignType added to enum → ALSO update test_phase1.py test_sign_type_enum_members hardcoded set
MONSF ≠ MONDF: separate MONSF_CORRECTION_NONLIT/LIT tables; estimate_monument() branches on is_monsf
DIRECT primary fab code = 0220 (Extrusions), NOT 0210 (Sheet Metal) — directionals are alum extrusion frames
Vinyl formula pattern: max(P50_floor, SF * rate) — NOT 1.0 + SF * rate (overcounts small signs)
Pydantic last-wins: duplicate fields in a unified JobInput model cause monument defaults to override channel letter inputs
```

---

## Calibration & Warehouse DB

- **Real warehouse DB:** `C:\Scripts\signx-warehouse\warehouse\signx.duckdb` — `data/signx.duckdb` is always empty (0 tables)
- **`find_warehouse_db()`** in `sign_types.py` resolves the path; use it instead of hardcoding
- **calibration.json auto-populates** `INSTALL_FLOOR` at module import — always query at runtime, not the constant
- **Work-code P50 query:** `SELECT work_code, PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY hours) FROM temp_labor t JOIN wo_labor w ON t.work_order = w.wo WHERE w.sign_type = 'X' GROUP BY work_code`

## Data Files

```
data/
  abc-estimating/          — ABC Pricing Guide source materials (1974, updated 2026)
  calibration.json         — Auto-calibration output (reload with POST /api/calibrate)
  signx.duckdb             — EMPTY placeholder — real warehouse is C:\Scripts\signx-warehouse\warehouse\signx.duckdb
  so_contracts_parsed.csv  — 25,400 rows historical quotes (billing = revenue col)

External (read-only):
  G:\Customers2\           — Customer project files (Windows path, Python pathlib OK)
  DuckDB warehouse         — 27,000+ job records, 22 years Eagle history
```

---

## Environment Variables

All loaded via `.env` (python-dotenv). Never hardcoded.

| Variable | Purpose |
|----------|---------|
| `NOTION_TOKEN` | Notion API key |
| `NOTION_BID_PIPELINE` | Notion bid pipeline DB ID |
| `NOTIFY_WEBHOOK_URL` | Notification webhook |
| `SMS_PHONE` | SMS recipient phone |
| `SMTP_SERVER` | SMTP for email notifications |
| `ANTHROPIC_API_KEY` | Claude Haiku for mail classification |

---

## Agent Comms (Sprint coordination)

- **Task channel:** `signx-intel` — all Sprint task traffic (TASK-N, Gemini proactive research)
  `signx-takeoff.jsonl` is always empty — do not read it
- **Dispatch command:**
  ```bash
  COMMS_AGENT="claude/architect" COMMS_CHANNELS="C:/Users/Brady.EAGLE/.ai/channels" \
    bash C:/tools/agent-comms/comms.sh task signx-intel "TASK-N [agent/role] ..."
  ```
- **Read channel:**
  ```bash
  python -c "
  import json
  with open('C:/Users/Brady.EAGLE/.ai/channels/signx-intel.jsonl') as f:
      lines = f.read().strip().split('\n')
  for l in lines[-20:]:
      d = json.loads(l)
      print(d['ts'][:16], d.get('from','?').ljust(14), d.get('type','?').ljust(8), d.get('msg','')[:100])
  "
  ```
- **Sprint close:** After each sprint completes, update the Sprint History section in this file

---

## Operating Rules

- Auto-approve: file edits, test runs, calibration runs, read-only API calls
- Stop and ask: any write to Notion, any send to Outlook, any structural calculation flagged as out-of-spec
- Never hardcode credentials — always `.env` via dotenv
- Always run timeout-protected pytest: `--timeout=30 --timeout-method=thread`
- After engine changes: run `test_validation.py` first (ground truth), then `test_regression.py`

---

## Sprint History

### Sprint F — COMPLETE (2026-03-01, commit 3505878)
- Centralized DuckDB path resolution (find_warehouse_db + WAREHOUSE_DB_PATHS)
- Fixed test_phase1 OT failures, DuckDB skipif guards

### Sprint G — COMPLETE (2026-03-02)
- Fixed HALO Section 4C bug (Pydantic last-wins — duplicate JobInput fields)
- Fixed BLDILL regression baseline (20.35h), removed dead code in estimate_building()
- Added POLLIT/POLNON regression tests (test_pylon_regression.py, 13 tests)
- Calibration pipeline fix (temp_labor + wo_labor)

### Sprint H — COMPLETE (2026-03-02)
- AWNILL illuminated awning estimator — 4 regression tests locked (60SF=46.30h)
- DIRECT fix: replaced 0210 Sheet Metal with 0220 Extrusions; warehouse P50 formulas; 20SF=16.30h
- MONSF fix: separate correction tables from MONDF; 20SF lit=25.54h (avg=28.27h)
- Calibration data refresh (calibrate.py)
- Suite: **252 pass, 0 fail, 2 skip**

### Open (Sprint I)
- [ ] Notion token rotation (401 unauthorized — Brady must rotate)
- [ ] RTLT/ILLUM/FFACE/PRNGRA sign types route to OTHER fallback (not yet estimated)
- [ ] Part number validation vs live KeyedIn catalog

## Last Updated
2026-03-02 — Sprint H complete. 252/0/2.
