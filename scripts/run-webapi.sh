#!/usr/bin/env bash
set -euo pipefail

# Determine repository root (directory containing this script's parent).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$REPO_ROOT"

# Source .env.local if it exists (for local environment variables)
if [ -f "${REPO_ROOT}/.env.local" ]; then
  set -a  # Export all variables defined below
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.env.local"
  set +a
fi

if [ -z "${JOB_STORAGE_DIR:-}" ]; then
  export JOB_STORAGE_DIR="${REPO_ROOT}/storage"
fi

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

BASE_ARGS=("$@")

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

MAIN_ARGS=("$@")

extract_arg_value() {
  local flag="$1"
  shift
  local expect_value=false
  for arg in "$@"; do
    if [ "$expect_value" = true ]; then
      echo "$arg"
      return 0
    fi
    case "$arg" in
      "$flag")
        expect_value=true
        ;;
      "$flag="*)
        echo "${arg#*=}"
        return 0
        ;;
    esac
  done
  return 1
}

MAIN_HOST="$(extract_arg_value --host "${BASE_ARGS[@]}" || true)"
if [ -z "$MAIN_HOST" ]; then
  MAIN_HOST="0.0.0.0"
fi

MAIN_PORT="$(extract_arg_value --port "${BASE_ARGS[@]}" || true)"
if [ -z "$MAIN_PORT" ]; then
  MAIN_PORT="8000"
fi

TV_HTTP_PORT="${EBOOK_API_TV_HTTP_PORT-8001}"
TV_HTTP_HOST="${EBOOK_API_TV_HTTP_HOST:-$MAIN_HOST}"

if command -v poetry >/dev/null 2>&1; then
  RUNNER=(poetry run python -m modules.webapi)
elif command -v pipenv >/dev/null 2>&1; then
  RUNNER=(pipenv run python -m modules.webapi)
else
  PYTHON_BIN="python"
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  fi
  RUNNER=("$PYTHON_BIN" -m modules.webapi)
fi

TV_HTTP_PID=""
if [ -n "$TV_HTTP_PORT" ]; then
  TV_HTTP_PORT_LOWER="$(printf '%s' "$TV_HTTP_PORT" | tr '[:upper:]' '[:lower:]')"
  case "$TV_HTTP_PORT_LOWER" in
    ""|0|false|off|no|disable|disabled)
      TV_HTTP_PORT=""
      ;;
  esac
fi

if [ -n "$TV_HTTP_PORT" ]; then
  if ! printf '%s' "$TV_HTTP_PORT" | grep -Eq '^[0-9]+$'; then
    echo "EBOOK_API_TV_HTTP_PORT must be a numeric port, got '$TV_HTTP_PORT'." >&2
    exit 1
  fi
  if [ "$TV_HTTP_PORT" = "$MAIN_PORT" ]; then
    echo "EBOOK_API_TV_HTTP_PORT matches the main API port ($MAIN_PORT); skipping Apple TV HTTP server." >&2
  else
    TV_ARGS=()
    skip_next=false
    for arg in "${BASE_ARGS[@]}"; do
      if [ "$skip_next" = true ]; then
        skip_next=false
        continue
      fi
      case "$arg" in
        --host|--port|--ssl-certfile|--ssl-keyfile|--ssl-keyfile-password)
          skip_next=true
          continue
          ;;
        --host=*|--port=*|--ssl-certfile=*|--ssl-keyfile=*|--ssl-keyfile-password=*)
          continue
          ;;
      esac
      TV_ARGS+=("$arg")
    done
    TV_ARGS+=(--host "$TV_HTTP_HOST" --port "$TV_HTTP_PORT")
  fi
fi

# Auto-restart support: if EBOOK_API_AUTO_RESTART=1, restart the server when it exits gracefully
AUTO_RESTART="${EBOOK_API_AUTO_RESTART:-1}"
RESTART_DELAY="${EBOOK_API_RESTART_DELAY:-2}"

# Helper to kill any existing processes on a port (cleanup orphans from previous runs)
kill_port() {
  local port="$1"
  local pids
  pids=$(lsof -ti:"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "Killing existing process(es) on port $port: $pids" >&2
    echo "$pids" | xargs kill 2>/dev/null || true
    sleep 0.5
  fi
}

# Clean up any orphaned processes from previous runs
if [ -n "${MAIN_PORT:-}" ]; then
  kill_port "$MAIN_PORT"
fi
if [ -n "${TV_HTTP_PORT:-}" ] && [ "$TV_HTTP_PORT" != "${MAIN_PORT:-}" ]; then
  kill_port "$TV_HTTP_PORT"
fi

# Helper to start TV HTTP server
start_tv_server() {
  if [ -n "${TV_HTTP_PORT:-}" ] && [ "$TV_HTTP_PORT" != "$MAIN_PORT" ]; then
    echo "Starting Apple TV HTTP API on ${TV_HTTP_HOST}:${TV_HTTP_PORT}." >&2
    EBOOK_USE_RAMDISK=0 "${RUNNER[@]}" "${TV_ARGS[@]}" &
    TV_HTTP_PID=$!
  fi
}

# Helper to stop TV HTTP server
stop_tv_server() {
  if [ -n "${TV_HTTP_PID:-}" ] && kill -0 "${TV_HTTP_PID}" 2>/dev/null; then
    kill "${TV_HTTP_PID}" 2>/dev/null || true
    wait "${TV_HTTP_PID}" 2>/dev/null || true
  fi
  TV_HTTP_PID=""
}

# Cleanup function for final exit
cleanup_and_exit() {
  # Kill the main server if running
  if [ -n "${SERVER_PID:-}" ] && kill -0 "${SERVER_PID}" 2>/dev/null; then
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi
  stop_tv_server
  exit 0
}

if [ "$AUTO_RESTART" = "1" ] || [ "$AUTO_RESTART" = "true" ]; then

  # Trap INT for user interrupt (Ctrl+C) - this should exit the script
  trap 'cleanup_and_exit' INT

  # Ignore TERM on the parent script - we want the Python process to receive it
  # but the bash loop should continue running
  trap '' TERM

  # Start TV server initially
  start_tv_server

  while true; do
    # Run the server in foreground - it will receive SIGTERM directly
    "${RUNNER[@]}" "${MAIN_ARGS[@]}" &
    SERVER_PID=$!

    # Wait for the server to exit
    wait $SERVER_PID
    exit_code=$?

    # Exit code 0 = graceful shutdown (SIGTERM), restart
    # Exit code 130 = Ctrl+C (SIGINT), don't restart
    # Exit code 143 = SIGTERM from kill command, restart
    # Other codes = error, don't restart
    case $exit_code in
      0|143)
        echo "Server exited with code $exit_code. Restarting in ${RESTART_DELAY}s..." >&2
        # Stop TV server before restart
        stop_tv_server
        sleep "$RESTART_DELAY"
        # Kill any orphaned processes on ports before restart
        kill_port "$MAIN_PORT"
        if [ -n "${TV_HTTP_PORT:-}" ] && [ "$TV_HTTP_PORT" != "$MAIN_PORT" ]; then
          kill_port "$TV_HTTP_PORT"
        fi
        # Restart TV server
        start_tv_server
        continue
        ;;
      130)
        echo "Server interrupted (Ctrl+C). Exiting." >&2
        cleanup_and_exit
        ;;
      *)
        echo "Server exited with error code $exit_code. Not restarting." >&2
        stop_tv_server
        exit $exit_code
        ;;
    esac
  done
else
  # Original behavior: run once and exit
  # Set up trap for cleanup on exit
  if [ -n "${TV_HTTP_PORT:-}" ] && [ "$TV_HTTP_PORT" != "$MAIN_PORT" ]; then
    echo "Starting Apple TV HTTP API on ${TV_HTTP_HOST}:${TV_HTTP_PORT}." >&2
    EBOOK_USE_RAMDISK=0 "${RUNNER[@]}" "${TV_ARGS[@]}" &
    TV_HTTP_PID=$!
    trap 'stop_tv_server' EXIT INT TERM
  fi

  exec "${RUNNER[@]}" "${MAIN_ARGS[@]}"
fi
