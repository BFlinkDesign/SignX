# Project Search Consistency Playbook

The `/projects` endpoint serves search results from OpenSearch with a PostgreSQL
fallback. To guarantee identical envelopes regardless of source, the following
rules are enforced:

1. **Single serialization path** – both OpenSearch and DB results are routed
   through `_coerce_search_record()` so field names and formats match exactly.
2. **ISO timestamps** – `created_at` values are normalized to ISO 8601 strings
   (UTC when available) so downstream clients can rely on a stable format.
3. **Trace parity** – The API response is built via
   `build_response_envelope(...)`, capturing whether a fallback was used in the
   envelope trace (`trace.data.intermediates.search_fallback`).
4. **Regression tests** – See `tests/unit/test_project_search_normalization.py`
   for guardrails that compare serialized SQLAlchemy models to normalized
   OpenSearch documents.

## Change checklist

When modifying project search behaviour:

- [ ] Update `_serialize_project_model()` if the DB payload shape changes.
- [ ] Update `_coerce_search_record()` so OpenSearch results mirror the same
      structure.
- [ ] Extend `test_project_search_normalization.py` with new fixture data.
- [ ] Verify envelope callers still use `build_response_envelope()` to capture
      trace metadata.

Keeping both paths in lockstep avoids subtle client regressions when OpenSearch
is unavailable and ensures audit trails remain deterministic.

