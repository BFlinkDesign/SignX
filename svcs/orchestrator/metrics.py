from __future__ import annotations

from pathlib import Path


def write_metrics(metrics_path: Path, lines: list[str]) -> None:
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


