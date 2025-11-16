from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pydantic import ValidationError

from contracts.translator import AskAnswer, AskRequest, AskResponse, Ref, Trace
import logging

logger = logging.getLogger(__name__)


ROOT = Path(__file__).resolve().parents[2]
ART_DIR = ROOT / "artifacts" / "translator"
ART_DIR.mkdir(parents=True, exist_ok=True)


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _trace(code_version: Dict[str, str], model_cfg: Dict[str, str], result: Dict[str, Any], inputs: str) -> Trace:
    return Trace(
        data_sha256=_sha(json.dumps(result, separators=(",", ":"))),
        inputs_hash=_sha(inputs),
        trace_id=uuid.uuid4().hex,
        span_id=uuid.uuid4().hex[:16],
        monotonic_ms=0.0,
        code_version=code_version,
        model_config=model_cfg,
    )


def _git() -> Dict[str, str]:
    def run(cmd: List[str]) -> str:
        try:
            return subprocess.check_output(cmd, cwd=ROOT, text=True).strip()
        except Exception as e:
            logger.warning("Exception in main.py: %s", str(e))
            return "n/a"

    return {
        "git_sha": run(["git", "rev-parse", "--short", "HEAD"]),
        "dirty": "true" if run(["git", "status", "--porcelain"]) else "false",
    }


# ----- INDEXING -----
def _scan_routes() -> List[Dict[str, str]]:
    routes: List[Dict[str, str]] = []
    for p in ROOT.glob("services/**/src/**/main.py"):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'@app\.(get|post|put|delete)\("([^"]+)"', txt):
            method, path = m.group(1).upper(), m.group(2)
            routes.append({"file": str(p.relative_to(ROOT)), "method": method, "path": path})
    for p in ROOT.glob("services/**/*main.py"):
        if p.suffix != ".py":
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'@app\.(get|post|put|delete)\("([^"]+)"', txt):
            method, path = m.group(1).upper(), m.group(2)
            routes.append({"file": str(p.relative_to(ROOT)), "method": method, "path": path})
    return routes


def _scan_contracts() -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for p in ROOT.glob("contracts/*.py"):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        classes = re.findall(r"class\s+([A-Za-z0-9_]+)\(BaseModel\)", txt)
        out.append({"file": str(p.relative_to(ROOT)), "models": classes})
    return out


def _scan_compose() -> Dict[str, Any]:
    # Prefer root infra/compose.yaml; fall back to apex/infra/compose.yaml
    y = ROOT / "infra" / "compose.yaml"
    if not y.exists():
        y = ROOT / "apex" / "infra" / "compose" / "compose.yaml"
    if not y.exists():
        return {}
    # cheap YAML-ish parse
    lines = y.read_text(encoding="utf-8", errors="ignore").splitlines()
    services: Dict[str, Dict[str, Any]] = {}
    cur: str | None = None
    for ln in lines:
        if re.match(r"^\s{2}[A-Za-z0-9_-]+:\s*$", ln):
            cur = ln.strip().rstrip(":")
            if cur != "services":
                services[cur] = {}
        if cur and "build:" in ln:
            services[cur]["build"] = True
        if cur and "image:" in ln:
            services[cur]["image"] = ln.split("image:", 1)[1].strip()
        if cur and "healthcheck:" in ln:
            services[cur]["healthcheck"] = True
    return {"path": str(y.relative_to(ROOT)), "services": services}


def _scan_agents() -> List[str]:
    return [str(p.relative_to(ROOT)) for p in ROOT.glob("svcs/agent_*/main.py")]


def _scan_todos() -> List[Dict[str, str]]:
    todos: List[Dict[str, str]] = []
    for p in ROOT.rglob("*.py"):
        try:
            for i, ln in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
                if "TODO" in ln:
                    todos.append({"file": str(p.relative_to(ROOT)), "line": i, "text": ln.strip()})
        except Exception as e:
            logger.warning("Exception in main.py: %s", str(e))
            pass
    for p in ROOT.rglob("README*.md"):
        for i, ln in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if "TODO" in ln:
                todos.append({"file": str(p.relative_to(ROOT)), "line": i, "text": ln.strip()})
    return todos


def _scan_events() -> Dict[str, Any]:
    log = ROOT / "artifacts" / "logs" / "events.ndjson"
    stats: Dict[str, int] = {}
    latest: List[Dict[str, Any]] = []
    if log.exists():
        for line in log.read_text(encoding="utf-8", errors="ignore").splitlines()[-200:]:
            try:
                o = json.loads(line)
                key = f"{o.get('agent', '?')}:{o.get('event', '?')}"
                stats[key] = stats.get(key, 0) + 1
                latest.append(o)
            except Exception as e:
                logger.warning("Exception in main.py: %s", str(e))
                pass
    return {"stats": stats, "tail": latest[-20:]}


def _index() -> Dict[str, Any]:
    return {
        "meta": {
            "generated_at": time.time(),
            "host": os.uname().nodename if hasattr(os, "uname") else "local",
            "git": _git(),
        },
        "routes": _scan_routes(),
        "contracts": _scan_contracts(),
        "compose": _scan_compose(),
        "agents": _scan_agents(),
        "todos": _scan_todos(),
        "events": _scan_events(),
        "files": {
            "schemas": [str(p.relative_to(ROOT)) for p in ROOT.glob("**/schemas/*.json")] +
            [str(p.relative_to(ROOT)) for p in ROOT.glob("**/schema*.json")]
        },
    }


def refresh_index() -> Path:
    idx = _index()
    payload = json.dumps(idx, indent=2, sort_keys=True)
    h = _sha(payload)
    tmp = ART_DIR / f"index.{h}.json.tmp"
    out = ART_DIR / f"index.{h}.json"
    with tmp.open("wb") as f:
        f.write(payload.encode())
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, out)
    if hasattr(os, "sync"):
        try:
            os.sync()  # type: ignore[attr-defined]
        except Exception as e:
            logger.warning("Exception in main.py: %s", str(e))
            pass
    (ART_DIR / "latest.json").write_text(payload, encoding="utf-8")
    return out


# ----- ANSWER ENGINE (rule-based; LLM optional) -----
def _keyword(q: str, index: Dict[str, Any]) -> Tuple[str, List[Ref], float]:
    ql = q.lower()
    refs: List[Ref] = []
    if any(k in ql for k in ["endpoint", "route", "api", "path"]):
        routes = index.get("routes", [])
        sample = "\n".join([f"- {r['method']} {r['path']}  ({r['file']})" for r in routes[:25]])
        for r in routes[:5]:
            refs.append(Ref(path=r["file"], summary=f"{r['method']} {r['path']}"))
        return (f"Discovered {len(routes)} routes:\n{sample}", refs, 0.9)
    if any(k in ql for k in ["contract", "schema", "model"]):
        cs = index.get("contracts", [])
        msg = "\n".join([f"- {c['file']}: {', '.join(c['models'])}" for c in cs[:25]])
        for c in cs[:5]:
            refs.append(Ref(path=c["file"], summary="models: " + ", ".join(c["models"])))
        return (f"Contracts found ({len(cs)} files):\n{msg}", refs, 0.88)
    if any(k in ql for k in ["service", "compose", "docker", "stack"]):
        comp = index.get("compose", {})
        svcs = comp.get("services", {})
        msg = "\n".join([f"- {k} (health={ 'yes' if v.get('healthcheck') else 'no'})" for k, v in svcs.items()])
        refs.append(Ref(path=comp.get("path", "infra/compose.yaml"), summary="compose"))
        return (f"Compose services discovered ({len(svcs)}):\n{msg}", refs, 0.86)
    if "agent" in ql or "queue" in ql:
        ags = index.get("agents", [])
        msg = "\n".join([f"- {a}" for a in ags])
        ev = index.get("events", {}).get("stats", {})
        refs.append(Ref(path="artifacts/logs/events.ndjson", summary="event counters"))
        return (f"Agents present ({len(ags)}):\n{msg}\n\nRecent event counters: {ev}", refs, 0.9)
    if "todo" in ql or "next" in ql or "pending" in ql:
        todos = index.get("todos", [])
        msg = "\n".join([f"- {t['file']}:{t['line']} {t['text']}" for t in todos[:30]])
        for t in todos[:3]:
            refs.append(Ref(path=t["file"], summary="TODO", lines=str(t["line"])))
        return (f"TODOs detected ({len(todos)}):\n{msg}", refs, 0.82)
    # generic: quick search in routes/contracts/todos filenames
    hits: List[str] = []
    for r in index.get("routes", []):
        if ql in r["path"].lower():
            hits.append(f"route {r['method']} {r['path']} ({r['file']})")
    for c in index.get("contracts", []):
        if any(ql in m.lower() for m in c["models"]):
            hits.append(f"contract {c['file']} models={','.join(c['models'])}")
    if hits:
        refs.append(Ref(path="artifacts/translator/latest.json", summary="index"))
        return ("\n".join(hits[:25]), refs, 0.7)
    return (
        "I couldn't match that exactly in the index. Ask about endpoints, contracts, agents, queue, todos, services, or files.",
        [],
        0.4,
    )


def answer_question(q: str) -> AskAnswer:
    idx_path = ART_DIR / "latest.json"
    if not idx_path.exists():
        refresh_index()
    index = json.loads(idx_path.read_text(encoding="utf-8"))
    text, refs, conf = _keyword(q, index)
    return AskAnswer(answer=text, refs=refs, confidence=conf)


# ----- CLI -----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="Scan repo and (re)build translator index")
    ap.add_argument("--ask", type=str, help="Ask a question about the codebase")
    args = ap.parse_args()

    code_ver = _git()
    model_cfg = {"provider": "translator", "model": "indexer-v1", "temperature": "0", "max_tokens": "0"}

    if args.refresh:
        out = refresh_index()
        logger.info(f"[translator] index written: {out}")
        return

    if args.ask:
        req = AskRequest(question=args.ask)
        t0 = time.monotonic_ns()
        ans = answer_question(req.question)
        resp = AskResponse(
            schema_version="resp-1.0",
            result=ans,
            assumptions=["Rule-based responder using repo index; no external model used."],
            confidence=ans.confidence,
            trace=_trace(code_ver, model_cfg, ans.model_dump(), req.model_dump_json()),
        )
        # set timing
        resp.trace.monotonic_ms = (time.monotonic_ns() - t0) / 1e6
        logger.info(json.dumps(resp.model_dump(), indent=2))
        return

    ap.print_help()


if __name__ == "__main__":
    main()


