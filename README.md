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

The first M3 admin increment adds an environment-configured single-admin login,
signed HttpOnly sessions, and a read-only review desk for the private roster,
variants, field candidates, and their official source provenance. Review actions,
ingestion controls, and publication remain intentionally unavailable.

The Measure Explorer and API-mode measure detail pages now read from FastAPI.
The Dashboard comparison ledger uses published API records in API mode and does
not label them fictional; comparison states remain unknown until the M2 backend
is implemented. What's New shows an honest unavailable state in API mode, and AI
Impact remains a demo-only prototype. The reviewed CMS roster may be loaded
locally only as private draft data; it is intentionally excluded from public API
responses. Detailed specification review and formal publication approval remain
incomplete, so M1 is not complete.

See `docs/checkpoint-c1.md` for schema decisions, scope boundaries, and the
verified local workflow.

## Quick local start

The repository Makefile keeps the normal workflow short. On the first run:

```sh
make setup
make admin-credentials
# Copy the generated CMSQI_ADMIN_* lines into .env once.
make seed
```

After that, start PostgreSQL, apply pending migrations, and launch both FastAPI
and Vite with one command:

```sh
make dev
```

Press `Ctrl+C` once to stop the frontend and backend. PostgreSQL intentionally
stays running for faster restarts; stop it separately with `make stop`. Run the
complete backend and frontend checks with `make check`. Use `make help` to see
the available shortcuts.

The commands below remain available when working on one service independently.

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
- `/admin` — authenticated, read-only private review queue
- `/admin/measures/:measureId` — private variants, candidates, and source provenance

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

Before opening the Admin workspace, generate local credentials interactively and
copy the printed values into the repository root `.env` file. No password is
stored in source control; only a scrypt password hash is configured.

```sh
cd backend
uv run python -m app.commands.generate_admin_credentials
```

Restart FastAPI after updating `.env`, then choose **Admin** in the frontend
workspace switch. Protected read endpoints live under `/api/admin/...` and use a
signed HttpOnly session cookie. Set `CMSQI_ADMIN_SESSION_SECURE=true` in every
HTTPS deployment.

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
