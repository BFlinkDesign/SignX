"""Enrich merged warehouse CSVs with reference table lookups.

Reads *_ALL.csv report-format files, joins reference codes to human-readable
names, and writes *_ALL_enriched.csv files. Handles the report-format structure
(repeated year headers, subtotal rows, blank lines) by enriching only data rows.

Usage:
    python enrich_csv_exports.py
"""
import csv
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

CSV_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\csv_exports")

# ---------------------------------------------------------------------------
# 1. Load Reference Tables
# ---------------------------------------------------------------------------

def load_ref_table(filename, key_col=0, val_col=1):
    """Load a reference CSV into a dict {code: description}.

    Cleans newlines from multiline cell values.
    """
    filepath = CSV_DIR / filename
    lookup = {}
    with open(filepath, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header
        for row in reader:
            if len(row) > max(key_col, val_col):
                key = row[key_col].strip()
                val = row[val_col].strip().replace("\n", " ")
                if key:
                    lookup[key] = val
    return lookup


def load_all_refs():
    """Load all reference tables into a dict of dicts."""
    refs = {}
    refs["sales_codes"] = load_ref_table("ref_SALES_CODES_LIST.csv")
    refs["work_codes"] = load_ref_table("ref_WORK_CODE_LIST.csv")
    refs["work_depts"] = load_ref_table("ref_WORK_DEPT_LIST.csv")
    refs["salespersons"] = load_ref_table("ref_SALESPERSONS_LIST.csv", val_col=1)
    refs["sign_types"] = load_ref_table("ref_SIGN_TYPE_CODES_LISTING.csv")
    refs["sign_templates"] = load_ref_table("ref_SIGN_TEMPLATE_LISTING.csv")
    refs["states"] = load_ref_table("ref_STATES_LIST.csv")
    refs["quote_status"] = load_ref_table("ref_EST_QUOTE_STATUS_CODE_LIST.csv")

    # Also load work_code -> work_dept mapping for chained lookup
    refs["work_code_to_dept"] = {}
    wc_path = CSV_DIR / "ref_WORK_CODE_LIST.csv"
    with open(wc_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) > 2 and row[0].strip():
                refs["work_code_to_dept"][row[0].strip()] = row[2].strip()

    print(f"Loaded reference tables:")
    for name, d in refs.items():
        print(f"  {name}: {len(d)} entries")
    print()
    return refs


# ---------------------------------------------------------------------------
# 2. Row Classification Helpers
# ---------------------------------------------------------------------------

def is_header_row(row, signatures):
    """Check if row matches any known column header signature."""
    if not row:
        return False
    for sig in signatures:
        if row[0].strip() == sig:
            return True
    return False


def is_blank_or_meta(row):
    """Check if row is blank, a report title, or metadata."""
    if not row:
        return True
    text = "|".join(row).strip()
    if not text or text == "|" * len(row):
        return True
    # Report metadata patterns
    if re.search(r"PERIOD:|Eagle Sign|EMPLOYEE LABOR|OPEN WORK ORDERS|"
                 r"GROSS MARGIN|SALES BY|DIVISION \d|Date Range|"
                 r"^\d{2} [A-Z]{3} \d{4}$|^\d{2}:\d{2}:\d{2}$",
                 row[0].strip()):
        return True
    # Timestamp-only first cell (e.g., "21:25:38")
    if re.match(r"^\d{2}:\d{2}:\d{2}$", row[0].strip()):
        return True
    return False


def is_subtotal_row(row):
    """Check if row is a subtotal/summary row."""
    text = "|".join(row)
    if "***" in text or "Totals" in text or "Grand Total" in text:
        return True
    if "NO RECORDS FOUND" in text:
        return True
    # Product Type Totals in CUST.PROD.EXPORT
    if len(row) > 3 and "Totals" in row[3]:
        return True
    return False


# ---------------------------------------------------------------------------
# 3. Enrichment Configurations Per File
# ---------------------------------------------------------------------------

def get_enrichment_configs(refs):
    """Return enrichment config for each _ALL.csv file.

    Each config dict:
        header_sig: first column name to identify header rows
        expected_cols: expected column count for data rows
        enrichments: list of (src_col_idx, ref_dict, new_col_name)
        extra_header_names: list of new column names to append to header rows
        is_data_fn: function(row) -> bool to identify data rows
    """
    configs = {}

    # --- EMP.HOURS.BY.DATE ---
    configs["EMP.HOURS.BY.DATE_ALL.csv"] = {
        "header_sig": "EmpNo",
        "expected_cols": 11,
        "enrichments": [
            (8, refs["work_codes"], "Work Code Ref Desc"),
            (8, refs["work_code_to_dept"], "_dept_code"),  # intermediate
        ],
        "extra_header_names": ["Work Code Ref Desc", "Work Dept", "Work Dept Name"],
        "post_process": "emp_hours",
    }

    # --- CUST.PROD.EXPORT ---
    configs["CUST.PROD.EXPORT_ALL.csv"] = {
        "header_sig": "Cust No",
        "expected_cols": 24,
        "enrichments": [
            (2, refs["sales_codes"], "Prod Code Ref Desc"),
            (17, refs["salespersons"], "Salesperson #1 Name"),
            (19, refs["salespersons"], "Salesperson #2 Name"),
            (21, refs["salespersons"], "Salesperson #3 Name"),
        ],
        "extra_header_names": [
            "Prod Code Ref Desc",
            "Salesperson #1 Name", "Salesperson #2 Name", "Salesperson #3 Name",
        ],
    }

    # --- GM.BY.INV.EXPORT ---
    configs["GM.BY.INV.EXPORT_ALL.csv"] = {
        "header_sig": "Invoice No",
        "expected_cols": 29,
        "enrichments": [
            (2, refs["sales_codes"], "Prod Code Desc"),
            (18, refs["salespersons"], "SalesPer #1 Name"),
            (20, refs["salespersons"], "SalesPer #2 Name"),
            (22, refs["salespersons"], "SalesPer #3 Name"),
        ],
        "extra_header_names": [
            "Prod Code Desc",
            "SalesPer #1 Name", "SalesPer #2 Name", "SalesPer #3 Name",
        ],
    }

    # --- SLSPER.PROD.EXPORT ---
    configs["SLSPER.PROD.EXPORT_ALL.csv"] = {
        "header_sig": "Invoice No",
        "expected_cols": 21,
        "enrichments": [
            (2, refs["sales_codes"], "Prod Code Desc"),
            (10, refs["salespersons"], "Salesperson #1 Name"),
            (12, refs["salespersons"], "Salesperson #2 Name"),
            (14, refs["salespersons"], "Salesperson #3 Name"),
        ],
        "extra_header_names": [
            "Prod Code Desc",
            "Salesperson #1 Name", "Salesperson #2 Name", "Salesperson #3 Name",
        ],
    }

    # --- EXPORT.WO.LABOR.ANALYSIS ---
    configs["EXPORT.WO.LABOR.ANALYSIS_ALL.csv"] = {
        "header_sig": "WO #",
        "expected_cols": 166,
        "enrichments": [
            (7, refs["sign_types"], "Sign Type Desc"),
            (8, refs["sign_templates"], "Template Desc"),
        ],
        "extra_header_names": ["Sign Type Desc", "Template Desc"],
    }

    return configs


# ---------------------------------------------------------------------------
# 4. Core Enrichment Engine
# ---------------------------------------------------------------------------

def enrich_file(input_path, output_path, config, refs):
    """Enrich a single _ALL.csv file.

    Returns stats dict with match/miss counts per enrichment column.
    """
    header_sig = config["header_sig"]
    expected_cols = config["expected_cols"]
    enrichments = config["enrichments"]
    extra_headers = config["extra_header_names"]
    post_process = config.get("post_process")

    stats = {
        "total_rows": 0,
        "data_rows": 0,
        "header_rows": 0,
        "meta_rows": 0,
        "subtotal_rows": 0,
        "matches": defaultdict(int),
        "misses": defaultdict(int),
        "orphan_codes": defaultdict(set),
        "sample_rows": [],
    }

    with open(input_path, encoding="utf-8") as fin, \
         open(output_path, "w", newline="", encoding="utf-8") as fout:
        reader = csv.reader(fin)
        writer = csv.writer(fout)

        for row in reader:
            stats["total_rows"] += 1

            # Classify the row
            if is_header_row(row, [header_sig]):
                stats["header_rows"] += 1
                writer.writerow(row + extra_headers)
                continue

            if is_blank_or_meta(row) or is_subtotal_row(row):
                stats["meta_rows" if is_blank_or_meta(row) else "subtotal_rows"] += 1
                writer.writerow(row)
                continue

            # Check if this looks like a data row by column count
            # Allow some flexibility (±2) for trailing commas
            if abs(len(row) - expected_cols) > 3:
                # Might be a department header row in WO.LABOR or other oddity
                writer.writerow(row)
                stats["meta_rows"] += 1
                continue

            # It's a data row — enrich it
            stats["data_rows"] += 1
            new_cols = []

            if post_process == "emp_hours":
                # Special: chain work_code -> dept_code -> dept_name
                work_code = row[8].strip() if len(row) > 8 else ""
                wc_desc = refs["work_codes"].get(work_code, "")
                dept_code = refs["work_code_to_dept"].get(work_code, "")
                dept_name = refs["work_depts"].get(dept_code, "")

                new_cols = [wc_desc, dept_code, dept_name]

                # Stats for work code
                col_name = "Work Code"
                if work_code:
                    if wc_desc:
                        stats["matches"][col_name] += 1
                    else:
                        stats["misses"][col_name] += 1
                        stats["orphan_codes"][col_name].add(work_code)

                col_name = "Work Dept"
                if dept_code:
                    if dept_name:
                        stats["matches"][col_name] += 1
                    else:
                        stats["misses"][col_name] += 1
                        stats["orphan_codes"][col_name].add(dept_code)
            else:
                for src_idx, ref_dict, col_name in enrichments:
                    code = row[src_idx].strip() if len(row) > src_idx else ""
                    resolved = ref_dict.get(code, "")
                    new_cols.append(resolved)

                    if code:
                        if resolved:
                            stats["matches"][col_name] += 1
                        else:
                            stats["misses"][col_name] += 1
                            stats["orphan_codes"][col_name].add(code)

            writer.writerow(row + new_cols)

            # Collect sample rows for spot-check
            if len(stats["sample_rows"]) < 50:
                stats["sample_rows"].append((row, new_cols))

    return stats


# ---------------------------------------------------------------------------
# 5. Spot-Check and Reporting
# ---------------------------------------------------------------------------

def print_spot_check(filename, stats, config):
    """Print 5 random enriched rows for validation."""
    samples = stats["sample_rows"]
    if not samples:
        print(f"  No data rows to spot-check")
        return

    picks = random.sample(samples, min(5, len(samples)))
    enrichments = config.get("enrichments", [])
    extra_headers = config["extra_header_names"]
    post_process = config.get("post_process")

    print(f"  Spot-check ({min(5, len(samples))} random rows):")
    for orig_row, new_cols in picks:
        if post_process == "emp_hours":
            work_code = orig_row[8] if len(orig_row) > 8 else ""
            print(f"    Work Code '{work_code}' -> Desc='{new_cols[0]}', "
                  f"Dept='{new_cols[1]}' ({new_cols[2]})")
        else:
            parts = []
            for i, (src_idx, ref_dict, col_name) in enumerate(enrichments):
                code = orig_row[src_idx].strip() if len(orig_row) > src_idx else ""
                if code and i < len(new_cols):
                    parts.append(f"'{code}'->'{new_cols[i]}'")
            if parts:
                print(f"    {', '.join(parts)}")


def print_join_report(all_stats):
    """Print summary of all enrichment joins."""
    print(f"\n{'='*70}")
    print(f"JOIN REPORT")
    print(f"{'='*70}")

    for filename, stats in all_stats.items():
        print(f"\n--- {filename} ---")
        print(f"  Total rows: {stats['total_rows']:,}  |  Data rows: {stats['data_rows']:,}  "
              f"|  Headers: {stats['header_rows']}  |  Meta: {stats['meta_rows']:,}  "
              f"|  Subtotals: {stats['subtotal_rows']:,}")

        if stats["matches"] or stats["misses"]:
            print(f"  {'Column':<25} {'Matched':>8} {'Missed':>8} {'Rate':>8}  Orphan codes")
            print(f"  {'-'*25} {'-'*8} {'-'*8} {'-'*8}  {'-'*20}")
            for col in sorted(set(list(stats["matches"].keys()) + list(stats["misses"].keys()))):
                m = stats["matches"].get(col, 0)
                miss = stats["misses"].get(col, 0)
                total = m + miss
                rate = f"{m/total*100:.1f}%" if total > 0 else "N/A"
                orphans = stats["orphan_codes"].get(col, set())
                orphan_str = ""
                if orphans:
                    shown = sorted(orphans)[:5]
                    orphan_str = ", ".join(shown)
                    if len(orphans) > 5:
                        orphan_str += f" (+{len(orphans)-5} more)"
                print(f"  {col:<25} {m:>8,} {miss:>8,} {rate:>8}  {orphan_str}")


# ---------------------------------------------------------------------------
# 6. Main
# ---------------------------------------------------------------------------

def main():
    print(f"CSV Export Enrichment Engine")
    print(f"Input/Output: {CSV_DIR}\n")

    refs = load_all_refs()
    configs = get_enrichment_configs(refs)

    all_stats = {}

    for filename, config in configs.items():
        input_path = CSV_DIR / filename
        output_path = CSV_DIR / filename.replace("_ALL.csv", "_ALL_enriched.csv")

        if not input_path.exists():
            print(f"SKIP: {filename} not found")
            continue

        print(f"Enriching {filename}...")
        stats = enrich_file(input_path, output_path, config, refs)
        all_stats[filename] = stats

        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  -> {output_path.name}: {stats['data_rows']:,} data rows enriched, {size_mb:.2f}MB")
        print_spot_check(filename, stats, config)
        print()

    # WIP.SUMMARY files have no joinable codes — skip with note
    for wip in ["EXPORT.WIP.SUMMARY_C_ALL.csv", "EXPORT.WIP.SUMMARY_O_ALL.csv"]:
        print(f"SKIP: {wip} (no reference code columns to enrich)")

    print_join_report(all_stats)


if __name__ == "__main__":
    random.seed(42)
    main()
