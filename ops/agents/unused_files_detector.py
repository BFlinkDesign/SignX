import os
import re
import ast
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

from rich import print as rprint


def _py_import_graph(root: Path) -> Tuple[Set[Path], Set[Path]]:
	"""Very lightweight Python import graph: returns (all_files, referenced_files)."""
	all_py: Set[Path] = set(p.resolve() for p in root.glob("**/*.py"))
	referenced: Set[Path] = set()

	module_path_map: Dict[str, Path] = {}
	for file in all_py:
		try:
			rel = file.relative_to(root).with_suffix("")
			mod = ".".join(rel.parts)
			module_path_map[mod] = file
		except ValueError:
			continue

	for file in all_py:
		try:
			src = file.read_text(encoding="utf-8", errors="ignore")
			tree = ast.parse(src)
		except Exception:
			continue
		for node in ast.walk(tree):
			if isinstance(node, ast.Import):
				for n in node.names:
					target = module_path_map.get(n.name)
					if target:
						referenced.add(target)
			elif isinstance(node, ast.ImportFrom):
				if node.module:
					target = module_path_map.get(node.module)
					if target:
						referenced.add(target)
	return all_py, referenced


def _ts_references(root: Path) -> Tuple[Set[Path], Set[Path]]:
	"""Find TS/TSX/JS/JSX files and approximate references via import lines."""
	all_files: Set[Path] = set()
	for pattern in ("**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"):
		all_files.update({p.resolve() for p in root.glob(pattern)})

	import_re = re.compile(r"^\s*import\s+.*?from\s+['\"](.*)['\"]", re.MULTILINE)
	referenced: Set[Path] = set()

	for f in list(all_files):
		try:
			txt = f.read_text(encoding="utf-8", errors="ignore")
		except Exception:
			continue
		for m in import_re.finditer(txt):
			ref = m.group(1)
			# Only handle relative paths here; ts-prune (if available) will be better
			if ref.startswith("."):
				target = (f.parent / ref).resolve()
				# Try extensions
				candidates = [
					target,
					target.with_suffix(".ts"),
					target.with_suffix(".tsx"),
					target.with_suffix(".js"),
					target.with_suffix(".jsx"),
					target / "index.ts",
					target / "index.tsx",
					target / "index.js",
					target / "index.jsx",
				]
				for c in candidates:
					if c.exists():
						referenced.add(c.resolve())
						break
	return all_files, referenced


def detect_unused_files(cfg: Dict[str, Any]) -> Dict[str, Any]:
	results: Dict[str, Any] = {"python": {}, "node": {}}
	roots = [Path(r) for r in cfg.get("project_roots", [])]

	for root in roots:
		# Python
		all_py, ref_py = _py_import_graph(root)
		py_unused = sorted(str(p) for p in (all_py - ref_py))
		results["python"][str(root)] = {"all": len(all_py), "referenced": len(ref_py), "unused_candidates": py_unused}

		# TS/JS
		all_ts, ref_ts = _ts_references(root)
		ts_unused = sorted(str(p) for p in (all_ts - ref_ts))
		results["node"][str(root)] = {"all": len(all_ts), "referenced": len(ref_ts), "unused_candidates": ts_unused}

	return results


