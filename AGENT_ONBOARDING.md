# SignX Agent Onboarding — Master Briefing
**Last verified:** 2026-03-02 (Claude Opus 4.6 — live test run)
**Point here first.** This is the single source of truth for all incoming agents.

---

## STOP — Read Before Touching Anything

### Current Test Reality (live run 2026-03-02)
```
244 passed, 4 FAILED, 2 skipped in 14.55s
```

**ARCHITECT_BRIEF.md and fleet-briefing-codex.md claim "250/250" or "zero-defect" — THOSE ARE WRONG.**
Trust this document and PROJECT-STATE.md, not ARCHITECT_BRIEF.md.

### The 4 Failing Tests (must fix before claiming "done")
| Test | File | Expected | Got | Root Cause |
|------|------|----------|-----|-----------|
| `test_cl_halo_total_man_hours_locked` | test_regression.py | 34.26h | 32.91h | Gemini regression in CL HALO path |
| `test_cl_strip_total_man_hours_locked` | test_regression.py | (locked) | different | Same Sprint G regression |
| `test_building_extrusion_total_man_hours_locked` | test_regression.py | 15.37h | 20.35h | `estimate_building()` changed without updating baseline |
| `test_halo_vs_face_lit_different_hours` | test_boundary.py | HALO != FACE_LIT | 21.56 == 21.56 | CRITICAL BUG: HALO using FACE_LIT (Section 4B) rates instead of 4C |

**The HALO = FACE_LIT bug is the most critical.** Section 4C reverse-channel rates are defined correctly in `SECTION_4_RATES` but are not being applied. Investigate around `abc_engine.py:1340-1355` (rates lookup). Check for calibration.json override or construction type coercion.

---

## Directory Map

```
C:/Users/Brady.EAGLE/Desktop/SignX/signx-takeoff/   ENGINE
  abc_engine.py           Core estimating engine (3,407 lines)
  app.py                  FastAPI server, port 8765
  calibrate.py            DuckDB calibration pipeline
  data/calibration.json   Loaded on import — stale, needs regen
  data/signx.duckdb       SYMLINK or copy — see REAL path below
  test_*.py               Test suites (run with timeouts!)

C:/Scripts/signx-warehouse/warehouse/signx.duckdb   CANONICAL WAREHOUSE
  253,000+ labor rows, 22 years Eagle Sign history
  Use WAREHOUSE_DB_PATHS / find_warehouse_db() — don't hardcode path

C:/Scripts/keyedin-capture/                          GWT SCRAPE SCRIPTS
  gwt_replay_test.py      Working replay (replace UUIDs, POST to commandService)
  gwt_response_parser.py  //OK[...] parser
  reports/                30 captured Informer report payloads

C:/Scripts/signx-intake/                             EMAIL / PA INTAKE
  classify_email.py       Live M365 inbox classifier
  m365_api.py             PA HTTP wrapper
  intake_server.py        Webhook endpoints

C:/Scripts/signx-agent/                              KEYEDIN PLAYWRIGHT AGENT
  (TypeScript/Playwright — separate project)

C:/Scripts/merge-staging/signx-warehouse/            OLDER STANDALONE REPO (Feb 2026)
  Has its own beads tracker. Don't confuse with main project.

C:/Users/Brady.EAGLE/Desktop/SignX/calculators/abc-engineering/legacy/parsed_data/mconv_dat.json
  Material conversion data — source of truth for material mappings (209KB)

C:/Users/Brady.EAGLE/Desktop/SignX/ARCHITECT_BRIEF.md
  ARCHITECTURAL REFERENCE ONLY — version history claims are inflated.
  Cross-check all claims against PROJECT-STATE.md.
```

---

## Critical Engine Rules

```
ALL work codes = man-hours EXCEPT:
  0640 (crane/lift)      = crew-hours
  0650 (service truck)   = crew-hours

Revenue column in warehouse = 'billing' (NOT 'quoted_price')

SignX boundary (HARD): output ONLY work codes + hours + part numbers
  NO $/hr rates, NO cost tables, NO dollar conversions
  KeyedIn handles all dollars — never cross this line

Logo PF: use biggest coefficient row (0.051 per questionnaire)

Engine outputs: hours, part numbers, material quantities ONLY
```

---

## Test Commands (always use timeouts)

```bash
cd C:/Users/Brady.EAGLE/Desktop/SignX/signx-takeoff

# Full suite — run first, establish baseline
timeout 300 pytest --timeout=30 --timeout-method=thread -q

# Ground truth only (11 tests, fastest signal)
timeout 60 pytest test_validation.py --timeout=30 -v

# Regression suite (70 tests — baseline-locked values)
timeout 120 pytest test_regression.py --timeout=30 -v

# Specific failing tests
timeout 60 pytest test_regression.py::test_cl_halo_total_man_hours_locked --timeout=30 -v
timeout 60 pytest test_boundary.py::test_halo_vs_face_lit_different_hours --timeout=30 -v
```

**After any abc_engine.py change:** run `test_validation.py` first (ground truth), then `test_regression.py`.
**If calibration.json is regenerated:** regression baselines WILL shift — update with `pytest --update-baselines` equivalent.

---

## Active Constraints

| Rule | Detail |
|------|--------|
| **NO KeyedIn ERP access before 5:30 PM (business hours)** | Use offline DuckDB only |
| **No hardcoded credentials** | All keys via `.env` + python-dotenv |
| **Regex anti-patterns** | Never use broad `.*` wildcards for code injection — caused Gemini Task 18/19 to delete estimator logic |
| **Secrets in chat** | Never paste API keys — transcript is plaintext JSONL |
| **Notion API token** | Expired as of 2026-03-02 (401 unauthorized) — needs rotation |

---

## Sprint G — Accurate Status (2026-03-02)

| Item | Status |
|------|--------|
| POLLIT/POLNON regression tests | DONE (e0bda4e) |
| calibrate.py fix (temp_labor + wo_labor) | DONE (f3a5696) |
| Dead code removal (4 _cal_* functions) | DONE (a15b178) |
| BLDILL/BLDNON estimator (`estimate_building`) | DONE — but **test baseline broken** |
| HALO Section 4C rates bug | **OPEN — 4 tests failing** |
| calibration.json regeneration | **OPEN** — will shift regression baselines |
| AWNILL variance (+28.6%) | **OPEN** |
| DIRECT variance (-19.1%) | **OPEN** |
| MONSF variance (-18.3%) | **OPEN** |
| Notion token rotation | **OPEN** (401 as of today) |

---

## KeyedIn GWT Scrape (after 5:30 PM)

**What works:**
- 30 Informer report payloads captured at `C:/Scripts/keyedin-capture/reports/`
- `gwt_replay_test.py` — replace session UUIDs (clientId/authToken) with fresh from login, POST to `commandService`
- `gwt_response_parser.py` — parses `//OK[...]` GWT responses to CSV

**Next step:** ViewRPCService.getData pagination using ViewToken (already extracted). See `memory/KEYEDIN-EXTRACTION.md`.

**CRITICAL:** Excel exports from KeyedIn TRUNCATE data. Always use Print/View payloads, not Excel exports.

---

## Known Gemini CLI Patterns (read fleet-lessons-gemini.md first)

Gemini tends to:
1. Declare tasks "FINAL SHIP" / "ZERO DEFECT" prematurely
2. Use broad regex wildcards (`re.sub(..., flags=re.DOTALL)`) that corrupt function bodies
3. Inject code that references undefined local variables
4. Ship 5 tasks in 25 minutes with 60% defect rate
5. Report wrong row counts (checked wrong file)

**Always verify Gemini's claims against actual test runs, not self-reported status.**

---

## Warehouse Stats (verified)

| Metric | Value |
|--------|-------|
| Total labor rows | 253,000+ |
| Sign types mapped | 37 |
| Primary focus | CLLIT, MONDF, BLDILL, POLLIT |
| GM% target | 40-45% |
| Validation | `v_unified_labor` or `temp_labor JOIN wo_labor` |

**Project-level validation only** — large jobs (DSM Airport, Availa Bank) are fragmented across many sub-WOs. Aggregate by base WO number before comparing to engine output.

---

## Notion Bid Pipeline

API token expired (401 as of 2026-03-02). Notify Brady to rotate at console.notion.so.

**Property names (verified 2026-02-27):**
- `Quote #` (not "Quote Number")
- `Est. Value` (not "Bid Amount")
- `Delivery Date` (not "Due Date")
- `Pipeline Stage` (not "Sub-Status")

---

## Where to Find Things

| Need | Location |
|------|----------|
| ABC rate tables | `abc_engine.py:300-350` (SECTION_4_RATES, INSTALL_RATES) |
| Material BOM formula | `abc_engine.py:1022-1100` (calculate_materials) |
| Building sign estimator | `abc_engine.py:3299+` (estimate_building) |
| Monument estimator | `abc_engine.py:~1600+` (estimate_monument) |
| Pylon estimator | `abc_engine.py:~2400+` (estimate_pylon) |
| ABC formulas source | `data/abc-estimating/abc-labor-rates-complete.md` |
| ABC JSON source | `C:/Scripts/keyedin-capture/reports/ABC_PRICING_GUIDE_2026_v2.json` |
| Material lookup | `calculators/abc-engineering/legacy/parsed_data/mconv_dat.json` |
| Work code reference | `abc_engine.py:WORK_CODES dict` |
| Regression baselines | `test_regression.py` (baseline = commit cccba7d, 2026-02-26) |
| Lessons log | `C:/Temp/fleet-lessons-gemini.md` |
