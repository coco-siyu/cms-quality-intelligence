# Deployment guide

## Current deployment status

The repository contains production-style frontend and backend images and a local
full-stack Compose configuration. Both images and the complete local stack passed
the smoke check on October 27, 2026. A Render Free public preview is also live.
Automated public verification passed for HTTPS redirects, direct client routes,
API health and proxying, the database-backed public endpoint, and unauthenticated
Admin protection. The unchecked manual items below remain required before this
preview should be described as production-ready.

## Render Free preview

The repository includes `render.yaml` for a temporary, no-cost public preview:

- `cms-quality-intelligence-web`: the compiled React application served by
  Nginx. It proxies `/api` and `/health` to the API so browser requests and the
  administrator session remain same-origin. Its `CMSQI_BACKEND_URL` points to
  the API's public Render hostname because free web services cannot receive
  private-network requests.
- `cms-quality-intelligence-api`: the FastAPI Docker image. Its preview startup
  applies Alembic migrations, idempotently prepares the frozen reviewed dataset,
  publishes only the verified roster baseline, and then accepts requests.
- `cms-quality-intelligence-db`: a private-network PostgreSQL 16 database.

To create the preview:

1. Run the complete local verification pass with `make check`.
2. Generate an administrator username and password hash locally:

   ```sh
   cd backend
   uv run python -m app.commands.generate_admin_credentials
   ```

3. Commit and push the reviewed deployment files to the GitHub branch that
   Render will track.
4. In Render, choose **New > Blueprint**, connect the repository, and select the
   root `render.yaml` file.
5. When prompted, provide `CMSQI_ADMIN_USERNAME` and
   `CMSQI_ADMIN_PASSWORD_HASH`. Do not provide or commit the plaintext password.
   Render generates the independent session-signing secret.
6. Apply the Blueprint and wait for the database, API, and web service to finish
   their initial deploys.
7. Treat the `cms-quality-intelligence-web` URL as the public application URL.
   The API service URL is an implementation detail.
8. Run the remote smoke check, replacing both placeholders:

   ```sh
   CMSQI_SMOKE_FRONTEND_URL=https://YOUR-WEB-SERVICE.onrender.com \
   CMSQI_SMOKE_API_URL=https://YOUR-API-SERVICE.onrender.com \
   ./scripts/smoke.sh
   ```

The Blueprint sets `CMSQI_DEPLOYMENT_ENVIRONMENT=preview` and
`CMSQI_BOOTSTRAP_PREVIEW=true`. Together these explicitly authorize the guarded,
idempotent preview bootstrap on service startup. The public side receives eight
measure identities, 14 verified PY2025/PY2026 memberships, their roster evidence,
and only the source revisions needed for that evidence. The Admin workspace
receives the 32 private collection variants and 352 pending field candidates.
Detailed candidate values, reviewer notes, and unresolved specification fields
remain outside public responses. The bootstrap also removes only explicitly
fictional `DEMO-*` seed fixtures so they cannot be mixed into the public roster.
Do not enable these preview flags in a durable production environment; use a
separately reviewed release procedure there.

Render Free is a preview environment, not a durable production environment. A
free web service sleeps after 15 minutes without traffic and can take about a
minute to wake. The free database is limited to 1 GB, has no backups, and expires
30 days after creation. Before expiration, export any records that must be
retained or upgrade/migrate the database. Never represent the preview as a
durable production deployment.

## Recommended layouts

Choose one of these without changing application behavior:

1. **Managed containers and PostgreSQL:** deploy the backend image and frontend
   image as two services, connect FastAPI to a managed PostgreSQL database, and
   route `/api` to FastAPI through the frontend platform or shared gateway.
2. **Small Linux VM:** install Docker, run the Compose stack behind a TLS reverse
   proxy, restrict PostgreSQL to the private host network, and back up the named
   volume.

The first option reduces database and TLS maintenance. The second is closer to
the local Compose topology but requires operating the host safely.

## Required production settings

Provide these through the host's encrypted secret/environment system:

- `CMSQI_DATABASE_URL`: production PostgreSQL connection string.
- `CMSQI_ADMIN_USERNAME`: non-default administrator name.
- `CMSQI_ADMIN_PASSWORD_HASH`: output from the credential generator, never the
  plaintext password.
- `CMSQI_ADMIN_SESSION_SECRET`: independently generated signing secret.
- `CMSQI_ADMIN_SESSION_SECURE=true`: required behind HTTPS.
- Optional `CMSQI_OPENAI_API_KEY` and `CMSQI_AI_CLARIFICATION_MODEL` only if the
  private clarification feature is intentionally enabled.

Use strong, unique database credentials. Do not deploy the local demo password,
the local `.env`, fictional fixtures as verified records, or patient-level data.

## Release procedure

1. Run `make check` from a clean checkout.
2. Build both images with `docker compose build backend frontend`.
3. Provision PostgreSQL and durable backups.
4. Configure production secrets.
5. Run `alembic upgrade head` as a release step before serving traffic.
6. Deploy the backend and confirm `/health`.
7. Deploy the frontend and confirm same-origin `/api` proxying.
8. Load only explicitly reviewed data through guarded commands.
9. Record the public URL, release revision, and verification date below.

## Rollback procedure

For an application-only regression, open each affected Render web service,
choose **Deploys**, and redeploy the last successful Git revision. Keep the API
and frontend on compatible revisions. If the release included a database schema
change, do not roll the API behind that migration without first reviewing the
Alembic compatibility and taking a database backup. The Git-based fallback is a
normal revert commit on `main`; do not rewrite shared history.

## Public verification checklist

- [x] HTTPS is valid and HTTP redirects to HTTPS.
- [x] `/` and a direct client route such as `/measures` load after refresh.
- [x] `/health` returns `{"status":"ok"}`.
- [ ] Public API returns the eight roster identities and 14 memberships after bootstrap.
- [x] `/api/admin/...` returns `401` without an authenticated session.
- [ ] Admin authentication uses a secure cookie.
- [ ] Database data persists after an application restart.
- [ ] Each published roster record exposes two working official CMS evidence links.
- [ ] No `.env`, key, password, private draft, or internal review response is public.
- [x] The deployed Git revision and rollback procedure are recorded.

## Deployment evidence

Complete this only after deployment:

| Field | Value |
| --- | --- |
| Public URL | `https://cms-quality-intelligence-web.onrender.com` |
| API URL | `https://cms-quality-intelligence-api.onrender.com` |
| Verified application revision | `3e69248` |
| Deployment environment | Render Free: Nginx/React, FastAPI, PostgreSQL 16 |
| Verified at | 2026-10-27 22:12 UTC |
| Verified by | Automated repository smoke check and public boundary probes |
