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

The initial migration retains stable measure identities, year/program
memberships, immutable version records, source documents and revisions,
field-level availability, evidence locators, publication state, and freshness
metadata. Public repositories project only records marked public/published.

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

The separately reviewed CMS roster can be prepared in a local `demo` or `dev`
database as private draft records. The command is idempotent and does not
publish records to the public API:

```sh
CMSQI_ALLOW_VERIFIED_DRAFT_SEED=true uv run python -m app.commands.seed_verified
```

The source inventory, hashes, evidence locators, and unresolved collection-type
questions are documented in `docs/sources/`. Detailed specification fields
remain out of scope until their variants are reviewed.

When the ignored `var/cms-sources/` cache is present, regenerate the private
field-review CSV from the frozen sources with Poppler's `pdftotext` available:

```sh
uv run python -m app.commands.prepare_review_crosswalk
```

The command changes no database records. All generated review decisions remain
pending until a qualified CMS quality-measure reviewer records an approval.
