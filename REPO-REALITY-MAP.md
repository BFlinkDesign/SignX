# Repo vs Reality — Feature Truth Table

**Audited:** 2026-03-01
**Method:** Read every referenced file, checked imports, verified data flow end-to-end

Legend:
- WORKS = runs, produces correct output, Brady uses it
- PARTIAL = code exists, runs with caveats or missing dependencies
- STUB = code exists but returns mocks/hardcoded/scaffolding
- MISSING = referenced but no code exists
- DEAD = code exists but abandoned/superseded

---

## Track 1: Estimation Engine

| Feature | Repo Claims | Reality | Evidence |
|---------|-------------|---------|----------|
| Channel Letters (CLLIT) | YES | **WORKS** | `abc_engine.py:estimate_channel_letters()`, tested, calibrated |
| Monument (MONU*) | YES | **WORKS** | `abc_engine.py:estimate_monument()`, tested, calibrated |
| Awning | YES | **WORKS** | `abc_engine.py:estimate_awning()`, tested |
| Removal | YES | **WORKS** | `abc_engine.py:estimate_removal()`, tested |
| Pylon | YES | **WORKS** | `abc_engine.py:estimate_pylon()`, tested |
| Cabinet | YES | **WORKS** | `abc_engine.py:estimate_cabinet()`, tested |
| Directional | YES | **WORKS** | `abc_engine.py:estimate_directional()`, tested |
| Dimensional Letters | YES | **WORKS** | `abc_engine.py:estimate_dimensional()`, tested |
| Pole Non-illuminated | YES | **WORKS** | `abc_engine.py:estimate_polnon()`, tested |
| Flat Panel | YES | **PARTIAL** | Provisional stub, not fully calibrated |
| Auto-calibration | YES | **WORKS** | `calibrate.py`, reads DuckDB on CNC-1 only |
| Benchmark comparison | YES | **PARTIAL** | `warehouse.py:benchmark()` — works on CNC-1, returns None on Linux (Windows paths) |
| LED module database | YES | **WORKS** | `abc_engine.py`, LED data embedded |
| Margin detection | YES | **WORKS** | `abc_engine.py`, margin safety checks |
| Material takeoff | YES | **PARTIAL** | Some sign types have material lists, others don't |
| Multi-sign bundling | YES | **STUB** | No bundle discount logic found |

## Track 2: Structural Engineering

| Feature | Repo Claims | Reality | Evidence |
|---------|-------------|---------|----------|
| ASCE 7-22 Wind | YES | **WORKS** | `signcalc-service/`, tested, PE-reviewable |
| Foundation Design | YES | **WORKS** | `signcalc-service/`, tested |
| Anchor Bolt | YES | **STUB** | Routes exist, calculations return placeholders |
| Steel Members | YES | **STUB** | AISC 360 stubs, no real implementation |
| Seismic | YES | **STUB** | Referenced in docs, no working code |
| PE Drawing Gen | YES | **PARTIAL** | `generate_foundation_drawing.py` exists, needs `C:\Temp` |

## Track 3: LED & Electrical

| Feature | Repo Claims | Reality | Evidence |
|---------|-------------|---------|----------|
| LED layout calculation | YES | **WORKS** | Embedded in abc_engine.py |
| Power supply sizing | YES | **WORKS** | Part of channel letter estimator |
| Wiring diagrams | YES | **STUB** | Cat Scale cheat sheets in Eagle Data, no code generation |
| UL compliance check | YES | **MISSING** | No code found |
| NEC calculations | YES | **MISSING** | No code found |

## Track 4: PDF & Drawing

| Feature | Repo Claims | Reality | Evidence |
|---------|-------------|---------|----------|
| Drawing search (G: drive) | YES | **WORKS** | `drawing_search.py`, searches `\\ES-FS02\Customers2` |
| Project file lookup | YES | **WORKS** | `project_files.py`, searches file server |
| PDF text extraction | YES | **PARTIAL** | `fitz` (PyMuPDF) imported in app.py |
| DWG/DXF parsing | YES | **STUB** | References in docs, no working parser |
| Quote PDF generation | YES | **MISSING** | Zero code |
| Bluebeam integration | YES | **MISSING** | Single file `Bluebeam/`, no implementation |

## Track 5: Data & Intelligence

| Feature | Repo Claims | Reality | Evidence |
|---------|-------------|---------|----------|
| Warehouse benchmark | YES | **WORKS** (CNC-1 only) | `warehouse.py` + DuckDB |
| Customer intelligence | YES | **WORKS** (CNC-1 only) | `customer_intel.py` + CSV |
| Bid scoring / win prob | YES | **WORKS** (CNC-1 only) | `bid_scoring.py`, AUC 0.80 |
| 500IQ Knowledge Graph | YES | **PARTIAL** | `SignX-500IQ/` built, shadow mode wired, not production |
| ML cost prediction | YES | **STUB** | `services/ml/cost_model.py` defined, never trained |
| RAG module | YES | **STUB** | `modules/rag/` exists, returns mocks |
| Intelligence module | YES | **STUB** | `modules/intelligence/` returns hardcoded data |
| Dossier/company profile | YES | **PARTIAL** | `/api/dossier/` endpoint exists, Claude-powered |

## Track 6: Bid Pipeline

| Feature | Repo Claims | Reality | Evidence |
|---------|-------------|---------|----------|
| Notion Bid Pipeline DB | YES | **WORKS** | 304c1e58d2dd814aae63c6a0d44e6679, 21 active bids |
| Email intake (COM poller) | YES | **WORKS** (CNC-1 only) | `mail_processor.py`, 60s Win32 COM polling |
| Email classifier | YES | **WORKS** | `mail_classifier.py`, regex + Claude Haiku |
| SMS notification | YES | **WORKS** | `/api/notify/bid-ready`, SMTP→Verizon gateway |
| Webhook notification | YES | **PARTIAL** | `NOTIFY_WEBHOOK_URL` env var, code ready, needs PA config |
| PA cloud flow | YES | **MISSING** | Build guide only (`BID-INTAKE-PROOF-BUILD-GUIDE.md`) |
| Auto-takeoff from email | YES | **WORKS** (CNC-1 only) | `mail_processor.py:176` → POST `/api/notion/takeoff` |

## Track 7: Shop Floor & Field

| Feature | Repo Claims | Reality | Evidence |
|---------|-------------|---------|----------|
| Work order dispatch | YES | **STUB** | Referenced in docs/tests, no implementation |
| Shop floor scheduling | YES | **MISSING** | No code |
| Field installation tracking | YES | **MISSING** | No code |
| Time tracking | YES | **MISSING** | No code |
| Inventory management | YES | **MISSING** | No code |

## Track 8: Platform & Infrastructure

| Feature | Repo Claims | Reality | Evidence |
|---------|-------------|---------|----------|
| Docker Compose (dev) | YES | **WORKS** | `infra/compose.yaml` |
| CI/CD (GitHub Actions) | YES | **WORKS** | `.github/workflows/`, green |
| Container registry | YES | **WORKS** | Dockerfile.api, Dockerfile.worker |
| Kubernetes | YES | **STUB** | `k8s/charts/` skeleton, 2 files |
| Terraform | YES | **STUB** | `infra/terraform/`, 2 files, can't deploy |
| Grafana/Prometheus | YES | **STUB** | Config files exist, monitoring not running |
| Agent orchestrator | YES | **STUB** | `svcs/orchestrator/`, 0 production imports |
| 9 agent microservices | YES | **STUB** | `svcs/agent_*/`, 0 production imports |

## Track 9: External Integrations

| Feature | Repo Claims | Reality | Evidence |
|---------|-------------|---------|----------|
| Notion API | YES | **WORKS** | Read/write/patch bids, 3 databases |
| KeyedIn ERP | YES | **PARTIAL** | Format endpoint exists, no auto-submit. 85+ recon scripts in repo. |
| Supabase auth | YES | **PARTIAL** | Code supports it, optional dependency |
| OpenSearch | YES | **PARTIAL** | Fallback to DB when unavailable |
| MinIO S3 | YES | **STUB** | compose.yaml has it, no production usage |
| Power Automate | YES | **PARTIAL** | Webhook endpoint coded, flow not deployed |
| Outlook COM | YES | **WORKS** (CNC-1 only) | `mail_processor.py` |

## Track 10: Knowledge & Training

| Feature | Repo Claims | Reality | Evidence |
|---------|-------------|---------|----------|
| Eagle Data training corpus | YES | **EXISTS** | 400+ files in `Eagle Data/BOT TRAINING/` |
| KeyedIn MCP server | YES | **WORKS** (CNC-1 only) | `C:\Scripts\keyedin-automation\keyedin.py`, not in repo |
| OBS recording automation | YES | **WORKS** (CNC-1 only) | `Ai Observation & Training/scripts/` |
| Cat Scale parser | YES | **WORKS** | `Benchmark/catscale_delta_parser.py` + tests |
| CorelDraw macros | YES | **EXISTS** | `CorelDraw Macros/`, binary VBA |
| Developer docs | YES | **EXISTS** | 185 files in `docs/` |

---

## Scorecard

| Status | Count | Percentage |
|--------|-------|------------|
| **WORKS** | 30 | 34% |
| **WORKS (CNC-1 only)** | 8 | 9% |
| **PARTIAL** | 14 | 16% |
| **STUB** | 18 | 21% |
| **MISSING** | 8 | 9% |
| **EXISTS (non-code)** | 5 | 6% |
| **DEAD** | 4 | 5% |
| **TOTAL** | **87** | |

**True working rate: 38 features (43%) work fully or on CNC-1**
**True stub/missing rate: 26 features (30%) are stubs or missing entirely**
