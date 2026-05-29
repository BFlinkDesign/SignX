"""Regression tests for the Kd handling in wind_force_on_sign.

Guards two related defects:

1. wind_force_on_sign() called velocity_pressure() with 4 positional args
   (V, Kz, Kzt, Ke) instead of 5 (V, Kz, Kzt, Kd, Ke), raising
   ``TypeError: velocity_pressure() missing 1 required positional
   argument: 'Ke'`` for every caller.

2. The naive crash-fix (just adding Kd to the velocity_pressure call)
   would double-count Kd, because the force step also multiplied by
   Kd_val. Per ASCE 7-22 Eq. 26.10-1, Kd belongs in qz and the force is
   F = qz * G * Cf * A. These tests assert Kd is applied exactly once.
"""

from __future__ import annotations

import inspect
import math

import pytest

from apex_signcalc.wind_asce7 import (
    G_RIGID,
    KD_SIGNS,
    _interp_cf_ab_by_bs,
    ke,
    kz,
    velocity_pressure,
    wind_force_on_sign,
)

# Deterministic case identical to the CI structural smoke test.
V_MPH = 115
WIDTH_FT = 8.0
HEIGHT_FT = 4.0
TOP_FT = 14.0
EXPOSURE = "C"

# Result keys (named once to avoid duplicated string literals).
K_F = "governing_F_lbf"
K_CASE = "governing_case"
K_QZ = "qz_psf"
K_FA = "F_A_lbf"
K_KD = "Kd"


@pytest.fixture(scope="module")
def result() -> dict:
    return wind_force_on_sign(
        V_mph=V_MPH,
        sign_width_ft=WIDTH_FT,
        sign_height_ft=HEIGHT_FT,
        height_to_top_ft=TOP_FT,
        exposure=EXPOSURE,
    )


def test_velocity_pressure_requires_five_positional_args():
    """Signature guard: velocity_pressure must take V, Kz, Kzt, Kd, Ke."""
    params = list(inspect.signature(velocity_pressure).parameters)
    assert params == ["V", "Kz", "Kzt", "Kd", "Ke"]


def test_wind_force_on_sign_does_not_raise_and_is_positive(result):
    """The defect raised TypeError before reaching a result."""
    assert result[K_F] > 0
    assert result[K_CASE] in ("A", "B", "C")


def test_qz_matches_asce_eq_26_10_1_with_kd_applied_once(result):
    """qz must equal 0.00256*Kz*Kzt*Kd*Ke*V^2 (Kd once, not Kd^2)."""
    h_centroid = TOP_FT - HEIGHT_FT / 2.0
    kz_val = kz(h_centroid, EXPOSURE)
    ke_val = ke(0.0)
    qz_expected = 0.00256 * kz_val * 1.0 * KD_SIGNS * ke_val * V_MPH**2
    assert math.isclose(result[K_QZ], round(qz_expected, 2), abs_tol=0.02)


def test_force_step_does_not_reapply_kd(result):
    """F_A = qz * G * Cf * A — Kd already in qz, not multiplied again."""
    area = WIDTH_FT * HEIGHT_FT
    cf_a = _interp_cf_ab_by_bs(WIDTH_FT / HEIGHT_FT, HEIGHT_FT / TOP_FT)
    f_a_expected = result[K_QZ] * G_RIGID * cf_a * area
    assert math.isclose(result[K_FA], f_a_expected, rel_tol=1e-3, abs_tol=0.5)


def test_kd_reported_and_single_application_golden(result):
    """Golden values for the CI smoke scenario (Kd applied exactly once)."""
    assert math.isclose(result[K_KD], KD_SIGNS, abs_tol=1e-9)
    assert math.isclose(result[K_QZ], 24.46, abs_tol=0.05)
    # Kd^2 double-count would drop F_A to ~0.85x of this value.
    assert math.isclose(result[K_FA], 864.9, rel_tol=0, abs_tol=1.0)
