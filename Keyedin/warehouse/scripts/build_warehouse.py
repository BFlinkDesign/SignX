"""
Phase 5: Build Unified Warehouse (SQLite)
==========================================
Combines Phase 1 (HTML parsed WOs + detail) and Phase 4 (local file ingestion)
into a single SQLite database with tiered trust upsert logic.

Trust hierarchy:
  1 = erp_fresh_scrape (Phase 3 - future)
  2 = informer_bi_export (Phase 2 - future)
  3 = html_reparse (Phase 1)
  4 = local_excel_csv (Phase 4)

Usage:
  python build_warehouse.py                    # Full build from latest data
  python build_warehouse.py --phase1-dir DIR   # Specify Phase 1 output
  python build_warehouse.py --phase4-dir DIR   # Specify Phase 4 output
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RAW_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\raw")
PROD_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\production")
DB_PATH = PROD_DIR / "eagle_warehouse.db"

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("warehouse")

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

SCHEMA_DDL = """
-- Work orders: the backbone
CREATE TABLE IF NOT EXISTS work_orders (
    wo_number TEXT PRIMARY KEY,
    source_tier INTEGER,
    source_file TEXT,
    customer_id TEXT,
    customer_name TEXT,
    location TEXT,
    status TEXT,
    date_completed TEXT,
    sign_type TEXT,
    sales_code TEXT,
    estimator TEXT,
    quote_nbr TEXT,
    part_number TEXT,
    price_class_code TEXT,
    description TEXT,
    -- cost fields
    total_labor_cost REAL,
    total_burden_cost REAL,
    total_material_cost REAL,
    total_outplant_cost REAL,
    total_use_tax REAL,
    total_cost REAL,
    quoted_price REAL,
    sale_price REAL,
    billing REAL,
    gross_margin REAL,
    gm_pct REAL
);

-- Labor detail transactions (individual time entries)
CREATE TABLE IF NOT EXISTS labor_detail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wo_number TEXT,
    labor_date TEXT,
    work_dept TEXT,
    work_code TEXT,
    employee_name TEXT,
    actual_hrs REAL,
    job_cost REAL,
    source_tier INTEGER,
    source_file TEXT,
    FOREIGN KEY (wo_number) REFERENCES work_orders(wo_number)
);

-- Labor summary (per WO/dept/code rollup with est vs actual)
CREATE TABLE IF NOT EXISTS labor_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wo_number TEXT,
    work_dept TEXT,
    work_code TEXT,
    est_hrs REAL,
    actual_hrs REAL,
    hrs_variance REAL,
    est_cost REAL,
    job_cost REAL,
    cost_variance REAL,
    description TEXT,
    source_tier INTEGER,
    source_file TEXT,
    FOREIGN KEY (wo_number) REFERENCES work_orders(wo_number)
);

-- Material transactions
CREATE TABLE IF NOT EXISTS material_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wo_number TEXT,
    material_date TEXT,
    work_dept TEXT,
    inventory_item TEXT,
    uom TEXT,
    est_qty REAL,
    actual_qty REAL,
    qty_variance REAL,
    est_cost REAL,
    job_cost REAL,
    cost_variance REAL,
    description TEXT,
    source_tier INTEGER,
    source_file TEXT,
    FOREIGN KEY (wo_number) REFERENCES work_orders(wo_number)
);

-- Outplant/subcontractor transactions
CREATE TABLE IF NOT EXISTS outplant_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wo_number TEXT,
    outplant_date TEXT,
    work_dept TEXT,
    sub_contractor TEXT,
    uom TEXT,
    est_qty REAL,
    actual_qty REAL,
    qty_variance REAL,
    est_cost REAL,
    job_cost REAL,
    cost_variance REAL,
    description TEXT,
    source_tier INTEGER,
    source_file TEXT,
    FOREIGN KEY (wo_number) REFERENCES work_orders(wo_number)
);

-- Invoices / sales transactions (from Phase 4 work_orders CSV)
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT,
    invoice_date TEXT,
    product_code TEXT,
    customer_id TEXT,
    customer_name TEXT,
    location_id TEXT,
    location_name TEXT,
    city TEXT,
    state TEXT,
    gross_sales REAL,
    total_cost REAL,
    gross_margin REAL,
    gm_pct REAL,
    extra_charge REAL,
    salesperson TEXT,
    wo_number TEXT,
    source_tier INTEGER,
    source_file TEXT
);

-- Inventory (current state)
CREATE TABLE IF NOT EXISTS inventory (
    part_number TEXT PRIMARY KEY,
    description TEXT,
    inventory_type TEXT,
    sales_code TEXT,
    lead_code TEXT,
    engr_status TEXT,
    warehouse_location TEXT,
    qty_on_hand REAL,
    uom TEXT,
    unit_price REAL,
    acctg_cost REAL,
    source_tier INTEGER,
    source_file TEXT
);

-- Purchase orders
CREATE TABLE IF NOT EXISTS purchase_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_number TEXT,
    po_line TEXT,
    po_date TEXT,
    vendor_id TEXT,
    vendor_name TEXT,
    buyer TEXT,
    order_status TEXT,
    wo_number TEXT,
    part_number TEXT,
    description TEXT,
    uom TEXT,
    order_qty REAL,
    received_qty REAL,
    received_date TEXT,
    due_date TEXT,
    unit_price REAL,
    source_tier INTEGER,
    source_file TEXT
);

-- Customers (derived from sales summary)
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT,
    customer_type TEXT,
    invoice_lines INTEGER,
    gross_sales REAL,
    total_cost REAL,
    gross_margin REAL,
    gm_pct REAL,
    source_tier INTEGER,
    source_file TEXT
);

-- Sales orders
CREATE TABLE IF NOT EXISTS sales_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT,
    po_number TEXT,
    so_number TEXT,
    order_date TEXT,
    ship_date TEXT,
    invoices TEXT,
    order_status TEXT,
    source_tier INTEGER,
    source_file TEXT
);

-- Employees (derived from labor data)
CREATE TABLE IF NOT EXISTS employees (
    employee_name TEXT PRIMARY KEY,
    first_seen TEXT,
    last_seen TEXT,
    total_hours REAL,
    primary_dept TEXT,
    departments TEXT,
    is_active INTEGER,
    source_tier INTEGER
);

-- Reference tables
CREATE TABLE IF NOT EXISTS ref_work_codes (
    code TEXT PRIMARY KEY,
    description TEXT,
    work_dept TEXT
);

CREATE TABLE IF NOT EXISTS ref_sign_types (
    code TEXT PRIMARY KEY,
    description TEXT
);

-- Shop efficiency metrics
CREATE TABLE IF NOT EXISTS shop_efficiency (
    work_code TEXT PRIMARY KEY,
    total_est_hrs REAL,
    total_actual_hrs REAL,
    job_count INTEGER,
    efficiency_score REAL,
    description TEXT,
    hours_variance REAL,
    variance_pct REAL,
    is_bottleneck INTEGER,
    source_tier INTEGER
);

-- Labor multipliers
CREATE TABLE IF NOT EXISTS labor_multipliers (
    work_code TEXT PRIMARY KEY,
    description TEXT,
    count INTEGER,
    total_hrs REAL,
    avg_hrs REAL,
    min_hrs REAL,
    max_hrs REAL,
    std_dev REAL,
    source_tier INTEGER
);

-- GM by salesperson detail
CREATE TABLE IF NOT EXISTS gm_by_salesperson (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT,
    invoice_date TEXT,
    product_code TEXT,
    customer_id TEXT,
    customer_name TEXT,
    gross_sales REAL,
    total_cost REAL,
    gross_margin REAL,
    gm_pct REAL,
    extra_charge REAL,
    salesperson_1 TEXT,
    comm_rate_1 REAL,
    salesperson_2 TEXT,
    comm_rate_2 REAL,
    location_id TEXT,
    location_name TEXT,
    city TEXT,
    state TEXT,
    source_tier INTEGER,
    source_file TEXT
);

-- Cat Scale labor forensics
CREATE TABLE IF NOT EXISTS labor_forensics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wo_number TEXT,
    date_worked TEXT,
    work_dept TEXT,
    work_code TEXT,
    employee_name TEXT,
    actual_hrs REAL,
    labor_cost REAL,
    source_tier INTEGER,
    source_file TEXT
);

-- Warehouse metadata
CREATE TABLE IF NOT EXISTS warehouse_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_labor_detail_wo ON labor_detail(wo_number);
CREATE INDEX IF NOT EXISTS idx_labor_detail_emp ON labor_detail(employee_name);
CREATE INDEX IF NOT EXISTS idx_labor_detail_dept ON labor_detail(work_dept);
CREATE INDEX IF NOT EXISTS idx_labor_detail_date ON labor_detail(labor_date);
CREATE INDEX IF NOT EXISTS idx_labor_summary_wo ON labor_summary(wo_number);
CREATE INDEX IF NOT EXISTS idx_material_wo ON material_transactions(wo_number);
CREATE INDEX IF NOT EXISTS idx_outplant_wo ON outplant_transactions(wo_number);
CREATE INDEX IF NOT EXISTS idx_invoices_cust ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_wo_customer ON work_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_wo_sign_type ON work_orders(sign_type);
CREATE INDEX IF NOT EXISTS idx_wo_estimator ON work_orders(estimator);
CREATE INDEX IF NOT EXISTS idx_wo_date ON work_orders(date_completed);
CREATE INDEX IF NOT EXISTS idx_po_vendor ON purchase_orders(vendor_id);
CREATE INDEX IF NOT EXISTS idx_sales_orders_so ON sales_orders(so_number);
CREATE INDEX IF NOT EXISTS idx_forensics_wo ON labor_forensics(wo_number);
CREATE INDEX IF NOT EXISTS idx_forensics_emp ON labor_forensics(employee_name);
CREATE INDEX IF NOT EXISTS idx_gm_sp_cust ON gm_by_salesperson(customer_id);
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def find_latest_dir_with(raw_dir: Path, filename: str) -> Path | None:
    """Find the most recent timestamped directory containing the given file."""
    candidates = []
    for d in raw_dir.iterdir():
        if d.is_dir() and (d / filename).exists():
            candidates.append(d)
    if not candidates:
        return None
    return sorted(candidates)[-1]


def safe_read_csv(path: Path, **kwargs) -> pd.DataFrame | None:
    """Read CSV with encoding fallback."""
    for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False, **kwargs)
        except UnicodeDecodeError:
            continue
    log.error(f"  Could not decode {path.name}")
    return None


def load_phase1(phase1_dir: Path) -> dict:
    """Load all Phase 1 CSVs into DataFrames."""
    data = {}
    files = {
        "wo_headers": "wo_headers.csv",
        "labor_detail": "labor_detail.csv",
        "labor_summary": "labor_summary.csv",
        "material_detail": "material_detail.csv",
        "outplant_detail": "outplant_detail.csv",
    }
    for key, fname in files.items():
        path = phase1_dir / fname
        if path.exists():
            df = safe_read_csv(path)
            if df is not None:
                data[key] = df
                log.info(f"  Phase 1 {key}: {len(df):,} rows")
            else:
                log.warning(f"  Phase 1 {key}: read error")
        else:
            log.warning(f"  Phase 1 {key}: not found at {path}")
    return data


def load_phase4(phase4_dir: Path) -> dict:
    """Load all Phase 4 CSVs into DataFrames."""
    data = {}
    for f in phase4_dir.glob("local_*.csv"):
        key = f.stem  # e.g., local_work_orders
        df = safe_read_csv(f)
        if df is not None:
            data[key] = df
            log.info(f"  Phase 4 {key}: {len(df):,} rows")
    return data


# ---------------------------------------------------------------------------
# Table loaders
# ---------------------------------------------------------------------------


def load_work_orders(conn: sqlite3.Connection, p1: dict):
    """Load work orders from Phase 1 wo_headers."""
    df = p1.get("wo_headers")
    if df is None:
        log.warning("  No wo_headers data — skipping work_orders table")
        return 0

    cols = [
        "wo_number", "source_tier", "source_file", "customer_id", "customer_name",
        "location", "status", "date_completed", "sign_type", "sales_code",
        "estimator", "quote_nbr", "part_number", "price_class_code", "description",
        "total_labor_cost", "total_burden_cost", "total_material_cost",
        "total_outplant_cost", "total_use_tax", "total_cost",
        "quoted_price", "sale_price", "billing", "gross_margin", "gm_pct",
    ]
    # Only include columns that exist
    available = [c for c in cols if c in df.columns]
    sub = df[available].copy()

    sub.to_sql("work_orders", conn, if_exists="replace", index=False)
    return len(sub)


def load_labor_detail(conn: sqlite3.Connection, p1: dict):
    """Load labor detail from Phase 1."""
    df = p1.get("labor_detail")
    if df is None:
        return 0
    cols = ["wo_number", "labor_date", "work_dept", "work_code",
            "employee_name", "actual_hrs", "job_cost", "source_tier", "source_file"]
    available = [c for c in cols if c in df.columns]
    df[available].to_sql("labor_detail", conn, if_exists="replace", index=False)
    return len(df)


def load_labor_summary(conn: sqlite3.Connection, p1: dict):
    """Load labor summary from Phase 1."""
    df = p1.get("labor_summary")
    if df is None:
        return 0
    cols = ["wo_number", "work_dept", "work_code", "est_hrs", "actual_hrs",
            "hrs_variance", "est_cost", "job_cost", "cost_variance",
            "description", "source_tier", "source_file"]
    available = [c for c in cols if c in df.columns]
    df[available].to_sql("labor_summary", conn, if_exists="replace", index=False)
    return len(df)


def load_material_transactions(conn: sqlite3.Connection, p1: dict):
    """Load material transactions from Phase 1."""
    df = p1.get("material_detail")
    if df is None:
        return 0
    cols = ["wo_number", "material_date", "work_dept", "inventory_item", "uom",
            "est_qty", "actual_qty", "qty_variance", "est_cost", "job_cost",
            "cost_variance", "description", "source_tier", "source_file"]
    available = [c for c in cols if c in df.columns]
    df[available].to_sql("material_transactions", conn, if_exists="replace", index=False)
    return len(df)


def load_outplant_transactions(conn: sqlite3.Connection, p1: dict):
    """Load outplant transactions from Phase 1."""
    df = p1.get("outplant_detail")
    if df is None:
        return 0
    cols = ["wo_number", "outplant_date", "work_dept", "sub_contractor", "uom",
            "est_qty", "actual_qty", "qty_variance", "est_cost", "job_cost",
            "cost_variance", "description", "source_tier", "source_file"]
    available = [c for c in cols if c in df.columns]
    df[available].to_sql("outplant_transactions", conn, if_exists="replace", index=False)
    return len(df)


def load_invoices(conn: sqlite3.Connection, p4: dict):
    """Load invoices from Phase 4 work_orders (actually invoice-level data)."""
    df = p4.get("local_work_orders")
    if df is None:
        return 0
    col_map = {
        "invoice_number": "invoice_number",
        "invoice_date": "invoice_date",
        "product_code": "product_code",
        "customer_id": "customer_id",
        "customer_name": "customer_name",
        "location_id": "location_id",
        "location_name": "location_name",
        "city": "city",
        "state": "state",
        "gross_sales": "gross_sales",
        "total_cost": "total_cost",
        "gross_margin": "gross_margin",
        "gm_pct": "gm_pct",
        "extra_charge": "extra_charge",
        "wo_number": "wo_number",
        "source_tier": "source_tier",
        "source_file": "source_file",
    }
    available = {k: v for k, v in col_map.items() if k in df.columns}
    sub = df[list(available.keys())].rename(columns=available)

    # Extract salesperson columns if present
    for sp_col in ["Salesperson", "Salesperson #1"]:
        if sp_col in df.columns:
            sub["salesperson"] = df[sp_col]
            break

    sub.to_sql("invoices", conn, if_exists="replace", index=False)
    return len(sub)


def load_inventory(conn: sqlite3.Connection, p4: dict):
    """Load inventory from Phase 4."""
    df = p4.get("local_inventory_active")
    if df is None:
        return 0
    cols = ["part_number", "description", "inventory_type", "sales_code",
            "lead_code", "engr_status", "warehouse_location", "qty_on_hand",
            "uom", "unit_price", "acctg_cost", "source_tier", "source_file"]
    available = [c for c in cols if c in df.columns]
    df[available].to_sql("inventory", conn, if_exists="replace", index=False)
    return len(df)


def load_purchase_orders(conn: sqlite3.Connection, p4: dict):
    """Load purchase orders from Phase 4."""
    df = p4.get("local_purchase_history")
    if df is None:
        return 0
    col_map = {
        "po_number": "po_number",
        "po_line": "po_line",
        "po_date": "po_date",
        "vendor_id": "vendor_id",
        "vendor_name": "vendor_name",
        "buyer": "buyer",
        "order_status": "order_status",
        "wo_number": "wo_number",
        "part_number": "part_number",
        "description": "description",
        "uom": "uom",
        "order_qty": "order_qty",
        "received_qty": "received_qty",
        "received_date": "received_date",
        "due_date": "due_date",
        "unit_price": "unit_price",
        "source_tier": "source_tier",
        "source_file": "source_file",
    }
    available = {k: v for k, v in col_map.items() if k in df.columns}
    sub = df[list(available.keys())].rename(columns=available)
    sub.to_sql("purchase_orders", conn, if_exists="replace", index=False)
    return len(sub)


def load_customers(conn: sqlite3.Connection, p4: dict):
    """Load customer summary from Phase 4."""
    df = p4.get("local_sales_summary_customer")
    if df is None:
        return 0
    col_map = {
        "customer_id": "customer_id",
        "customer_name": "customer_name",
        "Cust Type": "customer_type",
        "Invoice Lines": "invoice_lines",
        "Gross Sales (Total)": "gross_sales",
        "Total Cost (Total)": "total_cost",
        "gross_margin": "gross_margin",
        "gm_pct": "gm_pct",
        "source_tier": "source_tier",
        "source_file": "source_file",
    }
    available = {k: v for k, v in col_map.items() if k in df.columns}
    sub = df[list(available.keys())].rename(columns=available)
    sub.to_sql("customers", conn, if_exists="replace", index=False)
    return len(sub)


def load_sales_orders(conn: sqlite3.Connection, p4: dict):
    """Load sales orders from Phase 4."""
    df = p4.get("local_sales_orders")
    if df is None:
        return 0
    col_map = {
        "customer_name": "customer_name",
        "po_number": "po_number",
        "so_number": "so_number",
        "order_date": "order_date",
        "ship_date": "ship_date",
        "Invoices": "invoices",
        "order_status": "order_status",
        "source_tier": "source_tier",
        "source_file": "source_file",
    }
    available = {k: v for k, v in col_map.items() if k in df.columns}
    sub = df[list(available.keys())].rename(columns=available)
    sub.to_sql("sales_orders", conn, if_exists="replace", index=False)
    return len(sub)


def load_ref_work_codes(conn: sqlite3.Connection, p4: dict):
    """Load work code reference from Phase 4."""
    df = p4.get("local_ref_work_codes")
    if df is None:
        return 0
    col_map = {"work_code": "code", "Code": "code", "description": "description",
               "Description": "description", "work_dept": "work_dept", "Work Dept": "work_dept"}
    rename = {}
    for old, new in col_map.items():
        if old in df.columns:
            rename[old] = new
    sub = df.rename(columns=rename)
    target_cols = ["code", "description", "work_dept"]
    available = [c for c in target_cols if c in sub.columns]
    sub[available].to_sql("ref_work_codes", conn, if_exists="replace", index=False)
    return len(sub)


def load_ref_sign_types(conn: sqlite3.Connection, p4: dict):
    """Load sign type reference from Phase 4."""
    df = p4.get("local_ref_sign_types")
    if df is None:
        return 0
    col_map = {"Code": "code", "Description": "description",
               "work_code": "code", "description": "description"}
    rename = {}
    for old, new in col_map.items():
        if old in df.columns:
            rename[old] = new
    sub = df.rename(columns=rename)
    target_cols = ["code", "description"]
    available = [c for c in target_cols if c in sub.columns]
    sub[available].to_sql("ref_sign_types", conn, if_exists="replace", index=False)
    return len(sub)


def load_shop_efficiency(conn: sqlite3.Connection, p4: dict):
    """Load shop efficiency from Phase 4."""
    df = p4.get("local_shop_efficiency")
    if df is None:
        return 0
    col_map = {
        "Work_Code": "work_code", "Total_Est_Hrs": "total_est_hrs",
        "Total_Actual_Hrs": "total_actual_hrs", "Job_Count": "job_count",
        "Efficiency_Score": "efficiency_score", "description": "description",
        "Hours_Variance": "hours_variance", "Variance_Pct": "variance_pct",
        "Is_Bottleneck": "is_bottleneck", "source_tier": "source_tier",
    }
    available = {k: v for k, v in col_map.items() if k in df.columns}
    sub = df[list(available.keys())].rename(columns=available)
    sub.to_sql("shop_efficiency", conn, if_exists="replace", index=False)
    return len(sub)


def load_labor_multipliers(conn: sqlite3.Connection, p4: dict):
    """Load labor multipliers from Phase 4."""
    df = p4.get("local_labor_multipliers")
    if df is None:
        return 0
    col_map = {
        "Work_Code": "work_code", "description": "description",
        "Count": "count", "Total_Hrs": "total_hrs",
        "Avg_Hrs": "avg_hrs", "Min_Hrs": "min_hrs",
        "Max_Hrs": "max_hrs", "Std_Dev": "std_dev",
        "source_tier": "source_tier",
    }
    available = {k: v for k, v in col_map.items() if k in df.columns}
    sub = df[list(available.keys())].rename(columns=available)
    sub.to_sql("labor_multipliers", conn, if_exists="replace", index=False)
    return len(sub)


def load_labor_forensics(conn: sqlite3.Connection, p4: dict):
    """Load Cat Scale labor forensics from Phase 4."""
    df = p4.get("local_labor_forensics")
    if df is None:
        return 0
    col_map = {
        "Work_Order": "wo_number", "Date_Worked": "date_worked",
        "Work_Dept": "work_dept", "Work_Code": "work_code",
        "Employee_Name": "employee_name", "Actual_Hrs": "actual_hrs",
        "Labor_Cost": "labor_cost", "source_tier": "source_tier",
        "source_file": "source_file",
    }
    available = {k: v for k, v in col_map.items() if k in df.columns}
    sub = df[list(available.keys())].rename(columns=available)
    sub.to_sql("labor_forensics", conn, if_exists="replace", index=False)
    return len(sub)


def load_gm_by_salesperson(conn: sqlite3.Connection, p4: dict):
    """Load GM by salesperson from Phase 4 annual files + 20yr consolidated."""
    frames = []
    for key in ["local_gm_sp_2023", "local_gm_sp_2024", "local_gm_sp_2025"]:
        df = p4.get(key)
        if df is not None:
            frames.append(df)

    if not frames:
        return 0

    combined = pd.concat(frames, ignore_index=True)
    # These files have proper column headers after skiprows
    col_map = {
        "Invoice No": "invoice_number", "invoice_number": "invoice_number",
        "Inv Date": "invoice_date", "invoice_date": "invoice_date",
        "Prod Code": "product_code", "product_code": "product_code",
        "Cust No": "customer_id", "customer_id": "customer_id",
        "Customer Name": "customer_name", "customer_name": "customer_name",
        "Gross Sales": "gross_sales", "gross_sales": "gross_sales",
        "Total Cost": "total_cost", "total_cost": "total_cost",
        "Gross Margin": "gross_margin", "gross_margin": "gross_margin",
        "GM %": "gm_pct", "gm_pct": "gm_pct",
        "Extra Charge": "extra_charge", "extra_charge": "extra_charge",
        "Salesperson #1": "salesperson_1",
        "Comm Rate #1": "comm_rate_1",
        "Salesperson #2": "salesperson_2",
        "Comm Rate #2": "comm_rate_2",
        "Location No": "location_id", "location_id": "location_id",
        "Location Name": "location_name", "location_name": "location_name",
        "City": "city", "city": "city",
        "State": "state", "state": "state",
        "source_tier": "source_tier",
        "source_file": "source_file",
    }
    rename = {}
    for old, new in col_map.items():
        if old in combined.columns and old != new:
            rename[old] = new
    combined = combined.rename(columns=rename)

    target_cols = [
        "invoice_number", "invoice_date", "product_code", "customer_id",
        "customer_name", "gross_sales", "total_cost", "gross_margin",
        "gm_pct", "extra_charge", "salesperson_1", "comm_rate_1",
        "salesperson_2", "comm_rate_2", "location_id", "location_name",
        "city", "state", "source_tier", "source_file",
    ]
    available = [c for c in target_cols if c in combined.columns]
    combined[available].to_sql("gm_by_salesperson", conn, if_exists="replace", index=False)
    return len(combined)


def derive_employees(conn: sqlite3.Connection):
    """Derive employees table from labor_detail data."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO employees (
            employee_name, first_seen, last_seen, total_hours,
            primary_dept, departments, is_active, source_tier
        )
        SELECT
            employee_name,
            MIN(labor_date) as first_seen,
            MAX(labor_date) as last_seen,
            SUM(actual_hrs) as total_hours,
            (SELECT work_dept FROM labor_detail ld2
             WHERE ld2.employee_name = ld.employee_name
             GROUP BY work_dept ORDER BY SUM(actual_hrs) DESC LIMIT 1
            ) as primary_dept,
            GROUP_CONCAT(DISTINCT work_dept) as departments,
            CASE WHEN MAX(labor_date) >= date('now', '-180 days') THEN 1 ELSE 0 END as is_active,
            MIN(source_tier) as source_tier
        FROM labor_detail ld
        WHERE employee_name IS NOT NULL AND employee_name != ''
        GROUP BY employee_name
    """)
    count = cursor.rowcount
    conn.commit()
    return count


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_warehouse(conn: sqlite3.Connection) -> dict:
    """Run validation checks on the warehouse."""
    cursor = conn.cursor()
    results = {}

    tables = [
        "work_orders", "labor_detail", "labor_summary",
        "material_transactions", "outplant_transactions",
        "invoices", "inventory", "purchase_orders", "customers",
        "sales_orders", "employees", "ref_work_codes", "ref_sign_types",
        "shop_efficiency", "labor_multipliers", "labor_forensics",
        "gm_by_salesperson",
    ]

    total_rows = 0
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            results[table] = count
            total_rows += count
        except sqlite3.OperationalError:
            results[table] = 0

    results["_total_rows"] = total_rows

    # Cross-validation: WO count consistency
    cursor.execute("SELECT COUNT(DISTINCT wo_number) FROM work_orders")
    wo_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT wo_number) FROM labor_detail")
    labor_wo_count = cursor.fetchone()[0]
    results["_wo_count"] = wo_count
    results["_labor_wo_count"] = labor_wo_count

    # Source tier distribution
    cursor.execute("""
        SELECT source_tier, COUNT(*) FROM work_orders
        GROUP BY source_tier ORDER BY source_tier
    """)
    results["_wo_by_tier"] = dict(cursor.fetchall())

    # Estimator coverage
    cursor.execute("""
        SELECT COUNT(*) FROM work_orders WHERE estimator IS NOT NULL AND estimator != ''
    """)
    results["_wo_with_estimator"] = cursor.fetchone()[0]

    # Employee count
    cursor.execute("SELECT COUNT(*) FROM employees")
    results["_employee_count"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM employees WHERE is_active = 1")
    results["_active_employees"] = cursor.fetchone()[0]

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Phase 5: Build Unified Warehouse")
    parser.add_argument("--phase1-dir", type=Path, help="Phase 1 output directory")
    parser.add_argument("--phase4-dir", type=Path, help="Phase 4 output directory")
    parser.add_argument("--db-path", type=Path, default=DB_PATH)
    args = parser.parse_args()

    # Auto-detect directories
    phase1_dir = args.phase1_dir or find_latest_dir_with(RAW_DIR, "wo_headers.csv")
    phase4_dir = args.phase4_dir or find_latest_dir_with(RAW_DIR, "local_work_orders.csv")

    if not phase1_dir:
        log.error("No Phase 1 data found (wo_headers.csv). Run parse_full_cost_detail.py first.")
        sys.exit(1)

    log.info("=" * 60)
    log.info("PHASE 5: Build Unified Warehouse")
    log.info("=" * 60)
    log.info(f"  Phase 1 data: {phase1_dir}")
    log.info(f"  Phase 4 data: {phase4_dir or 'NOT FOUND'}")
    log.info(f"  Database: {args.db_path}")
    log.info("")

    # Load source data
    log.info("Loading Phase 1 data...")
    p1 = load_phase1(phase1_dir)
    log.info("")

    p4 = {}
    if phase4_dir:
        log.info("Loading Phase 4 data...")
        p4 = load_phase4(phase4_dir)
        log.info("")

    # Create database
    PROD_DIR.mkdir(parents=True, exist_ok=True)
    if args.db_path.exists():
        log.info(f"Removing existing database: {args.db_path}")
        args.db_path.unlink()

    conn = sqlite3.connect(str(args.db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # Create schema
    log.info("Creating schema...")
    conn.executescript(SCHEMA_DDL)
    conn.commit()

    # Load tables
    log.info("")
    log.info("Loading tables...")
    stats = {}

    # Phase 1 tables
    stats["work_orders"] = load_work_orders(conn, p1)
    log.info(f"  work_orders: {stats['work_orders']:,} rows")

    stats["labor_detail"] = load_labor_detail(conn, p1)
    log.info(f"  labor_detail: {stats['labor_detail']:,} rows")

    stats["labor_summary"] = load_labor_summary(conn, p1)
    log.info(f"  labor_summary: {stats['labor_summary']:,} rows")

    stats["material_transactions"] = load_material_transactions(conn, p1)
    log.info(f"  material_transactions: {stats['material_transactions']:,} rows")

    stats["outplant_transactions"] = load_outplant_transactions(conn, p1)
    log.info(f"  outplant_transactions: {stats['outplant_transactions']:,} rows")

    # Phase 4 tables
    stats["invoices"] = load_invoices(conn, p4)
    log.info(f"  invoices: {stats['invoices']:,} rows")

    stats["inventory"] = load_inventory(conn, p4)
    log.info(f"  inventory: {stats['inventory']:,} rows")

    stats["purchase_orders"] = load_purchase_orders(conn, p4)
    log.info(f"  purchase_orders: {stats['purchase_orders']:,} rows")

    stats["customers"] = load_customers(conn, p4)
    log.info(f"  customers: {stats['customers']:,} rows")

    stats["sales_orders"] = load_sales_orders(conn, p4)
    log.info(f"  sales_orders: {stats['sales_orders']:,} rows")

    stats["ref_work_codes"] = load_ref_work_codes(conn, p4)
    log.info(f"  ref_work_codes: {stats['ref_work_codes']:,} rows")

    stats["ref_sign_types"] = load_ref_sign_types(conn, p4)
    log.info(f"  ref_sign_types: {stats['ref_sign_types']:,} rows")

    stats["shop_efficiency"] = load_shop_efficiency(conn, p4)
    log.info(f"  shop_efficiency: {stats['shop_efficiency']:,} rows")

    stats["labor_multipliers"] = load_labor_multipliers(conn, p4)
    log.info(f"  labor_multipliers: {stats['labor_multipliers']:,} rows")

    stats["labor_forensics"] = load_labor_forensics(conn, p4)
    log.info(f"  labor_forensics: {stats['labor_forensics']:,} rows")

    stats["gm_by_salesperson"] = load_gm_by_salesperson(conn, p4)
    log.info(f"  gm_by_salesperson: {stats['gm_by_salesperson']:,} rows")

    # Derived tables
    log.info("")
    log.info("Deriving employee table from labor data...")
    emp_count = derive_employees(conn)
    stats["employees"] = emp_count
    log.info(f"  employees: {emp_count:,} rows")

    # Store metadata
    now = datetime.now().isoformat()
    meta = {
        "built_at": now,
        "phase1_dir": str(phase1_dir),
        "phase4_dir": str(phase4_dir) if phase4_dir else "N/A",
        "table_stats": json.dumps(stats),
    }
    for key, val in meta.items():
        conn.execute(
            "INSERT OR REPLACE INTO warehouse_meta (key, value) VALUES (?, ?)",
            (key, val),
        )
    conn.commit()

    # Validate
    log.info("")
    log.info("Running validation...")
    validation = validate_warehouse(conn)

    total_rows = sum(v for k, v in stats.items() if isinstance(v, int))

    log.info("")
    log.info("=" * 60)
    log.info("WAREHOUSE BUILD COMPLETE")
    log.info("=" * 60)
    log.info(f"  Database: {args.db_path}")
    log.info(f"  Size: {args.db_path.stat().st_size / 1024 / 1024:.1f} MB")
    log.info(f"  Total rows: {total_rows:,}")
    log.info(f"  Tables populated: {sum(1 for v in stats.values() if v > 0)}")
    log.info(f"  Work orders: {validation.get('_wo_count', 0):,}")
    log.info(f"  WOs with labor data: {validation.get('_labor_wo_count', 0):,}")
    log.info(f"  WOs with estimator: {validation.get('_wo_with_estimator', 0):,}")
    log.info(f"  Employees: {validation.get('_employee_count', 0):,}")
    log.info(f"  Active employees: {validation.get('_active_employees', 0):,}")
    log.info(f"  Source tiers: {validation.get('_wo_by_tier', {})}")

    # Write manifest
    manifest = {
        "built_at": now,
        "db_path": str(args.db_path),
        "phase1_dir": str(phase1_dir),
        "phase4_dir": str(phase4_dir) if phase4_dir else None,
        "stats": stats,
        "validation": {k: v for k, v in validation.items()},
        "total_rows": total_rows,
    }
    manifest_path = args.db_path.parent / "warehouse_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    log.info(f"  Manifest: {manifest_path}")

    conn.close()


if __name__ == "__main__":
    main()
