#!/bin/bash
# Scope the chosen runtime to this gate and all npm child processes.
set -euo pipefail

if [[ -n "${WEB_NODE_BIN:-}" ]]; then
  if [[ ! -x "$WEB_NODE_BIN/node" ]]; then
    echo "WEB_NODE_BIN must contain executable node; use a Node 24 bin directory." >&2
    exit 1
  fi
  export PATH="$WEB_NODE_BIN:$PATH"
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Web gates require Node 24 and npm. Run nvm install && nvm use, or set WEB_NODE_BIN=/path/to/node24/bin." >&2
  exit 1
fi

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
node "$repo_root/web/scripts/check-node-runtime.mjs"
exec npm "$@"
