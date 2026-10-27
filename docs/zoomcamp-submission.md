# AI Dev Tools Zoomcamp submission evidence

Status date: October 27, 2026

The current course repository describes the final project as an end-to-end
application with a clear problem, frontend, backend, API contract, persistence,
tests, containerization, deployment, and documentation of the AI-assisted
workflow. The official 2026 materials may still change, so this checklist must be
compared with the final submission page before submission.

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
| Public deployment | `docs/deployment.md` | **Blocked: hosting choice and account authorization required** |
| AI-assisted workflow documentation | `AGENTS.md` and `docs/ai-development.md` | Complete |
| Reproducible reviewer instructions | `README.md`, Makefile, smoke script, this guide | Complete locally; public URL pending |
| CI and baseline security | GitHub Actions, CodeQL, Dependabot, `security/README.md` | Configured; first hosted runs require push |

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
3. Sign in to the private admin workspace.
4. Open the CMS source registry and inspect immutable source history.
5. Start **Check for updates** and show timestamped document progress.
6. Inspect a source-backed candidate and its official evidence.
7. Explain that human approval is required and unresolved records remain private.
8. Show tests and the CI workflow.

The demo must not describe unreviewed CMS candidates as verified production data.

## Remaining submission blockers

1. Select and authorize a hosting provider.
2. Deploy the application and persistent PostgreSQL database.
3. Complete the deployment evidence in `docs/deployment.md`.
4. Recheck the official rubric and submission deadline.
5. For the certificate path, complete the course's required peer reviews.
