"""
test_regression.py — Estimation regression tests for abc_engine.

Covers:
  - Channel letter estimates (face-lit, halo, strip, CLNON)
  - Monument estimates (MONDF non-illuminated, MONSF illuminated)
  - Awning estimates (standard SF, larger SF)
  - Removal estimates (CLLIT, MONDF)

Each test locks in a known-good output value. Any future change that shifts
total_hours by more than 2% will be caught by the EXACT value assertions.
The "reasonable range" assertions provide an independent sanity layer.

Baseline capture: 2026-02-17 using abc_engine.py @ commit 1781383
Baseline refreshed: 2026-02-26 post OT-correction + removal formula engine update
Baseline refreshed: 2026-03-02 post calibration with 253K-row temp_labor dataset (36 sign types, 948 cells)
"""

import sys
import pytest

sys.path.insert(0, ".")

from abc_engine import (
    estimate_building,
    CabinetFace,
    CabinetFrame,
    CabinetShape,
    ConstructionType,
    FontType,
    JobInput,
    SignType,
    estimate,
    estimate_awning,
    estimate_monument,
    estimate_removal,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _work_codes(result) -> set[str]:
    """Return set of all work codes in labor + install lines."""
    return {l.work_code for l in result.labor_lines + result.install_lines}


def _assert_reasonable_range(value: float, lo: float, hi: float, label: str) -> None:
    assert lo <= value <= hi, (
        f"{label}: {value:.2f}h is outside expected range [{lo}, {hi}]"
    )


# ── Scenario 1: Standard CLLIT face-lit, 10 letters 18 inches ────────────────
#
# Locked baseline (refreshed 2026-03-02 post 253K-row calibration):
#   total_man_hours = 19.85   total_crew_hours = 4.21
# Expected work codes: 0110 0200 0210 0270 0282 0310 0410 0610 0620 0640 9600
# Note: 9200 fab OT dropped below threshold after recalibration (0.38h < 0.50h)

CL_STD_JOB = JobInput(
    letter_count=10, letter_height_inches=18, font_type=FontType.BLOCK,
    construction=ConstructionType.FACE_LIT, sign_type=SignType.CLLIT,
    install_height_ft=15, miles_one_way=20, crew_size=2,
)


def test_cl_std_total_man_hours_locked():
    """Locked: standard CLLIT 10x18in total_man_hours == 19.85h."""
    r = estimate(CL_STD_JOB)
    assert r.total_man_hours == pytest.approx(19.85, abs=0.01), (
        f"Regression: expected 19.85h, got {r.total_man_hours}h"
    )


def test_cl_std_total_crew_hours_locked():
    """Locked: standard CLLIT 10x18in total_crew_hours == 4.21h."""
    r = estimate(CL_STD_JOB)
    assert r.total_crew_hours == pytest.approx(4.21, abs=0.01), (
        f"Regression: expected 4.21h crew, got {r.total_crew_hours}h"
    )


def test_cl_std_work_codes_complete():
    """Standard CLLIT estimate has all expected work codes."""
    r = estimate(CL_STD_JOB)
    expected = {"0110", "0200", "0210", "0270", "0310", "0410",
                "0640", "0610", "0620", "0282", "9600"}
    assert expected.issubset(_work_codes(r)), (
        f"Missing work codes: {expected - _work_codes(r)}"
    )


def test_cl_std_reasonable_hour_range():
    """Standard CLLIT 10-letter job: total hours in sane range [20, 60]."""
    r = estimate(CL_STD_JOB)
    total = r.total_man_hours + r.total_crew_hours
    _assert_reasonable_range(total, 20, 60, "CLLIT 10x18in total hours")


def test_cl_std_bom_structure():
    """Standard CLLIT estimate BOM has required keys on every entry."""
    r = estimate(CL_STD_JOB)
    assert r.material_bom, "BOM is empty for standard CLLIT job"
    required_keys = {"part", "item", "qty", "unit"}
    for entry in r.material_bom:
        missing = required_keys - set(entry.keys())
        assert not missing, f"BOM entry missing keys {missing}: {entry}"


# ── Scenario 2: CLLIT halo construction, 90 PF manual, 36-inch letters ───────
#
# Locked baseline (refreshed 2026-03-02 post 253K-row calibration):
#   total_man_hours = 19.29   total_crew_hours = 4.38

CL_HALO_JOB = JobInput(
    pf_manual=90.0, letter_height_inches=36, font_type=FontType.BLOCK,
    construction=ConstructionType.HALO, sign_type=SignType.CLLIT,
    install_height_ft=20,
)


def test_cl_halo_total_man_hours_locked():
    """Locked: CLLIT halo 90 PF 36-in total_man_hours == 19.29h."""
    r = estimate(CL_HALO_JOB)
    assert r.total_man_hours == pytest.approx(19.29, abs=0.01), (
        f"Regression: expected 19.29h, got {r.total_man_hours}h"
    )


def test_cl_halo_crew_hours_at_install_floor():
    """Halo CLLIT: crew hours at calibrated install floor (4.38h)."""
    r = estimate(CL_HALO_JOB)
    assert r.total_crew_hours == pytest.approx(4.38, abs=0.01), (
        f"Regression: expected 4.38h crew, got {r.total_crew_hours}h"
    )


def test_cl_halo_reasonable_range():
    """CLLIT halo 90 PF: total hours in range [20, 80]."""
    r = estimate(CL_HALO_JOB)
    total = r.total_man_hours + r.total_crew_hours
    _assert_reasonable_range(total, 20, 80, "CLLIT halo 90 PF total hours")


# ── Scenario 3: CLNON non-illuminated, script font, 8 letters 12-inch ────────
#
# Locked baseline (refreshed 2026-03-02 post 253K-row calibration):
#   total_man_hours = 12.34   total_crew_hours = 3.09
# CLNON: OT dropped below threshold after recalibration (fab 0.49h, install 0.27h < 0.50h)

CL_NON_JOB = JobInput(
    letter_count=8, letter_height_inches=12, font_type=FontType.SCRIPT,
    construction=ConstructionType.FACE_LIT, sign_type=SignType.CLNON,
    install_height_ft=12,
)


def test_cl_non_total_man_hours_locked():
    """Locked: CLNON script 8x12in total_man_hours == 12.34h."""
    r = estimate(CL_NON_JOB)
    assert r.total_man_hours == pytest.approx(12.34, abs=0.01), (
        f"Regression: expected 12.34h, got {r.total_man_hours}h"
    )


def test_cl_non_no_ot_lines():
    """CLNON OT suppressed after recalibration (both below 0.50h threshold)."""
    r = estimate(CL_NON_JOB)
    ot_codes = {l.work_code for l in r.labor_lines + r.install_lines
                if l.work_code in ("9200", "9600")}
    assert ot_codes == set(), (
        f"CLNON OT should be suppressed (below threshold), found: {ot_codes}"
    )


def test_cl_non_reasonable_range():
    """CLNON 8-letter script job: total hours in range [10, 40]."""
    r = estimate(CL_NON_JOB)
    total = r.total_man_hours + r.total_crew_hours
    _assert_reasonable_range(total, 10, 40, "CLNON script 8x12in total hours")


# ── Scenario 4: Strip channel letters 150 PF, 40-ft install height ───────────
#
# Locked baseline (refreshed 2026-03-02 post 253K-row calibration):
#   total_man_hours = 34.26   total_crew_hours = 9.05

CL_STRIP_JOB = JobInput(
    pf_manual=150.0, letter_height_inches=36, font_type=FontType.BLOCK,
    construction=ConstructionType.STRIP, sign_type=SignType.CLLIT,
    install_height_ft=40, crew_size=3, miles_one_way=30,
)


def test_cl_strip_total_man_hours_locked():
    """Locked: strip CLLIT 150 PF 40-ft install total_man_hours == 34.26h."""
    r = estimate(CL_STRIP_JOB)
    assert r.total_man_hours == pytest.approx(34.26, abs=0.01), (
        f"Regression: expected 34.26h, got {r.total_man_hours}h"
    )


def test_cl_strip_crew_at_floor():
    """Strip CLLIT at 40ft: crew hours at calibrated floor (9.05)."""
    r = estimate(CL_STRIP_JOB)
    assert r.total_crew_hours == pytest.approx(9.05, abs=0.01), (
        f"Expected 9.05h crew, got {r.total_crew_hours}h"
    )


def test_cl_strip_reasonable_range():
    """Strip CLLIT 150 PF: total hours in range [30, 100]."""
    r = estimate(CL_STRIP_JOB)
    total = r.total_man_hours + r.total_crew_hours
    _assert_reasonable_range(total, 30, 100, "Strip CLLIT 150 PF total hours")


# ── Scenario 5: Monument MONDF non-illuminated, 32 SF (4x8 ft) ───────────────
#
# Locked baseline (captured 2026-02-17):
#   total_man_hours = 56.94   total_crew_hours = 0.0
# Expected codes include: 0110 0200 0210 0220 0235 0270 0410 0420 0520 0550 9200 0610 0620 0630

MON_DF_NL_JOB = JobInput(
    sign_type=SignType.MONDF, sign_sf_per_face=32.0, num_faces=2,
    is_illuminated=False, has_vinyl=True, has_structural_steel=False,
    install_height_ft=6, miles_one_way=0, crew_size=2,
)


def test_mon_df_nl_total_man_hours_locked():
    """Locked: MONDF non-lit 32 SF/face total_man_hours == 56.94h."""
    r = estimate_monument(MON_DF_NL_JOB)
    assert r.total_man_hours == pytest.approx(56.94, abs=0.01), (
        f"Regression: expected 56.94h, got {r.total_man_hours}h"
    )


def test_mon_df_nl_crew_hours_zero():
    """MONDF non-lit: no crew-hours (monument uses man-hours for 0630)."""
    r = estimate_monument(MON_DF_NL_JOB)
    assert r.total_crew_hours == 0.0, (
        f"Expected 0 crew hours for MONDF, got {r.total_crew_hours}"
    )


def test_mon_df_nl_work_codes_present():
    """MONDF estimate includes expected fab + install work codes."""
    r = estimate_monument(MON_DF_NL_JOB)
    codes = _work_codes(r)
    expected = {"0110", "0200", "0210", "0220", "0235", "0270",
                "0410", "0420", "0610", "0620", "0630"}
    missing = expected - codes
    assert not missing, f"MONDF missing work codes: {missing}"


def test_mon_df_nl_vinyl_codes_present():
    """MONDF with has_vinyl=True includes 0520 and 0550 codes."""
    r = estimate_monument(MON_DF_NL_JOB)
    codes = _work_codes(r)
    assert "0520" in codes, "Missing 0520 (cut/weed vinyl) in MONDF estimate"
    assert "0550" in codes, "Missing 0550 (vinyl application) in MONDF estimate"


def test_mon_df_nl_correction_warning_present():
    """MONDF estimate emits a correction warning."""
    r = estimate_monument(MON_DF_NL_JOB)
    has_correction = any("MONDF corrections applied" in w for w in r.warnings)
    assert has_correction, f"Expected MONDF correction warning, got: {r.warnings}"


def test_mon_df_nl_reasonable_range():
    """MONDF 32 SF non-lit: total hours in range [10, 100]."""
    r = estimate_monument(MON_DF_NL_JOB)
    _assert_reasonable_range(r.total_man_hours, 10, 100, "MONDF 32SF non-lit man-hours")


# ── Scenario 6: Monument MONSF illuminated, 20 SF (5x4 ft) ──────────────────
#
# Locked baseline (recalibrated 2026-03-02 after MONSF correction factors added):
#   total_man_hours = 25.54   total_crew_hours = 0.0
# Prior stale baseline 58.20h used MONDF factors — MONSF is much simpler.

MON_SF_LIT_JOB = JobInput(
    sign_type=SignType.MONSF, sign_sf_per_face=20.0, num_faces=1,
    is_illuminated=True, has_vinyl=True, install_height_ft=5,
)


def test_mon_sf_lit_total_man_hours_locked():
    """Locked: MONSF illuminated 20 SF total_man_hours == 25.54h."""
    r = estimate_monument(MON_SF_LIT_JOB)
    assert r.total_man_hours == pytest.approx(25.54, abs=0.01), (
        f"Regression: expected 25.54h, got {r.total_man_hours}h"
    )


def test_mon_sf_lit_electrical_code_present():
    """MONSF illuminated estimate includes 0340 (electrical wiring)."""
    r = estimate_monument(MON_SF_LIT_JOB)
    codes = _work_codes(r)
    assert "0340" in codes, "Missing 0340 (electrical wiring) in illuminated monument"


def test_mon_sf_lit_install_ot_present():
    """MONSF illuminated: 9600 install OT present (LIT OT rate 16.4% > threshold)."""
    r = estimate_monument(MON_SF_LIT_JOB)
    codes = _work_codes(r)
    assert "9600" in codes, (
        "Expected 9600 install OT for illuminated MONSF (LIT rate=16.4%, install=3.00h)"
    )


def test_mon_sf_lit_reasonable_range():
    """MONSF illuminated 20 SF: total hours in range [10, 100]."""
    r = estimate_monument(MON_SF_LIT_JOB)
    _assert_reasonable_range(r.total_man_hours, 10, 100, "MONSF 20SF lit man-hours")


# ── Scenario 7: Awning 60 SF with travel ─────────────────────────────────────
#
# Locked baseline (captured 2026-02-17):
#   total_man_hours = 37.90   total_crew_hours = 8.52
# Expected codes: 0110 0250 0260 0270 9200 0610 0620 0630 0640 9600

AWN_60SF_JOB = JobInput(
    sign_type=SignType.AWNNON, sign_sf_per_face=60.0, num_faces=1,
    miles_one_way=15, crew_size=2,
)


def test_awn_60sf_total_man_hours_locked():
    """Locked: awning 60 SF w/ 15 mi travel total_man_hours == 37.90h."""
    r = estimate_awning(AWN_60SF_JOB)
    assert r.total_man_hours == pytest.approx(37.90, abs=0.01), (
        f"Regression: expected 37.90h, got {r.total_man_hours}h"
    )


def test_awn_60sf_crew_hours_locked():
    """Locked: awning 60 SF crew hours == 8.52h (0640 2-man install)."""
    r = estimate_awning(AWN_60SF_JOB)
    assert r.total_crew_hours == pytest.approx(8.52, abs=0.01), (
        f"Regression: expected 8.52h crew, got {r.total_crew_hours}h"
    )


def test_awn_60sf_work_codes_present():
    """Awning 60 SF estimate has all expected work codes."""
    r = estimate_awning(AWN_60SF_JOB)
    codes = _work_codes(r)
    expected = {"0110", "0250", "0260", "0270", "9200",
                "0610", "0620", "0630", "0640", "9600"}
    missing = expected - codes
    assert not missing, f"Awning missing work codes: {missing}"


def test_awn_60sf_reasonable_range():
    """Awning 60 SF: total hours in range [10, 100]."""
    r = estimate_awning(AWN_60SF_JOB)
    total = r.total_man_hours + r.total_crew_hours
    _assert_reasonable_range(total, 10, 100, "Awning 60SF total hours")


# ── Scenario 8: Awning 100 SF (larger job) ───────────────────────────────────
#
# Locked baseline (captured 2026-02-17):
#   total_man_hours = 64.90   total_crew_hours = 14.20

AWN_100SF_JOB = JobInput(
    sign_type=SignType.AWNNON, sign_sf_per_face=100.0, num_faces=1,
)


def test_awn_100sf_total_man_hours_locked():
    """Locked: awning 100 SF total_man_hours == 64.90h."""
    r = estimate_awning(AWN_100SF_JOB)
    assert r.total_man_hours == pytest.approx(64.90, abs=0.01), (
        f"Regression: expected 64.90h, got {r.total_man_hours}h"
    )


def test_awn_100sf_crew_hours_locked():
    """Locked: awning 100 SF crew hours == 14.20h."""
    r = estimate_awning(AWN_100SF_JOB)
    assert r.total_crew_hours == pytest.approx(14.20, abs=0.01), (
        f"Regression: expected 14.20h crew, got {r.total_crew_hours}h"
    )


def test_awn_scales_linearly_with_sf():
    """Awning hours scale roughly proportionally with SF (60 vs 100)."""
    r60 = estimate_awning(AWN_60SF_JOB)
    r100 = estimate_awning(JobInput(sign_type=SignType.AWNNON,
                                    sign_sf_per_face=100.0, num_faces=1))
    # 100 SF should produce more hours than 60 SF
    assert r100.total_man_hours > r60.total_man_hours, (
        f"100 SF awning should have more man-hours than 60 SF: "
        f"{r100.total_man_hours} vs {r60.total_man_hours}"
    )


# ── Scenario 8b: Illuminated awning AWNILL 60 SF ─────────────────────────────
#
# Locked baseline (captured 2026-03-02 after AWNILL SignType added):
#   total_man_hours = 46.30   total_crew_hours = 8.52
# vs AWNNON 60SF = 37.90h  (+8.40h for 0200 Fab Layout + 0310 Electrical)
# Expected codes: 0110 0200 0250 0260 0270 0310 9200 0610 0620 0630 0640 9600

AWNILL_60SF_JOB = JobInput(
    sign_type=SignType.AWNILL,
    sign_sf_per_face=60.0,
    num_faces=1,
    is_illuminated=True,
)


def test_awnill_60sf_total_man_hours_locked():
    """Locked: illuminated awning 60 SF total_man_hours == 46.30h."""
    r = estimate_awning(AWNILL_60SF_JOB)
    assert r.total_man_hours == pytest.approx(46.30, abs=0.01), (
        f"Regression: expected 46.30h, got {r.total_man_hours}h"
    )


def test_awnill_60sf_crew_hours_locked():
    """Locked: illuminated awning 60 SF total_crew_hours == 8.52h."""
    r = estimate_awning(AWNILL_60SF_JOB)
    assert r.total_crew_hours == pytest.approx(8.52, abs=0.01), (
        f"Regression: expected 8.52h crew, got {r.total_crew_hours}h"
    )


def test_awnill_has_electrical_codes():
    """AWNILL must include 0200 (Fab Layout) and 0310 (Electrical); AWNNON must not."""
    r_ill = estimate_awning(AWNILL_60SF_JOB)
    codes_ill = _work_codes(r_ill)
    assert "0200" in codes_ill, "AWNILL missing 0200 Fab Layout"
    assert "0310" in codes_ill, "AWNILL missing 0310 Electrical"
    r_non = estimate_awning(AWN_60SF_JOB)
    codes_non = _work_codes(r_non)
    assert "0200" not in codes_non, "AWNNON should not have 0200"
    assert "0310" not in codes_non, "AWNNON should not have 0310"


def test_awnill_more_hours_than_awnnon():
    """AWNILL must produce more hours than AWNNON at same SF."""
    r_ill = estimate_awning(AWNILL_60SF_JOB)
    r_non = estimate_awning(AWN_60SF_JOB)
    assert r_ill.total_man_hours > r_non.total_man_hours, (
        f"AWNILL {r_ill.total_man_hours}h should exceed AWNNON {r_non.total_man_hours}h"
    )


# ── Scenario 9: Removal of CLLIT channel letters ─────────────────────────────
#
# Locked baseline (refreshed 2026-03-02 post 253K-row calibration):
#   total_man_hours = 5.56   total_crew_hours = 0.0
# Expected codes: 0625 0610 0620 9600

REM_CLLIT_JOB = JobInput(
    sign_type=SignType.CLLIT, num_units=1, miles_one_way=20, crew_size=2,
)


def test_rem_cllit_total_man_hours_locked():
    """Locked: CLLIT removal w/ 20 mi travel total_man_hours == 5.56h."""
    r = estimate_removal(REM_CLLIT_JOB)
    assert r.total_man_hours == pytest.approx(5.56, abs=0.01), (
        f"Regression: expected 5.56h, got {r.total_man_hours}h"
    )


def test_rem_cllit_has_removal_code():
    """CLLIT removal estimate includes 0625 (removal) work code."""
    r = estimate_removal(REM_CLLIT_JOB)
    codes = _work_codes(r)
    assert "0625" in codes, "Missing 0625 (removal) in CLLIT removal estimate"


def test_rem_cllit_has_travel_code():
    """CLLIT removal with miles_one_way=20 includes 0620 (travel)."""
    r = estimate_removal(REM_CLLIT_JOB)
    codes = _work_codes(r)
    assert "0620" in codes, "Missing 0620 (travel) in CLLIT removal estimate"


def test_rem_cllit_no_crew_hours():
    """Removal estimates produce zero crew hours."""
    r = estimate_removal(REM_CLLIT_JOB)
    assert r.total_crew_hours == 0.0, (
        f"Expected 0 crew hours for removal, got {r.total_crew_hours}"
    )


def test_rem_cllit_reasonable_range():
    """CLLIT removal: total man-hours in range [5, 40]."""
    r = estimate_removal(REM_CLLIT_JOB)
    _assert_reasonable_range(r.total_man_hours, 5, 40, "CLLIT removal man-hours")


# ── Scenario 10: Removal of MONDF monument ───────────────────────────────────
#
# Locked baseline (refreshed 2026-03-02 post 253K-row calibration):
#   total_man_hours = 2.80   total_crew_hours = 0.0

REM_MONDF_JOB = JobInput(
    sign_type=SignType.MONDF, num_units=1, miles_one_way=0, crew_size=2,
)


def test_rem_mondf_total_man_hours_locked():
    """Locked: MONDF removal (no travel) total_man_hours == 2.80h."""
    r = estimate_removal(REM_MONDF_JOB)
    assert r.total_man_hours == pytest.approx(2.80, abs=0.01), (
        f"Regression: expected 2.80h, got {r.total_man_hours}h"
    )


def test_rem_mondf_reasonable_range():
    """MONDF removal: total man-hours in range [2, 30]."""
    r = estimate_removal(REM_MONDF_JOB)
    _assert_reasonable_range(r.total_man_hours, 2, 30, "MONDF removal man-hours")


# ── Pydantic model validation ─────────────────────────────────────────────────

from pydantic import ValidationError

from models import (
    AwningEstimateRequest,
    ChannelLetterEstimateRequest,
    DimensionUnit,
    MonumentEstimateRequest,
    RemovalEstimateRequest,
)


class TestChannelLetterRequestValidation:

    def test_valid_cl_request_passes(self):
        """Valid ChannelLetterEstimateRequest with letter_count + height passes."""
        req = ChannelLetterEstimateRequest(letter_count=10, letter_height=18.0)
        assert req.letter_count == 10

    def test_valid_cl_request_pf_manual_passes(self):
        """Valid ChannelLetterEstimateRequest with pf_manual passes."""
        req = ChannelLetterEstimateRequest(pf_manual=75.0)
        assert req.pf_manual == 75.0

    def test_zero_letter_count_and_no_pf_raises(self):
        """ChannelLetterEstimateRequest with zero letter_count AND no pf_manual raises."""
        with pytest.raises(ValidationError, match="pf_manual.*letter_count|letter_count.*pf_manual"):
            ChannelLetterEstimateRequest(letter_count=0, pf_manual=None)

    def test_negative_pf_manual_raises(self):
        """Negative pf_manual is rejected by ge=0 constraint."""
        with pytest.raises(ValidationError):
            ChannelLetterEstimateRequest(pf_manual=-1.0)

    def test_pf_manual_too_large_raises(self):
        """pf_manual above 5000 is rejected by le=5000 constraint."""
        with pytest.raises(ValidationError):
            ChannelLetterEstimateRequest(pf_manual=9999.0)

    def test_mm_height_confusion_guard_raises(self):
        """height=210 with unit=inches triggers the >200 confusion guard.

        210 inches is within the le=240 field limit so Pydantic accepts the
        field value, but the model_validator then rejects it because 210 > 200
        looks like a mm value that should have been converted first.
        """
        with pytest.raises(ValidationError, match="mm"):
            ChannelLetterEstimateRequest(
                letter_count=10,
                letter_height=210.0,  # above 200-inch guard, within le=240 field cap
                dimension_unit=DimensionUnit.INCHES,
            )

    def test_inch_height_with_mm_unit_raises(self):
        """Small height value (e.g. 18) with unit=mm triggers confusion guard."""
        with pytest.raises(ValidationError, match="mm"):
            ChannelLetterEstimateRequest(
                letter_count=10,
                letter_height=18.0,   # 18 inches is < 50mm threshold
                dimension_unit=DimensionUnit.MM,
            )

    def test_to_job_input_roundtrip(self):
        """to_job_input() converts correctly and estimate() produces positive hours."""
        req = ChannelLetterEstimateRequest(
            letter_count=10, letter_height=18.0,
            dimension_unit=DimensionUnit.INCHES,
        )
        job = req.to_job_input()
        r = estimate(job)
        assert r.total_man_hours > 0


class TestMonumentRequestValidation:

    def test_valid_mondf_passes(self):
        """Valid MonumentEstimateRequest with width + height passes."""
        req = MonumentEstimateRequest(sign_type=SignType.MONDF, width=8.0, height=4.0)
        assert req.sign_type == SignType.MONDF

    def test_valid_monsf_with_area_passes(self):
        """Valid MONSF with face_area_sf direct override passes."""
        req = MonumentEstimateRequest(
            sign_type=SignType.MONSF,
            width=0.0, height=0.0,
            face_area_sf=20.0,
        )
        assert req.get_face_area_sf() == pytest.approx(20.0)

    def test_wrong_sign_type_raises(self):
        """Non-monument sign type (e.g. CLLIT) raises ValidationError."""
        with pytest.raises(ValidationError, match="MONDF|MONSF"):
            MonumentEstimateRequest(sign_type=SignType.CLLIT, width=8.0, height=4.0)

    def test_zero_dimensions_no_area_raises(self):
        """Width=0 and height=0 with no face_area_sf raises ValidationError."""
        with pytest.raises(ValidationError):
            MonumentEstimateRequest(sign_type=SignType.MONDF, width=0.0, height=0.0)

    def test_mm_unit_small_width_raises(self):
        """width < 100mm with unit=mm triggers confusion guard."""
        with pytest.raises(ValidationError, match="mm"):
            MonumentEstimateRequest(
                sign_type=SignType.MONDF,
                width=8.0,   # looks like 8 feet, not 8mm (too small for mm)
                height=4.0,
                dimension_unit=DimensionUnit.MM,
            )

    def test_feet_unit_huge_width_raises(self):
        """width > 50 feet triggers confusion guard (likely supplied in inches)."""
        with pytest.raises(ValidationError, match="feet"):
            MonumentEstimateRequest(
                sign_type=SignType.MONDF,
                width=96.0,   # 96 inches, not 96 feet
                height=48.0,
                dimension_unit=DimensionUnit.FEET,
            )

    def test_get_face_area_sf_from_dimensions(self):
        """get_face_area_sf() computes correctly from feet dimensions."""
        req = MonumentEstimateRequest(
            sign_type=SignType.MONDF,
            width=8.0, height=4.0,
            dimension_unit=DimensionUnit.FEET,
        )
        # 8ft x 4ft = 32 SF
        assert req.get_face_area_sf() == pytest.approx(32.0, abs=0.01)

    def test_get_face_area_sf_from_inches(self):
        """get_face_area_sf() converts inches to SF correctly."""
        req = MonumentEstimateRequest(
            sign_type=SignType.MONDF,
            width=96.0, height=48.0,
            dimension_unit=DimensionUnit.INCHES,
        )
        # (96 * 48) / 144 = 32 SF
        assert req.get_face_area_sf() == pytest.approx(32.0, abs=0.01)


class TestAwningRequestValidation:

    def test_valid_awning_request_passes(self):
        """Valid AwningEstimateRequest with projection + width passes."""
        req = AwningEstimateRequest(projection=36.0, width=120.0)
        assert req.projection == 36.0

    def test_wrong_sign_type_raises(self):
        """Non-awning sign type (e.g. MONDF) raises ValidationError."""
        with pytest.raises(ValidationError, match="AWNNON"):
            AwningEstimateRequest(
                sign_type=SignType.MONDF,
                projection=36.0, width=120.0,
            )

    def test_zero_projection_raises(self):
        """projection=0 raises ValidationError (require_nonzero_geometry)."""
        with pytest.raises(ValidationError):
            AwningEstimateRequest(projection=0.0, width=120.0)

    def test_zero_width_raises(self):
        """width=0 raises ValidationError."""
        with pytest.raises(ValidationError):
            AwningEstimateRequest(projection=36.0, width=0.0)

    def test_feet_unit_large_projection_raises(self):
        """projection > 20 with unit=feet triggers confusion guard."""
        with pytest.raises(ValidationError, match="feet"):
            AwningEstimateRequest(
                projection=36.0,   # 36 feet — exceeds the 20ft guard
                width=120.0,
                dimension_unit=DimensionUnit.FEET,
            )

    def test_mm_unit_small_projection_raises(self):
        """projection < 100mm triggers confusion guard."""
        with pytest.raises(ValidationError, match="mm"):
            AwningEstimateRequest(
                projection=36.0,   # 36mm — looks like inches supplied by mistake
                width=120.0,
                dimension_unit=DimensionUnit.MM,
            )

    def test_get_projection_inches_from_inches(self):
        """get_projection_inches() returns value unchanged for unit=inches."""
        req = AwningEstimateRequest(projection=36.0, width=120.0,
                                    dimension_unit=DimensionUnit.INCHES)
        assert req.get_projection_inches() == pytest.approx(36.0)

    def test_get_projection_inches_from_feet(self):
        """get_projection_inches() converts feet to inches correctly."""
        req = AwningEstimateRequest(projection=3.0, width=10.0,
                                    dimension_unit=DimensionUnit.FEET)
        assert req.get_projection_inches() == pytest.approx(36.0)

    def test_face_sf_calculated_correctly(self):
        """get_face_sf() returns width*valance/144 when has_valance=True."""
        req = AwningEstimateRequest(
            projection=36.0, width=120.0, valance_height=12.0,
            has_valance=True, dimension_unit=DimensionUnit.INCHES,
        )
        # 120in x 12in / 144 = 10 SF
        assert req.get_face_sf() == pytest.approx(10.0, abs=0.01)

    def test_face_sf_zero_without_valance(self):
        """get_face_sf() returns 0 when has_valance=False."""
        req = AwningEstimateRequest(
            projection=36.0, width=120.0, valance_height=12.0,
            has_valance=False,
        )
        assert req.get_face_sf() == 0.0


class TestRemovalRequestValidation:

    def test_valid_removal_request_passes(self):
        """Valid RemovalEstimateRequest passes validation."""
        req = RemovalEstimateRequest(sign_type=SignType.CLLIT, num_units=2,
                                     remove_height_ft=15.0)
        assert req.num_units == 2

    def test_negative_num_units_raises(self):
        """num_units < 1 raises ValidationError."""
        with pytest.raises(ValidationError):
            RemovalEstimateRequest(sign_type=SignType.CLLIT, num_units=0)

    def test_crane_without_height_raises(self):
        """requires_crane=True with height < 15 ft raises ValidationError."""
        with pytest.raises(ValidationError, match="crane"):
            RemovalEstimateRequest(
                sign_type=SignType.CLLIT,
                num_units=1,
                requires_crane=True,
                remove_height_ft=10.0,  # Below 15 ft minimum for crane
            )

    def test_demolition_on_non_pole_raises(self):
        """requires_demolition=True on CLLIT (non-pole) raises ValidationError."""
        with pytest.raises(ValidationError, match="demolition"):
            RemovalEstimateRequest(
                sign_type=SignType.CLLIT,
                num_units=1,
                requires_demolition=True,
            )

    def test_demolition_on_mondf_passes(self):
        """requires_demolition=True on MONDF (monument) passes validation."""
        req = RemovalEstimateRequest(
            sign_type=SignType.MONDF,
            num_units=1,
            requires_demolition=True,
        )
        assert req.requires_demolition is True

    def test_crane_with_sufficient_height_passes(self):
        """requires_crane=True with height >= 15 ft passes validation."""
        req = RemovalEstimateRequest(
            sign_type=SignType.CLLIT,
            num_units=1,
            requires_crane=True,
            remove_height_ft=25.0,
        )
        assert req.requires_crane is True


def test_building_extrusion_total_man_hours_locked():
    """Locked baseline for building signs (9" extrusion)."""
    job = JobInput(
        sign_type=SignType.BLDILL,
        sign_sf_per_face=50.0,
        num_faces=1,
        is_illuminated=True,
        construction_method="extrusion",
        return_depth_in=9.0
    )
    r = estimate_building(job)
    # Baseline updated 2026-03-02 Claude Opus 4.6 — post estimate_building() rewrite
    # Breakdown: 0110=0.75h + 0200=1.25h + 0220=4.60h + 0260=2.50h + 0270=5.00h + 0310=4.00h + 0630=2.25h = 20.35h
    assert r.total_man_hours == pytest.approx(20.35, abs=0.01)
    assert "202-0387" in str(r.material_bom)

