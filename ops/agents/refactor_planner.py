from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Tuple


def _merge_findings(audit: Dict[str, Any], unused: Dict[str, Any]) -> Dict[str, Any]:
	summary: Dict[str, Any] = {"python": {}, "node": {}}

	for lang in ("python", "node"):
		for root, items in audit.get(lang, {}).items():
			summary[lang].setdefault(root, {})
			summary[lang][root]["audit"] = items
		for root, items in unused.get(lang, {}).items():
			summary[lang].setdefault(root, {})
			summary[lang][root]["unused"] = items
	return summary


def _propose_deletions(merged: Dict[str, Any]) -> List[str]:
	"""
	Heuristic deletion set: files never referenced by import graph and not tests/migrations/readme.
	Conservative: only within listed project roots; proposals only (no file operations).
	"""
	proposals: List[str] = []
	ignore_suffixes = (".md",)
	ignore_substrings = ("migrations", "alembic", "tests", "test_", "README", "readme")

	for lang in ("python", "node"):
		for root, data in merged.get(lang, {}).items():
			unused = data.get("unused", {}).get("unused_candidates", [])
			for path in unused:
				p = str(path)
				if any(s in p for s in ignore_substrings):
					continue
				if p.endswith(ignore_suffixes):
					continue
				proposals.append(p)
	return proposals


def build_refactor_plan(cfg: Dict[str, Any], audit: Dict[str, Any], unused: Dict[str, Any], rag_info: Dict[str, Any]) -> Dict[str, Any]:
	merged = _merge_findings(audit, unused)
	deletions = _propose_deletions(merged)

	top_actions = {
		"linting": [
			"Fix ruff/mypy violations in highest-traffic services first (API, worker)",
			"Enable type-checking in CI; fail on new warnings",
		],
		"deps": [
			"Remove unused Python deps flagged by deptry; pin versions in pyproject/requirements",
			"Run pip-audit and address high/critical advisories",
		],
		"structure": [
			"Consolidate duplicate scripts in SignX-Studio/scripts into modules",
			"Move one-off experiments to an /archive directory",
		],
	}

	return {
		"top_actions": top_actions,
		"proposed_deletions": deletions,
		"rag": rag_info,
	}


