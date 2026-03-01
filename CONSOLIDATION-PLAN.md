# Consolidation Plan — Restructure Repo Around Real Working Code

**Created:** 2026-03-01
**Goal:** Align the GitHub repo with reality. Protect unprotected code. Delete scaffolding. Make the repo honest.

---

## Phase 1: PROTECT (Do immediately on CNC-1)

### Step 1.1: Add CNC-1 scripts to git

Run on CNC-1 (Brady's machine):

```powershell
cd C:\Users\Brady.EAGLE\Desktop\SignX

# Create directories for CNC-1-only code
mkdir signx-warehouse\scripts
mkdir keyedin-capture
mkdir keyedin-automation

# Copy critical parser
copy "C:\Scripts\signx-warehouse\scripts\parse_full_cost_detail.py" signx-warehouse\scripts\

# Copy capture scripts (code only, not 559MB HTML)
copy "C:\Scripts\keyedin-capture\*.py" keyedin-capture\
copy "C:\Scripts\keyedin-capture\requirements.txt" keyedin-capture\ 2>nul

# Copy automation/MCP server
copy "C:\Scripts\keyedin-automation\keyedin.py" keyedin-automation\
xcopy "C:\Scripts\keyedin-automation\scripts\*" keyedin-automation\scripts\ /E
copy "C:\Scripts\keyedin-automation\requirements.txt" keyedin-automation\ 2>nul

# Copy site map
mkdir keyedin-automation\discovery\keyedin
copy "C:\Scripts\keyedin-automation\discovery\keyedin\keyedin_site_map.json" keyedin-automation\discovery\keyedin\

# Stage and commit
git add signx-warehouse\scripts\parse_full_cost_detail.py
git add keyedin-capture\*.py
git add keyedin-automation\
git commit -m "chore: protect CNC-1-only scripts (parser, capture, MCP server)"
git push
```

### Step 1.2: Protect warehouse data (NOT in git — too large)

```powershell
# Verify OneDrive sync is current
dir "~\OneDrive - Eagle Sign Co\signx-warehouse\warehouse\raw\so_contracts_parsed.csv"
dir "~\OneDrive - Eagle Sign Co\signx-warehouse\warehouse\signx.duckdb"

# If not syncing, copy manually:
robocopy "C:\Scripts\signx-warehouse\warehouse" "~\OneDrive - Eagle Sign Co\signx-warehouse\warehouse" /MIR /XD __pycache__
```

### Step 1.3: Add .gitignore entries for large data

```gitignore
# Warehouse data (too large for git, use OneDrive)
*.duckdb
*.db
signx-warehouse/warehouse/raw/
signx-warehouse/warehouse/production/
keyedin-capture/reports/
```

---

## Phase 2: DELETE (Remove scaffolding and dead code)

### What to delete from the repo

| Path | Reason | LOC Removed |
|------|--------|-------------|
| `svcs/` | 9 agents + orchestrator, 0 production imports | 2,471 |
| `modules/` | 5 modules, all return mocks, never called | 1,388 |
| `signx_platform/` | Platform registry, never used | 522 |
| `SignX-Intel/` | Zero implementation, all scaffolding | 2,597 |
| `services/ml/` | XGBoost/GNN, never trained | 1,500 |
| `services/materials-service/` | Never integrated | 300 |
| `services/signs-service/` | Never called | 600 |
| `services/translator-service/` | Single file, never called | 100 |
| `eagle_analyzer_v1/` | Superseded by abc_engine.py | 3,215 |
| `EagleHub/` | Abandoned HTML dashboard | 1,745 |
| `WebScrapers/` | Vendored library, never imported | 5,811 |
| `ConstructIQ/` | YouTube transcript stubs | 168 |
| `k8s/charts/` | Skeleton Helm, can't deploy | 100 |
| `infra/terraform/` | Skeleton, can't deploy | 200 |
| `docker-compose.prod.yml` | Never deployed | 200 |
| `archive/` | Old deliverable docs | 456 |
| `recon-results/` | One-time recon | 676 |
| `export-test-results/` | Empty | 0 |
| `patches/` | One-time patches | 0 |
| `queue/` | Queue stubs | 0 |
| `runbooks/` | Never populated | 0 |
| `standards/` | Empty stubs | 0 |
| `monitoring/` | Not running | 221 |
| Root fix_*.py scripts | One-time DB fixers | ~400 |
| Root test_*.py scripts | One-time test scripts | ~600 |
| Root setup_*.py scripts | One-time setup | ~300 |
| Root *.ps1 scripts | One-time PowerShell | ~200 |
| `contracts/` | Contract tests for phantom services | 625 |
| `ops/` | Code fixers, one-time | 994 |
| **TOTAL** | | **~24,600 LOC** |

```bash
# Run from repo root
git rm -r svcs/ modules/ signx_platform/ SignX-Intel/ services/ml/ \
  services/materials-service/ services/signs-service/ services/translator-service/ \
  eagle_analyzer_v1/ EagleHub/ WebScrapers/ ConstructIQ/ k8s/charts/ \
  infra/terraform/ archive/ recon-results/ export-test-results/ patches/ \
  queue/ runbooks/ standards/ monitoring/ contracts/ ops/ \
  docker-compose.prod.yml

# Remove root one-off scripts
git rm fix_*.py test_aisc*.py test_export*.py test_monument*.py test_pe*.py \
  test_api_workflow.py test_monument_workflow.py create_monument_module.py \
  create_pole_architecture.sql setup_database.py setup_monument.py \
  update_all_db_connections.py verify_aisc.py run_migrations.py gen_renderer.py \
  run_agent_pipeline.ps1 run_autonomous_pipeline.ps1 setup_database.ps1 \
  final-cleanup.ps1 rebrand_to_signx_studio.ps1 locustfile.py

git commit -m "chore: remove 24,600 LOC of scaffolding, dead code, and one-off scripts"
```

### What to archive (move, don't delete)

```bash
# Move root markdown docs to docs/archive/
mkdir -p docs/archive/session-docs
git mv MASTER_FINAL_REPORT.md PRODUCTION_AUDIT_REPORT.md PROGRESS_REPORT.md \
  SESSION_SUMMARY.md SESSION-STATE-2026-02-15.md session-state.md \
  TRIAGE-REPORT.md EAGLE_SIGN_HANDOFF.md FULL_AUDIT_BUNDLE.md \
  calcu.plan.md claude-api-nextgen-ideas.md docs/archive/session-docs/

# Keep only essential root docs
# KEEP: README.md, CLAUDE.md, SIGNX-MASTER-SEQUENCE.md, SIGNX-PROJECT-STATE.md,
#       KEYEDIN-PIPELINE-STATUS.md, START_HERE.md, Makefile, api-spec.json,
#       env.example, mkdocs.yml, requirements-*.txt
```

---

## Phase 3: RESTRUCTURE (Proposed new directory layout)

```
SignX/
├── README.md
├── CLAUDE.md
├── SIGNX-MASTER-SEQUENCE.md
├── SIGNX-PROJECT-STATE.md
├── KEYEDIN-PIPELINE-STATUS.md
├── Makefile
├── api-spec.json
├── env.example
├── .github/workflows/
│
├── signx-takeoff/              # THE CORE — estimation engine + API
│   ├── abc_engine.py           # 8 estimators, 51 work codes
│   ├── app.py                  # FastAPI server, 47+ endpoints
│   ├── calibrate.py            # Auto-calibration
│   ├── warehouse.py            # Warehouse data access
│   ├── bid_scoring.py          # Win probability
│   ├── bid_model.py            # Logistic regression
│   ├── customer_intel.py       # Customer profiles
│   ├── drawing_search.py       # G: drive search
│   ├── project_files.py        # File server lookup
│   ├── mail_processor.py       # Outlook COM poller
│   ├── mail_classifier.py      # Email classifier
│   ├── mail_state.py           # Dedup state
│   ├── notion_sync.py          # Notion API
│   ├── iq_client.py            # 500IQ shadow mode client
│   ├── requirements.txt
│   ├── data/                   # Calibration + classifier data
│   ├── static/                 # Dashboard HTML
│   └── tests/                  # Unit + integration tests
│
├── SignX-500IQ/                 # Knowledge graph service
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── logic.py
│   ├── schemas.py
│   ├── seed_from_warehouse.py
│   └── requirements.txt
│
├── SignX-Intake/                # Email intake pipeline
│   ├── flows/                  # PA build guide
│   ├── prompts/                # Claude extraction prompts
│   ├── schemas/                # Notion schema
│   ├── recon/                  # GWT-RPC, Informer
│   └── test/
│
├── signx-warehouse/             # NEW — from CNC-1
│   └── scripts/
│       └── parse_full_cost_detail.py
│
├── keyedin-capture/             # NEW — from CNC-1
│   ├── extract_wo_batches.py
│   ├── cost_summary_automation.py
│   ├── fast_extract.py
│   └── setup_credentials.py
│
├── keyedin-automation/          # NEW — from CNC-1
│   ├── keyedin.py              # MCP server
│   ├── scripts/
│   └── discovery/
│
├── Keyedin/                     # Recon & reverse engineering archive
│
├── services/
│   └── signcalc-service/       # Structural calcs (wind + foundation)
│
├── Benchmark/                   # Cat Scale parser
│
├── infra/
│   ├── compose.yaml            # Dev compose
│   ├── docker/
│   └── backups/
│
├── scripts/                     # TRIMMED — only warehouse-related kept
│   ├── extract_mvi_csv_exports.py
│   ├── enrich_csv_exports.py
│   ├── lookup_job.py
│   └── smoke.py
│
├── tests/                       # TRIMMED — only tests for real services
│   ├── unit/
│   └── e2e/
│
├── Eagle Data/                  # Training data corpus (stays)
├── GandHSync/                   # File server sync (stays)
├── Ai Observation & Training/   # OBS automation (stays)
├── CorelDraw Macros/            # VBA macros (stays)
├── SignShopWorkflow/            # Workflow docs (stays)
├── Bluebeam/                    # (stays, 1 file)
├── Gemini Generator/            # (stays)
│
├── docs/                        # TRIMMED — remove generated bloat
│   ├── getting-started/
│   ├── guides/
│   ├── deployment/
│   └── archive/                 # Session docs moved here
│
└── data/
    └── standards/               # ASCE 7-22, PE catalog
```

---

## Phase 4: FIX HARDCODED PATHS

After restructuring, make all CNC-1 paths configurable:

```python
# Before (6 files):
Path(r"C:\Scripts\signx-warehouse\warehouse\raw\so_contracts_parsed.csv")

# After:
Path(os.environ.get("WAREHOUSE_CSV_DIR", r"C:\Scripts\signx-warehouse\warehouse\raw")) / "so_contracts_parsed.csv"
```

| File | Variable to Add | Default Value |
|------|----------------|---------------|
| `warehouse.py` | `WAREHOUSE_CSV_DIR` | `C:\Scripts\signx-warehouse\warehouse\raw` |
| `customer_intel.py` | `WAREHOUSE_CSV_DIR` | (same) |
| `bid_scoring.py` | `WAREHOUSE_CSV_DIR` | (same) |
| `bid_model.py` | `WAREHOUSE_CSV_DIR` | (same) |
| `abc_engine.py` | `SIGNX_WAREHOUSE_DB` | `C:/Scripts/signx-warehouse/warehouse/signx.duckdb` |
| `calibrate.py` | `SIGNX_WAREHOUSE_DB` | (already uses env var, just verify) |
| `drawing_search.py` | `DRAWINGS_ROOT` | (already uses env var) |
| `project_files.py` | `DRAWINGS_ROOT` | (already uses env var) |

---

## Phase 5: CLEANUP TESTS

Remove tests that test phantom services:

```bash
# Keep only tests for real services
git rm -r tests/worker/ tests/security/ tests/chaos/ tests/performance/
git rm tests/unit/test_stackup_agent.py tests/unit/test_parts_agent.py
git rm tests/unit/test_translator_basic.py
git rm tests/test_agents_smoke.py

# Keep:
# tests/unit/test_signage_solvers.py (signcalc)
# tests/e2e/test_complete_workflows.py
# tests/contract/ (if testing real services)
```

---

## Execution Summary

| Phase | Action | LOC Change | Time Est |
|-------|--------|------------|----------|
| 1. PROTECT | Copy CNC-1 scripts to repo | +2,000 | 15 min |
| 2. DELETE | Remove scaffolding/dead | -24,600 | 10 min |
| 3. RESTRUCTURE | Move/rename dirs | 0 | 20 min |
| 4. FIX PATHS | Env var all Windows paths | ~50 lines changed | 30 min |
| 5. CLEANUP TESTS | Remove phantom tests | -3,000 | 10 min |
| **TOTAL** | | **Net: -25,500 LOC** | **~1.5 hours** |

**Result:** Repo goes from ~97,000 LOC to ~71,500 LOC. Every file that remains either runs in production or is actively being developed. Zero scaffolding. All CNC-1 critical code protected in git. All external paths configurable via env vars.
