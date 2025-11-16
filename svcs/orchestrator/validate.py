from __future__ import annotations

import hashlib
import json
import os
import socket
import time
from pathlib import Path
from typing import Any, List, Optional

from pydantic import BaseModel, ValidationError
import logging

logger = logging.getLogger(__name__)


class Provenance(BaseModel):
    agent: str
    version: str
    code_sha: str
    started_at: float
    finished_at: float
    inputs_hash: str
    schema_version: str
    pid: int
    hostname: str
    monotonic_ms: float
    queue_version: Optional[str] = None


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def validate_and_wrap(
    *,
    raw: dict[str, Any],
    schema_model: type[BaseModel],
    agent: str,
    version: str,
    code_sha: str,
    started_at: float,
    inputs_bytes: bytes,
    schema_version: str,
    blob_refs: Optional[List[dict]] = None,
    queue_version: Optional[str] = None,
) -> dict[str, Any]:
    try:
        model = schema_model.model_validate(raw)
    except ValidationError as e:
        raise RuntimeError(f"schema_validation_failed:{agent}:{e}") from e

    # canonicalize payload for digest
    payload = schema_model.model_validate(raw).model_dump(mode="json")
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    data_sha = sha256_bytes(payload_bytes)

    t0 = time.perf_counter()
    model = schema_model.model_validate(raw)
    prov = Provenance(
        agent=agent,
        version=version,
        code_sha=code_sha,
        started_at=started_at,
        finished_at=time.time(),
        inputs_hash=sha256_bytes(inputs_bytes),
        schema_version=schema_version,
        pid=os.getpid(),
        hostname=socket.gethostname(),
        monotonic_ms=(time.perf_counter() - t0) * 1000.0,
        queue_version=queue_version,
    )
    # simple trace ids derived from inputs hash
    trace_id = sha256_bytes(inputs_bytes)[:16]
    span_id = data_sha[:16]
    envelope = {
        "result": payload,
        "assumptions": getattr(model, "assumptions", []),
        "confidence": getattr(model, "confidence", 0.0),
        "trace": {
            "data": {"inputs": {}, "intermediates": {}, "outputs": payload},
            "code_version": {"git_sha": code_sha, "dirty": False, "build_id": None},
            "model_config": {"provider": "apex", "model": agent, "temperature": 0.0, "max_tokens": 1, "seed": 0},
            "ids": {"trace_id": trace_id, "span_id": span_id, "parent_span_id": None},
        },
        "provenance": prov.model_dump(),
        "schema_version": schema_version,
        "data_sha256": data_sha,
        "blob_refs": blob_refs or [],
    }
    return envelope


def write_json_atomic(path: Path, obj: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = json.dumps(obj, indent=2, sort_keys=True).encode("utf-8")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    # fsync parent directory where supported
    try:
        dir_fd = os.open(str(path.parent), os.O_DIRECTORY)
        os.fsync(dir_fd)
        os.close(dir_fd)
    except Exception as e:
        logger.warning("Exception in validate.py: %s", str(e))
        pass
    os.replace(tmp, path)


def store_blob(root: Path, data: bytes, ext: str) -> str:
    h = hashlib.sha256(data).hexdigest()
    sub = h[:2]
    p = root / "artifacts" / "blobs" / sub
    p.mkdir(parents=True, exist_ok=True)
    tmp = p / f"{h}.{ext}.tmp"
    dst = p / f"{h}.{ext}"
    if not dst.exists():
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, dst)
        try:
            dir_fd = os.open(str(p), os.O_DIRECTORY)
            os.fsync(dir_fd)
            os.close(dir_fd)
        except Exception as e:
            logger.warning("Exception in validate.py: %s", str(e))
            pass
    return h


