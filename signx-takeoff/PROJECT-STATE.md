# PROJECT-STATE.md â€” SignX-Takeoff
Last updated: 2026-02-26 (overnight task â€” baseline refresh + CLAUDE.md)

## Status Line
**ACTIVE â€” 70/70 regression pass, 11/11 validation pass, 30+ API endpoints functional**

---

## Completed Phases

### Phase 0 â€” Foundation (2026-02 early)
- [x] FastAPI server scaffolded on port 8765
- [x] ABC engine core â€” channel letter estimation (PF-based, Sections 4/10B)
- [x] PDF peripheral feet extractor (PyMuPDF, Bezier curve length)
- [x] Footage chart interpolation
- [x] Basic warehouse benchmark vs so_contracts_parsed.csv

### Phase 1 â€” Engine Expansion
- [x] Monument estimator MONDF/MONSF (SF-based, DuckDB actuals)
- [x] Awning estimator AWNNON (SF + linear foot, Eagle actuals)
- [x] Removal estimator (crew-based, CLLIT/MONDF/POLLIT)
- [x] Directional estimator (DIRECT)
- [x] Dimensional letter estimator (GEMINI)
- [x] Pylon estimator (POLLIT)
- [x] Cabinet estimator
- [x] Part number generation (Eagle PN conventions)
- [x] Unit tests â€” 32/32 pass (test_phase1.py)

### Phase 2 â€” Calibration + Intelligence
- [x] Auto-calibration engine (DuckDB warehouse P50 x buffer / ABC fallback / industry rails)
- [x] calibration.json hot-reload (POST /api/calibrate)
- [x] LED module catalog integrated (Eagle Sign + LED Wizard 8)
- [x] Customer intelligence engine (fuzzy matching, historical profiling)
- [x] Win probability heuristic (bid_scoring.py, 6 factors, 18,972 quotes)
- [x] ML win probability (bid_model.py, LogisticRegression, 12 features)
- [x] Drawing search (G: drive, fuzzy folder matching)
- [x] Dossier completeness (project_files.py)
- [x] Validation suite â€” 11/11 pass (test_validation.py)

### Phase 3 â€” Email Intake + Bid Pipeline (Sprint F)
- [x] Win32com Outlook poller (mail_processor.py, 4 salesperson folders, 60s loop)
- [x] Dual email classifier â€” regex bid intake + Claude Haiku correspondence routing
- [x] Notion bid pipeline integration (GET /api/notion/bids, POST /api/notion/takeoff)
- [x] SMS + webhook notifications (POST /api/notify/bid-ready)
- [x] PATCH /api/notion/bid (bid status updates)
- [x] POST /api/keyedin/format (KeyedIn-ready output)
- [x] Customer intel API (/api/intel/*)
- [x] Bid scoring API (/api/bid/score, /api/bid/win-rates)

### Phase 4 â€” Structural Engineering (Sprint F cont.)
- [x] Wind load (ASCE 7-22) â€” POST /api/structural/wind
- [x] Foundation design (Broms/IBC) â€” POST /api/structural/foundation
- [x] Anchor design â€” POST /api/structural/anchors
- [x] Member check (AISC 360) â€” POST /api/structural/member-check
- [x] Member select â€” POST /api/structural/member-select
- [x] Full structural design package â€” POST /api/structural/full-design
- [x] Standard section library â€” GET /api/structural/sections

### Phase 5 â€” Regression Hardening (2026-02-26)
- [x] Baseline refresh after engine updates (cccba7d)
- [x] 70/70 regression tests pass with fresh baselines
- [x] CLAUDE.md + PROJECT-STATE.md created

---

## Open Items

### High Priority
- [ ] **Part number validation** â€” validate engine PN outputs against live KeyedIn catalog
  (currently Eagle PN conventions, not validated against system)
- [ ] **Regression watch** â€” re-run `test_regression.py` after any abc_engine.py change
  to catch drift early (baselines at cccba7d = 2026-02-26)
- [ ] **Pylon/cabinet structural wiring** â€” estimators exist but not connected to structural engine

### Medium Priority
- [ ] **G: drive bash access** â€” MSYS path translation blocks `ls G:/...` from bash.
  Mitigation: use Python pathlib. Do not use bash `ls` for G: drive paths.
- [x] **POLNON** — non-illuminated pylon (POLLIT logic with electrical skip)
- [ ] **Outdoor advertising** â€” billboard/large format not yet addressed
- [ ] **Sub-contractor RFQ** â€” sub_rfq_sender.py pattern from signx-intake not yet ported here
- [ ] **ML model refresh** â€” bid_model.py trained on 2025 data; retrain when Q1 2026 closes

### Known Blockers
- [ ] **Win32com Outlook** â€” mail_processor.py requires Windows + Outlook installed locally.
  Cannot be tested in headless/Linux CI. Skip mail tests in automated pipelines.

---

## Test Baseline Reference

| Suite | Tests | Status | Baseline Date |
|-------|-------|--------|---------------|
| test_validation.py | 11 | PASS | Rolling (ground truth) |
| test_regression.py | 70 | PASS | 2026-02-26 (cccba7d) |
| test_phase1.py | 32 | PASS | 2026-02-17 |
| test_boundary.py | ~15 | PASS | 2026-02-17 |
| tests/test_estimators.py | ~20 | PASS | 2026-02-17 |

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
