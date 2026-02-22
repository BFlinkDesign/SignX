# CODEBASE-MAP.md -- SignX-Takeoff

**Generated:** 2026-02-21
**Method:** Python `ast` module automated analysis + manual code review
**Scope:** All 28 `.py` files, 1 HTML frontend, 10 data files, 1 SQLite database

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [File Inventory](#2-file-inventory)
3. [Dependency Graph](#3-dependency-graph)
4. [Function & Class Index](#4-function--class-index)
5. [Data Flow Maps](#5-data-flow-maps)
6. [Configuration & Secrets](#6-configuration--secrets)
7. [Database Schema](#7-database-schema)
8. [Dead Code & Redundancy](#8-dead-code--redundancy)
9. [External Touchpoints](#9-external-touchpoints)

---

## 1. Project Overview

**SignX-Takeoff** is a sign estimation and bid management system for Eagle Sign Co. (Des Moines, Iowa). It combines:

- **ABC Sign Estimating Engine** -- formula-based labor estimation derived from the 1974 ABC Sign Products Pricing Guide (updated 2026), calibrated against 27,000+ historical warehouse jobs
- **Email Intake Pipeline** -- Win32com Outlook poller that classifies incoming bid requests and routes them through Notion databases
- **ML Win Probability** -- logistic regression model trained on 18,972 historical quotes cross-referenced with 27,062 warehouse jobs
- **Structural Engineering** -- ASCE 7-22 wind, AISC 360 steel, ACI 318-19 concrete, and Broms/IBC foundation calculations
- **Customer Intelligence** -- fuzzy-matched customer profiling, historical job similarity, and market benchmarking
- **Web Frontend** -- dark-themed single-page application for estimators

**Stack:** Python 3.13 / FastAPI / SQLite / DuckDB / PyMuPDF / scikit-learn / Anthropic Claude Haiku / Notion API / Win32com
**Entry point:** `app.py` on port 8765 (`python app.py` or `run.bat`)

### Codebase Statistics (AST-verified)

| Metric | Value |
|--------|-------|
| Python files | 28 |
| Total lines of Python | 15,673 |
| Functions defined | 424 |
| Classes defined | 60 |
| Environment variables | 16 |
| External URLs hardcoded | 15 |
| Notion database IDs | 4 |
| API endpoints | 30+ |
| Test files | 9 |

---

## 2. File Inventory

### Core Application (18 files, ~11,300 lines)

| File | Lines | Size | Purpose |
|------|-------|------|---------|
| `app.py` | 2,056 | 88 KB | FastAPI server -- central hub, 30+ REST endpoints, Notion integration, SMS/webhook notifications |
| `abc_engine.py` | 3,211 | 145 KB | ABC Sign Products estimation engine -- 8 sign-type estimators, rate tables, correction factors, calibration |
| `mail_classifier.py` | 727 | 31 KB | Dual email classifier: regex bid intake + Claude Haiku correspondence routing to 3 Notion databases |
| `mail_processor.py` | 517 | 22 KB | Win32com Outlook polling loop -- scans 4 salesperson folders every 60s, triggers auto-takeoff |
| `mail_state.py` | 203 | 7 KB | SQLite state management -- email dedup, follow-up timers, closeout variance tracking |
| `models.py` | 566 | 22 KB | Pydantic request models with validators for 4 sign types (channel letter, monument, awning, removal) |
| `extract_pf_from_pdf.py` | 371 | 16 KB | PDF vector path extraction via PyMuPDF -- Bezier curve length, polygon area, scale detection |
| `warehouse.py` | 177 | 7 KB | Warehouse benchmarking against `so_contracts_parsed.csv` (25,400 rows) |
| `customer_intel.py` | 557 | 24 KB | Customer intelligence engine -- fuzzy name matching, historical profiling, market benchmarks |
| `project_files.py` | 559 | 24 KB | G: drive (`\\ES-FS02\Customers2`) file scanner -- document classification, dossier completeness |
| `bid_scoring.py` | 1,155 | 52 KB | Win probability heuristic scoring -- 6 weighted factors across 18,972 quotes x 27,062 jobs |
| `bid_model.py` | 904 | 40 KB | ML win probability -- scikit-learn LogisticRegression, 12 features, time-decay weighting |
| `drawing_search.py` | 443 | 18 KB | G: drive drawing search -- customer alias mapping, fuzzy folder matching |
| `calibrate.py` | 628 | 26 KB | Auto-calibration engine -- DuckDB warehouse queries, three-tier: P50 x buffer / ABC fallback / industry rails |
| `check_pipeline.py` | 31 | 1 KB | Standalone Notion API query to list bid pipeline entries |
| `sign_type_analysis.py` | 25 | 1 KB | Standalone DuckDB query for sign type volume/revenue report |
| `mondf_analysis.py` | 23 | 1 KB | Standalone DuckDB query for MONDF work code breakdown |
| `t1_query.py` | 65 | 3 KB | Standalone DuckDB query for specific WO lookup |

### Test Files (9 files, ~3,400 lines)

| File | Lines | Purpose |
|------|-------|---------|
| `test_phase1.py` | 390 | Core ABC engine tests -- PF calculation, footage charts, rate lookups |
| `test_boundary.py` | 388 | Edge cases -- zero PF, extreme heights, invalid enums, overflow |
| `test_validation.py` | 307 | Input validation -- CSV loading, PDF extraction, warehouse integration |
| `test_regression.py` | 731 | Regression suite -- Pydantic model validation, known estimate snapshots |
| `test_gemini_art.py` | ? | PDF extraction tests for Gemini Art proof files |
| `tests/test_estimators.py` | 323 | All 8 estimator functions -- regression, boundaries, properties, scaling |
| `tests/test_endpoints_live.py` | 869 | Live HTTP endpoint integration tests (spins up server on port 18765) |
| `tests/test_intel_live.py` | 163 | Live customer intel + bid scoring integration tests |
| `tests/test_performance.py` | 241 | Performance/load tests -- concurrent requests, response time benchmarks |

### Frontend & Config

| File | Purpose |
|------|---------|
| `static/index.html` | Single-page web UI -- dark theme, drag-drop PDF upload, tabbed estimator interface, export |
| `requirements.txt` | Minimal: fastapi>=0.115.0, uvicorn>=0.32.0, python-multipart>=0.0.12, PyMuPDF>=1.24.0 |
| `run.bat` | One-click Windows launcher: `cd /d "%~dp0" && python app.py` |
| `SIGNX_MANIFEST.md` | Build manifest with discovery results, formula reference, validation status |

### Data Files (`data/`)

| File | Size | Purpose |
|------|------|---------|
| `calibration.json` | 107 KB | Auto-generated calibration data -- install floors, removal floors, OT factors, work code medians for 30 sign types x 497 cells |
| `calibration_matrix_raw.json` | 69 KB | Raw warehouse (sign_type x work_code) statistical matrix |
| `sign_type_classifier.json` | 10 KB | Sign type classification rules -- 37 types, regex patterns, keyword mapping |
| `work_code_profiles.json` | 23 KB | Work code statistical profiles |
| `workforce_intelligence.json` | 476 KB | Workforce intelligence data (largest data file) |
| `workforce_intelligence_summary.md` | 11 KB | Human-readable summary of workforce intelligence |
| `blind_spots_analysis.json` | 49 KB | Analysis of estimation blind spots and coverage gaps |
| `blind_spots_analysis.zip` | 63 KB | Compressed blind spots data |
| `gap_analysis.md` | 16 KB | Gap analysis between ABC formulas and warehouse actuals |
| `mail_state.db` | 29 KB | SQLite database -- 3 tables, 4 processed emails |
| `mail_processor.log` | 8 KB | Rotating log file for email processor |

---

## 3. Dependency Graph

### Internal Import Chain

```
app.py
  +-- abc_engine.py          (estimation engine)
  +-- bid_model.py            (ML win probability)
  +-- bid_scoring.py          (heuristic win scoring)
  +-- calibrate.py            (auto-calibration)
  +-- customer_intel.py       (customer profiling)
  +-- drawing_search.py       (G: drive search)
  +-- extract_pf_from_pdf.py  (PDF extraction)
  +-- mail_classifier.py      (email classification)
  +-- mail_state.py           (SQLite state)
  +-- project_files.py        (G: drive files)
  +-- warehouse.py            (warehouse benchmarking)
  +-- [external] apex_signcalc (structural engineering, ../services/signcalc-service)

mail_processor.py
  +-- mail_classifier.py
  +-- mail_state.py

models.py
  +-- abc_engine.py

calibrate.py (standalone CLI)
  (no internal deps -- uses DuckDB directly)
```

### Mermaid Dependency Diagram

```mermaid
graph TD
    APP[app.py<br>FastAPI Server]
    ABC[abc_engine.py<br>ABC Estimation]
    ML[bid_model.py<br>ML Win Prob]
    SCORE[bid_scoring.py<br>Heuristic Scoring]
    CAL[calibrate.py<br>Auto-Calibration]
    INTEL[customer_intel.py<br>Customer Intel]
    DRAW[drawing_search.py<br>Drawing Search]
    PDF[extract_pf_from_pdf.py<br>PDF Extraction]
    CLASS[mail_classifier.py<br>Email Classifier]
    STATE[mail_state.py<br>SQLite State]
    PROJ[project_files.py<br>Project Files]
    WH[warehouse.py<br>Warehouse Bench]
    MOD[models.py<br>Pydantic Models]
    MAIL[mail_processor.py<br>Outlook Poller]
    APEX[apex_signcalc<br>Structural Eng]

    APP --> ABC
    APP --> ML
    APP --> SCORE
    APP --> CAL
    APP --> INTEL
    APP --> DRAW
    APP --> PDF
    APP --> CLASS
    APP --> STATE
    APP --> PROJ
    APP --> WH
    APP --> APEX
    MOD --> ABC
    MAIL --> CLASS
    MAIL --> STATE
    ABC -.-> |DuckDB| DDB[(signx.duckdb)]
    CAL -.-> |DuckDB| DDB
    WH -.-> |CSV| CSV[(so_contracts_parsed.csv)]
    SCORE -.-> |CSV| CSV
    SCORE -.-> |CSV| QSR[(quote_status_report.csv)]
    ML -.-> |CSV| CSV
    ML -.-> |CSV| QSR
    INTEL -.-> |CSV| CSV
    STATE -.-> |SQLite| SQLDB[(mail_state.db)]
    CLASS -.-> |API| NOTION[Notion API]
    CLASS -.-> |API| CLAUDE[Claude Haiku API]
    DRAW -.-> |SMB| GDRIVE[\\ES-FS02\Customers2]
    PROJ -.-> |SMB| GDRIVE
    APP -.-> |API| NOTION
    MAIL -.-> |COM| OUTLOOK[Outlook COM]
    MAIL -.-> |HTTP| APP

    style APP fill:#0077ff,color:#fff
    style ABC fill:#00e676,color:#000
    style MAIL fill:#ff9100,color:#000
```

### External Dependencies by File

| File | External Packages |
|------|-------------------|
| `abc_engine.py` | json, math, re, dataclasses, enum, pathlib, typing, numpy*, pandas*, duckdb* |
| `app.py` | fastapi, uvicorn, httpx, pydantic, dotenv, asyncio, smtplib, email, json, logging, os, sys, pathlib, typing, datetime, apex_signcalc* |
| `bid_model.py` | numpy, sklearn (LogisticRegression, StandardScaler), csv, math, statistics, dataclasses, collections, datetime, pathlib |
| `bid_scoring.py` | csv, statistics, dataclasses, collections, datetime, pathlib |
| `calibrate.py` | duckdb, json, argparse, os, pathlib, sys, datetime |
| `customer_intel.py` | csv, statistics, dataclasses, datetime, pathlib |
| `drawing_search.py` | concurrent.futures, difflib (SequenceMatcher), logging, os, pathlib, re, dataclasses |
| `extract_pf_from_pdf.py` | fitz (PyMuPDF), math, dataclasses |
| `mail_classifier.py` | anthropic, requests, dotenv, json, os, re, pathlib, datetime |
| `mail_processor.py` | win32com.client, pythoncom, requests, argparse, json, logging, os, sys, time, pathlib, datetime |
| `mail_state.py` | sqlite3, json, os, pathlib, datetime |
| `models.py` | pydantic (BaseModel, field_validator), enum |
| `project_files.py` | concurrent.futures, threading, logging, os, pathlib, re, time, dataclasses, datetime |
| `warehouse.py` | csv, statistics, dataclasses, os, pathlib |

\* lazy import (inside function body, not at module level)

---

## 4. Function & Class Index

### Classes (60 total)

#### Enumerations (abc_engine.py)

| Class | Line | Values | Purpose |
|-------|------|--------|---------|
| `ConstructionType(str, Enum)` | 126 | FACE_LIT, HALO, OPEN_FACE, STRIP | Channel letter construction method |
| `FontType(str, Enum)` | 133 | BLOCK, SCRIPT, SERIF | Font type for footage chart lookup |
| `MountLocation(str, Enum)` | 139 | WALL, ROOF, GROUND | Installation mount position |
| `HeightCategory(str, Enum)` | 144 | SMALL, MEDIUM, LARGE, XLARGE | Letter height bracket (7-11, 12-24, 25-54, 55-120) |
| `SignType(str, Enum)` | 151 | 18 values: CLLIT, CLNON, MONDF, MONSF, POLLIT, POLNON, ALULIT, ALUNON, DIRECT, GEMINI, AWNNON, FLATPNL, etc. | Master sign type classification |
| `CabinetFace(str, Enum)` | 173 | SINGLE, DOUBLE | Cabinet face count |
| `CabinetShape(str, Enum)` | 179 | RECTANGULAR, ROUND, OVAL, IRREGULAR | Cabinet geometric shape |
| `CabinetFrame(str, Enum)` | 186 | LIGHT, MEDIUM, HEAVY | Cabinet structural weight class |
| `DimensionUnit(str, Enum)` | models.py:40 | inches, feet, mm | Input measurement unit |

#### Dataclasses (abc_engine.py)

| Class | Line | Fields | Purpose |
|-------|------|--------|---------|
| `JobInput` | 1058 | 35 fields | Complete input parameters for any sign estimate |
| `LaborLine` | 1126 | 7 fields (work_code, description, hours, unit_type, department, formula, section) | Single labor line item for KeyedIn |
| `EstimateResult` | 1138 | 9 fields (total_pf, labor_lines, install_lines, material_bom, led_spec, warnings, etc.) | Complete estimate output |

#### Dataclasses (other modules)

| Class | File | Purpose |
|-------|------|---------|
| `BenchmarkResult` | warehouse.py:26 | Warehouse comparison statistics |
| `CustomerProfile` | customer_intel.py:90 | Customer relationship profile (job count, revenue, recency, score) |
| `SimilarJob` | customer_intel.py:120 | Similar historical job match |
| `MarketIntel` | customer_intel.py:135 | Market pricing benchmarks per sign type |
| `ModelBundle` | bid_model.py:97 | Trained ML model + scaler + metadata |
| `MLPrediction` | bid_model.py:112 | ML prediction result with confidence |
| `FactorScore` | bid_scoring.py:341 | Individual scoring factor result |
| `BidScore` | bid_scoring.py:351 | Composite bid win probability score |
| `PriceRecommendation` | bid_scoring.py:371 | Suggested pricing range |
| `DrawingMatch` | drawing_search.py:101 | Matched drawing file from G: drive |
| `SearchResult` | drawing_search.py:116 | Drawing search result set |
| `LetterMeasurement` | extract_pf_from_pdf.py:24 | Per-letter PF measurement from PDF |
| `PDFExtraction` | extract_pf_from_pdf.py:42 | Complete PDF extraction result |
| `ProjectFile` | project_files.py:153 | Classified project file from G: drive |
| `DossierFiles` | project_files.py:172 | Complete project dossier with completeness score |

#### Pydantic Models (app.py -- API request bodies)

| Class | Line | Endpoint | Key Fields |
|-------|------|----------|------------|
| `FootageRequest` | 159 | POST /api/footage | letter_count, height_inches, font_type |
| `EstimateRequest` | 183 | POST /api/estimate | pf_source, pf_value, construction, height_inches, ... |
| `MonumentRequest` | 247 | POST /api/estimate/monument | sign_sf_per_face, num_faces, is_illuminated, ... |
| `AwningRequest` | 282 | POST /api/estimate/awning | width_inches, projection_inches, sign_sf, ... |
| `RemovalRequest` | 317 | POST /api/estimate/removal | sign_type, pf, include_raceway, ... |
| `PylonRequest` | 350 | POST /api/estimate/pylon | sign_sf_per_face, num_faces, is_illuminated, ... |
| `CabinetRequest` | 388 | POST /api/estimate/cabinet | sign_sf_per_face, num_faces, is_illuminated, ... |
| `DirectionalRequest` | 426 | POST /api/estimate/directional | width_inches, height_inches, num_faces, ... |
| `DimensionalRequest` | 460 | POST /api/estimate/dimensional | letter_count, height_inches, ... |
| `CalibrateRequest` | 568 | POST /api/calibrate | sign_type, buffer_multiplier |
| `WindRequest` | 632 | POST /api/structural/wind | V_mph, exposure_category, sign_area_sqft, ... |
| `FoundationRequest` | 664 | POST /api/structural/foundation | P_kips, M_kip_ft, soil_bearing_psf, ... |
| `AnchorRequest` | 688 | POST /api/structural/anchors | V_lbs, T_lbs, anchor_type, ... |
| `MemberCheckRequest` | 718 | POST /api/structural/member-check | shape, Pu_kips, Mu_x_kip_ft, ... |
| `MemberSelectRequest` | 742 | POST /api/structural/member-select | Pu_kips, Mu_x_kip_ft, ... |
| `FullDesignRequest` | 771 | POST /api/structural/full-design | V_mph, sign_width_ft, sign_height_ft, ... |
| `TakeoffRequest` | 1062 | POST /api/notion/takeoff | page_id |
| `StatusUpdateRequest` | 1199 | POST /api/notion/update-status | page_id, status |
| `NotifyRequest` | 1251 | POST /api/notify/bid-ready | quote_number, customer, total_hours, ... |
| `KeyedInFormatRequest` | 1384 | POST /api/keyedin/format | estimate |
| `ManualEmailRequest` | 2017 | POST /api/intake/manual | subject, body, sender, folder |

#### Pydantic Models (models.py -- validated request types)

| Class | Line | Methods | Purpose |
|-------|------|---------|---------|
| `ChannelLetterEstimateRequest` | 58 | `to_job_input()`, validators | Channel letter estimate with PF source validation |
| `MonumentEstimateRequest` | 258 | `to_job_input()`, validators | Monument estimate with SF validation |
| `AwningEstimateRequest` | 364 | `to_job_input()`, validators | Awning estimate with dimension conversion |
| `RemovalEstimateRequest` | 480 | `to_job_input()`, validators | Removal estimate |

### Key Functions (selected, 424 total)

#### abc_engine.py -- Estimation Functions

| Function | Line | Signature | Purpose |
|----------|------|-----------|---------|
| `estimate()` | 1221 | `(job: JobInput) -> EstimateResult` | Channel letter estimation (Sections 4B/4C/4A, 10B) |
| `estimate_monument()` | 1531 | `(job: JobInput) -> EstimateResult` | Monument MONDF/MONSF estimation (Section 2 + corrections) |
| `estimate_removal()` | 1834 | `(job: JobInput) -> EstimateResult` | Standalone removal (warehouse P50 x 1.20 primary) |
| `estimate_awning()` | 1914 | `(job: JobInput) -> EstimateResult` | Awning recover/new (Eagle actuals from Jobs #11530/#11532) |
| `estimate_pylon()` | 2094 | `(job: JobInput) -> EstimateResult` | Pylon/pole POLLIT/POLNON (Section 2 + POLLIT corrections) |
| `estimate_cabinet()` | 2397 | `(job: JobInput) -> EstimateResult` | Aluminum cabinet ALULIT/ALUNON (Section 2 + ALULIT corrections) |
| `estimate_directional()` | 2674 | `(job: JobInput) -> EstimateResult` | Directional/wayfinding DIRECT (warehouse P50, n=162) |
| `estimate_dimensional()` | 2884 | `(job: JobInput) -> EstimateResult` | Gemini/dimensional letters (warehouse P50, n=115) |
| `estimate_flatpanel()` | 3048 | `(job: JobInput) -> EstimateResult` | Flat panel FLATPNL (sheet metal + vinyl) |
| `calculate_pf_from_chart()` | 228 | `(count, height, font_type) -> float` | PF lookup from footage charts with interpolation |
| `calculate_led()` | 910 | `(pf, construction) -> dict` | LED module count, wattage, power supply sizing |
| `calculate_materials()` | 948 | `(pf, face_sf, depth, raceway_lf, construction) -> list` | Material BOM with Eagle part numbers |
| `load_comparable()` | 1496 | `(wo_number, db_path) -> dict[str, float]` | Pull actual hours from DuckDB by work order |
| `classify_sign_type()` | 845 | `(description) -> SignType` | Regex-based sign type classification from description text |
| `robust_z_mad()` | 800 | `(series, threshold) -> Series` | Outlier detection using Median Absolute Deviation |
| `_load_calibration()` | 63 | `() -> dict[str, Any]` | Load calibration.json for runtime correction factors |
| `reload_calibration()` | 75 | `() -> dict[str, Any]` | Force reload after recalibrate |

#### app.py -- API Endpoint Handlers

| Function | Line | Route | Method | Purpose |
|----------|------|-------|--------|---------|
| `upload_pdf()` | 134 | `/api/upload-pdf` | POST | PDF upload, PF extraction via PyMuPDF |
| `footage_chart()` | 173 | `/api/footage` | POST | Footage chart PF lookup |
| `full_estimate()` | 216 | `/api/estimate` | POST | Full channel letter estimate |
| `monument_estimate()` | 265 | `/api/estimate/monument` | POST | Monument sign estimate |
| `awning_estimate()` | 300 | `/api/estimate/awning` | POST | Awning sign estimate |
| `removal_estimate()` | 337 | `/api/estimate/removal` | POST | Removal estimate |
| `pylon_estimate()` | 373 | `/api/estimate/pylon` | POST | Pylon/pole estimate |
| `cabinet_estimate()` | 408 | `/api/estimate/cabinet` | POST | Cabinet sign estimate |
| `directional_estimate()` | 445 | `/api/estimate/directional` | POST | Directional sign estimate |
| `dimensional_estimate()` | 478 | `/api/estimate/dimensional` | POST | Dimensional/Gemini estimate |
| `calibrate_endpoint()` | 575 | `/api/calibrate` | POST | Trigger recalibration |
| `wind_loads()` | 641 | `/api/structural/wind` | POST | ASCE 7-22 wind load calculation |
| `foundation_design()` | 672 | `/api/structural/foundation` | POST | Spread footing / drilled shaft design |
| `anchor_design()` | 701 | `/api/structural/anchors` | POST | Anchor bolt design |
| `member_check()` | 731 | `/api/structural/member-check` | POST | AISC steel member check |
| `member_select()` | 754 | `/api/structural/member-select` | POST | Optimal steel member selection |
| `full_structural_design()` | 795 | `/api/structural/full-design` | POST | Complete structural package |
| `search_drawings()` | 879 | `/api/drawings/search` | GET | G: drive drawing search |
| `search_drawings_for_bid()` | 908 | `/api/drawings/search-bid` | GET | Drawing search by Notion bid page |
| `list_bids()` | 1025 | `/api/notion/bids` | GET | List Notion bid pipeline entries |
| `trigger_takeoff()` | 1067 | `/api/notion/takeoff` | POST | Trigger auto-estimation for a bid |
| `update_bid_status()` | 1200 | `/api/notion/update-status` | POST | Update Notion page status |
| `notify_bid_ready()` | 1253 | `/api/notify/bid-ready` | POST | Send SMS + webhook notification |
| `get_dossier()` | 1432 | `/api/dossier/{customer}` | GET | Customer project dossier |
| `get_customer_profile()` | 1492 | `/api/intel/customer/{name}` | GET | Customer intelligence profile |
| `score_bid_endpoint()` | 1585 | `/api/bid/score` | POST | Heuristic win probability score |
| `ml_score_bid()` | 1676 | `/api/bid/ml-score` | POST | ML win probability prediction |
| `format_keyedin()` | 1388 | `/api/keyedin/format` | POST | Format estimate for KeyedIn entry |
| `intake_feed()` | 1768 | `/api/intake/feed` | GET | Recent email intake feed |
| `manual_email_classify()` | 2020 | `/api/intake/manual` | POST | Manually classify an email |

#### mail_classifier.py -- Email Classification

| Function | Line | Purpose |
|----------|------|---------|
| `classify_and_route()` | ~680 | Main entry: classify email and route to appropriate Notion database |
| `parse_bid_intake()` | ~100 | Regex parser for "Quote #NNNNN - BID REQUEST" subjects |
| `classify_email()` | ~200 | Claude Haiku correspondence classifier |
| `create_bid_pipeline_entry()` | ~490 | Create Notion page in Bid Pipeline database |
| `create_correspondence_entry()` | ~530 | Create Notion page in Correspondence Log |
| `create_variation_entry()` | ~558 | Create Notion page in Variation Register |
| `link_to_bid_pipeline()` | ~575 | Link correspondence to existing bid pipeline entry |

#### mail_processor.py -- Email Polling

| Function | Line | Purpose |
|----------|------|---------|
| `_connect_outlook()` | 101 | COM connection with retry logic (3 attempts) |
| `process_folder()` | 223 | Process all unprocessed emails in one folder |
| `process_all_folders()` | 358 | Iterate all 4 salesperson folders |
| `run_loop()` | 389 | Main polling loop (60s interval) |
| `run_once()` | 422 | Single-pass processing |
| `_trigger_takeoff()` | 176 | POST to /api/notion/takeoff + /api/notify/bid-ready |

#### calibrate.py -- Auto-Calibration

| Function | Line | Purpose |
|----------|------|---------|
| `recalibrate()` | ~550 | Full recalibration: query DuckDB, compute factors, write calibration.json |
| `build_calibration()` | ~350 | Build calibration dict from raw warehouse data |
| `query_calibration_matrix()` | ~100 | DuckDB query for (sign_type x work_code) statistics |
| `compute_ot_factors()` | ~200 | OT probability and mean hours per sign type |
| `load_calibration()` | ~50 | Load calibration.json from disk |

#### bid_scoring.py -- Win Probability (Heuristic)

| Function | Line | Purpose |
|----------|------|---------|
| `score_bid()` | ~750 | Composite 6-factor win probability score |
| `_score_customer_recency()` | ~400 | 25% weight -- days since last job |
| `_score_customer_frequency()` | ~430 | 20% weight -- job count |
| `_score_price_position()` | ~460 | 20% weight -- price vs market |
| `_score_revenue_tier()` | ~500 | 15% weight -- customer revenue tier |
| `_score_sign_type_expertise()` | ~530 | 10% weight -- sign type historical win rate |
| `_score_margin_health()` | ~560 | 10% weight -- gross margin percentile |
| `get_price_recommendation()` | ~900 | Suggested pricing range based on win probability target |

#### bid_model.py -- Win Probability (ML)

| Function | Line | Purpose |
|----------|------|---------|
| `train_model()` | ~200 | Train LogisticRegression on 12 features with time-decay weights |
| `predict_win_probability()` | ~500 | Predict win probability for a new quote |
| `get_model_diagnostics()` | ~600 | Model performance metrics (AUC, accuracy, feature importance) |

---

## 5. Data Flow Maps

### Pipeline 1: Email Intake

```
Outlook Inbox
  |
  v
mail_processor.py::run_loop()     [Win32com COM, polls every 60s]
  |  Scans: Inbox/BID REQUEST/{Jeff Fye, Joe Phillips, Rich Thompson, House}/
  |  Filter: Last 7 days, Class=43 (MailItem)
  |  Dedup: internet_message_id via mail_state.is_processed()
  |
  v
mail_classifier.py::classify_and_route()
  |
  +--[regex match "Quote #NNNNN - BID REQUEST"]-->
  |     parse_bid_intake()
  |       -> Extract: quote_number, customer, sign_type, salesperson, status
  |       -> create_bid_pipeline_entry()  [Notion API -> Bid Pipeline DB]
  |       -> Return flow="bid_intake"
  |
  +--[no regex match]-->
        classify_email()  [Anthropic Claude Haiku API]
          -> Categories: bid_update, pricing_request, scheduling, complaint,
          |              vendor_communication, project_update, general,
          |              variation_notice, rfi, approval
          -> create_correspondence_entry()  [Notion API -> Corr Log DB]
          -> If variation: create_variation_entry()  [Notion -> Var Reg DB]
          -> link_to_bid_pipeline()  [Notion API -> relation]
          -> Return flow="correspondence"
  |
  v
mail_state.py::mark_processed()   [SQLite -> processed_emails table]
  |
  v
item.UnRead = False; item.Save()  [Win32com -> mark read]
  |
  v
[if flow == "bid_intake" and notion_page_id]:
  _trigger_takeoff()
    -> POST http://localhost:8765/api/notion/takeoff  [auto-estimation]
    -> POST http://localhost:8765/api/notify/bid-ready [SMS notification]
```

### Pipeline 2: Takeoff Engine (Estimation)

```
HTTP Request (POST /api/estimate, /api/estimate/monument, etc.)
  or
Auto-Takeoff (POST /api/notion/takeoff -> fetch Notion page -> determine sign type)
  |
  v
app.py endpoint handler
  |  Parses request body (Pydantic model validation)
  |  Maps sign_type -> estimator function via SIGN_TYPE_MAP dict
  |
  +--[channel letter]--> abc_engine.estimate(JobInput)
  |     1. Determine PF: PDF extraction / footage chart / manual
  |     2. Section 4 rates: sheet metal, mounting, paint (per PF x rate)
  |     3. LED sizing: modules, wattage, power supply
  |     4. Section 10B: install crew-hours (per PF x rate)
  |     5. Phase 0 corrections: install floor, CLLIT 0270 floor, OT factors
  |     6. Travel, load/unload, freight, removal (optional)
  |     7. Material BOM with Eagle part numbers
  |
  +--[monument]--> abc_engine.estimate_monument(JobInput)
  |     1. Section 2 rates (cabinet SF)
  |     2. MONDF_CORRECTION factors (lit vs nonlit, from 954-job warehouse)
  |     3. Section 5A paint rates
  |     4. Warehouse median for install (0630) -- ABC is 16.57x wrong
  |     5. OT: fab x 31%, install x 50%
  |
  +--[awning]--> abc_engine.estimate_awning(JobInput)
  |     SF-based rates from Eagle actuals (Jobs #11530/#11532)
  |
  +--[pylon]--> abc_engine.estimate_pylon(JobInput)
  |     Section 2 + POLLIT_CORRECTION, crane install (0650)
  |
  +--[cabinet]--> abc_engine.estimate_cabinet(JobInput)
  |     Section 2 + ALULIT_CORRECTION, wall-mounted (0630)
  |
  +--[directional]--> abc_engine.estimate_directional(JobInput)
  |     All warehouse P50 (n=162), no ABC section
  |
  +--[dimensional]--> abc_engine.estimate_dimensional(JobInput)
  |     All warehouse P50 (n=115), purchased letters
  |
  +--[flatpanel]--> abc_engine.estimate_flatpanel(JobInput)
  |     Simple sheet metal + vinyl, face-mounted
  |
  +--[removal]--> abc_engine.estimate_removal(JobInput)
        Two-tier: warehouse P50 x 1.20 / PF formula fallback
  |
  v
EstimateResult
  |  labor_lines: list[LaborLine]  (work_code, hours, formula, department)
  |  install_lines: list[LaborLine]
  |  material_bom: list[dict]  (item, part#, qty, unit)
  |  led_spec: dict
  |  total_man_hours, total_crew_hours
  |  warnings: list[str]
  |
  v
JSON response -> Web UI / Notion update / KeyedIn formatting
```

### Pipeline 3: All API Endpoints (Summary)

| Category | Endpoints | Data Sources |
|----------|-----------|--------------|
| **PDF Upload** | POST /api/upload-pdf | PyMuPDF (fitz) |
| **Footage Chart** | POST /api/footage | abc_engine footage charts |
| **Estimation** (8 types) | POST /api/estimate, /monument, /awning, /removal, /pylon, /cabinet, /directional, /dimensional | abc_engine + calibration.json + DuckDB |
| **Calibration** | POST /api/calibrate | DuckDB (signx.duckdb) |
| **Structural** (6) | POST /api/structural/wind, /foundation, /anchors, /member-check, /member-select, /full-design | apex_signcalc (external) |
| **Drawing Search** | GET /api/drawings/search, /search-bid | \\ES-FS02\Customers2 (SMB) |
| **Notion Bids** | GET /api/notion/bids, POST /takeoff, /update-status | Notion API |
| **Notification** | POST /api/notify/bid-ready, /webhook | SMTP (SMS gateway), Power Automate |
| **KeyedIn** | POST /api/keyedin/format | In-memory formatting |
| **Dossier** | GET /api/dossier/{customer} | project_files (\\ES-FS02\Customers2) |
| **Customer Intel** | GET /api/intel/customer/{name}, /similar, /market | customer_intel (CSV) |
| **Bid Scoring** | POST /api/bid/score, /ml-score | bid_scoring (CSV), bid_model (sklearn) |
| **Email Intake** | GET /api/intake/feed, POST /manual | mail_state (SQLite), mail_classifier |
| **Static** | GET / | static/index.html |

---

## 6. Configuration & Secrets

### Environment Variables (16 total, loaded from `../.env`)

| Variable | File | Default | Purpose |
|----------|------|---------|---------|
| `NOTION_TOKEN` | app.py:40, mail_classifier.py:31, check_pipeline.py:3 | `""` | Notion API bearer token |
| `NOTION_BID_PIPELINE` | app.py:41 | `""` | Notion Bid Pipeline database ID |
| `ANTHROPIC_API_KEY` | mail_classifier.py:30 | `""` | Claude Haiku API key for email classification |
| `NOTIFY_WEBHOOK_URL` | app.py:47 | `""` | Power Automate webhook URL for bid notifications |
| `SMS_PHONE` | app.py:50 | `"7122666482"` | SMS recipient phone number |
| `SMS_CARRIER_GATEWAY` | app.py:51 | `"vtext.com"` | Carrier email-to-SMS gateway (Verizon) |
| `SMTP_SERVER` | app.py:52 | `""` | SMTP server hostname |
| `SMTP_FROM` | app.py:53 | `""` | SMTP sender email address |
| `SMTP_PORT` | app.py:1259 | `"587"` | SMTP port (TLS) |
| `SMTP_USER` | app.py:1260 | `""` | SMTP authentication username |
| `SMTP_PASS` | app.py:1261 | `""` | SMTP authentication password |
| `SIGNX_WAREHOUSE_DB` | calibrate.py:36 | `"C:/Scripts/signx-warehouse/warehouse/signx.duckdb"` | DuckDB warehouse database path |
| `DRAWINGS_ROOT` | drawing_search.py:40, project_files.py:55 | `"\\\\ES-FS02\\Customers2"` | SMB path to customer drawings |

### Hardcoded Constants (Critical)

| Constant | File:Line | Value | Purpose |
|----------|-----------|-------|---------|
| `TAKEOFF_BASE_URL` | mail_processor.py:35 | `http://localhost:8765` | Self-referencing API base |
| `POLL_INTERVAL` | mail_processor.py:32 | `60` (seconds) | Email polling frequency |
| `LOOKBACK_DAYS` | mail_processor.py:33 | `7` | Email lookback window |
| `SALESPERSON_FOLDERS` | mail_processor.py:31 | `["Jeff Fye", "Joe Phillips", "Rich Thompson", "House"]` | Outlook folder names |
| `BID_PIPELINE_DB` | mail_classifier.py:34 | `304c1e58d2dd814aae63c6a0d44e6679` | Notion Bid Pipeline DB ID |
| `CORR_LOG_DB` | mail_classifier.py:35 | `309c1e58d2dd81ef9871d22f0e82a6f1` | Notion Correspondence Log DB ID |
| `VAR_REG_DB` | mail_classifier.py:36 | `309c1e58d2dd815a9a44edd9442c2a77` | Notion Variation Register DB ID |
| `NOTION_API_VERSION` | mail_classifier.py:32 | `"2022-06-28"` | Notion API version header |
| `IMPLIED_RATE` | warehouse.py | `40.0` ($/hr) | Labor cost to hours conversion |
| `WAREHOUSE_DB` | calibrate.py | `"C:/Scripts/signx-warehouse/warehouse/signx.duckdb"` | DuckDB path |
| `DB_PATH` | mail_state.py:18 | `data/mail_state.db` | SQLite database path |
| `DESIGN_HOURS` | abc_engine.py | `1.0` | Standard design hours per job |
| `FAB_LAYOUT_HOURS` | abc_engine.py | `1.5` | Standard fab layout hours |
| `MIN_BID_HOURS` | abc_engine.py | Business rule minimum | Minimum hours for any bid |

### Notion Database IDs (4 total)

| ID | Database | Used In |
|----|----------|---------|
| `304c1e58d2dd814aae63c6a0d44e6679` | Bid Pipeline | mail_classifier.py, check_pipeline.py, app.py |
| `309c1e58d2dd81ef9871d22f0e82a6f1` | Correspondence Log | mail_classifier.py |
| `309c1e58d2dd815a9a44edd9442c2a77` | Variation Register | mail_classifier.py |
| (from `NOTION_BID_PIPELINE` env var) | Bid Pipeline (alternate ref) | app.py |

### Hardcoded URLs (15 total)

| URL | File | Purpose |
|-----|------|---------|
| `https://api.notion.com/v1/databases/` | app.py (x2), mail_classifier.py (x2), check_pipeline.py | Notion API database queries |
| `https://api.notion.com/v1/pages` | app.py (x2), mail_classifier.py (x3) | Notion API page CRUD |
| `http://localhost:8765` | mail_processor.py | Self-referencing API (takeoff trigger) |
| `http://schemas.microsoft.com/mapi/proptag/0x1035001E` | mail_processor.py | MAPI property tag for Internet Message-ID |
| `http://127.0.0.1:18765` | tests/test_endpoints_live.py | Test server URL |
| `http://127.0.0.1:18766` | tests/test_performance.py | Performance test server URL |

### File System Paths (Hardcoded)

| Path | File | Purpose |
|------|------|---------|
| `\\ES-FS02\Customers2` | drawing_search.py, project_files.py | Customer drawings SMB share |
| `C:/Scripts/signx-warehouse/warehouse/signx.duckdb` | calibrate.py, abc_engine.py | DuckDB warehouse database |
| `C:/Scripts/signx-warehouse/warehouse/raw/so_contracts_parsed.csv` | warehouse.py, bid_scoring.py, customer_intel.py | Historical jobs CSV |
| `C:/Scripts/signx-warehouse/warehouse/raw/quote_status_report.csv` | bid_scoring.py, bid_model.py | Quote status CSV |
| `data/calibration.json` | abc_engine.py | Runtime calibration data |
| `data/mail_state.db` | mail_state.py | Email dedup SQLite |
| `../.env` | mail_classifier.py, app.py | Environment variables file |

---

## 7. Database Schema

### SQLite: `data/mail_state.db`

Journal mode: WAL. Foreign keys: ON.

**Table: `processed_emails`** (4 rows as of 2026-02-21)

| Column | Type | Constraint | Purpose |
|--------|------|-----------|---------|
| `internet_message_id` | TEXT | PRIMARY KEY | Email dedup key (MAPI Message-ID or fallback) |
| `processed_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | When processed |
| `flow` | TEXT | NOT NULL | `"bid_intake"` or `"correspondence"` |
| `folder` | TEXT | NOT NULL | Salesperson folder name |
| `subject` | TEXT | | Email subject line |
| `sender` | TEXT | | Sender display name |
| `result_json` | TEXT | | JSON blob of classify_and_route() result |

**Table: `follow_up_timers`** (0 rows)

| Column | Type | Constraint | Purpose |
|--------|------|-----------|---------|
| `bid_page_id` | TEXT | PRIMARY KEY | Notion page ID for the bid |
| `quote_name` | TEXT | | Quote display name |
| `customer` | TEXT | | Customer name |
| `salesman` | TEXT | | Assigned salesperson |
| `quoted_at` | DATETIME | | When quote was sent |
| `reminder_sent_at` | DATETIME | | When 48hr reminder was sent |
| `status` | TEXT | DEFAULT 'active' | `active`, `reminded` |

**Table: `closeout_variance`** (0 rows)

| Column | Type | Constraint | Purpose |
|--------|------|-----------|---------|
| `work_order` | TEXT | PRIMARY KEY | KeyedIn work order number |
| `quote_number` | TEXT | | Quote number |
| `estimated_total` | REAL | | Estimated total hours |
| `actual_total` | REAL | | Actual total hours |
| `variance_pct` | REAL | | (actual - estimated) / estimated * 100 |
| `computed_at` | DATETIME | | When variance was computed |

### DuckDB: `signx.duckdb` (external, read-only)

Location: `C:/Scripts/signx-warehouse/warehouse/signx.duckdb`

Referenced tables (from `calibrate.py` and `abc_engine.py`):
- `so_contract_labor` -- work order labor detail (work_code, actual_hours, run_date, wo_number)
- `so_contracts` -- sales order contract summary
- `so_contract_wo_summary` -- work order summary with description, sign_type, revenue

### CSV Data Files (external, read-only)

| File | Location | Rows | Used By |
|------|----------|------|---------|
| `so_contracts_parsed.csv` | `C:/Scripts/signx-warehouse/warehouse/raw/` | 25,400 | warehouse.py, bid_scoring.py, customer_intel.py, bid_model.py |
| `quote_status_report.csv` | `C:/Scripts/signx-warehouse/warehouse/raw/` | 18,972 | bid_scoring.py, bid_model.py |

### Notion Databases (external, via API)

| Database | ID | Properties (Key Fields) |
|----------|----|-----------------------|
| Bid Pipeline | `304c1e58...` | Quote Number, Customer, Sign Type, Salesperson, Status, Total Hours, Stage |
| Correspondence Log | `309c1e58...ef9871d22f0e82a6f1` | Subject, Sender, Category, Related Bid, Date |
| Variation Register | `309c1e58...9a44edd9442c2a77` | Subject, Type (change_order, rfi, etc.), Related Bid, Status |

---

## 8. Dead Code & Redundancy

### Potentially Uncalled Functions

| Function | File | Evidence |
|----------|------|----------|
| `robust_z_mad()` | abc_engine.py:800 | Statistical helper -- only used internally by `baseline_for_group()` which is itself only conditionally called |
| `baseline_for_group()` | abc_engine.py:830 | Only called if numpy/pandas available, not part of main estimate path |
| `_cal_work_code_median()` | abc_engine.py:112 | Calibration helper -- not directly called in current estimate functions |
| `add_follow_up()` | mail_state.py:149 | Follow-up timer creation -- defined but no callers in the codebase (feature not yet wired) |
| `get_pending_follow_ups()` | mail_state.py:177 | Follow-up timer query -- no callers (feature not yet wired) |
| `mark_follow_up_sent()` | mail_state.py:193 | Follow-up timer update -- no callers (feature not yet wired) |
| `warehouse_stats()` | customer_intel.py | Referenced in docstring but may be an alias -- verify |

### Unimported/Standalone Files

| File | Purpose | Status |
|------|---------|--------|
| `sign_type_analysis.py` | DuckDB query script | Standalone utility, not imported by any module |
| `mondf_analysis.py` | DuckDB query script | Standalone utility, not imported by any module |
| `t1_query.py` | DuckDB query for specific WO | Standalone utility, not imported by any module |
| `check_pipeline.py` | Notion API query | Standalone utility, not imported by any module |

### Duplicate Patterns

| Pattern | Locations | Notes |
|---------|-----------|-------|
| `NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")` | app.py:40, mail_classifier.py:31, check_pipeline.py:3 | Same env var loaded independently 3 times |
| `DRAWINGS_ROOT` | drawing_search.py:40, project_files.py:55 | Same SMB path loaded from same env var in 2 files |
| Section 2 rate lookup (`SECTION_2_RATES.get(cab_key)`) | abc_engine.py:1582, 2148, 2448 | Same fallback logic repeated in estimate_monument, estimate_pylon, estimate_cabinet |
| Section 5A paint rate lookup | abc_engine.py:1694, 2257, 2546, 2759, 2946 | Same pattern in 5 estimator functions |
| Vinyl labor calculation | abc_engine.py:1719, 2282, 2571, 2782 | Same `1.0 + SF * 0.02` / `1.0 + SF * 0.03` pattern in 4 estimators |
| `corrected()` / `corr_note()` helper closures | abc_engine.py:1569, 2134, 2434 | Same correction factor pattern defined as local closures in 3 estimators |
| OT calculation pattern | abc_engine.py (all estimators) | Each estimator has its own OT rate constants and similar calculation logic |

### TODO/PROVISIONAL Markers

| File | Line | Tag | Text |
|------|------|-----|------|
| `abc_engine.py` | 548 | PROVISIONAL | "will refine with direct warehouse query when available" |
| Multiple estimators | -- | [PROVISIONAL] | estimate_directional, estimate_dimensional marked as PROVISIONAL in docstrings |
| `abc_engine.py` | 2411 | [LOW CONFIDENCE] | estimate_cabinet -- "only 31 warehouse jobs available for calibration" |

### Unused Tables

| Table | File | Status |
|-------|------|--------|
| `follow_up_timers` | mail_state.py | Schema created, 0 rows, no callers for write functions |
| `closeout_variance` | mail_state.py | Schema created, 0 rows, no callers at all |

---

## 9. External Touchpoints

### HTTP API Calls (Outbound)

| Target | URL Pattern | File | Method | Purpose |
|--------|------------|------|--------|---------|
| Notion API | `https://api.notion.com/v1/databases/{id}/query` | app.py, mail_classifier.py, check_pipeline.py | POST | Query database entries |
| Notion API | `https://api.notion.com/v1/pages` | app.py, mail_classifier.py | POST | Create pages |
| Notion API | `https://api.notion.com/v1/pages/{id}` | app.py, mail_classifier.py | PATCH | Update page properties |
| Anthropic API | (via `anthropic` SDK) | mail_classifier.py | POST | Claude Haiku email classification |
| Self (localhost) | `http://localhost:8765/api/notion/takeoff` | mail_processor.py | POST | Auto-trigger estimation |
| Self (localhost) | `http://localhost:8765/api/notify/bid-ready` | mail_processor.py | POST | Trigger SMS notification |
| Power Automate | `NOTIFY_WEBHOOK_URL` env var | app.py | POST | Webhook notification |

### Win32com / COM Objects

| Component | File | Purpose |
|-----------|------|---------|
| `Outlook.Application` | mail_processor.py | MAPI namespace access for email reading |
| `namespace.GetDefaultFolder(6)` | mail_processor.py | olFolderInbox access |
| `item.PropertyAccessor.GetProperty()` | mail_processor.py | Internet Message-ID extraction |
| `pythoncom.CoInitialize()` | mail_processor.py | COM apartment initialization |

### File I/O (Network/Local)

| Path | File | Operation | Purpose |
|------|------|-----------|---------|
| `\\ES-FS02\Customers2` | drawing_search.py, project_files.py | Read (os.walk, os.listdir) | Customer drawing file discovery |
| `C:/Scripts/signx-warehouse/warehouse/signx.duckdb` | calibrate.py, abc_engine.py | Read (DuckDB) | Warehouse labor data queries |
| `C:/Scripts/signx-warehouse/warehouse/raw/so_contracts_parsed.csv` | warehouse.py, bid_scoring.py, customer_intel.py, bid_model.py | Read (csv.DictReader) | Historical job data |
| `C:/Scripts/signx-warehouse/warehouse/raw/quote_status_report.csv` | bid_scoring.py, bid_model.py | Read (csv.DictReader) | Quote outcome data |
| `data/calibration.json` | abc_engine.py, calibrate.py | Read/Write (json) | Calibration factors |
| `data/mail_state.db` | mail_state.py | Read/Write (sqlite3) | Email processing state |
| `data/mail_processor.log` | mail_processor.py | Write (RotatingFileHandler) | Processing log (5MB x 3 backups) |
| `../.env` | mail_classifier.py, app.py | Read (dotenv) | Environment variables |

### SMTP (Outbound)

| Server | File | Purpose |
|--------|------|---------|
| `SMTP_SERVER` (env var) | app.py:1253-1295 | Email-to-SMS via `{phone}@{carrier_gateway}` |
| Default gateway: `vtext.com` | app.py | Verizon SMS gateway |
| Port: 587 (TLS) | app.py | Standard SMTP-TLS |

### External Service Dependencies

| Service | SDK/Protocol | File | Critical? |
|---------|-------------|------|-----------|
| **Notion** | REST API (requests/httpx) | app.py, mail_classifier.py | Yes -- bid pipeline CRUD |
| **Anthropic Claude Haiku** | `anthropic` Python SDK | mail_classifier.py | Yes -- email classification |
| **DuckDB** (signx.duckdb) | `duckdb` Python driver | calibrate.py, abc_engine.py | Medium -- calibration only |
| **Outlook** | Win32com (COM) | mail_processor.py | Yes -- email intake |
| **SMB File Server** | OS filesystem (UNC paths) | drawing_search.py, project_files.py | Medium -- drawing search |
| **SMTP** | smtplib (stdlib) | app.py | Low -- SMS notifications only |
| **Power Automate** | Webhook (HTTP POST) | app.py | Low -- optional notification |
| **apex_signcalc** | Python import (local) | app.py | Medium -- structural engineering only |

### apex_signcalc Integration

Located at `../services/signcalc-service` (added to sys.path at app.py:100-108).
Provides structural engineering calculations:
- `wind_load()` -- ASCE 7-22 wind pressure
- `foundation_design()` -- spread footing / drilled shaft
- `anchor_design()` -- anchor bolt capacity
- `check_member()` -- AISC 360 steel member check
- `select_member()` -- optimal steel member selection
- `full_design()` -- complete structural package

---

## Appendix A: Rate Table Reference

### ABC Section 4 Rates (Channel Letters, per PF)

| Construction | Height | 0210 Sheet | 0270 Mount | 0410 Paint |
|-------------|--------|-----------|-----------|-----------|
| Face-Lit | 7"-11" | 0.149 | 0.024 | 0.022 |
| Face-Lit | 12"-24" | 0.102 | 0.021 | 0.017 |
| Face-Lit | 25"-54" | 0.069 | 0.025 | 0.025 |
| Face-Lit | 55"-120" | 0.102 | 0.021 | 0.017 |
| Halo | 7"-11" | 0.164 | 0.026 | 0.024 |
| Halo | 12"-24" | 0.112 | 0.023 | 0.019 |
| Halo | 25"-54" | 0.076 | 0.028 | 0.028 |

### Section 10B Install Rates (per PF, CREW-hours)

| Height | 0-35' | Over 35' |
|--------|-------|----------|
| 7"-11" | 0.051 | 0.066 |
| 12"-24" | 0.036 | 0.047 |
| 25"-54" | 0.032 | 0.042 |

### Work Codes (41 total in WORK_CODES dict)

| Code | Description | Department |
|------|-------------|------------|
| 0110 | Design/Drafting | Art/Design (100) |
| 0200 | Fabrication Layout | Fabrication (200) |
| 0210 | Sheet Metal | Fabrication (200) |
| 0215 | Structural Steel | Fabrication (200) |
| 0220 | Extrusions | Fabrication (200) |
| 0235 | Routing | Fabrication (200) |
| 0240 | Flat Cut Out Letters | Fabrication (200) |
| 0250 | Awning Fabrication | Fabrication (200) |
| 0260 | LED/Neon Install | Fabrication (200) |
| 0270 | Misc Fabrication | Fabrication (200) |
| 0282 | Check In Freight | Fabrication (200) |
| 0310 | LED Wiring | Electrical (300) |
| 0340 | Electrical Wiring | Electrical (300) |
| 0410 | Clean & Etch | Paint/Finish (400) |
| 0420 | Prime & Finish | Paint/Finish (400) |
| 0520 | Cut/Weed Vinyl | Vinyl (500) |
| 0550 | Vinyl Application | Vinyl (500) |
| 0605 | Footing Install | Installation (600) |
| 0610 | Load/Unload | Installation (600) |
| 0620 | Travel | Installation (600) |
| 0625 | Removal | Installation (600) |
| 0630 | 1 Man & Truck Install | Installation (600) |
| 0640 | 2 Men & Truck Install | Installation (600) |
| 0650 | 3 Men & Crane Install | Installation (600) |
| 9200 | Fabrication Overtime | Fabrication (200) |
| 9600 | Installation Overtime | Installation (600) |

---

## Appendix B: Sign Type Coverage Matrix

| Sign Type | Estimator | ABC Section | Calibration Source | Confidence |
|-----------|-----------|-------------|-------------------|------------|
| CLLIT | `estimate()` | Section 4B/4C + 10B | Warehouse (n=2,350) + ABC formulas | HIGH |
| CLNON | `estimate()` | Section 4A + 10B | Warehouse + ABC formulas | HIGH |
| MONDF | `estimate_monument()` | Section 2 + 5A + corrections | Warehouse (n=954) | HIGH |
| MONSF | `estimate_monument()` | Section 2 + 5A + corrections | Warehouse (n=205) | MEDIUM |
| POLLIT | `estimate_pylon()` | Section 2 + POLLIT corrections | MONDF pattern scaled (n=461) | PROVISIONAL |
| POLNON | `estimate_pylon()` | Section 2 + POLLIT corrections | MONDF pattern scaled | PROVISIONAL |
| ALULIT | `estimate_cabinet()` | Section 2 + ALULIT corrections | MONDF + 30% buffer (n=31) | LOW |
| ALUNON | `estimate_cabinet()` | Section 2 + ALULIT corrections | MONDF + 30% buffer | LOW |
| AWNNON | `estimate_awning()` | Eagle actuals (SF-based) | Jobs #11530/#11532 (n=66) | MEDIUM |
| DIRECT | `estimate_directional()` | None (warehouse P50) | Warehouse (n=162) | PROVISIONAL |
| GEMINI | `estimate_dimensional()` | None (warehouse P50) | Warehouse (n=115) | PROVISIONAL |
| FLATPNL | `estimate_flatpanel()` | None (simple flat panel) | Minimal data | PROVISIONAL |
| REMOVAL | `estimate_removal()` | Warehouse P50 x 1.20 | Warehouse (all types) | HIGH |

---

## Appendix C: ML Model Features (bid_model.py)

| # | Feature | Description |
|---|---------|-------------|
| 1 | `price_log` | log(quoted_price) |
| 2 | `salesperson_encoded` | Label-encoded salesperson |
| 3 | `quarter` | Calendar quarter (1-4) |
| 4 | `month_sin` | sin(2pi * month/12) for seasonality |
| 5 | `month_cos` | cos(2pi * month/12) for seasonality |
| 6 | `days_to_expiry` | Days between quote date and expiry |
| 7 | `customer_job_count` | Historical job count for customer |
| 8 | `customer_total_revenue_log` | log(total historical revenue) |
| 9 | `customer_avg_margin` | Average gross margin % for customer |
| 10 | `days_since_last_job` | Recency of last job |
| 11 | `is_repeat_customer` | Boolean: has prior jobs |
| 12 | `price_vs_type_avg` | Quote price / avg price for sign type |

**Time-decay weighting:** 5-year half-life, exponential decay from quote date.
**Cross-validation:** 5-fold stratified, reporting AUC and accuracy.
**Training:** Eager on import -- model trains when bid_model.py is first imported.

---

*End of CODEBASE-MAP.md*
