#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
XCBUILD="${XCBUILD:-/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild}"
DEVICECTL="${DEVICECTL:-$(xcrun --find devicectl)}"
XCPROJ="${XCPROJ:-${ROOT_DIR}/ios/InteractiveReader/InteractiveReader.xcodeproj}"
SCHEME="${SCHEME:-InteractiveReader}"
BUNDLE_ID="${BUNDLE_ID:-com.example.InteractiveReader}"
DEVICE_ID="${APPLE_DEVICE_ID:-}"
DERIVED_DATA="${APPLE_DEVICE_DERIVED_DATA:-}"
INSTALL=0
LAUNCH=0
DRY_RUN=0
LIST=0

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/apple_unattended_device_update.sh --list
  APPLE_DEVICE_ID=<udid-or-coredevice-id> bash scripts/apple_unattended_device_update.sh --build-only
  APPLE_DEVICE_ID=<udid-or-coredevice-id> CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
    bash scripts/apple_unattended_device_update.sh --install [--launch]

Options:
  --list        List devices known to devicectl and exit.
  --build-only  Build for the requested iPhone/iPad destination, but do not install.
  --install     Build and install the app with devicectl. Requires CONFIRM_PHYSICAL_DEVICE_UPDATE=YES.
  --launch      Launch the installed app after install.
  --dry-run     Print the commands that would run, then exit without building or installing.
  --device ID   Device identifier, ECID, serial, UDID, CoreDevice id, or name.
USAGE
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
    --install)
      INSTALL=1
      shift
      ;;
    --launch)
      LAUNCH=1
      shift
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

APP_PATH="${DERIVED_DATA}/Build/Products/Debug-iphoneos/InteractiveReader.app"
BUILD_CMD=(
  "${XCBUILD}"
  -project "${XCPROJ}"
  -scheme "${SCHEME}"
  -destination "id=${DEVICE_ID}"
  -derivedDataPath "${DERIVED_DATA}"
  build
)
INSTALL_CMD=("${DEVICECTL}" device install app --device "${DEVICE_ID}" "${APP_PATH}")
LAUNCH_CMD=("${DEVICECTL}" device process launch --terminate-existing --device "${DEVICE_ID}" "${BUNDLE_ID}")

echo "Build command:"
printf '  %q' "${BUILD_CMD[@]}"
echo

if [[ "${INSTALL}" == "1" ]]; then
  echo "Install command:"
  printf '  %q' "${INSTALL_CMD[@]}"
  echo
  if [[ "${LAUNCH}" == "1" ]]; then
    echo "Launch command:"
    printf '  %q' "${LAUNCH_CMD[@]}"
    echo
  fi
fi

if [[ "${DRY_RUN}" == "1" ]]; then
  exit 0
fi

if [[ "${INSTALL}" == "1" && "${CONFIRM_PHYSICAL_DEVICE_UPDATE:-}" != "YES" ]]; then
  echo "Refusing to install to a physical device without CONFIRM_PHYSICAL_DEVICE_UPDATE=YES." >&2
  exit 2
fi

"${BUILD_CMD[@]}"

if [[ "${INSTALL}" != "1" ]]; then
  echo "Built app: ${APP_PATH}"
  exit 0
fi

"${INSTALL_CMD[@]}"

if [[ "${LAUNCH}" == "1" ]]; then
  "${LAUNCH_CMD[@]}"
fi
