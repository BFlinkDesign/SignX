# SignX-Takeoff — Ground-Truth Audit Findings

Read-only audit. No application code was modified. Findings were produced by
direct execution and file reads on a Linux / Python 3.11.15 container.
`CLAUDE.md` claims a Windows host / Python 3.13; that difference matters only
for `pywin32` (see §1).

---

## 1. RUN STATUS

**It runs** (after installing dependencies — none were pre-installed and there
is no venv).

- **Entry point:** `signx-takeoff/app.py:111` — `app = FastAPI(title="SignX-Takeoff", version="2.0.0")`. Docstring: `Run: python app.py`, port 8765.
- **Venv:** none found (no `pyvenv.cfg` / `activate` / `.venv`). `requirements.txt` present.
- **Launch command:** `python app.py` or `python -m uvicorn app:app --port 8765` (run from `signx-takeoff/`).
- **Dependency resolution:** `pip install -r requirements.txt` **fails as written** — `pywin32==311` has no Linux wheel (`ERROR: No matching distribution found for pywin32==311`). The other 15 pins exist on PyPI and install cleanly. `pywin32` is used only by `mail_processor.py` (Windows/Outlook, documented Windows-only); `app.py` guards the `mail_classifier` import with `try/except ImportError`, so the server runs without it.
- **Verified:** with all deps except `pywin32` installed, `import app` succeeds (55 routes); `uvicorn app:app --port 8765` starts; `GET /api/health` → 200 `{"status":"degraded",...}` (degraded because warehouse/quote CSVs and DuckDB are Windows-path-only and absent here; `data/signx.duckdb` is a documented empty placeholder).

---

## 2. MAP

All modules are flat in `signx-takeoff/`.

| Module | Purpose |
|---|---|
| `app.py` | FastAPI server, ~49 route decorators (estimate / extract / notion / intel) |
| `abc_engine.py` | ABC engine — 11 estimator functions, rate tables, correction factors, calibration load |
| `abc_catalog.py` | Pure catalog-lookup helpers for `abc_engine` (BOM part numbers) |
| `led_catalog.py` | LED module / power-supply / face-material database |
| `calibrate.py` | Auto-calibration vs DuckDB warehouse actuals |
| `warehouse.py` | Benchmark estimate hours against historical job data |
| `extract_pf_from_pdf.py` | PyMuPDF PDF→PF parser (bezier-length perimeter summation) |
| `customer_intel.py` | Customer profiling / fuzzy matching / market benchmarks |
| `bid_scoring.py` | Heuristic win-probability scoring |
| `bid_model.py` | scikit-learn LogisticRegression win-probability model |
| `mail_classifier.py` | Regex + Claude Haiku email classifier |
| `mail_processor.py` | Win32com Outlook poller (Windows-only) |
| `mail_state.py` | SQLite state for mail intake |
| `drawing_search.py` | G: drive drawing fuzzy search |
| `project_files.py` | G: drive project-file scanner |
| `models.py` | Pydantic input-validation models |
| `sign_types.py` | Sign-type taxonomy + warehouse path resolution |
| `sign_type_analysis.py` | Analysis script (no docstring) |
| `mondf_analysis.py` | Analysis script (no docstring) |
| `t1_query.py` | One-off ad-hoc query script ("Temp query: WO 9719") |
| `check_pipeline.py` | Pipeline check script (no docstring) |

**Call path (primary endpoint):**
`POST /api/estimate` → `run_estimate(req: EstimateRequest)` (app.py:271) →
builds `JobInput` (abc_engine.py:1296) → **calls `estimate_building(job)`**
(app.py:300) → `benchmark(...)` (warehouse.py) → `_format_estimate_result(...)`
→ JSON.

**Dead code / orphans:**
- `estimate_flatpanel` (abc_engine.py:3365) — defined, zero callers (dead code).
- `mail_processor.py`, `sign_type_analysis.py`, `mondf_analysis.py`, `t1_query.py`, `check_pipeline.py` — imported by no module and no test.
- `models.py` — imported only by `test_regression.py` (and itself); `app.py` does not import it and defines its request models inline.
- No imported-but-missing files at runtime (`import app` resolves all imports, including `apex_signcalc` at `../services/signcalc-service/`). `requirements.txt` comment claims `apex_signcalc` is "imported conditionally in app.py" — it is not; app.py:105–109 imports it unconditionally with no `try/except`.

---

## 3. THE ABC ENGINE

Labor-formula logic is in `abc_engine.py`.

### Rate tables / constants (abc_engine.py:309–344)
```python
SECTION_4_RATES = {
    ConstructionType.FACE_LIT: {  # 4B Pan Channel
        HeightCategory.SMALL:  {"sheet": 0.149, "mount": 0.024, "paint": 0.022},
        HeightCategory.MEDIUM: {"sheet": 0.102, "mount": 0.021, "paint": 0.017},
        HeightCategory.LARGE:  {"sheet": 0.069, "mount": 0.025, "paint": 0.025},
        HeightCategory.XLARGE: {"sheet": 0.102, "mount": 0.021, "paint": 0.017},
    },
    ConstructionType.HALO: {  # 4C Reverse Channel
        HeightCategory.SMALL:  {"sheet": 0.164, "mount": 0.026, "paint": 0.024},
        HeightCategory.MEDIUM: {"sheet": 0.112, "mount": 0.023, "paint": 0.019},
        HeightCategory.LARGE:  {"sheet": 0.076, "mount": 0.028, "paint": 0.028},
        HeightCategory.XLARGE: {"sheet": 0.112, "mount": 0.023, "paint": 0.019},
    },
    ConstructionType.STRIP: {  # 4A Strip Channel (25"+)
        HeightCategory.LARGE:  {"sheet": 0.056, "mount": 0.059, "paint": 0.034},
        HeightCategory.XLARGE: {"sheet": 0.050, "mount": 0.041, "paint": 0.033},
        HeightCategory.SMALL:  {"sheet": 0.149, "mount": 0.024, "paint": 0.022},
        HeightCategory.MEDIUM: {"sheet": 0.102, "mount": 0.021, "paint": 0.017},
    },
}
SECTION_4_CONSTANT = 1.50  # hrs per set
DESIGN_HOURS = 1.00        # 0110
FAB_LAYOUT_HOURS = 1.50    # 0200
LED_WIRE_RATE = 0.015      # PF * 0.015 = 0310 hours

INSTALL_RATES = {
    HeightCategory.SMALL:  {"low": 0.051, "high": 0.066},
    HeightCategory.MEDIUM: {"low": 0.036, "high": 0.047},
    HeightCategory.LARGE:  {"low": 0.032, "high": 0.042},
    HeightCategory.XLARGE: {"low": 0.026, "high": 0.034},
}
INSTALL_CONSTANT_LOW = 1.50
INSTALL_CONSTANT_HIGH = 2.75
HEIGHT_FACTOR_OVER_35 = 1.35
SUBSTRATE_MULTIPLIERS = {"standard": 1.0, "eifs_unknown": 1.15,
                         "old_masonry": 1.20, "steel": 1.25}
```

### Channel-letter engine `estimate()` — core formulas (abc_engine.py:1465+)
```python
sheet_hrs = SECTION_4_CONSTANT + (total_pf * rates["sheet"])           # 0210
mount_hrs = total_pf * rates["mount"]                                  # 0270
if job.sign_type == SignType.CLLIT and mount_hrs < CLLIT_0270_FLOOR:   # 2.10
    mount_hrs = CLLIT_0270_FLOOR
led_wire_hrs = total_pf * LED_WIRE_RATE                                # 0310
paint_hrs = total_pf * rates["paint"]                                  # 0410
# Fab OT (9200): round(fab_prob * fab_mean, 2); emitted if >= 0.50
install_crew_hrs = (install_constant + total_pf * install_rate) * substrate_mult  # 0640
floor = INSTALL_FLOOR.get(job.sign_type.value)
if floor is not None and install_crew_hrs < floor:
    install_crew_hrs = floor
load_hrs = 1.0 + 0.5 * max(0, job.num_units - 1)                       # 0610
freight_hrs = 0.5 * pallets   # pallets = max(1, (job.num_units + 1)//2) # 0282
# Install OT (9600): round(inst_prob * inst_mean, 2); emitted if >= 0.50
```
- `face_sf = total_pf * job.letter_height_inches / 24.0` (abc_engine.py:1501)
- Travel (`_make_travel_line`, 1411): `travel_hrs = round((job.miles_one_way / 50.0) * 2 * job.crew_size, 2)`
- Raceway removal (1453): `rw_hrs = RACEWAY_REMOVAL_BASE + max(0, rw_lf - 10) * RACEWAY_REMOVAL_PER_LF` (`0.75` base, `0.05`/LF)

### Phase-0 floor / OT tables (abc_engine.py:434–516)
```python
INSTALL_FLOOR = {"CLLIT":9.90,"POLLIT":7.20,"MONDF":4.50,"MONSF":8.40,"DIRECT":7.20,
 "AWNNON":9.75,"AWNILL":9.75,"GEMINI":4.20,"LED":4.50,"ALULIT":4.80,"FLATPNL":2.40}
REMOVAL_FLOOR = {"CLLIT":3.90,"MONDF":2.40,"POLLIT":2.70,"OTHER":4.20,"BLDILL":2.40,
 "GEMINI":1.80,"DIRECT":1.50,"VINYL":1.20,"LED":2.10,"POLNON":1.20,"CLNON":1.50,
 "BLDNON":3.60,"AWNNON":3.00,"AWNILL":3.00,"MONSF":10.20}
REMOVAL_DEFAULT = 2.40
CLLIT_0270_FLOOR = 2.10
OT_FACTORS = {  # (fab_ot_prob, fab_ot_mean, inst_ot_prob, inst_ot_mean, expected_total)
 "CLLIT":(0.346,8.09,0.471,4.43,4.89), "POLLIT":(0.325,6.43,0.386,3.04,3.26),
 "MONDF":(0.521,4.10,0.527,3.66,4.07), "MONSF":(0.814,8.71,0.302,1.37,7.50),
 "DIRECT":(0.352,4.25,0.593,2.52,2.99),"AWNNON":(0.479,4.18,0.625,6.14,5.84),
 "GEMINI":(0.0,0.0,0.478,1.81,0.87),   "LED":(0.0,0.0,0.453,1.76,0.80)}
```
These hardcoded dicts are overwritten at import by `data/calibration.json` via
the `if _CALIBRATION:` block (abc_engine.py:489–527); runtime values are
whatever `calibration.json` holds.

### Correction-factor tables (verbatim, abc_engine.py:539–664)
- `MONDF_CORRECTION_NONLIT` = `{"0210":0.36,"0215":0.32,"0220":1.61,"0235":0.93,"0270":0.82,"0410":1.65,"0420":1.38,"0630":None}`
- `MONDF_CORRECTION_LIT` = `{"0210":0.54,"0215":0.73,"0220":4.65,"0235":1.23,"0270":0.79,"0340":4.25,"0410":1.10,"0420":1.17,"0630":None}`
- `MONSF_CORRECTION_NONLIT` = `{"0210":0.32,"0215":0.32,"0220":0.48,"0235":0.61,"0270":0.36,"0410":0.58,"0420":0.78,"0630":None}`
- `MONSF_CORRECTION_LIT` = `{"0210":0.54,"0215":0.54,"0220":0.72,"0235":0.82,"0270":0.55,"0310":1.65,"0340":1.83,"0410":0.80,"0420":0.85,"0630":None}`
- `POLLIT_CORRECTION` = `{"0210":0.45,"0215":1.80,"0220":1.40,"0235":0.80,"0270":1.10,"0340":3.50,"0410":1.30,"0420":1.30,"0650":None}`
- `ALULIT_CORRECTION` = `{"0210":0.40,"0220":1.50,"0235":0.60,"0270":1.30,"0410":1.40,"0420":1.20,"0630":None}`
- Hardcoded medians: `MONDF_0630_MEDIAN_NONLIT=3.63`, `MONDF_0630_MEDIAN_LIT=5.13`, `MONSF_0630_MEDIAN_NONLIT=3.00`, `POLLIT_0650_MEDIAN=8.50`, `POLLIT_0605_MEDIAN=14.00`, `ALULIT_0630_MEDIAN=5.76` (full set 568–664).

### Other estimators — formula cores
- **`estimate_monument`** (1789): `abc_210 = SECTION_2_CONSTANT + (total_sf * sec2_rate)`; `corr_200 = 3.6 if is_illuminated else 1.75` (MONDF) / `1.0` (MONSF); `abc_215 = total_sf * sec2_rate * 0.75`.
- **`estimate_pylon`** (2402): `abc_215 = total_sf*sec2_rate*1.50`; `abc_220 = SECTION_2E_CONSTANT + ext_lf*0.208`; `abc_235 = total_sf*sec2_rate*0.30`; `abc_270 = total_sf*sec2_rate`; `abc_340 = 1.0 + total_sf*0.030`; `install_hrs = POLLIT_0650_MEDIAN`.
- **`estimate_cabinet`** (2705): `abc_210 = SECTION_2_CONSTANT + total_sf*sec2_rate`; `abc_235 = total_sf*sec2_rate*0.40`; `abc_340 = 1.0 + total_sf*0.020`.
- **`estimate_awning`** (2196): `hrs_200 = max(3.00, total_sf*0.08)`; `hrs_310 = max(1.50, total_sf*0.04)`; `freight_hrs = total_sf*0.004`; `load_hrs = total_sf*0.037`; `install_1man_hrs = total_sf*0.285`; `install_2man_rate = 0.142`.
- **`estimate_directional`** (2982): `hrs_220 = max(2.10, round(total_sf*0.14,2))`; `hrs_235 = round(total_sf*0.06,2)`; `hrs_270 = max(1.50, round(total_sf*0.10,2))`; `hrs_410 = max(0.50, round(paint_sf*0.05,2))`; `hrs_420 = max(0.75, round(paint_sf*0.07,2))`; `hrs_520 = max(0.50,total_sf*0.06)`; `hrs_550 = max(0.50,total_sf*0.08)`; `ot_fab_rate = 0.035`.
- **`estimate_dimensional`** (3201): `est_face_sf = lc*(lh**2)*0.006`; `hrs_240 = round(lc*0.15,2)`; `hrs_270 = round(lc*0.08,2)`; `hrs_410 = round(paint_rate["constant"] + paint_sf*paint_rate["labor"], 2)`; `install_hrs = INSTALL_FLOOR.get("GEMINI",4.20)`; `ot_inst_rate = 0.048`.
- **`estimate_building`** (3530): `total_sf = job.sign_sf_per_face * job.num_faces`; `hrs_220 = max(2.0, perimeter_lf*0.15)`; `hrs_210 = max(1.5, total_sf*0.18)`; `hrs_260 = max(0.75, total_sf*0.05)`; `hrs_270 = max(1.5, total_sf*0.10)`; `elec_hrs = max(1.5, total_sf*0.08)`; `inst_hrs = 2.25 if is_illuminated else 1.75`.
- **`estimate_removal`** (2116): `removal_hrs = REMOVAL_FLOOR.get(sign_type_key)`; PF fallback `round(pf*0.051/2 + 0.5, 2)`; else `REMOVAL_DEFAULT`.
- **`estimate_flatpanel`** (3365): defined, **never called** — `sheet_hrs = max(1.0,total_sf*0.033)`, `paint_hrs = 1.0+total_sf*0.017`, `vinyl_cut_hrs = 1.0+total_sf*0.02`, `vinyl_app_hrs = 1.0+total_sf*0.03`, `install_hrs = max(1.50,total_sf*0.05)`.

---

## 4. THE PF PARSER

**Parser:** `extract_pf_from_pdf.py:126` —
`extract_pf_from_pdf(pdf_bytes, filename, page_num, scale_factor, known_letter_height)`.
Sums cubic-bezier (`_bezier_length`, 128 subdivisions), line, quad, rect
perimeters in PDF points; `pts_to_inches = 1.0/72.0`; applies `scale_factor`;
filters paths `< 1.0` perimeter-inch; `total_pf = total_perimeter_inches / 12.0`.

**Test suite:** `test_validation.py` Test 1 (lines 14–114) is the only
pytest-style PF suite. `test_gemini_art.py` also calls the parser.

**Real result for PF-parser tests: 0 pass, 0 fail, 4 skipped.**

| Test | Result |
|---|---|
| `test_pdf_parser_pf_within_tolerance[iadot_gemini_art]` | SKIPPED |
| `test_pdf_parser_pf_within_tolerance[guthrie_county_conceptual]` | SKIPPED |
| `test_pdf_parser_pf_within_tolerance[iadot_conceptual]` | SKIPPED |
| `test_pdf_parser_info_only_file` | SKIPPED |

Every PF test skips: each fixture is a hardcoded absolute Windows path that
does not exist here and is not in the repo, e.g.
`G:\I\Iowa Dept of Transportation\2025\AMES - 800 LINCOLN WAY\GEMINI\IADOT Ames Bldg Letters Brushed Alum Q39946 12562-2.pdf`
(expected_pf 78.64, tol 0.15);
`G:\G\Guthrie Co. State Bank\...\Guthrie Co Panora Channel Ltrs 0126-40593-00.pdf`
(expected_pf 133.93, tol 0.05);
`G:\I\Iowa Dept of Transportation\2025\AMES - 800 LINCOLN WAY\IADOT Ames Bldg Letters Brushed Alum 0925-39946-00.pdf`
(expected_pf 78.64, tol 0.05);
`C:\Users\Brady.EAGLE\Downloads\BRADYF_Infinity Neuro Channel Letters 0625-39541.pdf`
(info-only). The test guards with `if not p.exists(): pytest.skip(...)`.
**No `*.pdf` fixtures are committed anywhere in the repo.** No failing cases to
list because the parser is never executed against any input.
`test_gemini_art.py` is not a pytest test (no `test_` functions; module-level
loop that prints "FILE NOT FOUND"). **The PF parser has no executable test
coverage in this repo.**

---

## 5. TESTS OVERALL

Full collected suite (`pytest --continue-on-collection-errors`,
`signx-takeoff/`), raw result:

**284 passed, 8 skipped, 1 failed, 1 collection error.**

- **Failed (1):** `test_validation.py::test_warehouse_benchmark_returns_result` — `assert b is not None`; `benchmark(15.0)` returns `None` (empty warehouse DB).
- **Collection error (1):** `tests/test_intel_live.py` — `KeyError: 'total_revenue'` at module import (line 43 asserts at collection time against empty warehouse).
- **Skipped (8):** 4 PF-parser tests; 2 `test_abc_vs_actuals_*` (warehouse CSV absent); 2 warehouse/DuckDB schema guards.
- **Warnings (2):** `abc_engine.py:1725` `DeprecationWarning` — emits part `202-0710` for Trim Cap but warehouse confirms `202-0710` is the Type IV Retainer; and `calculate_materials called without trim_color; defaulting to black`.

**Files named `test_*` that are not pytest tests (collect 0 tests, never gate):**
`test_gemini_art.py`; `tests/test_endpoints_live.py` (script with `def main()`
/ `__main__`, no `test_` functions); `tests/test_intel_live.py` (errors at
collection).

**Untested:**
- PF parser: 0 executable tests.
- **HTTP API estimation layer: 0 executable tests.** The only test that hits `POST /api/estimate` is `tests/test_endpoints_live.py`, which pytest does not collect. `test_regression.py` / `test_phase1.py` / `test_boundary.py` call engine functions directly, never through `app.py` routes — the route wiring is entirely untested.
- CLAUDE.md claims "Suite: 252 pass, 0 fail, 2 skip" / "Validation 11/11" / "Regression 75/75"; actual here is 284 / 8 / 1 / 1, and `test_validation.py` = 4 passed, 6 skipped, 1 failed.

---

## 6. GAP LIST

1. `requirements.txt` does not install on Linux: `pywin32==311` has no Linux distribution; `pip install -r requirements.txt` aborts.
2. No virtual environment and no installed dependencies are shipped; bare repo cannot run until ~15 packages are installed.
3. `requirements.txt` comment states `apex_signcalc` is "imported conditionally in app.py" — false; `app.py:105–109` imports it unconditionally (no `try/except`).
4. `POST /api/estimate` (app.py:300), the documented primary channel-letter endpoint, calls `estimate_building(job)` instead of `estimate(job)`.
5. The channel-letter engine `estimate()` is imported (app.py:62) but never invoked by any route in `app.py`.
6. Because of #4, `POST /api/estimate` with valid channel-letter input `{"pf_source":"manual","pf_value":42.0,"height_inches":24,"construction":"face_lit","font_type":"block"}` returns `total_pf:0.0`, `construction:"building_stick"`, `labor:[]`, `install:[]`, `total_man_hours:0.0`, `total_crew_hours:0.0`, warning `"sign_sf_per_face required for building estimate."` — while a direct `estimate()` call with the same inputs returns `total_pf:42.0`, `13.78` man-hrs, `3.6` crew-hrs, 6 labor + 4 install lines.
7. `POST /api/notion/takeoff` dispatch (app.py:1196–1204): the `est_key == "channel_letter"` branch also calls `estimate_building(job)` on a channel-letter `JobInput`.
8. `tests/test_endpoints_live.py` is named `test_*` but defines no pytest test functions (only `def main()` / `__main__`); its `check("CL estimate returns hours", d.get("total_man_hours",0) > 0)` would fail but is never collected/run — the bug in #4/#6 is uncaught.
9. `tests/test_intel_live.py` raises `KeyError: 'total_revenue'` at collection time, interrupting suite collection without `--continue-on-collection-errors`.
10. `test_validation.py::test_warehouse_benchmark_returns_result` fails: `benchmark(15.0)` returns `None`.
11. All 4 PF-parser tests in `test_validation.py` skip; fixtures are hardcoded absolute Windows paths; no `.pdf` fixtures exist in the repo.
12. `test_gemini_art.py` is named `test_*` but has no test functions; uses non-existent Windows PDF paths.
13. `estimate_flatpanel` (abc_engine.py:3365) is defined but has zero callers (dead code).
14. Orphan modules imported by nothing (incl. tests): `mail_processor.py`, `sign_type_analysis.py`, `mondf_analysis.py`, `t1_query.py`, `check_pipeline.py`.
15. `models.py` is imported only by `test_regression.py`; `app.py` does not use it despite CLAUDE.md describing it as the request/response models for all estimators.
16. `HEIGHT_FACTOR_OVER_35 = 1.35` (abc_engine.py:359) is referenced only in a warning string (abc_engine.py:1737); the over-35ft install path uses `INSTALL_CONSTANT_HIGH` / `INSTALL_RATES["high"]` and never multiplies by `1.35`.
17. `abc_engine.py:1725` emits BOM part `202-0710` for "Trim Cap" while the in-code `DeprecationWarning` states warehouse confirms `202-0710` is the Type IV Retainer (wrong part number unless `ABC_CATALOG_ENRICHMENT=on`).
18. `calculate_materials` is called without `trim_color`, defaulting to black (`UserWarning`; hardcoded fallback rather than threaded input).
19. Hardcoded warehouse-derived constants (`INSTALL_FLOOR`, `REMOVAL_FLOOR`, `OT_FACTORS`, all `*_CORRECTION*` / `*_MEDIAN` tables) are baseline literals overwritten at import only if `data/calibration.json` is present.
20. `data/signx.duckdb` is an empty placeholder (0 tables); warehouse benchmarking, `bid_model` training (`0 labeled quotes`), and `/api/health` are degraded / non-functional without the Windows-only real warehouse path.
21. CLAUDE.md test-status claims ("252 pass / 0 fail / 2 skip", "Validation 11/11", "Regression 75/75") do not match the actual run (284 passed / 8 skipped / 1 failed / 1 collection error).

**Most likely cause of "output is wrong":** items 4, 6, 7 — the
channel-letter endpoint(s) run `estimate_building` instead of the
channel-letter `estimate()`, so the primary estimate returns all-zero / empty
output regardless of PF input. The engine function itself computes correctly
when called directly.
