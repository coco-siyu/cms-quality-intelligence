# Security and data-handling checks

## Boundaries

- The repository must not contain patient-level data or PHI.
- `.env` and all credentials remain untracked.
- Public repositories and endpoints return only published records.
- Admin endpoints require a signed session and server-side authorization.
- Source retrieval is restricted to allowlisted CMS HTTPS hosts and bounded by
  timeout, redirect, and response-size limits.
- AI clarification remains private, evidence-bounded, and unable to publish.

## Automated evidence

| Check | Command or workflow | Coverage |
| --- | --- | --- |
| Credential guard | `make security-check` | Ensures `.env` is ignored/untracked and scans for high-signal access-key/private-key patterns |
| Authorization and data isolation | `backend/tests/test_admin_api.py` and `backend/tests/test_measures_api.py` | Unauthenticated admin denial and private/public separation |
| Safe source retrieval | `backend/tests/test_source_ingestion.py` | Host allowlist, redirect, content type, size, and failure behavior |
| Contract validation | `backend/tests/test_openapi_contract.py` | OpenAPI structure and implemented operations |
| Static analysis | `.github/workflows/codeql.yml` | Python and JavaScript/TypeScript CodeQL analysis |
| Dependency monitoring | `.github/dependabot.yml` | npm, Python, Docker, and GitHub Actions update alerts |

## Local result

On October 27, 2026, the repository secret guard, backend Ruff checks, backend
test suite, frontend tests, frontend lint, frontend production build, both Docker
image builds, and the full application smoke check passed. GitHub-hosted CodeQL
and Dependabot evidence will exist only after these files are committed and
pushed; do not claim those hosted checks have run before then.

## Human checks before release

- Review generated dependency updates rather than merging them automatically.
- Inspect GitHub secret-scanning and CodeQL results after the first push.
- Use non-default production credentials and `CMSQI_ADMIN_SESSION_SECURE=true`.
- Confirm public responses do not contain private review notes or candidates.
- Rotate any credential immediately if it appears in logs, diffs, screenshots,
  or conversation transcripts.
