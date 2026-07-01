"""
Form coefficient calculations (Cb, Cm, Cp, Cw).

MVP scope: monohull only, using standard Lpp * Bwl * T formulas
(confirmed — no per-demihull variant needed for this module).

Cp is deliberately computed independently from volume/(Am * Lpp) rather
than derived as Cb/Cm. This gives a free internal consistency check: if
independently-computed Cp diverges meaningfully from Cb/Cm, it signals a
problem in the midship-section extraction, surfaced via `cp_consistency_flag`.
"""
from dataclasses import dataclass


@dataclass
class FormCoefficients:
    cb: float   # Block coefficient
    cm: float   # Midship section coefficient
    cp: float   # Prismatic coefficient (volume/(Am*Lpp))
    cw: float   # Waterplane coefficient
    cp_consistency_flag: bool  # True if |Cp - Cb/Cm| exceeds tolerance


def compute_coefficients(
    volume: float,
    am: float,
    aw: float,
    bwl: float,
    draft: float,
    lpp: float,
    tolerance: float = 0.02,
) -> FormCoefficients:
    cb = volume / (lpp * bwl * draft) if (lpp * bwl * draft) > 0 else 0.0
    cm = am / (bwl * draft) if (bwl * draft) > 0 else 0.0
    cp = volume / (am * lpp) if (am * lpp) > 0 else 0.0
    cw = aw / (lpp * bwl) if (lpp * bwl) > 0 else 0.0

    cp_from_ratio = (cb / cm) if cm > 0 else 0.0
    flag = abs(cp - cp_from_ratio) > tolerance

    return FormCoefficients(cb=cb, cm=cm, cp=cp, cw=cw, cp_consistency_flag=flag)
