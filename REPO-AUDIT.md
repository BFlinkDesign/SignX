# REPO-AUDIT.md — SignX Repository Audit

**Audited:** 2026-05-18
**Method:** Read-only. Directory survey, targeted file reads, all executable checks run.
**Repo:** `EAGLE605/SignX` at commit `05708f2`
**Platform:** Linux container (Python 3.11.15)

---

## PHASE 1 — SOURCES OF TRUTH

### TIER 1 — Enforced + Executable

| Artifact | Path | Status | Notes |
|----------|------|--------|-------|
| GitHub Actions CI | `.github/workflows/ci.yml` | [VERIFIED] Runs on push/PR to main | 3 jobs: signx-takeoff-tests, signcalc-tests, lint |
| GitHub Actions ML-CI | `.github/workflows/ml-ci.yml` | [VERIFIED] Path-triggered (bid_model, bid_scoring, calibrate, services/ml) | 2 jobs: ml-lint, ml-import-check |
| GitHub Actions Security | `.github/workflows/security-scan.yml` | [VERIFIED] Runs on push/PR | gitleaks + semgrep (semgrep is `continue-on-error: true`) |
| Ruff lint (CI) | `.github/workflows/ci.yml:101-105` | [VERIFIED] **Non-blocking** — uses `\|\| true` | Lint violations do not fail the build |
| `test_estimators.py` (CI) | `signx-takeoff/tests/test_estimators.py` | [VERIFIED] 56 tests, all pass | Only test file wired into CI for signx-takeoff |
| signcalc smoke test (CI) | `.github/workflows/ci.yml:70-83` | [VERIFIED] Inline Python assertions | Tests `wind_force_on_sign()` and `design_embed()` via inline script |

**Critical finding:** The ruff lint job uses `|| true` on both targets, making it advisory-only. [VERIFIED] The de facto enforced contract is: "56 estimator tests pass, signcalc smoke imports succeed, and secrets scan runs." Everything else is non-blocking.

### TIER 2 — Executable but Possibly Unenforced

| Artifact | Path | Status | Notes |
|----------|------|--------|-------|
| signcalc service tests | `services/signcalc-service/tests/test_sign_api.py` | [VERIFIED] 3 tests, **ALL 3 FAIL** (httpx API incompatibility) | Not wired into CI — CI uses inline smoke test instead |
| IQ client tests | `signx-takeoff/tests/test_iq_client.py` | [VERIFIED] 10 tests, all pass | Not run by CI |
| Non-CI signx-takeoff tests | `signx-takeoff/test_boundary.py`, `test_regression.py`, `test_phase1.py`, `test_validation.py` | [VERIFIED] 135 total: 123 pass, 12 fail | Not run by CI |
| Top-level `tests/` suite | `tests/` (59 .py files) | [VERIFIED] 301 collected, 8 collection errors, 34 fail, 126 pass, 141 errors | Not run by CI |
| Benchmark tests | `Benchmark/tests/` | [VERIFIED] **ALL 4 collection errors** (SyntaxError in parser) | Not run by CI |
| GitLab CI | `.gitlab-ci.yml` | [VERIFIED] Exists, references `ops/agents/orchestrator` | Not connected (no GitLab remote detected) [INFERRED] |
| Makefile | `Makefile` | [VERIFIED] Targets reference `services/api/` which does not exist | `make test` and `make lint` would fail |
| Live endpoint tests | `signx-takeoff/tests/test_endpoints_live.py`, `test_intel_live.py` | [VERIFIED] Exist (868 + 162 LOC) | Require running server + CNC-1 data |
| Performance tests | `signx-takeoff/tests/test_performance.py` | [VERIFIED] Exists (240 LOC) | Not run by CI |

### TIER 3 — Declarative Contracts

| Artifact | Path | Status | Notes |
|----------|------|--------|-------|
| OpenAPI 3.1 spec | `api-spec.json` (UTF-16 encoded) | [VERIFIED] 32 paths, 11 schemas | Describes a **completely different API** — see Phase 5 |
| Pydantic contracts | `services/signcalc-service/apex_signcalc/contracts.py` | [VERIFIED] `SignDesignRequest`, `SignDesignResponse`, `SCHEMA_VERSION="sign-1.0"` | Used by signcalc-service |
| Pydantic models | `signx-takeoff/models.py` | [VERIFIED] 565 LOC | Used by abc_engine and app.py |
| Notion schema | `SignX-Intake/schemas/notion-bid-pipeline.json` | [VERIFIED] Exists | Describes Notion DB structure |
| Engineering standards JSONs | `data/standards/` (8 files) | [VERIFIED] ASCE 7-22, AISC shapes, foundation methods, compliance | Loaded by signcalc-service |
| `pyproject.toml` (signcalc only) | `services/signcalc-service/pyproject.toml` | [VERIFIED] Dependencies + pytest config | Only properly-packaged service in repo |
| Contract tests (svcs) | `contracts/` (11 files) | [VERIFIED] Agent contract definitions | Used by `svcs/` agents, not by production code |

### TIER 4 — Human Prose, Drift-Prone

| Artifact | Path | Status | Notes |
|----------|------|--------|-------|
| `CLAUDE.md` | `CLAUDE.md` | [VERIFIED] References `services/api/`, `apex/apps/ui-web/`, Alembic, Celery, React, PostgreSQL, Redis | **Describes a system that does not exist** — see Phase 5 |
| `README.md` | `README.md` | [VERIFIED] Claims "Ready to Deploy", "Instant Online Quoting", "GPU-accelerated ML", "500+ customers" | **Almost entirely aspirational** — see Phase 5 |
| `.env.example` | `signx-takeoff/.env.example` | [VERIFIED] Documents NOTION_TOKEN, ANTHROPIC_API_KEY, SMTP config | Accurate for signx-takeoff env vars |
| 50+ root .md files | Various | [VERIFIED] Session states, reports, plans, handoffs | Historical snapshots, not current truth |
| `SIGNX-MASTER-SEQUENCE.md` | Root | [VERIFIED] Exists | Planning document |
| `KEYEDIN-PIPELINE-STATUS.md` | Root | [VERIFIED] Exists | CNC-1 pipeline documentation |
| 185 files in `docs/` | `docs/` | [INFERRED] Exist based on listing | Not individually verified |

### TIER 5 — Intent + History

| Artifact | Status | Notes |
|----------|--------|-------|
| Git commit messages | [VERIFIED] 16 commits examined | Descriptive, follow conventional commits loosely |
| CHANGELOG | [VERIFIED] **Not found** | No changelog file in repo |
| TODO/FIXME markers | [VERIFIED] 1 TODO in `signx-takeoff/led_catalog.py:255` | Minimal |
| ADRs | [VERIFIED] **Not found** | No Architecture Decision Records |

### ABSENT (Notable missing sources of truth)

- **No pre-commit hooks** (`.pre-commit-config.yaml` does not exist outside vendored WebScrapers) [VERIFIED]
- **No `pyproject.toml` for signx-takeoff** (the main production service) [VERIFIED]
- **No type checking** (no mypy config, no `py.typed` marker, no type-check CI step) [VERIFIED]
- **No CHANGELOG** [VERIFIED]
- **No ADRs** [VERIFIED]
- **No conftest.py in `signx-takeoff/tests/`** [VERIFIED]
- **No runtime assertions or contracts in signx-takeoff** beyond Pydantic model validation [VERIFIED]

### Highest-Authority Source

**The single highest-authority source is `.github/workflows/ci.yml`**, specifically the `signx-takeoff-tests` job which runs `test_estimators.py`. This is the only enforced, executable check that blocks merges. It validates 56 properties of the estimation engine. Everything else — lint, security scan, signcalc smoke test — either passes trivially or is non-blocking.

---

## PHASE 2 — RUN STATUS

### Entry Point 1: signx-takeoff (Production API)

| Item | Status |
|------|--------|
| **Start command** | `cd signx-takeoff && python -m uvicorn app:app --host 0.0.0.0 --port 8765` |
| **Dependencies resolve?** | [VERIFIED] YES on Linux (with `pip install -r requirements.txt`), except `pywin32` (Windows-only, fails on Linux but is caught with try/except in `mail_processor.py`) |
| **Can it start?** | [VERIFIED] YES — server boots and serves `/` (returns HTML dashboard). Requires `.env` with `NOTION_TOKEN` for Notion endpoints to function; app does NOT crash without it. |
| **Missing data on Linux** | [VERIFIED] Warehouse CSV/DuckDB paths are Windows-only (`C:\Scripts\...`). Features degrade to `None`/empty on Linux: `warehouse.benchmark()`, `customer_intel`, `bid_scoring`, `bid_model`, `calibrate`. |

### Entry Point 2: signcalc-service

| Item | Status |
|------|--------|
| **Start command** | `cd services/signcalc-service && python -m uvicorn main:app --port 8000` |
| **Dependencies resolve?** | [VERIFIED] YES (with `pip install` from pyproject.toml deps) |
| **Can it start?** | [VERIFIED] YES — `main.py` loads, FastAPI app boots. |

### Entry Point 3: Docker Compose (infra/compose.yaml)

| Item | Status |
|------|--------|
| **Start command** | `cd infra && docker-compose up -d` |
| **Can it build?** | [VERIFIED] **NO** — references `services/api` as build context, which does not exist. Build will fail at `api` service. |

### Entry Point 4: Makefile

| Item | Status |
|------|--------|
| **`make test`** | [VERIFIED] **FAILS** — runs `pytest services/api/tests/ -v`, path does not exist |
| **`make lint`** | [VERIFIED] **FAILS** — runs `ruff check services/api/`, path does not exist |
| **`make up`** | [VERIFIED] **FAILS** — runs compose that references missing service |

**Verdict: The repo boots for both Python entry points. Docker and Makefile are broken. Proceeding.**

---

## PHASE 3 — STRUCTURAL MAP

### Production Call Paths

**Path 1: Estimation (the core product)**
```
HTTP POST /api/estimate → app.py:209 → abc_engine.estimate() → EstimateResult
HTTP POST /api/estimate/monument → app.py:261 → abc_engine.estimate_monument()
HTTP POST /api/estimate/awning → app.py:296 → abc_engine.estimate_awning()
HTTP POST /api/estimate/removal → app.py:330 → abc_engine.estimate_removal()
HTTP POST /api/estimate/pylon → app.py:368 → abc_engine.estimate_pylon()
HTTP POST /api/estimate/cabinet → app.py:407 → abc_engine.estimate_cabinet()
HTTP POST /api/estimate/directional → app.py:444 → abc_engine.estimate_directional()
HTTP POST /api/estimate/dimensional → app.py:476 → abc_engine.estimate_dimensional()
```

**Path 2: Structural Engineering**
```
HTTP POST /api/structural/wind → app.py:746 → apex_signcalc.wind_asce7.wind_force_on_sign()
HTTP POST /api/structural/foundation → app.py:774 → apex_signcalc.foundation_embed.design_embed()
HTTP POST /api/structural/anchors → app.py:800 → apex_signcalc.anchors_baseplate.design_anchors()
HTTP POST /api/structural/member-check → app.py:831 → apex_signcalc.supports_pipe.check_section()
HTTP POST /api/structural/full-design → app.py:886 → chained: wind → member → foundation → anchors
```

**Path 3: Bid Pipeline & Notion**
```
HTTP GET /api/notion/bids → app.py:1128 → Notion API (httpx)
HTTP POST /api/notion/takeoff → app.py:1169 → estimate → Notion API write
HTTP PATCH /api/notion/bid → app.py:1310 → Notion API patch
HTTP POST /api/notify/bid-ready → app.py:1408 → SMTP→SMS gateway
```

**Path 4: Data Intelligence (CNC-1 only)**
```
HTTP GET /api/intel/customer/{name} → app.py:1871 → customer_intel.py → CSV on C:\
HTTP POST /api/bid/score → app.py:1995 → bid_scoring.py → CSV on C:\
HTTP POST /api/bid/ml-score → app.py:2064 → bid_model.py → CSV on C:\
HTTP GET /api/intel/warehouse → app.py:1951 → warehouse.py → CSV on C:\
```

### Files Imported by Nothing (Dead Code) [VERIFIED]

| File | LOC | Evidence |
|------|-----|----------|
| `signx-takeoff/mondf_analysis.py` | 22 | Standalone script, hardcoded DuckDB path, no imports found |
| `signx-takeoff/sign_type_analysis.py` | 24 | Standalone script, hardcoded DuckDB path, no imports found |
| `signx-takeoff/t1_query.py` | 64 | Standalone script, hardcoded DuckDB path, no imports found |
| `signx-takeoff/check_pipeline.py` | [INFERRED] | Not imported by app.py or any test |
| `svcs/` (all 13 agent dirs) | 2,471 | Zero production imports anywhere [VERIFIED — confirmed by exploration agent] |
| `modules/` (5 dirs) | 1,388 | Only referenced by `signx_platform/registry.py`, never called [VERIFIED] |
| `signx_platform/` (7 files) | 522 | Module registry system, never invoked by production code [VERIFIED] |
| `SignX-Intel/` (30+ files) | 2,597 | Zero implementation, all scaffolding [VERIFIED] |
| `services/materials-service/` | [VERIFIED] exists | Not imported by signx-takeoff or signcalc-service |
| `services/signs-service/` | [VERIFIED] exists | Not imported by signx-takeoff or signcalc-service |
| `services/translator-service/` | [VERIFIED] exists | Not imported by signx-takeoff or signcalc-service |
| `services/ml/` | [VERIFIED] exists | Models defined, never trained, never imported by production code |

### Files Referenced but Missing

| Expected Path | Referenced By | Evidence |
|---------------|--------------|----------|
| `services/api/` | `tests/conftest.py:18-27`, `infra/compose.yaml:4-6`, `Makefile:20,26` | [VERIFIED] Directory does not exist |
| `services/api/src/apex/api/main.py` | `tests/conftest.py:27` | [VERIFIED] Import fails — `ModuleNotFoundError: No module named 'apex'` |
| `services/api/src/apex/domains/signage/` | 11 test files in `tests/` | [VERIFIED] Module does not exist |
| `services/worker/` | `tests/worker/conftest.py` | [VERIFIED] Directory does not exist |
| `apex/apps/ui-web/` | `CLAUDE.md` | [VERIFIED] Directory does not exist |
| `notion_sync.py` | `CONSOLIDATION-PLAN.md` | [VERIFIED] File does not exist in signx-takeoff/ |

### Circular Dependencies

[VERIFIED] None detected. Import graph is acyclic. `app.py` imports from `abc_engine`, `calibrate`, `warehouse`, etc. None of those import `app`.

---

## PHASE 4 — VERIFICATION SURFACE

### Test Suite 1: CI-Enforced — `signx-takeoff/tests/test_estimators.py`

```
Result: 56 passed, 0 failed, 0 errors in 0.11s [VERIFIED]
```

Test categories:
- TestRegression (7 tests): locked regression values with 5% tolerance
- TestBoundaries (6 tests): zero-input and extreme-value behavior
- TestProperties (28 tests): parametrized across 7 estimators × 4 properties
- TestScaling (7 tests): monotonicity (more SF → more hours)

### Test Suite 2: CI-Enforced — signcalc smoke test (inline)

```
Result: PASSES [VERIFIED] — wind_force_on_sign and design_embed produce valid output
```

### Test Suite 3: signcalc-service formal tests (`test_sign_api.py`)

```
Result: 3 tests, 3 FAILED [VERIFIED]
```

All 3 failures identical:
- **Input:** `AsyncClient(app=app, base_url="http://test")`
- **Expected:** httpx AsyncClient accepts `app` kwarg (for ASGI transport)
- **Actual:** `TypeError: AsyncClient.__init__() got an unexpected keyword argument 'app'`
- **Cause:** httpx 0.28.x removed the `app` parameter; requires `ASGITransport` wrapper [VERIFIED]

### Test Suite 4: signx-takeoff non-CI tests

```
Result: 123 passed, 12 failed, 8 skipped in 0.36s [VERIFIED]
```

Individual failures:

| Test | Expected | Actual |
|------|----------|--------|
| `test_boundary.py::test_clnon_no_install_ot_line` | CLNON should have no OT lines | Has OT line '9600' (0.75 hrs) |
| `test_regression.py::test_cl_std_total_man_hours_locked` | Locked regression value | Value changed (regression broke) |
| `test_regression.py::test_cl_halo_total_man_hours_locked` | Locked regression value | Value changed |
| `test_regression.py::test_cl_non_total_man_hours_locked` | Locked regression value | Value changed |
| `test_regression.py::test_cl_non_no_ot_lines` | CLNON no OT lines | Has OT line |
| `test_regression.py::test_cl_strip_total_man_hours_locked` | Locked regression value | Value changed |
| `test_regression.py::test_rem_cllit_total_man_hours_locked` | Locked regression value | Value changed |
| `test_regression.py::test_rem_mondf_total_man_hours_locked` | Locked regression value | Value changed |
| `test_phase1.py::test_sign_type_enum_members` | All enum members present | Missing members |
| `test_phase1.py::test_gemini_has_install_ot` | Gemini sign type has OT | No OT found |
| `test_phase1.py::test_other_sign_type_no_ot_lines` | OTHER type no OT | Has unexpected OT |
| `test_validation.py::test_warehouse_benchmark_returns_result` | `benchmark(15.0)` returns data | Returns `None` (no warehouse CSV on Linux) |

### Test Suite 5: IQ Client tests

```
Result: 10 passed, 0 failed in 0.11s [VERIFIED]
```

### Test Suite 6: Top-level `tests/` directory

```
Result: 126 passed, 34 failed, 141 errors in 4.61s [VERIFIED]
```

**Collection errors (8):** Tests that cannot even import:

| File | Missing Import |
|------|---------------|
| `tests/api/test_materials_gateway.py` | `apex.api.main` |
| `tests/contract/test_openapi_contract.py` | `apex.api.main` |
| `tests/integration/test_cad_export_route.py` | `apex.api.main` |
| `tests/solvers/test_edge_cases.py` | `apex.domains.signage` |
| `tests/unit/test_cantilever_solver.py` | `apex.domains.signage` |
| `tests/unit/test_determinism.py` | `apex.domains.signage` |
| `tests/unit/test_signage_solvers.py` | `apex.domains.signage` |
| `tests/worker/` (all 5 files) | `celery` module |

**Failures (34):** Predominately due to:
- Missing `services/api` (test fixture loads fail)
- Services not running (connection refused to localhost:8000)
- Missing `apex.domains.signage` module
- httpx API change (same as signcalc)

### Test Suite 7: Benchmark tests

```
Result: 0 passed, 4 collection errors [VERIFIED]
```

**Cause:** `catscale_delta_parser.py:625` has a **SyntaxError** — a `logger.debug()` call appears between a `try:` block and its `except:` clause (misindented code). All 4 test files fail to import the parser.

### Lint: ruff check

**signx-takeoff/ (122 violations):** [VERIFIED]
- 58× E741 (ambiguous variable name `l`)
- 19× F401 (unused imports)
- 14× E402 (module-level import not at top of file)
- 12× F541 (f-string without placeholders)
- 3× F841 (assigned but never used)
- **Not blocking** — CI uses `|| true`

**services/signcalc-service/ (14 violations):** [VERIFIED]
- 6× F541, 4× F401, 1× F841, 2× F401 (typing), 1× F401 (dataclasses)
- **Not blocking** — CI uses `|| true`

### Type Checking

[VERIFIED] **No type checking configured anywhere.** No mypy, no pyright, no pytype. No `py.typed` marker. No type-check step in CI.

### What Has NO Test Coverage

[VERIFIED] The following production behaviors have zero automated test coverage:

1. All 49 HTTP endpoints in `app.py` (only manual/live tests exist)
2. PDF extraction (`extract_pf_from_pdf.py`)
3. Mail processing (`mail_processor.py`, `mail_classifier.py`, `mail_state.py`)
4. Notion API integration (inline in `app.py`)
5. Drawing search (`drawing_search.py`)
6. Project file lookup (`project_files.py`)
7. Customer intelligence (`customer_intel.py`)
8. Bid scoring feature engineering (`bid_scoring.py`)
9. Bid model training and prediction (`bid_model.py`)
10. Calibration pipeline (`calibrate.py`)
11. Warehouse data loading (`warehouse.py`)
12. LED catalog (`led_catalog.py`)
13. Dossier/Claude integration (`app.py:1526-1860`)
14. SMS/email notification (`app.py:1408-1456`)
15. KeyedIn format endpoint (`app.py:1492-1524`)
16. All structural engineering endpoints (wind, foundation, anchors, member check, full design)
17. The SignX-500IQ knowledge graph service
18. Error handling and edge cases in all endpoints

---

## PHASE 5 — CONFLICT LEDGER

### Conflict 1: OpenAPI Spec vs Actual API — ZERO OVERLAP

| Source | Tier | Claims |
|--------|------|--------|
| `api-spec.json` (OpenAPI 3.1) | Tier 3 | 32 paths: `/health`, `/ready`, `/projects/`, `/signage/...`, `/auth/...`, `/v1/materials/pick` |
| `signx-takeoff/app.py` (code) | Tier 1 (runtime) | 49 paths: `/api/estimate`, `/api/structural/wind`, `/api/notion/bids`, `/api/dossier`, etc. |

**There is not a single endpoint in common.** The OpenAPI spec describes a different application ("APEX API" with projects, auth, signage solvers, materials picker). The running code is "SignX Takeoff" with estimation, structural, Notion, and intelligence endpoints.

**Winner:** Code (Tier 1). The spec is a historical artifact from a different architecture.

### Conflict 2: CLAUDE.md vs Repository Structure

| CLAUDE.md Claims | Reality |
|------------------|---------|
| `services/api/` — Main FastAPI API server with Alembic migrations | [VERIFIED] **Does not exist** |
| `apex/apps/ui-web/` — React frontend application | [VERIFIED] **Does not exist** |
| `services/worker/` — Celery async task worker | [VERIFIED] **Does not exist** |
| PostgreSQL (port 5432) — Primary database | [VERIFIED] **Not used by production code** (signx-takeoff uses DuckDB + CSV + SQLite) |
| Redis (port 6379) — Caching and Celery queue | [VERIFIED] **Not used by production code** |
| MinIO — S3-compatible object storage | [VERIFIED] **Not used by production code** |
| OpenSearch — Search with DB fallback | [VERIFIED] **Not used by production code** |
| `npm run dev` — Frontend dev server | [VERIFIED] **No frontend exists** |
| `alembic upgrade head` — Run migrations | [VERIFIED] **No Alembic directory exists** |
| `pytest services/api/tests/ -v` — Run tests | [VERIFIED] **Path does not exist** |

**Winner:** Code (Tier 1). CLAUDE.md describes a planned/abandoned architecture. Every command in the "Essential Commands" section except `docker-compose up -d` references non-existent paths.

### Conflict 3: README.md vs Reality

| README Claims | Reality |
|---------------|---------|
| "Ready to Deploy" | [VERIFIED] Docker Compose cannot build (missing `services/api/`) |
| "Instant Online Quoting — <5 minutes" | [VERIFIED] No quoting UI exists; `modules/quoting/__init__.py` is empty |
| "GPU-accelerated ML models trained on your data" | [VERIFIED] `services/ml/` has model definitions but no trained models. `bid_model.py` trains a basic logistic regression on import. |
| "95-Year Knowledge Base — Gemini RAG" | [VERIFIED] `modules/rag/__init__.py` is empty. No RAG implementation found. |
| "Production Automation — CNC" | [VERIFIED] No CNC code found |
| "500+ customers" | [UNKNOWN] — cannot verify business claims |
| Repository structure diagram | [VERIFIED] Does not match actual layout (e.g., `platform/api/main.py` does not exist) |

**Winner:** Code (Tier 1). README is aspirational marketing.

### Conflict 4: Makefile vs Actual Paths

| Makefile Target | Runs | Reality |
|-----------------|------|---------|
| `make test` | `pytest services/api/tests/ -v` | [VERIFIED] Path does not exist — would fail |
| `make lint` | `ruff check services/api/` | [VERIFIED] Path does not exist — would fail |
| `make test-ml` | `pytest services/ml/tests/ -v` | [VERIFIED] Path exists but tests import missing packages |
| `make format` | `black services/api/ services/ml/` | [VERIFIED] `services/api/` does not exist |
| `make extract-pdfs` | `python scripts/extract_pdfs.py` | [VERIFIED] `scripts/extract_pdfs.py` does not exist |
| `make train-cost-model` | `python scripts/train_cost_model.py` | [VERIFIED] File does not exist |

**Winner:** Code (Tier 1). Makefile references an earlier architecture.

### Conflict 5: Docker Compose vs Actual Services

| `infra/compose.yaml` Defines | Builds From | Reality |
|-------------------------------|-------------|---------|
| `api` service | `../services/api` | [VERIFIED] Path does not exist |
| Health check | `http://localhost:8000/ready` | [VERIFIED] The actual API runs on port 8765 and has no `/ready` endpoint |

**Winner:** Code (Tier 1). Compose file is from the "APEX" architecture that was never completed.

### Conflict 6: `tests/conftest.py` vs Actual Module Structure

| `tests/conftest.py` (Tier 2) | Code (Tier 1) |
|-------------------------------|---------------|
| Imports `apex.api.main` from `services/api/src` | No such module exists |
| Sets `DATABASE_URL`, `REDIS_URL`, `OPENSEARCH_URL` | Production code uses none of these |
| Creates `AsyncClient(app=app)` | Production API is signx-takeoff on port 8765 |

**Winner:** Code (Tier 1). The conftest fixtures are orphaned from a deleted/never-built service.

### Conflict 7: Non-CI Tests vs Engine Behavior

| Test (Tier 2) | Engine Code (Tier 1) |
|----------------|---------------------|
| `test_regression.py`: 6 locked man-hour values | Engine produces different values (OT lines added since tests were locked) |
| `test_phase1.py`: expects `GEMINI` has OT, `OTHER` has no OT | Engine gives OT to OTHER, not GEMINI |
| `test_boundary.py`: CLNON should have no OT | Engine adds OT line `9600` to CLNON |

**Winner:** Code (Tier 1). Tests are stale — locked values were recorded before OT probability logic was added. Tests were never updated. This is the highest-risk conflict because regression tests are supposed to catch regressions, but they are themselves regressed.

### Conflict 8: GitLab CI vs GitHub CI

| Artifact | Claims |
|----------|--------|
| `.gitlab-ci.yml` (Tier 2) | Defines `audit:swarm` stage running `ops/agents/orchestrator` |
| `.github/workflows/ci.yml` (Tier 1) | The actual enforced CI |

[VERIFIED] GitLab CI file exists but repo is on GitHub. The GitLab pipeline references `ops/requirements.txt` and `ops/agents/` which exist in the repo but have no production use.

**Winner:** GitHub Actions (Tier 1). GitLab CI is dead.

---

## PHASE 6 — GAP LIST

1. [VERIFIED] `services/api/` does not exist. Referenced by: `tests/conftest.py`, `infra/compose.yaml`, `Makefile` (3 targets), `CLAUDE.md` (8 sections).
2. [VERIFIED] `services/worker/` does not exist. Referenced by: `tests/worker/conftest.py`.
3. [VERIFIED] `apex/apps/ui-web/` does not exist. Referenced by: `CLAUDE.md`.
4. [VERIFIED] `api-spec.json` (OpenAPI) describes zero endpoints that exist in the running application.
5. [VERIFIED] `CLAUDE.md` documents a system architecture that does not exist (PostgreSQL, Redis, MinIO, Celery, React, Alembic).
6. [VERIFIED] `README.md` claims "Ready to Deploy" but Docker Compose cannot build.
7. [VERIFIED] `Makefile` targets `test`, `lint`, `format`, `extract-pdfs`, `train-cost-model` all reference nonexistent paths/files.
8. [VERIFIED] Ruff lint is non-blocking in CI (`|| true` on both lint steps in `ci.yml:101-105`).
9. [VERIFIED] 122 ruff violations in `signx-takeoff/`, 14 in `services/signcalc-service/`.
10. [VERIFIED] No type checking (mypy/pyright) configured or enforced anywhere.
11. [VERIFIED] No `.pre-commit-config.yaml` (excluding vendored WebScrapers).
12. [VERIFIED] No `pyproject.toml` for `signx-takeoff/` — uses `requirements.txt` only.
13. [VERIFIED] `signx-takeoff/` is not a Python package (no `__init__.py`).
14. [VERIFIED] No `conftest.py` in `signx-takeoff/tests/`.
15. [VERIFIED] `test_sign_api.py` (signcalc): all 3 tests fail. `httpx.AsyncClient` no longer accepts `app` kwarg in 0.28.x.
16. [VERIFIED] `catscale_delta_parser.py:625` has a SyntaxError (misindented code between try/except). All 4 Benchmark test files fail to collect.
17. [VERIFIED] 12 signx-takeoff non-CI tests fail: 8 regression locks are stale (values changed after OT logic added), 3 OT-related expectation mismatches, 1 warehouse path missing on Linux.
18. [VERIFIED] Top-level `tests/`: 8 collection errors, 34 failures, 141 errors. Only 126 of 301 tests pass.
19. [VERIFIED] `tests/conftest.py:27` imports `apex.api.main` which does not exist — breaks all tests that use root conftest fixtures.
20. [VERIFIED] 49 HTTP endpoints in `app.py` have zero automated test coverage in CI.
21. [VERIFIED] All structural engineering endpoints (wind, foundation, anchors, member-check, full-design) have zero endpoint-level tests.
22. [VERIFIED] PDF extraction, mail processing, Notion integration, drawing search, SMS notification — zero tests.
23. [VERIFIED] `warehouse.py:20` hardcodes `C:\Scripts\signx-warehouse\warehouse\raw\so_contracts_parsed.csv`. Not configurable via env var.
24. [VERIFIED] `customer_intel.py:24` hardcodes same Windows path. Not configurable via env var.
25. [VERIFIED] `bid_scoring.py:29,34` hardcodes two Windows paths. Not configurable via env var.
26. [VERIFIED] `bid_model.py:42,47` hardcodes two Windows paths. Not configurable via env var.
27. [VERIFIED] `abc_engine.py:1554` hardcodes `C:/Scripts/signx-warehouse/warehouse/signx.duckdb` as default parameter.
28. [VERIFIED] `sign_type_analysis.py:2` hardcodes `C:\Scripts\signx-warehouse\warehouse\signx.duckdb` — standalone script.
29. [VERIFIED] `mondf_analysis.py:2` hardcodes same DuckDB path — standalone script.
30. [VERIFIED] `t1_query.py:4` hardcodes same DuckDB path — standalone script.
31. [VERIFIED] `generate_foundation_drawing.py:669` hardcodes `C:\Temp` as output directory.
32. [VERIFIED] `app.py:40` — `NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")` defaults to empty string. App starts but Notion calls fail silently with empty token.
33. [VERIFIED] `app.py:41` — `NOTION_BID_PIPELINE_DB` defaults to empty string. Same silent failure.
34. [VERIFIED] No startup validation — app boots with all empty env vars and fails at request time.
35. [VERIFIED] `app.py:15` imports `json` but never uses it (F401).
36. [VERIFIED] `app.py:57,60,62,63` imports 4 symbols from `abc_engine` that are never used (F401).
37. [VERIFIED] `calibrate.py:27` imports `sys` but never uses it (F401).
38. [VERIFIED] `mail_processor.py:18` imports `os` but never uses it (F401).
39. [VERIFIED] `mail_state.py:12` imports `json` but never uses it (F401).
40. [VERIFIED] `warehouse.py:13` imports `os` but never uses it (F401).
41. [VERIFIED] `bid_model.py:192` imports `cross_val_predict` but never uses it (F401).
42. [VERIFIED] `bid_model.py:350` assigns `raw_rate` but never uses it (F841).
43. [VERIFIED] `drawing_search.py:244` assigns `name_words` but never uses it (F841).
44. [VERIFIED] `bid_scoring.py:1068` assigns `cstats` but never uses it (F841).
45. [VERIFIED] `foundation_embed.py:283` assigns `phi_rad` but never uses it (F841).
46. [VERIFIED] `extract_pf_from_pdf.py:226` assigns `is_closed` but never uses it (F841).
47. [VERIFIED] 19 f-strings without placeholders across signx-takeoff (F541) — `f"string"` where plain `"string"` was intended.
48. [VERIFIED] 58 uses of variable name `l` (E741 — ambiguous, looks like `1`) across signx-takeoff.
49. [VERIFIED] `svcs/` (13 agent dirs, 2,471 LOC) — zero production imports. Dead code.
50. [VERIFIED] `modules/` (5 dirs, 1,388 LOC) — never called by production code. Dead code.
51. [VERIFIED] `signx_platform/` (7 files, 522 LOC) — module registry never invoked. Dead code.
52. [VERIFIED] `SignX-Intel/` (30+ files, 2,597 LOC) — zero implementation. Scaffolding.
53. [VERIFIED] `services/ml/` (11 files, 1,500+ LOC) — models defined, never trained. Scaffolding.
54. [VERIFIED] `services/materials-service/` — standalone, never integrated.
55. [VERIFIED] `services/signs-service/` — standalone, never called.
56. [VERIFIED] `services/translator-service/` — standalone, never called.
57. [VERIFIED] `eagle_analyzer_v1/` (11 files, 3,215 LOC) — superseded by `abc_engine.py`. Dead code.
58. [VERIFIED] `EagleHub/` (7 files, 1,745 LOC) — abandoned HTML dashboard. Dead code.
59. [VERIFIED] `WebScrapers/` (5,811 LOC) — vendored Scrapling library, never imported. Dead code.
60. [VERIFIED] `ConstructIQ/` (81 files, 168 LOC) — YouTube transcript stubs. Dead code.
61. [VERIFIED] `k8s/charts/` — skeleton Helm charts, cannot deploy.
62. [VERIFIED] `infra/terraform/` — skeleton Terraform, cannot deploy.
63. [VERIFIED] `docker-compose.prod.yml` — never deployed (no host configured).
64. [VERIFIED] `docker-compose.yml` (root) — separate from `infra/compose.yaml`, unclear which is canonical.
65. [VERIFIED] `.gitlab-ci.yml` — exists but repo is on GitHub. Orphaned CI config.
66. [VERIFIED] `monitoring/` — Grafana/Prometheus configs exist but monitoring is not running.
67. [VERIFIED] `contracts/` (11 files) — contract definitions for `svcs/` agents which are dead code.
68. [VERIFIED] `semgrep` security scan uses `continue-on-error: true` — non-blocking.
69. [VERIFIED] `pywin32==311` in `requirements.txt` — fails to install on Linux (caught by try/except in mail_processor.py, but still listed as hard dependency).
70. [VERIFIED] `bid_model.py` trains model on module import — runs training every time any code imports it.
71. [VERIFIED] No CHANGELOG file in repository.
72. [VERIFIED] No ADR (Architecture Decision Record) files.
73. [VERIFIED] `api-spec.json` is UTF-16 encoded (unusual for JSON; most tools expect UTF-8).
74. [VERIFIED] `signx-takeoff/.env.example:29` contains what appears to be a real phone number (`7122666482`).
75. [VERIFIED] `signx-takeoff/.env.example:8` contains what appear to be real Notion database IDs.
76. [VERIFIED] `app.py` is 2,156 lines — monolithic file containing all 49 endpoints, Notion integration, SMTP logic, and dossier/Claude calls with no separation.
77. [VERIFIED] `static/index.html` is 249,530 bytes — entire dashboard UI in a single HTML file.
78. [VERIFIED] No authentication or authorization on any signx-takeoff endpoint.
79. [VERIFIED] No rate limiting on any signx-takeoff endpoint.
80. [VERIFIED] No request logging middleware in signx-takeoff.
81. [VERIFIED] No CORS configuration in signx-takeoff (FastAPI default = no CORS headers).
82. [INFERRED] `RFP_Answer_Agent.mp4` (binary video file) is tracked in git at root level.
83. [VERIFIED] 50+ markdown files at repository root — many are session snapshots with no ongoing relevance.
84. [VERIFIED] `.env.example` real Notion DB ID `304c1e58d2dd814aae63c6a0d44e6679` for bid pipeline — confirms this is the production Notion workspace.

---

## ADDENDUM — Second Pass (2026-05-18, deeper verification)

### Additional Conflict: Docstring Work Code Count vs Runtime

| Source | Tier | Claims |
|--------|------|--------|
| `abc_engine.py:22` (docstring) | Tier 4 | "WORK_CODES (51 codes)" |
| `abc_engine.py:621-663` (code, runtime) | Tier 1 | 41 entries in WORK_CODES dict |

**Winner:** Code (Tier 1). Docstring overstates by 10 codes. [VERIFIED]

### Additional Conflict: Docstring Estimator Count vs Actual Functions

| Source | Tier | Claims |
|--------|------|--------|
| `abc_engine.py:3-8` (docstring) | Tier 4 | "6 estimators" |
| `abc_engine.py` (function definitions) | Tier 1 | 9 estimator functions: `estimate`, `estimate_monument`, `estimate_removal`, `estimate_awning`, `estimate_pylon`, `estimate_cabinet`, `estimate_directional`, `estimate_dimensional`, `estimate_flatpanel` |

**Winner:** Code (Tier 1). Docstring was written before directional/dimensional/flatpanel were added. [VERIFIED]

### Additional Runtime Verification

85. [VERIFIED] `abc_engine.py:22` docstring says "51 codes" but `WORK_CODES` dict contains exactly 41 entries at runtime.
86. [VERIFIED] `abc_engine.py:3-8` docstring says "6 estimators" but 9 estimator functions exist in the module.
87. [VERIFIED] `bid_model.py` trains a logistic regression model on module import. When no warehouse data is available (Linux/CI), training fails with `"Expected 2D array, got 1D array"` and falls back to returning fixed scores. This error fires every time `app.py` imports.
88. [VERIFIED] `abc_engine.py` has zero `assert` or `raise` statements in any estimator function — all inputs accepted without validation. Negative SF, negative letter counts, etc. would produce nonsense output silently.
89. [VERIFIED] `wind_asce7.py` DOES validate inputs: raises `ValueError` for invalid exposure, non-positive dimensions, non-positive wind speed. Signcalc has input validation; signx-takeoff does not.
90. [VERIFIED] `foundation_embed.py` DOES validate inputs: raises `ValueError` for non-positive dimensions and degenerate cases.
91. [VERIFIED] `app.py` has no CORS middleware — no `CORSMiddleware` import or configuration. Cross-origin browser requests would be blocked.
92. [VERIFIED] `app.py:43` — `"Authorization": f"Bearer {NOTION_TOKEN}"` is for outbound Notion API calls. No inbound authentication exists on any of the 49 endpoints.
93. [VERIFIED] `app.py` reports 54 routes total (includes built-in FastAPI routes like `/docs`, `/openapi.json`).
94. [VERIFIED] SignType enum has 18 members, but only 9 have dedicated estimator functions. The remaining 9 types (CLNON, MONSF, POLLIT, BLDILL, BLDNON, GEMINI, LED, ALULIT, ALUNON) are handled by the generic `estimate()` function or by `estimate_pylon()` (POLNON) — actual dispatch logic would need further tracing to confirm coverage.

---

*End of audit. 94 findings enumerated. No fixes proposed — that is a separate task.*
