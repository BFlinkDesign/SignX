from __future__ import annotations

import argparse
import csv
import json
import math
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

from contracts.stackup import StackupAnalyzeRequest, StackupAnalyzeResponse, HistogramBucket
from svcs.common.fsqueue import FSQueue
from svcs.orchestrator.validate import validate_and_wrap, write_json_atomic, store_blob
from svcs.common.index import already_processed, append_processed
from svcs.orchestrator.events import Event, append_event


RUNS_DIR = Path("runs")
STATUS_PATH = RUNS_DIR / "status.jsonl"
ART_DIR = Path("artifacts/stackup")


def _append_status(event: str, task_id: str, extra: Dict[str, Any] | None = None) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    record: Dict[str, Any] = {"task_id": task_id, "agent": "AGENT_STACKUP", "event": event}
    if extra:
        record.update(extra)
    with STATUS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


def cp_cpk(mean: float, sigma: float, lower: float | None, upper: float | None) -> Tuple[float | None, float | None]:
    if sigma <= 0 or (lower is None and upper is None):
        return None, None
    limits = []
    if lower is not None:
        limits.append((mean - lower) / (3 * sigma))
    if upper is not None:
        limits.append((upper - mean) / (3 * sigma))
    if not limits:
        return None, None
    cpk = min(limits)
    if lower is not None and upper is not None:
        cp = (upper - lower) / (6 * sigma)
    else:
        cp = None
    return cp, cpk


def simulate_stackup(req: StackupAnalyzeRequest) -> Tuple[np.ndarray, float, float, float | None, float | None, float | None, List[HistogramBucket], List[str]]:
    rng = np.random.default_rng(abs(hash(req.task_id)) % (2**32))
    # Worst-case and RSS
    nominal_sum = sum(f.nominal for f in req.features)
    worst_max = nominal_sum + sum(f.tol_plus for f in req.features)
    worst_min = nominal_sum - sum(f.tol_minus for f in req.features)
    rss_sigma = math.sqrt(sum(((f.tol_plus + f.tol_minus) / 2.0 / 3.0) ** 2 for f in req.features))

    # Monte Carlo
    n = min(req.sample_size, 50000)
    samples = np.zeros(n)
    for i, f in enumerate(req.features):
        if f.distribution == "normal":
            sigma = ((f.tol_plus + f.tol_minus) / 2.0) / 3.0
            samples += rng.normal(loc=f.nominal, scale=sigma, size=n)
        else:
            # uniform within +/- tol; model tol as symmetric using average
            half = (f.tol_plus + f.tol_minus) / 2.0
            samples += rng.uniform(low=f.nominal - half, high=f.nominal + half, size=n)

    mean = float(np.mean(samples))
    sigma = float(np.std(samples, ddof=1))
    cp, cpk = cp_cpk(mean, sigma, req.lower_spec, req.upper_spec)

    pass_prob = None
    if req.lower_spec is not None or req.upper_spec is not None:
        ok = np.ones(n, dtype=bool)
        if req.lower_spec is not None:
            ok &= samples >= req.lower_spec
        if req.upper_spec is not None:
            ok &= samples <= req.upper_spec
        pass_prob = float(np.mean(ok))

    # histogram summary (fixed bin count)
    bins = 20
    counts, edges = np.histogram(samples, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2.0
    histogram = [HistogramBucket(bin_center=float(c), count=int(nc)) for c, nc in zip(centers, counts)]

    assumptions: List[str] = []
    if any(f.tol_plus == 0 and f.tol_minus == 0 for f in req.features):
        assumptions.append("Zero tolerance feature treated as nominal-only.")

    return samples, mean, sigma, cp, cpk, pass_prob, histogram, assumptions


def process_file(root: Path, path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    req = StackupAnalyzeRequest.model_validate(payload)
    samples, mean, sigma, cp, cpk, pass_prob, histogram, assumptions = simulate_stackup(req)

    # store CSV as content-addressed blob and reference in assumptions
    ART_DIR.mkdir(parents=True, exist_ok=True)
    csv_bytes = ("value\n" + "\n".join(f"{float(v):.8f}" for v in samples[:50000])).encode("utf-8")
    blob_sha = store_blob(root, csv_bytes, "csv")
    assumptions.append(f"samples_csv_sha256={blob_sha}")

    result = StackupAnalyzeResponse(
        task_id=req.task_id,
        mean=mean,
        sigma=sigma,
        cpk=cpk,
        ppk=None,
        pass_prob=pass_prob,
        histogram=histogram,
        assumptions=assumptions,
        confidence=0.9 if req.sample_size >= 10000 else 0.7,
    ).model_dump(mode="json")

    started = time.time()
    wrapped = validate_and_wrap(
        raw=result,
        schema_model=StackupAnalyzeResponse,
        agent="stackup",
        version=os.getenv("AGENT_VERSION", "0.1.0"),
        code_sha=os.getenv("CODE_SHA", "dev"),
        started_at=started,
        inputs_bytes=path.read_bytes(),
        schema_version=os.getenv("SCHEMA_VERSION", "resp-1.0"),
        blob_refs=[{"sha256": blob_sha, "ext": "csv"}],
    )
    out_dir = root / "runs" / req.task_id / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out_dir / "stackup.json", wrapped)
    append_processed(root / "runs" / req.task_id, "stackup", wrapped.get("data_sha256", ""), wrapped.get("trace", {}).get("ids", {}).get("trace_id", ""))
    append_event(root / "artifacts" / "logs" / "events.ndjson", Event(
        task_id=req.task_id,
        agent="stackup",
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
    parser = argparse.ArgumentParser(description="AGENT_STACKUP")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    root = Path(".").resolve()
    q = FSQueue(root / "queue" / "stackup" / "inbox", root / "queue" / "stackup" / "wip", root / "queue" / "stackup" / "out")

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
                if already_processed(task_dir, "stackup"):
                    append_event(root / "artifacts" / "logs" / "events.ndjson", Event(task_id=payload.get("task_id", "unknown"), agent="stackup", kind="skipped_duplicate", trace_id="dup", span_id="dup", event="skipped_duplicate", monotonic_ms=0.0, data_sha256="", blob_refs=[], message="duplicate detected via processed index"))
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


