"""
Plane-slicing utilities for hydrostatic calculation.

Core design decision (see project spec, section 3.2):
We slice WITHOUT capping first to preserve the true wetted hull surface
(needed for WSA), then cap the waterplane hole SEPARATELY to produce a
watertight solid for volume/centroid integration. Capping too early would
corrupt WSA; skipping it breaks trimesh's divergence-theorem volume calc,
which requires a closed mesh.

IMPORTANT -- capping implementation note:
trimesh.Trimesh.fill_holes() ONLY patches single-triangle or single-quad
holes (see trimesh.repair.fill_holes source). A real waterplane cut is an
arbitrary n-gon (and for hulls with a knuckle/chine, possibly a non-convex
one, or multiple disjoint loops for a multi-hull), so fill_holes() silently
no-ops on it -- this was caught by tests/test_hydrostatics.py, which failed
with a "not watertight" error on a simple box-barge fixture. Instead we
explicitly triangulate the cut polygon (via the section's own boundary,
which correctly handles multiple/non-convex loops through Shapely) and
stitch the resulting cap faces onto the open mesh ourselves.
"""
import trimesh
import numpy as np
from trimesh.creation import triangulate_polygon
from dataclasses import dataclass


@dataclass
class SlicedHull:
    """Result of slicing a hull at a given draft."""
    submerged_open: trimesh.Trimesh | None    # wetted surface only, no cap -> WSA
    submerged_capped: trimesh.Trimesh | None  # watertight solid -> Volume, LCB, VCB
    is_valid: bool                             # False if draft is below keel (no volume)


def _build_cap(hull: trimesh.Trimesh, draft: float) -> trimesh.Trimesh | None:
    """
    Builds the waterplane cap as its own small mesh by triangulating the cut
    cross-section polygon(s). Sections the ORIGINAL hull (not the already-cut
    open mesh) -- sectioning exactly along the boundary of an already-cut
    mesh finds no plane-crossing edges and returns None, since the geometry
    ends precisely at that plane. Returns None if no valid section exists at
    this draft (e.g. draft exactly at a single point of the hull).
    """
    section = hull.section(
        plane_origin=[0.0, 0.0, draft],
        plane_normal=[0.0, 0.0, 1.0],
    )
    if section is None:
        return None

    section_2d, to_3d = section.to_planar()
    if len(section_2d.polygons_closed) == 0:
        return None

    all_verts, all_faces = [], []
    offset = 0
    for poly in section_2d.polygons_closed:
        v2d, f = triangulate_polygon(poly, engine="earcut")
        if len(v2d) == 0:
            continue
        v3d_local = np.column_stack([v2d, np.zeros(len(v2d))])
        v3d = trimesh.transform_points(v3d_local, to_3d)
        all_verts.append(v3d)
        all_faces.append(f + offset)
        offset += len(v2d)

    if not all_faces:
        return None

    return trimesh.Trimesh(
        vertices=np.vstack(all_verts),
        faces=np.vstack(all_faces),
        process=False,
    )


def slice_at_draft(hull: trimesh.Trimesh, draft: float) -> SlicedHull:
    """
    Slice the hull at Z = draft (Baseline is Z=0, per MVP assumption), keeping
    the submerged portion (Z <= draft).

    Returns a SlicedHull with both the open (uncapped) and capped versions.
    If the draft is at or below the keel, submerged_* will be None and
    is_valid=False.
    """
    plane_origin = [0.0, 0.0, draft]
    plane_normal = [0.0, 0.0, -1.0]  # keep the half-space where z <= draft

    submerged_open = hull.slice_plane(
        plane_origin=plane_origin,
        plane_normal=plane_normal,
        cap=False,
    )

    if submerged_open is None or len(submerged_open.faces) == 0:
        return SlicedHull(submerged_open=None, submerged_capped=None, is_valid=False)

    submerged_open.merge_vertices()

    # If the draft is at or beyond the hull's full height, slice_plane may
    # return the entire hull already closed (nothing above the plane to cut
    # away) -- no waterplane cut boundary exists, so no cap is needed at all.
    if submerged_open.is_watertight:
        return SlicedHull(
            submerged_open=submerged_open,
            submerged_capped=submerged_open,
            is_valid=True,
        )

    cap = _build_cap(hull, draft)
    if cap is None:
        return SlicedHull(submerged_open=submerged_open, submerged_capped=None, is_valid=False)

    combined = trimesh.util.concatenate([submerged_open, cap])
    combined.merge_vertices()
    combined.process()

    # Cap triangulation winding isn't guaranteed to match the solid's
    # outward-normal convention -- fix_normals resolves consistent outward
    # orientation across the whole combined solid, which both makes
    # is_watertight reliable and guarantees a positive-signed volume.
    if not combined.is_winding_consistent or combined.volume < 0:
        trimesh.repair.fix_normals(combined)

    submerged_capped = combined

    return SlicedHull(
        submerged_open=submerged_open,
        submerged_capped=submerged_capped,
        is_valid=True,
    )
