# Naval Architecture Suite

Scalable web-based naval architecture calculation tools. First module:
**Hydrostatic Curve Calculator** — pure hull-form hydrostatics from a
watertight `.3dm` mesh (Volume, Displacement, LCB, VCB, LCF, Aw, WSA, Cb,
Cm, Cp, Cw across a draft range).

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```
- Frontend: http://localhost:3000
- API: http://localhost:8000 (docs at http://localhost:8000/docs)

## Quick start (local, no Docker)

```bash
# Backend
cd apps/api
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd apps/web
npm install
npm run dev
```

## Running backend tests

```bash
cd apps/api
pytest tests/ -v
```

The core math (mesh slicing, capping, volume/centroid integration, form
coefficients) is regression-tested against a hand-derivable box-barge
fixture in `tests/test_hydrostatics.py` — run this after any change to
`app/core/`.

## MVP scope & assumptions (confirmed, see docs/hydrostatic-calculator-spec.md)

- **Full-hull meshes only.** No half-hull mirroring.
- **Baseline = mesh Z=0.** No baseline offset correction applied.
- **Monohull only.** Cb/Cm/Cp/Cw use standard Lpp × Bwl × T formulas.
- Coordinate convention: X positive forward (AP→FP), Y positive to
  starboard/port (centerline at Y=0), Z positive up from Baseline.

## Architecture

```
apps/api/    FastAPI backend — mesh parsing, slicing, hydrostatics math
apps/web/    Next.js frontend — engineering dashboard UI
docs/        Architecture and math specification
```

See `docs/hydrostatic-calculator-spec.md` for the full technical spec,
including the mathematical derivation of the slicing/capping approach.
