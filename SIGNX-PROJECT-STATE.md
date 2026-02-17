# SIGNX PROJECT STATE

**Updated:** 2026-02-17 20:35
**Repo:** `EAGLE605/SignX` (main)
**Last Commit:** `4d13ab7` — CI/CD fully green
**Server:** `signx-takeoff/app.py` on port 8765 (47 API endpoints)

---

## Current Sprint: F — Dashboard Autonomy & Intelligence Hardening

**Goal:** Every tab works autonomously. Drop a PDF or type a customer name → complete takeoff, BOM, engineering, drawings — zero manual busywork.

### Priority Issues (from 2026-02-17 user review)

| Issue | Tab | Severity | Details |
|-------|-----|----------|---------|
| ~~**Bid Pipeline stale**~~ | Bid Pipeline | FIXED | Inline stage dropdown + PATCH /api/notion/bid. Real-time Notion updates. |
| **Intelligence dossier incomplete** | Intelligence | HIGH | "Build Dossier" returns halfassed results. Warehouse missing data for some customers. Drawing search can't find CAT Scale. |
| ~~**Drawing search weak**~~ | Intelligence | FIXED | Fuzzy matching with difflib + 13 customer aliases. CAT Scale resolves correctly. |
| **Engineering tab confusing** | Engineering | MEDIUM | "Elevation" field is jargon. Too many manual inputs. Should auto-fill from sign type + Iowa defaults. |
| **Pole signs missing** | Estimating | MEDIUM | No separate pole sign tab. POLLIT exists under "Pylon" but no POLNON. Non-illuminated pole signs need their own estimator or the Pylon tab needs a non-illuminated toggle. |
| **No autonomous pipeline** | ALL | HIGH | Every tab is a separate manual calculator. Need: single intake → auto-route → complete output. |
| **PDF dimension detection wrong** | Channel Letters | HIGH | THD PDF shows 17x11" paper → system reads paper size, not actual sign dimensions. Needs dimension callout parsing or title block extraction. |
| **Non-technical user support** | Intelligence | MEDIUM | Natural language queries for new employees who don't know industry terms. |

---

## Dashboard Tabs (12 total)

| Tab | Status | Endpoints | Notes |
|-----|--------|-----------|-------|
| **Channel Letters** | WORKING | `/api/extract-pf`, `/api/estimate` | PDF upload, PF chart, manual PF. Needs better PDF dimension detection. |
| **Monument** | WORKING | `/api/estimate/monument` | SF-based, warehouse-corrected. |
| **Awning** | WORKING | `/api/estimate/awning` | SF-based, Eagle actuals from jobs #11530/#11532. |
| **Removal** | WORKING | `/api/estimate/removal` | Two-tier: warehouse P50 primary, PF fallback. Now has raceway adder. |
| **Pylon** | WORKING | `/api/estimate/pylon` | POLLIT only. Missing non-illuminated pole signs. |
| **Cabinet** | WORKING | `/api/estimate/cabinet` | ALULIT/ALUNON, warehouse-corrected. |
| **Directional** | PROVISIONAL | `/api/estimate/directional` | Warehouse data sparse, marked provisional. |
| **Dimensional** | PROVISIONAL | `/api/estimate/dimensional` | GEMINI letters, provisional. |
| **Bid Pipeline** | WORKING | `/api/notion/bids`, `/api/notion/takeoff`, `/api/notion/bid` | Inline stage dropdown PATCHes Notion. Status updates live. |
| **Engineering** | PARTIAL | 6 structural endpoints | Wind, foundation, member, anchors. Too many manual fields. "Elevation" confusing. |
| **Intelligence** | STALE | `/api/dossier`, `/api/intel/*`, `/api/bid/*` | Dossier incomplete, drawing search weak, no multi-location breakout. |
| **Calibration** | WORKING | `/api/calibration`, `/api/calibrate` | New: auto-calibration from warehouse P50. 30 types, 497 cells. |

---

## API Endpoints (47 total)

### Estimation (8)
- `POST /api/extract-pf` — PDF peripheral foot extraction
- `POST /api/footage-chart` — PF from height/count chart
- `POST /api/estimate` — Channel letter estimation
- `POST /api/estimate/monument` — Monument estimation
- `POST /api/estimate/awning` — Awning estimation
- `POST /api/estimate/removal` — Removal estimation (+ raceway adder)
- `POST /api/estimate/pylon` — Pylon estimation
- `POST /api/estimate/cabinet` — Cabinet estimation
- `POST /api/estimate/directional` — Directional [PROVISIONAL]
- `POST /api/estimate/dimensional` — Dimensional [PROVISIONAL]

### Calibration (2)
- `GET /api/calibration` — Current calibration data
- `POST /api/calibrate` — Trigger recalibration from warehouse

### Structural Engineering (6)
- `POST /api/structural/wind` — ASCE 7-22 wind load
- `POST /api/structural/foundation` — Broms/Hansen/Czerniak/IBC
- `POST /api/structural/anchors` — ACI 318 anchor bolts
- `POST /api/structural/member-check` — AISC 360 member check
- `POST /api/structural/member-select` — Auto-select member
- `POST /api/structural/full-design` — Complete sign design
- `GET /api/structural/sections` — AISC shapes catalog

### Drawings (2)
- `GET /api/drawings/search` — G: drive drawing search
- `POST /api/drawings/bid-lookup` — Drawing lookup by bid

### Notion/Pipeline (5)
- `GET /api/notion/bids` — Bid pipeline from Notion
- `POST /api/notion/takeoff` — Run takeoff for Notion bid
- `PATCH /api/notion/bid` — Update bid status/value/salesman/blocking in Notion
- `POST /api/notify/bid-ready` — SMS notification
- `GET /api/notion/flow-status` — PA Flow status

### Intelligence (10)
- `GET /api/dossier` — Customer dossier
- `POST /api/dossier/prefetch` — Prefetch dossier data
- `GET /api/cache/stats` — Cache statistics
- `GET /api/intel/customer/{name}` — Customer profile
- `GET /api/intel/similar` — Similar past jobs
- `GET /api/intel/market/{sign_type}` — Market intel by sign type
- `GET /api/intel/warehouse` — Warehouse stats
- `GET /api/project-files` — Project file search (G: drive)
- `POST /api/bid/score` — Heuristic win probability
- `GET /api/bid/win-rates` — Win rate stats
- `GET /api/bid/price-recommendation` — Price recommendation
- `GET /api/bid/scoring-health` — Scoring engine health
- `POST /api/bid/ml-score` — ML win probability (logistic regression)
- `GET /api/bid/ml-diagnostics` — ML model diagnostics

### KeyedIn (1)
- `POST /api/keyedin/format` — Format estimate for KeyedIn entry

---

## Estimator Engine (abc_engine.py)

| Estimator | Function | Sign Types | Status | Calibrated |
|-----------|----------|-----------|--------|------------|
| Channel Letters | `estimate()` | CLLIT, CLNON | PRODUCTION | YES (497 cells) |
| Monument | `estimate_monument()` | MONDF, MONSF | PRODUCTION | YES |
| Awning | `estimate_awning()` | AWNNON | PRODUCTION | YES |
| Removal | `estimate_removal()` | ALL types | PRODUCTION | YES (16 types) |
| Pylon | `estimate_pylon()` | POLLIT | PRODUCTION | YES |
| Cabinet | `estimate_cabinet()` | ALULIT, ALUNON | PRODUCTION | YES |
| Directional | `estimate_directional()` | DIRECT | PROVISIONAL | YES (sparse) |
| Dimensional | `estimate_dimensional()` | GEMINI | PROVISIONAL | YES (sparse) |
| Flat Panel | `estimate_flatpanel()` | FLATPNL | PROVISIONAL | NO (0 warehouse jobs) |

### Recent Engine Improvements (2026-02-17)
- **Auto-calibration**: `calibrate.py` queries warehouse → generates `calibration.json` → abc_engine auto-loads on import
- **30 sign types**, 497 calibration cells (sign_type x work_code with n>=3)
- **27 install floors** (was 10 hardcoded), 16 removal floors, 20 OT factor sets
- **Batch travel dedup**: `batch_index` / `batch_size` on JobInput — sign #2+ gets 0 travel
- **Raceway removal adder**: `has_raceway` flag → 0.75h base + 0.05h/LF extra labor
- **`_make_travel_line()` / `_make_raceway_removal_line()`** shared helpers across all 8 estimators
- **Three-tier calibration**: Warehouse P50×buffer (primary), ABC formula (fallback), industry rails (sanity check)

### Missing Estimators / Sign Types
- **POLNON** — Non-illuminated pole sign (currently only POLLIT exists)
- **BLDILL / BLDNON** — Building-mounted signs (enum exists, no estimator)
- **LED** — LED retrofit/conversion (enum exists, no estimator)
- **VINYL** — Standalone vinyl graphics (enum exists, no estimator)
- **NEON** — Neon (legacy, enum exists, no estimator)

---

## Structural Engineering (signcalc-service)

| Module | File | Status | Standards |
|--------|------|--------|-----------|
| Wind Loads | `wind_asce7.py` | HARDENED | ASCE 7-22 Ch 26+29, all 3 loading cases |
| Foundation | `foundation_embed.py` | HARDENED | Broms, Brinch Hansen, Czerniak, IBC 1807.3.1 |
| Anchor/Baseplate | `anchors_baseplate.py` | HARDENED | ACI 318-19 Ch 17, AISC DG1 |
| Member Selection | `supports_pipe.py` | HARDENED | AISC 360, HSS preferred |
| Drawing Model | `drawing_model.py` | COMPLETE | DEC-002 abstraction |
| DXF Renderer | `dxf_renderer.py` | COMPLETE | ezdxf R2010 |
| Foundation Drawing | `generate_foundation_drawing.py` | COMPLETE | Multi-view with cage detail |

---

## Intelligence Platform

| Component | File | Status | Details |
|-----------|------|--------|---------|
| Bid Scoring (heuristic) | `bid_scoring.py` | PRODUCTION | 6 weighted signals, 18,670 cross-validated |
| Bid Scoring (ML) | `bid_model.py` | PRODUCTION | Logistic regression, AUC 0.80, 10 features |
| Customer Intel | `customer_intel.py` | PARTIAL | Profiles, similar jobs, market intel. Missing multi-location breakout. |
| Project Files | `project_files.py` | WORKING | G: drive scanner with TTL cache. Weak on fuzzy matching. |
| Drawing Search | `drawing_search.py` | WORKING | Fuzzy matching (difflib), 13 aliases, os.scandir + folder cache. CAT Scale resolves. |

### Win Rate Cross-Validation (2026-02-17)
- Naive: 93.0% → Cross-validated: 76.0% → Actual (2022-2025): 32-50%
- $25-50K bracket: 35.3% (Eagle's worst bracket)
- KENT: 99.9%, MIKEE: 97.7%, JEFF: 53.2%

---

## Data Assets

| Asset | Rows | Location |
|-------|------|----------|
| signx.duckdb | 54K labor + 27K contracts | `C:\Scripts\signx-warehouse\warehouse\signx.duckdb` |
| Calibration matrix | 30 types, 497 cells | `signx-takeoff/data/calibration.json` |
| Raw matrix | 30 types, full stats | `signx-takeoff/data/calibration_matrix_raw.json` |
| Merged CSVs (7) | ~1.56M rows | `C:\Scripts\signx-warehouse\warehouse\raw\csv_exports\` |
| G: Drive drawings | ~75-100K PDFs | `//ES-FS02/Customers2` (A-Z customer folders) |
| Notion Pipeline | 21 bids, $516K | DB: 304c1e58d2dd814aae63c6a0d44e6679 |

---

## Industry Research (Completed 2026-02-17)

Six research agents scanned ISA, WSA, Signs101, SignCraft, vendor install guides, sign shop software, AI/ML ecosystem, and 2D-to-3D technology. Key findings:

- **No RSMeans equivalent for signs.** Industry guards labor benchmarks. Eagle's 954-job warehouse data is more granular than anything publicly available.
- **ABC Guide PF methodology still valid.** 1974-era physics of sign fabrication hasn't changed. Calibrate with crew-specific speed from warehouse.
- **Zero open-source competition** for sign estimation on GitHub. SignX is genuinely novel.
- **Key competitors:** shopVOX (formula-based), Kimco (MES), SquareCoil (ERP), EstiMate ($/inch), GraphixCalc (2003-era desktop)
- **Vinyl application rate:** 60 SF/hr (Signs101 consensus)
- **CL manual fab:** ~54 min/20" letter (Signs of the Times)
- **SignComp cabinet benchmark:** 4.5 hrs for 32 SF cabinet = 0.14 hrs/SF traditional
- **Top AI opportunities:** Werk24 API (drawing → JSON), SkyCiv API (cloud structural), NVIDIA cuOpt (crew routing), Florence-2 (drawing OCR), Docling MCP (PDF extraction)
- **Best 3D path:** CadQuery (pure Python parametric CAD) → Blender MCP (10K stars) for visualization

---

## Session History

| Date | Work | Commits |
|------|------|---------|
| 2026-02-17 (PM) | Bid Pipeline status updates (PATCH /api/notion/bid + inline dropdown). Fuzzy drawing search (difflib + 13 aliases + folder cache). CI/CD rewrite — all 3 jobs green. Security scan green (Semgrep + Gitleaks). | `6f6290d`, `4d13ab7` |
| 2026-02-17 (AM) | Auto-calibration engine (30 types, 497 cells). Batch travel dedup. Raceway removal adder. 8 estimators refactored with shared helpers. Calibration UI panel + API. 6 industry research agents completed. 49/49 tests passing. | `9a9f802`, `cdd109e` |
| 2026-02-16 | SpaceX UI redesign. ML model time-decay + cyclical features. Intelligence platform wiring. Sprint E completion. | `2b9ef1f`, `734f67a`, `b51c673` |
| 2026-02-15 | Sprints C-D. Pylon + cabinet estimators. Directional + dimensional. Bid Pipeline + Notion integration. 49-test pytest suite. | `407c6e5`, `44d30d2`, `ba8fe35` |
| 2026-02-14 | PE-stampable structural (wind, foundation, anchors, members). Signs-service compliance. Import sweep. | `05b27d4`, `c681b4a` |
| 2026-02-13 | Warehouse extraction. CSV enrichment. PA build guide. Monday estimation briefs. | (earlier commits) |

---

## Next Actions (Sprint F)

1. **Autonomous intake pipeline** — Single flow: drop PDF or type customer → auto-detect sign type → estimate + engineering + BOM + drawing
2. ~~**Fix Bid Pipeline**~~ DONE — Inline stage dropdown + PATCH to Notion. Real-time status updates.
3. **Fix Intelligence dossier** — Auto-pull ALL data (warehouse, drawings, project files, quotes). Multi-location breakout (CAT Scale). Natural language search for non-technical users.
4. ~~**Fix drawing search**~~ DONE — Fuzzy matching (difflib + 13 aliases + folder cache). CAT Scale resolves. Auto-attach still TODO.
5. **Add pole sign support** — POLNON sign type + non-illuminated toggle on Pylon tab, or separate Pole Sign tab.
6. **Engineering tab simplification** — Auto-fill Iowa defaults (115mph, Exposure C, 800ft). Hide jargon behind "Engineering Details" collapsible. Only show for sign types that need structural.
7. **PDF dimension detection** — Parse dimension callouts and title block text instead of measuring shapes on paper.
8. ~~**CI/CD**~~ DONE — 3 CI jobs (takeoff tests, signcalc smoke, ruff lint) + security scan (Semgrep + Gitleaks). All green.

---

## Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `signx-takeoff/app.py` | ~1730 | FastAPI server, 46 endpoints |
| `signx-takeoff/abc_engine.py` | ~3210 | 8 estimators, 51 work codes, auto-calibration |
| `signx-takeoff/calibrate.py` | ~350 | Auto-calibration engine (warehouse → calibration.json) |
| `signx-takeoff/bid_scoring.py` | ~400 | Heuristic win probability (6 signals) |
| `signx-takeoff/bid_model.py` | ~300 | ML logistic regression (AUC 0.80) |
| `signx-takeoff/customer_intel.py` | ~500 | Customer profiles, similar jobs, market intel |
| `signx-takeoff/project_files.py` | ~200 | G: drive scanner with TTL cache |
| `signx-takeoff/drawing_search.py` | ~150 | Drawing search (needs fuzzy matching) |
| `signx-takeoff/static/index.html` | ~3700 | SpaceX-themed dashboard UI |
| `services/signcalc-service/apex_signcalc/` | ~5000 | PE-stampable structural modules |
