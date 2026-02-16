"""
Eagle Sign Quote-to-Files Lookup Tool

Looks up ESC quote/job numbers against:
  - G: drive file index (esc_file_index_clean.csv)
  - SignX-Warehouse data (so_contracts_parsed.csv)

Usage:
  python lookup_job.py 40654
  python lookup_job.py 40654 40655 40660
"""

import csv
import sys
import os
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
ESC_INDEX = SCRIPT_DIR / "esc_file_index_clean.csv"
WAREHOUSE_CSV = SCRIPT_DIR / "warehouse" / "raw" / "so_contracts_parsed.csv"

EXT_LABELS = {
    ".pdf": "PDF", ".cdr": "CDR", ".ai": "AI", ".eps": "EPS",
    ".dxf": "DXF", ".dwg": "DWG", ".fs": "FS", ".jpg": "JPG",
    ".jpeg": "JPG", ".png": "PNG", ".doc": "DOC", ".docx": "DOCX",
    ".xls": "XLS", ".xlsx": "XLSX", ".rtf": "RTF", ".rou": "ROU",
    ".enr": "ENR", ".pcd": "PCD", ".scv": "SCV", ".msg": "MSG",
}


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}MB"


def format_currency(val: str) -> str:
    try:
        num = float(val)
        return f"${num:,.2f}"
    except (ValueError, TypeError):
        return val or "—"


def load_esc_index() -> dict[str, list[dict]]:
    index = defaultdict(list)
    with open(ESC_INDEX, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            index[row["quote_number"]].append(row)
    return index


def load_warehouse() -> dict[str, list[dict]]:
    warehouse = defaultdict(list)
    with open(WAREHOUSE_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            qn = row.get("quote_nbr", "").strip()
            if qn and qn != "TOTAL":
                warehouse[qn].append(row)
    return warehouse


def lookup_quote(quote_num: str, esc_index: dict, warehouse: dict) -> None:
    files = esc_index.get(quote_num, [])
    wo_rows = warehouse.get(quote_num, [])

    print(f"\n{'=' * 60}")
    print(f"  Quote {quote_num}")
    print(f"{'=' * 60}")

    # Warehouse data
    if wo_rows:
        row = wo_rows[0]
        customer = row["customer_name"]
        wo = row["work_order"]
        location = row.get("location", "")
        status = row.get("status", "")
        sales_code = row.get("sales_code", "")
        estimator = row.get("estimator", "")
        billing = format_currency(row.get("billing", ""))
        quoted_price = format_currency(row.get("quoted_price", ""))
        sale_price = format_currency(row.get("sale_price", ""))
        total_cost = format_currency(row.get("total_cost", ""))
        gm_pct = row.get("gm_percent", "")
        gm_display = f"{gm_pct}%" if gm_pct else "—"
        labor_cost = format_currency(row.get("labor_cost", ""))
        labor_hours = row.get("labor_detail_count", "")
        date_completed = row.get("date_completed", "")

        print(f"  Customer:  {customer}")
        print(f"  Location:  {location}")
        print(f"  WO:        {wo} | Status: {status}")
        print(f"  Sales:     {sales_code} | Estimator: {estimator or '—'}")
        print(f"  Billing:   {billing} | Quoted: {quoted_price} | Sale: {sale_price}")
        print(f"  Cost:      {total_cost} | Labor: {labor_cost} | GM: {gm_display}")
        print(f"  Completed: {date_completed} | Labor entries: {labor_hours}")

        # Show additional WO lines if multiple
        if len(wo_rows) > 1:
            print(f"  ({len(wo_rows)} WO line items for this quote)")
            total_billing = 0
            total_cost_sum = 0
            for r in wo_rows:
                try:
                    total_billing += float(r.get("billing", 0) or 0)
                except ValueError:
                    pass
                try:
                    total_cost_sum += float(r.get("total_cost", 0) or 0)
                except ValueError:
                    pass
            if total_billing > 0:
                agg_gm = (
                    (total_billing - total_cost_sum) / total_billing * 100
                    if total_billing
                    else 0
                )
                print(
                    f"  TOTALS:    Billing: ${total_billing:,.2f} | "
                    f"Cost: ${total_cost_sum:,.2f} | GM: {agg_gm:.1f}%"
                )
    else:
        print("  Warehouse: No matching quote_nbr found")
        # Try to infer customer from file paths
        if files:
            customer = files[0].get("customer_folder", "Unknown")
            print(f"  Customer (from G: drive): {customer}")

    # G: drive files
    if files:
        # Determine customer folder(s)
        folders = set()
        for f in files:
            parent = str(Path(f["full_path"]).parent)
            folders.add(parent)
        customer_root = files[0].get("customer_folder", "")
        letter = files[0].get("letter_folder", "")
        if letter and customer_root:
            print(f"  G: Drive:  G:\\{letter}\\{customer_root}\\")

        print(f"  Files ({len(files)}):")
        # Sort by extension then filename
        sorted_files = sorted(files, key=lambda x: (x["file_extension"], x["filename"]))
        for f in sorted_files:
            ext = f["file_extension"].lower()
            label = EXT_LABELS.get(ext, ext.lstrip(".").upper() or "???")
            size = format_size(int(f.get("file_size_bytes", 0) or 0))
            modified = f.get("last_modified", "")[:10]
            name = f["filename"]
            # Show subfolder if different from customer root
            rel = f["full_path"]
            print(f"    {label:<4} {name:<50} {size:>8}  {modified}")

        if len(folders) > 1:
            print(f"  Spread across {len(folders)} folders:")
            for folder in sorted(folders):
                print(f"    {folder}")
    else:
        print("  G: Drive:  No files found in ESC index")

    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python lookup_job.py <quote_number> [quote_number ...]")
        print("Example: python lookup_job.py 40654 40655 40660")
        sys.exit(1)

    quote_numbers = sys.argv[1:]

    print("Loading ESC index...", end=" ", flush=True)
    esc_index = load_esc_index()
    print(f"{sum(len(v) for v in esc_index.values()):,} files, {len(esc_index):,} quotes")

    print("Loading warehouse...", end=" ", flush=True)
    warehouse = load_warehouse()
    print(f"{sum(len(v) for v in warehouse.values()):,} rows, {len(warehouse):,} quotes")

    for qn in quote_numbers:
        lookup_quote(qn.strip(), esc_index, warehouse)

    # Batch summary if multiple
    if len(quote_numbers) > 1:
        print(f"{'=' * 60}")
        print(f"  Batch Summary: {len(quote_numbers)} quotes looked up")
        total_files = sum(len(esc_index.get(q.strip(), [])) for q in quote_numbers)
        matched_wo = sum(
            1 for q in quote_numbers if warehouse.get(q.strip())
        )
        print(f"  Total files found: {total_files}")
        print(f"  With warehouse data: {matched_wo}/{len(quote_numbers)}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
