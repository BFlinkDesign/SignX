from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


GOOGLE_API_REGEX = re.compile(r"AIzaSy[A-Za-z0-9_\-]{33}")


def _scan_for_secrets(roots: List[str]) -> List[str]:
	matches: List[str] = []
	for root in roots:
		for p in Path(root).rglob("*"):
			if not p.is_file():
				continue
			# Skip binary-ish
			if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".zip"}:
				continue
			try:
				text = p.read_text(encoding="utf-8", errors="ignore")
			except Exception:
				continue
			if GOOGLE_API_REGEX.search(text):
				matches.append(str(p))
	return matches


def main() -> int:
	"""
	Read ops/reports/findings.json and enforce fail conditions:
	- mypy or deptry non-zero exit → fail
	- vulture unused > threshold (default 100) → fail
	- secrets (Google-style API key regex) found → fail
	- ruff non-zero → warn (does not fail by default)
	"""
	report_path = Path("ops/reports/findings.json")
	if not report_path.exists():
		print("FATAL: findings.json not found. Ensure orchestrator ran first.", file=sys.stderr)
		return 2

	data = json.loads(report_path.read_text(encoding="utf-8"))
	audit = data.get("audit_results", {})
	unused = data.get("unused_results", {})

	failures: List[str] = []
	warnings: List[str] = []

	# Check python audits
	for root, tools in audit.get("python", {}).items():
		# mypy
		mypy = tools.get("mypy")
		if mypy and mypy.get("code", 0) != 0:
			failures.append(f"mypy failures in {root}")
		# deptry
		deptry = tools.get("deptry")
		if deptry and deptry.get("code", 0) != 0:
			failures.append(f"deptry failures in {root}")
		# ruff
		ruff = tools.get("ruff")
		if ruff and ruff.get("code", 0) != 0:
			warnings.append(f"ruff violations in {root}")

	# Unused threshold
	UNUSED_THRESHOLD = 100
	total_unused = 0
	for root, stats in unused.get("python", {}).items():
		total_unused += len(stats.get("unused_candidates", []))
	for root, stats in unused.get("node", {}).items():
		total_unused += len(stats.get("unused_candidates", []))
	if total_unused > UNUSED_THRESHOLD:
		failures.append(f"Excessive unused files detected: {total_unused} > {UNUSED_THRESHOLD}")

	# Secrets scan
	project_roots = data.get("plan", {}).get("rag", {}).get("project_roots") or []
	# Fallback to common roots if orchestrator didn't inject
	if not project_roots:
		project_roots = ["SignX-Studio", "SignX-Intel", "Keyedin"]
	secret_hits = _scan_for_secrets(project_roots)
	if secret_hits:
		failures.append(f"Hardcoded secret pattern found in {len(secret_hits)} file(s). Example: {secret_hits[0]}")

	# Output summary
	print("== Audit Gate Summary ==")
	if warnings:
		print(f"Warnings: {len(warnings)}")
		for w in warnings[:10]:
			print(f"- {w}")
	else:
		print("Warnings: 0")

	if failures:
		print(f"Failures: {len(failures)}")
		for f in failures:
			print(f"- {f}")
		return 1

	print("No failing conditions detected.")
	return 0


if __name__ == "__main__":
	sys.exit(main())

