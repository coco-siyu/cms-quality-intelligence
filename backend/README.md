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
