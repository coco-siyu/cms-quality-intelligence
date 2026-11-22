# Reproducibility and submission guide

Verified on November 15, 2026 against revision
`80db70b606dd4264ccaad6471f4a8dfa81f97fcd`.

## What this project demonstrates

CMS Quality Intelligence is a React/FastAPI/PostgreSQL application for reviewing
year-over-year CMS quality-measure evidence without treating extraction or AI
output as verified fact. The public side exposes only separately reviewed and
published records; the authenticated side preserves sources, immutable
revisions, draft candidates, decisions, and review history.

The release demonstrates the final-project shape described by the official
[2026 course repository](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp):
a clear problem, frontend, backend, API contract, persistence, tests,
containers, public deployment, and a documented AI-assisted workflow. The
course repository also warns that details may still change, so recheck it at
submission time.

## Prerequisites

- Git
- Python 3.12 and `uv`
- Node.js 22 and npm
- PostgreSQL 16 through Docker for host-development mode
- a current stable Docker Compose v2 release for container mode

## Clean checkout

```sh
git clone https://github.com/coco-siyu/cms-quality-intelligence.git
cd cms-quality-intelligence
cp .env.example .env
make setup
make admin-credentials
```

Copy the generated `CMSQI_ADMIN_*` values into `.env`. They are local values;
do not reuse the disposable Render demo credential. Load the reviewed preview
dataset and start the application:

```sh
make preview-data
make dev
```

Open <http://localhost:5173>. `make setup` installs locked dependencies, starts
PostgreSQL, and runs `uv run alembic upgrade head`. Later schema upgrades can be
applied explicitly from `backend/` with that same Alembic command.

For a compiled container review instead:

```sh
make containers
make smoke
```

This builds PostgreSQL, FastAPI, and Nginx/React services. Use
`make integration-test` for the isolated black-box container scenario and
`make stop` to stop services without deleting the database volume.

## Verification commands

```sh
make check
make security-audit
make integration-test
make verify-preview
```

`make security-audit` and `make verify-preview` require network access. The
November 15 clean-checkout run passed 242 backend tests, 42 frontend tests,
Ruff, ESLint, the secret guard, and the production build. The exact-revision
GitHub workflow passed the container suite and CodeQL. See the dated reports in
`security/` and `ops/` for actual findings and limitations.

## Live reviewer path

1. Open <https://cms-quality-intelligence-web.onrender.com>.
2. Compare PY2025 with PY2026 and open measure 001.
3. Inspect the published Changes record and follow its official CMS evidence.
4. Open What's New and confirm CMS source dates remain distinct from internal
   approval and public publication times.
5. Sign in to `/admin` with the disposable course-review credential in the
   README.
6. Inspect, but do not change, the private comparison and source workflows.
7. Review GitHub CI, CodeQL, the Task 71 reports, and the AI-development record.

## Rubric evidence index

| Evidence | Location |
| --- | --- |
| Problem and expected behavior | `README.md`, `docs/product-spec.md`, `docs/plan.md` |
| Frontend | `frontend/` |
| Backend and migrations | `backend/app/`, `backend/alembic/` |
| OpenAPI contract | `openapi.yaml`, `backend/tests/test_openapi_contract.py` |
| PostgreSQL persistence | `compose.yaml`, SQLAlchemy models, migration history |
| Automated verification | `Makefile`, `backend/tests/`, `frontend/src/test/`, `tests/integration/` |
| Containers and public deployment | Dockerfiles, `compose.yaml`, `render.yaml`, `docs/deployment.md` |
| CI, security, and operations | `.github/workflows/`, `security/`, `ops/` |
| AI-assisted workflow | `AGENTS.md`, `docs/ai-development.md` |
| Final reviewer index | `docs/zoomcamp-submission.md` |

## Known limitations

- The public release covers the verified APP Plus roster baseline and one
  reviewed unchanged comparison. Detailed clinical specification fields remain
  private until individually reviewed and published.
- Quality IDs 113 and 484 are present only on the PY2026 side of the current
  baseline. They are not classified as additions until explicit one-sided
  evidence handling is implemented and reviewed.
- Optional AI explanation generation requires a configured provider and remains
  human-reviewed; no public request triggers a model call.
- The Render Free deployment is a disposable preview, not durable production.
  It can sleep, its database has no backup guarantee, and its public demo
  credential permits writes.
- Scheduled source checks, production observability, backup/restore drills, and
  the agent-extension tasks are post-MVP work.
- On the November 15 Mac verification host, an obsolete Compose `v2.0.0-rc.3`
  plugin crashed before application startup. The clean GitHub container job
  passed; upgrade the local plugin before repeating local container QA.

