# Deployment guide

## Current deployment status

The repository contains production-style frontend and backend images and a local
full-stack Compose configuration. Both images and the complete local stack passed
the smoke check on October 27, 2026. A public URL has not yet been selected or
created. Do not claim deployment completion until the verification checklist at
the end of this document has been run against the chosen host.

## Render Free preview

The repository includes `render.yaml` for a temporary, no-cost public preview:

- `cms-quality-intelligence-web`: the compiled React application served by
  Nginx. It proxies `/api` and `/health` to the API so browser requests and the
  administrator session remain same-origin.
- `cms-quality-intelligence-api`: the FastAPI Docker image. Its normal container
  startup applies Alembic migrations before accepting requests.
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

Do not run either seed command against this preview by default. A new Render
database intentionally begins with only the schema, so public endpoints remain
empty until separately reviewed records are explicitly published.

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

## Public verification checklist

- [ ] HTTPS is valid and HTTP redirects to HTTPS.
- [ ] `/` and a direct client route such as `/measures` load after refresh.
- [ ] `/health` returns `{"status":"ok"}`.
- [ ] Public API endpoints return only published records.
- [ ] `/api/admin/...` returns `401` without an authenticated session.
- [ ] Admin authentication uses a secure cookie.
- [ ] Database data persists after an application restart.
- [ ] Official source links open the expected CMS publication.
- [ ] No `.env`, key, password, private draft, or internal review response is public.
- [ ] The deployed Git revision and rollback procedure are recorded.

## Deployment evidence

Complete this only after deployment:

| Field | Value |
| --- | --- |
| Public URL | Pending hosting selection |
| Git revision | Pending |
| Deployment environment | Pending |
| Verified at | Pending |
| Verified by | Pending |
