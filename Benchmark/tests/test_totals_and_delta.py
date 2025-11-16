from pathlib import Path

import pytest
import duckdb
import pandas as pd

import catscale_delta_parser as mod


def setup_parser_with_db(tmp_path: Path) -> mod.ProductionParser:
    install_root = tmp_path
    # Monkeypatch base dirs for isolated test
    mod.BASE_DIR = install_root
    mod.STORAGE_DIR = install_root / "storage"
    mod.REPORTS_DIR = install_root / "reports"
    mod.CONFIG_DIR = install_root / "config"
    mod.DOCPACK_DIR = install_root / "docpack"
    mod.CACHE_DIR = install_root / "cache"
    mod.LOGS_DIR = install_root / "logs"
    mod.BACKUP_DIR = install_root / "backup"
    mod.FORENSICS_DIR = install_root / "forensics"
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

    parser = mod.ProductionParser()
    return parser


def test_validate_delta_calculation(tmp_path: Path):
    parser = setup_parser_with_db(tmp_path)
    con = parser.con

    # Insert a fake file
    con.execute(
        "INSERT INTO files_manifest (file_path, file_sha256, file_size, page_count) VALUES (?, ?, ?, ?)",
        ["/tmp/f.pdf", "hash1", 100, 1],
    )
    file_id = con.execute("SELECT file_id FROM files_manifest WHERE file_sha256='hash1'").fetchone()[0]

    # Insert labor and material
    con.execute(
        "INSERT INTO labor_records (file_id, work_order, work_date, workcode, hours, cost, page_no, line_no) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [file_id, "12345", "2024-01-01", "1001", 2.0, 100.0, 1, 1],
    )
    con.execute(
        "INSERT INTO material_records (file_id, work_order, item_code, description, qty, unit_cost, total_cost, page_no, line_no) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [file_id, "12345", "P-1", "Part", 3, 10.0, 30.0, 1, 1],
    )

    # Printed total: should be MAX(total)
    df = pd.DataFrame([
        {"file_id": file_id, "material": 30.0, "labor": 100.0, "burden": 0.0, "tax": 0.0, "total": 130.0, "page_no": 1}
    ])
    parser.con.register("totals_df", df)
    con.execute(
        """
        INSERT INTO printed_totals
        (file_id, material_cost, labor_cost, burden_cost, outplant_cost, use_tax, total_cost, page_no)
        SELECT file_id,
               COALESCE(material, 0),
               COALESCE(labor, 0),
               COALESCE(burden, 0),
               0,
               COALESCE(tax, 0),
               COALESCE(total, 0),
               page_no
        FROM totals_df
        """
    )
    parser.con.unregister("totals_df")

    status = parser.validate_totals(file_id)
    assert status == "PASSED"

    parsed_total = con.execute(
        "SELECT COALESCE(SUM(cost), 0) + COALESCE(SUM(total_cost), 0) FROM labor_records, material_records WHERE labor_records.file_id=? AND material_records.file_id=?",
        [file_id, file_id],
    ).fetchone()[0]
    printed_total = con.execute(
        "SELECT COALESCE(MAX(total_cost), 0) FROM printed_totals WHERE file_id=?",
        [file_id],
    ).fetchone()[0]
    assert parsed_total == pytest.approx(130.0, rel=1e-6)
    assert printed_total == pytest.approx(130.0, rel=1e-6)


