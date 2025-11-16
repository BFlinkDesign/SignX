## Multi‑Agent RAG Auditing & Refactoring (Ops)

This `ops/agents` toolkit provides a modular, multi‑agent pipeline to:
- Audit code quality and technical debt across subprojects
- Detect unused files/dead code and unused dependencies
- Build a lightweight RAG index over code/docs to support reasoning
- Propose refactors and streamlining actions with an evidence trail

### High‑Level Agents
- AuditorAgent: runs static analyzers (ruff, mypy, deptry, vulture, eslint if available) and normalizes results.
- UnusedDetectorAgent: finds unused files and symbols (Python via AST+vulture; TS via ts-prune when available).
- RAGIndexerAgent: builds a local SQLite-backed code/docs index for retrieval.
- RefactorPlannerAgent: aggregates signals and produces actionable proposals (keep, refactor, archive, delete).
- Orchestrator: coordinates agents and emits reports in `ops/reports/`.

### Swarms and Subagents
- The orchestrator can spawn concurrent subagents per project root using a SwarmManager.
- Configure worker pool size and toggles in `ops/agents/config.yaml` (`swarm.max_workers`, `swarm.enabled`).
- CLI flags allow overriding: `--swarm/--no-swarm`, `--workers N`.

### Quick Start (Windows PowerShell)
1) (Optional) Create a virtualenv for ops tools
   - `py -3.12 -m venv .venv_ops`
   - `.\\.venv_ops\\Scripts\\Activate.ps1`
   - `pip install -r ops\\requirements.txt`
2) Run the full audit:
   - `powershell -ExecutionPolicy Bypass -File ops\\run_audit.ps1`
   - With swarm options: `powershell -ExecutionPolicy Bypass -File ops\\run_audit.ps1 -Workers 6`
3) Inspect outputs in:
   - `ops/reports/summary.md`
   - `ops/reports/findings.json`
   - `ops/reports/unused_files.json`
   - `ops/reports/rag/index.sqlite` (RAG store)

### Configuration
Edit `ops/agents/config.yaml` to include project roots to analyze and ignore patterns. Defaults focus on:
- `SignX-Studio/`
- `SignX-Intel/`
- `Keyedin/`

### Notes
- Node-based tools (eslint/ts-prune) are invoked only if found locally.
- All reports are deterministic and CI-friendly where possible.
- No app code is modified by default; proposals are written as reports.


