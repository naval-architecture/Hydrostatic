# Hydrostatic Curve Calculator — Architecture & Math Spec

> **Implementation status (2026-07-01):** Backend core math implemented and
> regression-tested. See `IMPLEMENTATION NOTES` at the end of this document
> for confirmed MVP scope and one correction made to the original plan during
> implementation (mesh capping approach).

## 0. Conventions (confirm before implementation)

| Axis | Convention |
|---|---|
| X | Positive forward, AP → FP |
| Y | Positive to starboard/port, centerline at Y = 0 |
| Z | Positive up from Baseline (Z=0) |
| Units | Meters (length), tonnes (mass), t/m³ (density) |
| Hull model | Toggle: full hull OR half-hull mirrored at Y=0 |

---

## 1. Monorepo Structure

```
naval-arch-suite/
├── docker-compose.yml
├── docker-compose.override.yml        # local dev overrides (hot reload)
├── .env.example
├── apps/
│   ├── web/                           # Next.js frontend
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── hydrostatics/
│   │   │       ├── page.tsx           # main dashboard route
│   │   │       └── components/
│   │   │           ├── InputPanel.tsx
│   │   │           ├── FileUpload.tsx
│   │   │           ├── ReferencePointsForm.tsx
│   │   │           ├── DraftRangeForm.tsx
│   │   │           ├── HydrostaticCurves.tsx   # Recharts panel
│   │   │           ├── ResultsTable.tsx        # shadcn DataTable
│   │   │           └── HullPreview3D.tsx       # optional: three.js viewer
│   │   ├── lib/
│   │   │   ├── api-client.ts          # typed fetch wrapper
│   │   │   ├── store.ts               # Zustand store
│   │   │   └── types.ts               # shared TS types (mirror Pydantic)
│   │   ├── components/ui/             # shadcn primitives
│   │   ├── package.json
│   │   ├── tailwind.config.ts
│   │   └── Dockerfile
│   │
│   └── api/                           # FastAPI backend
│       ├── app/
│       │   ├── main.py
│       │   ├── config.py
│       │   ├── routers/
│       │   │   └── hydrostatics.py
│       │   ├── schemas/
│       │   │   ├── requests.py        # Pydantic models
│       │   │   └── responses.py
│       │   ├── core/
│       │   │   ├── mesh_loader.py     # rhino3dm -> trimesh conversion
│       │   │   ├── slicer.py          # plane slicing + capping
│       │   │   ├── hydrostatics.py    # per-draft calc engine
│       │   │   └── coefficients.py    # Cb, Cp, Cm, Cw
│       │   └── utils/
│       │       └── geometry.py        # section area/centroid helpers
│       ├── tests/
│       │   ├── fixtures/              # sample .3dm test hulls
│       │   └── test_hydrostatics.py
│       ├── requirements.txt
│       └── Dockerfile
│
├── packages/
│   └── shared-types/                  # (optional, if you outgrow manual TS mirroring)
│
└── docs/
    └── hydrostatic-calculator-spec.md # this file
```

**Why this shape:** `apps/` isolates deployable services so `docker-compose.yml` maps 1:1 to services. `core/` in the API is pure computation with no FastAPI/HTTP awareness — makes it independently unit-testable against known hull forms (e.g. a Wigley hull or a simple box barge, where you can hand-derive Cb, LCB, VCB and assert against the algorithm). Always build that regression test fixture first — it's your ground truth as you add more modules (stability, GZ curves, etc.) later.

---

## 2. UI Wireframe & State Management

### Layout
```
┌─────────────┬──────────────────────────────────────────┐
│             │  [Hydrostatic Curves]  [Results Table]    │
│  Left Panel │ ┌────────────────────────────────────────┐│
│  (sticky,   │ │                                        ││
│   ~320px)   │ │   Recharts: multiple line series        ││
│             │ │   X-axis = property value                ││
│  • Upload   │ │   Y-axis = Draft (T)                      ││
│    .3dm     │ │   (toggle series visibility via legend)   ││
│  • Ref Pts  │ │                                        ││
│    AP/FP/   │ └────────────────────────────────────────┘│
│    MS/BL    │                                            │
│  • Draft    │  (Results Table tab: shadcn DataTable,     │
│    range    │   sortable, exportable to CSV)             │
│  • Density  │                                            │
│  • [Run]    │                                            │
└─────────────┴──────────────────────────────────────────┘
```
Traditional NA hydrostatic curve sheets plot draft on the Y-axis (vertical, mirroring the waterline rising up the hull) with each property on its own X scale — keep that orientation, it's what a naval architect expects at a glance, rather than defaulting to Recharts' natural X=independent-variable layout.

### State Management
- **Zustand** for global client state (uploaded file ref, input params, calculation results, loading/error state). Overkill to reach for Redux here; Zustand's small footprint fits a single-module dashboard and scales fine when you add more modules as separate slices.
- **TanStack Query** (`@tanstack/react-query`) wrapping the actual `/calculate` POST — gives you request dedup, retry, and cache-by-input-hash for free (useful since re-running the same draft range shouldn't re-hit the backend).
- Flow:
  1. `FileUpload` → uploads `.3dm` to `/api/hull/upload` → backend returns a `hull_id` (parsed mesh cached server-side, e.g. Redis or temp disk, keyed by UUID) — **don't** re-upload/re-parse the mesh on every draft-range tweak.
  2. `InputPanel` state (ref points, draft range, density) lives in Zustand, validated with `zod` before submit.
  3. `[Run]` triggers a mutation to `/api/hydrostatics/calculate` with `{hull_id, ...params}`.
  4. Response populates both `HydrostaticCurves` and `ResultsTable` from the same normalized array in the store — single source of truth, two views.

---

## 3. Python Math Logic (core algorithm)

### 3.1 Mesh loading (`mesh_loader.py`)
```python
import rhino3dm
import trimesh
import numpy as np

def load_hull_mesh(filepath: str, is_half_model: bool = False) -> trimesh.Trimesh:
    model = rhino3dm.File3dm.Read(filepath)

    all_vertices, all_faces = [], []
    vertex_offset = 0

    for obj in model.Objects:
        geom = obj.Geometry
        # Rhino may store the hull as Mesh directly, or as a Brep/Surface
        # that needs meshing first.
        if isinstance(geom, rhino3dm.Mesh):
            mesh = geom
        elif isinstance(geom, (rhino3dm.Brep, rhino3dm.Surface)):
            mesh = rhino3dm.Mesh.CreateFromBrep(
                geom if isinstance(geom, rhino3dm.Brep) else geom.ToBrep(),
                rhino3dm.MeshingParameters.Default
            )[0]  # CreateFromBrep returns a list of meshes (one per face)
        else:
            continue

        verts = np.array([[v.X, v.Y, v.Z] for v in mesh.Vertices])
        faces = np.array([[f.A, f.B, f.C] for f in mesh.Faces]) + vertex_offset
        all_vertices.append(verts)
        all_faces.append(faces)
        vertex_offset += len(verts)

    vertices = np.vstack(all_vertices)
    faces = np.vstack(all_faces)
    hull = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)

    if is_half_model:
        # Mirror across centerline (Y=0) and merge into a watertight full hull
        mirrored = hull.copy()
        mirrored.vertices[:, 1] *= -1
        mirrored.invert()  # flip face winding so normals stay outward
        hull = trimesh.util.concatenate([hull, mirrored])
        hull.merge_vertices()
        hull.process()

    if not hull.is_watertight:
        hull.fill_holes()   # attempt auto-repair; flag to user if this fails

    return hull
```

### 3.2 Slicing + capping (`slicer.py`)

The critical trick: **slice without capping first to get true wetted surface, then cap separately for the volume/centroid calc.** Capping fills the waterplane hole so trimesh's divergence-theorem volume/center_mass integrals are valid on a closed solid.

```python
import trimesh
import numpy as np

def slice_at_draft(hull: trimesh.Trimesh, draft: float):
    """
    Returns (submerged_open, submerged_capped) at the given draft (Z = draft).
    submerged_open: hull surface only, no waterplane cap -> use for WSA.
    submerged_capped: watertight solid -> use for Volume, LCB, VCB.
    """
    plane_origin = [0, 0, draft]
    plane_normal = [0, 0, -1]   # keep everything where z <= draft

    submerged_open = hull.slice_plane(
        plane_origin=plane_origin,
        plane_normal=plane_normal,
        cap=False
    )

    if submerged_open is None or len(submerged_open.faces) == 0:
        return None, None  # draft below keel — no submerged volume

    submerged_capped = submerged_open.copy()
    submerged_capped.fill_holes()   # caps the waterplane opening(s)
    submerged_capped.process()

    return submerged_open, submerged_capped
```

`fill_holes()` is doing real work here — it triangulates the boundary loop(s) left by the plane cut, which for a hull is the waterplane outline. Multi-hull forms (catamarans, SWATH) produce multiple boundary loops; `fill_holes` handles each independently, so this generalizes without extra branching.

### 3.3 Waterplane section (for Aw, LCF, Bwl)

Rather than deriving Aw/LCF from the capped mesh's cap faces (fragile — depends on triangulation), take an explicit planar cross-section:

```python
def get_waterplane_section(hull: trimesh.Trimesh, draft: float):
    section = hull.section(
        plane_origin=[0, 0, draft],
        plane_normal=[0, 0, 1]
    )
    if section is None:
        return None

    section_2d, to_3d = section.to_planar()  # to_3d: 4x4 transform back to world coords

    Aw = section_2d.area  # sum of all closed polygon areas (handles multi-hull)

    centroid_2d = section_2d.centroid  # (cx, cy) in the section's local 2D frame
    centroid_3d = trimesh.transform_points([[*centroid_2d, 0]], to_3d)[0]

    # Bounding box of the section gives waterline beam
    bounds_2d = section_2d.bounds  # [[minx, miny], [maxx, maxy]]
    Bwl = bounds_2d[1][1] - bounds_2d[0][1]  # careful: verify axis mapping after to_planar

    return {
        "area": Aw,
        "lcf": centroid_3d[0],   # X-coordinate = LCF
        "tcf": centroid_3d[1],   # Y-coordinate = TCF (should be ~0 if symmetric)
        "bwl": Bwl,
    }
```

> Implementation note for Claude Code: `to_planar()`'s local 2D axes are *not guaranteed* to align with world X/Y — verify by transforming a known point and adjusting the Bwl axis pick accordingly. Add this as a unit test against the box-barge fixture where Bwl is known exactly.

### 3.4 Volume, LCB, VCB

```python
def get_volumetric_properties(submerged_capped: trimesh.Trimesh):
    if not submerged_capped.is_watertight:
        raise ValueError("Capped mesh is not watertight — repair failed at this draft")

    volume = submerged_capped.volume          # via divergence theorem
    cob = submerged_capped.center_mass         # centroid of volume (uniform density)

    return {
        "volume": volume,
        "lcb": cob[0],
        "tcb": cob[1],
        "vcb": cob[2],
    }
```

`center_mass` in trimesh assumes uniform density across the solid, which is exactly what we want here — for a homogeneous "solid of displacement," centroid of volume *is* the center of buoyancy by definition. No mass properties beyond geometry are needed for this module.

### 3.5 Midship section (for Am, Cm)

```python
def get_midship_section_area(submerged_capped: trimesh.Trimesh, x_midship: float):
    section = submerged_capped.section(
        plane_origin=[x_midship, 0, 0],
        plane_normal=[1, 0, 0]
    )
    if section is None:
        return 0.0
    section_2d, _ = section.to_planar()
    return section_2d.area   # Am at the given draft
```

Slicing the **already-capped, already-draft-limited** solid means the resulting transverse section is automatically bounded above by the waterline — no separate draft clipping needed.

### 3.6 Full per-draft pipeline (`hydrostatics.py`)

```python
def calculate_hydrostatics_at_draft(
    hull: trimesh.Trimesh,
    draft: float,
    x_ap: float,
    x_fp: float,
    x_midship: float,
    density: float,
) -> dict | None:

    submerged_open, submerged_capped = slice_at_draft(hull, draft)
    if submerged_capped is None:
        return None  # above/below hull range

    vol_props = get_volumetric_properties(submerged_capped)
    wp = get_waterplane_section(hull, draft)
    if wp is None:
        return None

    WSA = submerged_open.area
    Am = get_midship_section_area(submerged_capped, x_midship)

    Lpp = abs(x_fp - x_ap)
    Bwl = wp["bwl"]
    T = draft  # relative to baseline; adjust if BL input != 0

    volume = vol_props["volume"]
    displacement = volume * density

    Cb = volume / (Lpp * Bwl * T) if (Lpp * Bwl * T) > 0 else 0
    Cm = Am / (Bwl * T) if (Bwl * T) > 0 else 0
    Cp = volume / (Am * Lpp) if (Am * Lpp) > 0 else 0   # = Cb / Cm, computed independently as a cross-check
    Cw = wp["area"] / (Lpp * Bwl) if (Lpp * Bwl) > 0 else 0

    return {
        "draft": draft,
        "volume": volume,
        "displacement": displacement,
        "lcb": vol_props["lcb"],
        "vcb": vol_props["vcb"],
        "lcf": wp["lcf"],
        "aw": wp["area"],
        "wsa": WSA,
        "bwl": Bwl,
        "am": Am,
        "cb": Cb,
        "cm": Cm,
        "cp": Cp,
        "cw": Cw,
    }
```

**Validation built in:** computing `Cp` independently from volume/Am/Lpp rather than as `Cb/Cm` gives you a cheap internal consistency check — if the two diverge meaningfully, something's off in the section extraction, and that's a useful debug signal to surface in the UI later (e.g. a small ⚠ badge on the results row).

---

## 4. API Contract

### `POST /api/hull/upload`
**Request:** `multipart/form-data`, field `file` = the `.3dm` file, field `is_half_model` = boolean.

**Response:**
```json
{
  "hull_id": "a1b2c3d4-...",
  "is_watertight": true,
  "vertex_count": 15234,
  "face_count": 30122,
  "bounding_box": {
    "x_min": -1.2, "x_max": 45.8,
    "y_min": -6.1, "y_max": 6.1,
    "z_min": -3.4, "z_max": 8.0
  },
  "warnings": []
}
```
`warnings` surfaces things like "hole-filling applied to repair small gaps" — don't silently auto-repair without telling the user their source mesh had defects.

### `POST /api/hydrostatics/calculate`
**Request:**
```json
{
  "hull_id": "a1b2c3d4-...",
  "reference_points": {
    "baseline_z": 0.0,
    "ap_x": 0.0,
    "fp_x": 42.0,
    "midship_x": 21.0
  },
  "draft_params": {
    "initial_draft": 0.5,
    "final_draft": 5.0,
    "increment": 0.25,
    "design_draft": 3.8
  },
  "water_density": 1.025
}
```

**Response:**
```json
{
  "hull_id": "a1b2c3d4-...",
  "density": 1.025,
  "lpp": 42.0,
  "results": [
    {
      "draft": 0.5,
      "volume": 120.4,
      "displacement": 123.41,
      "lcb": 20.1,
      "vcb": 0.31,
      "lcf": 19.8,
      "aw": 210.5,
      "wsa": 245.2,
      "bwl": 9.8,
      "am": 8.1,
      "cb": 0.612,
      "cm": 0.845,
      "cp": 0.724,
      "cw": 0.512
    }
  ],
  "design_draft_result": { "...": "same shape, computed at design_draft" },
  "warnings": []
}
```

Keeping `results` as a flat array of per-draft objects means the frontend can feed it *directly* into both Recharts (`dataKey="draft"` on the Y-axis, one `<Line>` per property) and the shadcn DataTable with zero reshaping — one fetch, one normalized shape, two views, as planned in §2.

---

## Open items to confirm before Claude Code build
1. Full-hull vs half-hull `.3dm` convention (assumed toggle, default half-hull).
2. Coordinate axis convention (assumed AP→FP = +X, up = +Z).
3. Baseline offset — is `baseline_z` always 0 in the model, or can the hull geometry sit at an arbitrary Z and baseline is a user-supplied offset? (Spec above treats `draft` as absolute Z; if baseline ≠ 0, subtract it before slicing.)
4. Multi-hull geometries (catamaran/trimaran) — confirmed working via `fill_holes()`'s multi-loop handling, but Cb/Cm/Cp formulas above assume monohull Lpp×Bwl×T; will need a "per-demihull" variant if you need that near-term.

---

## IMPLEMENTATION NOTES (added post-implementation)

### Confirmed MVP scope (2026-07-01)
1. **Full hull only.** Half-hull mirroring was designed but is NOT implemented.
   Uploading a half-hull (starboard-only) file will fail watertightness
   checks and produce a warning, not a silent wrong answer.
2. **Coordinate convention confirmed as specified:** X positive forward
   (AP=0 or arbitrary, FP > AP), Y positive to starboard/port (centerline
   Y=0), Z positive up, Baseline Z=0.
3. **Baseline offset:** confirmed NOT applied. `reference_points.baseline_z`
   is accepted in the API for future use but currently only triggers a
   warning if non-zero — it does not shift the calculation.
4. **Monohull only.** Cb/Cm/Cp/Cw use standard `Lpp × Bwl × T` throughout.

### Correction to the original capping approach

The original spec proposed `trimesh.Trimesh.fill_holes()` to close the
waterplane cut after slicing. **This does not work for real hull sections.**
`trimesh.repair.fill_holes()` (verified by reading its source, trimesh
4.4.9) only patches holes that are exactly a single triangle or a single
quad — it silently no-ops (returns `False`, adds zero faces) on any larger
or more complex polygon boundary, which is what every real waterplane cut
produces.

This was caught immediately by the box-barge regression test
(`tests/test_hydrostatics.py`): a simple rectangular hull sliced at
half-draft failed with "mesh is not watertight" because `fill_holes()`
silently failed to close an 8-edge boundary loop.

**Fix implemented in `app/core/slicer.py`:** instead of `fill_holes()`, the
waterplane cut polygon is obtained explicitly via
`hull.section(...).to_planar()` (which correctly handles non-convex
boundaries and multiple disjoint loops via Shapely under the hood), then
triangulated with `trimesh.creation.triangulate_polygon(..., engine="earcut")`
and stitched onto the open submerged mesh as a proper cap mesh, followed by
`trimesh.repair.fix_normals()` to guarantee consistent outward-normal
orientation (and therefore a correctly-signed volume).

This was validated two ways:
- Exact match against hand-derived values for a box barge (L=10, B=4, H=3
  at T=2): Volume=80.0, LCB=5.0, VCB=1.0, TCB=0.0, Aw=40.0, Bwl=4.0, Am=8.0,
  Cb=Cm=Cp=Cw=1.0 exactly.
- Exact match against hand-derived values for a V-bottom wedge hull (a
  genuinely non-trivial shape, not just the degenerate box case): Volume,
  Aw, Am, VCB, Cb, Cm, Cp, Cw, and Cw all matched analytical formulas
  exactly, including Cp=1.0 for a true prismatic (constant-section) shape.

A secondary edge case was also found and fixed: when a requested draft is
at or beyond the hull's full molded depth, `slice_plane` can return the
*entire* hull already closed (nothing above the plane to cut away), meaning
there is no cut boundary to cap at all. `slice_at_draft()` now checks
`submerged_open.is_watertight` first and skips capping entirely in that
case. Conversely, a draft that produces no intersection with the hull
surface at all (i.e., strictly above the hull) correctly returns `None` —
this is treated as an invalid loading condition (no waterplane exists),
not silently approximated as "fully submerged."

Additional dependency required beyond the original plan: `mapbox_earcut`
(polygon triangulation engine for `trimesh.creation.triangulate_polygon`;
trimesh has no default engine bundled).
