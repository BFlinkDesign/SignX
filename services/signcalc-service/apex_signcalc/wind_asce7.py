from __future__ import annotations

from typing import Dict


def interpolate_kz(kz_table: Dict[str, Dict[float, float]], exposure: str, z_ft: float) -> float:
    rows = sorted(kz_table.get(exposure, {} ).items())
    if not rows:
        return 1.0
    xs = [h for h, _ in rows]
    ys = [v for _, v in rows]
    if z_ft <= xs[0]:
        return ys[0]
    if z_ft >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= z_ft <= xs[i + 1]:
            x0, x1 = xs[i], xs[i + 1]
            y0, y1 = ys[i], ys[i + 1]
            t = (z_ft - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return ys[-1]


def qz_psf(V_basic: float, kz: float, kzt: float, kd: float, G: float) -> float:
    # qz = 0.00256 * Kz * Kzt * Kd * V^2 * G
    return 0.00256 * kz * kzt * kd * (V_basic ** 2) * G


