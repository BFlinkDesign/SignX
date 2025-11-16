# Repository Guidelines

## Project Structure & Module Organization
SignX centers on `platform/` (FastAPI entrypoint `api/main.py`, event bus, registry) plus pluggable modules in `modules/` (engineering, quoting, workflow, rag, documents). Durable services live in `services/` (`api/src` for the public HTTP tier, `ml/` for modeling, `worker/` for background jobs). Automation lives in `scripts/`, IaC stays in `infra/`, docs live in `docs/`, and tests sit in root `tests/` plus service suites such as `services/api/tests`.

## Build, Test, and Development Commands
Align with the Makefile:
- `make install` / `make install-ml` installs the Python stacks from `requirements*.txt` or `environment-ml.yml`.
- `python platform/api/main.py` runs the API on :8000 once `.venv` is active and `GEMINI_API_KEY` is exported.
- `make test`, `make test-ml`, or `make all` wrap the pytest targets and emit coverage for Codecov.
- `make lint`, `make format`, and `make up|down` run `ruff`, `black`, and the `infra/` docker-compose stack.

## Coding Style & Naming Conventions
`.editorconfig` enforces LF endings, trailing newlines, and 4-space indents for Python (2 spaces elsewhere). Run `black` before committing and resolve `ruff` violations locally; CI blocks non-compliant patches. Keep packages/modules in `snake_case`, classes in `PascalCase`, env vars in `UPPER_SNAKE`, and expose FastAPI routers from `services/api/src/api/<area>/router.py` through `__all__`. New feature modules should mirror `modules/engineering`: define a `ModuleDefinition`, register via `platform/registry.py`, and document inputs/outputs in a short README.

## Testing Guidelines
Pytest is configured via `services/api/pytest.ini`; adopt filenames `test_<feature>.py`, fixtures in `tests/fixtures/`, and `Test*` classes for structure. Run `pytest services/api/tests -v --cov=services/api --cov-report=xml` (or `make test`) for API changes and `make test-ml` for ML pipelines. `.coveragerc` tracks `platform`, `modules`, and `services` with branch coverage enabled, so add regression tests whenever behavior changes and mark slower workflows with `pytest.mark.integration`.

## Commit & Pull Request Guidelines
Commits follow Conventional Commits (`fix(ci):`, `chore(repo):`, `ci(security):`, etc.) with scopes like `quoting`, `ml`, or `worker`. Each PR should reference its issue, outline behavior changes, list the validation commands you ran, and include API samples or UI screenshots if responses change. Document migrations in `docs/CHANGELOG` and note any follow-up tasks.

## Security & Configuration Tips
`.github/workflows/security-scan.yml` runs Semgrep SAST, Gitleaks secret scanning, and Safety dependency checks on every push/PR. Run `semgrep --config=auto .`, `gitleaks detect --source .`, and `safety check --full-report` locally so the workflow stays green. Keep `.env` files out of Git (already gitignored), read secrets via `services/api/src/config`, and rotate API keys referenced in `setup_database.py` scripts after sharing logs.
