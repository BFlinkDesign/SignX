SHELL := /bin/bash
.ONESHELL:

export PYTHONUNBUFFERED=1

up:
	docker compose --env-file .env -f infra/compose.yaml up --build -d
	@echo "â†’ waiting for api health..."
	@timeout 60 bash -c 'until curl -fsS http://localhost:8000/health >/dev/null; do sleep 1; done'
	@echo "âœ“ api healthy"

down:
	docker compose -f infra/compose.yaml down -v --remove-orphans

logs:
	docker compose -f infra/compose.yaml logs -f --tail=200

sync:
	uv pip sync <(uv pip compile --generate-hashes pyproject.toml)

sync-api:
	uv pip compile services/api/pyproject.toml -o .venv/req-api.txt --generate-hashes && uv pip install -r .venv/req-api.txt

sync-worker:
	uv pip compile services/worker/pyproject.toml -o .venv/req-worker.txt --generate-hashes && uv pip install -r .venv/req-worker.txt

lint:
	ruff check .

typecheck:
	mypy .

test:
	pytest -q

smoke:
	python scripts/smoke.py

fmt:
	ruff format .

.PHONY: verify verify-demo gc gc-dry

verify: ## Verify a task: make verify TASK=demo-materials-1
	python svcs/orchestrator/main.py --verify $(TASK)

verify-demo: ## Verify demo-materials-1
	$(MAKE) verify TASK=demo-materials-1

gc: ## Prune unreferenced blobs (CAS)
	python svcs/orchestrator/gc.py

gc-dry: ## Dry-run CAS GC
	python svcs/orchestrator/gc.py --dry-run
