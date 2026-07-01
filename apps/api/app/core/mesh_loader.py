"""
Loads a Rhino .3dm file into a watertight trimesh.Trimesh hull surface.

MVP scope (confirmed):
- FULL HULL meshes only. No half-hull mirroring is performed.
  If a half-hull (starboard-only) file is ever uploaded, this module will
  NOT detect or correct it — the resulting mesh will not be watertight and
  downstream volume/centroid calculations will raise a ValueError.
- Baseline is assumed to be exactly Z=0 in the source file. No offset
  correction is applied here or anywhere downstream.
"""
import rhino3dm
import trimesh
import numpy as np


class MeshLoadError(Exception):
    """Raised when a .3dm file cannot be parsed into a usable hull mesh."""
    pass


def load_hull_mesh(filepath: str) -> trimesh.Trimesh:
    """
    Parse a .3dm file and return a single merged trimesh.Trimesh representing
    the hull surface (up to main deck), assumed to be a full-hull, watertight
    (or near-watertight) mesh.

    Raises MeshLoadError if no mesh/surface geometry is found in the file.
    """
    model = rhino3dm.File3dm.Read(filepath)
    if model is None:
        raise MeshLoadError(f"Could not read .3dm file at {filepath}")

    all_vertices = []
    all_faces = []
    vertex_offset = 0

    for obj in model.Objects:
        geom = obj.Geometry
        mesh = None

        if isinstance(geom, rhino3dm.Mesh):
            mesh = geom
        elif isinstance(geom, rhino3dm.Brep):
            meshes = rhino3dm.Mesh.CreateFromBrep(geom, rhino3dm.MeshingParameters.Default)
            if meshes:
                # Merge all per-face meshes of the Brep into one
                merged = meshes[0]
                for m in meshes[1:]:
                    merged.Append(m)
                mesh = merged
        elif isinstance(geom, rhino3dm.Surface):
            brep = geom.ToBrep()
            meshes = rhino3dm.Mesh.CreateFromBrep(brep, rhino3dm.MeshingParameters.Default)
            if meshes:
                merged = meshes[0]
                for m in meshes[1:]:
                    merged.Append(m)
                mesh = merged

        if mesh is None or mesh.Vertices.Count == 0:
            continue

        verts = np.array([[v.X, v.Y, v.Z] for v in mesh.Vertices], dtype=np.float64)
        faces = np.array([[f.A, f.B, f.C] for f in mesh.Faces], dtype=np.int64) + vertex_offset

        all_vertices.append(verts)
        all_faces.append(faces)
        vertex_offset += len(verts)

    if not all_vertices:
        raise MeshLoadError(
            "No Mesh, Brep, or Surface geometry found in the .3dm file. "
            "Ensure the hull is exported as a joined polysurface or mesh."
        )

    vertices = np.vstack(all_vertices)
    faces = np.vstack(all_faces)

    hull = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
    hull.merge_vertices()

    return hull


def validate_and_repair(hull: trimesh.Trimesh) -> tuple[trimesh.Trimesh, list[str]]:
    """
    Checks watertightness and attempts a light repair via hole-filling.
    Returns (possibly-repaired mesh, list of warning strings for the user).

    Does NOT attempt half-hull mirroring or centerline detection — per MVP
    scope, non-watertight full-hull meshes are a data quality issue to flag,
    not silently work around.
    """
    warnings: list[str] = []

    if not hull.is_watertight:
        # trimesh.fill_holes() only patches single triangle/quad holes; it's
        # sufficient here for small mesh-export gaps (missing individual
        # faces) but will NOT close a large opening like an un-decked hull
        # or a half-hull section plane. Those are flagged, not silently
        # "fixed" with a wrong result.
        hull.fill_holes()
        hull.process()
        if hull.is_watertight:
            warnings.append(
                "Source mesh had small gaps; automatically repaired via hole-filling."
            )
        else:
            warnings.append(
                "WARNING: mesh is not watertight after repair attempt. "
                "Volume and centroid results may be inaccurate. Check for a "
                "half-hull export (mirroring is not supported in this MVP), "
                "a missing main-deck cap, or open transom edges."
            )

    if hull.volume < 0:
        # Inverted normals — flip so outward-facing normals give positive volume
        hull.invert()
        warnings.append("Mesh face winding was inverted; normals were corrected.")

    return hull, warnings
