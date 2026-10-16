# CMS Quality Intelligence

CMS Quality Intelligence is an evidence-grounded web application for tracking
changes to CMS quality-measure requirements. The product scope and delivery
sequence are defined in `docs/product-spec.md`, `docs/plan.md`, and
`docs/tasks.md`.

The application is being built as a small modular monolith:

- React, TypeScript, Vite, TanStack Router, and TanStack Query for the frontend
- FastAPI and Pydantic for the API, with Python dependencies managed by `uv`
- PostgreSQL for persistent, versioned records in later checkpoints
- `openapi.yaml` as the frontend/backend contract

## Current status

Checkpoint A provides runnable frontend and backend foundations, smoke tests,
and an initial read-only M1 API contract. Checkpoint B adds the Lovable-derived
dashboard and measure-detail experience at `/` and `/measures/:measureId`, with
responsive editorial layouts and typed client-side interactions.

Until Checkpoint C connects the frontend to the FastAPI contract, these screens
read only from the clearly isolated `frontend/src/features/measures/demo/`
adapter and fictional fixtures. The prototype records are not verified CMS data
and must not be treated or seeded as production records.

## Frontend

```sh
cd frontend
npm install
npm run dev
```

The development server defaults to `http://localhost:5173`.

The current prototype routes are:

- `/` — dashboard, change ledger, news, search, and measure filters
- `/measures/:measureId` — comparison, evidence, overview, AI-impact, and review-history tabs

Frontend checks:

```sh
npm test
npm run lint
npm run build
```

## Backend

```sh
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

The API defaults to `http://localhost:8000`; its health endpoint is
`GET /health`.

Backend checks:

```sh
uv run pytest
uv run ruff check .
```

No patient-level data or PHI belongs in this repository. CMS facts must be
source-backed and admin-verified before being exposed as verified data.
