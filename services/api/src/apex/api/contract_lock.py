from __future__ import annotations

import hashlib
import json
import logging
import os
import pathlib

import httpx


def ensure_materials_contract() -> str:
    url = os.getenv("MATERIALS_SCHEMA_URL", "http://materials-service:8080/schema")
    want = os.getenv("APEX_CONTRACT_MATERIALS_SHA", "")
    path = pathlib.Path("/artifacts/schemas/materials-service.v1.json")
    r = httpx.get(url, timeout=10)
    r.raise_for_status()
    schema = r.json()
    b = json.dumps(schema, separators=(",", ":")).encode()
    got = hashlib.sha256(b).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b)
    if want and got != want:
        logging.error("Contract SHA mismatch: got %s want %s", got, want)
        if os.getenv("APEX_ENV") == "prod":
            raise SystemExit(2)
    return got


