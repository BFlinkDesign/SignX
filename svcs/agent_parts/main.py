from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from contracts.parts import PartsQueryRequest, PartsQueryResponse, PartMatch
from svcs.common.fsqueue import FSQueue
from svcs.orchestrator.validate import validate_and_wrap, write_json_atomic
from svcs.common.index import already_processed, append_processed
from svcs.orchestrator.events import Event, append_event


RUNS_DIR = Path("runs")
DATA_DIR = Path("svcs/agent_parts/data")


def _append_status(event: str, task_id: str, extra: Dict[str, Any] | None = None) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    record: Dict[str, Any] = {"task_id": task_id, "agent": "AGENT_PARTS", "event": event}
    if extra:
        record.update(extra)
    with STATUS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


@dataclass
class CatalogRow:
    dataset_path: str
    row_id: int
    data: Dict[str, Any]


def load_catalogs() -> List[CatalogRow]:
    rows: List[CatalogRow] = []
    files = glob.glob(str(DATA_DIR / "*.csv"))
    for fp in files:
        with open(fp, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                rows.append(CatalogRow(dataset_path=fp, row_id=i, data=row))
    if rows:
        return rows
    # fallback minimal catalog
    fallback = [
        {"part_id": "M6x20_hex_steel_zinc", "thread": "M6", "length_mm": "20", "material": "steel", "finish": "zinc", "price": "0.05"},
        {"part_id": "M6x25_hex_steel_zinc", "thread": "M6", "length_mm": "25", "material": "steel", "finish": "zinc", "price": "0.06"},
        {"part_id": "M6x20_hex_ss304", "thread": "M6", "length_mm": "20", "material": "304SS", "finish": "plain", "price": "0.09"},
    ]
    return [CatalogRow(dataset_path="synth", row_id=i, data=r) for i, r in enumerate(fallback)]


def tokens(s: str) -> set[str]:
    return set(s.lower().replace("_", " ").replace("-", " ").split())


def rank(req: PartsQueryRequest, rows: List[CatalogRow]) -> List[PartMatch]:
    hard = {k.lower(): str(v).lower() for k, v in req.hard_constraints.items()}
    soft = {k.lower(): str(v).lower() for k, v in req.soft_constraints.items()}
    query_tokens = tokens(req.query)

    matches: List[Tuple[float, CatalogRow]] = []
    for r in rows:
        data_l = {k.lower(): str(v).lower() for k, v in r.data.items()}
        # hard constraints exact match
        hard_ok = all(data_l.get(k) == v for k, v in hard.items())
        if not hard_ok:
            continue
        score = 0.0
        for k, v in soft.items():
            if data_l.get(k) == v:
                score += 10.0
        # fuzzy title/id matching
        id_tokens = tokens(r.data.get("part_id", ""))
        overlap = len(query_tokens & id_tokens)
        score += overlap * 1.0
        # price tie-breaker
        try:
            price = float(r.data.get("price", "1.0"))
        except Exception:
            price = 1.0
        score += max(0.0, 1.0 - price)
        matches.append((score, r))

    matches.sort(key=lambda x: x[0], reverse=True)
    out: List[PartMatch] = []
    for score, r in matches[:5]:
        out.append(
            PartMatch(
                part_id=str(r.data.get("part_id", f"row{r.row_id}")),
                score=round(score, 3),
                specs=r.data,
                dataset_path=r.dataset_path,
                row_id=r.row_id,
            )
        )
    return out


def process_file(root: Path, path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    req = PartsQueryRequest.model_validate(payload)
    rows = load_catalogs()
    top = rank(req, rows)
    coverage = 0
    if req.hard_constraints:
        coverage += 1
    if req.soft_constraints:
        coverage += 1
    confidence = 0.6 + 0.2 * (coverage / 2.0)
    result = PartsQueryResponse(
        task_id=req.task_id,
        top_matches=top,
        normalized_spec={},
        retrieval_provenance=[f"{m.dataset_path}#{m.row_id}" for m in top],
        confidence=round(confidence, 3),
    ).model_dump(mode="json")
    wrapped = validate_and_wrap(
        raw=result,
        schema_model=PartsQueryResponse,
        agent="parts",
        version=os.getenv("AGENT_VERSION", "0.1.0"),
        code_sha=os.getenv("CODE_SHA", "dev"),
        started_at=time.time(),
        inputs_bytes=path.read_bytes(),
        schema_version=os.getenv("SCHEMA_VERSION", "resp-1.0"),
    )
    out_dir = root / "runs" / req.task_id / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out_dir / "parts.json", wrapped)
    append_processed(root / "runs" / req.task_id, "parts", wrapped.get("data_sha256", ""), wrapped.get("trace", {}).get("ids", {}).get("trace_id", ""))
    append_event(root / "artifacts" / "logs" / "events.ndjson", Event(
        task_id=req.task_id,
        agent="parts",
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
    parser = argparse.ArgumentParser(description="AGENT_PARTS")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    root = Path(".").resolve()
    q = FSQueue(root / "queue" / "parts" / "inbox", root / "queue" / "parts" / "wip", root / "queue" / "parts" / "out")

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
                if already_processed(task_dir, "parts"):
                    append_event(root / "artifacts" / "logs" / "events.ndjson", Event(task_id=payload.get("task_id", "unknown"), agent="parts", kind="skipped_duplicate", trace_id="dup", span_id="dup", event="skipped_duplicate", monotonic_ms=0.0, data_sha256="", blob_refs=[], message="duplicate detected via processed index"))
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


