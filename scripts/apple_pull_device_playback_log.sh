#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEVICECTL="${DEVICECTL:-/Applications/Xcode.app/Contents/Developer/usr/bin/devicectl}"
DEVICE_ID="${APPLE_DEVICE_ID:-}"
DEVICE_PROFILE="${APPLE_DEVICE_PROFILE:-ipad}"
OUTPUT_PATH="${APPLE_DEVICE_PLAYBACK_LOG:-}"
TIMEOUT="${APPLE_DEVICE_COPY_TIMEOUT:-60}"

usage() {
  cat <<'USAGE'
Usage: scripts/apple_pull_device_playback_log.sh --device DEVICE [--profile ipad|iphone|appletv] [--output PATH]

Pulls the DEBUG playback transport breadcrumb file from a physical Apple app
container after a manual repro. The file is token-safe and contains transport
state only, not book text or media titles.

Environment equivalents:
  APPLE_DEVICE_ID, APPLE_DEVICE_PROFILE, APPLE_DEVICE_PLAYBACK_LOG,
  APPLE_DEVICE_COPY_TIMEOUT, DEVICECTL
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device)
      DEVICE_ID="${2:-}"
      shift 2
      ;;
    --profile)
      DEVICE_PROFILE="${2:-}"
      shift 2
      ;;
    --output)
      OUTPUT_PATH="${2:-}"
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

if [[ -z "${DEVICE_ID}" ]]; then
  echo "Missing --device or APPLE_DEVICE_ID." >&2
  exit 2
fi

case "${DEVICE_PROFILE}" in
  appletv|tvos)
    BUNDLE_ID="com.example.InteractiveReader.tvos"
    SAFE_PROFILE="appletv"
    ;;
  ipad|iphone|ios)
    BUNDLE_ID="com.example.InteractiveReader"
    SAFE_PROFILE="${DEVICE_PROFILE}"
    ;;
  *)
    echo "Unsupported profile: ${DEVICE_PROFILE}" >&2
    exit 2
    ;;
esac

safe_device="$(printf '%s' "${DEVICE_ID}" | tr -c 'A-Za-z0-9._-' '-' | sed -e 's/^-*//' -e 's/-*$//')"
if [[ -z "${safe_device}" ]]; then
  safe_device="device"
fi

if [[ -z "${OUTPUT_PATH}" ]]; then
  OUTPUT_PATH="${ROOT_DIR}/test-results/apple-device-playback-transport-${safe_device}.log"
fi
JSON_PATH="${OUTPUT_PATH%.log}.json"
COREDEVICE_LOG="${OUTPUT_PATH%.log}.coredevice.log"
mkdir -p "$(dirname "${OUTPUT_PATH}")"

"${DEVICECTL}" device copy from \
  --device "${DEVICE_ID}" \
  --source "Library/Caches/interactive-reader-playback-transport.log" \
  --destination "${OUTPUT_PATH}" \
  --domain-type appDataContainer \
  --domain-identifier "${BUNDLE_ID}" \
  --timeout "${TIMEOUT}" \
  --json-output "${JSON_PATH}" \
  --log-output "${COREDEVICE_LOG}"

echo "Playback transport log pulled for ${DEVICE_ID} (${SAFE_PROFILE}): ${OUTPUT_PATH}"
