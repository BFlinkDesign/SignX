from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from contracts.compliance import ComplianceCheckRequest, ComplianceCheckResponse
from svcs.common.fsqueue import FSQueue
from svcs.orchestrator.validate import validate_and_wrap, write_json_atomic
from svcs.common.index import already_processed, append_processed
from svcs.orchestrator.events import Event, append_event


RUNS_DIR = Path("runs")
DATA_DIR = Path("svcs/agent_compliance/data")


def _append_status(event: str, task_id: str, extra: Dict[str, Any] | None = None) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    record: Dict[str, Any] = {"task_id": task_id, "agent": "AGENT_COMPLIANCE", "event": event}
    if extra:
        record.update(extra)
    with STATUS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


@dataclass
class PatentAbs:
    id: str
    abstract: str


def load_patents() -> List[PatentAbs]:
    files = glob.glob(str(DATA_DIR / "patent_abstracts.csv"))
    rows: List[PatentAbs] = []
    for fp in files:
        with open(fp, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(PatentAbs(id=row.get("id", "unknown"), abstract=row.get("abstract", "")))
    if rows:
        return rows
    return [PatentAbs(id="p1", abstract="bracket with slots and holes for mounting"), PatentAbs(id="p2", abstract="press fit shaft hub assembly tolerance analysis")]


def ngrams(s: str, n: int = 3) -> set[str]:
    tokens = s.lower().split()
    return set(" ".join(tokens[i : i + n]) for i in range(max(0, len(tokens) - n + 1)))


def check_ip_similarity(text: str, patents: List[PatentAbs]) -> Tuple[bool, str]:
    tgrams = ngrams(text, 3)
    best = 0.0
    best_id = ""
    for p in patents:
        pgrams = ngrams(p.abstract, 3)
        if not pgrams or not tgrams:
            continue
        overlap = len(tgrams & pgrams) / len(tgrams)
        if overlap > best:
            best = overlap
            best_id = p.id
    return (best > 0.3), f"ip_overlap:{best_id}:{best:.2f}"


def standards_tags(context: str) -> List[str]:
    tags: List[str] = []
    if any(k in context.lower() for k in ["gd&t", "tolerance", "datum"]):
        tags.append("ASME Y14.5")
    return tags


def safety_checks(inputs: Dict[str, Any], outputs: Dict[str, Any]) -> Tuple[bool, str]:
    has_load = "load" in inputs or "loads" in inputs
    has_sf = "safety_factor" in outputs or "sf" in outputs
    if has_load and not has_sf:
        return True, "missing_safety_factor"
    return False, "ok"


def sign_checksum(obj: Dict[str, Any]) -> str:
    data = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def process_file(root: Path, path: Path) -> None:
    req = ComplianceCheckRequest.model_validate(json.loads(path.read_text(encoding="utf-8")))
    flags: List[str] = []
    audit: List[str] = []
    patents = load_patents()
    ip_flag, ip_meta = check_ip_similarity(req.context, patents)
    if ip_flag:
        flags.append("ip_overlap")
        audit.append(ip_meta)
    tags = standards_tags(req.context)
    if tags:
        audit.extend([f"std:{t}" for t in tags])
    safety_flag, safety_meta = safety_checks(req.inputs, req.outputs)
    if safety_flag:
        flags.append(safety_meta)
        audit.append("safety:missing_sf")
    severity = "high" if any(f in ("ip_overlap", "missing_safety_factor") for f in flags) else "low"
    actions: List[str] = []
    if "ip_overlap" in flags:
        actions.append("Perform patent counsel review.")
    if "missing_safety_factor" in flags:
        actions.append("Add explicit safety factor to outputs.")
    signed = sign_checksum({"inputs": req.inputs, "outputs": req.outputs})
    result = ComplianceCheckResponse(
        task_id=req.task_id,
        flags=flags,
        severity=severity,
        required_actions=actions,
        audit_trail=audit,
        signed_checksum=signed,
    ).model_dump(mode="json")
    wrapped = validate_and_wrap(
        raw=result,
        schema_model=ComplianceCheckResponse,
        agent="compliance",
        version=os.getenv("AGENT_VERSION", "0.1.0"),
        code_sha=os.getenv("CODE_SHA", "dev"),
        started_at=time.time(),
        inputs_bytes=path.read_bytes(),
        schema_version=os.getenv("SCHEMA_VERSION", "resp-1.0"),
    )
    out_dir = root / "runs" / req.task_id / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out_dir / "compliance.json", wrapped)
    append_processed(root / "runs" / req.task_id, "compliance", wrapped.get("data_sha256", ""), wrapped.get("trace", {}).get("ids", {}).get("trace_id", ""))
    append_event(root / "artifacts" / "logs" / "events.ndjson", Event(
        task_id=req.task_id,
        agent="compliance",
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
    parser = argparse.ArgumentParser(description="AGENT_COMPLIANCE")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    root = Path(".").resolve()
    q = FSQueue(root / "queue" / "compliance" / "inbox", root / "queue" / "compliance" / "wip", root / "queue" / "compliance" / "out")

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
                if already_processed(task_dir, "compliance"):
                    append_event(root / "artifacts" / "logs" / "events.ndjson", Event(task_id=payload.get("task_id", "unknown"), agent="compliance", kind="skipped_duplicate", trace_id="dup", span_id="dup", event="skipped_duplicate", monotonic_ms=0.0, data_sha256="", blob_refs=[], message="duplicate detected via processed index"))
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


