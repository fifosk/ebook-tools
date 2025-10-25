#!/usr/bin/env bash
set -euo pipefail

# Determine repository root (directory containing this script's parent).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$REPO_ROOT"

USER_STORE_PATH="${REPO_ROOT}/config/users/users.json"
USER_SAMPLE_PATH="${REPO_ROOT}/config/users/users.sample.json"

if [ ! -f "$USER_STORE_PATH" ] && [ -f "$USER_SAMPLE_PATH" ]; then
  echo "User store not found at ${USER_STORE_PATH}." >&2
  if [ -t 0 ]; then
    read -r -p "Create it from users.sample.json now? [y/N] " response || response=""
    case "${response}" in
      [yY][eE][sS]|[yY])
        cp "$USER_SAMPLE_PATH" "$USER_STORE_PATH"
        echo "Copied template credentials. Update the passwords with 'ebook-tools user password'." >&2
        ;;
      *)
        echo "Skipping automatic copy. Create the file manually before allowing logins." >&2
        ;;
    esac
  else
    echo "Run 'cp config/users/users.sample.json config/users/users.json' and rotate the passwords before continuing." >&2
  fi
fi

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
