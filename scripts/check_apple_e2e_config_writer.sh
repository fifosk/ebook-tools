#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HELPER="${ROOT_DIR}/scripts/write_apple_e2e_config.py"
TMP_DIR="$(mktemp -d /tmp/ebook-tools-apple-e2e-config.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT

ENV_FILE="${TMP_DIR}/quoted.env"
CONFIG_PATH="${TMP_DIR}/profile/ios_e2e_config.json"
JOURNEY_SRC="${TMP_DIR}/create_readiness.json"
JOURNEY_PATH="${TMP_DIR}/profile/ios_e2e_journey.json"

cat > "${ENV_FILE}" <<'EOF'
E2E_USERNAME='editor'
E2E_PASSWORD="secret"
E2E_API_BASE_URL='https://quoted.example/'
EOF
cat > "${JOURNEY_SRC}" <<'EOF'
{"id":"create_readiness","steps":[]}
EOF

python3 -m py_compile "${HELPER}"
python3 "${HELPER}" \
  --env-file "${ENV_FILE}" \
  --config-path "${CONFIG_PATH}" \
  --journey-src "${JOURNEY_SRC}" \
  --journey-path "${JOURNEY_PATH}"

python3 -m json.tool "${CONFIG_PATH}" >/dev/null
python3 -m json.tool "${JOURNEY_PATH}" >/dev/null

python3 - "${CONFIG_PATH}" "${JOURNEY_SRC}" "${JOURNEY_PATH}" <<'PY'
import json
import sys
from pathlib import Path

config_path, journey_src, journey_path = map(Path, sys.argv[1:])
config = json.loads(config_path.read_text(encoding="utf-8"))
assert config == {
    "profile": "profile",
    "username": "editor",
    "password": "secret",
    "api_base_url": "https://quoted.example/",
    "allow_restored_session": False,
}, config
assert journey_path.read_text(encoding="utf-8") == journey_src.read_text(encoding="utf-8")
PY

E2E_USERNAME=env-user \
E2E_PASSWORD=env-secret \
E2E_API_BASE_URL=https://env.example \
E2E_ALLOW_RESTORED_SESSION=1 \
python3 "${HELPER}" \
  --env-file "${ENV_FILE}" \
  --config-path "${CONFIG_PATH}" \
  --journey-src "${JOURNEY_SRC}" \
  --journey-path "${JOURNEY_PATH}"

python3 - "${CONFIG_PATH}" <<'PY'
import json
import sys
from pathlib import Path

config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert config == {
    "profile": "profile",
    "username": "env-user",
    "password": "env-secret",
    "api_base_url": "https://env.example",
    "allow_restored_session": True,
}, config
PY

echo "apple e2e config writer checks passed"
