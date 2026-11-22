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
| Combined local audit | `make security-audit` | Runs the credential guard plus Python and production npm advisory scans; requires advisory-service network access |
| Authorization and data isolation | `backend/tests/test_admin_api.py` and `backend/tests/test_measures_api.py` | Unauthenticated admin denial and private/public separation |
| Safe source retrieval | `backend/tests/test_source_ingestion.py` | Host allowlist, redirect, content type, size, and failure behavior |
| Browser output encoding | `frontend/src/test/apiIntegration.test.tsx` | Confirms API-supplied markup is rendered as inert text rather than executable DOM |
| Contract validation | `backend/tests/test_openapi_contract.py` | OpenAPI structure and implemented operations |
| Static analysis | `.github/workflows/codeql.yml` | Python and JavaScript/TypeScript CodeQL analysis |
| Dependency monitoring | `.github/dependabot.yml` | npm, Python, Docker, and GitHub Actions update alerts |

## Local result

The current dated audit, remediation, residual development-tool findings, and
data-handling policy are recorded in
[`task-63-audit-2026-11-14.md`](task-63-audit-2026-11-14.md). The local secret
guard and production dependency scans pass after the recorded lockfile updates.
CodeQL and Dependabot remain the hosted follow-up layer; do not describe a
hosted run as passing without checking its GitHub result for the relevant commit.

Task 71's release audit, including Bandit output, current dependency results,
hosted workflow links, residual findings, and triage decisions, is recorded in
[`task-71-audit-2026-11-15.md`](task-71-audit-2026-11-15.md).

## Human checks before release

- Review generated dependency updates rather than merging them automatically.
- Inspect GitHub secret-scanning and CodeQL results after the first push.
- Use non-default production credentials and `CMSQI_ADMIN_SESSION_SECURE=true`.
- Confirm public responses do not contain private review notes or candidates.
- Treat development-only advisory findings separately from deployed production
  dependencies, but continue monitoring and update the toolchain when a valid
  patched release is available.
- Rotate any credential immediately if it appears in logs, diffs, screenshots,
  or conversation transcripts.
