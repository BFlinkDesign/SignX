from __future__ import annotations


def qb_pa(rho: float, v_b: float) -> float:
    # qb = 0.5 * rho * v_b^2
    return 0.5 * rho * (v_b ** 2)


def qp_pa(ce_z: float, ce_T: float, qb: float) -> float:
    # q_p(z) = c_e(z) * c_{e,T} * q_b
    return ce_z * ce_T * qb


