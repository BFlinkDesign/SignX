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

from apex_signcalc.wind_asce7 import (
    G_RIGID,
    KD_SIGNS,
    ke,
    kz,
    velocity_pressure,
    wind_force_on_sign,
)
import apex_signcalc.wind_asce7 as w


# Deterministic case identical to the CI structural smoke test.
SMOKE = dict(
    V_mph=115,
    sign_width_ft=8,
    sign_height_ft=4,
    height_to_top_ft=14,
    exposure="C",
)


def test_velocity_pressure_requires_five_positional_args():
    """Signature guard: velocity_pressure must take V, Kz, Kzt, Kd, Ke."""
    params = list(inspect.signature(velocity_pressure).parameters)
    assert params == ["V", "Kz", "Kzt", "Kd", "Ke"]


def test_wind_force_on_sign_does_not_raise_and_is_positive():
    """The defect raised TypeError before reaching a result."""
    r = wind_force_on_sign(**SMOKE)
    assert r["governing_F_lbf"] > 0
    assert r["governing_case"] in ("A", "B", "C")


def test_qz_matches_asce_eq_26_10_1_with_kd_applied_once():
    """qz must equal 0.00256*Kz*Kzt*Kd*Ke*V^2 (Kd once, not Kd^2)."""
    r = wind_force_on_sign(**SMOKE)
    h_centroid = SMOKE["height_to_top_ft"] - SMOKE["sign_height_ft"] / 2.0
    Kz = kz(h_centroid, SMOKE["exposure"])
    Ke = ke(0.0)
    qz_expected = 0.00256 * Kz * 1.0 * KD_SIGNS * Ke * SMOKE["V_mph"] ** 2
    assert math.isclose(r["qz_psf"], round(qz_expected, 2), abs_tol=0.02)


def test_force_step_does_not_reapply_kd():
    """F_A = qz * G * Cf * A — Kd already in qz, not multiplied again."""
    r = wind_force_on_sign(**SMOKE)
    A = SMOKE["sign_width_ft"] * SMOKE["sign_height_ft"]
    Cf_A = w._interp_cf_ab_by_bs(
        SMOKE["sign_width_ft"] / SMOKE["sign_height_ft"],
        SMOKE["sign_height_ft"] / SMOKE["height_to_top_ft"],
    )
    f_a_expected = r["qz_psf"] * G_RIGID * Cf_A * A
    assert math.isclose(r["F_A_lbf"], f_a_expected, rel_tol=1e-3, abs_tol=0.5)


def test_kd_reported_and_single_application_golden():
    """Golden values for the CI smoke scenario (Kd applied exactly once)."""
    r = wind_force_on_sign(**SMOKE)
    assert math.isclose(r["Kd"], KD_SIGNS, abs_tol=1e-9)
    assert math.isclose(r["qz_psf"], 24.46, abs_tol=0.05)
    # Kd^2 double-count would drop F_A to ~0.85x of this value.
    assert math.isclose(r["F_A_lbf"], 864.9, rel_tol=0, abs_tol=1.0)
