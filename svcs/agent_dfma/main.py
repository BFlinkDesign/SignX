from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from contracts.dfma import DFMAEvaluateRequest, DFMAEvaluateResponse, CostBreakdown
from svcs.common.fsqueue import FSQueue
from svcs.orchestrator.validate import validate_and_wrap, write_json_atomic
from svcs.common.index import already_processed, append_processed
from svcs.orchestrator.events import Event, append_event


RUNS_DIR = Path("runs")
RULES_DIR = Path("svcs/agent_dfma/rules")


def _append_status(event: str, task_id: str, extra: Dict[str, Any] | None = None) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    record: Dict[str, Any] = {"task_id": task_id, "agent": "AGENT_DFMA", "event": event}
    if extra:
        record.update(extra)
    with STATUS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


def load_rules(process: str) -> List[Dict[str, Any]]:
    fname = {
        "sheet_metal": "sheet_metal.json",
        "machining": "machining.json",
        "3dp": "printing.json",
    }.get(process, "sheet_metal.json")
    path = RULES_DIR / fname
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(req: DFMAEvaluateRequest) -> Tuple[List[str], List[str], CostBreakdown, float]:
    rules = load_rules(req.process)
    violations: List[str] = []
    suggestions: List[str] = []

    # Basic deterministic rule checks based on params
    p = req.params
    if req.process == "sheet_metal":
        r_over_t = float(p.get("r_over_t", 1.0))
        if r_over_t < 1.0:
            violations.append("min_bend_radius_violation")
            suggestions.append("Increase bend radius to >= 1t.")
        hole_edge = float(p.get("hole_edge_multiple", 1.0))
        if hole_edge < 1.5:
            violations.append("hole_to_edge_violation")
            suggestions.append("Increase hole-to-edge distance to >= 1.5d.")

    if req.process == "machining":
        slot_ratio = float(p.get("slot_l_over_d", 0.0))
        if slot_ratio > 6.0:
            violations.append("deep_narrow_slot")
            suggestions.append("Reduce slot depth or widen slot to <= 6xD.")

    if req.process == "3dp":
        wall = float(p.get("wall_thickness_mm", 0.0))
        if wall < 1.0:
            violations.append("wall_too_thin")
            suggestions.append("Increase wall thickness to >= 1.0mm.")

    # Cost model
    quantity = float(p.get("quantity", 1))
    material_cost = float(p.get("material_cost", 1.0)) * quantity
    hours = float(p.get("hours", 0.1))
    rate = float(p.get("rate", 50.0))
    process_cost = hours * rate
    setups = int(p.get("setups", 1))
    setup_cost = setups * 20.0
    penalty_cost = 0.0
    if violations:
        penalty_cost += 10.0 * len(violations)

    breakdown = CostBreakdown(
        material_cost=round(material_cost, 2),
        process_cost=round(process_cost, 2),
        setup_cost=round(setup_cost, 2),
        penalty_cost=round(penalty_cost, 2),
    )
    unit_cost = (breakdown.material_cost + breakdown.process_cost + breakdown.setup_cost + breakdown.penalty_cost) / max(quantity, 1.0)
    confidence = 0.8 if rules else 0.6
    return violations, [*suggestions], breakdown, round(confidence, 3)


def process_file(root: Path, path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    req = DFMAEvaluateRequest.model_validate(payload)
    violations, suggestions, breakdown, confidence = evaluate(req)
    unit_cost = (breakdown.material_cost + breakdown.process_cost + breakdown.setup_cost + breakdown.penalty_cost) / max(float(req.params.get("quantity", 1)), 1.0)
    result = DFMAEvaluateResponse(
        task_id=req.task_id,
        violations=violations,
        suggestions=suggestions,
        estimated_unit_cost=round(unit_cost, 2),
        breakdown=breakdown,
        confidence=confidence,
    ).model_dump(mode="json")
    wrapped = validate_and_wrap(
        raw=result,
        schema_model=DFMAEvaluateResponse,
        agent="dfma",
        version=os.getenv("AGENT_VERSION", "0.1.0"),
        code_sha=os.getenv("CODE_SHA", "dev"),
        started_at=time.time(),
        inputs_bytes=path.read_bytes(),
        schema_version=os.getenv("SCHEMA_VERSION", "resp-1.0"),
    )
    out_dir = root / "runs" / req.task_id / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out_dir / "dfma.json", wrapped)
    append_processed(root / "runs" / req.task_id, "dfma", wrapped.get("data_sha256", ""), wrapped.get("trace", {}).get("ids", {}).get("trace_id", ""))
    append_event(root / "artifacts" / "logs" / "events.ndjson", Event(
        task_id=req.task_id,
        agent="dfma",
        kind="completed",
        trace_id=wrapped.get("trace", {}).get("ids", {}).get("trace_id", ""),
        span_id=wrapped.get("trace", {}).get("ids", {}).get("span_id", ""),
        event="completed",
        monotonic_ms=float(wrapped.get("provenance", {}).get("monotonic_ms", 0.0)),
        data_sha256=wrapped.get("data_sha256", ""),
        blob_refs=wrapped.get("blob_refs", []),
        duration_ms=float(wrapped.get("provenance", {}).get("monotonic_ms", 0.0)),
        input_bytes=len(path.read_bytes()),
        output_bytes=len(json.dumps(wrapped).encode("utf-8")),
        result_size_bytes=len(json.dumps(wrapped.get("result", {})).encode("utf-8")),
    ))


def main() -> None:
    parser = argparse.ArgumentParser(description="AGENT_DFMA")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    root = Path(".").resolve()
    q = FSQueue(root / "queue" / "dfma" / "inbox", root / "queue" / "dfma" / "wip", root / "queue" / "dfma" / "out")

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
                if already_processed(task_dir, "dfma"):
                    append_event(root / "artifacts" / "logs" / "events.ndjson", Event(task_id=payload.get("task_id", "unknown"), agent="dfma", kind="skipped_duplicate", trace_id="dup", span_id="dup", event="skipped_duplicate", monotonic_ms=0.0, data_sha256="", blob_refs=[], message="duplicate detected via processed index"))
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


