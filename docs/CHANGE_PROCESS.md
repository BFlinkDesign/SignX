# Solver & API Change Process

We maintain deterministic, code-referenced engineering calculations. When
updating solvers or API payloads:

1. **Open a design record** – capture the motivation, affected standards, and
   expected outputs. Link the change request to the relevant code references in
   `services/api/src/apex/domains/signage/code_refs.py`.
2. **Update deterministic math first** – implement the synchronous solver,
   verify results locally, then wrap with `make_async()` and (if needed)
   `deterministic_cache` to keep concurrency safe.
3. **Document references** – ensure docstrings and validation messages reference
   constants from `code_refs.py`. This keeps unit tests, docs, and errors in
   sync.
4. **Add regression coverage** – extend unit tests with expected values. Use the
   provided fixtures to compare old vs new results and document the delta in the
   test itself.
5. **Update documentation** – refresh relevant markdown files (`docs/`,
   `services/api/src/apex/domains/signage/README.md`) with the new behaviour and
   compliance notes.
6. **Run validation suite** – execute `pytest` against unit and integration
   suites plus any domain-specific scripts (e.g., `scripts/validate_calculations.py`).
7. **PE review sign-off** – attach regression reports and updated docs for PE
   validation before promoting to production.

Following this checklist ensures envelope traces remain accurate, audit trails
stay reproducible, and compliance documentation never drifts from the
implementation.

