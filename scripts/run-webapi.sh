#!/usr/bin/env bash
set -euo pipefail

# Determine repository root (directory containing this script's parent).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$REPO_ROOT"

NEEDS_HOST=true
for arg in "$@"; do
  case "$arg" in
    --host|--host=*)
      NEEDS_HOST=false
      break
      ;;
  esac
done

if [ "$NEEDS_HOST" = true ]; then
  set -- --host 0.0.0.0 "$@"
fi

if command -v poetry >/dev/null 2>&1; then
  exec poetry run python -m modules.webapi "$@"
elif command -v pipenv >/dev/null 2>&1; then
  exec pipenv run python -m modules.webapi "$@"
else
  PYTHON_BIN="python"
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  fi
  exec "$PYTHON_BIN" -m modules.webapi "$@"
fi
