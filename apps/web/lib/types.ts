// Mirrors apps/api/app/schemas/{requests,responses}.py exactly.
// Keep these in sync manually for the MVP; consider a codegen step
// (e.g. openapi-typescript against FastAPI's /openapi.json) once the
// schema stabilizes.

export interface BoundingBox {
  x_min: number; x_max: number;
  y_min: number; y_max: number;
  z_min: number; z_max: number;
}

export interface UploadResponse {
  hull_id: string;
  is_watertight: boolean;
  vertex_count: number;
  face_count: number;
  bounding_box: BoundingBox;
  warnings: string[];
}

export interface ReferencePoints {
  baseline_z: number;
  ap_x: number;
  fp_x: number;
  midship_x: number;
}

export interface DraftParams {
  initial_draft: number;
  final_draft: number;
  increment: number;
  design_draft?: number | null;
}

export interface CalculateRequest {
  hull_id: string;
  reference_points: ReferencePoints;
  draft_params: DraftParams;
  water_density: number;
}

export interface HydrostaticResult {
  draft: number;
  volume: number;
  displacement: number;
  lcb: number;
  vcb: number;
  tcb: number;
  lcf: number;
  tcf: number;
  aw: number;
  wsa: number;
  bwl: number;
  am: number;
  cb: number;
  cm: number;
  cp: number;
  cw: number;
  cp_consistency_flag: boolean;
}

export interface CalculateResponse {
  hull_id: string;
  density: number;
  lpp: number;
  results: HydrostaticResult[];
  design_draft_result: HydrostaticResult | null;
  warnings: string[];
}

export const WATER_DENSITY = {
  FRESHWATER: 1.000,
  SEAWATER: 1.025,
} as const;
