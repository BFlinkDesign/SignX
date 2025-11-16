"""Shared hashing utilities for deterministic SHA256 computation."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_payload_sha256(payload: dict[str, Any]) -> str:
    """Compute deterministic SHA256 hash of payload.
    
    Normalizes payload by:
    - Sorting keys
    - Excluding timestamps
    - Deterministic JSON encoding
    
    Args:
        payload: Dict with keys: module, config, files, cost_snapshot
    
    Returns:
        SHA256 hex digest
    """
    normalized = {
        "module": payload.get("module"),
        "config": payload.get("config", {}),
        "files": sorted(payload.get("files", [])),
        "cost_snapshot": payload.get("cost_snapshot", {}),
    }
    json_str = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

