#!/usr/bin/env bash

set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backend_pid=""
frontend_pid=""

cleanup() {
  trap - EXIT INT TERM
  if [[ -n "${backend_pid}" ]] && kill -0 "${backend_pid}" 2>/dev/null; then
    kill "${backend_pid}" 2>/dev/null || true
  fi
  if [[ -n "${frontend_pid}" ]] && kill -0 "${frontend_pid}" 2>/dev/null; then
    kill "${frontend_pid}" 2>/dev/null || true
  fi
  wait "${backend_pid}" "${frontend_pid}" 2>/dev/null || true
}

trap cleanup EXIT
trap 'exit 0' INT TERM

echo "Starting FastAPI at http://localhost:8000"
(
  cd "${repository_root}/backend"
  exec uv run uvicorn app.main:app --reload
) &
backend_pid=$!

echo "Starting Vite at http://localhost:5173"
(
  cd "${repository_root}/frontend"
  exec npm run dev
) &
frontend_pid=$!

echo "Press Ctrl+C once to stop both application servers. PostgreSQL will stay running."
while kill -0 "${backend_pid}" 2>/dev/null && kill -0 "${frontend_pid}" 2>/dev/null; do
  sleep 1
done

sleep 1
if ! kill -0 "${backend_pid}" 2>/dev/null && ! kill -0 "${frontend_pid}" 2>/dev/null; then
  exit 0
fi

echo "One application server stopped; shutting down the other."
exit 1
