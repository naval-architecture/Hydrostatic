from pydantic import BaseModel


class BoundingBox(BaseModel):
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float


class UploadResponse(BaseModel):
    hull_id: str
    is_watertight: bool
    vertex_count: int
    face_count: int
    bounding_box: BoundingBox
    warnings: list[str] = []


class HydrostaticResultSchema(BaseModel):
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


class CalculateResponse(BaseModel):
    hull_id: str
    density: float
    lpp: float
    results: list[HydrostaticResultSchema]
    design_draft_result: HydrostaticResultSchema | None = None
    warnings: list[str] = []
