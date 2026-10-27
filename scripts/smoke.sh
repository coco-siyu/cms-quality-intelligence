#!/usr/bin/env bash

set -euo pipefail

api_url="${CMSQI_SMOKE_API_URL:-http://localhost:8000}"
frontend_url="${CMSQI_SMOKE_FRONTEND_URL:-http://localhost:5173}"

health_response="$(curl --fail --silent --show-error "${api_url}/health")"
if [[ "${health_response}" != *'"status":"ok"'* ]]; then
  echo "API health response was not healthy: ${health_response}" >&2
  exit 1
fi

curl --fail --silent --show-error "${api_url}/api/performance-years" >/dev/null

proxied_health="$(curl --fail --silent --show-error "${frontend_url}/health")"
if [[ "${proxied_health}" != *'"status":"ok"'* ]]; then
  echo "Frontend API proxy did not return a healthy response: ${proxied_health}" >&2
  exit 1
fi
curl --fail --silent --show-error "${frontend_url}/api/performance-years" >/dev/null

homepage="$(curl --fail --silent --show-error "${frontend_url}/")"
if [[ "${homepage}" != *'<div id="root"></div>'* ]]; then
  echo "Frontend response did not contain the application root." >&2
  exit 1
fi

measure_page="$(curl --fail --silent --show-error "${frontend_url}/measures")"
if [[ "${measure_page}" != *'<div id="root"></div>'* ]]; then
  echo "Direct client route did not fall back to the application shell." >&2
  exit 1
fi

echo "Smoke check passed: frontend, API, and database-backed endpoint are available."
