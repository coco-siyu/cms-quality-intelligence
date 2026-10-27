#!/usr/bin/env bash

set -euo pipefail

for _attempt in $(seq 1 60); do
  if ./scripts/smoke.sh >/dev/null 2>&1; then
    ./scripts/smoke.sh
    exit 0
  fi
  sleep 1
done

echo "The application did not become ready within 60 seconds." >&2
echo "Inspect container output with: docker compose logs" >&2
exit 1
