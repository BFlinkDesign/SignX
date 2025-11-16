from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Callable, List, Tuple

from rich import print as rprint


SubagentFn = Callable[[Dict[str, Any], str], Tuple[str, Dict[str, Any]]]


def _run_subagent(fn: SubagentFn, cfg: Dict[str, Any], root: str) -> Tuple[str, Dict[str, Any]]:
	return fn(cfg, root)


class SwarmManager:
	def __init__(self, max_workers: int = 4) -> None:
		self.max_workers = max_workers

	def run_per_root(self, cfg: Dict[str, Any], roots: List[str], subagents: List[SubagentFn]) -> Dict[str, Any]:
		"""
		Spawns subagents per root concurrently. Each subagent returns (name, data).
		Aggregates results as {root: {name: data}}.
		"""
		results: Dict[str, Any] = {}
		with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
			futures = []
			for root in roots:
				for fn in subagents:
					futures.append(pool.submit(_run_subagent, fn, cfg, root))

			for fut in as_completed(futures):
				try:
					name, data = fut.result()
					root = data.get("_root", "unknown")
					results.setdefault(root, {})
					results[root][name] = data
				except Exception as e:
					rprint(f"[red]Subagent error:[/red] {e}")
		return results


