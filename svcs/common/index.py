from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def processed_index_path(task_dir: Path) -> Path:
    idx = task_dir / "_index" / "processed.ndjson"
    idx.parent.mkdir(parents=True, exist_ok=True)
    return idx


def already_processed(task_dir: Path, agent: str) -> bool:
    idx = processed_index_path(task_dir)
    if not idx.exists():
        return False
    with idx.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line.strip())
                if rec.get("agent") == agent:
                    return True
            except Exception as e:
                logger.warning("Exception in index.py: %s", str(e))
                continue
    return False


def append_processed(task_dir: Path, agent: str, out_sha: str, trace_id: str) -> None:
    """Atomically append a processed record with single-writer discipline.

    Uses a temp dir and staged concat to avoid clobber and be cross-platform.
    """
    idx = processed_index_path(task_dir)
    tmp_dir = idx.parent / (".append-" + uuid.uuid4().hex)
    tmp_dir.mkdir(parents=True, exist_ok=False)
    try:
        tmp_file = tmp_dir / "processed.ndjson"
        rec = {"agent": agent, "out_sha256": out_sha, "trace_id": trace_id}
        with tmp_file.open("ab") as f:
            line = json.dumps(rec, separators=(",", ":")).encode("utf-8") + b"\n"
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        stage = idx.with_suffix(".stage")
        with stage.open("ab") as out:
            if idx.exists():
                with idx.open("rb") as src:
                    shutil.copyfileobj(src, out)
            with tmp_file.open("rb") as src:
                shutil.copyfileobj(src, out)
            out.flush()
            os.fsync(out.fileno())
        os.replace(stage, idx)
        try:
            dir_fd = os.open(str(idx.parent), os.O_DIRECTORY)
            os.fsync(dir_fd)
            os.close(dir_fd)
        except Exception as e:
            logger.warning("Exception in index.py: %s", str(e))
            pass
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


