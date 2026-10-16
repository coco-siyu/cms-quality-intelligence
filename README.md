# CMS Quality Intelligence

CMS Quality Intelligence is an evidence-grounded web application for tracking
changes to CMS quality-measure requirements. The product scope and delivery
sequence are defined in `docs/product-spec.md`, `docs/plan.md`, and
`docs/tasks.md`.

The application is being built as a small modular monolith:

- React, TypeScript, Vite, TanStack Router, and TanStack Query for the frontend
- FastAPI and Pydantic for the API, with Python dependencies managed by `uv`
- PostgreSQL for persistent, versioned measure and evidence records
- `openapi.yaml` as the frontend/backend contract

## Current status

Checkpoints A and B provide the runnable application foundation and the
Lovable-derived editorial interface. Checkpoint C1 adds PostgreSQL persistence,
Alembic migrations, the M1 public measure endpoints, and typed frontend API
queries.

The Measure Explorer and API-mode measure detail pages now read from FastAPI.
The Dashboard comparison ledger, What's New feed, and AI Impact prototype remain
M2-only demo experiences and are visibly labelled fictional. No authoritative
CMS measure inventory has been loaded, so M1 is not complete and the demo seed
must not be represented as CMS guidance.

See `docs/checkpoint-c1.md` for schema decisions, scope boundaries, and the
verified local workflow.

## Frontend

```sh
cd frontend
npm ci
npm run dev
```

The development server defaults to `http://localhost:5173`.

The current prototype routes are:

- `/` — introduction, comparison ledger, and linked summary metrics
- `/measures` — API-backed public directory by default; explicit demo mode is available
- `/measures/:measureId` — API-backed overview, versions, evidence, and source status
- `/whats-new` — dedicated fictional update feed

Frontend checks:

```sh
npm test
npm run lint
npm run build
```

Use `VITE_DATA_MODE=demo` only when intentionally reviewing the clearly labelled
fictional Checkpoint B fixtures. API mode is the default and never silently
falls back to those fixtures after a request failure.

## Local database and backend

```sh
cp .env.example .env
docker compose up -d postgres
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

The API defaults to `http://localhost:8000`. Public routes are `GET /health`,
`GET /api/performance-years`, `GET /api/measures`,
`GET /api/measures/{measure_id}`, and
`GET /api/measures/{measure_id}/versions`.

To load the two explicitly fictional records into the local database, opt in
for that command only. It refuses database names that do not contain `demo`:

```sh
cd backend
CMSQI_ALLOW_DEMO_SEED=true uv run python -m app.commands.seed_demo
CMSQI_ALLOW_DEMO_SEED=true uv run python -m app.commands.seed_demo --reset
```

Backend checks:

```sh
uv run pytest
uv run ruff check .
```

Stop the database without deleting its volume with `docker compose stop`. Use
`docker compose down --volumes` only when intentionally discarding the local
demo database.

No patient-level data or PHI belongs in this repository. CMS facts must be
source-backed and admin-verified before being exposed as verified data.
