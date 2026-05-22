"""Tests for calc_40398.py — black-box live-run + independent re-derivation.

Scope (HONEST): these verify the calc's COMPUTATIONAL correctness and its
honesty labelling. They do NOT and cannot verify the structural DESIGN is
complete/safe/PE-sealed. "Tests pass" here == the math/logic is correct and
the two grounded defect fixes are locked, NOT a stamped design.
"""
from __future__ import annotations
import math, re, subprocess, sys
from pathlib import Path
import pytest

HERE = Path(__file__).parent
SCRIPT = HERE / "calc_40398.py"

# constants — MUST mirror calc_40398.py exactly (independent re-derivation)
B_w, s_h = 15 + 3/12, 14 + 8/12
As = B_w * s_h
z_cen = s_h / 2.0
Ke = math.exp(-0.0000362 * 1279.0)
Kz, Kzt, Kd, G, Cf = 0.85, 1.0, 0.85, 0.85, 1.45  # Cf grounded: ASCE 7-22 Fig 29.3-1 (s/h=1, B/s~1)


@pytest.fixture(scope="module")
def out():
    r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True,
                        text=True, timeout=60)
    assert r.returncode == 0, f"calc exited {r.returncode}: {r.stderr[:400]}"
    return r.stdout


def _blocks(text):
    """Parse per-V rows -> {V: {...}}."""
    res = {}
    for m in re.finditer(
        r"V=(\d+) mph.*?qz=\s*([\d.]+)psf\s+F=\s*([\d.]+)lb\s+"
        r"M_base=\s*([\d.]+)ftlb.*?footing:\s*[\d.]+x[\d.]+x[\d.]+ft\s+\w+\s+"
        r"smax=([\d.]+)psf\s+e=([\d.]+)\s+kern=([\d.]+)\s+"
        r"FS_OT=([\d.]+)\s+FS_SL=([\d.]+).*?dia_est~([\d.]+)in",
        text, re.S):
        V = int(m.group(1))
        res[V] = dict(qz=float(m.group(2)), F=float(m.group(3)),
                      M=float(m.group(4)), smax=float(m.group(5)),
                      e=float(m.group(6)), kern=float(m.group(7)),
                      FS_OT=float(m.group(8)), FS_SL=float(m.group(9)),
                      dia=float(m.group(10)))
    return res


def test_exit_and_three_blocks(out):
    b = _blocks(out)
    assert set(b) == {111, 115, 119}, f"missing V blocks: {sorted(b)}"


@pytest.mark.parametrize("V", [111, 115, 119])
def test_wind_independent_rederivation(out, V):
    b = _blocks(out)[V]
    qz = 0.00256 * Kz * Kzt * Kd * Ke * V * V
    F = qz * G * Cf * As
    M = F * z_cen
    assert b["qz"] == pytest.approx(qz, rel=0.01), (b["qz"], qz)
    assert b["F"] == pytest.approx(F, rel=0.01), (b["F"], F)
    assert b["M"] == pytest.approx(M, rel=0.01), (b["M"], M)


def test_monotonic(out):
    b = _blocks(out)
    assert b[111]["F"] < b[115]["F"] < b[119]["F"]
    assert b[111]["M"] < b[115]["M"] < b[119]["M"]
    assert b[111]["smax"] <= 1500 and b[115]["smax"] <= 1500 and b[119]["smax"] <= 1500


@pytest.mark.parametrize("V", [111, 115, 119])
def test_footing_middle_third_margin(out, V):
    """Regression for defect-fix #2: e must be within 0.75*kern (not knife-edge)."""
    b = _blocks(out)[V]
    assert b["e"] <= 0.75 * b["kern"] + 0.02, (V, b["e"], b["kern"])
    assert b["FS_OT"] >= 1.5 and b["FS_SL"] >= 1.5


@pytest.mark.parametrize("V", [111, 115, 119])
def test_anchor_uses_0375_factor(out, V):
    """Regression for defect-fix #1: anchor Ft = 0.375*Fu (AISC 360-22), not 0.33."""
    b = _blocks(out)[V]
    # re-derive dia from printed M with the CORRECT 0.375 factor
    Mp = b["M"] / 2.0
    T_grp = Mp / (8.0/12.0)
    T_bolt = T_grp / 2.0
    Ab_375 = T_bolt / (0.375*58000.0)
    dia_375 = math.sqrt(Ab_375*4/math.pi)/0.78
    Ab_33 = T_bolt / (0.33*58000.0)
    dia_33 = math.sqrt(Ab_33*4/math.pi)/0.78
    assert b["dia"] == pytest.approx(dia_375, abs=0.03), (b["dia"], dia_375)
    assert abs(b["dia"] - dia_33) > 0.05, "still using superseded 0.33 factor"


def test_honesty_labels_present(out):
    """The calc MUST self-declare non-final status (governance rule)."""
    for token in ("???? DRAFT", "PRE-PE", "NOT COMPLETE", "NOT APPROVED",
                  "DEFERRED/UNVERIFIED", "ASSERT"):
        assert token in out, f"missing integrity label: {token!r}"


# ---- rational 2-pole overturning mechanics (defect #3/#5 + deflection) ----
POLE_SPACING_FT = 7.0


def _rational(out):
    r = {}
    for m in re.finditer(
        r"V=(\d+) mph.*?M_base=\s*([\d.]+)ftlb.*?"
        r"2-pole RATIONAL \(governs\): P_couple=([\d.]+)lb "
        r"V_pole=([\d.]+)lb T_uplift=([\d.]+)lb T_bolt~([\d.]+)lb "
        r"dia~([\d.]+)in\s+defl=([\d.]+)/([\d.]+)in\s+(OK|FAIL)",
        out, re.S):
        r[int(m.group(1))] = dict(M=float(m.group(2)), P=float(m.group(3)),
            Vp=float(m.group(4)), Tu=float(m.group(5)), Tb=float(m.group(6)),
            dia=float(m.group(7)), defl=float(m.group(8)),
            dlim=float(m.group(9)), ok=m.group(10))
    return r


def test_rational_block_present(out):
    assert set(_rational(out)) == {111, 115, 119}


@pytest.mark.parametrize("V", [111, 115, 119])
def test_couple_equals_M_over_spacing(out, V):
    b = _rational(out)[V]
    assert b["P"] == pytest.approx(b["M"] / POLE_SPACING_FT, rel=0.01)


def test_rational_monotonic(out):
    r = _rational(out)
    assert r[111]["P"] < r[115]["P"] < r[119]["P"]
    assert r[111]["Tu"] < r[115]["Tu"] < r[119]["Tu"]


@pytest.mark.parametrize("V", [111, 115, 119])
def test_deflection_within_limit(out, V):
    b = _rational(out)[V]
    assert b["defl"] <= b["dlim"] and b["ok"] == "OK", (V, b)
