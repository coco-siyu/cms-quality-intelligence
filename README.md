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

See [`docs/architecture.md`](docs/architecture.md) for component boundaries,
trust decisions, processing flow, and local/deployed runtime layouts.
See [`docs/deployment.md`](docs/deployment.md) for the local container workflow,
the Render Free preview procedure, required secrets, and public verification
checklist.

## Current status

Checkpoints A and B provide the runnable application foundation and the
Lovable-derived editorial interface. Checkpoint C1 adds PostgreSQL persistence,
Alembic migrations, the M1 public measure endpoints, and typed frontend API
queries. Checkpoints C2.1–C2.5 add the reviewed PY2025–PY2026 source inventory,
immutable retrieval manifest, exact roster evidence locators, explicit
collection variants, and a guarded private review workflow. The database can
hold 32 collection-specific variants, 352 source-backed field candidates, and
append-only reviewer decisions. Seeded detailed-field candidates begin pending
and remain non-public unless a separate publication workflow is completed. A
guarded preview bootstrap publishes only the eight verified identities, 14
program-year memberships, roster evidence, and the three official source
revisions supporting those memberships. All 32 collection variants and 352
detailed field candidates remain private for administrator review.

The M3 admin foundation adds an environment-configured single-admin login,
signed HttpOnly sessions, and a private review desk for the roster, variants,
field candidates, and their official source provenance. An administrator can
review one field candidate at a time, correct an approved value, request a
revision, mark a field not applicable, and inspect append-only decision history.
The review dialog pairs the same collection-specific field across PY2025 and
PY2026, labels exact wording matches or differences without assigning clinical
meaning, and explains extraction states that need SME, manual, or applicability
review. Official source excerpts are stored and displayed separately from
normalized candidate values; rows without a captured excerpt direct the reviewer
to the exact locator and official source. Separately, the source registry accepts
only allowlisted cms.gov HTML/PDF URLs, records bounded retrieval attempts, stores
immutable content-hash revisions, extracts text with section/page locators, skips
unchanged files, and supports append-only force re-extraction. A separate protected
normalization action converts recognized document labels into typed private field
candidates with exact segment evidence. Only exact existing identities can reach
the review queue; incomplete and ambiguous results remain unresolved. An optional
clarification action can inspect bounded excerpts from additional registered CMS
sources and retain a schema-validated proposal or disagreement for human review.
The source workspace can also launch a bounded registry-wide **Check for updates**
run. It persists and returns the queued run before retrieval, then the private UI
polls while work is active. The run records each source's timestamped stage history,
continues after isolated failures, normalizes changed readable sources, and stops
all resulting candidates at human verification. Administrators can inspect recent
run history, completion counts, current document stages, and persistent failure
reasons. Interrupted work remains visibly non-complete, and partially failed runs
are never presented as successful.
Neither source checking, normalization, nor clarification verifies or publishes
data. Individual reviewed fields have a separately authorized publication
endpoint; the real queue remains unpublished until qualified review decisions
exist.

The Measure Explorer and API-mode measure detail pages now read from FastAPI.
The Dashboard comparison ledger uses published API records in API mode and does
not label them fictional; comparison states remain unknown until the M2 backend
is implemented. What's New shows an honest unavailable state in API mode, and AI
Impact remains a demo-only prototype. The public roster baseline can be explored
without presenting unreviewed clinical details as verified. Detailed
specification review and formal field publication remain incomplete, so M1 is
not complete.

See `docs/checkpoint-c1.md` for schema decisions, scope boundaries, and the
verified local workflow.

## Quick local start

The repository supports a fast host-development workflow and a fully containerized
review workflow. Both use the same PostgreSQL schema and API contract.

### Host development with live reload

On the first run:

```sh
make setup
make admin-credentials
# Copy the generated CMSQI_ADMIN_* lines into .env once.
make preview-data
```

After that, start PostgreSQL, apply pending migrations, and launch both FastAPI
and Vite with one command:

```sh
make dev
```

Press `Ctrl+C` once to stop the frontend and backend. PostgreSQL intentionally
stays running for faster restarts; stop Compose services with `make stop`. Run
the complete backend and frontend checks with `make check`. Use `make help` to
see the available shortcuts.

### Complete containerized application

After creating `.env` and local admin credentials, build and start PostgreSQL,
FastAPI, migrations, and the compiled frontend with one command:

```sh
make containers
```

The frontend is available at `http://localhost:5173` and FastAPI at
`http://localhost:8000`. `make containers` waits for the stack and checks the
frontend, API health, and a database-backed endpoint. Repeat that check with
`make smoke`, follow output with `make container-logs`, and stop the stack with
`make stop`.

To seed private reviewed-draft artifacts inside the containerized backend:

```sh
docker compose exec \
  -e CMSQI_ALLOW_VERIFIED_DRAFT_SEED=true \
  backend .venv/bin/python -m app.commands.seed_verified
```

Use `make preview-data` in the host-development workflow when you want the same
split as the hosted preview: verified roster membership in the public workspace,
with collection variants and detailed candidates available only in Admin. The
command is idempotent.

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
- `/admin/sources` — private CMS source registry, bounded ingestion runs, and extraction status
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

The source registry is available at `/admin/sources`. Register only a vetted
official CMS URL, then use **Check source** to create a private retrieval event.
Use **Check for updates** to run the same safe path for every active source. The
registry-wide action is capped by `CMSQI_INGESTION_RUN_MAX_SOURCES` (25 by default)
and returns a durable queued run for background processing. The page refreshes
progress while that run is active and preserves timestamped source-level stages,
final outcomes, and errors in run history.
**Force re-extract** reruns text extraction for identical bytes while retaining
the prior extraction. **Normalize candidates** applies deterministic field rules to
the latest successful extraction and may stage exact identity matches in the
private review queue. **Inspect candidates** shows unresolved fields. When the
optional provider is configured, **Clarify with AI** searches additional active
registered CMS sources and stores a private evidence-bounded proposal. None of
these actions approves or publishes measure data.

AI clarification is disabled by default. To enable it locally, set both values
below in the repository root `.env` and restart FastAPI:

```sh
CMSQI_OPENAI_API_KEY=your-api-key
CMSQI_AI_CLARIFICATION_MODEL=your-structured-output-capable-model
```

The request uses strict structured output and `store=false`. The database retains
the configured model name, prompt version, provider response ID, exact CMS excerpt
snapshots, and support/conflict assessments for administrator review. Do not
commit the API key.

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

For an explicit preview environment, prepare the same records and publish only
the source-backed roster baseline:

```sh
CMSQI_DEPLOYMENT_ENVIRONMENT=preview \
CMSQI_BOOTSTRAP_PREVIEW=true \
uv run python -m app.commands.bootstrap_preview
```

This operation does not publish collection-specific variants, extracted field
candidates, reviewer notes, or detailed specification values. It also removes
only explicitly fictional `DEMO-*` seed fixtures so the preview cannot mix them
with the verified roster.

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

## Zoomcamp evidence

- [`docs/zoomcamp-submission.md`](docs/zoomcamp-submission.md) maps final-project
  requirements to repository evidence and records remaining blockers.
- [`docs/ai-development.md`](docs/ai-development.md) documents how Lovable,
  Codex, automated checks, and human review were used.
- [`docs/deployment.md`](docs/deployment.md) defines production settings and the
  public verification checklist. A real public URL is still pending a hosting
  decision and must not be claimed before it is tested.
- [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs backend, frontend,
  contract, and image-build checks for pushes and pull requests.
