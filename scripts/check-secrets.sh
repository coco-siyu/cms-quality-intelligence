#!/usr/bin/env bash

set -euo pipefail

if ! git check-ignore --quiet .env; then
  echo ".env must remain ignored by Git." >&2
  exit 1
fi

if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo ".env is tracked and may expose local credentials." >&2
  exit 1
fi

patterns='AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'
matches="$(
  rg --line-number --hidden \
    --glob '!.git/**' \
    --glob '!.env' \
    --glob '!frontend/node_modules/**' \
    --glob '!frontend/dist/**' \
    --glob '!backend/.venv/**' \
    --glob '!backend/.pytest_cache/**' \
    --glob '!backend/.ruff_cache/**' \
    --regexp "${patterns}" . || true
)"

if [[ -n "${matches}" ]]; then
  echo "Potential credential material was found:" >&2
  echo "${matches}" >&2
  exit 1
fi

echo "Secret guard passed: .env is untracked and no high-signal key patterns were found."
