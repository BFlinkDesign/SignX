"""
test_boundary.py — Boundary and edge case tests for abc_engine.

Covers:
  - Zero / minimum / maximum price_factor (PF) values
  - Edge case letter heights: 0, 1, 100 inches
  - Install height edge cases: 0, 1, 100 ft
  - Missing / None data handling (JobInput defaults)
  - Empty sign area (cabinet_sf=0, paint_sf=0)
  - Illumination status edge cases (CLLIT vs CLNON)
"""

import pytest

from abc_engine import (
    CabinetFace,
    CabinetFrame,
    CabinetShape,
    ConstructionType,
    FontType,
    JobInput,
    SignType,
    estimate,
    calculate_pf_from_chart,
    interpolate_pf,
    get_height_category,
    HeightCategory,
    FOOTAGE_CHART_BLOCK,
)


# ── PF / price_factor edge cases ──────────────────────────────────────────────

def test_pf_zero_does_not_crash():
    """estimate() with pf_manual=0 returns a result without raising."""
    job = JobInput(pf_manual=0.0, letter_height_inches=12,
                   font_type=FontType.BLOCK, construction=ConstructionType.FACE_LIT)
    result = estimate(job)
    assert result is not None


def test_pf_zero_produces_nonnegative_hours():
    """estimate() with pf_manual=0 returns non-negative total hours."""
    job = JobInput(pf_manual=0.0, letter_height_inches=12,
                   font_type=FontType.BLOCK, construction=ConstructionType.FACE_LIT)
    result = estimate(job)
    assert result.total_man_hours >= 0, (
        f"Negative man-hours at PF=0: {result.total_man_hours}"
    )


def test_pf_minimum_positive():
    """estimate() with pf_manual=0.01 (near-zero) returns a result."""
    job = JobInput(pf_manual=0.01, letter_height_inches=12,
                   font_type=FontType.BLOCK, construction=ConstructionType.FACE_LIT)
    result = estimate(job)
    assert result is not None
    assert result.total_man_hours >= 0


def test_pf_maximum_large_value():
    """estimate() with pf_manual=9999 (very large) returns a result without overflow."""
    job = JobInput(pf_manual=9999.0, letter_height_inches=12,
                   font_type=FontType.BLOCK, construction=ConstructionType.FACE_LIT)
    result = estimate(job)
    assert result is not None
    assert result.total_man_hours > 0, "Expected positive hours for very large PF"
    # Sanity: hours should not be infinite
    import math
    assert math.isfinite(result.total_man_hours), (
        f"total_man_hours is not finite for PF=9999: {result.total_man_hours}"
    )


def test_pf_hours_scale_with_pf():
    """Larger PF produces more labor hours (monotonic relationship)."""
    job_small = JobInput(pf_manual=10.0, letter_height_inches=12,
                         font_type=FontType.BLOCK, construction=ConstructionType.FACE_LIT)
    job_large = JobInput(pf_manual=500.0, letter_height_inches=12,
                         font_type=FontType.BLOCK, construction=ConstructionType.FACE_LIT)
    r_small = estimate(job_small)
    r_large = estimate(job_large)
    assert r_large.total_man_hours > r_small.total_man_hours, (
        f"Expected hours(PF=500) > hours(PF=10), got "
        f"{r_large.total_man_hours} vs {r_small.total_man_hours}"
    )


# ── Letter height edge cases ──────────────────────────────────────────────────

def test_height_zero_inches_chart_lookup():
    """calculate_pf_from_chart with height=0 uses the minimum chart entry."""
    pf = calculate_pf_from_chart(letter_count=1, height_inches=0, font=FontType.BLOCK)
    min_height = min(FOOTAGE_CHART_BLOCK.keys())
    expected_pf = FOOTAGE_CHART_BLOCK[min_height]
    assert pf == pytest.approx(expected_pf, rel=1e-6), (
        f"Height=0 should clamp to min chart entry {min_height}\": "
        f"expected pf={expected_pf}, got {pf}"
    )


def test_height_1_inch_estimate_does_not_crash():
    """estimate() with letter_height_inches=1 runs without raising."""
    job = JobInput(letter_count=5, letter_height_inches=1,
                   font_type=FontType.BLOCK, construction=ConstructionType.FACE_LIT)
    result = estimate(job)
    assert result is not None
    assert result.total_man_hours >= 0


def test_height_100_inches_estimate_does_not_crash():
    """estimate() with letter_height_inches=100 (very large) runs without raising."""
    job = JobInput(letter_count=5, letter_height_inches=100,
                   font_type=FontType.BLOCK, construction=ConstructionType.FACE_LIT)
    result = estimate(job)
    assert result is not None
    assert result.total_man_hours >= 0


def test_height_1_inch_category_is_small():
    """1-inch letters are categorized as HeightCategory.SMALL."""
    cat = get_height_category(1)
    assert cat == HeightCategory.SMALL, f"Expected SMALL for 1\", got {cat}"


def test_height_100_inches_category_is_xlarge():
    """100-inch letters are categorized as HeightCategory.XLARGE."""
    cat = get_height_category(100)
    assert cat == HeightCategory.XLARGE, f"Expected XLARGE for 100\", got {cat}"


def test_height_0_inches_category_is_small():
    """0-inch letters (edge) are categorized as HeightCategory.SMALL."""
    cat = get_height_category(0)
    assert cat == HeightCategory.SMALL, f"Expected SMALL for 0\", got {cat}"


# ── Install height edge cases ─────────────────────────────────────────────────

def test_install_height_zero_ft_does_not_crash():
    """estimate() with install_height_ft=0 runs without raising."""
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, install_height_ft=0,
    )
    result = estimate(job)
    assert result is not None


def test_install_height_1_ft_does_not_crash():
    """estimate() with install_height_ft=1 runs without raising."""
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, install_height_ft=1,
    )
    result = estimate(job)
    assert result is not None


def test_install_height_100_ft_does_not_crash():
    """estimate() with install_height_ft=100 runs without raising."""
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, install_height_ft=100,
    )
    result = estimate(job)
    assert result is not None


def test_install_height_higher_produces_more_install_hours():
    """Higher install height should produce >= install hours than ground level."""
    job_low = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, install_height_ft=5,
    )
    job_high = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, install_height_ft=50,
    )
    r_low = estimate(job_low)
    r_high = estimate(job_high)
    low_hrs = sum(l.hours for l in r_low.install_lines)
    high_hrs = sum(l.hours for l in r_high.install_lines)
    assert high_hrs >= low_hrs, (
        f"Expected install hours at 50ft >= 5ft, got {high_hrs} vs {low_hrs}"
    )


# ── Missing / None data handling ──────────────────────────────────────────────

def test_jobinput_all_defaults_does_not_crash():
    """JobInput() with no arguments runs estimate() without raising."""
    job = JobInput()
    result = estimate(job)
    assert result is not None


def test_jobinput_none_pf_manual_uses_chart():
    """When pf_manual is None/default, engine falls back to footage chart calculation."""
    job_with_chart = JobInput(
        letter_count=10, letter_height_inches=12,
        font_type=FontType.BLOCK, construction=ConstructionType.FACE_LIT,
    )
    job_with_manual = JobInput(
        pf_manual=42.0,  # 10 letters * 4.20 PF/letter = 42 PF from chart
        letter_height_inches=12,
        font_type=FontType.BLOCK, construction=ConstructionType.FACE_LIT,
    )
    r_chart = estimate(job_with_chart)
    r_manual = estimate(job_with_manual)
    # Both should produce comparable results (within 5%)
    assert r_chart.total_man_hours > 0
    assert r_manual.total_man_hours > 0
    ratio = r_chart.total_man_hours / r_manual.total_man_hours
    assert 0.90 <= ratio <= 1.10, (
        f"Chart-derived PF hours differ unexpectedly from manual PF=42: "
        f"chart={r_chart.total_man_hours:.2f}h, manual={r_manual.total_man_hours:.2f}h"
    )


def test_letter_count_zero_does_not_crash():
    """letter_count=0 with no pf_manual runs estimate() without raising."""
    job = JobInput(letter_count=0, letter_height_inches=12,
                   font_type=FontType.BLOCK, construction=ConstructionType.FACE_LIT)
    result = estimate(job)
    assert result is not None


def test_return_depth_zero_does_not_crash():
    """return_depth_inches=0 (flat face, no return) runs without raising."""
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, return_depth_inches=0,
    )
    result = estimate(job)
    assert result is not None


# ── Empty sign area ───────────────────────────────────────────────────────────

def test_cabinet_sf_zero_does_not_crash():
    """cabinet_sf=0 (no cabinet work) runs estimate() without raising."""
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, cabinet_sf=0.0,
    )
    result = estimate(job)
    assert result is not None


def test_paint_sf_zero_skips_paint_labor():
    """paint_sf=0 produces no 5A paint labor lines."""
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, paint_sf=0.0, paint_colors=1,
    )
    result = estimate(job)
    # With 0 SF there should be no Section 5A paint line (work code 0330)
    paint_lines = [l for l in result.labor_lines if l.work_code == "0330"]
    assert not paint_lines, (
        f"Expected no 0330 paint lines with paint_sf=0, got {paint_lines}"
    )


def test_cabinet_sf_positive_adds_cabinet_labor():
    """cabinet_sf > 0 produces Section 2 cabinet labor hours."""
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT,
        cabinet_sf=50.0,
        cabinet_face=CabinetFace.SINGLE,
        cabinet_frame=CabinetFrame.LIGHT,
        cabinet_shape=CabinetShape.RECTANGULAR,
    )
    result = estimate(job)
    # Section 2 cabinet fab uses work code 0200
    cabinet_lines = [l for l in result.labor_lines if l.work_code == "0200"]
    assert cabinet_lines, "Expected 0200 cabinet labor line when cabinet_sf=50"
    assert cabinet_lines[0].hours > 0


# ── Illumination status edge cases ────────────────────────────────────────────

def test_cllit_produces_led_material():
    """CLLIT (illuminated) estimate includes LED module material line."""
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, sign_type=SignType.CLLIT,
    )
    result = estimate(job)
    # LED modules: Hanley 3120 is 307-0261
    led_parts = [m for m in result.material_bom if "307-" in m.get("part", "")]
    assert led_parts, (
        "Expected LED module material line (307-XXXX) in CLLIT estimate"
    )


def test_clnon_install_ot_from_calibration():
    """CLNON install OT suppressed after 253K-row recalibration (0.27h < 0.50h threshold)."""
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, sign_type=SignType.CLNON,
    )
    result = estimate(job)
    inst_ot = next((l for l in result.install_lines if l.work_code == "9600"), None)
    # CLNON OT: 18.8% prob x 1.42h avg = 0.27h -- below 0.50h suppression threshold
    assert inst_ot is None, (
        f"CLNON 9600 should be suppressed (0.27h < 0.50h threshold), got {inst_ot}"
    )


def test_halo_construction_does_not_crash():
    """HALO construction type runs estimate() without raising."""
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.HALO, sign_type=SignType.CLLIT,
    )
    result = estimate(job)
    assert result is not None
    assert result.total_man_hours >= 0


def test_open_face_construction_does_not_crash():
    """OPEN_FACE construction type runs estimate() without raising."""
    job = JobInput(
        letter_count=10, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.OPEN_FACE, sign_type=SignType.CLNON,
    )
    result = estimate(job)
    assert result is not None
    assert result.total_man_hours >= 0


def test_halo_vs_face_lit_different_hours():
    """HALO and FACE_LIT construction types produce different labor totals."""
    job_face = JobInput(
        pf_manual=100.0, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.FACE_LIT, sign_type=SignType.CLLIT,
    )
    job_halo = JobInput(
        pf_manual=100.0, letter_height_inches=12, font_type=FontType.BLOCK,
        construction=ConstructionType.HALO, sign_type=SignType.CLLIT,
    )
    r_face = estimate(job_face)
    r_halo = estimate(job_halo)
    # They should differ — halo uses different ABC section rates
    assert r_face.total_man_hours != r_halo.total_man_hours, (
        "FACE_LIT and HALO construction produced identical hours — "
        "different ABC sections should yield different results"
    )


# ── Result structure integrity ────────────────────────────────────────────────

def test_result_has_required_fields():
    """EstimateResult always contains expected output fields."""
    job = JobInput(letter_count=10, letter_height_inches=12,
                   font_type=FontType.BLOCK, construction=ConstructionType.FACE_LIT)
    result = estimate(job)
    assert hasattr(result, "labor_lines"), "Missing labor_lines"
    assert hasattr(result, "install_lines"), "Missing install_lines"
    assert hasattr(result, "material_bom"), "Missing material_bom"
    assert hasattr(result, "total_man_hours"), "Missing total_man_hours"
    assert hasattr(result, "warnings"), "Missing warnings"


def test_labor_lines_have_work_codes():
    """All labor line items have a non-empty work_code string."""
    job = JobInput(letter_count=10, letter_height_inches=12,
                   font_type=FontType.BLOCK, construction=ConstructionType.FACE_LIT)
    result = estimate(job)
    for line in result.labor_lines + result.install_lines:
        assert line.work_code and isinstance(line.work_code, str), (
            f"Labor line missing work_code: {line}"
        )


def test_material_bom_has_required_keys():
    """All BOM entries have part, item, qty, and unit keys."""
    job = JobInput(letter_count=10, letter_height_inches=12,
                   font_type=FontType.BLOCK, construction=ConstructionType.FACE_LIT,
                   return_depth_inches=5)
    result = estimate(job)
    required_keys = {"part", "item", "qty", "unit"}
    for m in result.material_bom:
        missing = required_keys - set(m.keys())
        assert not missing, f"BOM entry missing keys {missing}: {m}"
