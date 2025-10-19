#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WEB_DIR="${REPO_ROOT}/web"

cd "${WEB_DIR}"

if command -v pnpm >/dev/null 2>&1 && [ -f "${WEB_DIR}/pnpm-lock.yaml" ]; then
  exec pnpm run dev -- "$@"
elif command -v yarn >/dev/null 2>&1 && [ -f "${WEB_DIR}/yarn.lock" ]; then
  exec yarn run dev -- "$@"
elif command -v npm >/dev/null 2>&1; then
  exec npm run dev -- "$@"
else
  echo "Error: could not find a supported Node.js package manager (pnpm, yarn, npm)." >&2
  exit 1
fi
