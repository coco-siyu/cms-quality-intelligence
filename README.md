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
queries. Checkpoints C2.1–C2.5 add the reviewed PY2025–PY2026 source inventory,
immutable retrieval manifest, exact roster evidence locators, explicit
collection variants, and a guarded private review workflow. The database can
hold 32 collection-specific variants, 352 source-backed field candidates, and
append-only reviewer decisions, but all current detailed-field decisions remain
pending and non-public.

The Measure Explorer and API-mode measure detail pages now read from FastAPI.
The Dashboard comparison ledger, What's New feed, and AI Impact prototype remain
M2-only demo experiences and are visibly labelled fictional. The reviewed CMS
roster may be loaded locally only as private draft data; it is intentionally
excluded from public API responses. Detailed specification fields and formal
publication approval remain incomplete, so M1 is not complete.

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

To load the reviewed PY2025–PY2026 roster, collection variants, and field
candidates as idempotent private draft records, use the separate guarded
command. It refuses database names that do not contain `demo` or `dev` and
never changes records to published:

```sh
CMSQI_ALLOW_VERIFIED_DRAFT_SEED=true uv run python -m app.commands.seed_verified
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
