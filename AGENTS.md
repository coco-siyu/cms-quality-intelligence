# CMS Quality Intelligence contributor instructions

## Source of truth

- Read `docs/product-spec.md`, `docs/plan.md`, `docs/tasks.md`, and
  `openapi.yaml` before changing product behavior.
- Preserve the modular React/FastAPI/PostgreSQL architecture described in
  `docs/architecture.md`.
- Official CMS evidence is authoritative. Never describe an extracted,
  AI-generated, fictional, or unreviewed candidate as verified production data.
- Never infer that a measure was removed solely because it is absent from one
  source.
- Do not add patient-level data, PHI, real credentials, or secrets.

## Dependency management

- Use `uv` for all backend dependency management:

  ```sh
  cd backend
  uv sync
  uv add <PACKAGE-NAME>
  uv run python <PYTHON-FILE>
  ```

- Use npm and the committed lockfile for the frontend. Do not introduce Bun,
  TanStack Start, Nitro, or cloud services without an approved architecture
  change.
- Add only dependencies required by the implemented behavior.

## Implementation expectations

- Inspect a file before overwriting or substantially refactoring it.
- Keep public and private data boundaries enforced in backend queries and routes,
  not only through hidden frontend controls.
- Keep business, comparison, verification, and publication decisions out of
  presentation components.
- Preserve source URLs, immutable revisions, evidence locators, review history,
  and explicit unavailable/unresolved states.
- Make small, reviewable changes and regularly commit code to Git. Never push,
  merge, or rewrite shared history without the maintainer's approval.

## Verification

- Run `make check` for a complete local verification pass.
- For focused backend work, run `uv run ruff check .` and the relevant pytest
  files from `backend/`.
- For focused frontend work, run the relevant Vitest files, `npm run lint`, and
  `npm run build` from `frontend/`.
- Update `openapi.yaml`, contract tests, documentation, and backlog status when
  an API or acceptance criterion changes.
- Mark work complete only when its documented acceptance criteria pass.
