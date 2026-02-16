"""
SignX-Takeoff Validation Suite
Tests 1-4: PDF parser, ABC formulas, part numbers, warehouse quality
"""
import csv
import os
import sys
from pathlib import Path

# ── Test 1: PDF Parser ──────────────────────────────────────────────────────

def test_pdf_parser():
    """Test PDF parser against real conceptual PDFs."""
    from extract_pf_from_pdf import extract_pf_from_pdf

    test_files = [
        # Gemini Art — 1:1 scale, best vector source
        {
            "name": "IADOT Gemini Art (1:1)",
            "path": r"G:\I\Iowa Dept of Transportation\2025\AMES - 800 LINCOLN WAY\GEMINI\IADOT Ames Bldg Letters Brushed Alum Q39946 12562-2.pdf",
            "expected_pf": 78.64,
            "tolerance": 0.15,  # 15% — inherent difference between Gemini Art and CorelDRAW conceptual
            "scale_factor": 0,
        },
        # Guthrie County conceptual (letter-size, needs scale)
        {
            "name": "Guthrie County Conceptual (SF=2.75)",
            "path": r"G:\G\Guthrie Co. State Bank\Guthrie County State Bank, Panora\2025\Guthrie Co Panora Channel Ltrs 0126-40593-00.pdf",
            "expected_pf": 133.93,
            "tolerance": 0.05,  # 5% with correct scale
            "scale_factor": 2.75,
        },
        # IADOT conceptual (letter-size, needs scale)
        {
            "name": "IADOT Conceptual (SF=2.75)",
            "path": r"G:\I\Iowa Dept of Transportation\2025\AMES - 800 LINCOLN WAY\IADOT Ames Bldg Letters Brushed Alum 0925-39946-00.pdf",
            "expected_pf": 78.64,
            "tolerance": 0.05,
            "scale_factor": 2.75,
        },
        # Downloads folder fallback
        {
            "name": "Infinity Neuro Channel Letters",
            "path": r"C:\Users\Brady.EAGLE\Downloads\BRADYF_Infinity Neuro Channel Letters 0625-39541.pdf",
            "expected_pf": None,
            "tolerance": None,
            "scale_factor": 0,
        },
    ]

    results = []
    for tf in test_files:
        p = Path(tf["path"])
        if not p.exists():
            results.append({
                "name": tf["name"],
                "status": "BLOCKED",
                "detail": f"File not found: {tf['path']}",
            })
            continue

        try:
            with open(p, "rb") as f:
                data = f.read()

            # Try all pages (some conceptuals have title page first)
            best_pf = 0
            best_page = 0
            best_result = None
            import fitz
            doc = fitz.open(stream=data, filetype="pdf")
            num_pages = len(doc)
            doc.close()

            sf = tf.get("scale_factor", 0)
            for page_num in range(min(num_pages, 5)):  # Check up to 5 pages
                result = extract_pf_from_pdf(data, filename=p.name, page_num=page_num,
                                             scale_factor=sf)
                if result.total_pf > best_pf:
                    best_pf = result.total_pf
                    best_page = page_num
                    best_result = result

            if best_result is None or best_pf == 0:
                results.append({
                    "name": tf["name"],
                    "status": "FAIL",
                    "detail": "No vector paths extracted from any page",
                })
                continue

            detail = (
                f"PF={best_pf:.2f} ft (page {best_page}) | "
                f"{best_result.letter_count} shapes | "
                f"Face={best_result.total_face_sf:.2f} SF | "
                f"Heights={best_result.min_height_inches:.1f}\"-{best_result.max_height_inches:.1f}\""
            )

            if tf["expected_pf"] is not None:
                variance = abs(best_pf - tf["expected_pf"]) / tf["expected_pf"]
                detail += f" | Expected={tf['expected_pf']:.2f} | Variance={variance*100:.1f}%"
                if variance <= tf["tolerance"]:
                    status = "PASS"
                else:
                    status = f"FAIL (variance {variance*100:.1f}% > {tf['tolerance']*100:.0f}%)"
            else:
                status = "INFO (no benchmark)"
                detail += " | No expected PF to compare against"

            if best_result.warnings:
                detail += f" | Warnings: {'; '.join(best_result.warnings)}"

            results.append({"name": tf["name"], "status": status, "detail": detail})

        except Exception as e:
            results.append({
                "name": tf["name"],
                "status": "ERROR",
                "detail": str(e),
            })

    return results


# ── Test 2: ABC Formula vs Warehouse Actuals ─────────────────────────────────

def test_abc_vs_actuals():
    """Spot-check ABC engine against completed jobs."""
    from abc_engine import estimate, JobInput, ConstructionType, FontType

    csv_path = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\so_contracts_parsed.csv")
    if not csv_path.exists():
        return [{"name": "ABC vs Actuals", "status": "BLOCKED", "detail": "CSV not found"}]

    # Load channel letter jobs with known labor costs
    channel_jobs = []
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sc = (row.get("sales_code") or "").strip().upper()
            if sc not in ("CHANNL", "CHANL", "CHNL", "CHLET"):
                continue
            try:
                labor_cost = float(row.get("labor_cost") or 0)
                billing = float(row.get("billing") or 0)
                total_cost = float(row.get("total_cost") or 0)
            except (ValueError, TypeError):
                continue
            if labor_cost <= 0 or billing <= 0:
                continue
            channel_jobs.append({
                "wo": row.get("work_order", ""),
                "customer": row.get("customer_name", ""),
                "labor_cost": labor_cost,
                "billing": billing,
                "total_cost": total_cost,
                "desc": row.get("description", ""),
            })

    if not channel_jobs:
        return [{"name": "ABC vs Actuals", "status": "FAIL", "detail": "No channel letter jobs found in CSV"}]

    # Find jobs in the 10-30 hour range (moderate complexity)
    IMPLIED_RATE = 40.0
    moderate = [j for j in channel_jobs if 10 <= j["labor_cost"] / IMPLIED_RATE <= 30]
    if not moderate:
        moderate = channel_jobs[:10]

    # Pick 3 representative jobs
    test_jobs = moderate[:3]
    results = []

    for tj in test_jobs:
        actual_hours = tj["labor_cost"] / IMPLIED_RATE

        # Estimate: assume 12" block face-lit, reverse-engineer PF from hours
        # Use footage chart: 12" block = 4.20 PF/letter
        # Total fab hours ≈ 1.0 + 1.5 + (PF * 0.175) [sum of all per-PF rates for 12-24"]
        # 0.102 + 0.021 + 0.015 + 0.017 = 0.155 per PF, plus constants 1.0 + 1.5 + 1.5 = 4.0
        # So actual_hours ≈ 4.0 + PF * 0.155 => PF ≈ (actual_hours - 4.0) / 0.155
        estimated_pf = max(5.0, (actual_hours - 4.0) / 0.155)

        job = JobInput(
            pf_manual=estimated_pf,
            letter_height_inches=12,
            font_type=FontType.BLOCK,
            construction=ConstructionType.FACE_LIT,
            return_depth_inches=5,
            install_height_ft=15,
            miles_one_way=20,
            crew_size=2,
            num_units=1,
        )
        result = estimate(job)
        abc_total = result.total_man_hours + result.total_crew_hours

        variance = abs(abc_total - actual_hours) / actual_hours * 100

        results.append({
            "name": f"WO {tj['wo']} ({tj['customer'][:25]})",
            "status": "PASS" if variance < 50 else "WARN",
            "detail": (
                f"Actual={actual_hours:.1f} hrs (${tj['labor_cost']:.0f} labor) | "
                f"ABC={abc_total:.1f} hrs (est PF={estimated_pf:.1f}) | "
                f"Variance={variance:.0f}% | Revenue=${tj['billing']:.0f}"
            ),
        })

    # Add summary
    results.insert(0, {
        "name": "Channel Letter Jobs Found",
        "status": "INFO",
        "detail": f"{len(channel_jobs)} total CHANNL jobs with labor+billing data in warehouse",
    })

    return results


# ── Test 3: Part Number Validation ───────────────────────────────────────────

def test_part_numbers():
    """Validate ABC engine part numbers against known Eagle inventory."""
    from abc_engine import estimate, JobInput, ConstructionType, FontType

    job = JobInput(
        letter_count=10,
        letter_height_inches=12,
        font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT,
        return_depth_inches=5,
    )
    result = estimate(job)

    # Known valid Eagle part numbers from eagle-rates-fab-cheat-sheet.md
    KNOWN_VALID = {
        "217-0485": ".177 Impact Modified Acrylic",
        "205-0111": ".040 B/W alum",
        "205-0180": ".040 W/W alum",
        "202-0710": "Type IV retainer (1\")",
        "307-0261": "Hanley 3120",
        "307-0265": "Hanley 60w 12v P.S.",
        "307-0264": "Hanley 120w 12v P.S.",
        "307-0170": "Hanley 192w 24v P.S.",
        "307-0100": "18g LED wire",
        "214-0000": "Hardware (general)",
    }

    results = []
    for m in result.material_bom:
        part = m["part"]
        if part in KNOWN_VALID:
            results.append({
                "name": f"{part} ({m['item'][:30]})",
                "status": "PASS",
                "detail": f"Matches: {KNOWN_VALID[part]}",
            })
        elif part.startswith(("202-", "203-", "204-", "205-", "206-", "214-", "217-", "307-", "311-", "313-")):
            results.append({
                "name": f"{part} ({m['item'][:30]})",
                "status": "NEEDS MANUAL CHECK",
                "detail": f"Valid prefix but not in cheat sheet. Qty={m['qty']} {m['unit']}",
            })
        else:
            results.append({
                "name": f"{part} ({m['item'][:30]})",
                "status": "FAIL",
                "detail": f"Unknown part number format",
            })

    return results


# ── Test 4: Warehouse Benchmark Quality ──────────────────────────────────────

def test_warehouse_quality():
    """Audit warehouse.py for correct column usage and filtering."""
    import inspect
    from warehouse import benchmark, _load_channel_letter_jobs

    results = []

    # Check source code for billing vs quoted_price
    source = inspect.getsource(_load_channel_letter_jobs)

    uses_billing = "billing" in source
    uses_quoted_price = "quoted_price" in source

    if uses_billing and not uses_quoted_price:
        results.append({
            "name": "Revenue Column",
            "status": "PASS",
            "detail": "Uses `billing` column (correct). Does NOT use `quoted_price`.",
        })
    elif uses_billing and uses_quoted_price:
        results.append({
            "name": "Revenue Column",
            "status": "WARN",
            "detail": "References both `billing` and `quoted_price`. Verify `billing` is primary.",
        })
    else:
        results.append({
            "name": "Revenue Column",
            "status": "FAIL",
            "detail": f"billing={uses_billing}, quoted_price={uses_quoted_price}. Must use `billing`!",
        })

    # Check filter criteria
    checks_channl = "CHANNL" in source
    checks_cllit = "CLLIT" in source
    checks_channel_desc = "CHANNEL" in source

    if checks_channl or checks_cllit:
        results.append({
            "name": "Channel Letter Filter",
            "status": "PASS",
            "detail": f"Filters on: CHANNL={checks_channl}, CLLIT={checks_cllit}, desc-CHANNEL={checks_channel_desc}",
        })
    else:
        results.append({
            "name": "Channel Letter Filter",
            "status": "FAIL",
            "detail": "No channel letter filter found in source code",
        })

    # Check hour derivation
    uses_labor_cost = "labor_cost" in source
    results.append({
        "name": "Hour Derivation",
        "status": "INFO",
        "detail": f"Derives hours from labor_cost / implied_rate. Uses labor_cost={uses_labor_cost}. "
                  f"Note: CSV has labor_cost (dollars), not direct hour column.",
    })

    # Run benchmark and check results
    b = benchmark(15.0)
    if b:
        results.append({
            "name": "Benchmark Execution",
            "status": "PASS",
            "detail": (
                f"{b.matching_jobs} jobs | Avg={b.avg_labor_hours} hrs | "
                f"Median={b.median_labor_hours} hrs | StdDev=+/-{b.std_dev} | "
                f"Revenue=${b.avg_revenue:.0f} | GM={b.avg_margin_pct}% | "
                f"Confidence={b.confidence}"
            ),
        })
    else:
        results.append({
            "name": "Benchmark Execution",
            "status": "FAIL",
            "detail": "benchmark() returned None",
        })

    return results


# ── Run All Tests ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 80)
    print("  SignX-Takeoff Validation Suite")
    print("=" * 80)

    all_results = []

    print("\n--- Test 1: PDF Parser ---")
    pdf_results = test_pdf_parser()
    all_results.extend(pdf_results)
    for r in pdf_results:
        print(f"  [{r['status']:20s}] {r['name']}")
        print(f"                       {r['detail']}")

    print("\n--- Test 2: ABC vs Actual Hours ---")
    abc_results = test_abc_vs_actuals()
    all_results.extend(abc_results)
    for r in abc_results:
        print(f"  [{r['status']:20s}] {r['name']}")
        print(f"                       {r['detail']}")

    print("\n--- Test 3: Part Numbers ---")
    part_results = test_part_numbers()
    all_results.extend(part_results)
    for r in part_results:
        print(f"  [{r['status']:20s}] {r['name']}")
        print(f"                       {r['detail']}")

    print("\n--- Test 4: Warehouse Quality ---")
    wh_results = test_warehouse_quality()
    all_results.extend(wh_results)
    for r in wh_results:
        print(f"  [{r['status']:20s}] {r['name']}")
        print(f"                       {r['detail']}")

    # ── Scorecard ────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  VALIDATION SCORECARD")
    print("=" * 80)
    print(f"  {'Test':<45s} {'Status':<25s}")
    print(f"  {'-'*45} {'-'*25}")
    for r in all_results:
        status = r['status']
        if status == 'PASS':
            marker = 'PASS'
        elif status.startswith('FAIL'):
            marker = 'FAIL'
        elif status == 'BLOCKED':
            marker = 'BLOCKED'
        elif status == 'ERROR':
            marker = 'ERROR'
        elif status == 'WARN':
            marker = 'WARN'
        else:
            marker = status
        print(f"  {r['name']:<45s} {marker:<25s}")

    pass_count = sum(1 for r in all_results if r['status'] == 'PASS')
    total = len(all_results)
    print(f"\n  Score: {pass_count}/{total} PASS")
    print("=" * 80)
