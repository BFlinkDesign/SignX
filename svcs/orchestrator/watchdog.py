from __future__ import annotations

import time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def watchdog(root: Path, stall_seconds: int = 60) -> None:
	now = time.time()
	for task_dir in (root / "runs").glob("*"):
		status = task_dir / "status.log"
		if not status.exists():
			continue
		last = status.read_text(encoding="utf-8").strip().splitlines()[-1]
		try:
			ts = float(last.split(" ", 1)[0])
		except Exception as e:
			logger.warning("Exception in watchdog.py: %s", str(e))
			continue
		if now - ts > stall_seconds:
			(task_dir / "alerts.log").open("a", encoding="utf-8").write(f"{now:.3f} STALLED >{stall_seconds}s\n")
			logger.info(f"[watchdog] stalled {task_dir.name}")
