from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
import logging

logger = logging.getLogger(__name__)


EXIT_OK = 0
EXIT_INTEGRITY = 2
EXIT_ORDERING = 4


TRACE_ID_RE = re.compile(r"^(?:[0-9a-fA-F]{16}|[0-9a-fA-F]{32}|[0-9a-fA-F-]{36})$")
MAX_REASONABLE_SECONDS = 24 * 60 * 60


def read_events(events_path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not events_path.exists():
        return events
    with events_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                # malformed lines count as integrity errors later
                events.append({"__malformed__": line})
    return events


# Use shared utility if available, otherwise keep local implementation
try:
    from packages.utils import sha256_file
except ImportError:
    def sha256_file(p: Path) -> str:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()


def verify_task(task: str, base_dir: Path) -> int:
    runs_dir = base_dir / "runs" / task
    out_dir = runs_dir / "out"
    events_path = runs_dir / "events.ndjson"

    exit_code = EXIT_OK

    # 1) Sentinel .tmp detection
    tmp_files = list(out_dir.rglob("*.tmp")) if out_dir.exists() else []
    if tmp_files:
        print(json.dumps({
            "code": EXIT_INTEGRITY,
            "error": "tmp_files_present",
            "files": [str(p) for p in tmp_files]
        }, indent=2))
        return EXIT_INTEGRITY

    # 2) Load events
    events = read_events(events_path)

    # 3) Trace ID + duration sanity + malformed detection
    for idx, ev in enumerate(events):
        if "__malformed__" in ev:
            print(json.dumps({
                "code": EXIT_INTEGRITY,
                "error": "malformed_event",
                "line": idx + 1,
                "content": ev["__malformed__"]
            }, indent=2))
            return EXIT_INTEGRITY
        trace_id = ev.get("trace_id")
        if trace_id is not None and not TRACE_ID_RE.match(str(trace_id)):
            print(json.dumps({
                "code": EXIT_INTEGRITY,
                "error": "bad_trace_id",
                "line": idx + 1,
                "trace_id": trace_id
            }, indent=2))
            return EXIT_INTEGRITY
        started = ev.get("started_at")
        ended = ev.get("ended_at")
        if started is not None and ended is not None:
            try:
                # Support ms or s
                dur = float(ended) - float(started)
                if dur > 10_000:  # interpret as ms
                    dur /= 1000.0
                if dur < 0 or dur > MAX_REASONABLE_SECONDS:
                    print(json.dumps({
                        "code": EXIT_INTEGRITY,
                        "error": "bad_duration",
                        "line": idx + 1,
                        "duration_s": dur
                    }, indent=2))
                    return EXIT_INTEGRITY
            except Exception as e:
                logger.warning("Exception in main.py: %s", str(e))
                pass

    # 4) Event ordering by agent on wall_ts
    by_agent: dict[str, float] = {}
    for idx, ev in enumerate(events):
        agent = str(ev.get("agent", ""))
        ts = ev.get("wall_ts")
        if ts is None:
            continue
        try:
            ts_f = float(ts)
        except Exception as e:
            logger.warning("Exception in main.py: %s", str(e))
            continue
        if agent in by_agent and ts_f < by_agent[agent]:
            print(json.dumps({
                "code": EXIT_ORDERING,
                "error": "non_monotonic_wall_ts",
                "agent": agent,
                "prev_ts": by_agent[agent],
                "ts": ts_f,
                "line": idx + 1
            }, indent=2))
            return EXIT_ORDERING
        by_agent[agent] = ts_f

    # 5) CAS tamper detection (optional fields)
    # Expect events referencing blobs as {"blob_path": "cas/..", "blob_sha256": "..."}
    for idx, ev in enumerate(events):
        bp = ev.get("blob_path")
        sh = ev.get("blob_sha256")
        if not bp or not sh:
            continue
        p = (runs_dir / bp).resolve()
        if p.exists():
            calc = sha256_file(p)
            if calc.lower() != str(sh).lower():
                print(json.dumps({
                    "code": EXIT_INTEGRITY,
                    "error": "blob_sha_mismatch",
                    "path": str(p),
                    "calc": calc,
                    "exp": sh,
                    "line": idx + 1
                }, indent=2))
                return EXIT_INTEGRITY

    logger.info(json.dumps({"ok": True, "task": task}, indent=2))
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", dest="verify", help="Task ID to verify", default=None)
    ap.add_argument("--base", dest="base", help="Base project directory", default=str(Path(__file__).resolve().parents[2]))
    args = ap.parse_args()

    base_dir = Path(args.base)
    if args.verify:
        return verify_task(args.verify, base_dir)

    ap.print_help()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())


