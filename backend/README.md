# CMS Quality Intelligence backend

FastAPI and SQLAlchemy modular monolith for the public M1 Measure Explorer.
Python dependencies and commands are managed with `uv`; schema changes are
managed with Alembic.

From the repository root, copy `.env.example` to `.env` and start PostgreSQL:

```sh
docker compose up -d postgres
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

The migrations retain stable measure identities, year/program memberships,
collection-specific immutable version records, source documents and revisions,
field-level availability, private review candidates, evidence locators,
publication state, and freshness metadata. Public repositories project only
records marked public/published.

Run quality checks:

```sh
uv run ruff check .
uv run pytest
```

The optional seed is intentionally fictional. It requires both
`CMSQI_ALLOW_DEMO_SEED=true` and a database name containing `demo`:

```sh
CMSQI_ALLOW_DEMO_SEED=true uv run python -m app.commands.seed_demo
CMSQI_ALLOW_DEMO_SEED=true uv run python -m app.commands.seed_demo --reset
```

`--reset` deletes only records with `DEMO-` identifiers before rebuilding the
fixture set. The command never loads real CMS records or patient-level data.

The separately reviewed CMS roster, 32 collection variants, and 352 field
candidates can be prepared in a local `demo` or `dev` database as private draft
records. The command is idempotent and does not publish records to the public
API:

```sh
CMSQI_ALLOW_VERIFIED_DRAFT_SEED=true uv run python -m app.commands.seed_verified
```

The source inventory, hashes, evidence locators, collection-type decisions, and
remaining review questions are documented in `docs/sources/`. Detailed
specification candidates remain private until their variants are reviewed.

When the ignored `var/cms-sources/` cache is present, regenerate the private
field-review CSV from the frozen sources with Poppler's `pdftotext` available:

```sh
uv run python -m app.commands.prepare_review_crosswalk
```

The command changes no database records. The guarded seed command separately
copies those candidates into private staging with every review decision set to
`pending`; a qualified CMS quality-measure reviewer must approve them before a
future publication workflow may use them.

After a qualified reviewer completes the **Field Evidence** sheet, export that
sheet as CSV and validate it before importing anything:

```sh
uv run python -m app.commands.import_review_decisions --input /path/to/reviewed-field-evidence.csv
```

The default is a dry run. To append valid decisions to the private audit trail
and update private candidate state in a local `demo` or `dev` database, opt in
explicitly:

```sh
CMSQI_ALLOW_REVIEW_IMPORT=true uv run python -m app.commands.import_review_decisions \
  --input /path/to/reviewed-field-evidence.csv --apply
```

The importer rejects altered candidate evidence, unknown or duplicate review
IDs, incomplete reviewer metadata, stale approvals, and unsupported decisions.
It is idempotent and does not create published specification fields or change
measure publication state.
