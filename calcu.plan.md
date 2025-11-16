Brady — here’s a tight, execution-ready audit + cutover plan from the state you described to a shippable, deterministic CalcuSign on APEX. I’m optimizing for zero-drift determinism, traceability, and CI gates that catch regressions before they escape.



# Status Snapshot (truth table)



| Area                                       | State                         | Gaps to Ship                                                                                                                   |
| ------------------------------------------ | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **DB schema** (projects, payloads, events) | ✅ Alembic + models wired      | Verify `ENUM` migration idempotency; add unique composite index `(project_id,module,created_at)` for payload history scan perf |
| **Projects CRUD**                          | ✅ with ETag                   | Add state machine guardrails & `412` on invalid transitions; add `/final` non-destructive view                                 |
| **Files (MinIO)**                          | ✅ presign + attach struct     | Hook MinIO client HEAD verify; SHA256 mismatch → `422` + event; store `content_type` + size                                    |
| **Direct Burial**                          | ✅ wired to signcalc + yardage | Add monotonic enforcement + unit tests over grid; surface `CALIBRATION_VERSION` in envelope.trace                              |
| **Pole filtering**                         | ✅ with AISC catalog + lock    | Ensure deflection check uses same load path as strength; include “nearest-passing” suggestion when none feasible               |
| **Baseplate checks**                       | ✅ ACI-style                   | PASS/FAIL checklist must be **all PASS** for approval; annotate each with demand/capacity/util and code reference              |
| **Pricing**                                | ✅ versioned YAML (v1)         | Add effective-date guard; reject unknown version with `409` but allow override in preview mode                                 |
| **Site resolution**                        | 🔶 endpoint stub              | Add geocode + wind lookup, cache, abstain path with confidence penalty                                                         |
| **PDF reports**                            | 🔶 renderer hook              | Implement 4-page deterministic layout + cache keyed by snapshot SHA; embed fonts; freeze timestamps                            |
| **Workers (Celery)**                       | 🔶 task skeletons             | Wire report/submit/email; exp backoff + circuit breaker + DLQ                                                                  |
| **Search & Index**                         | 🔶 fallback scaffold          | Implement OpenSearch indexer + DB fallback; log `search.fallback=true`                                                         |
| **Tests**                                  | 🔶 sparse                     | Fill contract, determinism, business logic, and e2e suites per matrix below                                                    |
| **Compose & Env**                          | ✅ unified                     | Add readiness healthchecks (Redis/OS/MinIO), and env validation at boot                                                        |
| **Docs/Runbooks**                          | 🔶 partial                    | OpenAPI examples, runbooks for footing/baseplate/submission                                                                    |



---



# Immediate Cutover Plan (48-hour sprintable)



## 1) Hardening hooks (foundation)



**Why:** enforce invariants globally; shrink per-route complexity.



* **Idempotency middleware** (header `Idempotency-Key`):



  * Key: `idem:{route}:{sha256(body)}:{key}`

  * Store final JSON response for 24h (Redis). Return cached on repeat.

* **Event emitter decorator**:



  * Emits `*.started` and `*.finished` events with `request_id`, `project_id`, content SHA; catches exceptions to emit `*.failed`.

* **Envelope builder**:



  * Round floats to UI precision, seed sort, include `constants_version`, `pricing_version`, and `index_version`. Compute `content_sha256` post-rounding.



> Drop-in snippets (ready to paste):



**Idempotency (FastAPI dependency)**



```python
# services/api/src/apex/api/common/idem.py
from hashlib import sha256
import json, aioredis

async def enforce_idempotency(request, call_next):
    key = request.headers.get("Idempotency-Key")
    if not key: return await call_next(request)
    body = await request.body()
    cache_key = f"idem:{request.url.path}:{sha256(body).hexdigest()}:{key}"
    r = await aioredis.from_url(os.getenv("REDIS_URL","redis://redis:6379"))
    if cached := await r.get(cache_key):
        return JSONResponse(content=json.loads(cached), status_code=200)
    response = await call_next(request)
    if response.status_code < 500:
        await r.set(cache_key, await response.body(), ex=86400)
    return response
```



**Event decorator**



```python
# services/api/src/apex/api/common/events.py
import functools, time
from .emit import emit_event

def instrument(event_name: str):
    def deco(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            emit_event(event_name+".started", **kwargs)
            t0 = time.perf_counter()
            try:
                res = await fn(*args, **kwargs)
                emit_event(event_name+".finished", took_ms=int((time.perf_counter()-t0)*1000))
                return res
            except Exception as e:
                emit_event(event_name+".failed", error=str(e))
                raise
        return wrapper
    return deco
```



## 2) Site Resolution (Phase 3) — deterministic + abstain path



* Geocode via Google (primary) → fallback provider. On failure: `result=null`, `assumptions+=["geocode_failed"]`, `confidence = base - 0.2`.

* Wind map lookup: prefer **pack** (digitized ASCE7) keyed by rounded `(lat,lon)`; only hit NOAA API when “live” flag set. Cache both positive/negative results (Redis; TTL 7d/30m).

* Return `SiteLoads` in envelope.



**Acceptance:**



* Returns same wind `V_3s` for identical `(lat,lon)` across runs (deterministic).

* On geocode failure, contract still returns envelope with lowered `confidence`.



## 3) Report Rendering (Phase 7.1) — deterministic 4-pager + cache



* **Key:** `pdf_sha = sha256(json.dumps(snapshot, sort_keys=True, separators=...))`

* **Fonts:** embed the same font files, freeze metadata times to envelope timestamp.

* **Pages:**



  1. Cover (project meta, mini map screenshot optional; if absent, show address only).

  2. Elevation (pole + footing/baseplate dims).

  3. Design Outputs (moments, yards, baseplate checks table).

  4. General Notes + code references and packs.



**Acceptance:** same snapshot → identical SHA; MinIO returns cached PDF.



## 4) Celery Tasks & External PM (Phase 8)



* `projects_report.py`: build or fetch cached PDF; emit `report.generated`.

* `projects_submit.py`: POST to PM; store `project_number`; retries (max 5) with exp backoff; **circuit breaker** after 3 consecutive failures; DLQ final payload.

* `projects_email.py`: send templated emails; log delivery; do **not** roll back on failure.



**Acceptance:** Simulated PM outage keeps project in `estimating`; events show retries + breaker open; DLQ populated.



## 5) OpenSearch Indexing + Fallback (Phase 9)



* Index on project create/update; capture `index_version`.

* Search route: try OS, else DB fallback; envelope.trace `search.fallback=true` when used.



**Acceptance:** With OS container down, listing still works; logs warning, not exception.



---



# Test Matrix (CI gates)



## Contract (tests/contract/)



* `test_envelope_consistency.py` — every route returns canonical envelope; floats rounded.

* `test_schemathesis_signage.py` — Run Schemathesis over `/openapi.json` with **checks=all**.



## Determinism (tests/unit/)



* `test_pdf_determinism.py` — identical inputs → same `pdf_sha`.

* `test_footing_monotonic.py` — for diameter grid, ensure `diameter↓ ⇒ depth↑`.

* `test_pole_filtering.py` — infeasible sizes never returned; minimal feasible is default.



## Business Logic (tests/service/)



* `test_material_locks.py` — aluminum >15ft → `422`.

* `test_multi_pole.py` — moments split evenly; capacities per pole correct.

* `test_baseplate_checks.py` — approval only when all PASS.

* `test_pricing_versioning.py` — v1 loads; wrong version `409` unless preview mode.

* `test_submission_idempotency.py` — same key → identical result.



## E2E (tests/e2e/)



* `test_full_workflow.py` — draft → estimate → submit → PM sync (mock).

* `test_abstain_paths.py` — geocode fail lowers confidence; no feasible pole returns explanation and nearest-passing suggestions.

* `test_search_fallback.py` — kill OS → DB fallback still returns list.



---



# Operational Runbook (operators can follow verbatim)



## Bootstrap & Migrate



```bash
# 1) env
cp .env.example .env
export PRICING_VERSION=v1

# 2) start stack
docker compose -f infra/compose.yaml up -d --build

# 3) migrations
docker compose exec api alembic upgrade head
```



## Smoke



```bash
# create project
curl -sX POST :8000/projects -H 'content-type: application/json' -d '{"name":"Demo","meta":{"address":"123 Main, Dallas TX"}}' | jq .

# estimate
curl -sX POST :8000/projects/{id}/estimate -d '{"height_ft":24,"addons":["calc_packet","hard_copies"]}' | jq .

# site resolve (abstain if no API key)
curl -s :8000/signage/common/site/resolve -d '{"address":"123 Main, Dallas TX"}' | jq .

# pole options
curl -s :8000/signage/common/poles/options -d '{"Mu_required_kip_in":120,"deflection_allow_in":1.5,"height_ft":20,"material":"steel","num_poles":1,"prefs":{"family":"round","steel_grade":"A36","sort_by":"weight"}}' | jq .
```



---



# Gaps to Close (precise tasks with acceptance)



1. **SITE-1:** Geocode + wind integration



   * **DoD:** cache + abstain path + confidence penalty; unit tests for caching and failure path.



2. **REPORT-1:** Deterministic PDF + MinIO cache



   * **DoD:** byte-identical PDFs for same snapshot in CI; 4 pages populated; SHA in envelope.artifacts.



3. **WORKER-1:** Celery tasks wired + circuit breakers



   * **DoD:** outage simulation shows retries, breaker open, DLQ entries; no rollback of submission.



4. **SEARCH-1:** OpenSearch indexer + fallback



   * **DoD:** with OS down, search works via DB; `trace.search.fallback=true`.



5. **TESTS-ALL:** Fill matrix above



   * **DoD:** all green locally and in CI; Schemathesis passes.



6. **FILES-1:** MinIO attach verification



   * **DoD:** HEAD verifies size/hash; SHA mismatch → `422`, event logged.



7. **PROJECTS-STATE:** Transition guards



   * **DoD:** invalid transitions → `412`; events emitted on each transition.



---



# Guardrails & Observability (baked-in)



* **Secrets:** env-only; validate on boot (fail fast) → missing `GOOGLE_MAPS_API_KEY` flips site resolve to abstain mode.

* **RBAC:** route scopes (read/write/submit); deny by default; tests assert 403s.

* **Structured logs:** `request_id`, `project_id`, `event_type`, `content_sha`; log sampling for success, full for failures.

* **ETag enforcement:** write routes require `If-Match`; respond `412` on mismatch.

* **Circuit breakers:** geocode, PM, email; metrics exported (`breaker_open_total`).



---



# Risk Register → Action



* **Provider nondeterminism (maps/wind)** → Prefer **packs**; only use live API with explicit flag; record provider+version in `trace`.

* **PDF drift (fonts/timestamps)** → Embed fonts; freeze creation time to envelope timestamp; single renderer config in repo.

* **Search outage** → DB fallback + `search.fallback=true`; queue index ops and DLQ on mapping errors.

* **Concurrent edits** → ETag everywhere; tests for conflict handling.

* **Idempotency leakage** → Redis TTL 24h; store final response snapshot by idem key; test duplicate submit returns identical body.



---



# What’s Already Safe vs. Needs Eyes



**Safe to proceed:**



* Projects CRUD (persistence + ETag)

* Pole filtering + material lock

* Baseplate checks (enforce “all PASS”)

* Direct burial + yardage calc

* Pricing v1 + config loader



**Needs eyes before release:**



* Deterministic PDF (byte-stable)

* Site resolve confidence logic

* Submission side-effects (breaker/DLQ)

* Full CI (Schemathesis + e2e) gate



---



# Delivery Sequence (fastest path to “demoable + safe”)



1. **REPORT-1** (users see value; also validates snapshot SHA path)

2. **SITE-1** (unblocks Stage 3 completeness)

3. **WORKER-1** (submission pipeline reliability)

4. **SEARCH-1** (UX perf + resiliency)

5. **TESTS-ALL** (lock in invariants)



---



# Go/No-Go Checklist (ship gate)



* [ ] All endpoints return Envelope with rounded numbers & `content_sha256`

* [ ] `test_pdf_determinism.py` → PASS (identical SHA)

* [ ] `test_footing_monotonic.py` → PASS (grid)

* [ ] `test_pole_filtering.py` → PASS (no infeasible)

* [ ] `test_submission_idempotency.py` → PASS

* [ ] Geocode fail path lowers `confidence`

* [ ] OpenSearch outage scenario passes via DB fallback

* [ ] No secrets in repo; env validated on boot

* [ ] `project_events` shows full audit trail for e2e



---



# Confidence Index



**Confidence: 0.84 (high).**

**Basis:** Your reported implementation state maps cleanly to the original plan; remaining items are integrations + determinism work. Unknowns: exact AISC catalog parity, ASCE/ACI digitization specifics, and any private schema nuances. The plan above assumes standard FastAPI/SQLAlchemy/Celery/MinIO/OpenSearch stack semantics.



---



If you want me to proceed hands-on, I’ll start with **REPORT-1** (deterministic renderer + cache) and **SITE-1** (geocode/wind with abstain), then drop in the test suites so CI goes green as we land functionality.


