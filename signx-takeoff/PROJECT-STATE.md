# PROJECT-STATE.md -- SignX-Takeoff
Last updated: 2026-03-01 (Sprint F complete, benchmark report generated)

## Status Line
**ACTIVE -- 247 tests passing (2 skipped), 30+ API endpoints functional, calibration pipeline connected to 253K-row warehouse (36 sign types, 948 cells)**

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

### Sprint G -- In Progress
- [x] **POLLIT/POLNON regression tests** -- 13 tests added (test_pylon_regression.py, commit e0bda4e)
- [x] **Calibration pipeline fix** -- calibrate.py migrated from missing so_contract_labor to temp_labor + wo_labor (commit f3a5696). 36 sign types, 948 cells now available.
- [x] **Dead code removal** -- 4 unused _cal_* functions removed from abc_engine.py (commit a15b178)
- [x] **BLDILL/BLDNON estimator** -- Unified Takeoff logic implemented (commit 1f90739)
- [ ] **Calibration data refresh** -- run `python calibrate.py` to regenerate calibration.json with 253K-row dataset (will shift regression baselines)
- [ ] **AWNILL calibration** -- +28.6% variance (most over-estimated sign type)
- [ ] **DIRECT calibration** -- -19.1% variance (significantly under-estimated)
- [ ] **MONSF calibration** -- -18.3% variance

## Test Baseline Reference

| Suite | Tests | Status | Baseline Date |
|-------|-------|--------|---------------|
| test_validation.py | 11 | PASS | Rolling (ground truth) |
| test_regression.py | 70 | PASS | 2026-02-26 (cccba7d) |
| test_phase1.py | 32 | PASS | 2026-03-01 (Sprint F) |
| test_pylon_regression.py | 13 | PASS | 2026-03-01 (Sprint G) |
| test_boundary.py | ~15 | PASS | 2026-02-17 |
| tests/test_estimators.py | ~20 | PASS | 2026-02-17 |
| **TOTAL** | **247** | **PASS (2 skipped)** | **2026-03-01** |

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
