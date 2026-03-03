# PROJECT-STATE.md -- SignX-Takeoff
Last updated: 2026-03-03 (Sprint H complete; Sprint I dispatched to Gemini + Codex)

## Status Line
**ACTIVE -- 252 passing, 0 FAILING, 2 skipped (live run 2026-03-02) -- Sprint H complete**

---

## Completed Phases

### Phase 0 -- Foundation (2026-02 early)
- [x] FastAPI server scaffolded on port 8765
- [x] ABC engine core -- channel letter estimation (PF-based, Sections 4/10B)
- [x] PDF peripheral feet extractor (PyMuPDF, Bezier curve length)
- [x] Footage chart interpolation
- [x] Basic warehouse benchmark vs so_contracts_parsed.csv

### Phase 1 -- Engine Expansion
- [x] Monument estimator MONDF/MONSF (SF-based, DuckDB actuals)
- [x] Awning estimator AWNNON (SF + linear foot, Eagle actuals)
- [x] Removal estimator (crew-based, CLLIT/MONDF/POLLIT)
- [x] Directional estimator (DIRECT)
- [x] Dimensional letter estimator (GEMINI)
- [x] Pylon estimator (POLLIT)
- [x] Cabinet estimator
- [x] Part number generation (Eagle PN conventions)
- [x] Unit tests -- 32/32 pass (test_phase1.py)

### Phase 2 -- Calibration + Intelligence
- [x] Auto-calibration engine (DuckDB warehouse P50 x buffer / ABC fallback / industry rails)
- [x] calibration.json hot-reload (POST /api/calibrate)
- [x] LED module catalog integrated (Eagle Sign + LED Wizard 8)
- [x] Customer intelligence engine (fuzzy matching, historical profiling)
- [x] Win probability heuristic (bid_scoring.py, 6 factors, 18,972 quotes)
- [x] ML win probability (bid_model.py, LogisticRegression, 12 features)
- [x] Drawing search (G: drive, fuzzy folder matching)
- [x] Dossier completeness (project_files.py)
- [x] Validation suite -- 11/11 pass (test_validation.py)

### Phase 3 -- Email Intake + Bid Pipeline (Sprint F)
- [x] Win32com Outlook poller (mail_processor.py, 4 salesperson folders, 60s loop)
- [x] Dual email classifier -- regex bid intake + Claude Haiku correspondence routing
- [x] Notion bid pipeline integration (GET /api/notion/bids, POST /api/notion/takeoff)
- [x] SMS + webhook notifications (POST /api/notify/bid-ready)
- [x] PATCH /api/notion/bid (bid status updates)
- [x] POST /api/keyedin/format (KeyedIn-ready output)
- [x] Customer intel API (/api/intel/*)
- [x] Bid scoring API (/api/bid/score, /api/bid/win-rates)

### Phase 4 -- Structural Engineering (Sprint F cont.)
- [x] Wind load (ASCE 7-22) -- POST /api/structural/wind
- [x] Foundation design (Broms/IBC) -- POST /api/structural/foundation
- [x] Anchor design -- POST /api/structural/anchors
- [x] Member check (AISC 360) -- POST /api/structural/member-check
- [x] Member select -- POST /api/structural/member-select
- [x] Full structural design package -- POST /api/structural/full-design
- [x] Standard section library -- GET /api/structural/sections

### Phase 5 -- Regression Hardening (2026-02-26)
- [x] Baseline refresh after engine updates (cccba7d)
- [x] 70/70 regression tests pass with fresh baselines
- [x] CLAUDE.md + PROJECT-STATE.md created

### Phase 6 -- Sprint F (2026-03-01, commit 3505878)
- [x] Centralized DuckDB path resolution (find_warehouse_db + WAREHOUSE_DB_PATHS)
- [x] Fixed test_phase1 OT failures, DuckDB skipif guards
- [x] 178 tests passing, 2 skipped, 15 files modified, net -56 lines
- [x] Warehouse benchmark: 253K-row cost detail labor loaded into DuckDB (temp_labor)
- [x] Est vs Actual analysis by sign type (CLLIT +1.5%, MONDF -3.5%, POLLIT -9.9%)
- [x] Per-work-code breakdown for all sign types (benchmark report at C:\Temp\warehouse-benchmark-report.md)

---

## Open Items

### High Priority
- [ ] **Part number validation** -- validate engine PN outputs against live KeyedIn catalog
  (currently Eagle PN conventions, not validated against system)
- [ ] **Regression watch** -- re-run `test_regression.py` after any abc_engine.py change
  to catch drift early (baselines at cccba7d = 2026-02-26)
- [ ] **Pylon/cabinet structural wiring** -- estimators exist but not connected to structural engine

### Medium Priority
- [x] **G: drive bash access** -- RESOLVED. Pathlib used consistently throughout
  (drawing_search.py, project_files.py, app.py). Confirmed by Gemini audit 2026-03-01.
- [x] **POLNON** -- non-illuminated pylon (POLLIT logic with electrical skip)
- [ ] **Outdoor advertising** -- billboard/large format not yet addressed
- [ ] **Sub-contractor RFQ** -- sub_rfq_sender.py pattern from signx-intake not yet ported here
- [ ] **ML model refresh** -- bid_model.py trained on 2025 data; retrain when Q1 2026 closes

### Known Blockers
- [ ] **Win32com Outlook** -- mail_processor.py requires Windows + Outlook installed locally.
  Cannot be tested in headless/Linux CI. Skip mail tests in automated pipelines.

---

### Sprint G -- COMPLETE (2026-03-02 Claude Opus 4.6)

#### Fixed (Claude Opus 4.6, 2026-03-02)
- [x] **HALO Section 4C bug** -- Root cause: Gemini Sprint G added duplicate `is_illuminated` etc. to `JobInput`. Pydantic last-wins caused monument defaults to override all channel letters. Fixed by removing duplicates from Unified block + changing `estimate()` to use `sign_type==CLNON` instead of `is_illuminated` check.
- [x] **BLDILL regression baseline** -- Updated from stale 15.37h (pre-rewrite) to verified 20.35h. Fixed BOM PN from 202-0390 (wrong) to 202-0387 (EAGLE_INVENTORY['ABC_EXTRUSION_9']).
- [x] **estimate_building() dead code** -- Removed unreachable old function body (22 lines after `return result`).

#### Completed (Gemini Sprint G)
- [x] **POLLIT/POLNON regression tests** -- 13 tests added (test_pylon_regression.py, e0bda4e)
- [x] **Calibration pipeline fix** -- temp_labor + wo_labor (f3a5696). 36 sign types, 948 cells.
- [x] **Dead code removal** -- 4 unused _cal_* functions removed (a15b178)
- [x] **BLDILL/BLDNON estimator** -- `estimate_building()` added.

#### Open (Sprint H)
- [x] **Calibration data refresh** -- `python calibrate.py` (Codex TASK-3 complete 2026-03-02)
- [x] **AWNILL** -- FIXED 2026-03-02: added AWNILL SignType + 0200 + 0310 codes; 60SF=46.30h locked
- [x] **DIRECT** -- FIXED 2026-03-02: replaced 0210 w/ 0220, fixed vinyl/paint/travel formulas; 20SF now 16.3h (avg=16.73h)
- [x] **MONSF** -- FIXED 2026-03-02: added MONSF correction factors; 20SF lit now 25.54h (was 58.20h, avg=28.27h)
- [ ] **Notion token rotation** -- 401 unauthorized (Brady must rotate)

---

### Sprint I -- In Progress (2026-03-03)

#### Dispatched
- [ ] **TASK-7 [gemini/researcher]** -- RTLT/ILLUM/FFACE/PRNGRA estimator spec: query warehouse P50 per work code, deliver spec table for implementation
- [ ] **TASK-8 [codex/deployer]** -- Fix app.py AwningRequest missing `is_illuminated` field; wire through to estimate_awning(); verify 4 AWNILL regression tests pass

#### Open
- [ ] **RTLT/ILLUM implementation** -- implement estimators after Gemini TASK-7 spec lands
- [ ] **Notion token rotation** -- Brady must rotate; all Notion writes blocked until then
- [ ] **Part number validation** -- validate engine PN outputs vs live KeyedIn catalog

## Test Baseline Reference

| Suite | Tests | Status | Notes |
|-------|-------|--------|-------|
| test_validation.py | 11 | PASS | Ground truth — must always pass |
| test_regression.py | 75 | PASS | +4 AWNILL tests added 2026-03-02 |
| test_phase1.py | 32 | PASS | AWNILL added to enum set 2026-03-02 |
| test_pylon_regression.py | 13 | PASS | Sprint G |
| test_boundary.py | ~15 | PASS | HALO != FACE_LIT verified |
| tests/test_estimators.py | ~20 | PASS | |
| **TOTAL** | **254 collected** | **252 PASS, 0 FAIL, 2 SKIP** | **Live run 2026-03-02** |

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| FastAPI over Flask | Async support for concurrent structural calcs + email polling |
| DuckDB for warehouse | 27,000 row analytical queries in <100ms; no server needed |
| Pydantic models in models.py | Centralized validation, avoids duplication across estimators |
| Engine outputs hours only | SignX boundary: KeyedIn owns all dollar conversions |
| calibration.json auto-reload | Engine can recalibrate without restart |
| Haiku for mail classification | Fast + cheap; full Opus not needed for intake routing |
| SQLite for mail state | Dedup + follow-up timers without external DB dependency |
