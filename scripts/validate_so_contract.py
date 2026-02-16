"""Validate SO.CONTRACT parser accuracy across all 4 CSVs."""

import csv
import random
import re
from collections import defaultdict
from pathlib import Path

CSV_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\raw")
RAW_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\so_contract_raw")

random.seed(42)  # Reproducible


def load_csv(name):
    path = CSV_DIR / name
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# =========================================================================
# TEST 1: Null/empty rate audit
# =========================================================================
def test1_null_audit():
    print("=" * 70)
    print("TEST 1: Null/Empty Rate Audit")
    print("=" * 70)

    files = [
        "so_contract_wo_summary.csv",
        "so_contract_labor.csv",
        "so_contract_material.csv",
        "so_contract_outplant.csv",
    ]

    all_pass = True

    for fname in files:
        rows = load_csv(fname)
        total = len(rows)
        if not rows:
            print(f"\n  {fname}: EMPTY FILE")
            all_pass = False
            continue

        fields = rows[0].keys()
        print(f"\n  {fname} ({total:,} rows)")
        print(f"  {'Column':<30} {'Populated':>10} {'Empty':>8} {'% Pop':>8}")
        print(f"  {'-'*30} {'-'*10} {'-'*8} {'-'*8}")

        suspicious = []
        for field in fields:
            empty = sum(1 for r in rows if not r.get(field, "").strip())
            pct = (total - empty) / total * 100
            flag = " ***" if pct < 90 else ""
            print(f"  {field:<30} {total - empty:>10,} {empty:>8,} {pct:>7.1f}%{flag}")
            if pct < 90:
                suspicious.append((field, pct))

        if suspicious:
            print(f"\n  SUSPICIOUS columns (<90% populated):")
            for field, pct in suspicious:
                print(f"    - {field}: {pct:.1f}%")
            # Some columns are legitimately optional (estimator, quote_nbr, etc.)
            # work_dept is optional for material/outplant (general vs dept-assigned)
            critical_fields = {
                "wo_number", "run_date", "report_id", "total_cost",
                "job_cost", "actual_hours", "actual_qty",
            }
            if "labor" in fname:
                critical_fields.add("work_dept")
            critical = [f for f, p in suspicious if f in critical_fields]
            if critical:
                print(f"  FAIL: Critical columns with low fill: {critical}")
                all_pass = False

    return all_pass


# =========================================================================
# TEST 2: Random sample spot-check (N=10)
# =========================================================================
def extract_field_from_text(text, pattern):
    """Extract a value from raw report text using regex."""
    m = re.search(pattern, text)
    return m.group(1).strip() if m else None


def parse_money_str(s):
    if not s:
        return 0.0
    s = s.strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def test2_random_spot_check():
    print("\n" + "=" * 70)
    print("TEST 2: Random Sample Spot-Check (N=10)")
    print("=" * 70)

    summary = load_csv("so_contract_wo_summary.csv")

    # Get unique (report_id, wo_number) pairs that have matching raw files
    candidates = []
    seen = set()
    for row in summary:
        rid = row["report_id"]
        wo = row["wo_number"]
        key = (rid, wo)
        if key in seen:
            continue
        seen.add(key)
        txt_path = RAW_DIR / f"{rid}.txt"
        if txt_path.exists():
            candidates.append((row, txt_path))

    if len(candidates) < 10:
        print(f"  Only {len(candidates)} candidates with raw files. Need 10.")
        return False

    sample = random.sample(candidates, 10)
    all_pass = True

    for i, (csv_row, txt_path) in enumerate(sample, 1):
        wo = csv_row["wo_number"]
        try:
            text = txt_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = txt_path.read_text(encoding="cp1252")

        # Find the WO block in the text
        wo_pattern = re.compile(
            rf"WORK ORDER\s+{re.escape(wo)}\b.*?(?=WORK ORDER\s+\S|$)",
            re.DOTALL,
        )
        wo_match = wo_pattern.search(text)
        if not wo_match:
            # Single-WO report - use entire text
            wo_text = text
        else:
            wo_text = wo_match.group()

        # Extract fields from raw text
        raw_mat = extract_field_from_text(wo_text, r"TOTAL MATERIAL COST\s+([\d,.]+)")
        raw_labor = extract_field_from_text(wo_text, r"TOTAL LABOR COST\s+([\d,.]+)")
        raw_quoted = extract_field_from_text(wo_text, r"QUOTED PRICE\s+([\d,.]+)")
        raw_status = extract_field_from_text(wo_text, r"Status\s*:\s*(.+?)(?:\s{2,}|$)")
        raw_cust = extract_field_from_text(
            wo_text, r"Customer:\s+\S+\s+(.+?)(?:\s{2,}Location:|$)"
        )

        # Compare
        checks = []

        def compare(label, raw_val, csv_val, is_money=True):
            if raw_val is None:
                checks.append((label, "SKIP", f"not found in text"))
                return
            if is_money:
                raw_f = parse_money_str(raw_val)
                csv_f = parse_money_str(csv_val)
                match = abs(raw_f - csv_f) < 0.02
                checks.append(
                    (label, "MATCH" if match else "MISMATCH",
                     f"raw={raw_f} csv={csv_f}")
                )
            else:
                raw_clean = raw_val.strip()
                csv_clean = csv_val.strip()
                match = raw_clean == csv_clean
                checks.append(
                    (label, "MATCH" if match else "MISMATCH",
                     f"raw='{raw_clean}' csv='{csv_clean}'")
                )

        compare("total_material_cost", raw_mat, csv_row["total_material_cost"])
        compare("total_labor_cost", raw_labor, csv_row["total_labor_cost"])
        compare("quoted_price", raw_quoted, csv_row["quoted_price"])
        compare("status", raw_status, csv_row["status"], is_money=False)
        compare("customer_name", raw_cust, csv_row["customer_name"], is_money=False)

        mismatches = [c for c in checks if c[1] == "MISMATCH"]
        status = "PASS" if not mismatches else "FAIL"
        if mismatches:
            all_pass = False

        print(f"\n  [{i}/10] WO {wo} ({txt_path.name[:50]}...)")
        for label, result, detail in checks:
            flag = " ***" if result == "MISMATCH" else ""
            print(f"    {label:<25} {result:<10} {detail}{flag}")

    return all_pass


# =========================================================================
# TEST 3: Cross-reference totals
# =========================================================================
def test3_cross_reference():
    print("\n" + "=" * 70)
    print("TEST 3: Cross-Reference Totals")
    print("=" * 70)

    summary = load_csv("so_contract_wo_summary.csv")
    labor = load_csv("so_contract_labor.csv")
    material = load_csv("so_contract_material.csv")

    # Total cost across ALL rows (including duplicates)
    total_all = sum(parse_money_str(r["total_cost"]) for r in summary)
    print(f"\n  Sum total_cost (all 13,751 rows): ${total_all:,.2f}")

    # Deduplicated: latest run_date per wo_number
    latest = {}
    for row in summary:
        wo = row["wo_number"]
        rd = row["run_date"]
        if wo not in latest or rd > latest[wo]["run_date"]:
            latest[wo] = row

    total_dedup = sum(parse_money_str(r["total_cost"]) for r in latest.values())
    print(f"  Sum total_cost (dedup {len(latest):,} WOs): ${total_dedup:,.2f}")

    # Labor sum
    labor_sum = sum(parse_money_str(r["job_cost"]) for r in labor)
    print(f"  Sum labor job_cost (all rows): ${labor_sum:,.2f}")

    # Material sum
    material_sum = sum(parse_money_str(r["job_cost"]) for r in material)
    print(f"  Sum material job_cost (all rows): ${material_sum:,.2f}")

    # Sanity: $27M figure was across all rows
    print(f"\n  Reported $27M figure check: ${total_all:,.2f}")
    diff = abs(total_all - 27030572.88)
    ok = diff < 1.0
    print(f"  Difference from reported: ${diff:.2f} -> {'PASS' if ok else 'FAIL'}")

    return ok


# =========================================================================
# TEST 4: Labor row count validation (5 random WOs)
# =========================================================================
def test4_labor_count():
    print("\n" + "=" * 70)
    print("TEST 4: Labor Row Count Validation (5 random WOs)")
    print("=" * 70)

    summary = load_csv("so_contract_wo_summary.csv")
    labor = load_csv("so_contract_labor.csv")

    # Build labor count per (report_id, wo_number)
    labor_counts = defaultdict(int)
    for row in labor:
        key = (row["report_id"], row["wo_number"])
        labor_counts[key] += 1

    # Pick 5 random WOs that have labor rows and matching raw files
    candidates = []
    seen = set()
    for row in summary:
        rid = row["report_id"]
        wo = row["wo_number"]
        key = (rid, wo)
        if key in seen:
            continue
        seen.add(key)
        if labor_counts.get(key, 0) > 0:
            txt_path = RAW_DIR / f"{rid}.txt"
            if txt_path.exists():
                candidates.append((rid, wo, txt_path, labor_counts[key]))

    sample = random.sample(candidates, min(5, len(candidates)))
    all_pass = True

    for rid, wo, txt_path, csv_count in sample:
        try:
            text = txt_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = txt_path.read_text(encoding="cp1252")

        # Find WO block
        wo_esc = re.escape(wo)
        wo_pattern = re.compile(
            rf"-{{5,}}\s*WORK ORDER\s+{wo_esc}\s*-{{5,}}(.*?)(?=-{{5,}}\s*WORK ORDER|\Z)",
            re.DOTALL,
        )
        wo_match = wo_pattern.search(text)
        if not wo_match:
            # Try full text for single-WO reports
            wo_text = text
        else:
            wo_text = wo_match.group()

        # Count **** subtotal lines in LABOR section
        in_labor = False
        raw_count = 0
        for line in wo_text.split("\n"):
            if re.match(r"\s*LABOR\s+WORK\s+WORK", line):
                in_labor = True
                continue
            elif re.match(r"\s*(MATERIAL|OUTPLANT)\s+WORK", line):
                in_labor = False
                continue
            if in_labor and "****" in line and "**** Total ****" not in line:
                raw_count += 1

        match = raw_count == csv_count
        status = "MATCH" if match else "MISMATCH"
        if not match:
            all_pass = False

        print(f"\n  WO {wo} (report: {rid[:45]}...)")
        print(f"    Raw **** lines in LABOR: {raw_count}")
        print(f"    CSV labor rows:          {csv_count}")
        print(f"    -> {status}")

    return all_pass


# =========================================================================
# TEST 5: Known benchmark (WO 10863.2)
# =========================================================================
def test5_benchmark():
    print("\n" + "=" * 70)
    print("TEST 5: Known Benchmark - WO 10863.2 (Purple Door Home Decor)")
    print("=" * 70)

    summary = load_csv("so_contract_wo_summary.csv")
    labor = load_csv("so_contract_labor.csv")

    # Find WO 10863.2 rows
    wo_rows = [r for r in summary if r["wo_number"] == "10863.2"]
    print(f"\n  Found {len(wo_rows)} summary rows for WO 10863.2")

    if not wo_rows:
        print("  FAIL: WO 10863.2 not found")
        return False

    # Use first occurrence
    row = wo_rows[0]
    checks = []

    # total_cost
    tc = parse_money_str(row["total_cost"])
    ok = abs(tc - 5182.30) < 0.02
    checks.append(("total_cost", tc, 5182.30, ok))

    # quoted_price
    qp = parse_money_str(row["quoted_price"])
    ok = abs(qp - 8813.78) < 0.02
    checks.append(("quoted_price", qp, 8813.78, ok))

    # status
    st = row["status"].strip()
    ok = st == "Fin Closed"
    checks.append(("status", st, "Fin Closed", ok))

    # customer_name
    cn = row["customer_name"].strip()
    ok = cn == "PURPLE DOOR HOME DECOR"
    checks.append(("customer_name", cn, "PURPLE DOOR HOME DECOR", ok))

    # labor count
    rid = row["report_id"]
    labor_rows = [r for r in labor if r["report_id"] == rid and r["wo_number"] == "10863.2"]
    labor_count = len(labor_rows)
    ok = labor_count == 21
    checks.append(("labor_subtotals", labor_count, 21, ok))

    all_pass = True
    for label, actual, expected, ok in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  {label:<25} actual={actual!s:<30} expected={expected!s:<30} {status}")

    return all_pass


# =========================================================================
# Main
# =========================================================================
def main():
    print("SO.CONTRACT Parser Validation Suite")
    print("=" * 70)

    results = {}
    results["Test 1: Null/Empty Audit"] = test1_null_audit()
    results["Test 2: Random Spot-Check"] = test2_random_spot_check()
    results["Test 3: Cross-Reference Totals"] = test3_cross_reference()
    results["Test 4: Labor Row Count"] = test4_labor_count()
    results["Test 5: Known Benchmark"] = test5_benchmark()

    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    for test, passed in results.items():
        print(f"  {test:<40} {'PASS' if passed else 'FAIL'}")

    all_pass = all(results.values())
    print(f"\n  Overall: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    exit(main())
