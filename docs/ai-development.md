# AI-assisted development record

## Purpose

This project uses AI development tools to accelerate planning, implementation,
review, and debugging while retaining human control over architecture, source
accuracy, credentials, and publication decisions. This document records that
workflow for review; it is not evidence that AI-generated healthcare claims are
correct.

## Tools and roles

| Tool | Use in this project | Human control |
| --- | --- | --- |
| Lovable | Produced visual interface references and interactive prototypes | The maintainer selected the visual direction and rejected its generated backend/runtime choices |
| Codex | Repository inspection, scoped implementation, tests, debugging, and documentation | The maintainer approved checkpoints, selected branches, reviewed screens, and decided when work advanced |
| Git and GitHub | Preserved small reviewable changes and pull-request history | The maintainer controlled commits, pushes, merges, and the `main` branch |
| Optional OpenAI API | Private evidence-bounded clarification proposals | Disabled without configuration; output requires human review and cannot publish records |

## Representative workflow

### 1. Specification before implementation

The maintainer supplied a product specification, milestone plan, backlog, and
OpenAPI contract as the source of truth. The Lovable applications were treated as
visual references. AI-assisted analysis mapped prototype components to the
existing React/FastAPI/PostgreSQL architecture before code was changed.

### 2. Incremental frontend migration

The maintainer approved React, TypeScript, Vite, and client-side TanStack Router
while explicitly rejecting TanStack Start, Nitro, Bun, and new cloud services.
The interface was migrated in checkpoints, first keeping labelled fictional data,
then replacing it with typed API queries. The maintainer visually reviewed the
dashboard, measure routes, admin workspace, and field-review dialog.

### 3. Evidence and data safeguards

AI-assisted source research produced candidate inventories, never automatically
verified production facts. The implementation retains official URLs, revisions,
hashes, locators, excerpts, uncertainty states, and private draft boundaries.
The maintainer requested explanations of the review workflow before authorizing
later tasks. No patient-level data was introduced.

### 4. Implementation and correction loop

Work was performed in focused backlog slices. After each slice, automated tests,
linting, type checks, and production builds were run. Examples of corrections
made during review include:

- Preventing a second ingestion run from relabelling active work as interrupted.
- Recording extraction only when extraction actually starts.
- Fixing a frontend candidate-loading condition that incorrectly appeared active.
- Persisting unexpected background ingestion failures instead of leaving an
  indefinitely running state.
- Keeping demonstration records out of public API responses.

### 5. Human review boundaries

The maintainer retains responsibility for:

- Confirming CMS facts with qualified subject-matter expertise.
- Approving or correcting extracted candidates.
- Selecting deployment infrastructure and managing cloud credentials.
- Reviewing diffs and deciding when to commit, push, merge, or publish.
- Performing the Zoomcamp submission and required peer reviews.

## Repository instructions and reproducibility

- `AGENTS.md` defines the required backend package manager and commit practice.
- `docs/product-spec.md`, `docs/plan.md`, and `docs/tasks.md` constrain product work.
- `openapi.yaml` constrains frontend/backend communication.
- `make check` runs backend and frontend verification.
- `.github/workflows/ci.yml` repeats locked checks on pushes and pull requests.

## Limitations

- Conversation history is not a substitute for durable technical documentation;
  decisions relevant to the product are summarized in repository documents.
- Automated tests validate software behavior, not clinical or policy correctness.
- AI-generated code and prose can be wrong. Passing checks and human source review
  remain required.
- The optional clarification provider is not necessary for normal public browsing
  and fails closed when credentials are absent.
