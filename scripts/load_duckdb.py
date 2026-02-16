"""Load enriched warehouse CSVs into a DuckDB database.

Strips report-format artifacts (metadata rows, repeated headers, subtotals,
blank lines), writes clean intermediate CSVs, and loads them via DuckDB's
native read_csv for maximum speed.

Usage:
    python load_duckdb.py
"""
import csv
import re
import tempfile
from pathlib import Path

import duckdb

CSV_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\csv_exports")
DB_PATH = Path(r"C:\Scripts\signx-warehouse\warehouse\signx.duckdb")
CLEAN_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\clean")

# ---------------------------------------------------------------------------
# 1. Row Classification (mirrors enrich_csv_exports.py logic)
# ---------------------------------------------------------------------------

def is_blank_or_meta(row):
    if not row:
        return True
    text = "|".join(row).strip()
    if not text or all(c in "| " for c in text):
        return True
    if re.search(
        r"PERIOD:|Eagle Sign|EMPLOYEE LABOR|OPEN WORK ORDERS|"
        r"GROSS MARGIN|SALES BY|DIVISION \d|Date Range|"
        r"^\d{2} [A-Z]{3} \d{4}$|^\d{2}:\d{2}:\d{2}$",
        row[0].strip(),
    ):
        return True
    if re.match(r"^\d{2}:\d{2}:\d{2}$", row[0].strip()):
        return True
    return False


def is_subtotal(row):
    text = "|".join(row)
    if "***" in text or "Grand Total" in text:
        return True
    if "NO RECORDS FOUND" in text:
        return True
    if "Product Type Totals" in text:
        return True
    return False


# ---------------------------------------------------------------------------
# 2. Table Configurations
# ---------------------------------------------------------------------------

def safe_col_name(name, idx, seen):
    """Create a unique, SQL-safe column name."""
    if not name or name.strip() == "":
        name = f"col_{idx}"
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name.strip())
    name = re.sub(r"_+", "_", name).strip("_").lower()
    if not name:
        name = f"col_{idx}"
    base = name
    counter = 2
    while name in seen:
        name = f"{base}_{counter}"
        counter += 1
    seen.add(name)
    return name


TABLES = [
    {
        "file": "EMP.HOURS.BY.DATE_ALL_enriched.csv",
        "header_sig": "EmpNo",
        "table_name": "emp_hours",
    },
    {
        "file": "CUST.PROD.EXPORT_ALL_enriched.csv",
        "header_sig": "Cust No",
        "table_name": "cust_prod",
    },
    {
        "file": "GM.BY.INV.EXPORT_ALL_enriched.csv",
        "header_sig": "Invoice No",
        "table_name": "gm_by_inv",
    },
    {
        "file": "SLSPER.PROD.EXPORT_ALL_enriched.csv",
        "header_sig": "Invoice No",
        "table_name": "slsper_prod",
    },
    {
        "file": "EXPORT.WO.LABOR.ANALYSIS_ALL_enriched.csv",
        "header_sig": "WO #",
        "table_name": "wo_labor",
    },
    {
        "file": "EXPORT.WIP.SUMMARY_C_ALL.csv",
        "header_sig": "Work Order",
        "table_name": "wip_summary_closed",
    },
    {
        "file": "EXPORT.WIP.SUMMARY_O_ALL.csv",
        "header_sig": "Work Order",
        "table_name": "wip_summary_open",
    },
]


# ---------------------------------------------------------------------------
# 3. Strip report-format to clean CSV
# ---------------------------------------------------------------------------

def strip_to_clean_csv(src_path, dst_path, header_sig):
    """Strip report-format CSV to a clean CSV with one header + data rows.

    Returns (header_list, data_row_count).
    """
    header = None
    ncols = None
    data_count = 0

    with open(src_path, encoding="utf-8") as fin, \
         open(dst_path, "w", newline="", encoding="utf-8") as fout:
        reader = csv.reader(fin)
        writer = csv.writer(fout)

        for row in reader:
            # Skip blank rows
            if not row or all(c.strip() == "" for c in row):
                continue

            # Header row detection
            if row[0].strip().strip('"') == header_sig:
                if header is None:
                    header = [c.strip().strip('"') for c in row]
                    ncols = len(header)
                    # Write normalized header
                    seen = set()
                    clean_header = [safe_col_name(h, i, seen) for i, h in enumerate(header)]
                    writer.writerow(clean_header)
                continue

            if is_blank_or_meta(row):
                continue
            if is_subtotal(row):
                continue

            # Skip rows before header is found
            if header is None:
                continue

            # Column count check
            if abs(len(row) - ncols) > 3:
                continue

            # Normalize width
            cleaned = [c.strip().strip('"') for c in row]
            if len(cleaned) < ncols:
                cleaned += [""] * (ncols - len(cleaned))
            elif len(cleaned) > ncols:
                cleaned = cleaned[:ncols]

            writer.writerow(cleaned)
            data_count += 1

    return header, data_count


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------

def main():
    print("DuckDB Warehouse Loader")
    print(f"Source: {CSV_DIR}")
    print(f"Target: {DB_PATH}\n")

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    # Remove stale DB
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing {DB_PATH.name}\n")

    con = duckdb.connect(str(DB_PATH))

    # --- Main tables ---
    print("=" * 60)
    print("MAIN TABLES")
    print("=" * 60)

    for cfg in TABLES:
        src = CSV_DIR / cfg["file"]
        if not src.exists():
            print(f"\nSKIP: {cfg['file']} not found")
            continue

        table_name = cfg["table_name"]
        clean_path = CLEAN_DIR / f"{table_name}.csv"

        print(f"\n--- {cfg['file']} -> {table_name} ---")

        # Step 1: Strip to clean CSV
        header, data_count = strip_to_clean_csv(src, clean_path, cfg["header_sig"])
        if not header:
            print("  No header found, skipping")
            continue
        clean_size = clean_path.stat().st_size / (1024 * 1024)
        print(f"  Cleaned: {data_count:,} rows, {len(header)} cols, {clean_size:.1f}MB")

        # Step 2: Load into DuckDB via native read_csv
        clean_posix = clean_path.as_posix()
        con.execute(f"DROP TABLE IF EXISTS {table_name}")
        con.execute(f"""
            CREATE TABLE {table_name} AS
            SELECT * FROM read_csv('{clean_posix}',
                header=true,
                auto_detect=true,
                ignore_errors=true,
                null_padding=true,
                max_line_size=1048576)
        """)

        count = con.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        ncols = con.execute(f"""
            SELECT count(*) FROM information_schema.columns
            WHERE table_name = '{table_name}'
        """).fetchone()[0]
        print(f"  Loaded: {count:,} rows, {ncols} cols into {table_name}")

    # --- Reference tables ---
    print(f"\n{'=' * 60}")
    print("REFERENCE TABLES")
    print("=" * 60)

    ref_files = sorted(CSV_DIR.glob("ref_*.csv"))
    ref_loaded = 0
    for ref_file in ref_files:
        table_name = ref_file.stem.lower()
        posix = ref_file.as_posix()
        con.execute(f"DROP TABLE IF EXISTS {table_name}")
        try:
            con.execute(f"""
                CREATE TABLE {table_name} AS
                SELECT * FROM read_csv('{posix}',
                    header=true,
                    delim=',',
                    quote='"',
                    normalize_names=true,
                    ignore_errors=true,
                    null_padding=true,
                    auto_detect=true)
            """)
            count = con.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
            print(f"  {table_name}: {count} rows")
            ref_loaded += 1
        except Exception:
            # Fallback: read with Python csv (handles multiline headers),
            # flatten, write clean version, reload
            clean_path = CLEAN_DIR / f"{table_name}.csv"
            with open(ref_file, encoding="utf-8") as fin, \
                 open(clean_path, "w", newline="", encoding="utf-8") as fout:
                reader = csv.reader(fin)
                writer = csv.writer(fout)
                header_row = next(reader)
                seen = set()
                clean_hdr = [safe_col_name(
                    h.replace("\n", " ").replace("\r", " ").strip(), i, seen
                ) for i, h in enumerate(header_row)]
                writer.writerow(clean_hdr)
                for row in reader:
                    cleaned = [c.replace("\n", " ").replace("\r", " ").strip()
                               for c in row]
                    writer.writerow(cleaned)
            cposix = clean_path.as_posix()
            try:
                con.execute(f"""
                    CREATE TABLE {table_name} AS
                    SELECT * FROM read_csv('{cposix}',
                        header=true,
                        auto_detect=true,
                        ignore_errors=true,
                        null_padding=true)
                """)
                count = con.execute(
                    f"SELECT count(*) FROM {table_name}"
                ).fetchone()[0]
                print(f"  {table_name}: {count} rows (cleaned)")
                ref_loaded += 1
            except Exception as e2:
                print(f"  {table_name}: FAILED even after clean - {e2}")

    print(f"\n  {ref_loaded} reference tables loaded")

    # --- Summary ---
    print(f"\n{'=' * 60}")
    print("DATABASE SUMMARY")
    print("=" * 60)

    tables = con.execute("""
        SELECT table_name,
               (SELECT count(*) FROM information_schema.columns c
                WHERE c.table_name = t.table_name) as col_count
        FROM information_schema.tables t
        WHERE table_schema = 'main'
        ORDER BY table_name
    """).fetchall()

    total_rows = 0
    for tname, ncols in tables:
        row_count = con.execute(f"SELECT count(*) FROM {tname}").fetchone()[0]
        total_rows += row_count
        print(f"  {tname:<40} {ncols:>4} cols  {row_count:>10,} rows")

    db_size = DB_PATH.stat().st_size / (1024 * 1024)
    print(f"\n  Total: {len(tables)} tables, {total_rows:,} rows")
    print(f"  Database: {DB_PATH} ({db_size:.1f}MB)")

    con.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
