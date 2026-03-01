# CNC-1 Code Inventory — Full Audit

**Audited:** 2026-03-01
**Source:** GitHub repo `EAGLE605/SignX` (commit `b7609f7`) running on Linux container
**Limitation:** Cannot access CNC-1 filesystem directly — CNC-1-only items are inferred from code references, docs, and `KEYEDIN-PIPELINE-STATUS.md`

---

## Part A: What's IN the GitHub Repo

### PRODUCTION — Code that runs today, produces output Brady uses

| Path | Files | LOC | Last Modified | Has Data | Description |
|------|-------|-----|---------------|----------|-------------|
| `signx-takeoff/abc_engine.py` | 1 | 3,210 | 2026-02-28 | `data/calibration.json` (7 files) | 8 sign estimators, 51 work codes. THE money maker. |
| `signx-takeoff/app.py` | 1 | 2,060 | 2026-03-01 | — | FastAPI server, 47+ endpoints. Central hub. |
| `signx-takeoff/calibrate.py` | 1 | 627 | 2026-02-28 | — | Auto-calibration from warehouse P50 medians. |
| `signx-takeoff/warehouse.py` | 1 | 378 | 2026-02-28 | — | Loads `so_contracts_parsed.csv` for benchmarking. Needs `C:\Scripts\signx-warehouse`. |
| `signx-takeoff/bid_scoring.py` | 1 | 1,132 | 2026-02-28 | — | Win probability model, AUC 0.80. Needs warehouse CSVs. |
| `signx-takeoff/bid_model.py` | 1 | 925 | 2026-02-28 | — | Logistic regression bid model. Needs warehouse CSVs. |
| `signx-takeoff/customer_intel.py` | 1 | 585 | 2026-02-28 | — | Customer profile from warehouse data. |
| `signx-takeoff/drawing_search.py` | 1 | 420 | 2026-02-28 | — | Searches `\\ES-FS02\Customers2` for drawings. |
| `signx-takeoff/project_files.py` | 1 | 312 | 2026-02-28 | — | Project file lookup on file server. |
| `signx-takeoff/mail_processor.py` | 1 | 517 | 2026-02-28 | — | Win32 COM Outlook poller (60s), bid intake automation. |
| `signx-takeoff/mail_classifier.py` | 1 | 580 | 2026-02-28 | — | Dual-flow: regex KeyedIn parser + Claude Haiku classifier. Routes to 3 Notion DBs. |
| `signx-takeoff/mail_state.py` | 1 | 168 | 2026-02-28 | `data/mail_state.db` | SQLite dedup for processed emails. |
| `signx-takeoff/static/index.html` | 1 | 3,700 | 2026-02-28 | — | Dashboard UI Brady uses daily. 12 tabs. |
| `signx-takeoff/notion_sync.py` | 1 | 450+ | 2026-02-28 | — | Notion API integration (read/write bids). |
| `services/signcalc-service/` | 18 | 5,000+ | 2026-02-28 | `data/` (standards JSONs) | Wind + foundation calcs. PE-stampable. |
| `Benchmark/catscale_delta_parser.py` | 6 | 3,946 | 2026-02-28 | — | Cat Scale PDF parser with delta analysis. |
| **PRODUCTION SUBTOTAL** | **~37** | **~24,000** | | | |

### DEVELOPMENT — Active development, not yet production

| Path | Files | LOC | Last Modified | Description |
|------|-------|-----|---------------|-------------|
| `SignX-500IQ/` | 8 | 2,863 | 2026-03-01 | Knowledge graph service. Seeded from warehouse. Shadow-mode wired to takeoff. |
| `signx-takeoff/iq_client.py` | 1 | 195 | 2026-03-01 | Async client for 500IQ with safety gates. |
| `signx-takeoff/tests/test_iq_client.py` | 1 | 320 | 2026-03-01 | 10 tests for IQ integration. |
| `SignX-Intake/` | 12 | 1,843 | 2026-02-28 | PA build guide, extraction prompts, test emails, schema, recon scripts. |
| `Keyedin/` | 85 py + 41 html | 27,966 | 2026-02-28 | Massive recon/capture effort. GWT-RPC cracking, CDP extraction, MCP server code. |
| **DEVELOPMENT SUBTOTAL** | **~107** | **~33,000** | | |

### SCAFFOLDING — Generated architecture, never connected to production

| Path | Files | LOC | Description | Evidence |
|------|-------|-----|-------------|----------|
| `svcs/` (9 agents + orchestrator) | 17 | 2,471 | Agent microservices | 0 production imports anywhere |
| `modules/` (5 modules) | 6 | 1,388 | Platform modules | Only referenced by platform registry, never called |
| `signx_platform/` | 7 | 522 | Platform API | Module registry, never used |
| `SignX-Intel/` | 30+ | 2,597 | Cost intelligence service | Zero implementation, all scaffolding |
| `services/ml/` | 11 | 1,500+ | XGBoost/GNN models | Models defined, never trained |
| `services/materials-service/` | 4 | 300+ | Materials scoring | Standalone, never integrated |
| `services/signs-service/` | 12 | 600+ | Sign rules service | Never called |
| `services/translator-service/` | 1 | 100+ | Translation | Single file, never called |
| `infra/terraform/` | 2 | 200+ | Terraform modules | Skeleton, can't deploy |
| `k8s/charts/` | 2 | 100+ | Helm charts | Skeleton, never used |
| `docker-compose.prod.yml` | 1 | 200+ | Production compose | Never deployed (no host configured) |
| `tests/` (top-level) | 58 | 6,760 | Test suites | Many test services that don't exist |
| `scripts/` | 25 | 9,413 | Setup/seed/import scripts | Most target DB that's not running |
| `contracts/` | 11 | 625 | Contract tests | Target phantom services |
| `monitoring/` | 3 | 221 | Grafana/Prometheus configs | No monitoring running |
| `ops/` | 15 | 994 | Operational scripts | Code fixers, one-time use |
| **SCAFFOLDING SUBTOTAL** | **~205** | **~28,000** | | |

### DEAD — Abandoned, superseded, or broken

| Path | Files | LOC | Description | Evidence |
|------|-------|-----|-------------|----------|
| `eagle_analyzer_v1/` | 11 | 3,215 | Legacy analyzer | Superseded by abc_engine.py |
| `EagleHub/` | 7 | 1,745 | Abandoned dashboard | Never deployed, HTML prototypes |
| `WebScrapers/` | 5,811 LOC | 5,811 | Vendored Scrapling library | Never imported |
| `ConstructIQ/` | 81 | 168 | YouTube transcript stubs | Empty content |
| `archive/` | 80 | 456 | Old deliverable docs | Historical only |
| `CorelDraw Macros/` | 5 | 0 (binary+html) | VBA macros | Standalone, not code |
| `Bluebeam/` | 1 | 31 | Bluebeam integration note | Single file |
| `Gemini Generator/` | 7 | 0 | Gemini doc generator | Isolated tool |
| `recon-results/` | 2 | 676 | One-time recon | Historical |
| `export-test-results/` | 1 | 0 | Empty | Single gitkeep |
| `patches/` | 4 | 0 | Patch files | One-time use |
| `queue/` | 5 | 0 | Queue stubs | Never used |
| `runbooks/` | 2 | 0 | Runbook docs | Never populated |
| `standards/` | 3 | 0 | Standards stubs | Empty |
| `info/` | 11 | 0 | Info docs | Reference only |
| **DEAD SUBTOTAL** | **~235** | **~12,000** | | |

### REFERENCE / DATA — Not code, but valuable

| Path | Files | Type | Description |
|------|-------|------|-------------|
| `Eagle Data/BOT TRAINING/` | 400+ | CSV, PDF, DWG, CDR, XLSX | 22 years of Eagle Sign production data, CAD files, LED specs, estimating guides |
| `SignShopWorkflow/` | 8 | Markdown | Workflow documentation |
| `docs/` | 185 | Markdown | Extensive documentation |
| `data/standards/` | 9 | JSON | ASCE 7-22, PE drawing catalog |
| `GandHSync/` | 11 | BAT, PS1, VBS | Brady's file server sync scripts (G: and H: drives) |
| `Ai Observation & Training/` | 18 | PS1, MKV, JSON | OBS recording automation, PC discovery prompts |
| Root `*.md` files | 50+ | Markdown | Session states, reports, plans, handoff docs |

---

## Part B: What's on CNC-1 ONLY (NOT in GitHub)

These locations are referenced in code/docs but their contents are NOT in the repo:

### CRITICAL — Production data & working scripts

| CNC-1 Path | Type | Referenced By | Est. Size | Risk if Lost |
|------------|------|---------------|-----------|--------------|
| `C:\Scripts\signx-warehouse\warehouse\signx.duckdb` | DuckDB database | `abc_engine.py:1554`, `calibrate.py:38`, `t1_query.py:4` | ~200 MB | **CRITICAL** — calibration, benchmarks, analysis all depend on it |
| `C:\Scripts\signx-warehouse\warehouse\raw\so_contracts_parsed.csv` | CSV | `warehouse.py:20`, `bid_scoring.py:29`, `customer_intel.py:24`, `bid_model.py:42` | ~50 MB | **CRITICAL** — benchmark + bid scoring dead without it |
| `C:\Scripts\signx-warehouse\warehouse\raw\quote_status_report.csv` | CSV | `bid_scoring.py:34`, `bid_model.py:47` | ~10 MB | **HIGH** — bid model training data |
| `C:\Scripts\signx-warehouse\scripts\parse_full_cost_detail.py` | Python | `KEYEDIN-PIPELINE-STATUS.md` | 907 LOC | **CRITICAL** — parses 168 HTML files into warehouse CSVs |
| `C:\Scripts\signx-warehouse\warehouse\production\eagle_warehouse.db` | SQLite | `KEYEDIN-PIPELINE-STATUS.md` | 211 MB | **CRITICAL** — production warehouse database |
| `C:\Scripts\signx-warehouse\warehouse\raw\csv_exports\` | Directory | `scripts/extract_mvi_csv_exports.py`, `scripts/enrich_csv_exports.py` | ~200 MB | **HIGH** — raw CSV exports from KeyedIn |

### HIGH — Working automation scripts

| CNC-1 Path | Type | Referenced By | Description | Risk |
|------------|------|---------------|-------------|------|
| `C:\Scripts\keyedin-capture\` | Python scripts | `KEYEDIN-PIPELINE-STATUS.md` | 9+ scripts: CDP extraction, batch capture, credential setup | **HIGH** — 52 working scripts, 559 MB captured data |
| `C:\Scripts\keyedin-capture\reports\cost_detail\` | 168 HTML files | `KEYEDIN-PIPELINE-STATUS.md` | 33,428 work orders, 559 MB | **HIGH** — raw source for warehouse |
| `C:\Scripts\keyedin-automation\` | Python + ChromaDB | `KEYEDIN-PIPELINE-STATUS.md` | MCP knowledge server, site maps, discovery | **HIGH** — 7 working scripts + 1,141 indexed docs |
| `C:\Scripts\keyedin-automation\discovery\keyedin\keyedin_site_map.json` | JSON | `KEYEDIN-PIPELINE-STATUS.md` | 288 KeyedIn functions mapped | **MEDIUM** — recreatable but 2+ hours |

### MEDIUM — File server dependencies

| CNC-1 Path | Type | Referenced By | Description | Risk |
|------------|------|---------------|-------------|------|
| `\\ES-FS02\Customers2` | SMB share (G: drive) | `drawing_search.py:40`, `project_files.py:55` | Customer drawings, 20+ years | **LOW** — exists on file server, not at risk of loss |
| `C:\Scripts\Ai Observation & Training\OBS_Staging` | Directory | `obs_mover.ps1:19` | OBS recording staging | **LOW** — convenience automation |
| `C:\WorkSync\` | Sync mirror | `GandHSync/` | Local copies of G: and H: drives | **LOW** — mirror, source is on ES-FS02 |

---

## Part C: Summary Statistics

| Category | Files | LOC | In Git |
|----------|-------|-----|--------|
| PRODUCTION (repo) | ~37 | ~24,000 | YES |
| DEVELOPMENT (repo) | ~107 | ~33,000 | YES |
| SCAFFOLDING (repo) | ~205 | ~28,000 | YES |
| DEAD (repo) | ~235 | ~12,000 | YES |
| Reference/Data (repo) | 400+ | — | YES |
| CNC-1 ONLY (critical) | ~60+ scripts | ~5,000+ | **NO** |
| CNC-1 ONLY (data) | ~200+ files | — | **NO** (~2.2 GB) |

**Total repo LOC (code):** ~97,000
**Production LOC:** ~24,000 (25%)
**CNC-1-only critical LOC:** ~5,000+ (completely unprotected)
**CNC-1-only data:** ~2.2 GB (partially backed up to OneDrive)
