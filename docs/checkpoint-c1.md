# Checkpoint C1 — API and data foundation

Checkpoint C1 connects the M1 Measure Explorer surface to a public FastAPI API
and a versioned PostgreSQL schema. It does not load or claim a verified CMS
inventory, and it does not implement the M2 comparison engine.

## Data model

The initial Alembic migration creates:

- `measures` for stable identities and an explicit public flag;
- `program_memberships` for program/year applicability and publication state;
- `measure_versions` and `specification_fields` for retained year-specific
  versions, explicit `available` / `unavailable` / `unresolved` semantics, and
  freshness metadata;
- `source_documents`, immutable `source_revisions`, and
  `evidence_references` for document hashes, dates, excerpts, and locators;
- `measure_comparisons` and `measure_comparison_fields` as a read-only
  projection slot for an already approved comparison state.

The comparison tables do not calculate changes. Production deterministic
comparison is C2/M2 work and requires a formal contract extension first.
Uniqueness, year-range, enum, foreign-key, and field-value constraints protect
version and availability semantics. New versions and source revisions are
inserted rather than destructively overwriting historical records.

## Public API

`openapi.yaml` remains unchanged and authoritative. C1 implements:

- `GET /api/performance-years`
- `GET /api/measures`
- `GET /api/measures/{measure_id}`
- `GET /api/measures/{measure_id}/versions`

The list supports approved-field keyword search, year, comparison-state,
affected-field, verification-state, and pagination parameters. Detail responses
include only published versions and evidence from published source revisions.
Drafts, internal database keys, document hashes, and private records are not
serialized by public response models. Validation and missing-resource errors use
the `ApiError` shape in the OpenAPI contract.

## Frontend data modes

`VITE_DATA_MODE=api` is the default. In this mode, Measure Explorer and measure
detail use typed TanStack Query modules under
`frontend/src/features/measures/api/`. Loading, empty, unresolved, 404, and
network-error states are explicit; an API error never triggers a demo fallback.

`VITE_DATA_MODE=demo` is an intentional visual-prototype mode backed only by
`frontend/src/features/measures/demo/`. Regardless of the selected mode, the
Dashboard comparison ledger, What's New feed, and AI Impact copy are M2-only
and remain marked fictional until production contracts exist.

## Local workflow

```sh
cp .env.example .env
docker compose up -d postgres

cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` and `/health` to port 8000 when
`VITE_API_BASE_URL` is blank.

### Safe demonstration records

The seed command refuses to run unless the operator opts in and the target
database name contains `demo`. Every fixture identity starts with `DEMO-`, all
copy says it is fictional, and no fixture is marked verified.

```sh
cd backend
CMSQI_ALLOW_DEMO_SEED=true uv run python -m app.commands.seed_demo
CMSQI_ALLOW_DEMO_SEED=true uv run python -m app.commands.seed_demo --reset
```

`--reset` removes only `DEMO-*` records and recreates them. Do not run the seed
against a production database. No patient-level data belongs in any environment.

## Verification commands

```sh
cd backend
uv run ruff check .
uv run pytest

cd ../frontend
npm run lint
npm run test
npm run build
```

## Known limitations and C2 prerequisites

- No authoritative 2025 or 2026 CMS APP Plus data has been inventoried,
  reconciled, or loaded.
- Performance-year defaults are configuration values when the database contains
  no published membership records.
- The frontend currently requests at most 100 measures in one page for filtered
  Previous/Next navigation; server-driven multi-page navigation remains future
  work.
- Dashboard metrics, timeline/feed, deterministic diffs, wording-only
  classification, and role-specific explanations require M2 contracts and
  verified source records.
- Admin authentication, ingestion, candidate review, and approval workflows
  remain M3 scope.
