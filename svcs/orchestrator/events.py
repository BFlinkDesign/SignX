from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class Event(BaseModel):
    schema_version: str = "evt-1.0"
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    wall_ts: float = Field(default_factory=lambda: time.time())
    severity: str = "INFO"
    kind: str = "completed"
    task_id: str
    agent: str
    trace_id: str
    span_id: str
    event: str
    monotonic_ms: float
    data_sha256: str
    blob_refs: List[dict] = Field(default_factory=list)
    attempt: int = 1
    duration_ms: float | None = None
    input_bytes: int | None = None
    output_bytes: int | None = None
    result_size_bytes: int | None = None
    message: str | None = None


def append_event(path: Path, evt: Event) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(evt.model_dump_json() + "\n")


