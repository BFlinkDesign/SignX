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

from contracts.materials import (
    MaterialPickRequest,
    MaterialPickResponse,
    Recommendation,
    Contribution,
)
from svcs.common.fsqueue import FSQueue
from svcs.orchestrator.validate import validate_and_wrap, write_json_atomic
from svcs.common.index import already_processed, append_processed
from svcs.orchestrator.events import Event, append_event
import logging

logger = logging.getLogger(__name__)

RUNS_DIR = Path("runs")
STATUS_PATH = RUNS_DIR / "status.jsonl"

DATA_DIR = Path("svcs/agent_materials/data")


def _append_status(event: str, task_id: str, extra: Dict[str, Any] | None = None) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    record: Dict[str, Any] = {"task_id": task_id, "agent": "AGENT_MATERIALS", "event": event}
    if extra:
        record.update(extra)
    with STATUS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


@dataclass
class Candidate:
    name: str
    yield_mpa: float
    cost_index: float  # arbitrary relative index, lower is cheaper
    corrosion_ordinal: int  # higher is better qualitatively
    source: str


def load_candidates() -> List[Candidate]:
    files = glob.glob(str(DATA_DIR / "*.csv"))
    candidates: List[Candidate] = []
    for fp in files:
        with open(fp, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    candidates.append(
                        Candidate(
                            name=row.get("name", "unknown"),
                            yield_mpa=float(row["yield_mpa"]),
                            cost_index=float(row["cost_index"]),
                            corrosion_ordinal=int(row.get("corrosion_ordinal", 3)),
                            source=row.get("source", fp),
                        )
                    )
                except Exception as e:
                    logger.warning("Exception in main.py: %s", str(e))
                    continue
    if candidates:
        return candidates
    # Fallback synthesized dataset
    return [
        Candidate("6061-T6 Al", 275.0, 1.0, 3, "synth"),
        Candidate("7075-T6 Al", 505.0, 1.5, 2, "synth"),
        Candidate("304 SS", 215.0, 1.8, 4, "synth"),
        Candidate("316L SS", 170.0, 2.0, 5, "synth"),
        Candidate("Ti-6Al-4V", 830.0, 5.0, 4, "synth"),
    ]


def _min_max(values: List[float]) -> Tuple[float, float]:
    vmin = min(values)
    vmax = max(values)
    return vmin, vmax if vmax != vmin else (vmin, vmin + 1.0)


def score_candidates(req: MaterialPickRequest, cands: List[Candidate]) -> Tuple[List[Recommendation], List[Contribution], float, List[str], List[str]]:
    # Normalize weights
    w_cost = req.weights.cost
    w_strength = req.weights.strength
    w_cor = req.weights.corrosion
    total_w = max(w_cost + w_strength + w_cor, 1e-9)
    w_cost /= total_w
    w_strength /= total_w
    w_cor /= total_w

    ys = [c.yield_mpa for c in cands]
    cs = [c.cost_index for c in cands]
    qs = [c.corrosion_ordinal for c in cands]
    y_min, y_max = min(ys), max(ys)
    c_min, c_max = min(cs), max(cs)
    q_min, q_max = min(qs), max(qs)

    recs: List[Recommendation] = []
    prov: List[str] = []
    for c in cands:
        # Normalize to [0,100]
        y_norm = 0.0 if y_max == y_min else 100.0 * (c.yield_mpa - y_min) / (y_max - y_min)
        # Cost lower is better
        c_norm = 0.0 if c_max == c_min else 100.0 * (c_max - c.cost_index) / (c_max - c_min)
        q_norm = 0.0 if q_max == q_min else 100.0 * (c.corrosion_ordinal - q_min) / (q_max - q_min)
        score = w_strength * y_norm + w_cost * c_norm + w_cor * q_norm
        constraints: List[str] = []
        if req.min_yield_mpa is not None and c.yield_mpa >= req.min_yield_mpa:
            constraints.append("min_yield_mpa")
        if any("corrosion" in k.lower() for k in req.key_requirements):
            constraints.append("corrosion_considered")
        recs.append(
            Recommendation(
                material=c.name,
                score=round(score, 3),
                reason="weighted sum of normalized properties",
                constraints_satisfied=constraints,
            )
        )
        prov.append(c.source)

    recs.sort(key=lambda r: r.score, reverse=True)

    # Contributions are global, reported for top candidate
    top = recs[0]
    top_c = next(c for c in cands if c.name == top.material)
    y_norm_top = 0.0 if y_max == y_min else 100.0 * (top_c.yield_mpa - y_min) / (y_max - y_min)
    c_norm_top = 0.0 if c_max == c_min else 100.0 * (c_max - top_c.cost_index) / (c_max - c_min)
    q_norm_top = 0.0 if q_max == q_min else 100.0 * (top_c.corrosion_ordinal - q_min) / (q_max - q_min)
    contributions = [
        Contribution(property="strength", weight=round(w_strength, 3), normalized_value=round(y_norm_top, 3), contribution=round(w_strength * y_norm_top, 3)),
        Contribution(property="cost", weight=round(w_cost, 3), normalized_value=round(c_norm_top, 3), contribution=round(w_cost * c_norm_top, 3)),
        Contribution(property="corrosion", weight=round(w_cor, 3), normalized_value=round(q_norm_top, 3), contribution=round(w_cor * q_norm_top, 3)),
    ]

    # Confidence heuristic
    coverage = 0
    if req.min_yield_mpa is not None:
        coverage += 1
    if req.key_requirements:
        coverage += 1
    coverage_ratio = coverage / 2.0
    top3 = recs[:3]
    spread = 0.0 if len(top3) < 2 else max(r.score for r in top3) - min(r.score for r in top3)
    spread_factor = 1.0 if spread > 10 else spread / 10.0
    prov_factor = 1.0 if any(p != "synth" for p in prov) else 0.6
    confidence = max(0.0, min(1.0, 0.3 * coverage_ratio + 0.4 * spread_factor + 0.3 * prov_factor))

    caveats: List[str] = []
    if all(p == "synth" for p in prov):
        caveats.append("Using synthesized material dataset; results illustrative.")

    return recs[:5], contributions, round(confidence, 3), caveats, list(dict.fromkeys(prov))


def process_file(root: Path, path: Path) -> None:
    raw_bytes = path.read_bytes()
    payload = json.loads(raw_bytes)
    req = MaterialPickRequest.model_validate(payload)
    cands = load_candidates()
    recs, contributions, confidence, caveats, provenance = score_candidates(req, cands)
    result = MaterialPickResponse(
        task_id=req.task_id,
        top_recommendations=recs,
        contributions=contributions,
        confidence=confidence,
        caveats=caveats,
        provenance=provenance,
    ).model_dump(mode="json")
    started = time.time()
    wrapped = validate_and_wrap(
        raw=result,
        schema_model=MaterialPickResponse,
        agent="materials",
        version=os.getenv("AGENT_VERSION", "0.1.0"),
        code_sha=os.getenv("CODE_SHA", "dev"),
        started_at=started,
        inputs_bytes=raw_bytes,
        schema_version=os.getenv("SCHEMA_VERSION", "resp-1.0"),
    )
    out_dir = root / "runs" / req.task_id / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out_dir / "materials.json", wrapped)
    append_processed(root / "runs" / req.task_id, "materials", wrapped.get("data_sha256", ""), wrapped.get("trace", {}).get("ids", {}).get("trace_id", ""))
    append_event(root / "artifacts" / "logs" / "events.ndjson", Event(
        task_id=req.task_id,
        agent="materials",
        kind="completed",
        trace_id=wrapped.get("trace", {}).get("ids", {}).get("trace_id", ""),
        span_id=wrapped.get("trace", {}).get("ids", {}).get("span_id", ""),
        event="completed",
        monotonic_ms=float(wrapped.get("provenance", {}).get("monotonic_ms", 0.0)),
        data_sha256=wrapped.get("data_sha256", ""),
        blob_refs=wrapped.get("blob_refs", []),
        duration_ms=float(wrapped.get("provenance", {}).get("monotonic_ms", 0.0)),
        input_bytes=len(raw_bytes),
        output_bytes=len(json.dumps(wrapped).encode("utf-8")),
        result_size_bytes=len(json.dumps(wrapped.get("result", {})).encode("utf-8")),
    ))


def main() -> None:
    parser = argparse.ArgumentParser(description="AGENT_MATERIALS")
    parser.add_argument("--once", action="store_true", help="Process existing inbox once and exit")
    args = parser.parse_args()

    root = Path(".").resolve()
    inbox = root / "queue" / "materials" / "inbox"
    wip = root / "queue" / "materials" / "wip"
    out = root / "queue" / "materials" / "out"
    q = FSQueue(inbox, wip, out)

    def process_all() -> int:
        count = 0
        for p in q.poll():
            try:
                wip_file, fd, lock_path = q.claim(p)
            except RuntimeError:
                continue
            try:
                # preflight duplicate skip
                payload = json.loads(wip_file.read_text(encoding="utf-8"))
                task_dir = root / "runs" / payload.get("task_id", "unknown")
                if already_processed(task_dir, "materials"):
                    append_event(root / "artifacts" / "logs" / "events.ndjson", Event(
                        task_id=payload.get("task_id", "unknown"), agent="materials", kind="skipped_duplicate", trace_id="dup", span_id="dup", event="skipped_duplicate", monotonic_ms=0.0, data_sha256="", blob_refs=[], message="duplicate detected via processed index"
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


