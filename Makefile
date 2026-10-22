SHELL := /bin/bash

.DEFAULT_GOAL := help

.PHONY: help setup db dev stop seed admin-credentials check backend-check frontend-check

help:
	@echo "CMS Quality Intelligence local commands"
	@echo
	@echo "  make setup              Install dependencies, start PostgreSQL, and migrate"
	@echo "  make admin-credentials  Generate the one-time local admin settings"
	@echo "  make seed               Load source-backed CMS records as private drafts"
	@echo "  make dev                Start PostgreSQL, FastAPI, and Vite"
	@echo "  make stop               Stop PostgreSQL (application servers stop with Ctrl+C)"
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

stop:
	docker compose stop

seed: db
	cd backend && uv run alembic upgrade head
	cd backend && CMSQI_ALLOW_VERIFIED_DRAFT_SEED=true uv run python -m app.commands.seed_verified

admin-credentials: .env
	cd backend && uv run python -m app.commands.generate_admin_credentials
	@echo
	@echo "Copy the generated CMSQI_ADMIN_* lines into .env, then restart 'make dev'."

check: backend-check frontend-check

backend-check:
	cd backend && uv run ruff check app tests
	cd backend && uv run pytest

frontend-check:
	cd frontend && npm test -- --run
	cd frontend && npm run lint
	cd frontend && npm run build
