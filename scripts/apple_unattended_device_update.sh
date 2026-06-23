#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
XCBUILD="${XCBUILD:-/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild}"
DEVICECTL="${DEVICECTL:-$(xcrun --find devicectl)}"
XCPROJ="${XCPROJ:-${ROOT_DIR}/ios/InteractiveReader/InteractiveReader.xcodeproj}"
SCHEME="${SCHEME:-InteractiveReader}"
CONFIGURATION="${CONFIGURATION:-Debug}"
PRODUCT_NAME="${PRODUCT_NAME:-InteractiveReader}"
BUNDLE_ID="${BUNDLE_ID:-com.example.InteractiveReader}"
DEVICE_ID="${APPLE_DEVICE_ID:-}"
DERIVED_DATA="${APPLE_DEVICE_DERIVED_DATA:-}"
APP_PATH="${APPLE_DEVICE_APP_PATH:-}"
DEVELOPMENT_TEAM="${APPLE_DEVELOPMENT_TEAM:-}"
DEVICECTL_TIMEOUT="${APPLE_DEVICECTL_TIMEOUT:-60}"
ALLOW_PROVISIONING_UPDATES="${ALLOW_PROVISIONING_UPDATES:-0}"
INSTALL=0
LAUNCH=0
DRY_RUN=0
LIST=0
SKIP_BUILD=0
VERIFY_AFTER_INSTALL=1
VERIFY_ONLY=0
PREFLIGHT_ONLY=0

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/apple_unattended_device_update.sh --list
  APPLE_DEVICE_ID=<udid-or-coredevice-id> bash scripts/apple_unattended_device_update.sh --device-preflight-only
  APPLE_DEVICE_ID=<udid-or-coredevice-id> bash scripts/apple_unattended_device_update.sh --verify-installed
  APPLE_DEVICE_ID=<udid-or-coredevice-id> bash scripts/apple_unattended_device_update.sh --build-only
  APPLE_DEVICE_ID=<udid-or-coredevice-id> CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
    bash scripts/apple_unattended_device_update.sh --install [--launch]

Options:
  --list                         List devices known to devicectl and exit.
  --device-preflight-only        Query the device through devicectl without building or installing.
  --verify-installed             Query installed app metadata for BUNDLE_ID and exit.
  --build-only, --signed-build-only
                                 Build for the requested iPhone/iPad destination, but do not install.
  --install                      Build and install the app with devicectl. Requires CONFIRM_PHYSICAL_DEVICE_UPDATE=YES.
  --skip-build                   Install the existing --app-path/APPLE_DEVICE_APP_PATH without rebuilding.
  --app-path PATH                App bundle to install or verify after a skipped build.
  --launch                       Launch the installed app after install.
  --no-verify                    Skip post-install app metadata verification.
  --allow-provisioning-updates   Pass -allowProvisioningUpdates to xcodebuild.
  --team-id TEAMID               Pass DEVELOPMENT_TEAM=TEAMID to xcodebuild.
  --configuration NAME           Xcode configuration. Defaults to Debug.
  --dry-run                      Print the commands that would run, then exit without building or installing.
  --device ID                    Device identifier, ECID, serial, UDID, CoreDevice id, or name.

Environment:
  CONFIRM_PHYSICAL_DEVICE_UPDATE=YES is required for --install.
  APPLE_DEVICE_ID, APPLE_DEVICE_APP_PATH, APPLE_DEVELOPMENT_TEAM,
  APPLE_DEVICE_DERIVED_DATA, APPLE_DEVICECTL_TIMEOUT, XCBUILD, DEVICECTL,
  XCPROJ, SCHEME, CONFIGURATION, PRODUCT_NAME, and BUNDLE_ID override defaults.
USAGE
}

print_command() {
  local label="$1"
  shift
  echo "${label}:"
  printf '  %q' "$@"
  echo
}

json_scratch_path() {
  local name="$1"
  local safe_id
  safe_id="$(python3 -c 'import re, sys; print(re.sub(r"[^A-Za-z0-9._-]+", "-", sys.argv[1]).strip("-") or "device")' "${DEVICE_ID}")"
  echo "${ROOT_DIR}/test-results/${name}-${safe_id}.json"
}

summarize_installed_app_json() {
  local json_path="$1"
  python3 - "$json_path" "$BUNDLE_ID" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
bundle_id = sys.argv[2]

try:
    payload = json.loads(path.read_text())
except Exception as exc:
    raise SystemExit(f"Unable to read devicectl JSON output at {path}: {exc}")

matches = []

def walk(value):
    if isinstance(value, dict):
        values = {str(v) for v in value.values() if isinstance(v, (str, int, float))}
        if bundle_id in values:
            matches.append(value)
        for child in value.values():
            walk(child)
    elif isinstance(value, list):
        for child in value:
            walk(child)

walk(payload)

if not matches:
    raise SystemExit(f"Installed app metadata for {bundle_id} was not found.")

app = matches[0]

def pick(*keys):
    for key in keys:
        value = app.get(key)
        if isinstance(value, (str, int, float)) and str(value).strip():
            return str(value)
    return "unknown"

name = pick("name", "localizedName", "bundleName")
version = pick("version", "shortVersionString", "CFBundleShortVersionString")
build = pick("bundleVersion", "buildVersion", "CFBundleVersion")
print(f"Verified installed app: {name} {bundle_id} version={version} build={build}")
PY
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list)
      LIST=1
      shift
      ;;
    --build-only)
      INSTALL=0
      shift
      ;;
    --signed-build-only)
      INSTALL=0
      shift
      ;;
    --install)
      INSTALL=1
      shift
      ;;
    --skip-build)
      SKIP_BUILD=1
      shift
      ;;
    --app-path)
      APP_PATH="${2:-}"
      shift 2
      ;;
    --launch)
      LAUNCH=1
      shift
      ;;
    --no-verify)
      VERIFY_AFTER_INSTALL=0
      shift
      ;;
    --verify-installed|--verify-only)
      VERIFY_ONLY=1
      shift
      ;;
    --device-preflight-only|--preflight-only)
      PREFLIGHT_ONLY=1
      shift
      ;;
    --allow-provisioning-updates)
      ALLOW_PROVISIONING_UPDATES=1
      shift
      ;;
    --team-id)
      DEVELOPMENT_TEAM="${2:-}"
      shift 2
      ;;
    --configuration)
      CONFIGURATION="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --device)
      DEVICE_ID="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "${LIST}" == "1" ]]; then
  "${DEVICECTL}" list devices
  exit 0
fi

if [[ -z "${DEVICE_ID}" ]]; then
  echo "APPLE_DEVICE_ID or --device is required for unattended device updates." >&2
  usage >&2
  exit 2
fi

if [[ -z "${DERIVED_DATA}" ]]; then
  SAFE_ID="$(python3 -c 'import re, sys; print(re.sub(r"[^A-Za-z0-9._-]+", "-", sys.argv[1]).strip("-") or "device")' "${DEVICE_ID}")"
  DERIVED_DATA="${ROOT_DIR}/test-results/DerivedData-device-${SAFE_ID}"
fi

if [[ -z "${APP_PATH}" ]]; then
  APP_PATH="${DERIVED_DATA}/Build/Products/${CONFIGURATION}-iphoneos/${PRODUCT_NAME}.app"
fi

VERIFY_JSON="$(json_scratch_path apple-device-installed-app)"
INSTALL_JSON="$(json_scratch_path apple-device-install)"
LAUNCH_JSON="$(json_scratch_path apple-device-launch)"

BUILD_CMD=(
  "${XCBUILD}"
  -project "${XCPROJ}"
  -scheme "${SCHEME}"
  -configuration "${CONFIGURATION}"
  -destination "id=${DEVICE_ID}"
  -derivedDataPath "${DERIVED_DATA}"
)
if [[ "${ALLOW_PROVISIONING_UPDATES}" == "1" ]]; then
  BUILD_CMD+=(-allowProvisioningUpdates)
fi
if [[ -n "${DEVELOPMENT_TEAM}" ]]; then
  BUILD_CMD+=("DEVELOPMENT_TEAM=${DEVELOPMENT_TEAM}")
fi
BUILD_CMD+=(build)

INSTALL_CMD=(
  "${DEVICECTL}" device install app
  --device "${DEVICE_ID}"
  "${APP_PATH}"
  --timeout "${DEVICECTL_TIMEOUT}"
  --json-output "${INSTALL_JSON}"
)
VERIFY_CMD=(
  "${DEVICECTL}" device info apps
  --device "${DEVICE_ID}"
  --bundle-id "${BUNDLE_ID}"
  --timeout "${DEVICECTL_TIMEOUT}"
  --json-output "${VERIFY_JSON}"
)
LAUNCH_CMD=(
  "${DEVICECTL}" device process launch
  --terminate-existing
  --device "${DEVICE_ID}"
  --timeout "${DEVICECTL_TIMEOUT}"
  --json-output "${LAUNCH_JSON}"
  "${BUNDLE_ID}"
)

if [[ "${PREFLIGHT_ONLY}" == "1" ]]; then
  print_command "Device preflight command" "${VERIFY_CMD[@]}"
  if [[ "${DRY_RUN}" == "1" ]]; then
    exit 0
  fi
  mkdir -p "$(dirname "${VERIFY_JSON}")"
  "${VERIFY_CMD[@]}" || {
    echo "Device preflight failed. Confirm the device is connected, awake, trusted, and visible to CoreDevice." >&2
    exit 1
  }
  echo "Device preflight passed for ${DEVICE_ID}."
  exit 0
fi

if [[ "${VERIFY_ONLY}" == "1" ]]; then
  print_command "Installed app verification command" "${VERIFY_CMD[@]}"
  if [[ "${DRY_RUN}" == "1" ]]; then
    exit 0
  fi
  mkdir -p "$(dirname "${VERIFY_JSON}")"
  "${VERIFY_CMD[@]}"
  summarize_installed_app_json "${VERIFY_JSON}"
  exit 0
fi

if [[ "${SKIP_BUILD}" != "1" ]]; then
  print_command "Build command" "${BUILD_CMD[@]}"
fi

if [[ "${INSTALL}" == "1" ]]; then
  print_command "Install command" "${INSTALL_CMD[@]}"
  if [[ "${VERIFY_AFTER_INSTALL}" == "1" ]]; then
    print_command "Post-install verification command" "${VERIFY_CMD[@]}"
  fi
fi

if [[ "${INSTALL}" == "1" && "${LAUNCH}" == "1" ]]; then
  print_command "Launch command" "${LAUNCH_CMD[@]}"
fi

if [[ "${DRY_RUN}" == "1" ]]; then
  exit 0
fi

if [[ "${INSTALL}" == "1" && "${CONFIRM_PHYSICAL_DEVICE_UPDATE:-}" != "YES" ]]; then
  echo "Refusing to install to a physical device without CONFIRM_PHYSICAL_DEVICE_UPDATE=YES." >&2
  exit 2
fi

mkdir -p "$(dirname "${INSTALL_JSON}")"

if [[ "${SKIP_BUILD}" != "1" ]]; then
  "${BUILD_CMD[@]}"
fi

if [[ "${INSTALL}" != "1" ]]; then
  if [[ "${SKIP_BUILD}" == "1" ]]; then
    echo "Skipped build. App path: ${APP_PATH}"
  else
    echo "Built app: ${APP_PATH}"
  fi
  exit 0
fi

if [[ ! -d "${APP_PATH}" ]]; then
  echo "App bundle not found: ${APP_PATH}" >&2
  exit 1
fi

"${INSTALL_CMD[@]}"

if [[ "${VERIFY_AFTER_INSTALL}" == "1" ]]; then
  "${VERIFY_CMD[@]}"
  summarize_installed_app_json "${VERIFY_JSON}"
fi

if [[ "${LAUNCH}" == "1" ]]; then
  "${LAUNCH_CMD[@]}"
fi
