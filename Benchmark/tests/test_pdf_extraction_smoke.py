from pathlib import Path

import pytest

import catscale_delta_parser as mod


def test_pdf_open_retry_logic(tmp_path: Path, monkeypatch):
    mod.BASE_DIR = tmp_path
    for name in [
        "storage",
        "reports",
        "config",
        "docpack",
        "cache",
        "logs",
        "backup",
        "forensics",
    ]:
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    mod.STORAGE_DIR = tmp_path / "storage"
    mod.REPORTS_DIR = tmp_path / "reports"
    mod.CONFIG_DIR = tmp_path / "config"
    mod.DOCPACK_DIR = tmp_path / "docpack"
    mod.CACHE_DIR = tmp_path / "cache"
    mod.LOGS_DIR = tmp_path / "logs"
    mod.BACKUP_DIR = tmp_path / "backup"
    mod.FORENSICS_DIR = tmp_path / "forensics"

    # Create a minimal invalid PDF file to trigger retry then failure
    pdf_path = mod.STORAGE_DIR / "invalid.pdf"
    pdf_path.write_text("not a real pdf", encoding="utf-8")

    parser = mod.ProductionParser()
    with pytest.raises(Exception):
        parser.process_pdf(pdf_path)


