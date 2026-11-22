# AI Dev Tools Zoomcamp submission evidence

Status date: November 15, 2026

The official
[2026 course repository](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp)
describes the final project as an end-to-end application with a clear problem,
frontend, backend, API contract, persistence, tests, containerization, public
deployment, and documentation of the AI-assisted workflow. It also warns that
2026 details may still change, so compare this checklist with the final
submission page immediately before submission.

## Requirement map

| Requirement | Repository evidence | Status |
| --- | --- | --- |
| Clear problem and expected behavior | `README.md`, `docs/product-spec.md`, `docs/plan.md` | Complete |
| Frontend | React/TypeScript application under `frontend/` | Complete |
| Backend | FastAPI application and services under `backend/app/` | Complete |
| Frontend/backend contract | `openapi.yaml` and contract tests | Complete |
| Persistent storage | PostgreSQL, SQLAlchemy models, and Alembic migrations | Complete |
| Automated tests | Backend pytest suite; frontend Vitest, lint, and build | Complete |
| Containerization | Backend/frontend Dockerfiles and full `compose.yaml` stack | Complete; both images and the full local smoke check passed October 27, 2026 |
| Public deployment | `docs/deployment.md` | Render Free preview live; automated public smoke and access-boundary checks pass |
| AI-assisted workflow documentation | `AGENTS.md` and `docs/ai-development.md` | Complete |
| Reproducible reviewer instructions | `README.md`, `docs/reproducibility.md`, Makefile | Clean-clone `make check` passed; exact-commit hosted container job passed |
| CI and baseline security | GitHub Actions, CodeQL, Dependabot, `security/`, `ops/` | Hosted CI and CodeQL pass on deployed revision `80db70b`; dated findings are preserved |

## Useful review commands

```sh
make setup
make check
make containers
make smoke
```

The non-container development workflow remains available through `make dev`.

## Demonstration path

1. Open the public homepage and Measure Explorer.
2. Show that public routes contain only published API records.
3. Sign in to the private admin workspace with the disposable credentials in
   `README.md`.
4. Open the CMS source registry and inspect immutable source history.
5. Start **Check for updates** and show timestamped document progress.
6. Inspect a source-backed candidate and its official evidence.
7. Explain that human approval is required and unresolved records remain private.
8. Show tests and the CI workflow.

The demo must not describe unreviewed CMS candidates as verified production data.

## Remaining submission blockers

1. Recheck the official rubric and submission deadline because the course marks
   the 2026 details as subject to change.
2. For the certificate path, complete the course's required peer reviews.
3. Upgrade the affected Mac's obsolete Docker Compose RC plugin before repeating
   local container QA; the exact-commit GitHub container job is currently the
   clean-host container evidence.
4. Rotate or remove the intentionally public preview login after the review
   period.
