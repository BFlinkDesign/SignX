from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path
from typing import Iterator, Tuple
import logging

logger = logging.getLogger(__name__)


QUEUE_VERSION = "v1"


class FSQueue:
    """Filesystem queue with atomic claim via lockfile and rename.

    Cross-platform: uses O_CREAT|O_EXCL to create a .lock file atomically.
    The caller must keep the lock file descriptor open until completion.
    """

    def __init__(self, inbox: Path, wip: Path, out: Path):
        self.inbox, self.wip, self.out = inbox, wip, out
        for d in (inbox, wip, out):
            d.mkdir(parents=True, exist_ok=True)

    def _try_lock(self, p: Path):
        lock_path = p.with_suffix(p.suffix + ".lock")
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            # write lock metadata
            meta = {
                "pid": os.getpid(),
                "host": socket.gethostname(),
                "ts": time.time(),
                "queue_version": QUEUE_VERSION,
            }
            os.write(fd, json.dumps(meta, sort_keys=True).encode("utf-8"))
            return fd, lock_path
        except FileExistsError:
            return None, lock_path

    def poll(self) -> Iterator[Path]:
        yield from sorted(self.inbox.glob("*.json"))

    def claim(self, p: Path) -> Tuple[Path, int, Path]:
        fd, lock_path = self._try_lock(p)
        if fd is None:
            raise RuntimeError(f"locked:{p.name}")
        dst = self.wip / p.name
        p.replace(dst)
        return dst, fd, lock_path

    def complete(self, wip_file: Path, result: dict, out_name: str) -> Path:
        self.out.mkdir(parents=True, exist_ok=True)
        out_file = self.out / out_name
        tmp = out_file.with_suffix(out_file.suffix + ".tmp")
        tmp.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(out_file)
        wip_file.unlink(missing_ok=True)
        return out_file

    def release(self, fd: int, lock_path: Path) -> None:
        try:
            os.close(fd)
        finally:
            try:
                lock_path.unlink(missing_ok=True)
            except Exception as e:
                logger.warning("Exception in fsqueue.py: %s", str(e))
                pass

    def processed_dir(self) -> Path:
        p = self.out.parent / "processed"
        p.mkdir(parents=True, exist_ok=True)
        return p


