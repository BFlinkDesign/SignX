import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from rich import print as rprint


def _tool_available(cmd: str) -> bool:
	return shutil.which(cmd) is not None


def _run(cmd: List[str], cwd: Path | None = None) -> tuple[int, str, str]:
	proc = subprocess.Popen(
		cmd,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		cwd=str(cwd) if cwd else None,
		shell=False,
	)
	stdout, stderr = proc.communicate()
	return proc.returncode, stdout.decode("utf-8", errors="ignore"), stderr.decode("utf-8", errors="ignore")


def _collect_python_roots(project_roots: List[str]) -> List[Path]:
	roots: List[Path] = []
	for root in project_roots:
		p = Path(root)
		if (p / "pyproject.toml").exists() or any(p.glob("**/*.py")):
			roots.append(p)
	return roots


def _collect_node_roots(project_roots: List[str]) -> List[Path]:
	roots: List[Path] = []
	for root in project_roots:
		p = Path(root)
		if (p / "package.json").exists() or any(p.glob("**/*.ts")) or any(p.glob("**/*.tsx")):
			roots.append(p)
	return roots


def run_all_audits(cfg: Dict[str, Any]) -> Dict[str, Any]:
	results: Dict[str, Any] = {"python": {}, "node": {}}
	project_roots: List[str] = cfg.get("project_roots", [])
	tools_cfg = cfg.get("tools", {})

	python_roots = _collect_python_roots(project_roots)
	node_roots = _collect_node_roots(project_roots)

	# Python tools
	for root in python_roots:
		rprint(f"[cyan]Auditing Python root[/cyan] {root}")
		root_key = str(root)
		results["python"].setdefault(root_key, {})

		if tools_cfg.get("ruff", True) and _tool_available("ruff"):
			code, out, err = _run(["ruff", "check", "--format", "json", "."], cwd=root)
			results["python"][root_key]["ruff"] = {"code": code, "stdout": out, "stderr": err}

		if tools_cfg.get("mypy", True) and _tool_available("mypy"):
			code, out, err = _run(["mypy", "--pretty", "."], cwd=root)
			results["python"][root_key]["mypy"] = {"code": code, "stdout": out, "stderr": err}

		if tools_cfg.get("deptry", True) and _tool_available("deptry"):
			code, out, err = _run(["deptry", "."], cwd=root)
			results["python"][root_key]["deptry"] = {"code": code, "stdout": out, "stderr": err}

		if tools_cfg.get("vulture", True) and _tool_available("vulture"):
			code, out, err = _run(["vulture", "."], cwd=root)
			results["python"][root_key]["vulture"] = {"code": code, "stdout": out, "stderr": err}

	# Node tools
	for root in node_roots:
		rprint(f"[cyan]Auditing Node/TS root[/cyan] {root}")
		root_key = str(root)
		results["node"].setdefault(root_key, {})

		eslint_enabled = tools_cfg.get("eslint", True)
		if eslint_enabled:
			eslint_bin = shutil.which("eslint") or str((root / "node_modules" / ".bin" / "eslint").resolve())
			if eslint_bin and Path(eslint_bin).exists():
				code, out, err = _run([eslint_bin, ".", "-f", "json"], cwd=root)
				results["node"][root_key]["eslint"] = {"code": code, "stdout": out, "stderr": err}

	return results


