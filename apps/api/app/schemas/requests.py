from pydantic import BaseModel, Field


class DraftParams(BaseModel):
    initial_draft: float = Field(..., ge=0)
    final_draft: float = Field(..., gt=0)
    increment: float = Field(..., gt=0)
    design_draft: float | None = Field(None, description="Optional single draft to also compute explicitly")


class CalculateRequest(BaseModel):
    hull_id: str
    draft_params: DraftParams
    water_density: float = Field(1.025, description="t/m3. Freshwater=1.000, Seawater=1.025")
