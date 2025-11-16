from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from contracts.eval import EvalRunRequest, EvalRunResponse, Metric


RUNS_DIR = Path("runs")
OUTBOX_DIR = RUNS_DIR / "outbox"  # keep for response placement
STATUS_PATH = RUNS_DIR / "status.jsonl"
ART_DIR = Path("artifacts/eval")
GOLDEN_DIR = Path("tests/e2e/golden")
QUEUE_DIR = Path("queue")


def _append_status(event: str, task_id: str, extra: Dict[str, Any] | None = None) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    record: Dict[str, Any] = {"task_id": task_id, "agent": "AGENT_EVAL", "event": event}
    if extra:
        record.update(extra)
    with STATUS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


def drop_payload(agent: str, task_id: str, payload: dict) -> None:
    inbox = QUEUE_DIR / agent / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / f"{task_id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def wait_for_response(task_id: str, agent: str, timeout_s: float = 10.0) -> dict | None:
    deadline = time.time() + timeout_s
    outname = f"{task_id}__{agent}__response.json"
    while time.time() < deadline:
        path = OUTBOX_DIR / outname
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        time.sleep(0.2)
    return None


def run_suite() -> EvalRunResponse:
    # For now, synthesize a small suite using orchestrator demo tasks semantics
    tasks = [
        ("materials", "eval-mat-1", {
            "task_id": "eval-mat-1",
            "application": "outdoor bracket",
            "key_requirements": ["corrosion"],
            "min_yield_mpa": 200.0,
            "weights": {"cost": 0.3, "strength": 0.5, "corrosion": 0.2}
        }),
        ("stackup", "eval-stk-1", {
            "task_id": "eval-stk-1",
            "description": "press fit",
            "features": [
                {"name": "a", "nominal": 10.0, "tol_plus": 0.1, "tol_minus": 0.1, "distribution": "normal"},
                {"name": "b", "nominal": 5.0, "tol_plus": 0.1, "tol_minus": 0.1, "distribution": "normal"}
            ],
            "sample_size": 10000,
            "lower_spec": None,
            "upper_spec": None
        }),
        ("dfma", "eval-dfma-1", {
            "task_id": "eval-dfma-1",
            "description": "sheet metal bracket",
            "process": "sheet_metal",
            "params": {"r_over_t": 1.0, "hole_edge_multiple": 1.5, "quantity": 100}
        })
    ]
    for agent, tid, payload in tasks:
        drop_payload(agent, tid, payload)

    # Wait for all
    ok = 0
    for agent, tid, _ in tasks:
        if wait_for_response(tid, agent) is not None:
            ok += 1

    metrics = [
        Metric(name="agents_success", value=float(ok / len(tasks))),
        Metric(name="latency_placeholder", value=0.0),
    ]
    report = ART_DIR / f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
    ART_DIR.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join([
        "# Eval Report",
        f"Agents success: {ok}/{len(tasks)}",
    ]), encoding="utf-8")
    return EvalRunResponse(task_id="eval-run", metrics=metrics, artifacts=[str(report)], failed=ok != len(tasks))


def process_one_envelope(path: Path) -> bool:
    env = json.loads(path.read_text(encoding="utf-8"))
    if env.get("agent") != "AGENT_EVAL" or env.get("type") != "EvalRunRequest":
        return False
    req = EvalRunRequest.model_validate(env["payload"])
    resp = run_suite()
    out_path = OUTBOX_DIR / f"{req.task_id}__AGENT_EVAL__response.json"
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(resp.model_dump_json(indent=2), encoding="utf-8")
    if resp.failed:
        _append_status("FAIL", req.task_id, {"artifacts": resp.artifacts})
    else:
        _append_status("completed", req.task_id, {"artifacts": resp.artifacts})
    processed_dir = path.parent / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    path.rename(processed_dir / path.name)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="AGENT_EVAL")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    def process_all() -> int:
        count = 0
        for p in sorted(INBOX_DIR.glob("*.json")):
            try:
                if process_one_envelope(p):
                    count += 1
            except Exception as e:
                _append_status("error", json.loads(p.read_text()).get("task_id", "unknown"), {"error": str(e)})
        return count

    if args.once:
        process_all()
    else:
        while True:
            n = process_all()
            time.sleep(1.0 if n == 0 else 0.1)


if __name__ == "__main__":
    main()


