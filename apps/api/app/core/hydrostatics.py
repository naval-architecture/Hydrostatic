"""
Per-draft and draft-range hydrostatic calculation pipeline. This is the
orchestration layer that ties together slicing (slicer.py), section
geometry (utils/geometry.py), and form coefficients (coefficients.py).

MVP assumptions baked in throughout:
- Baseline = Z=0 in the source mesh (no offset correction).
- Full hull only (no mirroring).
- Monohull formulas for Cb/Cm/Cp/Cw.
"""
import numpy as np
import trimesh
from dataclasses import dataclass, asdict

from app.core.slicer import slice_at_draft
from app.core.coefficients import compute_coefficients
from app.utils.geometry import get_waterplane_section, get_midship_section_area


@dataclass
class HydrostaticResult:
    draft: float
    volume: float
    displacement: float
    lcb: float
    vcb: float
    tcb: float
    lcf: float
    tcf: float
    aw: float
    wsa: float
    bwl: float
    am: float
    cb: float
    cm: float
    cp: float
    cw: float
    cp_consistency_flag: bool

    def to_dict(self) -> dict:
        return asdict(self)


def calculate_hydrostatics_at_draft(
    hull: trimesh.Trimesh,
    draft: float,
    ap_x: float,
    fp_x: float,
    midship_x: float,
    density: float,
) -> HydrostaticResult | None:
    """
    Computes the full hydrostatic property set at a single draft.
    Returns None if the draft produces no submerged volume (e.g. below keel),
    or if the draft is at/beyond the hull's full molded depth (no waterplane
    intersection exists in that case -- Aw/LCF/Bwl are undefined, and this
    represents an invalid loading condition rather than a valid one to
    silently approximate).
    """
    sliced = slice_at_draft(hull, draft)
    if not sliced.is_valid:
        return None

    if not sliced.submerged_capped.is_watertight:
        raise ValueError(
            f"Capped submerged mesh is not watertight at draft={draft}. "
            "Check source mesh integrity (see /hull/upload warnings)."
        )

    volume = float(sliced.submerged_capped.volume)
    if volume <= 0:
        return None

    cob = sliced.submerged_capped.center_mass  # centroid of volume = center of buoyancy
    wsa = float(sliced.submerged_open.area)

    wp = get_waterplane_section(hull, draft)
    if wp is None:
        return None

    lpp = abs(fp_x - ap_x)
    am = get_midship_section_area(sliced.submerged_capped, midship_x)

    coeffs = compute_coefficients(
        volume=volume, am=am, aw=wp.area, bwl=wp.bwl, draft=draft, lpp=lpp
    )

    displacement = volume * density

    return HydrostaticResult(
        draft=draft,
        volume=volume,
        displacement=displacement,
        lcb=float(cob[0]),
        vcb=float(cob[2]),
        tcb=float(cob[1]),
        lcf=wp.lcf,
        tcf=wp.tcf,
        aw=wp.area,
        wsa=wsa,
        bwl=wp.bwl,
        am=am,
        cb=coeffs.cb,
        cm=coeffs.cm,
        cp=coeffs.cp,
        cw=coeffs.cw,
        cp_consistency_flag=coeffs.cp_consistency_flag,
    )


def calculate_hydrostatics_range(
    hull: trimesh.Trimesh,
    initial_draft: float,
    final_draft: float,
    increment: float,
    ap_x: float,
    fp_x: float,
    midship_x: float,
    density: float,
) -> list[HydrostaticResult]:
    """
    Runs calculate_hydrostatics_at_draft across a draft range
    [initial_draft, final_draft] stepped by `increment` (inclusive of the
    final draft if it lands on the grid, via a small epsilon tolerance).
    Drafts with no valid submerged volume are silently skipped (e.g. a
    requested initial_draft below the keel).
    """
    if increment <= 0:
        raise ValueError("increment must be > 0")
    if final_draft < initial_draft:
        raise ValueError("final_draft must be >= initial_draft")

    n_steps = int(round((final_draft - initial_draft) / increment)) + 1
    drafts = [initial_draft + i * increment for i in range(n_steps)]

    results = []
    for draft in drafts:
        result = calculate_hydrostatics_at_draft(
            hull, draft, ap_x, fp_x, midship_x, density
        )
        if result is not None:
            results.append(result)

    return results
