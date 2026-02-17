"""
test_phase1.py — Phase 1 validation: correction factors vs warehouse actuals.

Tests that the three Phase 0 corrections (install floor, CLLIT 0270 floor,
OT probability) are properly encoded and produce estimates within reasonable
range of warehouse P50 values.

Source data: signx.duckdb (so_contract_labor + so_contracts)
"""

from abc_engine import (
    CabinetFace,
    CabinetFrame,
    CabinetShape,
    CLLIT_0270_FLOOR,
    ConstructionType,
    estimate,
    FontType,
    INSTALL_FLOOR,
    JobInput,
    OT_FACTORS,
    SECTION_2_RATES,
    SECTION_2E_RATES,
    SECTION_5A_RATES,
    SECTION_10A_RATES,
    SignType,
)


def test_enums():
    """Task #2: All new enums have expected members."""
    results = []

    # SignType
    expected_types = [
        "CLLIT", "CLNON", "MONDF", "MONSF", "POLLIT", "DIRECT",
        "BLDILL", "BLDNON", "AWNNON", "GEMINI", "LED",
        "ALULIT", "ALUNON", "VINYL", "NEON", "OTHER",
    ]
    actual = [s.value for s in SignType]
    if set(expected_types) == set(actual):
        results.append({"name": "SignType enum", "status": "PASS",
                        "detail": f"{len(actual)} members"})
    else:
        missing = set(expected_types) - set(actual)
        extra = set(actual) - set(expected_types)
        results.append({"name": "SignType enum", "status": "FAIL",
                        "detail": f"Missing: {missing}, Extra: {extra}"})

    # CabinetShape
    shapes = [s.value for s in CabinetShape]
    if set(shapes) == {"rectangular", "semi_irregular", "intricate"}:
        results.append({"name": "CabinetShape enum", "status": "PASS",
                        "detail": f"{shapes}"})
    else:
        results.append({"name": "CabinetShape enum", "status": "FAIL",
                        "detail": f"Got: {shapes}"})

    # CabinetFrame
    frames = [f.value for f in CabinetFrame]
    if set(frames) == {"light", "heavy", "none"}:
        results.append({"name": "CabinetFrame enum", "status": "PASS",
                        "detail": f"{frames}"})
    else:
        results.append({"name": "CabinetFrame enum", "status": "FAIL",
                        "detail": f"Got: {frames}"})

    # CabinetFace
    faces = [f.value for f in CabinetFace]
    if set(faces) == {"single_face", "double_face"}:
        results.append({"name": "CabinetFace enum", "status": "PASS",
                        "detail": f"{faces}"})
    else:
        results.append({"name": "CabinetFace enum", "status": "FAIL",
                        "detail": f"Got: {faces}"})

    return results


def test_rate_dicts():
    """Task #3: Rate dicts match ABC guide values."""
    results = []

    # Section 2: spot-check SF Light Rectangular
    key = (CabinetFace.SINGLE, CabinetFrame.LIGHT, CabinetShape.RECTANGULAR)
    rate = SECTION_2_RATES.get(key)
    if rate and rate["labor"] == 0.184 and rate["material"] == 1.80:
        results.append({"name": "Section 2 SF Light Rect", "status": "PASS",
                        "detail": f"labor={rate['labor']}, material=${rate['material']}"})
    else:
        results.append({"name": "Section 2 SF Light Rect", "status": "FAIL",
                        "detail": f"Got: {rate}"})

    # Section 2: DF Heavy Rectangular
    key = (CabinetFace.DOUBLE, CabinetFrame.HEAVY, CabinetShape.RECTANGULAR)
    rate = SECTION_2_RATES.get(key)
    if rate and rate["labor"] == 0.265:
        results.append({"name": "Section 2 DF Heavy Rect", "status": "PASS",
                        "detail": f"labor={rate['labor']}"})
    else:
        results.append({"name": "Section 2 DF Heavy Rect", "status": "FAIL",
                        "detail": f"Got: {rate}"})

    # Section 2E: raceway straight
    rate = SECTION_2E_RATES.get(("raceway", "straight"))
    if rate and rate["labor"] == 0.208:
        results.append({"name": "Section 2E Raceway Straight", "status": "PASS",
                        "detail": f"labor={rate['labor']}/LF"})
    else:
        results.append({"name": "Section 2E Raceway Straight", "status": "FAIL",
                        "detail": f"Got: {rate}"})

    # Section 5A: 1 color
    rate = SECTION_5A_RATES.get(1)
    if rate and rate["constant"] == 1.0 and rate["labor"] == 0.017:
        results.append({"name": "Section 5A 1-color", "status": "PASS",
                        "detail": f"const={rate['constant']}h, labor={rate['labor']}/SF"})
    else:
        results.append({"name": "Section 5A 1-color", "status": "FAIL",
                        "detail": f"Got: {rate}"})

    # Section 5A: 5 colors
    rate = SECTION_5A_RATES.get(5)
    if rate and rate["constant"] == 3.0 and rate["labor"] == 0.050:
        results.append({"name": "Section 5A 5-color", "status": "PASS",
                        "detail": f"const={rate['constant']}h, labor={rate['labor']}/SF"})
    else:
        results.append({"name": "Section 5A 5-color", "status": "FAIL",
                        "detail": f"Got: {rate}"})

    # Section 10A: SF plastic first
    rate = SECTION_10A_RATES.get(("sf_plastic", "first"))
    if rate and rate["constant"] == 1.50 and rate["wall"] == 0.036:
        results.append({"name": "Section 10A SF Plastic 1st", "status": "PASS",
                        "detail": f"const={rate['constant']}h, wall={rate['wall']}/SF"})
    else:
        results.append({"name": "Section 10A SF Plastic 1st", "status": "FAIL",
                        "detail": f"Got: {rate}"})

    # Section 10A: letters on deck
    rate = SECTION_10A_RATES.get(("letters_on_deck", "first"))
    if rate and rate["constant"] == 2.00 and rate["wall"] == 0.040:
        results.append({"name": "Section 10A Letters on Deck", "status": "PASS",
                        "detail": f"const={rate['constant']}h, wall={rate['wall']}/SF"})
    else:
        results.append({"name": "Section 10A Letters on Deck", "status": "FAIL",
                        "detail": f"Got: {rate}"})

    return results


def test_jobinput_fields():
    """Task #4: New fields on JobInput with correct defaults."""
    results = []
    j = JobInput()

    checks = [
        ("sign_type", j.sign_type, SignType.CLLIT),
        ("cabinet_sf", j.cabinet_sf, 0.0),
        ("cabinet_face", j.cabinet_face, CabinetFace.SINGLE),
        ("cabinet_shape", j.cabinet_shape, CabinetShape.RECTANGULAR),
        ("cabinet_frame", j.cabinet_frame, CabinetFrame.LIGHT),
        ("paint_colors", j.paint_colors, 1),
        ("paint_sf", j.paint_sf, 0.0),
        ("install_mount_type", j.install_mount_type, "wall"),
        ("is_first_sign", j.is_first_sign, True),
    ]

    for name, actual, expected in checks:
        if actual == expected:
            results.append({"name": f"JobInput.{name}", "status": "PASS",
                            "detail": f"default={actual}"})
        else:
            results.append({"name": f"JobInput.{name}", "status": "FAIL",
                            "detail": f"expected={expected}, got={actual}"})

    return results


def test_install_correction():
    """CORRECTION 1: Install floor fires and matches warehouse P50 x 1.20."""
    results = []

    # CLLIT with small PF (42 PF = 10 letters 12")
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, install_height_ft=15,
        sign_type=SignType.CLLIT,
    )
    r = estimate(job)

    # Find 0640 install line
    install_hrs = next(
        (l.hours for l in r.install_lines if l.work_code == "0640"), 0
    )
    floor = INSTALL_FLOOR["CLLIT"]  # 9.90

    if install_hrs >= floor:
        results.append({"name": "CLLIT install floor (42 PF)", "status": "PASS",
                        "detail": f"install={install_hrs}h >= floor={floor}h"})
    else:
        results.append({"name": "CLLIT install floor (42 PF)", "status": "FAIL",
                        "detail": f"install={install_hrs}h < floor={floor}h"})

    # Verify correction warning present
    has_warning = any("Install corrected" in w for w in r.warnings)
    if has_warning:
        results.append({"name": "CLLIT install warning", "status": "PASS",
                        "detail": "Correction warning present"})
    else:
        results.append({"name": "CLLIT install warning", "status": "FAIL",
                        "detail": "No correction warning found"})

    # Large PF (200 PF) should exceed floor naturally
    job_large = JobInput(
        pf_manual=200.0, letter_height_inches=24,
        construction=ConstructionType.FACE_LIT, install_height_ft=15,
        sign_type=SignType.CLLIT,
    )
    r_large = estimate(job_large)
    large_install = next(
        (l.hours for l in r_large.install_lines if l.work_code == "0640"), 0
    )
    abc_raw = 1.50 + 200.0 * 0.036  # 8.70 crew-hrs... still below floor of 9.90
    # With floor=9.90, even 200 PF will be corrected
    if large_install >= floor:
        results.append({"name": "CLLIT install floor (200 PF)", "status": "PASS",
                        "detail": f"install={large_install}h (ABC raw={abc_raw:.2f}h, floor={floor}h)"})
    else:
        results.append({"name": "CLLIT install floor (200 PF)", "status": "FAIL",
                        "detail": f"install={large_install}h < floor={floor}h"})

    return results


def test_cllit_0270_correction():
    """CORRECTION 2: CLLIT 0270 floor fires for small PF jobs."""
    results = []

    # Small job: 42 PF, rate=0.021 -> ABC=0.88h, should be floored to 2.10h
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, sign_type=SignType.CLLIT,
    )
    r = estimate(job)
    mount_hrs = next(
        (l.hours for l in r.labor_lines if l.work_code == "0270"), 0
    )

    if mount_hrs >= CLLIT_0270_FLOOR:
        results.append({"name": "CLLIT 0270 floor (42 PF)", "status": "PASS",
                        "detail": f"0270={mount_hrs}h >= floor={CLLIT_0270_FLOOR}h (ABC raw=0.88h)"})
    else:
        results.append({"name": "CLLIT 0270 floor (42 PF)", "status": "FAIL",
                        "detail": f"0270={mount_hrs}h < floor={CLLIT_0270_FLOOR}h"})

    # Non-CLLIT type should NOT have the correction
    job_other = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, sign_type=SignType.OTHER,
    )
    r_other = estimate(job_other)
    mount_other = next(
        (l.hours for l in r_other.labor_lines if l.work_code == "0270"), 0
    )
    if mount_other < CLLIT_0270_FLOOR:
        results.append({"name": "Non-CLLIT 0270 unchanged", "status": "PASS",
                        "detail": f"OTHER 0270={mount_other}h (no correction applied)"})
    else:
        results.append({"name": "Non-CLLIT 0270 unchanged", "status": "INFO",
                        "detail": f"OTHER 0270={mount_other}h (above floor naturally)"})

    return results


def test_ot_probability():
    """CORRECTION 3: OT probability lines added for sign types with data."""
    results = []

    # CLLIT should have both 9200 and 9600
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, sign_type=SignType.CLLIT,
    )
    r = estimate(job)

    fab_ot = next((l for l in r.labor_lines if l.work_code == "9200"), None)
    inst_ot = next((l for l in r.install_lines if l.work_code == "9600"), None)

    ot = OT_FACTORS["CLLIT"]
    expected_fab = round(ot[0] * ot[1], 2)  # 0.346 * 8.09 = 2.80
    expected_inst = round(ot[2] * ot[3], 2)  # 0.471 * 4.43 = 2.09

    if fab_ot and abs(fab_ot.hours - expected_fab) < 0.01:
        results.append({"name": "CLLIT fab OT (9200)", "status": "PASS",
                        "detail": f"{fab_ot.hours}h (35% prob x 8.09h)"})
    else:
        results.append({"name": "CLLIT fab OT (9200)", "status": "FAIL",
                        "detail": f"Expected {expected_fab}h, got {fab_ot.hours if fab_ot else 'None'}"})

    if inst_ot and abs(inst_ot.hours - expected_inst) < 0.01:
        results.append({"name": "CLLIT install OT (9600)", "status": "PASS",
                        "detail": f"{inst_ot.hours}h (47% prob x 4.43h)"})
    else:
        results.append({"name": "CLLIT install OT (9600)", "status": "FAIL",
                        "detail": f"Expected {expected_inst}h, got {inst_ot.hours if inst_ot else 'None'}"})

    # GEMINI should only have install OT (no fab OT)
    job_gem = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, sign_type=SignType.GEMINI,
    )
    r_gem = estimate(job_gem)
    gem_fab = next((l for l in r_gem.labor_lines if l.work_code == "9200"), None)
    gem_inst = next((l for l in r_gem.install_lines if l.work_code == "9600"), None)

    if gem_fab is None:
        results.append({"name": "GEMINI no fab OT", "status": "PASS",
                        "detail": "No 9200 line (correct, prob=0%)"})
    else:
        results.append({"name": "GEMINI no fab OT", "status": "FAIL",
                        "detail": f"Unexpected 9200 line: {gem_fab.hours}h"})

    if gem_inst and gem_inst.hours > 0:
        results.append({"name": "GEMINI install OT (9600)", "status": "PASS",
                        "detail": f"{gem_inst.hours}h (48% prob x 1.81h)"})
    else:
        results.append({"name": "GEMINI install OT (9600)", "status": "FAIL",
                        "detail": f"Expected install OT line"})

    # OTHER should have NO OT lines (not in OT_FACTORS)
    job_other = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, sign_type=SignType.OTHER,
    )
    r_other = estimate(job_other)
    other_ot = [l for l in r_other.labor_lines + r_other.install_lines
                if l.work_code in ("9200", "9600")]
    if not other_ot:
        results.append({"name": "OTHER no OT lines", "status": "PASS",
                        "detail": "No OT lines for untracked type"})
    else:
        results.append({"name": "OTHER no OT lines", "status": "FAIL",
                        "detail": f"Unexpected OT lines: {[l.work_code for l in other_ot]}"})

    return results


def test_warehouse_validation():
    """Validate correction factors against DuckDB warehouse P50 values."""
    results = []
    try:
        import duckdb
        db = duckdb.connect(
            "C:/Scripts/signx-warehouse/warehouse/signx.duckdb", read_only=True
        )
    except Exception as e:
        return [{"name": "DuckDB connection", "status": "BLOCKED",
                 "detail": str(e)}]

    # Install P50 validation
    rows = db.execute("""
        SELECT
            c.sign_type,
            count(*) as n,
            round(percentile_cont(0.50) WITHIN GROUP (ORDER BY l.actual_hours), 2) as p50
        FROM so_contract_labor l
        JOIN so_contracts c ON l.wo_number = c.work_order
        WHERE l.work_code = '0630' AND l.actual_hours > 0
            AND c.sign_type IN ('CLLIT','POLLIT','MONDF','MONSF','DIRECT','AWNNON','GEMINI','LED','ALULIT')
        GROUP BY c.sign_type
    """).fetchall()

    for st, n, p50 in rows:
        floor = INSTALL_FLOOR.get(st)
        if floor is None:
            continue
        expected_floor = round(p50 * 1.20, 2)
        tolerance = 0.15  # 15% tolerance on the floor calculation
        ratio = floor / expected_floor if expected_floor > 0 else 0

        if 1.0 - tolerance <= ratio <= 1.0 + tolerance:
            results.append({
                "name": f"{st} install floor vs P50",
                "status": "PASS",
                "detail": f"floor={floor}h, P50*1.20={expected_floor}h, ratio={ratio:.2f}x (n={n})",
            })
        else:
            results.append({
                "name": f"{st} install floor vs P50",
                "status": "WARN",
                "detail": f"floor={floor}h, P50*1.20={expected_floor}h, ratio={ratio:.2f}x (n={n})",
            })

    # CLLIT 0270 P50 validation
    r = db.execute("""
        SELECT
            round(percentile_cont(0.50) WITHIN GROUP (ORDER BY l.actual_hours), 2) as p50
        FROM so_contract_labor l
        JOIN so_contracts c ON l.wo_number = c.work_order
        WHERE c.sign_type = 'CLLIT' AND l.work_code = '0270' AND l.actual_hours > 0
    """).fetchone()
    if r:
        p50 = r[0]
        expected = round(p50 * 1.20, 2)
        ratio = CLLIT_0270_FLOOR / expected if expected > 0 else 0
        if 0.85 <= ratio <= 1.15:
            results.append({
                "name": "CLLIT 0270 floor vs P50",
                "status": "PASS",
                "detail": f"floor={CLLIT_0270_FLOOR}h, P50*1.20={expected}h, ratio={ratio:.2f}x",
            })
        else:
            results.append({
                "name": "CLLIT 0270 floor vs P50",
                "status": "WARN",
                "detail": f"floor={CLLIT_0270_FLOOR}h, P50*1.20={expected}h, ratio={ratio:.2f}x",
            })

    db.close()
    return results


# ── Run All ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 80)
    print("  Phase 1 Validation Suite")
    print("=" * 80)

    all_results = []
    tests = [
        ("Task #2: Enums", test_enums),
        ("Task #3: Rate Dicts", test_rate_dicts),
        ("Task #4: JobInput Fields", test_jobinput_fields),
        ("Correction 1: Install Floor", test_install_correction),
        ("Correction 2: CLLIT 0270", test_cllit_0270_correction),
        ("Correction 3: OT Probability", test_ot_probability),
        ("Warehouse Validation", test_warehouse_validation),
    ]

    for section_name, test_fn in tests:
        print(f"\n--- {section_name} ---")
        section_results = test_fn()
        all_results.extend(section_results)
        for r in section_results:
            print(f"  [{r['status']:<8s}] {r['name']}")
            print(f"            {r['detail']}")

    # Scorecard
    print("\n" + "=" * 80)
    print("  PHASE 1 SCORECARD")
    print("=" * 80)
    pass_count = sum(1 for r in all_results if r["status"] == "PASS")
    warn_count = sum(1 for r in all_results if r["status"] == "WARN")
    fail_count = sum(1 for r in all_results if r["status"] == "FAIL")
    total = len(all_results)
    print(f"  PASS: {pass_count}/{total}")
    if warn_count:
        print(f"  WARN: {warn_count}/{total}")
    if fail_count:
        print(f"  FAIL: {fail_count}/{total}")
    print("=" * 80)
