"""
test_phase1.py — Phase 1 validation: correction factors vs warehouse actuals.

Tests that the three Phase 0 corrections (install floor, CLLIT 0270 floor,
OT probability) are properly encoded and produce estimates within reasonable
range of warehouse P50 values.

Source data: signx.duckdb (so_contract_labor + so_contracts)
"""

import pytest

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


# ── Task #2: Enums ────────────────────────────────────────────────────────────

def test_sign_type_enum_members():
    """All expected SignType enum members are present."""
    expected_types = {
        "CLLIT", "CLNON", "MONDF", "MONSF", "POLLIT", "DIRECT",
        "BLDILL", "BLDNON", "AWNNON", "GEMINI", "LED",
        "ALULIT", "ALUNON", "VINYL", "NEON", "OTHER",
    }
    actual = {s.value for s in SignType}
    assert actual == expected_types, (
        f"Missing: {expected_types - actual}, Extra: {actual - expected_types}"
    )


def test_cabinet_shape_enum_members():
    """CabinetShape has exactly rectangular, semi_irregular, intricate."""
    shapes = {s.value for s in CabinetShape}
    assert shapes == {"rectangular", "semi_irregular", "intricate"}


def test_cabinet_frame_enum_members():
    """CabinetFrame has exactly light, heavy, none."""
    frames = {f.value for f in CabinetFrame}
    assert frames == {"light", "heavy", "none"}


def test_cabinet_face_enum_members():
    """CabinetFace has exactly single_face, double_face."""
    faces = {f.value for f in CabinetFace}
    assert faces == {"single_face", "double_face"}


# ── Task #3: Rate Dicts ───────────────────────────────────────────────────────

def test_section2_sf_light_rectangular():
    """Section 2 SF Light Rectangular rate matches ABC guide values."""
    key = (CabinetFace.SINGLE, CabinetFrame.LIGHT, CabinetShape.RECTANGULAR)
    rate = SECTION_2_RATES.get(key)
    assert rate is not None, "Key not found in SECTION_2_RATES"
    assert rate["labor"] == 0.184, f"Expected labor=0.184, got {rate['labor']}"
    assert rate["material"] == 1.80, f"Expected material=1.80, got {rate['material']}"


def test_section2_df_heavy_rectangular():
    """Section 2 DF Heavy Rectangular labor rate matches ABC guide."""
    key = (CabinetFace.DOUBLE, CabinetFrame.HEAVY, CabinetShape.RECTANGULAR)
    rate = SECTION_2_RATES.get(key)
    assert rate is not None, "Key not found in SECTION_2_RATES"
    assert rate["labor"] == 0.265, f"Expected labor=0.265, got {rate['labor']}"


def test_section2e_raceway_straight():
    """Section 2E raceway straight labor rate matches ABC guide."""
    rate = SECTION_2E_RATES.get(("raceway", "straight"))
    assert rate is not None, "Key ('raceway','straight') not found in SECTION_2E_RATES"
    assert rate["labor"] == 0.208, f"Expected labor=0.208/LF, got {rate['labor']}"


def test_section5a_1_color():
    """Section 5A 1-color rates match ABC guide."""
    rate = SECTION_5A_RATES.get(1)
    assert rate is not None, "Key 1 not found in SECTION_5A_RATES"
    assert rate["constant"] == 1.0, f"Expected constant=1.0h, got {rate['constant']}"
    assert rate["labor"] == 0.017, f"Expected labor=0.017/SF, got {rate['labor']}"


def test_section5a_5_colors():
    """Section 5A 5-color rates match ABC guide."""
    rate = SECTION_5A_RATES.get(5)
    assert rate is not None, "Key 5 not found in SECTION_5A_RATES"
    assert rate["constant"] == 3.0, f"Expected constant=3.0h, got {rate['constant']}"
    assert rate["labor"] == 0.050, f"Expected labor=0.050/SF, got {rate['labor']}"


def test_section10a_sf_plastic_first():
    """Section 10A SF plastic first rates match ABC guide."""
    rate = SECTION_10A_RATES.get(("sf_plastic", "first"))
    assert rate is not None, "Key ('sf_plastic','first') not found in SECTION_10A_RATES"
    assert rate["constant"] == 1.50, f"Expected constant=1.50h, got {rate['constant']}"
    assert rate["wall"] == 0.036, f"Expected wall=0.036/SF, got {rate['wall']}"


def test_section10a_letters_on_deck():
    """Section 10A letters on deck rates match ABC guide."""
    rate = SECTION_10A_RATES.get(("letters_on_deck", "first"))
    assert rate is not None, "Key ('letters_on_deck','first') not found in SECTION_10A_RATES"
    assert rate["constant"] == 2.00, f"Expected constant=2.00h, got {rate['constant']}"
    assert rate["wall"] == 0.040, f"Expected wall=0.040/SF, got {rate['wall']}"


# ── Task #4: JobInput Fields ──────────────────────────────────────────────────

def test_jobinput_default_sign_type():
    assert JobInput().sign_type == SignType.CLLIT


def test_jobinput_default_cabinet_sf():
    assert JobInput().cabinet_sf == 0.0


def test_jobinput_default_cabinet_face():
    assert JobInput().cabinet_face == CabinetFace.SINGLE


def test_jobinput_default_cabinet_shape():
    assert JobInput().cabinet_shape == CabinetShape.RECTANGULAR


def test_jobinput_default_cabinet_frame():
    assert JobInput().cabinet_frame == CabinetFrame.LIGHT


def test_jobinput_default_paint_colors():
    assert JobInput().paint_colors == 1


def test_jobinput_default_paint_sf():
    assert JobInput().paint_sf == 0.0


def test_jobinput_default_install_mount_type():
    assert JobInput().install_mount_type == "wall"


def test_jobinput_default_is_first_sign():
    assert JobInput().is_first_sign is True


# ── Correction 1: Install Floor ───────────────────────────────────────────────

def test_cllit_install_floor_small_pf():
    """CLLIT install floor fires for small 42 PF job (10 letters 12")."""
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, install_height_ft=15,
        sign_type=SignType.CLLIT,
    )
    r = estimate(job)
    install_hrs = next(
        (l.hours for l in r.install_lines if l.work_code == "0640"), 0
    )
    floor = INSTALL_FLOOR["CLLIT"]  # 9.90
    assert install_hrs >= floor, (
        f"CLLIT install hours {install_hrs}h < floor {floor}h for 42 PF job"
    )


def test_cllit_install_correction_warning_present():
    """Correction warning is emitted when install floor fires."""
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, install_height_ft=15,
        sign_type=SignType.CLLIT,
    )
    r = estimate(job)
    has_warning = any("Install corrected" in w for w in r.warnings)
    assert has_warning, "Expected 'Install corrected' warning but none found"


def test_cllit_install_floor_large_pf():
    """CLLIT install floor still applies at 200 PF (ABC raw 8.70h < floor 9.90h)."""
    job_large = JobInput(
        pf_manual=200.0, letter_height_inches=24,
        construction=ConstructionType.FACE_LIT, install_height_ft=15,
        sign_type=SignType.CLLIT,
    )
    r_large = estimate(job_large)
    large_install = next(
        (l.hours for l in r_large.install_lines if l.work_code == "0640"), 0
    )
    floor = INSTALL_FLOOR["CLLIT"]  # 9.90
    assert large_install >= floor, (
        f"CLLIT install hours {large_install}h < floor {floor}h for 200 PF job"
    )


# ── Correction 2: CLLIT 0270 Floor ───────────────────────────────────────────

def test_cllit_0270_floor_fires_for_small_pf():
    """CLLIT 0270 floor fires: 42 PF ABC raw=0.88h should be raised to floor."""
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, sign_type=SignType.CLLIT,
    )
    r = estimate(job)
    mount_hrs = next(
        (l.hours for l in r.labor_lines if l.work_code == "0270"), 0
    )
    assert mount_hrs >= CLLIT_0270_FLOOR, (
        f"CLLIT 0270 hours {mount_hrs}h < floor {CLLIT_0270_FLOOR}h (ABC raw ~0.88h)"
    )


def test_non_cllit_0270_not_corrected():
    """Non-CLLIT sign types do NOT have the 0270 floor correction applied."""
    job_other = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, sign_type=SignType.OTHER,
    )
    r_other = estimate(job_other)
    mount_other = next(
        (l.hours for l in r_other.labor_lines if l.work_code == "0270"), 0
    )
    # Should be below the CLLIT correction floor (correction not applied to OTHER)
    assert mount_other < CLLIT_0270_FLOOR, (
        f"OTHER sign type 0270={mount_other}h is unexpectedly at or above CLLIT floor {CLLIT_0270_FLOOR}h"
    )


# ── Correction 3: OT Probability ─────────────────────────────────────────────

def test_cllit_fab_ot_line_present():
    """CLLIT estimate includes a 9200 (fab OT) line with correct probability hours."""
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, sign_type=SignType.CLLIT,
    )
    r = estimate(job)
    fab_ot = next((l for l in r.labor_lines if l.work_code == "9200"), None)
    ot = OT_FACTORS["CLLIT"]
    expected_fab = round(ot[0] * ot[1], 2)  # 0.346 * 8.09 = 2.80
    assert fab_ot is not None, "Expected 9200 fab OT line not found"
    assert abs(fab_ot.hours - expected_fab) < 0.01, (
        f"CLLIT 9200 hours: expected {expected_fab}h, got {fab_ot.hours}h"
    )


def test_cllit_install_ot_line_present():
    """CLLIT estimate includes a 9600 (install OT) line with correct probability hours."""
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, sign_type=SignType.CLLIT,
    )
    r = estimate(job)
    inst_ot = next((l for l in r.install_lines if l.work_code == "9600"), None)
    ot = OT_FACTORS["CLLIT"]
    expected_inst = round(ot[2] * ot[3], 2)  # 0.471 * 4.43 = 2.09
    assert inst_ot is not None, "Expected 9600 install OT line not found"
    assert abs(inst_ot.hours - expected_inst) < 0.01, (
        f"CLLIT 9600 hours: expected {expected_inst}h, got {inst_ot.hours}h"
    )


def test_gemini_no_fab_ot():
    """GEMINI sign type has no 9200 fab OT line (prob=0%)."""
    job_gem = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, sign_type=SignType.GEMINI,
    )
    r_gem = estimate(job_gem)
    gem_fab = next((l for l in r_gem.labor_lines if l.work_code == "9200"), None)
    assert gem_fab is None, f"Unexpected 9200 fab OT line for GEMINI: {gem_fab}"


def test_gemini_has_install_ot():
    """GEMINI sign type has a 9600 install OT line with hours > 0."""
    job_gem = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, sign_type=SignType.GEMINI,
    )
    r_gem = estimate(job_gem)
    gem_inst = next((l for l in r_gem.install_lines if l.work_code == "9600"), None)
    assert gem_inst is not None and gem_inst.hours > 0, (
        "Expected GEMINI install OT (9600) line with hours > 0"
    )


def test_other_sign_type_no_ot_lines():
    """OTHER sign type (not in OT_FACTORS) has no 9200 or 9600 lines."""
    job_other = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, sign_type=SignType.OTHER,
    )
    r_other = estimate(job_other)
    ot_lines = [
        l for l in r_other.labor_lines + r_other.install_lines
        if l.work_code in ("9200", "9600")
    ]
    assert not ot_lines, (
        f"Unexpected OT lines for OTHER type: {[l.work_code for l in ot_lines]}"
    )


# ── Warehouse Validation (requires DuckDB) ────────────────────────────────────

@pytest.mark.skipif(
    not __import__("pathlib").Path(
        "C:/Scripts/signx-warehouse/warehouse/signx.duckdb"
    ).exists(),
    reason="DuckDB warehouse not available",
)
def test_install_floors_within_15pct_of_warehouse_p50():
    """Install floor values are within 15% of warehouse P50 * 1.20 for each sign type."""
    import duckdb
    db = duckdb.connect(
        "C:/Scripts/signx-warehouse/warehouse/signx.duckdb", read_only=True
    )
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
    db.close()

    failures = []
    for st, n, p50 in rows:
        floor = INSTALL_FLOOR.get(st)
        if floor is None:
            continue
        expected_floor = round(p50 * 1.20, 2)
        if expected_floor <= 0:
            continue
        ratio = floor / expected_floor
        tolerance = 0.15
        if not (1.0 - tolerance <= ratio <= 1.0 + tolerance):
            failures.append(
                f"{st}: floor={floor}h, P50*1.20={expected_floor}h, ratio={ratio:.2f}x (n={n})"
            )

    assert not failures, "Install floors outside 15% tolerance:\n" + "\n".join(failures)


@pytest.mark.skipif(
    not __import__("pathlib").Path(
        "C:/Scripts/signx-warehouse/warehouse/signx.duckdb"
    ).exists(),
    reason="DuckDB warehouse not available",
)
def test_cllit_0270_floor_within_15pct_of_warehouse_p50():
    """CLLIT 0270 floor is within 15% of warehouse P50 * 1.20."""
    import duckdb
    db = duckdb.connect(
        "C:/Scripts/signx-warehouse/warehouse/signx.duckdb", read_only=True
    )
    row = db.execute("""
        SELECT
            round(percentile_cont(0.50) WITHIN GROUP (ORDER BY l.actual_hours), 2) as p50
        FROM so_contract_labor l
        JOIN so_contracts c ON l.wo_number = c.work_order
        WHERE c.sign_type = 'CLLIT' AND l.work_code = '0270' AND l.actual_hours > 0
    """).fetchone()
    db.close()

    assert row is not None, "No CLLIT 0270 data in warehouse"
    p50 = row[0]
    expected = round(p50 * 1.20, 2)
    assert expected > 0
    ratio = CLLIT_0270_FLOOR / expected
    assert 0.85 <= ratio <= 1.15, (
        f"CLLIT 0270 floor={CLLIT_0270_FLOOR}h, P50*1.20={expected}h, ratio={ratio:.2f}x — outside 15% tolerance"
    )
