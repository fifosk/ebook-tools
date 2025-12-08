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

parse_bool() {
  local value
  value="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$value" in
    1|true|yes|on) return 0 ;;
    0|false|no|off) return 1 ;;
    *)
      echo "Unrecognised boolean value '$1'" >&2
      return 2
      ;;
  esac
}

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

HTTPS_ENABLED=false
HTTPS_REQUESTED_VIA_ENV=false
DEFAULT_CERT_PATH="${REPO_ROOT}/conf/certs/dev.crt"
DEFAULT_KEY_PATH="${REPO_ROOT}/conf/certs/dev.key"
CERT_PATH="${EBOOK_API_SSL_CERTFILE:-$DEFAULT_CERT_PATH}"
KEY_PATH="${EBOOK_API_SSL_KEYFILE:-$DEFAULT_KEY_PATH}"

if [ -n "${EBOOK_API_ENABLE_HTTPS:-}" ]; then
  HTTPS_REQUESTED_VIA_ENV=true
  if parse_bool "$EBOOK_API_ENABLE_HTTPS"; then
    HTTPS_ENABLED=true
  else
    if [ $? -ne 1 ]; then
      exit 1
    fi
    HTTPS_ENABLED=false
  fi
fi

if [ "$HTTPS_ENABLED" = false ]; then
  if [ -n "${EBOOK_API_SSL_CERTFILE:-}" ] || [ -n "${EBOOK_API_SSL_KEYFILE:-}" ]; then
    HTTPS_ENABLED=true
  elif [ -f "$CERT_PATH" ] && [ -f "$KEY_PATH" ]; then
    HTTPS_ENABLED=true
  fi
fi

if [ "$HTTPS_ENABLED" = true ]; then
  KEY_PASSWORD="${EBOOK_API_SSL_KEYFILE_PASSWORD:-}"

  if [ ! -f "$CERT_PATH" ]; then
    echo "HTTPS enabled but certificate file not found: $CERT_PATH" >&2
    exit 1
  fi
  if [ ! -f "$KEY_PATH" ]; then
    echo "HTTPS enabled but key file not found: $KEY_PATH" >&2
    exit 1
  fi

  set -- "$@" --ssl-certfile "$CERT_PATH" --ssl-keyfile "$KEY_PATH"
  if [ -n "$KEY_PASSWORD" ]; then
    set -- "$@" --ssl-keyfile-password "$KEY_PASSWORD"
  fi

  echo "Starting web API with HTTPS enabled (cert: $CERT_PATH)." >&2
else
  if [ "$HTTPS_REQUESTED_VIA_ENV" = true ]; then
    echo "EBOOK_API_ENABLE_HTTPS is disabled; starting web API without TLS." >&2
  elif [ -f "$DEFAULT_CERT_PATH" ] && [ -f "$DEFAULT_KEY_PATH" ]; then
    echo "Found default certs at ${DEFAULT_CERT_PATH} / ${DEFAULT_KEY_PATH} but HTTPS is off. Set EBOOK_API_ENABLE_HTTPS=1 to enable TLS." >&2
  fi
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
