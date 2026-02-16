"""Load enriched warehouse CSVs into a DuckDB database.

Strips report-format artifacts (metadata rows, repeated headers, subtotals,
blank lines) and loads clean data rows into typed DuckDB tables.

Usage:
    python load_duckdb.py
"""
import csv
import re
import sys
from pathlib import Path

import duckdb

CSV_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\csv_exports")
DB_PATH = Path(r"C:\Scripts\signx-warehouse\warehouse\signx.duckdb")

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
    if "Totals" in text and ("***" in text or re.search(r"\bTotals\b", text)):
        return True
    return False


# ---------------------------------------------------------------------------
# 2. Table Configurations
# ---------------------------------------------------------------------------

TABLES = {
    "emp_hours": {
        "file": "EMP.HOURS.BY.DATE_ALL_enriched.csv",
        "header_sig": "EmpNo",
        "table_name": "emp_hours",
        "columns": [
            ("emp_no", "VARCHAR"),
            ("employee_name", "VARCHAR"),
            ("time_date", "VARCHAR"),
            ("wo_ind_code", "VARCHAR"),
            ("job_location", "VARCHAR"),
            ("start_time", "VARCHAR"),
            ("stop_time", "VARCHAR"),
            ("labor_hrs", "DOUBLE"),
            ("work_code", "VARCHAR"),
            ("work_description", "VARCHAR"),
            ("timecard_comments", "VARCHAR"),
            ("work_code_ref_desc", "VARCHAR"),
            ("work_dept", "VARCHAR"),
            ("work_dept_name", "VARCHAR"),
        ],
    },
    "cust_prod": {
        "file": "CUST.PROD.EXPORT_ALL_enriched.csv",
        "header_sig": "Cust No",
        "table_name": "cust_prod",
        "columns": [
            ("cust_no", "VARCHAR"),
            ("customer_name", "VARCHAR"),
            ("prod_code", "VARCHAR"),
            ("product_type_desc", "VARCHAR"),
            ("inv_date", "VARCHAR"),
            ("invoice_no", "VARCHAR"),
            ("job_part", "VARCHAR"),
            ("gross_sales", "DOUBLE"),
            ("total_cost", "DOUBLE"),
            ("gross_margin", "DOUBLE"),
            ("gm_pct", "DOUBLE"),
            ("extra_charge", "DOUBLE"),
            ("sales_tax", "DOUBLE"),
            ("location_no", "VARCHAR"),
            ("location_name", "VARCHAR"),
            ("city", "VARCHAR"),
            ("state", "VARCHAR"),
            ("salesperson_1", "VARCHAR"),
            ("comm_rate_1", "DOUBLE"),
            ("salesperson_2", "VARCHAR"),
            ("comm_rate_2", "DOUBLE"),
            ("salesperson_3", "VARCHAR"),
            ("comm_rate_3", "DOUBLE"),
            ("_blank", "VARCHAR"),
            ("prod_code_ref_desc", "VARCHAR"),
            ("salesperson_1_name", "VARCHAR"),
            ("salesperson_2_name", "VARCHAR"),
            ("salesperson_3_name", "VARCHAR"),
        ],
    },
    "gm_by_inv": {
        "file": "GM.BY.INV.EXPORT_ALL_enriched.csv",
        "header_sig": "Invoice No",
        "table_name": "gm_by_inv",
        "columns": [
            ("invoice_no", "VARCHAR"),
            ("inv_date", "VARCHAR"),
            ("prod_code", "VARCHAR"),
            ("wo_part", "VARCHAR"),
            ("quote", "VARCHAR"),
            ("gross_sales", "DOUBLE"),
            ("total_cost", "DOUBLE"),
            ("gross_margin", "DOUBLE"),
            ("gm_pct", "DOUBLE"),
            ("extra_chg", "DOUBLE"),
            ("sales_tax", "DOUBLE"),
            ("quote_cost", "DOUBLE"),
            ("quote_price", "DOUBLE"),
            ("quote_gm_pct", "DOUBLE"),
            ("quote_sell_price", "DOUBLE"),
            ("quote_sell_gm_pct", "DOUBLE"),
            ("cust_no", "VARCHAR"),
            ("customer_name", "VARCHAR"),
            ("salesper_1", "VARCHAR"),
            ("rate_1", "DOUBLE"),
            ("salesper_2", "VARCHAR"),
            ("rate_2", "DOUBLE"),
            ("salesper_3", "VARCHAR"),
            ("rate_3", "DOUBLE"),
            ("location_no", "VARCHAR"),
            ("location_name", "VARCHAR"),
            ("city", "VARCHAR"),
            ("state", "VARCHAR"),
            ("_blank", "VARCHAR"),
            ("prod_code_desc", "VARCHAR"),
            ("salesper_1_name", "VARCHAR"),
            ("salesper_2_name", "VARCHAR"),
            ("salesper_3_name", "VARCHAR"),
        ],
    },
    "slsper_prod": {
        "file": "SLSPER.PROD.EXPORT_ALL_enriched.csv",
        "header_sig": "Invoice No",
        "table_name": "slsper_prod",
        "columns": [
            ("invoice_no", "VARCHAR"),
            ("inv_date", "VARCHAR"),
            ("prod_code", "VARCHAR"),
            ("cust_no", "VARCHAR"),
            ("customer_name", "VARCHAR"),
            ("gross_sales", "DOUBLE"),
            ("total_cost", "DOUBLE"),
            ("gross_margin", "DOUBLE"),
            ("gm_pct", "DOUBLE"),
            ("extra_charge", "DOUBLE"),
            ("salesperson_1", "VARCHAR"),
            ("comm_rate_1", "DOUBLE"),
            ("salesperson_2", "VARCHAR"),
            ("comm_rate_2", "DOUBLE"),
            ("salesperson_3", "VARCHAR"),
            ("comm_rate_3", "DOUBLE"),
            ("location_no", "VARCHAR"),
            ("location_name", "VARCHAR"),
            ("city", "VARCHAR"),
            ("state", "VARCHAR"),
            ("_blank", "VARCHAR"),
            ("prod_code_desc", "VARCHAR"),
            ("salesperson_1_name", "VARCHAR"),
            ("salesperson_2_name", "VARCHAR"),
            ("salesperson_3_name", "VARCHAR"),
        ],
    },
    "wo_labor": {
        "file": "EXPORT.WO.LABOR.ANALYSIS_ALL_enriched.csv",
        "header_sig": "WO #",
        "table_name": "wo_labor",
        # This table has 168 columns with repeating dept groups.
        # We'll auto-detect column names from the header row.
        "columns": "auto",
    },
    "wip_summary_c": {
        "file": "EXPORT.WIP.SUMMARY_C_ALL.csv",
        "header_sig": "Work Order",
        "table_name": "wip_summary_closed",
        "columns": [
            ("work_order", "VARCHAR"),
            ("quote_part_desc", "VARCHAR"),
            ("qty_mfg", "INTEGER"),
            ("qty_comp", "INTEGER"),
            ("act_material", "DOUBLE"),
            ("act_labor", "DOUBLE"),
            ("act_burden", "DOUBLE"),
            ("act_cncrt", "DOUBLE"),
            ("act_out1", "DOUBLE"),
            ("act_utax", "DOUBLE"),
            ("act_total", "DOUBLE"),
            ("est_material", "DOUBLE"),
            ("est_labor", "DOUBLE"),
            ("est_burden", "DOUBLE"),
            ("est_cncrt", "DOUBLE"),
            ("est_out1", "DOUBLE"),
            ("est_utax", "DOUBLE"),
            ("est_total", "DOUBLE"),
            ("var_cost", "DOUBLE"),
            ("act_billing", "DOUBLE"),
            ("act_gm_pct", "DOUBLE"),
            ("est_billing", "DOUBLE"),
            ("est_gm_pct", "DOUBLE"),
            ("due_date", "VARCHAR"),
            ("cust_no", "VARCHAR"),
            ("customer_name", "VARCHAR"),
            ("c_f", "VARCHAR"),
            ("std_comp_amt", "DOUBLE"),
            ("est_cogs", "DOUBLE"),
            ("net_wip", "DOUBLE"),
            ("invoice_date", "VARCHAR"),
            ("invoice_nbr", "VARCHAR"),
            ("est_hrs", "DOUBLE"),
            ("act_hrs", "DOUBLE"),
        ],
    },
    "wip_summary_o": {
        "file": "EXPORT.WIP.SUMMARY_O_ALL.csv",
        "header_sig": "Work Order",
        "table_name": "wip_summary_open",
        # O variant has 2 extra unnamed columns; detect from header
        "columns": "auto",
    },
}


# ---------------------------------------------------------------------------
# 3. CSV Parsing
# ---------------------------------------------------------------------------

def parse_report_csv(filepath, header_sig, expected_ncols=None):
    """Parse a report-format CSV, returning (header, data_rows).

    Strips metadata, blank lines, subtotals, and repeated headers.
    """
    header = None
    data = []

    with open(filepath, encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            # Skip blank rows
            if not row or all(c.strip() == "" for c in row):
                continue

            # Check for header row
            if row[0].strip().strip('"') == header_sig:
                if header is None:
                    header = [c.strip().strip('"') for c in row]
                    if expected_ncols is None:
                        expected_ncols = len(header)
                continue  # Skip all header rows (repeated per year)

            if is_blank_or_meta(row):
                continue
            if is_subtotal(row):
                continue

            # Check column count (allow ±3 tolerance)
            if expected_ncols and abs(len(row) - expected_ncols) > 3:
                continue

            # Pad short rows, trim long rows to header width
            if header:
                if len(row) < len(header):
                    row = row + [""] * (len(header) - len(row))
                elif len(row) > len(header):
                    row = row[: len(header)]

            # Strip quotes from values (WIP files have triple-quoted values)
            cleaned = [c.strip().strip('"') for c in row]
            data.append(cleaned)

    return header, data


# ---------------------------------------------------------------------------
# 4. DuckDB Table Creation & Loading
# ---------------------------------------------------------------------------

def safe_col_name(name, idx, seen):
    """Create a unique, SQL-safe column name."""
    if not name or name.strip() == "":
        name = f"col_{idx}"
    # Normalize
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name.strip())
    name = re.sub(r"_+", "_", name).strip("_").lower()
    if not name:
        name = f"col_{idx}"
    # Deduplicate
    base = name
    counter = 2
    while name in seen:
        name = f"{base}_{counter}"
        counter += 1
    seen.add(name)
    return name


def auto_columns_from_header(header):
    """Generate (col_name, type) tuples from a raw header row."""
    seen = set()
    cols = []
    for i, h in enumerate(header):
        name = safe_col_name(h, i, seen)
        cols.append((name, "VARCHAR"))
    return cols


def create_table(con, table_name, columns):
    """Create a DuckDB table from column definitions."""
    col_defs = ", ".join(f'"{name}" {dtype}' for name, dtype in columns)
    con.execute(f"DROP TABLE IF EXISTS {table_name}")
    con.execute(f"CREATE TABLE {table_name} ({col_defs})")


def safe_double(val):
    """Convert a string to float, handling commas and blanks."""
    if not val or val.strip() == "":
        return None
    val = val.strip().replace(",", "").replace("%", "")
    try:
        return float(val)
    except ValueError:
        return None


def safe_int(val):
    if not val or val.strip() == "":
        return None
    val = val.strip().replace(",", "")
    try:
        return int(float(val))
    except ValueError:
        return None


def insert_rows(con, table_name, columns, data):
    """Insert data rows into a DuckDB table with type conversion."""
    if not data:
        return 0

    placeholders = ", ".join(["?"] * len(columns))
    sql = f"INSERT INTO {table_name} VALUES ({placeholders})"

    batch = []
    skipped = 0
    for row in data:
        converted = []
        for i, (_, dtype) in enumerate(columns):
            val = row[i] if i < len(row) else ""
            if dtype == "DOUBLE":
                converted.append(safe_double(val))
            elif dtype == "INTEGER":
                converted.append(safe_int(val))
            else:
                converted.append(val if val else None)
        batch.append(converted)

    # Batch insert
    con.executemany(sql, batch)
    return len(batch)


# ---------------------------------------------------------------------------
# 5. WO Labor special handling — deduplicate repeated dept column names
# ---------------------------------------------------------------------------

def build_wo_labor_columns(header):
    """Build column defs for WO Labor with dept-prefixed group columns.

    The header has repeating groups of (blank, Est Hrs, Act Hrs, Variance,
    Est Dollars, Act Dollars, Variance) for each dept code. The dept codes
    are in the metadata row above the header (not in the header itself).
    We'll just number the groups.
    """
    seen = set()
    cols = []
    group_idx = 0
    group_fields = ["est_hrs", "act_hrs", "variance_hrs",
                    "est_dollars", "act_dollars", "variance_dollars"]
    group_pos = 0
    in_group = False

    for i, h in enumerate(header):
        h_clean = h.strip()

        # First 10 columns are the fixed fields
        if i < 10:
            name = safe_col_name(h_clean, i, seen)
            cols.append((name, "VARCHAR"))
            continue

        # Detect group separator (empty column between groups)
        if h_clean == "" and not in_group:
            group_idx += 1
            group_pos = 0
            in_group = True
            name = safe_col_name(f"g{group_idx:02d}_sep", i, seen)
            cols.append((name, "VARCHAR"))
            continue

        if in_group and group_pos < 6:
            name = safe_col_name(f"g{group_idx:02d}_{group_fields[group_pos]}", i, seen)
            cols.append((name, "DOUBLE"))
            group_pos += 1
            if group_pos >= 6:
                in_group = False
            continue

        # Trailing columns after all groups
        name = safe_col_name(h_clean if h_clean else f"col_{i}", i, seen)
        cols.append((name, "VARCHAR" if "Desc" in h or "Type" in h or "#" in h
                     else "DOUBLE" if "Hrs" in h or "Dollars" in h or "Variance" in h
                     else "VARCHAR"))

    return cols


# ---------------------------------------------------------------------------
# 6. Reference Tables
# ---------------------------------------------------------------------------

def load_ref_tables(con):
    """Load all ref_*.csv files into DuckDB as ref_ tables."""
    ref_files = sorted(CSV_DIR.glob("ref_*.csv"))
    loaded = 0
    for ref_file in ref_files:
        table_name = ref_file.stem.lower()  # e.g., ref_salespersons_list
        try:
            con.execute(f"DROP TABLE IF EXISTS {table_name}")
            con.execute(f"""
                CREATE TABLE {table_name} AS
                SELECT * FROM read_csv_auto('{ref_file.as_posix()}',
                    header=true,
                    ignore_errors=true,
                    normalize_names=true)
            """)
            count = con.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
            print(f"  {table_name}: {count} rows")
            loaded += 1
        except Exception as e:
            print(f"  {table_name}: FAILED - {e}")
    return loaded


# ---------------------------------------------------------------------------
# 7. Main
# ---------------------------------------------------------------------------

def main():
    print(f"DuckDB Warehouse Loader")
    print(f"Source: {CSV_DIR}")
    print(f"Target: {DB_PATH}\n")

    con = duckdb.connect(str(DB_PATH))

    # Load main tables
    print("=" * 60)
    print("MAIN TABLES")
    print("=" * 60)

    for key, cfg in TABLES.items():
        filepath = CSV_DIR / cfg["file"]
        if not filepath.exists():
            print(f"\nSKIP: {cfg['file']} not found")
            continue

        table_name = cfg["table_name"]
        header_sig = cfg["header_sig"]
        print(f"\n--- {cfg['file']} -> {table_name} ---")

        # Parse the report CSV
        header, data = parse_report_csv(filepath, header_sig)
        if not header:
            print(f"  No header found, skipping")
            continue
        print(f"  Parsed: {len(data):,} data rows, {len(header)} columns")

        # Determine column definitions
        if cfg["columns"] == "auto":
            if key == "wo_labor":
                columns = build_wo_labor_columns(header)
            else:
                columns = auto_columns_from_header(header)
        else:
            columns = cfg["columns"]

        # Validate column count matches
        if len(columns) != len(header):
            print(f"  Column mismatch: defined {len(columns)}, header has {len(header)}")
            print(f"  Falling back to auto-detect")
            columns = auto_columns_from_header(header)

        # Create table and insert
        create_table(con, table_name, columns)
        inserted = insert_rows(con, table_name, columns, data)
        print(f"  Loaded: {inserted:,} rows into {table_name}")

        # Verify
        count = con.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        print(f"  Verified: {count:,} rows in table")

    # Load reference tables
    print(f"\n{'=' * 60}")
    print("REFERENCE TABLES")
    print("=" * 60)
    ref_count = load_ref_tables(con)
    print(f"\n  Loaded {ref_count} reference tables")

    # Summary
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
        print(f"  {tname:<35} {ncols:>4} cols  {row_count:>10,} rows")

    print(f"\n  Total: {len(tables)} tables, {total_rows:,} rows")
    print(f"  Database: {DB_PATH} ({DB_PATH.stat().st_size / 1024 / 1024:.1f}MB)")

    con.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
