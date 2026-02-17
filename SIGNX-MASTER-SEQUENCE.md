# SIGNX Master Sequence -- Eagle Sign Co

**Version:** 1.0
**Date:** 2026-02-17
**Repo:** `EAGLE605/SignX` (main branch)
**Last Commit:** `1781383` -- unified abc_engine with monument/awning/removal estimators + warehouse-derived corrections

This is the single source of truth for the entire SignX project. Everything that exists, everything that is planned, and the order in which it should be built.

---

## The Full Pipeline Vision

```
Email --> [SignX-Intake] --> Notion Bid Pipeline --> [SignX-Takeoff] --> [SignX-Intel] --> [SignX-Studio] --> [SignX-Draw] --> KeyedIn
```

| Stage | What It Does | Status |
|-------|-------------|--------|
| **Email** | Bid requests arrive at brady@eaglesign.net, sorted into BID REQUEST/{salesperson} subfolders | MANUAL |
| **SignX-Intake** | Power Automate extracts project data via Claude, creates Notion row | PLANNED (build guide ready) |
| **Notion Bid Pipeline** | Command center DB (304c1e58...) tracks 21 quotes, $516K pipeline | EXISTS |
| **SignX-Takeoff** | ABC formula engine + warehouse benchmark = labor/material/cost estimate | WORKING |
| **SignX-Intel** | ML cost prediction, warehouse analytics, margin leak detection | PARTIAL (analysis done, models not trained) |
| **SignX-Studio** | React PWA frontend -- dashboard, builder, engineering viewer | NOT STARTED (node_modules scaffolded, no source) |
| **SignX-Draw** | DXF/CAD generation via ezdxf -- foundation plans, shop drawings | PARTIAL (API route exists, ezdxf integrated) |
| **KeyedIn** | ERP quote entry -- 333 endpoints mapped, MCP server exists | PARTIAL (no auto-entry yet) |

---

## What is DONE (completed and working today)

### Estimation Engine (signx-takeoff/)

| Component | Evidence | Files |
|-----------|----------|-------|
| Channel letter ABC estimator | Section 4B/4C/4A rates, 3 height ranges, 4 work codes per range | `signx-takeoff/abc_engine.py` (1,864 lines) |
| Monument estimator | ABC Section 2 cabinet rates + warehouse-calibrated corrections from 954 jobs | `signx-takeoff/abc_engine.py` |
| Awning estimator | Warehouse P50 + buffer, AWNNON sign type profiling | `signx-takeoff/abc_engine.py` |
| Removal estimator | Install crew-hrs x 0.65 x 2 formula, disposal/permit add-ons | `signx-takeoff/abc_engine.py` |
| PDF PF extraction | PyMuPDF bezier curve walker, Shoelace area, auto-scale detection | `signx-takeoff/extract_pf_from_pdf.py` (371 lines) |
| Footage chart calculator | Standard PF-per-letter lookup | `signx-takeoff/app.py` |
| Warehouse benchmark | 2,443 channel letter jobs, confidence scoring, nearest-match | `signx-takeoff/warehouse.py` (177 lines) |
| LED sizing + power supply | Modules = PF x density x 1.05, wattage calc, PS bracket selection | `signx-takeoff/abc_engine.py` |
| Material BOM with real part numbers | 8 line items (acrylic, return coil, back, trim cap, LED, PS, wire, hardware) | `signx-takeoff/abc_engine.py` |
| Web UI | Dark-themed SPA, PDF drag-drop, 3 PF modes, tabbed output, CSV export | `signx-takeoff/static/index.html` (696 lines) |
| FastAPI server | 3 endpoints: `/api/extract-pf`, `/api/footage-chart`, `/api/estimate` | `signx-takeoff/app.py` (226 lines) |
| Validation suite | 16/20 pass, 8/8 part numbers verified | `signx-takeoff/test_validation.py` |

### Structural Engineering (signcalc-service/)

| Component | Evidence | Files |
|-----------|----------|-------|
| ASCE 7-22 wind loads | Full Section 29.3, Kz table (22 heights x 3 exposures), Kd, Ke, Cf Cases A/B/C, load combos ASD6/7/8 | `apex_signcalc/wind_asce7.py` (737 lines) |
| Foundation design -- Broms/Hansen/IBC | 3 PE-stampable methods, cohesive + cohesionless soil, DFM cost flags, full audit trail | `apex_signcalc/foundation_embed.py` (633 lines) |
| Sections database | 2,299 AISC 16th Ed shapes loaded from JSON, 15 shape types, fallback for common sign sections | `apex_signcalc/sections.py` (379 lines), `data/standards/aisc_shapes.json` (1,133 KB) |
| Load combinations | ASD and LRFD combos per ASCE 7-22 | Embedded in `wind_asce7.py` |
| Wind EN 1991 (Eurocode) | European wind code implementation | `apex_signcalc/wind_en1991.py` |
| Rebar schedules | Basic rebar design (3 options -- needs expansion to ACI 318-19) | `apex_signcalc/rebar_schedules.py` |
| Report rendering | JSON/PDF/DXF output format | `apex_signcalc/report_render.py` |

### Knowledge Bases (data/standards/)

| KB | File | Content |
|----|------|---------|
| AISC Shapes | `aisc_shapes.json` | 2,299 sections, 15 types, 20+ properties each |
| ASCE 7-22 Wind | `asce7_22_wind.json` | Chapter 26 + 29.3 tables (Kz, Kd, Ke, Cf) |
| Foundation Methods | `foundation_methods.json` | Broms/Hansen/Czerniak/IBC 1807.3.1 reference |
| ABC Labor Rates | `abc-labor-rates-complete.md` | 342 formulas, Sections 2/3F/4/5/10 |

### Data Warehouse

| Asset | Size | Location |
|-------|------|----------|
| Merged CSVs (7 tables) | 1.56M rows, 542 MB | `C:\Scripts\signx-warehouse\warehouse\raw\csv_exports\*_ALL.csv` |
| Enriched CSVs (5 tables) | 571K data rows, 70.2 MB | `C:\Scripts\signx-warehouse\warehouse\raw\csv_exports\*_enriched.csv` |
| Ref tables (33) | 968 rows, 1.2 MB | `C:\Scripts\signx-warehouse\warehouse\raw\ref_tables\*.json` |
| SO Contracts | 25,400 rows, 18 MB | `C:\Scripts\signx-warehouse\warehouse\raw\so_contracts_parsed.csv` |
| DuckDB warehouse | 12,189 jobs, 54K labor records | `signx-warehouse/warehouse/production/eagle_warehouse.db` (211 MB) |
| ESC file index | 40,611 files, 4.8 MB | `C:\Scripts\signx-warehouse\esc_file_index.csv` |

### Agent Framework (svcs/)

| Agent | Lines | Real Logic |
|-------|------:|-----------|
| orchestrator | ~300 | Task enqueueing, report synthesis, SHA256 integrity verification, SLA definitions |
| agent_cad | ~140 | FreeCAD script generation, content-addressed blob storage |
| agent_compliance | ~190 | IP trigram similarity, safety factor validation, ASME Y14.5 tagging |
| agent_dfma | ~175 | Sheet metal / machining / 3D printing DFM rules, cost model |
| agent_materials | ~255 | CSV material selection, min-max normalization, weighted scoring |
| agent_parts | ~190 | Parts catalog search, fuzzy token matching, Top-5 ranking |
| agent_stackup | ~190 | Monte Carlo tolerance stackup (50K samples), Cp/Cpk indices |
| agent_translator | ~285 | Repo indexer, keyword Q&A engine, caches at artifacts/translator/ |
| common/fsqueue | ~80 | Cross-platform filesystem queue with atomic lockfile |
| common/index | ~70 | Idempotent NDJSON processed-record index |

### Compliance Checking (signs-service/)

| Standard | Coverage |
|----------|----------|
| UL 48 | Electric sign safety rules |
| NEC 600 | Disconnect, GFCI, bonding requirements |
| UL 879 / UL 969 | Label sets |
| MUTCD | Traffic sign compliance |
| OSHA 1910.145 | Safety sign specifications |

### Infrastructure

| Component | Status |
|-----------|--------|
| CI/CD | 3 GitHub Actions workflows: `ci.yml`, `ml-ci.yml`, `security-scan.yml` |
| Docker Compose (dev) | 12 services defined in `infra/compose.yaml` |
| Docker Compose (prod) | pgvector, Redis, FastAPI API in `docker-compose.prod.yml` |
| Monitoring | Prometheus + Grafana + 10 alert rules + synthetic monitoring |
| Makefile | 10 targets (lint, format, up, down, test, etc.) |
| DB backups | 3 SQL dumps at `infra/backups/postgres/` |
| Security scanning | Semgrep, Gitleaks, Safety in CI |

### Platform Core (signx_platform/)

| Component | Status |
|-----------|--------|
| Module registry | Plugin system with register/get/list, event-subscriber discovery |
| Event bus | Pub/sub with wildcard patterns, in-memory history (1,000 events) |

### Other Completed Items

| Item | Details |
|------|---------|
| PA build guide | 7-step Power Automate flow guide at `C:\Scripts\signx-intake\pa-flow-build-guide.md` |
| Monday estimation briefs | 3 context briefs (Mercy UC, St. Anthony EMC, Ankeny Parks) |
| KeyedIn endpoint mapping | 262 CGI + 71 Informer = 333 endpoints |
| Work code profiling | 51 codes with dept/phase mapping |
| Margin leak analysis | >$1.2M identified across CLLIT, AWNNON, POLLIT, universal OT |
| Gap analysis | Complete Phase 0 gap analysis with margin framework |

---

## What is IN PROGRESS (current session work)

| Item | Progress | Details |
|------|----------|---------|
| Dashboard HTML | IN PROGRESS | Multi-section web app with all SignX subsystems |
| Import fix verification | COMPLETE | All 7 P0-P7 blockers resolved, 15+ components unblocked |
| Phase 2 structural hardening | 60% | 3/5 modules rewritten (wind, foundation, sections); anchors_baseplate and supports_pipe remain stubs |
| API endpoint testing | IN PROGRESS | Testing takeoff, monument, wind endpoints with real data |

---

## Master Feature Sequence (numbered, ordered by dependency and value)

### Track 1: Estimation Engine (signx-takeoff) -- THE MONEY MAKER

This is where Eagle Sign makes or loses money. Every hour of estimation error multiplied across hundreds of jobs per year.

| # | Feature | Status | Details |
|---|---------|--------|---------|
| 1 | Channel letter ABC estimator | DONE | Section 4B/4C/4A, 3 height ranges, 4 work codes, LED sizing, material BOM |
| 2 | Monument estimator | DONE | ABC Section 2 cabinet + warehouse corrections from 954-job analysis |
| 3 | Awning estimator | DONE | Warehouse P50 + 20% buffer, AWNNON profiling |
| 4 | Removal estimator | DONE | Install x 0.65 x 2, disposal/permit add-ons |
| 5 | Extrusion/structural steel estimator | TODO | Work code 0220, bimodal distribution needs segment detection. No ABC section -- pure warehouse-based. |
| 6 | Pylon/pole sign estimator | TODO | POLLIT -- 461 jobs in warehouse (highest volume after channel letters). ABC Sections 2/5/10 for cabinet/install components. Structural fab (0215) has +11.03h variance. |
| 7 | Cabinet estimator | TODO | ALULIT (31 jobs) / ALUNON (13 jobs). ABC Section 2A-2E. Low warehouse confidence -- group with MONDF patterns + 30% buffer. |
| 8 | Post & panel estimator | TODO | Covered in Accutrack v3.8.1 but rates not digitized. Check `abcsignc.mdb`. |
| 9 | Routed face estimator | TODO | Covered in Accutrack v3.8.1. CNC-heavy -- large discount factor applies. |
| 10 | Wireway/curved frame estimator | TODO | Covered in Accutrack v3.8.1. Specialty fabrication. |
| 11 | CNC discount factors | TODO | 30-50% fab reduction for codes 0210/0215/0220/0230/0235/0240/0270. Needs shop floor timing study to calibrate. Does NOT apply to install, paint, electrical, or vinyl. |
| 12 | Missing ABC Sections 1, 6-9 | TODO | Read from `ABC PRICING GUIDE 1974.xlsx` (5,738 lines) and `ABC 6th Edition Handbook.pdf`. Existing sections (2/3F/4/5/10) cover primary sign types. |
| 13 | Overtime buffer | TODO | 30-80% of jobs have OT (codes 9200/9600), always estimated at 0.00. Universal: add automatic 15% OT buffer. MONSF worst at 81% OT occurrence with +8.71h avg. |
| 14 | Installation recalibration | TODO | Current install estimates off by 5-14h across all sign types. Replace with warehouse P50. AWNNON worst at +13.98h variance. |
| 15 | Per-letter customer pricing converter | TODO | Industry has shifted to $150-$550/letter for customer quotes. Keep PF for internal ABC calcs, convert for customer-facing output. Add per-LF raceway pricing ($35-$65/LF). |
| 16 | Dynamic margin manager | TODO | Client tier adjustment, job complexity multiplier (0.90x simple to 1.20x complex), material markup 1.5x, labor markup 1.3x, profit 20-30% of total per industry standard. |

### Track 2: Structural Engineering (signcalc-service) -- PE-STAMPABLE

All calculations must include code section references, safety factors, assumption lists, and audit trails for professional engineer stamp.

| # | Feature | Status | Details |
|---|---------|--------|---------|
| 17 | ASCE 7-22 wind loads | DONE | Full Section 29.3, 3 loading cases, exposure B/C/D, 22 heights, load combos |
| 18 | Foundation design -- Broms/Hansen/IBC | DONE | 3 methods, cohesive + cohesionless, DFM cost flags |
| 19 | Sections database -- 2,299 AISC shapes | DONE | All 15 shape types, full properties, JSON source |
| 20 | Load combinations | DONE | ASD6/7/8 per ASCE 7-22 |
| 21 | Anchor/baseplate design -- ACI 318-19 | STUB (16 lines) | Returns hardcoded values. Needs: base plate bearing, anchor bolt tension/shear interaction (Tu/Tn)^5/3 + (Vu/Vn)^5/3 <= 1.0, concrete breakout, pullout, side-face blowout |
| 22 | Member selection -- AISC 360-22 | STUB (18 lines) | Simple bending only. Needs: flexure with LTB (Ch F), shear (Ch G), axial compression with slenderness (Ch E), combined interaction H1-1a/H1-1b, compact/noncompact/slender classification, L/120 deflection limit |
| 23 | DXF/CAD export -- foundation plans | PARTIAL | API routes exist (`/api/cad/export/foundation`, `/api/cad/download/foundation`), ezdxf integrated, AIA layers defined, rebar schedule table. Plan/section views, title block implemented. |
| 24 | Seismic analysis | TODO | USGS data integration, ASCE 7-22 seismic provisions. DB migration 013 created but not populated. |
| 25 | Combined stress analysis | TODO | AISC 360-22 combined axial + bending interaction equations |
| 26 | Spread footing design | TODO | For monument/freestanding signs with base plates |
| 27 | Generative design | TODO | AI suggests 3 valid structural designs based on site constraints. Aspirational. |

### Track 3: LED & Electrical

| # | Feature | Status | Details |
|---|---------|--------|---------|
| 28 | Basic LED module count + power supply sizing | DONE | In abc_engine: face-lit PF x 1.2 x 1.05, halo PF x 1.0 x 1.05, PS bracket logic |
| 29 | NEC 600 compliance checking | DONE | Disconnect, GFCI, bonding requirements in signs-service |
| 30 | UL 48 electric sign safety | DONE | Rule module in signs-service |
| 31 | LED Wizard 8 clone -- PowerFlow engine | TODO | Research done (see `docs/research/`). Eagle already has LED Wizard v8 desktop. Web version would auto-populate module layouts by letter size, density guidelines, DXF export of module positions. |
| 32 | Voltage drop calculator | TODO | Wire run length -> voltage drop -> minimum wire gauge |
| 33 | Wire gauge selector | TODO | NEC ampacity tables, ambient temperature derating |
| 34 | EZLayout Builder web version | TODO | Principal Sloan layout tool equivalent. Research completed. |

### Track 4: PDF/Drawing Intelligence

| # | Feature | Status | Details |
|---|---------|--------|---------|
| 35 | PDF PF extraction -- PyMuPDF vector parser | DONE | Bezier curve walker, Shoelace area, works with Gemini Art (11% variance) and conceptuals with SF=2.75 (2-4%) |
| 36 | Footage chart calculator | DONE | Standard PF-per-letter lookup in app.py |
| 37 | Enhanced PDF parsing -- auto-detect sign type | TODO | Parse sign type, dimensions, location from bid PDFs automatically |
| 38 | Bluebeam automation -- auto-measure from markups | TODO | Read Bluebeam XML markups for dimension extraction |
| 39 | CorelDRAW macro integration | EXISTS | `CorelDraw Macros/Module1 Sign Takeoff.bas` -- VBA perimeter via `seg.Length`. Used as reference for PDF parser. |
| 40 | EnRoute CNC file generation | TODO | Export cut paths for CNC router/plasma |
| 41 | SAi Production Suite integration | TODO | Print/cut workflow integration |
| 42 | FreeCAD macro generation | PARTIAL | `services/signs-service/cad/macro.py` generates FreeCAD scripts. agent_cad wraps this. |
| 43 | Awning Composer 5 integration | TODO | Eagle already has Awning Composer 5 desktop software |
| 44 | Shop drawing generation -- ezdxf DXF | TODO | Full shop drawings beyond foundation plans. SignX-Draw sprint. |

### Track 5: Data & Intelligence (SignX-Intel)

| # | Feature | Status | Details |
|---|---------|--------|---------|
| 45 | Warehouse benchmark engine | DONE | 2,443+ channel letter jobs, labor derivation, confidence scoring |
| 46 | Work code profiling | DONE | 51 codes with dept/phase mapping, variance analysis |
| 47 | Margin leak detection | DONE | >$1.2M identified: CLLIT 0270 ($843K), universal OT ($325K), POLLIT structural ($67K), AWNNON install ($40K) |
| 48 | XGBoost cost predictor | EXISTS | `services/ml/cost_model.py` -- GPU-accelerated, feature engineering (aspect ratio, slenderness, wind pressure proxy), Monte Carlo uncertainty. Has 6 tests. Needs training on warehouse data. |
| 49 | PDF cost summary extractor | EXISTS | `services/ml/pdf_extractor.py` -- Eagle cost summary PDF extraction. Has 6 tests. |
| 50 | GNN structure graph | EXISTS | `services/ml/structure_graph.py` -- PyTorch Geometric for pole stress prediction. Has 2 tests. Needs torch_geometric installed. |
| 51 | CNC vs hand timing calibration | TODO | Needs actual Eagle CNC vs hand-fab timing data from shop floor study |
| 52 | Sign type auto-classifier | TODO | Regex patterns exist in `sign_type_analyzer.py`. Needs ML upgrade for bid PDF classification. |

### Track 6: Bid Pipeline & CRM (SignX-Intake)

| # | Feature | Status | Details |
|---|---------|--------|---------|
| 53 | Power Automate bid intake | PLANNED | Build guide ready at `C:\Scripts\signx-intake\pa-flow-build-guide.md`. 4 flows defined (BID-INTAKE-PROOF, BID-INTAKE-ALL, VENDOR-QUOTE-EXTRACT, DAILY-BID-DIGEST). Cost: ~$1-3/mo. Brady builds manually in PA editor. |
| 54 | Notion Bid Pipeline integration | READY | DB exists (304c1e58...), 21 quotes, $516K pipeline. Power Automate Notion IP connector configured. |
| 55 | Email -> Claude extraction -> Notion row | PLANNED | Anthropic IP connector (Claude Sonnet) extracts project data. JSON body templates ready. Known issue: Haiku wraps JSON in markdown fences -- must strip. |
| 56 | KeyedIn quote entry automation | EXISTS | `Keyedin/` directory with 333 endpoints mapped (262 CGI + 71 Informer). MCP server at EAGLE605/keyedin-mcp. No auto-entry flow built yet. 14 export endpoints need VPN testing. |
| 57 | Proposal PDF generator | TODO | AI generates PDF proposals with renders, specs, and pricing |
| 58 | DocuSign integration | TODO | Contract signing workflow |
| 59 | Lead gen from permits/filings | TODO | Scrape building permits and new business filings for prospects |

### Track 7: Shop Floor & Field (Future)

| # | Feature | Status | Details |
|---|---------|--------|---------|
| 60 | Job board / Kanban | TODO | Zero-click manufacturing execution per architecture plan |
| 61 | QR travelers for parts | TODO | QR scan updates job status automatically |
| 62 | Inventory deduction from BOM | TODO | Auto-deduct materials when fabrication starts |
| 63 | Smart dispatch for install crews | TODO | AI routes crews based on GPS and job readiness |
| 64 | AR preview -- phone shows sign placement | TODO | Uses engineering coordinates. Aspirational. |
| 65 | One-tap closeout with photo verification | TODO | AI verifies photo matches proof -> auto-invoice |
| 66 | Install PWA | TODO | Offline-capable PWA for field crews |

### Track 8: Platform & Infrastructure

| # | Feature | Status | Details |
|---|---------|--------|---------|
| 67 | Dashboard UI -- multi-section web app | IN PROGRESS | Being built this session. Vite + React + MUI + Zustand scaffolded in `ui/` (node_modules exist, no source yet). |
| 68 | Agent framework -- 9 agents + orchestrator | DONE | FSQueue-based, file-based for determinism, atomic operations. All agents import successfully. |
| 69 | Module registry + event bus | DONE | signx_platform/registry.py + events.py. Plugin architecture with auto-discovery. |
| 70 | Compliance checking | DONE | UL 48, NEC 600, UL 879/969, OSHA 1910.145, MUTCD rules in signs-service |
| 71 | Docker Compose dev stack -- 12 services | EXISTS | `infra/compose.yaml`. Services import-blocked until recent fixes. Now unblocked. |
| 72 | CI/CD -- 3 GitHub Actions workflows | DONE | ci.yml, ml-ci.yml, security-scan.yml with timeouts |
| 73 | Kubernetes helm charts | SKELETON | `k8s/charts/apex/` -- Chart.yaml + values exist. Templates MISSING. Not deployable. |
| 74 | Terraform AWS | SKELETON | `infra/terraform/modules/apex/main.tf` declares VPC/RDS/EKS/S3/KMS. All 6 sub-modules MISSING. |
| 75 | Monitoring -- Prometheus + Grafana | EXISTS | prometheus.yml, 10 alert rules, Grafana dashboard JSON, synthetic monitoring script |
| 76 | React frontend -- SignX-Studio PWA | NOT STARTED | Architecture plan calls for Next.js + React Flow + Tailwind. `ui/` has Vite scaffolding with no source files. |
| 77 | signx_platform/api/main.py entrypoint | FIXED | Was DEAD (IndentationError). Now imports correctly. FastAPI app with CORS, health, module listing. |

### Track 9: External Tool Integrations

| # | Feature | Status | Details |
|---|---------|--------|---------|
| 78 | KeyedIn ERP | PARTIAL | 333 endpoints mapped, MCP server exists at EAGLE605/keyedin-mcp. Browser automation scripts in `Keyedin/`. 14 endpoints need VPN testing. |
| 79 | Accutrack v3.8.1 | REFERENCE ONLY | Legacy ABC pricing software at `Eagle Data/BOT TRAINING/Estimating/ABC ESTIMATING FILE/`. SignX-Takeoff supersedes it with warehouse benchmarking and margin analysis. May contain rates for Sections 1/6-9 not yet digitized. |
| 80 | Principal Sloan / EZLayout | RESEARCH DONE | LED layout tool research in docs/research/ |
| 81 | Glantz Sign Supply Wizard | RESEARCH DONE | Supply quoting tool research |
| 82 | Google Maps API -- site satellite view | TODO | Architecture plan calls for map view in SignX-Studio |
| 83 | USGS seismic data | TODO | API integration for seismic parameters by lat/lon. DB migration 013 created. |
| 84 | Geocoding for wind speed lookup | TODO | Location -> lat/lon -> basic wind speed V |

### Track 10: Knowledge & Training

| # | Feature | Status | Details |
|---|---------|--------|---------|
| 85 | ABC Pricing Guide 1974 | DIGITIZED | `abc-labor-rates-complete.md` (342 formulas, Sections 2/3F/4/5/10). Original XLSX has 5,738 lines -- Sections 1/6-9 not yet extracted. |
| 86 | AISC shapes database | DONE | 2,299 sections in `data/standards/aisc_shapes.json` |
| 87 | ASCE 7-22 tables | DONE | `data/standards/asce7_22_wind.json` |
| 88 | Foundation methods | DONE | `data/standards/foundation_methods.json` |
| 89 | Eagle work code reference | DONE | 51 codes embedded in abc_engine.py, also in `Work Codes and Pricing.csv` (64 codes) |
| 90 | ConstructIQ training data | EXISTS | 81 files but mostly 13-line YouTube transcript placeholders. Low value. |
| 91 | Accutrack MDB database | EXISTS | `data/abc-estimating/abcsignc.mdb` (2.5 MB). Original Access DB, not programmatically accessed. |
| 92 | 95-year project archive | TODO | RAG indexing of historical projects. Gemini File Search integration exists in modules/rag/ but _parse_projects is a stub. |
| 93 | Gemini RAG module | EXISTS | `modules/rag/__init__.py` makes real Gemini API calls. Needs GEMINI_API_KEY. Citation extraction is stub. |

---

## Known Bugs & Blockers

### Fixed This Session (Phase 1A)

| ID | Bug | Resolution |
|----|-----|------------|
| P0 | `platform/` shadows Python stdlib `platform` module | Renamed to `signx_platform/` |
| P1 | Missing logger init in 5 modules | Added `import logging; logger = logging.getLogger(__name__)` |
| P2 | Pydantic v2 `model_config` reserved name collision | Renamed field to `model_configuration` in 5 files |
| P3 | `signx_platform/api/main.py` IndentationError | Moved imports to top, fixed uvicorn.run indentation |
| P4 | `ml/cost_model.py` duplicate inline imports | Removed duplicates |
| P5 | signs-service missing `__init__.py` files | Created in 4 directories |
| P7 | agent_eval undefined `INBOX_DIR` | Added `INBOX_DIR = QUEUE_DIR / "eval" / "inbox"` |

### Still Open

| ID | Bug | Impact | Effort |
|----|-----|--------|--------|
| -- | `anchors_baseplate.py` returns hardcoded values | Non-functional anchor design | 4-8 hours |
| -- | `supports_pipe.py` simple bending only | No LTB, shear, or combined stress checks | 4-8 hours |
| -- | `supports_tube.py` / `supports_wshape.py` need new AISC 360 | Same as pipe support | 2-4 hours each |
| -- | `agent_signs` is placeholder | Hardcoded response, does not wire to signs-service | 2 hours |
| -- | `modules/documents` referenced but missing | Platform module registration fails for documents | 1 hour |
| -- | `signx_platform/events.py` _store_event is TODO | No DB persistence for events | 2 hours |
| -- | ESC index false positives | Year patterns in quote_number create false matches | 1 hour |
| -- | SignX-Takeoff PDF auto-scale unreliable | known_letter_height picks up borders on conceptuals, not letters | Known limitation -- use SF=2.75 |
| -- | k8s templates missing | Helm chart exists but no deployment/service/ingress templates | Days |
| -- | Terraform sub-modules missing | 6 referenced AWS modules don't exist | Days |

---

## Systematic Estimation Errors (Warehouse Evidence)

These errors apply to EVERY estimate Eagle produces. Fixing them has the highest dollar-for-dollar ROI.

### Universal Problems (Every Sign Type)

| Problem | Evidence | Annual Impact |
|---------|----------|---------------|
| Installation always underestimated | +5h to +14h variance across all types | $325K+ per year |
| Overtime never estimated | Codes 9200/9600 always est=0.00, appear in 30-80% of jobs | $325K leaked |
| Travel underestimated | Code 0620 variance +0.88 to +1.43h | $50K+ annually |

### Type-Specific Critical Gaps

| Type | Code | Problem | Hours Lost per Job |
|------|------|---------|--------------------|
| CLLIT | 0270 Misc Fab | +56.88h average variance | Investigate -- likely catch-all code |
| AWNNON | 0630 Install | +13.98h average variance | Awning installs massively undercosted |
| POLLIT | 0215 Structural | +11.03h average variance | Large structural fab underestimated |
| MONSF | 9200 Fab OT | +8.71h (never estimated) | 81% of MONSF jobs have fab overtime |
| MONDF | 0270 Misc Fab | +7.23h average variance | Monument misc fab consistently short |

### Total Estimated Margin Leak: >$1.2M

At $65/hr blended rate:
- CLLIT misc fab: 228 jobs x 56.88h x $65 = **$843K** (investigate 0270 anomaly first)
- Universal OT: ~1,000 jobs x 5h x $65 = **$325K**
- POLLIT structural: 94 jobs x 11.03h x $65 = **$67K**
- AWNNON install: 44 jobs x 13.98h x $65 = **$40K**

---

## Margin Framework (Architectural Constraint)

This framework governs ALL estimation decisions. Non-negotiable.

| Layer | Source | Purpose | Rule |
|-------|--------|---------|------|
| ABC Rates | 1974 ABC Pricing Guide | PRICING ENGINE -- what customer pays | Always use when available |
| Warehouse Actuals | eagle_warehouse.db (12,189 jobs) | BENCHMARK -- what it actually costs Eagle | Compare, never replace ABC |
| Delta | ABC rate - Warehouse actual | MARGIN INDICATOR | Positive = profit. Negative = margin leak. |

### Decision Rules

| Scenario | Action |
|----------|--------|
| ABC rate exists AND ABC > warehouse actual | KEEP ABC -- the delta is profit margin |
| ABC rate exists AND ABC < warehouse actual | FLAG as MARGIN LEAK -- investigate |
| ABC rate missing (no section) | Use warehouse P50 + 20% buffer, mark `[PROVISIONAL]` |
| Warehouse data sparse (<10 jobs) | Use warehouse mean + 30% buffer, mark `[LOW CONFIDENCE]` |
| No ABC AND no warehouse data | DO NOT ESTIMATE -- flag for manual pricing |

---

## Recommended Execution Order (What to build next)

### Sprint A (Immediate -- this week)

| Priority | Task | ROI Justification |
|----------|------|-------------------|
| A1 | Dashboard HTML with all sections | Visibility into entire system -- Brady needs a single pane of glass |
| A2 | Test all API endpoints | Verify what works before building more |
| A3 | Commit + push to GitHub | Preserve all session work safely |

### Sprint B (High ROI -- next week)

| Priority | Task | ROI Justification |
|----------|------|-------------------|
| B1 | Pylon/pole estimator (POLLIT) | 461 jobs -- highest volume after channel letters. $67K margin leak identified. |
| B2 | Cabinet estimator (ALULIT/ALUNON) | ABC Section 2 rates already digitized. Low warehouse confidence -- use MONDF patterns. |
| B3 | Extrusion estimator (work code 0220) | Bimodal distribution -- needs segment detection for structural vs cosmetic extrusion. |
| B4 | Installation recalibration using warehouse P50 | Fixes 5-14h underestimate across ALL sign types. Immediate dollar impact. |
| B5 | Overtime buffer (automatic 15% OT) | 30-80% of jobs have OT, never estimated. Low effort, high impact. |

### Sprint C (Revenue impact)

| Priority | Task | ROI Justification |
|----------|------|-------------------|
| C1 | Power Automate bid intake flow | Brady builds manually from PA guide. Automates email -> Notion. |
| C2 | Per-letter customer pricing output | Industry-standard customer-facing format ($150-$550/letter) |
| C3 | Dynamic margin manager | Client tier, complexity, material/labor markup rules |
| C4 | Proposal PDF generator | Professional output for customer presentation |

### Sprint D (Engineering completeness)

| Priority | Task | ROI Justification |
|----------|------|-------------------|
| D1 | Anchor/baseplate design -- ACI 318-19 Ch 17 | Required for PE-stampable output. Currently returns hardcoded values. |
| D2 | Member selection -- AISC 360-22 full checks | LTB, shear, combined stress, deflection. Currently simple bending only. |
| D3 | DXF/CAD export for foundations | API exists, needs front-end trigger and verification |
| D4 | Seismic analysis | USGS integration for seismic parameters |
| D5 | Combined stress + spread footing | Rounds out structural engineering capabilities |

### Sprint E (Intelligence)

| Priority | Task | ROI Justification |
|----------|------|-------------------|
| E1 | Train XGBoost cost model on warehouse data | 14 tests exist, model code exists, just needs training pipeline run |
| E2 | Sign type auto-classifier | Route incoming bids to correct estimator automatically |
| E3 | CNC discount factor calibration | Needs shop floor study. 30-50% fab reduction potential. |
| E4 | Enhanced PDF parsing | Auto-extract sign type and dimensions from bid PDFs |

### Sprint F (LED & Electrical)

| Priority | Task | ROI Justification |
|----------|------|-------------------|
| F1 | LED Wizard clone -- PowerFlow engine | Auto-populate module layouts by letter size |
| F2 | Voltage drop calculator | Wire run -> voltage drop -> minimum gauge |
| F3 | Wire gauge selector | NEC ampacity tables with derating |

### Sprint G (Platform)

| Priority | Task | ROI Justification |
|----------|------|-------------------|
| G1 | React PWA frontend (SignX-Studio) | Customer-facing portal for self-service quotes |
| G2 | Docker compose full stack validation | Verify all 12 services start and communicate |
| G3 | KeyedIn auto-entry | Automate quote entry from SignX estimates |
| G4 | Kubernetes deployment | Production deployment infrastructure |

### Sprint H (Future)

| Priority | Task | ROI Justification |
|----------|------|-------------------|
| H1 | Shop floor job board | Zero-click manufacturing status |
| H2 | Install crew PWA | Offline-capable field app |
| H3 | AR preview | Hold phone to see sign placement |
| H4 | Smart dispatch | AI crew routing |

---

## GitHub Repos

| Repo | Purpose | Status |
|------|---------|--------|
| `EAGLE605/SignX` | Main monorepo (this repo) | Active |
| `EAGLE605/signx-warehouse` | KeyedIn data extraction + DuckDB warehouse | Active |
| `EAGLE605/calcusignY` | Structural engineering playground (predecessor) | Archive |
| `EAGLE605/SignEngineeringCalc` | Earlier structural calc attempt | Archive |
| `EAGLE605/keyedin-mcp` | KeyedIn ERP MCP server | Active |

---

## Key Data Assets

| Asset | Location | Size | Records |
|-------|----------|------|---------|
| Warehouse CSVs (7 merged) | `C:\Scripts\signx-warehouse\warehouse\raw\csv_exports\*_ALL.csv` | 542 MB | 1.56M rows |
| Enriched CSVs (5) | `C:\Scripts\signx-warehouse\warehouse\raw\csv_exports\*_enriched.csv` | 70.2 MB | 571K rows |
| SO Contracts | `C:\Scripts\signx-warehouse\warehouse\raw\so_contracts_parsed.csv` | 18 MB | 25,400 rows |
| Eagle Warehouse DB | `signx-warehouse/warehouse/production/eagle_warehouse.db` | 211 MB | 12,189 jobs, 54K labor records |
| AISC Shapes | `data/standards/aisc_shapes.json` | 1,133 KB | 2,299 sections |
| ABC Formulas | `abc-labor-rates-complete.md` | -- | 342 formulas |
| Work Codes | `abc_engine.py` (embedded) | -- | 51 codes |
| ESC File Index | `C:\Scripts\signx-warehouse\esc_file_index.csv` | 4.8 MB | 40,611 files |
| Accutrack MDB | `data/abc-estimating/abcsignc.mdb` | 2.5 MB | Unknown tables |
| ABC Pricing Guide | `ABC PRICING GUIDE 1974.xlsx` | -- | 5,738 lines |
| Ref Tables (33) | `C:\Scripts\signx-warehouse\warehouse\raw\ref_tables\*.json` | 1.2 MB | 968 rows |
| ABC Pricing Guide JSON | `C:\Scripts\keyedin-capture\reports\ABC_PRICING_GUIDE_2026_v2.json` | 148 KB | All sign types with dept breakdowns |

---

## Warehouse Data Coverage by Sign Type

### Strong Data (>100 labor-bearing jobs)

| Type | Jobs | Confidence | ABC Coverage |
|------|------|------------|--------------|
| POLLIT | 461 | HIGH | Sections 2, 5, 10 (cabinet/install) |
| CLLIT | 442 | HIGH | Sections 4, 5, 10B (primary path) |
| MONDF | 188 | HIGH | Sections 2, 5, 10 (cabinet components) |
| DIRECT | 162 | HIGH | No ABC section -- `[PROVISIONAL]` |
| GEMINI | 115 | MODERATE | No ABC section -- `[PROVISIONAL]` |

### Weak Data (<50 labor-bearing jobs)

| Type | Jobs | Confidence | Recommendation |
|------|------|------------|----------------|
| LED | 53 | LOW | Install-focused, use warehouse data |
| AWNNON | 48 | LOW | Use warehouse P50 + 20% buffer |
| MONSF | 43 | LOW | Cross-reference with MONDF patterns |
| ALULIT | 31 | VERY LOW | Group with MONDF + 30% buffer |
| ALUNON | 13 | INSUFFICIENT | Group with MONDF + 30% buffer |

### No Warehouse Labor Data

FORMED, STLLIT, AWNILL, AWNREC, POLNON, BLDNON -- manual pricing only.

---

## Triage Summary (from 2026-02-16 4-agent probe)

| Verdict | Count | Percentage |
|---------|-------|------------|
| ALIVE (real logic, imports OK) | 19 | 59% |
| DORMANT (real logic, import-blocked) | 7 | 22% |
| DEAD (stubs, missing, syntax errors) | 6 | 19% |
| **Total components** | **32** | |

After Phase 1A import fixes: **15 previously blocked components are now unblocked.**

### What is the real product (by business value):

1. `signx-takeoff/` -- Working estimation server (ALIVE, production-ready)
2. `svcs/` agent framework -- 8 working agents + orchestrator (ALIVE, needs integration testing)
3. `services/signcalc-service/` -- Structural engineering engine (ALIVE once Phase 2 complete)
4. `services/materials-service/` -- Material selection (ALIVE, model_config fixed)
5. `services/ml/` -- ML pipeline with 14 tests (ALIVE, needs training data)

### What is aspirational:

- `modules/` -- Mostly stubs/mocks (quoting has partial logic, rag has real Gemini calls)
- `k8s/terraform` -- Skeleton configs, not deployable
- SignX-Studio PWA -- No source files written yet
- Shop floor / field services -- No code exists

---

## Test Coverage

| Area | Test Files | Test Functions | Framework |
|------|-----------|----------------|-----------|
| signx-takeoff | 3 | 11 | Custom runner (not pytest) |
| signcalc-service | 1 | 3 | pytest-asyncio |
| services/ml | 3 | 14 | pytest |
| Everything else | 0 | 0 | N/A |
| **Total** | **7** | **28** | Mixed |

---

## Standards Referenced

| Standard | Version | Used In |
|----------|---------|---------|
| ASCE 7 | 2022 | Wind loads (Ch 26, 29.3) |
| AISC 360 | 2022 | Steel member design |
| AISC Manual | 16th Ed | Shapes database (2,299 sections) |
| AISC DG1 | 2nd Ed | Base plate design (TODO) |
| ACI 318 | 2019 | Anchor design Ch 17 (TODO), rebar |
| IBC | 2021/2024 | Foundations (1807.3.1), load combos |
| UL 48 | Current | Electric sign safety |
| NEC 600 | Current | Electric sign installations |
| UL 879 / UL 969 | Current | Sign label requirements |
| OSHA 1910.145 | Current | Safety sign specifications |
| MUTCD | 11th Ed | Traffic sign compliance |
| ANSI Y14.5 | Current | Dimensioning and tolerancing (DXF) |
| AIA CAD Layer Guidelines | 2nd Ed | DXF layer naming |
| Broms | 1964 | Lateral resistance of piles |
| Brinch Hansen | 1961 | Rigid pile analysis |
| Czerniak | 1957 | Sign-specific foundations |

---

## Key Assumptions (track and validate)

| Assumption | Status | Evidence |
|------------|--------|----------|
| ABC Section 4B rates are current Eagle standards | ASSUMED | Sourced from abc-labor-rates-complete.md, not validated against recent actual jobs |
| `labor_cost / $40` gives reasonable hour estimates | ASSUMED | Implied rate $40/hr. Variance 40-54% vs ABC estimates. |
| Warehouse `billing` column = actual invoiced revenue | ASSUMED | Used for GM% calculation. `quoted_price` exists but is less reliable. |
| Work codes 0640/0650 = CREW-hours (not man-hours) | VERIFIED | Critical for KeyedIn entry -- multiply by crew size for total man-hours |
| PyMuPDF `qu` items are Quad objects (4 corners) | VERIFIED | Not quadratic beziers as initially assumed |
| Gemini Art PDFs have 1:1 scale pages | VERIFIED | e.g. 94"x22" page size, no scaling needed |
| Conceptual PDFs need SF=2.75 for PF extraction | VERIFIED | Letter-size paper, auto-detection unreliable on borders |
| Haiku wraps JSON in markdown fences | VERIFIED | Must strip in Power Automate flow |

---

## Duplicate Data Locations

| Data | Locations | Canonical |
|------|-----------|-----------|
| Warehouse raw data | `C:\Scripts\signx-warehouse\` (1.3GB), `C:\Scripts\SignX\Keyedin\warehouse\` (330MB), `C:\Scripts\merge-staging\` (331MB) | `C:\Scripts\signx-warehouse\` |
| ABC .mdb database | `data/abc-estimating/abcsignc.mdb`, `data/legacy-databases/abcsignc.mdb` | `data/abc-estimating/` |
| SIGNX repo | `C:\Users\Brady.EAGLE\Desktop\SIGNX\` (GitHub clone), `C:\Scripts\SignX\` (5.3GB local) | Desktop is clean GitHub clone. `C:\Scripts\SignX\` has more local data. |

---

## CNC Impact on 1974 ABC Rates

The ABC rates were written for hand fabrication. Modern CNC reduces fabrication labor significantly but does NOT affect installation, painting, electrical, or vinyl work.

| Operation | 1974 Method | 2024 Method | Labor Reduction |
|-----------|-------------|-------------|----------------|
| Letter cutting | Hand shears/brake | CNC router/plasma | 30-50% |
| Cabinet fabrication | Manual layout + cut | CNC router + bend | 30-40% |
| Routing/engraving | Manual router | CNC router | 40-60% |
| Installation | Crane + crew | Crane + crew | ~0% (unchanged) |
| Painting | Spray booth | Spray booth | ~0% (unchanged) |

**Apply CNC discount to:** 0210, 0215, 0220, 0230, 0235, 0240, 0270
**Do NOT apply to:** 0410 (paint), 0310/0320 (electrical), 0430 (vinyl), 0630/0640/0650 (install), 0620 (travel)

---

## Session History

| Session | Date | Work | Key Results |
|---------|------|------|-------------|
| T1 | 2026-02 | MVI CSV extraction | 7 merged CSVs, 1.56M rows, --resume flag |
| T1 cont. | 2026-02 | CSV enrichment | 5 enriched files with ref table lookups |
| T2 | 2026-02 | SignX-Takeoff validation | 16/20 pass, PDF parser fixed, part numbers verified |
| T3 | 2026-02 | PA build guide | 7-step flow, 3 HTTP body files, markdown fence cleanup |
| T4 | 2026-02 | Monday estimation briefs | Mercy UC, St. Anthony EMC, Ankeny Parks |
| T5 | 2026-02-15 | Warehouse + unified abc_engine | Monument/awning/removal estimators, warehouse corrections |
| T6 | 2026-02-16 | Triage + gap analysis | 32-component audit, >$1.2M margin leak, margin framework |
| T7 | 2026-02-17 | Import fixes + structural rewrite | Phase 1A complete (7 fixes), Phase 2 at 60% (wind/foundation/sections rewritten) |
| T8 | 2026-02-17 | Dashboard + API testing + master sequence | This session |

---

*This document is the single source of truth for the SIGNX project at Eagle Sign Co. Update it when significant work is completed or plans change.*
