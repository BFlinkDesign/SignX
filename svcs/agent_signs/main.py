from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

from contracts.signs import (
    SignRequest,
    SignResponse,
    Spec,
    ElectricalSpec,
    MechanicalSpec,
    GraphicsSpec,
)
from svcs.common.fsqueue import FSQueue
from svcs.orchestrator.validate import validate_and_wrap, write_json_atomic
from svcs.common.index import already_processed, append_processed
from svcs.orchestrator.events import Event, append_event

# ---------------------------------------------------------------------------
# Dynamic import of signs-service domain logic.
#
# The signs-service lives at services/signs-service/ (hyphenated directory,
# not a standard Python package name).  We load it as 'signs_service' via
# importlib so we can call build_spec() without duplicating its logic here.
# ---------------------------------------------------------------------------

_SIGNS_SERVICE_DIR = Path(__file__).resolve().parents[2] / "services" / "signs-service"


def _load_signs_service() -> Any:
    """
    Load services/signs-service as the 'signs_service' package and return
    the main module (which exposes build_spec).

    This is done once at import time; subsequent calls return the cached module.
    """
    pkg_name = "signs_service"
    if pkg_name in sys.modules:
        return sys.modules[pkg_name + ".main"]

    # Register the package root so relative imports inside it resolve correctly.
    pkg_init = _SIGNS_SERVICE_DIR / "__init__.py"
    pkg_spec = importlib.util.spec_from_file_location(
        pkg_name,
        pkg_init,
        submodule_search_locations=[str(_SIGNS_SERVICE_DIR)],
    )
    pkg_mod = importlib.util.module_from_spec(pkg_spec)
    sys.modules[pkg_name] = pkg_mod
    pkg_spec.loader.exec_module(pkg_mod)

    # Register sub-packages so relative imports work transitively.
    for subpkg in ("rules", "bom", "cad"):
        sp_init = _SIGNS_SERVICE_DIR / subpkg / "__init__.py"
        sp_spec = importlib.util.spec_from_file_location(
            f"{pkg_name}.{subpkg}",
            sp_init,
            submodule_search_locations=[str(_SIGNS_SERVICE_DIR / subpkg)],
        )
        sp_mod = importlib.util.module_from_spec(sp_spec)
        sys.modules[f"{pkg_name}.{subpkg}"] = sp_mod
        sp_spec.loader.exec_module(sp_mod)

    # Load main.py (FastAPI app + build_spec function).
    main_spec = importlib.util.spec_from_file_location(
        f"{pkg_name}.main",
        _SIGNS_SERVICE_DIR / "main.py",
    )
    main_mod = importlib.util.module_from_spec(main_spec)
    sys.modules[f"{pkg_name}.main"] = main_mod
    main_spec.loader.exec_module(main_mod)
    return main_mod


try:
    _signs_main = _load_signs_service()
    _build_spec = _signs_main.build_spec
    _SIGNS_SERVICE_AVAILABLE = True
except Exception as _load_err:  # noqa: BLE001
    _SIGNS_SERVICE_AVAILABLE = False
    _load_err_msg = str(_load_err)


def _run_signs_service(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call signs-service build_spec() with the task payload.

    Returns the full domain dict including result, compliance findings,
    assumptions, and confidence score.

    Falls back to a minimal safe stub if the signs-service cannot be loaded,
    recording the load error in the result so it is visible in the audit trail.
    """
    if _SIGNS_SERVICE_AVAILABLE:
        req = SignRequest.model_validate(payload)
        # build_spec is a FastAPI route function; call it directly as a pure
        # function — it accepts a SignRequest and returns a plain dict.
        domain = _build_spec(req)
        return domain["result"]
    else:
        # Degraded-mode fallback: emit a stub result with an explicit error flag
        # so downstream review tooling can detect the failure.
        return SignResponse(
            spec=Spec(
                materials=[],
                finishes=[],
                ip_rating_target=None,
                enclosure_class=None,
            ),
            electrical_spec=ElectricalSpec(
                disconnect="DEGRADED — signs-service unavailable",
                max_input_current_A=0.0,
                branch_circuit_A=0.0,
                listing_category=None,
                required_field_labels=[],
            ),
            mechanical_spec=MechanicalSpec(
                mounting_pattern="DEGRADED",
                min_fastener_grade="DEGRADED",
                sealants=[],
                gasket_material=None,
            ),
            graphics_spec=GraphicsSpec(),
            bom=[],
            cad_macro=f"# AGENT_SIGNS: signs-service load failed: {_load_err_msg}\n",
            install_notes=["ERROR: signs-service could not be loaded — see cad_macro for details."],
            compliance=[],
            risks=[f"signs-service unavailable: {_load_err_msg}"],
        ).model_dump(mode="json")


def process_file(root: Path, path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    task_id = payload.get("task_id", "unknown")
    out_dir = root / "runs" / task_id / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Delegate to the real signs-service domain logic (NEC 600, UL 48, OSHA checks).
    result = _run_signs_service(payload)

    started = time.time()
    envelope = validate_and_wrap(
        raw=result,
        schema_model=SignResponse,
        agent="AGENT_SIGNS",
        version="0.1.0",
        code_sha="dev",
        started_at=started,
        inputs_bytes=json.dumps(payload, sort_keys=True).encode("utf-8"),
        schema_version="resp-1.0",
        blob_refs=[],
        queue_version="v1",
    )
    out_path = out_dir / "signs.json"
    write_json_atomic(out_path, envelope)
    append_event(root / "artifacts" / "logs" / "events.ndjson", Event(
        task_id=task_id,
        agent="signs",
        kind="completed",
        trace_id=envelope["trace"]["ids"]["trace_id"],
        span_id=envelope["trace"]["ids"]["span_id"],
        event="completed",
        monotonic_ms=envelope["provenance"]["monotonic_ms"],
        data_sha256=envelope["data_sha256"],
        blob_refs=envelope.get("blob_refs", []),
        message="signs processed",
    ))
    append_processed(root / "runs" / task_id, "AGENT_SIGNS", envelope["data_sha256"], envelope["trace"]["ids"]["trace_id"])


def main() -> None:
    parser = argparse.ArgumentParser(description="AGENT_SIGNS")
    parser.add_argument("--once", action="store_true", help="Process existing inbox once and exit")
    args = parser.parse_args()

    root = Path(".").resolve()
    inbox = root / "queue" / "signs" / "inbox"
    wip = root / "queue" / "signs" / "wip"
    out = root / "queue" / "signs" / "out"
    q = FSQueue(inbox, wip, out)

    def process_all() -> int:
        count = 0
        for p in q.poll():
            try:
                wip_file, fd, lock_path = q.claim(p)
            except RuntimeError:
                continue
            try:
                payload = json.loads(wip_file.read_text(encoding="utf-8"))
                task_dir = root / "runs" / payload.get("task_id", "unknown")
                if already_processed(task_dir, "AGENT_SIGNS"):
                    append_event(root / "artifacts" / "logs" / "events.ndjson", Event(
                        task_id=payload.get("task_id", "unknown"), agent="signs", kind="skipped_duplicate", trace_id="dup", span_id="dup", event="skipped_duplicate", monotonic_ms=0.0, data_sha256="", blob_refs=[], message="duplicate detected via processed index"
                    ))
                else:
                    process_file(root, wip_file)
                    count += 1
            finally:
                q.release(fd, lock_path)
        return count

    if args.once:
        process_all()
    else:
        while True:
            n = process_all()
            time.sleep(1.0 if n == 0 else 0.1)


if __name__ == "__main__":
    main()


