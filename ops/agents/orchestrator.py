import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml
import typer
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table

from .run_audits import run_all_audits
from .unused_files_detector import detect_unused_files
from .rag_indexer import build_rag_index
from .refactor_planner import build_refactor_plan
from .swarm import SwarmManager


app = typer.Typer(help="SignX multi-agent auditing & refactoring orchestrator")


def load_config(config_path: Path) -> Dict[str, Any]:
	rprint(f"[cyan]Loading config from[/cyan] {config_path}")
	with config_path.open("r", encoding="utf-8") as f:
		return yaml.safe_load(f)


def ensure_reports_dir() -> Path:
	reports_dir = Path("ops/reports")
	reports_dir.mkdir(parents=True, exist_ok=True)
	(reports_dir / "rag").mkdir(parents=True, exist_ok=True)
	return reports_dir


@app.command()
def full(
	config: str = "ops/agents/config.yaml",
	swarm: bool = typer.Option(None, help="Enable/disable swarm execution (overrides config)"),
	workers: int = typer.Option(None, help="Max workers for swarm (overrides config)"),
) -> None:
	"""
	Run the full multi-agent pipeline and produce consolidated reports.
	"""
	cfg = load_config(Path(config))
	reports_dir = ensure_reports_dir()

	project_roots: List[str] = cfg.get("project_roots", [])
	rprint(Panel.fit(f"Analyzing roots:\n" + "\n".join(f"- {p}" for p in project_roots), title="Targets"))

	# 1) Build RAG index first (used by planner for context)
	rag_info = build_rag_index(cfg)

	# Swarm configuration
	swarm_cfg = cfg.get("swarm", {})
	use_swarm = swarm if swarm is not None else bool(swarm_cfg.get("enabled", True))
	max_workers = workers if workers is not None else int(swarm_cfg.get("max_workers", 4))

	if use_swarm:
		rprint(Panel.fit(f"Swarm enabled with max_workers={max_workers}", title="Swarm"))
		manager = SwarmManager(max_workers=max_workers)

		# Define subagent wrappers that operate per-root
		def audit_agent(local_cfg: Dict[str, Any], root: str):
			# limit analysis to a single root view by copying cfg
			sub_cfg = dict(local_cfg)
			sub_cfg["project_roots"] = [root]
			data = run_all_audits(sub_cfg)
			return ("audit", {"_root": root, "data": data})

		def unused_agent(local_cfg: Dict[str, Any], root: str):
			sub_cfg = dict(local_cfg)
			sub_cfg["project_roots"] = [root]
			data = detect_unused_files(sub_cfg)
			return ("unused", {"_root": root, "data": data})

		results_by_root = manager.run_per_root(
			cfg,
			project_roots,
			subagents=[audit_agent, unused_agent],
		)
		# Merge per-root results into the expected shapes
		audit_results = {"python": {}, "node": {}}
		unused_results = {"python": {}, "node": {}}
		for root, components in results_by_root.items():
			a = components.get("audit", {}).get("data", {})
			u = components.get("unused", {}).get("data", {})
			for lang in ("python", "node"):
				for k, v in a.get(lang, {}).items():
					audit_results[lang][k] = v
				for k, v in u.get(lang, {}).items():
					unused_results[lang][k] = v
	else:
		# 2) Run audits (ruff, mypy, deptry, vulture, eslint... as available)
		audit_results = run_all_audits(cfg)
		# 3) Detect unused files/symbols
		unused_results = detect_unused_files(cfg)

	# 4) Aggregate and propose refactors/streamlining
	plan = build_refactor_plan(cfg, audit_results, unused_results, rag_info)

	# Persist artifacts
	with (reports_dir / "findings.json").open("w", encoding="utf-8") as f:
		json.dump(
			{
				"audit_results": audit_results,
				"unused_results": unused_results,
				"rag": rag_info,
				"plan": plan,
			},
			f,
			indent=2,
		)

	# Write simple human summary
	summary_path = reports_dir / "summary.md"
	with summary_path.open("w", encoding="utf-8") as f:
		f.write("# SignX Multi‑Agent Audit Summary\n\n")
		f.write("## Targets\n")
		for root in project_roots:
			f.write(f"- {root}\n")
		f.write("\n## Key Findings\n")
		for area, items in plan.get("top_actions", {}).items():
			f.write(f"- {area}:\n")
			for item in items:
				f.write(f"  - {item}\n")
		f.write("\n## Proposed Deletions\n")
		for path in plan.get("proposed_deletions", []):
			f.write(f"- {path}\n")

	rprint(Panel.fit(f"Reports written to: {reports_dir}", title="Done"))


if __name__ == "__main__":
	app()

