from __future__ import annotations

import json
import subprocess as sp
from pathlib import Path


def test_demo_pipeline(tmp_path: Path):
    # bootstrap
    sp.check_call(["python", "svcs/orchestrator/main.py", "--bootstrap"])  # exports schemas and enqueues demo tasks
    # run all agents once
    for agent in ["materials", "stackup", "dfma", "cad", "parts", "compliance", "eval"]:
        sp.check_call(["python", f"svcs/agent_{agent}/main.py", "--once"])  # type: ignore[str-bytes-safe]

    # synthesize report for the first demo by task_id
    runs = sorted((Path(".") / "runs").glob("*"))
    assert runs, "no runs found"
    # pick the first user-enqueued demo task id
    task = "demo-materials-1"
    sp.check_call(["python", "svcs/orchestrator/main.py", "--report", task])

    # assertions
    outdir = Path("runs") / task / "out"
    # Only materials is guaranteed by bootstrap; others are separate demo ids
    assert (outdir / "materials.json").exists(), "missing materials output"
    data = json.loads((outdir / "materials.json").read_text())
    assert 0.0 <= data.get("confidence", 0.0) <= 1.0


