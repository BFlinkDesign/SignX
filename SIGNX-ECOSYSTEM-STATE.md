# SignX Ecosystem State
**Updated:** 2026-03-01 22:00 CT by Claude Code (Sprint F session)

## Overview
SignX is Eagle Sign & Design Inc.'s proprietary estimation, intelligence, and workflow platform. No other sign company has this. It turns 27,063 historical jobs from KeyedIn ERP into competitive intelligence, automated takeoffs, and bid scoring.

## Active Repositories

### 1. EAGLE605/SignX (monorepo) -- PUBLIC
- **Local:** `~/Desktop/SignX`
- **Branch:** main | **Dirty:** 45 files (7 modified by Sprint F, 38 untracked data/exports)
- **Contains:**
  - `signx-takeoff/` -- FastAPI estimation engine (the crown jewel)
  - `prototype-keyedin/` -- Kimco MCP server (nested git repo)
  - `Keyedin/` -- Legacy warehouse data + extraction scripts (untracked)
  - `calculators/`, `data/`, `customers/` -- Historical data (untracked)

### 2. EAGLE605/signx-intake -- PRIVATE
- **Local:** `C:\Scripts\signx-intake`
- **Branch:** master | **Clean**
- **Purpose:** Email pipeline (PA webhook -> Claude Haiku classification -> Notion)
- **Status:** Substantially complete. 3 open items blocked on Brady (VENDOR QUOTES folder, vendor emails, named tunnel)

### 3. EAGLE605/signx-warehouse -- PRIVATE
- **Local:** `C:\Scripts\signx-warehouse`
- **Branch:** master | **Dirty:** 2 files
- **Purpose:** DuckDB warehouse (40 tables, 609K rows from KeyedIn exports)
- **Key data:** `warehouse/raw/so_contracts_parsed.csv` (27,062 jobs), `warehouse/raw/quote_status_report.csv` (18,972 quotes)

### 4. EAGLE605/prototype-keyedin -- PRIVATE
- **Local:** `~/Desktop/SignX/prototype-keyedin`
- **Branch:** master | **Clean**
- **Purpose:** Kimco ERP MCP server (19 tools, 99 API GUIDs mapped)
- **Status:** OAuth blocked pending Kimco activation. k5 session auth works (~60 min TTL)

### 5. EAGLE605/CorelDraw-Macro -- PRIVATE
- **Local:** Via CorelDRAW VBA GlobalMacros
- **Purpose:** FlinkSignPROv4 -- CorelDRAW automation (stud placement, nesting, shop drawings)
- **Status:** Active, production use

### 6. EAGLE605/calcusignY -- PRIVATE
- **Purpose:** Legacy sign calculator (pre-SignX)
- **Status:** Superseded by signx-takeoff estimators

## Archived (Dead) Repositories
- EAGLE605/SignEngineeringCalc -- archived 2026-03-01
- EAGLE605/ai-signage-takeoff -- archived 2026-03-01
- EAGLE605/eaglesign-data -- archived 2026-03-01

## SignX-Takeoff Engine (~/Desktop/SignX/signx-takeoff/)

### Architecture
```
FastAPI (app.py, ~1800 lines)
  |-- 47 API endpoints
  |-- 12 dashboard tabs (SpaceX-themed UI)
  |-- Static: static/index.html (~3700 lines)
  |
  |-- Estimation Engines:
  |   |-- abc_engine.py (ABC formula: channel letters, monument, awning, etc.)
  |   |-- extract_pf_from_pdf.py (PDF vector extraction -> peripheral feet)
  |   |-- calibrate.py (auto-calibration from warehouse P50 data)
  |
  |-- Intelligence Layer:
  |   |-- customer_intel.py (27K job mining, customer profiles, similar jobs)
  |   |-- bid_scoring.py (6-factor win probability, 18K quote cross-validation)
  |   |-- bid_model.py (ML logistic regression, AUC=0.798)
  |   |-- sign_types.py [NEW] (canonical taxonomy, 20 sign type groups)
  |
  |-- File Search:
  |   |-- drawing_search.py (G: drive drawing locator, SMB)
  |   |-- project_files.py (dossier file scanner, 12 doc types)
  |
  |-- Support:
  |   |-- warehouse.py (benchmark comparisons)
  |   |-- mail_classifier.py / mail_processor.py (email routing)
  |   |-- led_catalog.py (LED module database)
  |   |-- models.py (Pydantic models)
```

### Sprint F Changes (This Session)
1. **Created `sign_types.py`** -- Single source of truth for sign type taxonomy (20 groups, up from 8). Eliminated 8 duplicate alias maps across 3 files.
2. **Refactored CSV path resolution** -- `find_warehouse_csv()` / `find_quote_csv()` with env var override support (`SIGNX_WAREHOUSE_CSV`, `SIGNX_QUOTE_CSV`).
3. **Fixed PDF dimension detection** -- Auto-scale now uses median shape height (robust to serif/ascender outliers) instead of max bounding box. Added `median_height_inches` and `representative_height_inches` to extraction output.
4. **Added Notion config warning** -- Dossier endpoint now warns when NOTION_TOKEN is missing instead of silently omitting bid pipeline data.
5. **Updated:** customer_intel.py, bid_scoring.py, bid_model.py, warehouse.py, app.py, extract_pf_from_pdf.py

### Estimators (8 sign types)
| Type | Engine | Status |
|------|--------|--------|
| Channel Letters (CLLIT/CLNON) | ABC formula + PDF extraction | Production |
| Monument (MONDF/MONSF) | ABC formula | Production |
| Awning (AWNNON/AWNLIT) | ABC formula | Production |
| Removal | Flat rate + complexity | Production |
| Pylon (POLLIT/POLNON) | ABC formula | Production |
| Cabinet (ALULIT/ALUNON) | ABC formula | Production |
| Directional (DIRECT) | Simple estimator | Production |
| Dimensional (GEMINI) | PDF + purchased letters | Production |

### Intelligence Dossier (/api/dossier)
One API call aggregates 8 data sources:
1. Customer profile (27K warehouse jobs, fuzzy matching)
2. Similar past jobs (type + revenue + location scoring)
3. Market intel (pricing benchmarks P25/P50/P75)
4. G: drive project files (classified into 12 doc types)
5. G: drive drawings (CDR/PDF/AI search with WO matching)
6. Win probability -- heuristic (6 weighted factors)
7. Win probability -- ML (logistic regression, AUC=0.798)
8. Price recommendation (3-tier from won bid distribution)
9. Notion bid pipeline (when configured)

### ML Model Performance
- **Type:** Logistic regression with time-decay weighting
- **Training data:** 18,165 labeled quotes cross-validated against 27,062 warehouse jobs
- **AUC-ROC:** 0.798 | **Brier:** 0.2531 | **CV Accuracy:** 58.3%
- **Top features:** Salesperson win rate (+0.88), customer job count (+0.64), days to expiry (+0.33)
- **Trains eagerly on import** -- no serialized model file, retrains each server start (~5 seconds)

## Integration Points

### KeyedIn ERP (legacy, active)
- Source of truth for dollars, quotes, work orders, labor rates
- GWT RPC protocol with session auth (JSESSIONID + UniVerse backend)
- Extraction script at `C:\Scripts\keyedin-extraction\keyedin_extractor.py` -- BROKEN (class migration)
- Warehouse data extracted to CSV, loaded by signx-takeoff at startup

### Kimco ERP (future)
- SaaS at `prototype.kimcoerp.com`
- 99 API GUIDs mapped via MCP server
- OAuth activation pending
- Dollar figures unreliable until go-live
- **SignX boundary rule:** SignX outputs work codes, hours, quantities ONLY. Never dollars.

### Power Automate (M365 integration)
- 12+ active flows handling email triggers, bid alerts, correspondence classification
- Only path to M365 data (user consent OFF in Eagle tenant)
- Key flows: M365-Mail-API, M365-Calendar-API, CORRESPONDENCE-CLASSIFIER, BID-INTAKE-PROOF, SignX-BidAlert-* (3 flows)
- Webhook URLs are permanent (sig-based auth, no expiry)

### Notion
- Bid Pipeline database for active quote tracking
- Requires NOTION_TOKEN and NOTION_BID_PIPELINE env vars
- Property names: "Quote #" (not "Quote Number"), "Est. Value" (not "Bid Amount")

### G: Drive (\\ES-FS02\Customers2)
- Customer project files, drawings (CDR, PDF, AI)
- Searched by drawing_search.py and project_files.py
- 3-second SMB timeout for responsiveness

## Open Items / Blockers

### Blocked on Brady
- [ ] Create "VENDOR QUOTES" Outlook folder (for signx-intake Flow 3)
- [ ] Populate `sub_contacts.json` with real vendor emails
- [ ] Run `cloudflared tunnel login` for named tunnel

### Technical Debt
- [ ] Sign type taxonomy only covers 20 groups -- warehouse has ~38 distinct codes
- [ ] No test PDFs checked into repo for extract_pf_from_pdf validation
- [ ] Warehouse CSV reloaded on every server restart (~5 sec) -- consider serialized cache
- [ ] ML model retrains on every import -- consider joblib persistence
- [ ] 45 dirty files in monorepo need triage (commit meaningful ones, gitignore the rest)

### In Progress (Fleet)
- P1: KeyedIn extractor fix (OpenClaw) -- needs SecureCommandPayload wrapper + fresh JSESSIONID
- Engineering tab simplification (Gemini CLI) -- Iowa defaults, collapsible advanced section
