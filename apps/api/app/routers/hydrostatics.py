"""
API routes for hull upload and hydrostatic calculation.

MVP hull cache: a simple in-process dict keyed by hull_id (UUID4). This is
fine for local/single-worker dev and on-site intranet deployment at small
scale. If you move to multi-worker/multi-replica deployment, swap this for
Redis or disk-backed storage keyed the same way — the router logic doesn't
need to change, only HULL_CACHE's implementation.
"""
import os
import uuid
import shutil

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import settings
from app.core.mesh_loader import load_hull_mesh, validate_and_repair, MeshLoadError
from app.core.hydrostatics import calculate_hydrostatics_range, calculate_hydrostatics_at_draft
from app.schemas.requests import CalculateRequest
from app.schemas.responses import (
    UploadResponse, BoundingBox, CalculateResponse, HydrostaticResultSchema,
)

router = APIRouter()

# hull_id (str) -> trimesh.Trimesh
HULL_CACHE: dict = {}


@router.post("/hull/upload", response_model=UploadResponse)
async def upload_hull(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".3dm"):
        raise HTTPException(status_code=400, detail="Only .3dm files are supported.")

    tmp_path = os.path.join(settings.upload_dir, f"{uuid.uuid4()}.3dm")
    try:
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        hull = load_hull_mesh(tmp_path)
        hull, warnings = validate_and_repair(hull)

    except MeshLoadError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    hull_id = str(uuid.uuid4())
    HULL_CACHE[hull_id] = hull

    bounds = hull.bounds  # [[x_min,y_min,z_min],[x_max,y_max,z_max]]

    return UploadResponse(
        hull_id=hull_id,
        is_watertight=hull.is_watertight,
        vertex_count=len(hull.vertices),
        face_count=len(hull.faces),
        bounding_box=BoundingBox(
            x_min=float(bounds[0][0]), x_max=float(bounds[1][0]),
            y_min=float(bounds[0][1]), y_max=float(bounds[1][1]),
            z_min=float(bounds[0][2]), z_max=float(bounds[1][2]),
        ),
        warnings=warnings,
    )


@router.post("/hydrostatics/calculate", response_model=CalculateResponse)
async def calculate(req: CalculateRequest):
    hull = HULL_CACHE.get(req.hull_id)
    if hull is None:
        raise HTTPException(
            status_code=404,
            detail="hull_id not found. Re-upload the .3dm file (server may have restarted).",
        )

    dp = req.draft_params
    warnings: list[str] = []

    # AP/FP/Midship are derived from the hull's own X bounds rather than
    # user input — the model's reference axis convention already places
    # AP and FP at the hull's extreme X coordinates.
    bounds = hull.bounds
    ap_x = float(bounds[0][0])
    fp_x = float(bounds[1][0])
    midship_x = (ap_x + fp_x) / 2

    try:
        results = calculate_hydrostatics_range(
            hull=hull,
            initial_draft=dp.initial_draft,
            final_draft=dp.final_draft,
            increment=dp.increment,
            ap_x=ap_x,
            fp_x=fp_x,
            midship_x=midship_x,
            density=req.water_density,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not results:
        raise HTTPException(
            status_code=422,
            detail="No valid hydrostatic results in the given draft range — "
                   "check that drafts fall within the hull's Z bounds.",
        )

    design_result = None
    if dp.design_draft is not None:
        dr = calculate_hydrostatics_at_draft(
            hull, dp.design_draft, ap_x, fp_x, midship_x, req.water_density
        )
        if dr is not None:
            design_result = HydrostaticResultSchema(**dr.to_dict())
        else:
            warnings.append(f"design_draft={dp.design_draft} produced no valid submerged volume.")

    lpp = abs(fp_x - ap_x)

    return CalculateResponse(
        hull_id=req.hull_id,
        density=req.water_density,
        lpp=lpp,
        results=[HydrostaticResultSchema(**r.to_dict()) for r in results],
        design_draft_result=design_result,
        warnings=warnings,
    )
