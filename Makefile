SHELL := /bin/bash

.DEFAULT_GOAL := help

.PHONY: help setup db dev containers container-logs stop seed admin-credentials smoke check security-check backend-check frontend-check

help:
	@echo "CMS Quality Intelligence local commands"
	@echo
	@echo "  make setup              Install dependencies, start PostgreSQL, and migrate"
	@echo "  make admin-credentials  Generate the one-time local admin settings"
	@echo "  make seed               Load source-backed CMS records as private drafts"
	@echo "  make dev                Start PostgreSQL, FastAPI, and Vite"
	@echo "  make containers         Build and start the complete containerized application"
	@echo "  make container-logs     Follow logs from the containerized application"
	@echo "  make smoke              Check frontend, API, and database-backed endpoint"
	@echo "  make security-check     Check tracked files for common credential leaks"
	@echo "  make stop               Stop all Docker Compose services"
	@echo "  make check              Run backend and frontend verification"

.env:
	cp .env.example .env
	@echo "Created .env from .env.example."

setup: .env
	cd backend && uv sync
	cd frontend && npm ci
	$(MAKE) db
	cd backend && uv run alembic upgrade head
	@echo
	@echo "Setup complete. Run 'make admin-credentials' once, then 'make seed' and 'make dev'."

db: .env
	docker compose up -d postgres
	./scripts/wait-for-postgres.sh

dev: db
	cd backend && uv run alembic upgrade head
	./scripts/dev.sh

containers: .env
	docker compose up --build -d
	./scripts/wait-for-app.sh

container-logs:
	docker compose logs --follow

smoke:
	./scripts/smoke.sh

stop:
	docker compose stop

seed: db
	cd backend && uv run alembic upgrade head
	cd backend && CMSQI_ALLOW_VERIFIED_DRAFT_SEED=true uv run python -m app.commands.seed_verified

admin-credentials: .env
	cd backend && uv run python -m app.commands.generate_admin_credentials
	@echo
	@echo "Copy the generated CMSQI_ADMIN_* lines into .env, then restart 'make dev'."

check: security-check backend-check frontend-check

security-check:
	./scripts/check-secrets.sh

backend-check:
	cd backend && uv run ruff check app tests
	cd backend && uv run pytest

frontend-check:
	cd frontend && npm test -- --run
	cd frontend && npm run lint
	cd frontend && npm run build
