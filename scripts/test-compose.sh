#!/usr/bin/env bash

set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_project="${CMSQI_COMPOSE_PROJECT_NAME:-cmsqi-integration-$$}"
backend_port="${CMSQI_INTEGRATION_BACKEND_PORT:-18000}"
frontend_port="${CMSQI_INTEGRATION_FRONTEND_PORT:-15173}"
postgres_port="${CMSQI_INTEGRATION_POSTGRES_PORT:-15432}"
keep_stack="${CMSQI_KEEP_INTEGRATION_STACK:-0}"

export CMSQI_COMPOSE_PROJECT_NAME="${compose_project}"
export CMSQI_INTEGRATION_API_URL="http://127.0.0.1:${backend_port}"
export CMSQI_INTEGRATION_FRONTEND_URL="http://127.0.0.1:${frontend_port}"
export CMSQI_TEST_ADMIN_PASSWORD_HASH='scrypt$16384$8$1$Y29tcG9zZS10ZXN0LXNhbHQ$mCknDamj0MQSwkdgEvjV7bIuFYzsX3bdczrmX9JMvu0'
export POSTGRES_DB="cms_quality_integration"
export POSTGRES_USER="cms_quality_integration"
export POSTGRES_PASSWORD="cms_quality_integration_only"
export POSTGRES_PORT="${postgres_port}"
export BACKEND_PORT="${backend_port}"
export FRONTEND_PORT="${frontend_port}"

compose=(
  docker compose
  --project-name "${compose_project}"
  --file "${repository_root}/compose.yaml"
  --file "${repository_root}/tests/integration/compose.test.yaml"
)

cleanup() {
  status=$?
  trap - EXIT
  if [[ ${status} -ne 0 ]]; then
    "${compose[@]}" logs --no-color --tail 200 || true
  fi
  if [[ "${keep_stack}" != "1" ]]; then
    "${compose[@]}" down --volumes --remove-orphans || true
  else
    echo "Compose integration stack retained: ${compose_project}"
  fi
  exit "${status}"
}
trap cleanup EXIT

if [[ ! -f "${repository_root}/.env" ]]; then
  echo "Missing .env. Run 'cp .env.example .env' or use 'make integration-test'." >&2
  exit 1
fi

"${compose[@]}" up --build --detach

CMSQI_SMOKE_API_URL="${CMSQI_INTEGRATION_API_URL}" \
CMSQI_SMOKE_FRONTEND_URL="${CMSQI_INTEGRATION_FRONTEND_URL}" \
  "${repository_root}/scripts/wait-for-app.sh"

cd "${repository_root}/backend"
UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/cmsqi-uv-cache}" \
  uv run pytest "${repository_root}/tests/integration" -q
