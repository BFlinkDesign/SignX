from __future__ import annotations

def qz_psf(V_basic: float, Kz: float, Kzt: float, Kd: float, G: float = 0.85) -> float:
    """ASCE 7 convention (lb/ft^2).

    qz = 0.00256 * Kz * Kzt * Kd * V_basic^2 * G
    """
    return 0.00256 * Kz * Kzt * Kd * (V_basic ** 2) * G


