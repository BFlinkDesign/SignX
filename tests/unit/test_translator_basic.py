from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_index_and_ask():
    # refresh index
    res = subprocess.run([sys.executable, "svcs/agent_translator/main.py", "--refresh"], cwd=ROOT, capture_output=True)
    assert res.returncode == 0
    latest = ROOT / "artifacts" / "translator" / "latest.json"
    assert latest.exists()

    # ask about endpoints
    res = subprocess.run(
        [sys.executable, "svcs/agent_translator/main.py", "--ask", "list endpoints"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    payload = json.loads(res.stdout)
    assert payload["schema_version"] == "resp-1.0"
    assert "result" in payload
    assert payload["result"]["confidence"] >= 0.4


