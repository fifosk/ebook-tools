#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
XCBUILD="${XCBUILD:-/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild}"
CODESIGN="${CODESIGN:-/usr/bin/codesign}"
XCPROJ="${XCPROJ:-${ROOT_DIR}/ios/InteractiveReader/InteractiveReader.xcodeproj}"
SCHEME="${SCHEME:-InteractiveReader}"
CONFIGURATION="${CONFIGURATION:-Debug}"
DERIVED_DATA="${APPLE_DEVICE_DERIVED_DATA:-${ROOT_DIR}/test-results/DerivedData-device-full-entitlements}"
APP_PRODUCT_NAME="${PRODUCT_NAME:-InteractiveReader}"
APP_BUNDLE_ID="${BUNDLE_ID:-com.example.InteractiveReader}"
EXTENSION_PRODUCT_NAME="${APPLE_EXTENSION_PRODUCT_NAME:-NotificationServiceExtension}"
EXTENSION_BUNDLE_ID="${APPLE_EXTENSION_BUNDLE_ID:-com.example.InteractiveReader.NotificationServiceExtension}"
APP_ENTITLEMENTS="${APP_ENTITLEMENTS_PLIST:-${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Supporting/InteractiveReader.entitlements}"
EXTENSION_ENTITLEMENTS="${EXTENSION_ENTITLEMENTS_PLIST:-}"
MERGED_APP_ENTITLEMENTS="${APPLE_MERGED_APP_ENTITLEMENTS_PLIST:-}"
MERGED_EXTENSION_ENTITLEMENTS="${APPLE_MERGED_EXTENSION_ENTITLEMENTS_PLIST:-}"
APP_PROFILE="${FULL_CAPABILITY_IOS_PROFILE:-}"
EXTENSION_PROFILE="${WILDCARD_IOS_EXTENSION_PROFILE:-}"
SIGNING_IDENTITY="${APPLE_DEVELOPMENT_IDENTITY:-}"
DEVICE_ID="${APPLE_DEVICE_ID:-}"
LAUNCH_CONSOLE_TIMEOUT="${APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT:-10}"
EXECUTE=0
INSTALL=0

usage() {
  cat <<'USAGE'
Usage:
  APPLE_DEVICE_ID=<device-id-or-name> \
  FULL_CAPABILITY_IOS_PROFILE=/path/app.mobileprovision \
  WILDCARD_IOS_EXTENSION_PROFILE=/path/extension.mobileprovision \
  APPLE_DEVELOPMENT_IDENTITY="Apple Development: Name (TEAMID)" \
    bash scripts/apple_full_entitlement_signing_plan.sh

Options:
  --device ID                    Device identifier or name for the final guarded install command.
  --app-profile PATH             Full-capability iOS provisioning profile for InteractiveReader.app.
  --extension-profile PATH       Wildcard or exact profile for NotificationServiceExtension.appex.
  --signing-identity NAME        codesign identity to use for app, extension, and nested dylibs.
  --app-entitlements PATH        App entitlements plist. Defaults to InteractiveReader.entitlements.
  --extension-entitlements PATH  Optional extension project entitlements plist. Omitted by default.
  --merged-app-entitlements PATH Generated app entitlements output path.
  --merged-extension-entitlements PATH
                                 Generated extension entitlements output path.
  --derived-data PATH            DerivedData folder for the unsigned device build.
  --configuration NAME           Xcode configuration. Defaults to Debug.
  --launch-console-timeout SEC   Final launch-console timeout. Defaults to 10.
  --execute                      Run the printed build/sign/verify flow, without installing.
  --install                      With --execute, run the guarded physical-device install handoff.
  -h, --help                     Show this help.

Environment aliases:
  APPLE_DEVICE_ID, FULL_CAPABILITY_IOS_PROFILE, WILDCARD_IOS_EXTENSION_PROFILE,
  APPLE_DEVELOPMENT_IDENTITY, APP_ENTITLEMENTS_PLIST, EXTENSION_ENTITLEMENTS_PLIST,
  APPLE_MERGED_APP_ENTITLEMENTS_PLIST, APPLE_MERGED_EXTENSION_ENTITLEMENTS_PLIST,
  APPLE_DEVICE_DERIVED_DATA, APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT, XCBUILD, XCPROJ,
  SCHEME, CONFIGURATION, PRODUCT_NAME, BUNDLE_ID, APPLE_EXTENSION_PRODUCT_NAME,
  and APPLE_EXTENSION_BUNDLE_ID.

This planner is non-mutating by default: it validates required inputs and
prints the full-entitlement build, profile embedding, codesign, verify, and
guarded skip-build install commands. Add --execute to build/sign/verify, and
add --install only after an explicit physical-device deploy request.
USAGE
}

print_command() {
  local label="$1"
  shift
  echo "${label}:"
  printf '  %q' "$@"
  echo
}

require_file() {
  local label="$1"
  local path="$2"
  if [[ -z "${path}" ]]; then
    echo "${label} is required." >&2
    exit 2
  fi
  if [[ ! -f "${path}" ]]; then
    echo "${label} not found: ${path}" >&2
    exit 2
  fi
}

require_value() {
  local label="$1"
  local value="$2"
  if [[ -z "${value}" ]]; then
    echo "${label} is required." >&2
    exit 2
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device)
      DEVICE_ID="${2:-}"
      shift 2
      ;;
    --app-profile)
      APP_PROFILE="${2:-}"
      shift 2
      ;;
    --extension-profile)
      EXTENSION_PROFILE="${2:-}"
      shift 2
      ;;
    --signing-identity)
      SIGNING_IDENTITY="${2:-}"
      shift 2
      ;;
    --app-entitlements)
      APP_ENTITLEMENTS="${2:-}"
      shift 2
      ;;
    --extension-entitlements)
      EXTENSION_ENTITLEMENTS="${2:-}"
      shift 2
      ;;
    --merged-app-entitlements)
      MERGED_APP_ENTITLEMENTS="${2:-}"
      shift 2
      ;;
    --merged-extension-entitlements)
      MERGED_EXTENSION_ENTITLEMENTS="${2:-}"
      shift 2
      ;;
    --derived-data)
      DERIVED_DATA="${2:-}"
      shift 2
      ;;
    --configuration)
      CONFIGURATION="${2:-}"
      shift 2
      ;;
    --launch-console-timeout)
      LAUNCH_CONSOLE_TIMEOUT="${2:-}"
      shift 2
      ;;
    --execute)
      EXECUTE=1
      shift
      ;;
    --install)
      INSTALL=1
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

if [[ "${INSTALL}" == "1" && "${EXECUTE}" != "1" ]]; then
  echo "--install requires --execute." >&2
  exit 2
fi

require_value "APPLE_DEVICE_ID or --device" "${DEVICE_ID}"
require_value "APPLE_DEVELOPMENT_IDENTITY or --signing-identity" "${SIGNING_IDENTITY}"
require_file "FULL_CAPABILITY_IOS_PROFILE or --app-profile" "${APP_PROFILE}"
require_file "WILDCARD_IOS_EXTENSION_PROFILE or --extension-profile" "${EXTENSION_PROFILE}"
require_file "APP_ENTITLEMENTS_PLIST or --app-entitlements" "${APP_ENTITLEMENTS}"
if [[ -n "${EXTENSION_ENTITLEMENTS}" ]]; then
  require_file "EXTENSION_ENTITLEMENTS_PLIST or --extension-entitlements" "${EXTENSION_ENTITLEMENTS}"
fi

APP_PATH="${DERIVED_DATA}/Build/Products/${CONFIGURATION}-iphoneos/${APP_PRODUCT_NAME}.app"
APPEX_PATH="${APP_PATH}/PlugIns/${EXTENSION_PRODUCT_NAME}.appex"
if [[ -z "${MERGED_APP_ENTITLEMENTS}" ]]; then
  MERGED_APP_ENTITLEMENTS="${DERIVED_DATA}/MergedEntitlements/${APP_PRODUCT_NAME}.entitlements.plist"
fi
if [[ -z "${MERGED_EXTENSION_ENTITLEMENTS}" ]]; then
  MERGED_EXTENSION_ENTITLEMENTS="${DERIVED_DATA}/MergedEntitlements/${EXTENSION_PRODUCT_NAME}.entitlements.plist"
fi

BUILD_CMD=(
  "${XCBUILD}"
  -project "${XCPROJ}"
  -scheme "${SCHEME}"
  -configuration "${CONFIGURATION}"
  -destination "generic/platform=iOS"
  -derivedDataPath "${DERIVED_DATA}"
  CODE_SIGNING_ALLOWED=NO
  build
)
PROFILE_APP_CMD=(cp "${APP_PROFILE}" "${APP_PATH}/embedded.mobileprovision")
PROFILE_EXTENSION_CMD=(cp "${EXTENSION_PROFILE}" "${APPEX_PATH}/embedded.mobileprovision")
MERGE_APP_ENTITLEMENTS_CMD=(
  python3
  "${ROOT_DIR}/scripts/apple_merge_entitlements.py"
  --profile "${APP_PROFILE}"
  --bundle-id "${APP_BUNDLE_ID}"
  --project-entitlements "${APP_ENTITLEMENTS}"
  --output "${MERGED_APP_ENTITLEMENTS}"
)
MERGE_EXTENSION_ENTITLEMENTS_CMD=(
  python3
  "${ROOT_DIR}/scripts/apple_merge_entitlements.py"
  --profile "${EXTENSION_PROFILE}"
  --bundle-id "${EXTENSION_BUNDLE_ID}"
  --output "${MERGED_EXTENSION_ENTITLEMENTS}"
)
if [[ -n "${EXTENSION_ENTITLEMENTS}" ]]; then
  MERGE_EXTENSION_ENTITLEMENTS_CMD+=(--project-entitlements "${EXTENSION_ENTITLEMENTS}")
fi
SIGN_EXTENSION_DYLIBS_CMD=(
  find "${APPEX_PATH}" -maxdepth 1 -type f -name "*.dylib" -print0
)
SIGN_APP_DYLIBS_CMD=(
  find "${APP_PATH}" -maxdepth 1 -type f -name "*.dylib" -print0
)
SIGN_EXTENSION_CMD=("${CODESIGN}" --force --sign "${SIGNING_IDENTITY}" --timestamp=none)
SIGN_EXTENSION_CMD+=(--entitlements "${MERGED_EXTENSION_ENTITLEMENTS}")
SIGN_EXTENSION_CMD+=("${APPEX_PATH}")
SIGN_APP_CMD=(
  "${CODESIGN}"
  --force
  --sign "${SIGNING_IDENTITY}"
  --timestamp=none
  --entitlements "${MERGED_APP_ENTITLEMENTS}"
  "${APP_PATH}"
)
VERIFY_CMD=("${CODESIGN}" --verify --deep --strict --verbose=4 "${APP_PATH}")
INSTALL_CMD=(
  bash "${ROOT_DIR}/scripts/apple_unattended_device_update.sh"
  --device "${DEVICE_ID}"
  --profile ipad
  --skip-build
  --app-path "${APP_PATH}"
  --install
  --launch
  --launch-console-timeout "${LAUNCH_CONSOLE_TIMEOUT}"
)

cat <<EOF
Full-entitlement iPhone/iPad signing plan
App bundle id: ${APP_BUNDLE_ID}
Extension bundle id: ${EXTENSION_BUNDLE_ID}
Unsigned build app path: ${APP_PATH}
Notification extension path: ${APPEX_PATH}

EOF

print_command "Unsigned device build" "${BUILD_CMD[@]}"
print_command "Generate merged app entitlements" "${MERGE_APP_ENTITLEMENTS_CMD[@]}"
print_command "Generate merged extension entitlements" "${MERGE_EXTENSION_ENTITLEMENTS_CMD[@]}"
print_command "Embed app provisioning profile" "${PROFILE_APP_CMD[@]}"
print_command "Embed extension provisioning profile" "${PROFILE_EXTENSION_CMD[@]}"
echo "Sign extension dylibs:"
printf '  %q' "${SIGN_EXTENSION_DYLIBS_CMD[@]}"
printf ' | xargs -0 -I{} %q --force --sign %q --timestamp=none "{}"\n' "${CODESIGN}" "${SIGNING_IDENTITY}"
print_command "Sign notification extension" "${SIGN_EXTENSION_CMD[@]}"
echo "Sign app dylibs:"
printf '  %q' "${SIGN_APP_DYLIBS_CMD[@]}"
printf ' | xargs -0 -I{} %q --force --sign %q --timestamp=none "{}"\n' "${CODESIGN}" "${SIGNING_IDENTITY}"
print_command "Sign app with full entitlements" "${SIGN_APP_CMD[@]}"
print_command "Verify signed app" "${VERIFY_CMD[@]}"
echo "Final guarded install command:"
echo "  CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \\"
printf '  %q' "${INSTALL_CMD[@]}"
echo

if [[ "${EXECUTE}" != "1" ]]; then
  exit 0
fi

echo
echo "Executing full-entitlement build/sign flow..."
"${BUILD_CMD[@]}"
"${MERGE_APP_ENTITLEMENTS_CMD[@]}"
"${MERGE_EXTENSION_ENTITLEMENTS_CMD[@]}"
"${PROFILE_APP_CMD[@]}"
"${PROFILE_EXTENSION_CMD[@]}"
find "${APPEX_PATH}" -maxdepth 1 -type f -name "*.dylib" -print0 \
  | while IFS= read -r -d '' dylib_path; do
      "${CODESIGN}" --force --sign "${SIGNING_IDENTITY}" --timestamp=none "${dylib_path}"
    done
"${SIGN_EXTENSION_CMD[@]}"
find "${APP_PATH}" -maxdepth 1 -type f -name "*.dylib" -print0 \
  | while IFS= read -r -d '' dylib_path; do
      "${CODESIGN}" --force --sign "${SIGNING_IDENTITY}" --timestamp=none "${dylib_path}"
    done
"${SIGN_APP_CMD[@]}"
"${VERIFY_CMD[@]}"

if [[ "${INSTALL}" == "1" ]]; then
  "${INSTALL_CMD[@]}"
else
  echo "Built and signed app: ${APP_PATH}"
fi
