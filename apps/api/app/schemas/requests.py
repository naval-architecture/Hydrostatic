from pydantic import BaseModel, Field


class ReferencePoints(BaseModel):
    baseline_z: float = Field(0.0, description="Z of Baseline. MVP assumes this is always 0 (mesh Z=0 = Baseline).")
    ap_x: float = Field(..., description="X location of Aft Perpendicular")
    fp_x: float = Field(..., description="X location of Forward Perpendicular")
    midship_x: float = Field(..., description="X location of Midship")


class DraftParams(BaseModel):
    initial_draft: float = Field(..., gt=0)
    final_draft: float = Field(..., gt=0)
    increment: float = Field(..., gt=0)
    design_draft: float | None = Field(None, description="Optional single draft to also compute explicitly")


class CalculateRequest(BaseModel):
    hull_id: str
    reference_points: ReferencePoints
    draft_params: DraftParams
    water_density: float = Field(1.025, description="t/m3. Freshwater=1.000, Seawater=1.025")
