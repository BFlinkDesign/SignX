from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from contracts.cad import CADMacroRequest, CADMacroResponse
from svcs.common.fsqueue import FSQueue
from svcs.orchestrator.validate import validate_and_wrap, write_json_atomic, store_blob
from svcs.common.index import already_processed, append_processed
from svcs.orchestrator.events import Event, append_event


RUNS_DIR = Path("runs")
ART_DIR = Path("artifacts/cad")


def _append_status(event: str, task_id: str, extra: Dict[str, Any] | None = None) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    record: Dict[str, Any] = {"task_id": task_id, "agent": "AGENT_CAD", "event": event}
    if extra:
        record.update(extra)
    with STATUS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


def build_freecad_script(req: CADMacroRequest) -> str:
    ops = []
    ops.append("import FreeCAD, Part\n")
    ops.append("doc = FreeCAD.newDocument('APEX_' + str('%s'))\n" % req.task_id)
    ops.append("# create base sketch/solid\n")
    ops.append("box = Part.makeBox(10,10,1)\n")
    ops.append("shape = box\n")
    for p in req.primitives:
        if p == "pad":
            ops.append("shape = shape.extrude(FreeCAD.Vector(0,0,5))\n")
        elif p == "pocket":
            ops.append("# pocket simulated by cut\n")
            ops.append("cyl = Part.makeCylinder(2,5)\n")
            ops.append("shape = shape.cut(cyl)\n")
        elif p == "fillet":
            ops.append("shape = shape.makeFillet(0.5, shape.Edges)\n")
    ops.append("Part.show(shape)\n")
    ops.append("doc.recompute()\n")
    ops.append("# save artifacts (paths controlled by orchestrator runtime)\n")
    ops.append("# doc.saveAs('/artifacts/cad/%s.FCStd')\n" % req.task_id)
    return "".join(ops)


def process_file(root: Path, path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    req = CADMacroRequest.model_validate(payload)
    if req.target != "freecad":
        raise ValueError("Only freecad target supported in v0")
    ART_DIR.mkdir(parents=True, exist_ok=True)
    script_text = build_freecad_script(req)
    script_bytes = script_text.encode("utf-8")
    blob_sha = store_blob(root, script_bytes, "py")
    script_path = ART_DIR / f"{req.task_id}.py"
    script_path.write_bytes(script_bytes)
    result = CADMacroResponse(
        task_id=req.task_id,
        script_path=str(script_path),
        features=req.primitives,
        params=[f for f in req.dims.keys()],
        preview_notes=[f"script_blob_sha256={blob_sha}"]
    ).model_dump(mode="json")
    wrapped = validate_and_wrap(
        raw=result,
        schema_model=CADMacroResponse,
        agent="cad",
        version=os.getenv("AGENT_VERSION", "0.1.0"),
        code_sha=os.getenv("CODE_SHA", "dev"),
        started_at=time.time(),
        inputs_bytes=path.read_bytes(),
        schema_version=os.getenv("SCHEMA_VERSION", "resp-1.0"),
        blob_refs=[{"sha256": blob_sha, "ext": "py"}],
    )
    out_dir = root / "runs" / req.task_id / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out_dir / "cad.json", wrapped)
    append_processed(root / "runs" / req.task_id, "cad", wrapped.get("data_sha256", ""), wrapped.get("trace", {}).get("ids", {}).get("trace_id", ""))
    append_event(root / "artifacts" / "logs" / "events.ndjson", Event(
        task_id=req.task_id,
        agent="cad",
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
    parser = argparse.ArgumentParser(description="AGENT_CAD")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    root = Path(".").resolve()
    q = FSQueue(root / "queue" / "cad" / "inbox", root / "queue" / "cad" / "wip", root / "queue" / "cad" / "out")

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
                if already_processed(task_dir, "cad"):
                    append_event(root / "artifacts" / "logs" / "events.ndjson", Event(task_id=payload.get("task_id", "unknown"), agent="cad", kind="skipped_duplicate", trace_id="dup", span_id="dup", event="skipped_duplicate", monotonic_ms=0.0, data_sha256="", blob_refs=[], message="duplicate detected via processed index"))
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


