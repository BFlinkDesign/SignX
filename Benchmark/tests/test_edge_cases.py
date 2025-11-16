import io
from pathlib import Path

import pytest
import catscale_delta_parser as mod


def test_empty_pdf_directory(tmp_path: Path):
    # No PDFs present; main should return non-zero (warning path) but not crash
    mod.BASE_DIR = tmp_path
    mod.STORAGE_DIR = tmp_path / "storage"
    mod.REPORTS_DIR = tmp_path / "reports"
    mod.CONFIG_DIR = tmp_path / "config"
    mod.DOCPACK_DIR = tmp_path / "docpack"
    mod.CACHE_DIR = tmp_path / "cache"
    mod.LOGS_DIR = tmp_path / "logs"
    mod.BACKUP_DIR = tmp_path / "backup"
    mod.FORENSICS_DIR = tmp_path / "forensics"
    for d in [
        mod.STORAGE_DIR,
        mod.REPORTS_DIR,
        mod.CONFIG_DIR,
        mod.DOCPACK_DIR,
        mod.CACHE_DIR,
        mod.LOGS_DIR,
        mod.BACKUP_DIR,
        mod.FORENSICS_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)

    # Simulate CLI main with no inputs and empty storage
    rc = mod.main()
    assert rc == 1


def test_corrupted_pdf_fallback(tmp_path: Path, monkeypatch):
    # Set up dirs
    mod.BASE_DIR = tmp_path
    mod.STORAGE_DIR = tmp_path / "storage"
    mod.REPORTS_DIR = tmp_path / "reports"
    mod.CONFIG_DIR = tmp_path / "config"
    mod.DOCPACK_DIR = tmp_path / "docpack"
    mod.CACHE_DIR = tmp_path / "cache"
    mod.LOGS_DIR = tmp_path / "logs"
    mod.BACKUP_DIR = tmp_path / "backup"
    mod.FORENSICS_DIR = tmp_path / "forensics"
    for d in [
        mod.STORAGE_DIR,
        mod.REPORTS_DIR,
        mod.CONFIG_DIR,
        mod.DOCPACK_DIR,
        mod.CACHE_DIR,
        mod.LOGS_DIR,
        mod.BACKUP_DIR,
        mod.FORENSICS_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)

    # Create a dummy corrupted PDF file
    bad_pdf = mod.STORAGE_DIR / "bad.pdf"
    bad_pdf.write_bytes(b"%PDF-1.4\n% Corrupted content\n%%EOF")

    parser = mod.ProductionParser()

    with pytest.raises(Exception):
        # Our process_pdf has internal retries and finally raises to caller
        parser.process_pdf(bad_pdf)

    # Ensure forensic report is written
    forensic_files = list(mod.FORENSICS_DIR.glob("error_*.txt"))
    assert forensic_files, "Expected a forensic error report for corrupted PDF"


