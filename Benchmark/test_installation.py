#!/usr/bin/env python3
"""
Environment self-check for CAT Scale Benchmark System.

Runs a quick end-to-end verification:
1) Dependency imports
2) DuckDB connectivity
3) Sample PDF processing (creates a blank PDF)
4) Report outputs present

Prints "✓ All systems operational" on success, or detailed errors and exits 1.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path


def check_dependencies(errors: list[str]) -> None:
    core_modules = [
        ("pandas", "required"),
        ("numpy", "required"),
        ("duckdb", "required"),
        ("pdfplumber", "required"),
        ("pypdfium2", "required"),
        ("PyPDF2", "required"),
        ("PIL", "required (Pillow)"),
    ]
    optional_modules = [
        ("pytesseract", "optional"),
    ]

    for mod, req in core_modules:
        try:
            __import__(mod)
        except Exception as e:
            errors.append(f"Dependency missing: {mod} ({req}) — {e}")

    for mod, req in optional_modules:
        try:
            __import__(mod)
        except Exception:
            # optional; do not error
            pass


def check_duckdb(errors: list[str]) -> None:
    try:
        import duckdb  # type: ignore

        con = duckdb.connect(":memory:")
        assert con.execute("select 1").fetchone()[0] == 1
        con.close()
    except Exception as e:
        errors.append(f"DuckDB connectivity failed: {e}")


def process_sample_pdf(errors: list[str]) -> None:
    try:
        import catscale_delta_parser as mod  # local module
        from PyPDF2 import PdfWriter  # type: ignore

        base_dir = Path(mod.BASE_DIR)
        storage = base_dir / "storage"
        reports = base_dir / "reports"
        storage.mkdir(parents=True, exist_ok=True)
        reports.mkdir(parents=True, exist_ok=True)

        sample_pdf = storage / "_selftest_blank.pdf"
        if not sample_pdf.exists():
            # create a simple one-page blank PDF
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            with open(sample_pdf, "wb") as f:
                writer.write(f)

        parser = mod.ProductionParser()
        # Process sample PDF
        parser.process_pdf(sample_pdf)
        # Generate reports (idempotent)
        parser.generate_reports()

        # Validate outputs exist
        bmarks = list((base_dir / "reports").glob("benchmarks_*.txt"))
        receipts = list((base_dir / "reports").glob("receipts_*.csv"))
        if not bmarks:
            errors.append("Report missing: benchmarks_*.txt not found in reports/")
        if not receipts:
            errors.append("Report missing: receipts_*.csv not found in reports/")

    except Exception as e:
        errors.append(f"Sample PDF processing failed: {e}\n{traceback.format_exc()}")


def main() -> int:
    errors: list[str] = []
    check_dependencies(errors)
    check_duckdb(errors)
    process_sample_pdf(errors)

    if errors:
        print("✗ Installation check failed:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("✓ All systems operational")
    return 0


if __name__ == "__main__":
    sys.exit(main())


