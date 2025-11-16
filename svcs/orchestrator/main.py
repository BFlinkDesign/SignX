from __future__ import annotations

import argparse
import hashlib
import json
import os
import textwrap
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Dict

from pydantic import BaseModel

import contracts
from contracts.materials import MaterialPickRequest, WeightVector
from contracts.stackup import StackupAnalyzeRequest, Feature
from contracts.dfma import DFMAEvaluateRequest
import logging

logger = logging.getLogger(__name__)


RUNS_DIR = Path("runs")
STATUS_PATH = RUNS_DIR / "status.jsonl"

ARTIFACTS_DIR = Path("artifacts")
SCHEMAS_DIR = ARTIFACTS_DIR / "schemas"
ORCH_ART_DIR = ARTIFACTS_DIR / "orchestrator"
EVENTS_LOG = ARTIFACTS_DIR / "logs" / "events.ndjson"
QUEUE_DIR = Path("queue")
EXIT_OK = 0
EXIT_INTEGRITY = 2
EXIT_COMPLETENESS = 3
EXIT_ORDERING = 4
TRACE_ID_RE = re.compile(r"^[a-f0-9\-]{16,36}$")


@dataclass
class Envelope:
    task_id: str
    agent: str
    type: str
    payload: Dict[str, Any]


def _ensure_dirs() -> None:
    for p in [SCHEMAS_DIR, ORCH_ART_DIR, EVENTS_LOG.parent, QUEUE_DIR]:
        p.mkdir(parents=True, exist_ok=True)


def _append_status(event: str, task_id: str, agent: str, extra: Dict[str, Any] | None = None) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    record: Dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "agent": agent,
        "event": event,
    }
    if extra:
        record.update(extra)
    with STATUS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


def export_json_schemas() -> None:
    """Export JSON Schemas for all contracts into artifacts/schemas."""
    modules = [
        contracts.materials,
        contracts.stackup,
        contracts.dfma,
        contracts.cad,
        contracts.parts,
        contracts.compliance,
        contracts.eval,
        contracts.signs,
    ]
    for mod in modules:
        for name, schema in mod.schemas().items():
            out_path = SCHEMAS_DIR / f"{name}.json"
            out_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")


def _enqueue_payload(agent: str, task_id: str, payload: dict) -> Path:
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()[:16]
    inbox = QUEUE_DIR / agent.lower() / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    filename = f"{task_id}__{payload_hash}.json"
    path = inbox / filename
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _append_status("enqueued", task_id, agent, {"hash": payload_hash, "queue": str(inbox)})
    # create per-task run dir and status log
    tdir = RUNS_DIR / task_id
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / "status.log").open("a", encoding="utf-8").write(f"{datetime.now(timezone.utc).timestamp():.3f} orchestrator enqueued {agent}\n")
    return path


def enqueue_demo_tasks() -> None:
    """Create and enqueue three demo task envelopes."""
    # 1) MaterialPickRequest
    m_task = MaterialPickRequest(
        task_id="demo-materials-1",
        application="Al 6061 bracket for outdoor use",
        key_requirements=["outdoor corrosion"],
        min_yield_mpa=240.0,
        weights=WeightVector(cost=0.3, strength=0.5, corrosion=0.2),
    )
    _enqueue_payload("materials", m_task.task_id, json.loads(m_task.model_dump_json()))

    # 2) StackupAnalyzeRequest
    s_task = StackupAnalyzeRequest(
        task_id="demo-stackup-1",
        description="shaft-hub press fit",
        features=[
            Feature(name="shaft_d", nominal=20.0, tol_plus=0.01, tol_minus=0.01, distribution="normal"),
            Feature(name="hub_bore", nominal=19.98, tol_plus=0.01, tol_minus=0.01, distribution="normal"),
        ],
        sample_size=10000,
        lower_spec=None,
        upper_spec=None,
    )
    _enqueue_payload("stackup", s_task.task_id, json.loads(s_task.model_dump_json()))

    # 3) DFMAEvaluateRequest
    d_task = DFMAEvaluateRequest(
        task_id="demo-dfma-1",
        description="sheet metal L-bracket",
        process="sheet_metal",
        params={"r_over_t": 1.0, "gauge_mm": 2.0, "quantity": 5000},
    )
    _enqueue_payload("dfma", d_task.task_id, json.loads(d_task.model_dump_json()))


def synthesize_report(task_id: str, run_dir: Path) -> Path:
    # Expect agent outputs under runs/<task_id>/out/<agent>.json
    out_dir = run_dir / "runs" / task_id / "out"
    artifacts_dir = run_dir / "artifacts" / "orchestrator"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    md = artifacts_dir / f"{task_id}.md"

    sections: list[str] = []
    for path in sorted(out_dir.glob("*.json")):
        agent = path.stem
        data = json.loads(path.read_text(encoding="utf-8"))
        conf = data.get("confidence", 0.0)
        assumptions = data.get("assumptions", [])
        sections.append(
            f"## {agent}\n- confidence: **{conf:.2f}**\n- assumptions: {assumptions}\n\n```json\n{json.dumps(data['result'], indent=2)}\n```"
        )

    body = "\n\n".join(sections) if sections else "_no agent outputs found_"
    md.write_text(
        textwrap.dedent(
            f"""
            # Task Report — {task_id}
            Timestamp: {datetime.utcnow().isoformat()}Z

            {body}
            """
        ).strip(),
        encoding="utf-8",
    )
    return md


def main() -> None:
    parser = argparse.ArgumentParser(description="APEX Orchestrator")
    parser.add_argument("--bootstrap", action="store_true", help="Bootstrap contracts and enqueue demo tasks")
    parser.add_argument("--report", metavar="TASK_ID", help="Synthesize report for task")
    parser.add_argument("--verify", metavar="TASK_ID", help="Verify outputs and blobs for task")
    args = parser.parse_args()

    _ensure_dirs()
    export_json_schemas()

    if args.bootstrap:
        enqueue_demo_tasks()
    if args.report:
        rp = synthesize_report(args.report, Path("."))
        logger.info(f"[orchestrator] report written: {rp}")
    if args.verify:
        # verify gates
        task_id = args.verify
        failures_sha: list[str] = []
        failures_comp: list[str] = []
        failures_order: list[str] = []
        out_dir = RUNS_DIR / task_id / "out"
        if not out_dir.exists():
            failures_comp.append("missing out dir")
        else:
            # .tmp sentinel detection in out/
            tmps = list(out_dir.glob("*.tmp"))
            if tmps:
                failures_sha += [f"tmp sentinel present: {p}" for p in tmps]
            # .tmp sentinel detection in artifacts/
            art_tmps = list(ARTIFACTS_DIR.rglob("*.tmp"))
            if art_tmps:
                failures_sha += [f"artifact tmp sentinel present: {p}" for p in art_tmps]
            # duplicate outputs
            names = [p.stem for p in out_dir.glob("*.json")]
            if len(names) != len(set(names)):
                failures_comp.append("duplicate outputs in out/")
            for path in sorted(out_dir.glob("*.json")):
                data = json.loads(path.read_text(encoding="utf-8"))
                # forbid extra top-level keys
                allowed = {"result","assumptions","confidence","trace","provenance","schema_version","data_sha256","blob_refs"}
                extra = set(data.keys()) - allowed
                if extra:
                    failures_sha.append(f"envelope has extra keys in {path.name}: {sorted(extra)}")
                # data_sha256 matches computed
                payload = json.dumps(data.get("result", {}), sort_keys=True, separators=(",", ":")).encode("utf-8")
                sha = hashlib.sha256(payload).hexdigest()
                if sha != data.get("data_sha256"):
                    failures_sha.append(f"sha mismatch for {path.name}")
                # blob refs exist and content matches
                for ref in data.get("blob_refs", []):
                    sha_ref = ref.get("sha256")
                    ext = ref.get("ext", "")
                    blob_path = ARTIFACTS_DIR / "blobs" / sha_ref[:2] / f"{sha_ref}.{ext}"
                    if not blob_path.exists():
                        failures_sha.append(f"missing blob {sha_ref}.{ext}")
                    else:
                        content_sha = hashlib.sha256(blob_path.read_bytes()).hexdigest()
                        if content_sha != sha_ref:
                            failures_sha.append(f"blob content mismatch {blob_path}")
                # monotonic present and non-negative; finished_at >= started_at
                mono = data.get("provenance", {}).get("monotonic_ms", 0.0)
                if mono is None or mono < 0:
                    failures_sha.append(f"bad monotonic_ms for {path.name}")
                prov = data.get("provenance", {})
                if prov.get("finished_at", 0) < prov.get("started_at", 0):
                    failures_sha.append(f"time ordering invalid for {path.name}")
                # trace ids present
                ids = data.get("trace", {}).get("ids", {})
                if not ids.get("trace_id") or not ids.get("span_id"):
                    failures_sha.append(f"missing trace ids for {path.name}")
                else:
                    if not TRACE_ID_RE.match(ids.get("trace_id","")) or not TRACE_ID_RE.match(ids.get("span_id","")):
                        failures_sha.append(f"malformed trace ids for {path.name}")
            # processed index duplicates
            idx = RUNS_DIR / task_id / "_index" / "processed.ndjson"
            if idx.exists():
                seen = set()
                for line in idx.read_text(encoding="utf-8").splitlines():
                    try:
                        rec = json.loads(line)
                        key = rec.get("agent")
                        if key in seen:
                            failures_comp.append("duplicate entries in processed.ndjson")
                            break
                        seen.add(key)
                    except Exception:
                        failures_comp.append("malformed processed.ndjson entry")
                        break
            # event stream monotonic ordering per (task, agent)
            events_path = ARTIFACTS_DIR / "logs" / "events.ndjson"
            if events_path.exists():
                per_agent: dict[str, float] = {}
                for line in events_path.read_text(encoding="utf-8").splitlines():
                    try:
                        ev = json.loads(line)
                        if ev.get("task_id") != task_id:
                            continue
                        k = ev.get("agent")
                        ts = float(ev.get("wall_ts", 0.0))
                        if k in per_agent and ts < per_agent[k]:
                            failures_order.append(f"non-monotonic event ts for {k}")
                            break
                        per_agent[k] = ts
                    except Exception as e:
                        logger.warning("Exception in main.py: %s", str(e))
                        continue
        # choose exit code
        if failures_comp or failures_sha or failures_order:
            md = ORCH_ART_DIR / f"{task_id}_verify_fail.md"
            items = []
            items += [f"- {m}" for m in failures_comp]
            items += [f"- {m}" for m in failures_sha]
            items += [f"- {m}" for m in failures_order]
            md.write_text("\n".join(items), encoding="utf-8")
            if failures_sha:
                code = EXIT_INTEGRITY
            elif failures_comp:
                code = EXIT_COMPLETENESS
            else:
                code = EXIT_ORDERING
            logger.error(f"[orchestrator] verification failed(code={code}): see {md}")
            raise SystemExit(code)
        else:
            logger.info("[orchestrator] verification OK")


if __name__ == "__main__":
    main()


