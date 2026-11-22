# Task 71 operational health and diagnosis

Check date: November 15, 2026  
Checked Git revision: `80db70b606dd4264ccaad6471f4a8dfa81f97fcd`

## Hosted release health

`make verify-preview` passed after the release and first reviewed comparison
publication. It confirmed:

- the React frontend, FastAPI health endpoint, and PostgreSQL-backed public API
  were reachable;
- eight public measure identities and 14 year memberships were present;
- measure 001 retained two official CMS evidence references for each year;
- an unauthenticated private request returned HTTP 401;
- HTTP redirected to HTTPS; and
- the roster response fingerprint was
  `8243a53c7ccaad91a8cc1faa998f20b7d40cb1c7c8fa7b04802c069ebb53e795`, with
  last-verified marker `2026-10-18T18:54:47Z`.

The Render dashboards showed both services live on commit `80db70b`. The public
comparison endpoint returned one evidence-gated record: Quality ID 001,
classified as unchanged between PY2025 and PY2026 and published at
`2026-11-15T23:14:42.365370Z`. Six private two-sided drafts were prepared; the
one-sided 113 and 484 records were safely skipped rather than inferred as added.

## Clean-checkout verification

An isolated clone at `/private/tmp/cmsqi-task72.q9wzF0` was created from the
audited revision. It ran:

```sh
cp .env.example .env
cd backend && uv sync --frozen
cd ../frontend && npm ci
cd .. && make check
```

The secret guard and Ruff passed; 242 backend tests and 42 frontend tests passed;
ESLint passed; and the production frontend built. The only backend warning was a
third-party Starlette deprecation. Vite gave a non-blocking warning for a
JavaScript chunk larger than 500 kB. GitHub's clean Ubuntu runner also passed
the backend, frontend, secret-guard, and container integration jobs.

## Diagnosed local container-tool failure

The local Docker CLI was 27.0.3, but the Compose plugin identified itself as
`v2.0.0-rc.3`. Both `docker compose version` and
`docker compose config --quiet` printed a Go nil-pointer panic and exited with
status 2. This is a host-tool failure before application containers are parsed
or started; it is not evidence of an application runtime failure.

Triage:

1. The exact revision's GitHub container job passed on a clean runner, including
   Compose validation and the isolated integration suite.
2. Render and the public smoke checks passed independently of the local plugin.
3. Upgrade Docker Desktop or install a current stable Compose v2 plugin, then
   rerun `docker compose version`, `docker compose config --quiet`, and
   `make integration-test`.
4. Until then, use the passing GitHub job as the clean-host container evidence;
   do not describe the broken local RC plugin as validated.

## Operational limitations

- Render Free services can sleep and need a cold-start delay.
- The free database has no backup guarantee and expires unless upgraded.
- The published demo credential is disposable and must be rotated after review.
- Scheduled source checks, durable production backups, and production
  observability/alerting remain post-MVP work.

