# Docker Compose integration tests

This suite treats the three-service Compose application as a black box. It uses
an isolated Compose project and PostgreSQL volume, publishes the repository's
reviewed preview roster, supplies test-only administrator credentials, and
disables optional AI providers.

Run it from the repository root:

```sh
make integration-test
```

The runner builds the images, starts the stack, waits for the database-backed
API, runs the tests, prints recent container logs on failure, and removes its
containers and volume. Set `CMSQI_KEEP_INTEGRATION_STACK=1` to keep a failed
stack for diagnosis.

The scenarios cover:

- direct backend health and the Nginx same-origin health proxy;
- frontend delivery and SPA fallback for public and admin client routes;
- FastAPI JSON errors under `/api` rather than accidental SPA fallback;
- migrations plus the reviewed 2025–2026 preview-roster bootstrap;
- public response isolation from private candidates and review metadata;
- rejected unauthenticated access and invalid admin credentials;
- session-cookie attributes, authenticated private reads, and logout;
- explicit action-header enforcement for protected mutations; and
- PostgreSQL persistence after restarting all three Compose services.

Controlled ingestion and publication state transitions remain in the backend
integration suite, where CMS-like fixture bytes and failure timing can be made
deterministic. Browser interactions remain in Vitest; this suite verifies the
deployed HTTP and container boundaries that those faster tests cannot cover.
