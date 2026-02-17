# SIGNX Monorepo Triage Report

**Date:** 2026-02-16
**Method:** 4-agent parallel read-only probe + infra audit
**Scope:** signx-takeoff/, platform/, modules/, services/, svcs/, infra/

---

## Executive Summary

| Verdict | Count | What's There |
|---------|-------|--------------|
| **ALIVE** | 19 | signx-takeoff (4), platform core (2), signcalc-service, materials-service, signs-service, translator-service, ml/ (5 modules), svcs agents (6), common (2) |
| **DORMANT** | 7 | 5 modules (import bugs), agent_eval (INBOX_DIR bug), agent_signs (placeholder) |
| **DEAD** | 6 | platform/api/main.py (syntax), modules/documents (missing), ml/cost_model (indent), k8s templates (missing), terraform sub-modules (missing) |

**Critical finding:** The initial import-failure pass made the repo look 46% dead. Deep code review reveals **most components have real, substantial logic** — they're blocked by 3 fixable systemic bugs, not by being stubs.

**3 systemic root causes blocking imports:**
1. `platform/` directory shadows Python's `platform` stdlib module
2. Missing `logger` initialization in `modules/*`
3. Pydantic v2 `model_config` reserved name collision

---

## 1. signx-takeoff/ — ALIVE (Crown Jewel)

The most production-ready subsystem. Real domain logic, real data, working API.

| Component | Import | Tests | Real Logic | Dependencies | Verdict |
|-----------|--------|-------|------------|--------------|---------|
| `abc_engine.py` (1864 lines) | YES | 7+4 tests (custom runner) | **DEEP** — 4 estimators (channel letters, monument, removal, awning), 51 work codes, correction factors from 954-job warehouse, LED sizing, material BOM with real Eagle part numbers, MAD outlier detection | stdlib only; duckdb/numpy/pandas lazy | **ALIVE** |
| `app.py` (226 lines) | YES | Indirect via smoke | YES — 3 FastAPI endpoints: `/api/extract-pf` (PDF upload), `/api/footage-chart`, `/api/estimate` (full estimation + benchmark) | fastapi, uvicorn, abc_engine | **ALIVE** |
| `extract_pf_from_pdf.py` (371 lines) | YES | test_validation, test_gemini_art | YES — PDF vector path walker (bezier curves, polygons), Shoelace area, auto-scale detection | PyMuPDF (fitz) | **ALIVE** |
| `warehouse.py` (177 lines) | YES | test_warehouse_quality | YES — 25,400-row CSV loader, channel letter filter, labor derivation, confidence scoring, nearest-match | stdlib (csv, statistics) | **ALIVE** |
| `static/index.html` (696 lines) | N/A | None | YES — Complete dark-themed SPA: PDF drag-drop, footage chart, tabbed UI, BOM display, CSV export | Vanilla JS | **ALIVE** |

**Known bug:** `estimate_removal()` line 1655 references undefined `MONDF_OT_INSTALL_FACTOR` — would crash at runtime for removal jobs with OT.

**External data deps:** DuckDB at `C:\Scripts\signx-warehouse\warehouse\signx.duckdb`, CSV at same path, test PDFs on `G:\` drive.

**Tests:** Custom runner (`if __name__ == "__main__"`), not pytest. 11 test functions across 3 files.

---

## 2. platform/ — ALIVE core, DEAD entrypoint

| Component | Import | Tests | Real Logic | Dependencies | Verdict |
|-----------|--------|-------|------------|--------------|---------|
| `registry.py` | YES | 0 | YES — `ModuleRegistry` with register/get/list, event-subscriber discovery, Pydantic `ModuleDefinition`, global singleton | fastapi, pydantic | **ALIVE** |
| `events.py` | YES | 0 | YES — `EventBus` pub/sub with wildcard patterns, in-memory history (1000 events), async handler dispatch. `_store_event` is TODO (no DB persistence) | asyncio, pydantic | **ALIVE** |
| `api/main.py` | **NO — IndentationError L186** | 0 | YES — FastAPI app with CORS, health, module listing, event endpoints, `register_modules()` startup. But `logger` used at L135 before `import logging` at L183, and `uvicorn.run()` wrongly indented | fastapi, uvicorn | **DEAD** |

**CRITICAL ISSUE:** `platform/` directory name shadows Python's stdlib `platform` module. Locally it works (local package priority), but any downstream code doing `import platform; platform.system()` gets this directory instead.

---

## 3. modules/ — ALL DORMANT (real logic, broken imports)

| Component | Import | Tests | Real Logic | Dependencies | Verdict |
|-----------|--------|-------|------------|--------------|---------|
| `engineering` | NO — `NameError: logger` | 0 | STUB — Module def + 1 `/status` endpoint returning hardcoded dict. Event handlers are TODOs. | platform.registry/events | **DORMANT** |
| `intelligence` | NO — `NameError: logger` | 0 | STUB — 3 endpoints returning **hardcoded mock data** (predicted_cost=12500, total_hours=24.5). "TODO: Import actual CostPredictor" | platform.registry/events | **DORMANT** |
| `quoting` | NO — `NameError: logger` | 0 | PARTIAL — `QuoteService` with real orchestration (`asyncio.gather`), dimension parser (regex), base cost lookup, timeline estimation, structural feasibility heuristics. Sub-methods are simplified stubs. | platform.registry/events, modules.rag | **DORMANT** |
| `workflow` | NO — `NameError: logger` | 0 | STUB — 3 endpoints (status, trigger email, activity). Publishes hardcoded simulated event. "TODO: Implement actual email monitoring" | platform.registry/events | **DORMANT** |
| `rag` | NO — `platform` shadowing | 0 | PARTIAL — `RAGService` with 4 methods making real Gemini API calls via `genai.generate_content()`. `_parse_projects` and `_extract_citations` are stubs. Needs `GEMINI_API_KEY`. | google-generativeai, platform | **DORMANT** |
| `documents` | **MISSING** | 0 | N/A — Referenced in `platform/api/main.py:158` but directory does not exist | N/A | **DEAD** |

---

## 4. services/ — MOSTLY ALIVE (substantial logic, import-blocked)

Code review reveals these are **not stubs** — they have real engineering logic.

| Component | Import Barrier | Tests | Real Logic | Dependencies | Verdict |
|-----------|---------------|-------|------------|--------------|---------|
| **signcalc-service** | `platform` shadowing | 3 async tests + fixtures | **DEEP** — Full structural design: ASCE7+EN1991 wind loads, pipe/W/tube member selection, embedded foundation, anchor/baseplate, rebar schedules, report render (JSON/PDF/DXF). Has Dockerfile, YAML standards packs. ~200+ lines + 10 submodules | fastapi, yaml, YAML packs | **ALIVE** (blocked) |
| **materials-service** | Pydantic `model_config` | 0 | **YES** — Weighted multi-criteria material selection, min-max normalization, qualitative scoring (corrosion grades), confidence calibration, trace hashing, git metadata. Full `/pick` endpoint with unit conversion. 335 lines | fastapi, pydantic | **ALIVE** (blocked) |
| **signs-service** | Relative import error | 0 | **YES** — NAICS 339950 scope, UL 48/NEC 600/UL 879/UL 969/MUTCD/OSHA 1910.145 compliance, electrical listing, NEC disconnect/GFCI/bonding, UL 969 label set, BOM seeding, FreeCAD macro gen. 185 lines + 5 rule modules | fastapi, contracts.signs | **ALIVE** (blocked) |
| **translator-service** | Pydantic `model_config` | 0 | YES — Thin HTTP wrapper around agent_translator. `/healthz`, `/refresh`, `/ask` endpoints | fastapi, svcs.agent_translator | **ALIVE** (blocked) |
| **ml/cost_model** | IndentationError L186-188 | 6 tests | **YES** — GPU-accelerated XGBoost cost predictor, feature engineering (aspect ratio, slenderness, wind pressure proxy), Monte Carlo uncertainty, model persistence | xgboost, sklearn, pandas | **ALIVE** (blocked) |
| **ml/pdf_extractor** | `platform` shadowing | 6 tests | **YES** — Eagle Sign Company cost summary PDF extraction | pdfplumber | **ALIVE** (blocked) |
| **ml/data_validator** | `platform` shadowing | 0 | YES — Pydantic data schema with 40+ fields | pydantic | **ALIVE** (blocked) |
| **ml/structure_graph** | Needs torch_geometric | 2 tests | **YES** — PyTorch Geometric GNN for pole stress prediction | torch, torch_geometric | **ALIVE** (blocked) |
| **ml/experiment_tracker** | Needs mlflow | 0 | YES — MLflow experiment tracking | mlflow | **ALIVE** (blocked) |

**ML test coverage:** 14 tests across 3 test files (cost_model: 6, pdf_extractor: 6, structure_graph: 2).

---

## 5. svcs/ (Agent Framework) — MOSTLY ALIVE

All 9 agents follow an identical, well-designed architecture: FSQueue polling -> claim -> process -> validate_and_wrap envelope -> write_json_atomic -> append_processed -> append_event -> release. **Entirely file-based** — no database or external API deps. Deliberate design for determinism and auditability.

| Component | Import | Tests | Real Logic | Dependencies | Verdict |
|-----------|--------|-------|------------|--------------|---------|
| **orchestrator** (~300 lines) | YES | 0 | **YES** — Central coordinator: JSON schema export, task enqueueing, report synthesis, comprehensive verification gates (SHA256 integrity, blob existence, trace ID format, monotonic event ordering, duplicate detection, .tmp sentinel). Watchdog, SLA defs, metrics. CLI: --bootstrap, --report, --verify | All 8 contracts, pydantic | **ALIVE** |
| **agent_cad** (~140 lines) | YES | 0 | YES — FreeCAD script generation from CADMacroRequest. Pad/pocket/fillet primitives. Content-addressed blob storage | contracts.cad, FSQueue | **ALIVE** |
| **agent_compliance** (~190 lines) | YES | 0 | YES — IP similarity via trigram overlap against patent CSV, safety factor validation, ASME Y14.5 standards tagging, checksum signing, severity classification | contracts.compliance, FSQueue | **ALIVE** |
| **agent_dfma** (~175 lines) | YES | 0 | YES — DFM rule evaluation: sheet_metal (bend radius, hole-to-edge), machining (slot depth ratio), 3D printing (wall thickness). Cost model with material/process/setup/penalty. Loads JSON rule files | contracts.dfma, FSQueue, JSON rules | **ALIVE** |
| **agent_materials** (~255 lines) | YES | 0 | YES — Material selection with CSV data (fallback: 6061-T6, 7075-T6, 304SS, 316L, Ti-6Al-4V). Min-max normalization, weighted scoring, confidence heuristic | contracts.materials, FSQueue, CSV | **ALIVE** |
| **agent_parts** (~190 lines) | YES | 0 | YES — Parts catalog search, hard/soft constraint matching, fuzzy token matching, price tie-breaking, Top-5 ranking | contracts.parts, FSQueue, CSV | **ALIVE** |
| **agent_stackup** (~190 lines) | YES | 0 | YES — Monte Carlo tolerance stackup: worst-case + RSS, normal/uniform distributions (50K samples), Cp/Cpk capability indices, histogram bucketing | contracts.stackup, numpy, FSQueue | **ALIVE** |
| **agent_translator** (~285 lines) | YES | 0 | YES — Repo indexer: scans FastAPI routes, Pydantic models, compose services, agents, TODOs. Keyword-based Q&A engine. Caches index at `artifacts/translator/latest.json` | contracts.translator, pydantic, subprocess | **ALIVE** |
| **agent_eval** (~140 lines) | YES | 0 | YES — Integration test harness: synthesizes eval tasks, enqueues, waits with timeout, computes metrics, generates markdown report. **BUG: `INBOX_DIR` undefined at L123** | contracts.eval, FSQueue | **DORMANT** |
| **agent_signs** (~115 lines) | YES | 0 | MINIMAL — Placeholder. Hardcoded SignResponse (5052-H32 Al, powdercoat). Comment: "main logic resides in signs-service" | contracts.signs, FSQueue | **DORMANT** |
| **common/fsqueue** (~80 lines) | YES | 0 | YES — Cross-platform filesystem queue with atomic O_CREAT\|O_EXCL lockfile. poll/claim/complete/release lifecycle | stdlib only | **ALIVE** |
| **common/index** (~70 lines) | YES | 0 | YES — Idempotent NDJSON processed-record index. Atomic append with temp staging + fsync | stdlib only | **ALIVE** |

---

## 6. Infrastructure — DORMANT (well-designed, disconnected)

### Docker Compose (3 files)

| File | Services | Wired to Code? | Verdict |
|------|----------|----------------|---------|
| `docker-compose.yml` (root) | 1: postgres:16-alpine | DB only | **DORMANT** |
| `docker-compose.prod.yml` (root) | 3: pgvector:pg16, Redis 7, FastAPI API | YES — builds `./services/api`, security hardened (no-new-privileges, resource limits, healthchecks) | **DORMANT** (API import-blocked) |
| `infra/compose.yaml` (full dev) | 12: api, worker, signcalc, db, cache, object(MinIO), search(OpenSearch), dashboards, grafana, frontend, postgres_exporter, supabase-db | Comprehensive — references real service dirs | **DORMANT** (services import-blocked) |

### Kubernetes

| File | Status | Notes |
|------|--------|-------|
| `k8s/charts/apex/Chart.yaml` | Skeleton | Bitnami postgres+redis deps, appVersion 0.1.0 |
| `k8s/charts/apex/values-prod.yaml` | Exists | Values file |
| Templates | **MISSING** | No deployment/service/ingress templates |
| Verdict | **DEAD** | Not deployable |

### Terraform

| File | Status | Notes |
|------|--------|-------|
| `infra/terraform/modules/apex/main.tf` | Exists | Declares VPC, RDS, ElastiCache, S3, EKS, KMS (full AWS stack) |
| `infra/terraform/modules/apex/variables.tf` | Exists | Variable definitions |
| Sub-modules (vpc, rds, eks, elasticache, s3, kms) | **ALL MISSING** | 6 referenced modules don't exist |
| Verdict | **DEAD** | Top-level only |

### Monitoring

| Component | Status | Notes |
|-----------|--------|-------|
| `infra/monitoring/prometheus.yml` | Valid | Scrapes api:8000, worker:5555, postgres-exporter, redis-exporter |
| `infra/monitoring/alerts.yml` | Valid | 10 alert rules (error rate, latency, pool exhaustion, queue backlog, cache hit ratio, search fallback) |
| `infra/monitoring/grafana/dashboards/` | Dashboard JSON | apex-overview |
| `monitoring/synthetic.py` | Real logic | 4 async scenarios (health, create_project, derive_cabinet, pole_options) with webhook alerting |
| Verdict | **DORMANT** | Well-designed, targets non-running services |

### Makefile (10 targets)

| Target | Works? | Notes |
|--------|--------|-------|
| `lint` | YES | `ruff check services/api/` |
| `format` | YES | `black services/api/ services/ml/` |
| `clean` | YES | Removes __pycache__, .pyc, egg-info |
| `up/down/logs` | Needs Docker | Points to `infra/` compose |
| `test/test-ml` | Blocked | pytest on import-blocked services |
| `ml-pipeline` | Untested | extract-pdfs -> train -> test |

### Backups

Real database backups exist at `infra/backups/postgres/`:
- `apex_2025-11-01_17-33.sql`
- `apex_2025-11-01_17-34.sql`
- `supabase_2025-11-01_17-33.sql`

---

## 7. Systemic Root Causes

### Issue #1: `platform/` shadows stdlib (Impact: 4+ components)

```
SIGNX/
├── platform/          <-- This directory name
│   ├── registry.py    <-- ALIVE (ironically)
│   └── events.py      <-- ALIVE
└── services/
    └── signcalc-service/
        └── *.py       <-- `import platform` gets SIGNX/platform/ instead of stdlib
```

**Affected:** signcalc-service, ml/pdf_extractor, ml/data_validator, modules/rag
**Fix:** Rename `platform/` to `signx_platform/` or `core/`. Update all imports.

### Issue #2: Missing logger initialization (Impact: 4 modules)

All modules in `modules/` reference `logger` without creating it.

**Affected:** engineering, intelligence, quoting, workflow
**Fix:** Add to each module:
```python
import logging
logger = logging.getLogger(__name__)
```

### Issue #3: Pydantic v2 `model_config` collision (Impact: 3 services + 1 agent)

Code uses `model_config` as a field name, but Pydantic v2 reserves it as a class-level `ConfigDict`.

**Affected:** materials-service, translator-service, agent_translator
**Fix:** Rename field to `configuration` or `model_settings`.

### Additional bugs found:
- `abc_engine.py:1655` — undefined `MONDF_OT_INSTALL_FACTOR` (NameError on removal jobs)
- `agent_eval/main.py:123` — undefined `INBOX_DIR` (NameError at runtime)
- `ml/cost_model.py:186-188` — duplicate inline imports breaking indentation
- `platform/api/main.py:183-186` — `import logging` after `if __name__` block, IndentationError

---

## 8. Prioritized Fix Plan

| Priority | Fix | Components Unblocked | Effort |
|----------|-----|---------------------|--------|
| **P0** | Rename `platform/` -> `signx_platform/` | signcalc-service, ml/pdf_extractor, ml/data_validator, modules/rag | 30 min |
| **P1** | Add logger init to 4 modules | modules/engineering, intelligence, quoting, workflow | 15 min |
| **P2** | Rename `model_config` field | materials-service, translator-service, agent_translator | 30 min |
| **P3** | Fix `platform/api/main.py` indent + logger order | platform entrypoint | 10 min |
| **P4** | Fix `ml/cost_model.py` indent error | services/ml/cost_model | 5 min |
| **P5** | Fix signs-service relative imports | services/signs-service | 15 min |
| **P6** | Fix `MONDF_OT_INSTALL_FACTOR` in abc_engine | signx-takeoff removal estimator | 5 min |
| **P7** | Fix `INBOX_DIR` in agent_eval | svcs/agent_eval | 5 min |
| **P8** | Add missing `modules/documents/` | platform module registration | 30 min |
| **P9** | Write tests for svcs agents (0 tests currently) | 10 agents + orchestrator | 4-8 hrs |
| **P10** | Complete k8s templates + terraform sub-modules | Deployment pipeline | Days |

**Quick wins (P0-P7): ~2 hours to unblock 15+ components.**

---

## 9. Revised Verdict Summary

### By actual code quality (post deep review):

```
ALIVE  (19)  ███████████████████░░░░░░░░░░░░░  59%
DORMANT (7)  ███████░░░░░░░░░░░░░░░░░░░░░░░░░  22%
DEAD    (6)  ██████░░░░░░░░░░░░░░░░░░░░░░░░░░  19%

Total components assessed: 32
```

### By current import status (what actually runs today):

```
Imports OK  (17)  █████████████████░░░░░░░░░░░░░░░  53%
Blocked     (15)  ███████████████░░░░░░░░░░░░░░░░░  47%
```

### Test coverage:

| Area | Test Files | Test Functions | Framework |
|------|-----------|----------------|-----------|
| signx-takeoff | 3 | 11 | Custom runner (not pytest) |
| signcalc-service | 1 | 3 | pytest-asyncio |
| services/ml | 3 | 14 | pytest |
| **Everything else** | **0** | **0** | N/A |
| **Total** | **7** | **28** | Mixed |

---

## 10. Architecture Insights

### What's well-designed:
- **svcs agent framework** — Consistent FSQueue-based architecture across all agents. File-based for determinism. Atomic operations. Content-addressed blob storage. This is production-quality coordination infrastructure.
- **abc_engine** — 1864 lines of real domain logic with warehouse-calibrated corrections from 954-job analysis. This is the business value.
- **signcalc-service** — Full structural engineering calculations (ASCE7, EN1991) with standards YAML packs.
- **Monitoring stack** — Prometheus + Grafana + synthetic monitoring is well-thought-out.
- **Docker production config** — Security hardened with proper health checks, resource limits, no-new-privileges.

### What's aspirational:
- **modules/** — Mostly stubs/mocks. quoting has partial logic, rag has real Gemini calls, rest is scaffolding.
- **k8s/terraform** — Skeleton configs with missing sub-modules. Not deployable.
- **modules/documents** — Referenced but doesn't exist.

### What's the real product:
1. `signx-takeoff/` — Working estimation server (ALIVE today)
2. `svcs/` agent framework — 8 working agents + orchestrator (ALIVE, needs integration testing)
3. `services/signcalc-service` — Structural engineering engine (ALIVE once platform/ renamed)
4. `services/materials-service` — Material selection (ALIVE once model_config renamed)
5. `services/ml/` — ML pipeline with 14 tests (ALIVE once import issues fixed)

**Bottom line:** This repo is 59% alive by code quality. The 47% import failure rate is caused by just 3 bugs that take ~2 hours to fix. The agent framework and domain engines contain real, substantial engineering logic — not scaffolding.
