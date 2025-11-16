from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Any, Iterable, List

from rich import print as rprint
import logging

logger = logging.getLogger(__name__)

try:
	from sentence_transformers import SentenceTransformer
	_HAS_ST = True
except Exception:
	_HAS_ST = False


def _iter_files(roots: List[str], include_globs: List[str], exclude_globs: List[str], max_kb: int) -> Iterable[Path]:
	for root in roots:
		base = Path(root)
		for pattern in include_globs:
			for p in base.glob(pattern):
				if p.is_dir():
					continue
				# naive exclude check
				if any(p.match(ex) for ex in exclude_globs):
					continue
				try:
					if p.stat().st_size > max_kb * 1024:
						continue
				except Exception as e:
					logger.warning("Exception in rag_indexer.py: %s", str(e))
					continue
				yield p


def _ensure_db(db_path: Path) -> sqlite3.Connection:
	db_path.parent.mkdir(parents=True, exist_ok=True)
	conn = sqlite3.connect(str(db_path))
	conn.execute(
		"CREATE TABLE IF NOT EXISTS docs (path TEXT PRIMARY KEY, content TEXT NOT NULL)"
	)
	conn.execute(
		"CREATE TABLE IF NOT EXISTS embeddings (path TEXT PRIMARY KEY, vec BLOB)"
	)
	return conn


def _chunk(text: str, chunk_size: int, overlap: int) -> List[str]:
	parts: List[str] = []
	start = 0
	while start < len(text):
		end = min(len(text), start + chunk_size)
		parts.append(text[start:end])
		start = end - overlap
		if start < 0:
			start = 0
	return parts


def build_rag_index(cfg: Dict[str, Any]) -> Dict[str, Any]:
	rag_cfg = cfg.get("rag", {})
	db_path = Path(rag_cfg.get("db_path", "ops/reports/rag/index.sqlite"))
	chunk_size = int(rag_cfg.get("chunk_size", 1024))
	overlap = int(rag_cfg.get("chunk_overlap", 128))
	max_kb = int(rag_cfg.get("max_file_size_kb", 256))
	model_name = rag_cfg.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")

	roots = cfg.get("project_roots", [])
	include = cfg.get("include_globs", ["**/*.py", "**/*.md"])
	exclude = cfg.get("exclude_globs", [])

	conn = _ensure_db(Path(db_path))
	cur = conn.cursor()

	files_indexed = 0
	chunks_indexed = 0

	model = None
	if _HAS_ST:
		try:
			model = SentenceTransformer(model_name)
			rprint(f"[green]Using embedding model[/green] {model_name}")
		except Exception as e:
			rprint(f"[yellow]Falling back to no-embedding mode:[/yellow] {e}")

	for p in _iter_files(roots, include, exclude, max_kb=max_kb):
		try:
			text = p.read_text(encoding="utf-8", errors="ignore")
		except Exception as e:
			logger.warning("Exception in rag_indexer.py: %s", str(e))
			continue
		cur.execute("INSERT OR REPLACE INTO docs(path, content) VALUES(?, ?)", (str(p), text))
		files_indexed += 1

		if model is not None:
			for part in _chunk(text, chunk_size, overlap):
				vec = model.encode(part)
				cur.execute("INSERT OR REPLACE INTO embeddings(path, vec) VALUES(?, ?)", (str(p), vec.tobytes()))
				chunks_indexed += 1

	conn.commit()
	conn.close()

	return {
		"db_path": str(db_path),
		"files_indexed": files_indexed,
		"chunks_indexed": chunks_indexed,
		"embeddings_enabled": bool(model is not None),
	}


