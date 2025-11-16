from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Set
import logging

logger = logging.getLogger(__name__)


def collect_referenced_blobs(runs_dir: Path) -> Set[Path]:
    refs: Set[Path] = set()
    for task_dir in runs_dir.glob("*/out/**/*.json"):
        # record JSON artifact paths themselves
        refs.add(task_dir.resolve())
    # Also collect from events if they reference cas paths
    for events in runs_dir.glob("*/events.ndjson"):
        try:
            for line in events.read_text(encoding="utf-8").splitlines():
                if '"blob_path"' in line:
                    # naive path scrape; safer parsing requires json.loads
                    import json as _json
                    try:
                        ev = _json.loads(line)
                        bp = ev.get("blob_path")
                        if bp:
                            refs.add((events.parent / bp).resolve())
                    except Exception as e:
                        logger.warning("Exception in gc.py: %s", str(e))
                        continue
        except Exception as e:
            logger.warning("Exception in gc.py: %s", str(e))
            continue
    return refs


def gc(base_dir: Path, dry_run: bool) -> int:
    runs_dir = base_dir / "runs"
    cas_dir = base_dir / "cas"
    if not cas_dir.exists():
        logger.info(json.dumps({"ok": True, "deleted": 0, "note": "no cas/ directory"}))
        return 0

    refs = collect_referenced_blobs(runs_dir)
    to_delete = []
    for p in cas_dir.rglob("*"):
        if p.is_file() and p.resolve() not in refs:
            to_delete.append(p)

    if dry_run:
        logger.info(json.dumps({"ok": True, "would_delete": [str(p) for p in to_delete]}, indent=2))
        return 0

    for p in to_delete:
        try:
            p.unlink(missing_ok=True)
        except Exception as e:
            logger.warning("Exception in gc.py: %s", str(e))
            pass
    logger.info(json.dumps({"ok": True, "deleted": len(to_delete)}, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--base", default=str(Path(__file__).resolve().parents[2]))
    args = ap.parse_args()
    return gc(Path(args.base), args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())


