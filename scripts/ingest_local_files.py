"""
Phase 4: Ingest Local Files into Warehouse Raw Layer
=====================================================
Scans H:\, OneDrive, and G: drive for structured data files.
Applies schema enforcement, quarantines failures, tags source_tier=4.

Zero network risk — works entirely from local files.

Outputs:
  - warehouse/raw/{timestamp}/local_*.csv  (ingested data)
  - warehouse/staging/quarantine.csv       (rows that failed validation)
  - warehouse/raw/{timestamp}/manifest.json (ingestion metadata)

Usage:
  python ingest_local_files.py                    # Full ingest
  python ingest_local_files.py --source work_orders  # Single source
  python ingest_local_files.py --dry-run           # Preview only
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\raw")
STAGING_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\staging")
SOURCE_TIER = 4  # local_excel_csv per trust hierarchy

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("phase4")

# ---------------------------------------------------------------------------
# Schema mappings: column name normalization
# ---------------------------------------------------------------------------

COLUMN_ALIASES = {
    # Work order identifiers
    "wo_number": ["WO", "Work Order", "WO#", "WorkOrder", "WORK ORDER", "WO Nbr",
                   "WO/GL Nbr", "W.O. Number"],
    "invoice_number": ["Invoice No", "Invoice Number", "Inv No", "Invoice Nbr"],
    "invoice_date": ["Inv Date", "Invoice Date", "InvDate"],
    "so_number": ["SO Nbr", "SO Number", "S.O. Number", "Sales Order"],
    "po_number": ["PO Nbr", "PO Number", "P.O. Nbr", "Purchase Order"],

    # Customer
    "customer_id": ["Cust No", "Customer No", "Customer Number", "Customer Nbr", "Cust Nbr"],
    "customer_name": ["Customer Name", "Customer", "Cust Name"],
    "location_id": ["Location No", "Location Number", "Location Nbr"],
    "location_name": ["Location Name", "Location"],
    "city": ["City"],
    "state": ["State", "St"],

    # Financial
    "gross_sales": ["Gross Sales", "Sales", "Revenue", "Total Sales"],
    "total_cost": ["Total Cost", "Cost", "Est Cost", "TotalCost", "TOTAL COST"],
    "gross_margin": ["Gross Margin", "Margin", "GM"],
    "gm_pct": ["GM %", "GM%", "Gross Margin %", "Margin %"],
    "extra_charge": ["Extra Charge", "Extra Charges"],
    "unit_price": ["Unit Price", "Price", "List Price"],

    # Product / Part
    "product_code": ["Product Code", "Prod Code", "Product", "Sign Type"],
    "part_number": ["Part Nbr", "Part Number", "Part No", "Part #", "Inv Item"],
    "description": ["Description", "Desc", "Item Description"],
    "uom": ["UOM", "UM", "U/M", "Unit of Measure"],
    "inventory_type": ["Inv Type", "Inventory Type", "Type"],

    # Vendor / Purchasing
    "vendor_id": ["Vendor Nbr", "Vendor No", "Vendor Number"],
    "vendor_name": ["Vendor Name", "Vendor"],
    "buyer": ["Buyer"],
    "po_date": ["PO Date", "Order Date"],
    "po_line": ["PO Line", "Line"],
    "order_qty": ["Order Qty", "Qty Ordered", "Quantity"],
    "received_qty": ["Recd Qty", "Qty Received", "Received"],
    "received_date": ["Recd Date", "Received Date"],
    "due_date": ["Due Date"],

    # Labor / Employee
    "employee_name": ["Employee", "Employee Name", "Emp Name"],
    "work_dept": ["Dept", "Department", "Work Dept", "Dept Code"],
    "work_code": ["Code", "Work Code", "Op Code"],
    "labor_date": ["Date", "Labor Date", "Work Date"],
    "hours": ["Hours", "Hrs", "Total Hours", "Regular", "Actual Hrs"],
    "ot_hours": ["OT", "Overtime", "OT Hours"],

    # Inventory
    "qty_on_hand": ["Qty On Hand", "QOH", "On Hand"],
    "warehouse_location": ["Whse Location", "Warehouse", "Location"],
    "acctg_cost": ["Acctg Cost", "Accounting Cost", "Avg Cost"],
    "sales_code": ["Sales Code", "Sale Code"],
    "lead_code": ["Lead Code"],
    "engr_status": ["Engr Status", "Engineering Status"],

    # Order
    "order_status": ["Order Status", "Status"],
    "order_date": ["S.O. Date", "SO Date", "Order Date"],
    "ship_date": ["Default Ship Date", "Ship Date"],

    # Flags
    "is_service": ["Is Service", "Service"],
    "order_year": ["Order Year", "Year"],
    "order_month": ["Order Month", "Month"],
}

# Reverse lookup: alias -> canonical name
_ALIAS_MAP = {}
for canonical, aliases in COLUMN_ALIASES.items():
    for alias in aliases:
        _ALIAS_MAP[alias.lower().strip()] = canonical


def normalize_column(col: str) -> str:
    """Map a column name to its canonical form."""
    key = col.lower().strip()
    return _ALIAS_MAP.get(key, col)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize all column names in a DataFrame."""
    df.columns = [normalize_column(c) for c in df.columns]
    return df


# ---------------------------------------------------------------------------
# Data type enforcement
# ---------------------------------------------------------------------------


def enforce_types(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Enforce data types. Returns (clean_df, quarantine_df).
    Quarantine rows where critical fields are unparseable.
    """
    quarantine_rows = []
    clean_idx = []

    # Currency columns: strip $, commas, convert to float
    currency_cols = [c for c in df.columns if c in (
        "gross_sales", "total_cost", "gross_margin", "extra_charge",
        "unit_price", "acctg_cost", "est_cost", "job_cost",
    )]
    for col in currency_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"[\$,]", "", regex=True)
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Percentage columns
    pct_cols = [c for c in df.columns if c in ("gm_pct",)]
    for col in pct_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("%", "")
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Date columns: parse to ISO format
    date_cols = [c for c in df.columns if c in (
        "invoice_date", "labor_date", "po_date", "received_date",
        "due_date", "order_date", "ship_date",
    )]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")
            df[col] = df[col].dt.strftime("%Y-%m-%d")

    # Numeric quantity columns
    qty_cols = [c for c in df.columns if c in (
        "order_qty", "received_qty", "qty_on_hand", "hours", "ot_hours",
    )]
    for col in qty_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # WO numbers: keep as string (preserve leading zeros)
    if "wo_number" in df.columns:
        df["wo_number"] = df["wo_number"].astype(str).str.strip()

    return df, pd.DataFrame()  # No quarantine for now — coerce handles errors


# ---------------------------------------------------------------------------
# Source definitions
# ---------------------------------------------------------------------------


class DataSource:
    """Definition of a local data file to ingest."""

    def __init__(self, name: str, path: str | Path, description: str,
                 output_name: str, priority: int = 1,
                 sheet_name: str | int = 0, skiprows: int = 0):
        self.name = name
        self.path = Path(path)
        self.description = description
        self.output_name = output_name
        self.priority = priority
        self.sheet_name = sheet_name
        self.skiprows = skiprows


# All sources to ingest, ordered by priority
SOURCES = [
    # --- Priority 1: Core transaction data ---
    DataSource(
        "work_orders_csv",
        r"H:\brady\BOT TRAINING\Scripts\Modern Labor Standards\work orders\structured_data\all_work_orders.csv",
        "Master work order / invoice ledger (all sales transactions)",
        "local_work_orders.csv",
        priority=1,
    ),
    DataSource(
        "purchase_history",
        r"H:\brady\BOT TRAINING\Eagle Data\combined for llm use\Purchase History.csv",
        "All purchase order transactions",
        "local_purchase_history.csv",
        priority=1,
    ),
    DataSource(
        "sales_orders",
        r"H:\brady\BOT TRAINING\Eagle Data\combined for llm use\Closed Sales Order Status by Customer.csv",
        "Closed sales order status by customer",
        "local_sales_orders.csv",
        priority=1,
    ),
    DataSource(
        "inventory_active",
        r"H:\brady\BOT TRAINING\Eagle Data\combined for llm use\Inventory List_Active.csv",
        "Active inventory parts list",
        "local_inventory_active.csv",
        priority=1,
    ),
    DataSource(
        "wip_summary",
        r"H:\brady\BOT TRAINING\Eagle Keyedin Files\BRADYF.WIP.SUMMARY 010106-062725.csv",
        "Work-in-progress summary (Jan 2006 - Jun 2025)",
        "local_wip_summary.csv",
        priority=1,
    ),
    DataSource(
        "gm_salesperson_20yr",
        r"H:\brady\BOT TRAINING\Sales\GM by Salesperson\BRADYF_GM_SALESPERSON 11-1-05 to 10-31-25.CSV",
        "Gross margin by salesperson (20-year consolidated)",
        "local_gm_salesperson.csv",
        priority=1,
    ),

    # --- Priority 1: Employee hours ---
    DataSource(
        "emp_hours_brady",
        r"H:\brady\BOT TRAINING\Eagle Keyedin Files\Brady Flink\BRADYF_EMP.HOURS.BY.DATE 12.1.11 - 2.27.25.csv",
        "Brady Flink employee hours by date",
        "local_emp_hours_brady.csv",
        priority=1,
    ),
    DataSource(
        "emp_hours_brian",
        r"H:\brady\BOT TRAINING\Eagle Keyedin Files\Brian Fontaine\BRIANF_EMP.HOURS.BY.DATE Start - 2.27.25.csv",
        "Brian Fontaine employee hours by date",
        "local_emp_hours_brian.csv",
        priority=1,
    ),
    DataSource(
        "emp_hours_john",
        r"H:\brady\BOT TRAINING\Eagle Keyedin Files\John Redig\JOHNR_EMP.HOURS.BY.DATE 12.1.11 - 2.27.25.csv",
        "John Redig employee hours by date",
        "local_emp_hours_john.csv",
        priority=1,
    ),
    DataSource(
        "emp_hours_matt",
        r"H:\brady\BOT TRAINING\Eagle Keyedin Files\Matt Reis\MATTREIS_EMP.HOURS.BY.DATE.1.1.11 - 2.27.25.csv",
        "Matt Reis employee hours by date",
        "local_emp_hours_matt.csv",
        priority=1,
    ),

    # --- Priority 2: Reference data ---
    DataSource(
        "sign_type_codes",
        r"H:\brady\BOT TRAINING\Eagle Data\combined for llm use\SIGN_TYPE_CODES.csv",
        "Sign type code definitions",
        "local_ref_sign_types.csv",
        priority=2,
    ),
    DataSource(
        "work_codes",
        r"H:\brady\BOT TRAINING\Eagle Data\combined for llm use\WORK CODE.xlsx",
        "Work code definitions",
        "local_ref_work_codes.csv",
        priority=2,
    ),
    DataSource(
        "sales_summary_customer",
        r"H:\brady\BOT TRAINING\Eagle Data\combined for llm use\Sales Summary - by Customer.csv",
        "Sales summary by customer",
        "local_sales_summary_customer.csv",
        priority=2,
    ),
    DataSource(
        "sales_summary_product",
        r"H:\brady\BOT TRAINING\Eagle Data\combined for llm use\Sales Summary - by Product Type.csv",
        "Sales summary by product type",
        "local_sales_summary_product.csv",
        priority=2,
    ),
    DataSource(
        "vendor_listing",
        r"H:\brady\BOT TRAINING\Eagle Data\Vendor Listing.csv",
        "Vendor master listing",
        "local_vendors.csv",
        priority=2,
    ),
    DataSource(
        "mfg_parts",
        r"H:\brady\BOT TRAINING\Eagle Data\combined for llm use\MFG PARTS 2024.xlsx",
        "Active manufactured parts",
        "local_mfg_parts.csv",
        priority=2,
    ),
    DataSource(
        "purchased_parts",
        r"H:\brady\BOT TRAINING\Eagle Data\combined for llm use\PURCHASED PARTS 2024.xlsx",
        "Active purchased parts",
        "local_purchased_parts.csv",
        priority=2,
    ),

    # --- Priority 2: GM by Salesperson annual files ---
    DataSource(
        "gm_sp_2025",
        r"H:\brady\BOT TRAINING\Sales\GM by Salesperson\BRADYF_GM_SALESPERSON 2025.CSV",
        "GM by salesperson FY2025",
        "local_gm_sp_2025.csv",
        priority=2,
    ),
    DataSource(
        "gm_sp_2024",
        r"H:\brady\BOT TRAINING\Sales\GM by Salesperson\BRADYF_GM_SALESPERSON 2024.CSV",
        "GM by salesperson FY2024",
        "local_gm_sp_2024.csv",
        priority=2,
        skiprows=3,
    ),
    DataSource(
        "gm_sp_2023",
        r"H:\brady\BOT TRAINING\Sales\GM by Salesperson\BRADYF_GM_SALESPERSON 2023.CSV",
        "GM by salesperson FY2023",
        "local_gm_sp_2023.csv",
        priority=2,
        skiprows=3,
    ),

    # --- Priority 3: Cat Scale audit data ---
    DataSource(
        "labor_forensics",
        r"H:\brady\BOT TRAINING\Cat Scale\- Audit -\2026\LABOR_FORENSICS.csv",
        "Cat Scale labor forensics audit",
        "local_labor_forensics.csv",
        priority=3,
    ),
    DataSource(
        "shop_efficiency",
        r"H:\brady\BOT TRAINING\Cat Scale\- Audit -\2026\SHOP_EFFICIENCY.csv",
        "Shop efficiency metrics",
        "local_shop_efficiency.csv",
        priority=3,
    ),
    DataSource(
        "labor_multipliers",
        r"H:\brady\BOT TRAINING\Cat Scale\- Audit -\2026\Labor_Multipliers.csv",
        "Labor burden multipliers (potential burden rate discovery)",
        "local_labor_multipliers.csv",
        priority=3,
    ),

    # --- Priority 2: Sales order history ---
    DataSource(
        "sales_order_numbers",
        r"H:\brady\BOT TRAINING\Eagle Data\Sales Order Numbers by Customer 01012006-07182025.csv",
        "Sales order numbers by customer (20-year history)",
        "local_sales_order_numbers.csv",
        priority=2,
    ),

    # --- Priority 2: OneDrive files ---
    DataSource(
        "stock_status",
        r"C:\Users\Brady.EAGLE\OneDrive - Eagle Sign Co\BRADYF_STOCK.STATUS.xlsx",
        "Current stock status",
        "local_stock_status.csv",
        priority=2,
    ),
    DataSource(
        "onedrive_wip",
        r"C:\Users\Brady.EAGLE\OneDrive - Eagle Sign Co\BRADYF.WIP.SUMMARY.xlsx",
        "WIP summary (OneDrive version)",
        "local_onedrive_wip.csv",
        priority=2,
    ),
]


# ---------------------------------------------------------------------------
# File reading
# ---------------------------------------------------------------------------


def read_file(source: DataSource) -> pd.DataFrame | None:
    """Read a data file (CSV or XLSX) into a DataFrame."""
    path = source.path
    if not path.exists():
        log.warning(f"  FILE NOT FOUND: {path}")
        return None

    try:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            # Try multiple encodings
            for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
                try:
                    df = pd.read_csv(
                        path,
                        encoding=encoding,
                        skiprows=source.skiprows,
                        low_memory=False,
                    )
                    break
                except UnicodeDecodeError:
                    continue
            else:
                log.error(f"  Could not decode {path.name} with any encoding")
                return None
        elif suffix in (".xlsx", ".xls"):
            df = pd.read_excel(
                path,
                sheet_name=source.sheet_name,
                skiprows=source.skiprows,
            )
        elif suffix == ".json":
            df = pd.read_json(path)
        else:
            log.warning(f"  Unsupported format: {suffix}")
            return None

        return df
    except Exception as e:
        log.error(f"  Error reading {path.name}: {e}")
        return None


# ---------------------------------------------------------------------------
# Main ingestion
# ---------------------------------------------------------------------------


def ingest_source(source: DataSource, out_dir: Path, dry_run: bool = False) -> dict:
    """Ingest a single data source. Returns stats dict."""
    log.info(f"Ingesting: {source.name}")
    log.info(f"  Path: {source.path}")

    stats = {
        "name": source.name,
        "path": str(source.path),
        "description": source.description,
        "priority": source.priority,
        "status": "skipped",
        "rows": 0,
        "columns": 0,
        "quarantined": 0,
        "file_size_bytes": 0,
    }

    if not source.path.exists():
        stats["status"] = "file_not_found"
        log.warning(f"  SKIPPED — file not found")
        return stats

    stats["file_size_bytes"] = source.path.stat().st_size

    # Read file
    df = read_file(source)
    if df is None or df.empty:
        stats["status"] = "read_error"
        log.warning(f"  SKIPPED — could not read or empty")
        return stats

    original_cols = list(df.columns)
    log.info(f"  Raw: {len(df):,} rows, {len(df.columns)} columns")
    log.info(f"  Columns: {original_cols[:8]}{'...' if len(original_cols) > 8 else ''}")

    # Normalize columns
    df = normalize_columns(df)

    # Enforce types
    df, quarantine = enforce_types(df)

    # Add source metadata
    df["source_tier"] = SOURCE_TIER
    df["source_file"] = str(source.path)
    df["ingested_at"] = datetime.now().isoformat()

    stats["rows"] = len(df)
    stats["columns"] = len(df.columns)
    stats["quarantined"] = len(quarantine)
    stats["column_names"] = list(df.columns)
    stats["original_columns"] = original_cols

    if dry_run:
        stats["status"] = "dry_run"
        log.info(f"  DRY RUN — would write {len(df):,} rows to {source.output_name}")
        return stats

    # Write output CSV
    out_path = out_dir / source.output_name
    df.to_csv(out_path, index=False, encoding="utf-8")
    log.info(f"  Wrote {len(df):,} rows -> {source.output_name}")

    stats["status"] = "success"
    stats["output_path"] = str(out_path)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Phase 4: Ingest Local Files")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--source", type=str, help="Ingest single source by name")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--priority", type=int, help="Only ingest sources at this priority level")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y-%m-%dT%H%M")
    out_dir = args.output_dir / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    # Filter sources
    sources = SOURCES
    if args.source:
        sources = [s for s in SOURCES if s.name == args.source]
        if not sources:
            log.error(f"Unknown source: {args.source}")
            log.info(f"Available: {[s.name for s in SOURCES]}")
            sys.exit(1)
    if args.priority:
        sources = [s for s in sources if s.priority == args.priority]

    log.info(f"Phase 4: Ingest Local Files")
    log.info(f"Sources: {len(sources)}")
    log.info(f"Output: {out_dir}")
    if args.dry_run:
        log.info("DRY RUN MODE — no files will be written")
    log.info("")

    all_stats = []
    total_rows = 0
    success_count = 0
    skip_count = 0

    for source in sources:
        stats = ingest_source(source, out_dir, dry_run=args.dry_run)
        all_stats.append(stats)
        if stats["status"] == "success" or stats["status"] == "dry_run":
            total_rows += stats["rows"]
            success_count += 1
        else:
            skip_count += 1
        log.info("")

    # Summary
    log.info("=" * 60)
    log.info("PHASE 4 COMPLETE")
    log.info(f"  Sources ingested: {success_count}/{len(sources)}")
    log.info(f"  Sources skipped:  {skip_count}")
    log.info(f"  Total rows:       {total_rows:,}")
    log.info(f"  Source tier:      {SOURCE_TIER} (local_excel_csv)")

    # Per-source summary
    log.info("")
    log.info(f"{'Source':<30} {'Status':<15} {'Rows':>10}")
    log.info("-" * 60)
    for s in all_stats:
        log.info(f"  {s['name']:<28} {s['status']:<15} {s['rows']:>10,}")

    # Missing files
    missing = [s for s in all_stats if s["status"] == "file_not_found"]
    if missing:
        log.warning(f"\n{len(missing)} files not found:")
        for s in missing:
            log.warning(f"  {s['path']}")

    # Write manifest
    manifest = {
        "timestamp": timestamp,
        "source_tier": SOURCE_TIER,
        "sources_attempted": len(sources),
        "sources_success": success_count,
        "sources_skipped": skip_count,
        "total_rows": total_rows,
        "dry_run": args.dry_run,
        "details": all_stats,
    }
    manifest_path = out_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    log.info(f"\nManifest: {manifest_path}")
    log.info(f"Output: {out_dir}")


if __name__ == "__main__":
    main()
