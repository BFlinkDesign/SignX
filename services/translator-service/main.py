from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from pydantic import ValidationError

from contracts.translator import AskAnswer, AskRequest, AskResponse, Trace


app = FastAPI(title="APEX Translator Service", default_response_class=ORJSONResponse)
ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts" / "translator"


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _git() -> Dict[str, str]:
    import subprocess

    def run(cmd):
        try:
            return subprocess.check_output(cmd, cwd=ROOT, text=True).strip()
        except Exception as e:
            logger.warning("Exception in main.py: %s", str(e))
            return "n/a"

    return {
        "git_sha": run(["git", "rev-parse", "--short", "HEAD"]),
        "dirty": "true" if run(["git", "status", "--porcelain"]) else "false",
    }


def _trace(result: Dict[str, Any], inputs: str) -> Trace:
    return Trace(
        data_sha256=_sha(json.dumps(result, separators=(",", ":"))),
        inputs_hash=_sha(inputs),
        trace_id=uuid.uuid4().hex,
        span_id=uuid.uuid4().hex[:16],
        monotonic_ms=0.0,
        code_version=_git(),
        model_config={"provider": "translator", "model": "indexer-v1", "temperature": "0", "max_tokens": "0"},
    )


def _load_index() -> Dict[str, Any]:
    p = ART / "latest.json"
    if not p.exists():
        # build initial index by invoking agent if available
        from svcs.agent_translator.main import refresh_index

        refresh_index()
    return json.loads((ART / "latest.json").read_text(encoding="utf-8"))


from svcs.agent_translator.main import answer_question, refresh_index
import logging

logger = logging.getLogger(__name__)


@app.get("/healthz")
def healthz():
    ok = (ART / "latest.json").exists()
    return {"status": "ok" if ok else "degraded"}


@app.post("/refresh")
def refresh():
    out = refresh_index()
    return {"status": "ok", "index": str(out)}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    t0 = time.monotonic_ns()
    try:
        _ = _load_index()
        ans: AskAnswer = answer_question(req.question)
    except ValidationError as e:
        return ORJSONResponse(status_code=422, content={"error": e.errors()})
    result = ans.model_dump()
    trace = _trace(result, req.model_dump_json())
    trace.monotonic_ms = (time.monotonic_ns() - t0) / 1e6
    resp = AskResponse(
        schema_version="resp-1.0",
        result=ans,
        assumptions=["Repo-indexed, rule-based answer."],
        confidence=ans.confidence,
        trace=trace,
    )
    return resp


