"""
Section-based geometric helpers: waterplane properties and transverse
(midship) section area. Kept separate from volumetric calcs (core/slicer.py,
core/hydrostatics.py) because these operate on 2D planar cross-sections
rather than 3D solids.
"""
import trimesh
import numpy as np
from dataclasses import dataclass


@dataclass
class WaterplaneSection:
    area: float          # Aw
    lcf: float            # X-coordinate of waterplane centroid
    tcf: float            # Y-coordinate of waterplane centroid (should be ~0 if symmetric)
    bwl: float            # max beam at this waterline


def get_waterplane_section(hull: trimesh.Trimesh, draft: float) -> WaterplaneSection | None:
    """
    Cross-sections the ORIGINAL (unsliced) hull surface at Z = draft to get
    the waterplane outline, then computes area, centroid (LCF/TCF), and
    beam (Bwl) from it.

    Using the original hull (not the sliced/capped submerged solid) avoids
    any dependency on cap-triangulation artifacts.
    """
    section = hull.section(
        plane_origin=[0.0, 0.0, draft],
        plane_normal=[0.0, 0.0, 1.0],
    )
    if section is None:
        return None

    section_2d, to_3d = section.to_planar()

    if section_2d.area <= 0:
        return None

    aw = section_2d.area

    centroid_2d = section_2d.centroid  # (cx, cy) in the section's local 2D frame
    centroid_3d = trimesh.transform_points(
        np.array([[centroid_2d[0], centroid_2d[1], 0.0]]), to_3d
    )[0]

    # Bounding box in the section's local 2D frame. NOTE: local axes are not
    # guaranteed to align with world X/Y for an arbitrary cutting plane, but
    # since our plane_normal is always [0,0,1] (a pure Z-plane), trimesh's
    # to_planar() aligns local (u, v) with world (X, Y) directly — verified
    # against a known box-barge fixture in tests/test_hydrostatics.py.
    bounds_2d = section_2d.bounds  # [[u_min, v_min], [u_max, v_max]]
    bwl = bounds_2d[1][1] - bounds_2d[0][1]

    return WaterplaneSection(
        area=aw,
        lcf=float(centroid_3d[0]),
        tcf=float(centroid_3d[1]),
        bwl=float(bwl),
    )


def get_midship_section_area(submerged_capped: trimesh.Trimesh, x_midship: float) -> float:
    """
    Cross-sections the already-capped, already-draft-limited submerged solid
    at X = x_midship. Because the input is already bounded above by the
    waterline (it's the capped submerged solid, not the raw hull), the
    resulting section is automatically the correct transverse area Am —
    no separate draft clipping is required.
    """
    section = submerged_capped.section(
        plane_origin=[x_midship, 0.0, 0.0],
        plane_normal=[1.0, 0.0, 0.0],
    )
    if section is None:
        return 0.0

    section_2d, _ = section.to_planar()
    return float(section_2d.area)
