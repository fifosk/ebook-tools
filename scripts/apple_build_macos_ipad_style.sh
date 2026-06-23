#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
XCBUILD="${XCBUILD:-/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild}"
XCPROJ="${XCPROJ:-${ROOT_DIR}/ios/InteractiveReader/InteractiveReader.xcodeproj}"
SCHEME="${SCHEME:-InteractiveReader}"
DERIVED_DATA="${MACOS_IPAD_DERIVED_DATA:-${ROOT_DIR}/test-results/DerivedData-macos-ipad-style}"
CODE_SIGNING_ALLOWED="${CODE_SIGNING_ALLOWED:-NO}"
DESTINATION="${MACOS_IPAD_DESTINATION:-}"
QUIET_FLAG=()
DRY_RUN=0
SHOW_DESTINATION=0

usage() {
  cat <<'EOF'
Usage: scripts/apple_build_macos_ipad_style.sh [--dry-run] [--show-destination]

Build the iOS/iPadOS InteractiveReader target for the local macOS
"Designed for iPad/iPhone" destination. No physical device is used.

Options:
  --dry-run           Print the resolved build command and app path only.
  --show-destination  Print the resolved destination and exit.
  -h, --help          Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --show-destination)
      SHOW_DESTINATION=1
      shift
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

if [[ "${XCODEBUILD_QUIET:-1}" != "0" ]]; then
  QUIET_FLAG=(-quiet)
fi

if [[ -z "${DESTINATION}" ]]; then
  DESTINATION_ID="$(
    "${XCBUILD}" -project "${XCPROJ}" -scheme "${SCHEME}" -showdestinations \
      | python3 -c 'import re, sys
text = sys.stdin.read().splitlines()
for line in text:
    if "platform:macOS" in line and "variant:Designed for [iPad,iPhone]" in line:
        match = re.search(r"id:([^,}]+)", line)
        if match:
            print(match.group(1).strip())
            raise SystemExit(0)
raise SystemExit("No local macOS Designed for iPad/iPhone destination was found.")'
  )"
  DESTINATION="platform=macOS,id=${DESTINATION_ID}"
fi

APP_PATH="$(
  "${XCBUILD}" \
    -project "${XCPROJ}" \
    -scheme "${SCHEME}" \
    -destination "${DESTINATION}" \
    -derivedDataPath "${DERIVED_DATA}" \
    CODE_SIGNING_ALLOWED="${CODE_SIGNING_ALLOWED}" \
    -showBuildSettings \
    | python3 -c 'import sys
settings = {}
for line in sys.stdin:
    if "=" not in line:
        continue
    key, value = line.strip().split("=", 1)
    settings[key.strip()] = value.strip()
products = settings.get("BUILT_PRODUCTS_DIR")
product = settings.get("FULL_PRODUCT_NAME")
if products and product:
    print(f"{products}/{product}")
'
)"
if [[ -z "${APP_PATH}" ]]; then
  APP_PATH="${DERIVED_DATA}/Build/Products/Debug-iphoneos/${SCHEME}.app"
fi

echo "Resolved destination: ${DESTINATION}"
echo "Resolved app path: ${APP_PATH}"

if [[ "${SHOW_DESTINATION}" == "1" ]]; then
  exit 0
fi

BUILD_COMMAND=(
  "${XCBUILD}"
  -project "${XCPROJ}"
  -scheme "${SCHEME}"
  -destination "${DESTINATION}"
  -derivedDataPath "${DERIVED_DATA}"
  CODE_SIGNING_ALLOWED="${CODE_SIGNING_ALLOWED}"
  "${QUIET_FLAG[@]}"
  build
)

if [[ "${DRY_RUN}" == "1" ]]; then
  printf 'Dry run build command:'
  printf ' %q' "${BUILD_COMMAND[@]}"
  printf '\n'
  exit 0
fi

echo "Building ${SCHEME} for ${DESTINATION}"
"${BUILD_COMMAND[@]}"

echo "Built app: ${APP_PATH}"
