#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
XCBUILD="${XCBUILD:-/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild}"
DEVICECTL="${DEVICECTL:-$(xcrun --find devicectl)}"
CODESIGN="${CODESIGN:-/usr/bin/codesign}"
XCPROJ="${XCPROJ:-${ROOT_DIR}/ios/InteractiveReader/InteractiveReader.xcodeproj}"
SCHEME_ENV_SET="${SCHEME+x}"
PRODUCT_NAME_ENV_SET="${PRODUCT_NAME+x}"
BUNDLE_ID_ENV_SET="${BUNDLE_ID+x}"
PLATFORM_PRODUCT_DIR_ENV_SET="${APPLE_DEVICE_PLATFORM_PRODUCT_DIR+x}"
SCHEME="${SCHEME:-InteractiveReader}"
CONFIGURATION="${CONFIGURATION:-Debug}"
PRODUCT_NAME="${PRODUCT_NAME:-InteractiveReader}"
BUNDLE_ID="${BUNDLE_ID:-com.example.InteractiveReader}"
DEVICE_PROFILE="${APPLE_DEVICE_PROFILE:-ios}"
PLATFORM_PRODUCT_DIR="${APPLE_DEVICE_PLATFORM_PRODUCT_DIR:-iphoneos}"
DEVICE_ID="${APPLE_DEVICE_ID:-}"
DERIVED_DATA="${APPLE_DEVICE_DERIVED_DATA:-}"
APP_PATH="${APPLE_DEVICE_APP_PATH:-}"
SIGNED_ARTIFACT_PATH="${APPLE_DEVICE_SIGNED_ARTIFACT_PATH:-}"
DEVELOPMENT_TEAM="${APPLE_DEVELOPMENT_TEAM:-}"
DEVICECTL_TIMEOUT="${APPLE_DEVICECTL_TIMEOUT:-60}"
ALLOW_PROVISIONING_UPDATES="${ALLOW_PROVISIONING_UPDATES:-0}"
STRIP_IOS_ENTITLEMENTS="${APPLE_DEVICE_STRIP_IOS_ENTITLEMENTS:-0}"
FALLBACK_TO_SIGNED_ARTIFACT="${APPLE_DEVICE_FALLBACK_TO_SIGNED_ARTIFACT:-0}"
LAUNCH_CONSOLE_TIMEOUT="${APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT:-}"
LAUNCH_LOG="${APPLE_DEVICE_LAUNCH_LOG:-}"
INSTALL=0
LAUNCH=0
LAUNCH_ONLY=0
DRY_RUN=0
LIST=0
SKIP_BUILD=0
VERIFY_AFTER_INSTALL=1
PREFLIGHT_BEFORE_INSTALL=1
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
    bash scripts/apple_unattended_device_update.sh --launch-only --launch-console-timeout 60
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
  --fallback-to-signed-artifact  If xcodebuild fails during a confirmed install, verify and install
                                 a pre-signed full-entitlement app bundle instead. With
                                 --skip-build, verify --app-path as the signed artifact before install.
  --signed-artifact-path PATH    Pre-signed app bundle for --fallback-to-signed-artifact.
                                 Defaults to test-results/DerivedData-device-full-entitlements.
  --launch                       Launch the installed app after install.
  --launch-only                  Launch the already-installed app without building or installing.
                                 Useful for attaching console logs during manual playback tests.
                                 Requires CONFIRM_PHYSICAL_DEVICE_UPDATE=YES.
  --no-verify                    Skip post-install app metadata verification.
  --no-preflight                 Skip the pre-install CoreDevice health check.
  --allow-provisioning-updates   Pass -allowProvisioningUpdates to xcodebuild.
  --strip-ios-entitlements-for-local-signing
                                 Temporarily remove the iOS app entitlements build setting
                                 during build, then restore the project file. Useful when
                                 a local development profile lacks iCloud/push/sign-in.
                                 Requires APPLE_DEVICE_ALLOW_ENTITLEMENT_STRIPPING=YES.
  --launch-console-timeout SECONDS
                                 Launch with --console and treat a timeout as success,
                                 proving the app did not immediately crash.
  --team-id TEAMID               Pass DEVELOPMENT_TEAM=TEAMID to xcodebuild.
  --configuration NAME           Xcode configuration. Defaults to Debug.
  --profile PROFILE              Device profile: ios, iphone, ipad, tvos, or appletv.
                                 tvos/appletv selects InteractiveReaderTV,
                                 com.example.InteractiveReader.tvos, and appletvos.
  --dry-run                      Print the commands that would run, then exit without building or installing.
  --device ID                    Device identifier, ECID, serial, UDID, CoreDevice id, or name.

Environment:
  CONFIRM_PHYSICAL_DEVICE_UPDATE=YES is required for --install.
  APPLE_DEVICE_ID, APPLE_DEVICE_PROFILE, APPLE_DEVICE_APP_PATH,
  APPLE_DEVELOPMENT_TEAM, APPLE_DEVICE_PLATFORM_PRODUCT_DIR,
  APPLE_DEVICE_DERIVED_DATA, APPLE_DEVICECTL_TIMEOUT, XCBUILD, DEVICECTL,
  XCPROJ, SCHEME, CONFIGURATION, PRODUCT_NAME, and BUNDLE_ID override defaults.
  APPLE_DEVICE_FALLBACK_TO_SIGNED_ARTIFACT=1 and APPLE_DEVICE_SIGNED_ARTIFACT_PATH
  enable the iCloud-preserving cached signed-artifact install fallback.
  APPLE_DEVICE_STRIP_IOS_ENTITLEMENTS=1 and APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT
  enable the matching unattended fallback behaviors.
  APPLE_DEVICE_LAUNCH_LOG overrides the default launch-console log path under
  test-results/apple-device-launch-console-<device>.log.
  APPLE_DEVICE_ALLOW_ENTITLEMENT_STRIPPING=YES is required before the
  entitlement-stripping fallback can mutate project settings during a build.
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
        if value.get("bundleIdentifier") == bundle_id:
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

json_contains_locked_launch_error() {
  local json_path="$1"
  python3 - "$json_path" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])

try:
    payload = json.loads(path.read_text())
except Exception:
    raise SystemExit(1)

def walk(value):
    if isinstance(value, dict):
        for child in value.values():
            if walk(child):
                return True
    elif isinstance(value, list):
        for child in value:
            if walk(child):
                return True
    elif isinstance(value, str):
        lowered = value.lower()
        if "unable to launch" in lowered and "unlock" in lowered:
            return True
        if "locked" in lowered and "requestdenied" in lowered:
            return True
    return False

raise SystemExit(0 if walk(payload) else 1)
PY
}

plist_value() {
  local plist_path="$1"
  local key="$2"
  /usr/bin/plutil -extract "${key}" raw -o - "${plist_path}" 2>/dev/null || true
}

source_info_plist() {
  case "${DEVICE_PROFILE}" in
    tvos|appletv)
      echo "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Supporting/Info-tvOS.plist"
      ;;
    *)
      echo "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Supporting/Info.plist"
      ;;
  esac
}

verify_signed_artifact_bundle() {
  local artifact_path="$1"
  local artifact_info="${artifact_path}/Info.plist"
  local expected_info
  local actual_bundle_id actual_short actual_build expected_short expected_build

  if [[ -z "${artifact_path}" || ! -d "${artifact_path}" ]]; then
    echo "Signed artifact app bundle not found: ${artifact_path}" >&2
    return 1
  fi
  if [[ ! -f "${artifact_info}" ]]; then
    echo "Signed artifact is missing Info.plist: ${artifact_path}" >&2
    return 1
  fi

  "${CODESIGN}" --verify --deep --strict --verbose=4 "${artifact_path}"

  actual_bundle_id="$(plist_value "${artifact_info}" CFBundleIdentifier)"
  if [[ "${actual_bundle_id}" != "${BUNDLE_ID}" ]]; then
    echo "Signed artifact bundle id ${actual_bundle_id:-<missing>} does not match ${BUNDLE_ID}." >&2
    return 1
  fi

  expected_info="$(source_info_plist)"
  if [[ -f "${expected_info}" ]]; then
    actual_short="$(plist_value "${artifact_info}" CFBundleShortVersionString)"
    actual_build="$(plist_value "${artifact_info}" CFBundleVersion)"
    expected_short="$(plist_value "${expected_info}" CFBundleShortVersionString)"
    expected_build="$(plist_value "${expected_info}" CFBundleVersion)"
    if [[ -n "${expected_short}" && "${actual_short}" != "${expected_short}" ]]; then
      echo "Signed artifact version ${actual_short:-<missing>} does not match current ${expected_short}." >&2
      return 1
    fi
    if [[ -n "${expected_build}" && "${actual_build}" != "${expected_build}" ]]; then
      echo "Signed artifact build ${actual_build:-<missing>} does not match current ${expected_build}." >&2
      return 1
    fi
  fi
}

resolve_xcodebuild_destination_id() {
  local selector="$1"
  local json_path="$2"
  mkdir -p "$(dirname "${json_path}")"
  "${DEVICECTL}" device info details \
    --device "${selector}" \
    --timeout "${DEVICECTL_TIMEOUT}" \
    --json-output "${json_path}" >/dev/null
  python3 - "${json_path}" "${selector}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
fallback = sys.argv[2]

try:
    payload = json.loads(path.read_text())
except Exception:
    print(fallback)
    raise SystemExit(0)

def walk(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "udid" and isinstance(child, str) and child.strip():
                return child.strip()
            found = walk(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = walk(child)
            if found:
                return found
    return ""

print(walk(payload) or fallback)
PY
}

restore_project_file() {
  if [[ -n "${PROJECT_FILE_BACKUP:-}" && -f "${PROJECT_FILE_BACKUP}" && -n "${PROJECT_FILE_TO_RESTORE:-}" ]]; then
    cp "${PROJECT_FILE_BACKUP}" "${PROJECT_FILE_TO_RESTORE}"
  fi
}

strip_ios_entitlements_for_local_signing() {
  local project_file="${XCPROJ}/project.pbxproj"
  if [[ ! -f "${project_file}" ]]; then
    echo "Cannot strip iOS entitlements; project file not found: ${project_file}" >&2
    exit 1
  fi
  PROJECT_FILE_TO_RESTORE="${project_file}"
  PROJECT_FILE_BACKUP="$(json_scratch_path apple-device-project-backup)"
  mkdir -p "$(dirname "${PROJECT_FILE_BACKUP}")"
  cp "${project_file}" "${PROJECT_FILE_BACKUP}"
  trap restore_project_file EXIT
  python3 - "${project_file}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_text()
needle = "\t\t\t\t\tCODE_SIGN_ENTITLEMENTS = InteractiveReader/Supporting/InteractiveReader.entitlements;\n"
count = source.count(needle)
if count == 0:
    raise SystemExit("No iOS CODE_SIGN_ENTITLEMENTS lines matched the local-signing patch.")
path.write_text(source.replace(needle, ""))
print(f"Temporarily removed {count} iOS app entitlement build setting(s) for local signing.")
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
    --fallback-to-signed-artifact)
      FALLBACK_TO_SIGNED_ARTIFACT=1
      shift
      ;;
    --signed-artifact-path)
      SIGNED_ARTIFACT_PATH="${2:-}"
      shift 2
      ;;
    --launch)
      LAUNCH=1
      shift
      ;;
    --launch-only)
      LAUNCH=1
      LAUNCH_ONLY=1
      SKIP_BUILD=1
      INSTALL=0
      shift
      ;;
    --no-verify)
      VERIFY_AFTER_INSTALL=0
      shift
      ;;
    --no-preflight)
      PREFLIGHT_BEFORE_INSTALL=0
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
    --strip-ios-entitlements-for-local-signing)
      STRIP_IOS_ENTITLEMENTS=1
      shift
      ;;
    --launch-console-timeout)
      LAUNCH_CONSOLE_TIMEOUT="${2:-}"
      shift 2
      ;;
    --team-id)
      DEVELOPMENT_TEAM="${2:-}"
      shift 2
      ;;
    --configuration)
      CONFIGURATION="${2:-}"
      shift 2
      ;;
    --profile)
      DEVICE_PROFILE="${2:-}"
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

case "${DEVICE_PROFILE}" in
  ios|iphone|ipad)
    if [[ -z "${SCHEME_ENV_SET}" ]]; then
      SCHEME="InteractiveReader"
    fi
    if [[ -z "${PRODUCT_NAME_ENV_SET}" ]]; then
      PRODUCT_NAME="InteractiveReader"
    fi
    if [[ -z "${BUNDLE_ID_ENV_SET}" ]]; then
      BUNDLE_ID="com.example.InteractiveReader"
    fi
    if [[ -z "${PLATFORM_PRODUCT_DIR_ENV_SET}" ]]; then
      PLATFORM_PRODUCT_DIR="iphoneos"
    fi
    ;;
  tvos|appletv)
    if [[ -z "${SCHEME_ENV_SET}" ]]; then
      SCHEME="InteractiveReaderTV"
    fi
    if [[ -z "${PRODUCT_NAME_ENV_SET}" ]]; then
      PRODUCT_NAME="InteractiveReaderTV"
    fi
    if [[ -z "${BUNDLE_ID_ENV_SET}" ]]; then
      BUNDLE_ID="com.example.InteractiveReader.tvos"
    fi
    if [[ -z "${PLATFORM_PRODUCT_DIR_ENV_SET}" ]]; then
      PLATFORM_PRODUCT_DIR="appletvos"
    fi
    ;;
  *)
    echo "Unknown device profile: ${DEVICE_PROFILE}" >&2
    usage >&2
    exit 2
    ;;
esac

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
  APP_PATH="${DERIVED_DATA}/Build/Products/${CONFIGURATION}-${PLATFORM_PRODUCT_DIR}/${PRODUCT_NAME}.app"
fi
if [[ -z "${SIGNED_ARTIFACT_PATH}" ]]; then
  SIGNED_ARTIFACT_PATH="${ROOT_DIR}/test-results/DerivedData-device-full-entitlements/Build/Products/${CONFIGURATION}-${PLATFORM_PRODUCT_DIR}/${PRODUCT_NAME}.app"
fi

VERIFY_JSON="$(json_scratch_path apple-device-installed-app)"
PREFLIGHT_JSON="$(json_scratch_path apple-device-preflight)"
BUILD_DESTINATION_JSON="$(json_scratch_path apple-device-build-destination)"
INSTALL_JSON="$(json_scratch_path apple-device-install)"
LAUNCH_JSON="$(json_scratch_path apple-device-launch)"
if [[ -z "${LAUNCH_LOG}" ]]; then
  LAUNCH_LOG="$(json_scratch_path apple-device-launch-console)"
  LAUNCH_LOG="${LAUNCH_LOG%.json}.log"
fi
XCODEBUILD_DESTINATION_ID="${DEVICE_ID}"
if [[ "${SKIP_BUILD}" != "1" && "${DRY_RUN}" != "1" ]]; then
  XCODEBUILD_DESTINATION_ID="$(resolve_xcodebuild_destination_id "${DEVICE_ID}" "${BUILD_DESTINATION_JSON}")"
  if [[ "${XCODEBUILD_DESTINATION_ID}" != "${DEVICE_ID}" ]]; then
    echo "Resolved xcodebuild destination id: ${XCODEBUILD_DESTINATION_ID}"
  fi
fi

BUILD_CMD=(
  "${XCBUILD}"
  -project "${XCPROJ}"
  -scheme "${SCHEME}"
  -configuration "${CONFIGURATION}"
  -destination "id=${XCODEBUILD_DESTINATION_ID}"
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
PREFLIGHT_CMD=(
  "${DEVICECTL}" device info details
  --device "${DEVICE_ID}"
  --timeout "${DEVICECTL_TIMEOUT}"
  --json-output "${PREFLIGHT_JSON}"
)
LAUNCH_CMD=(
  "${DEVICECTL}" device process launch
  --terminate-existing
  --device "${DEVICE_ID}"
  --timeout "${DEVICECTL_TIMEOUT}"
  --json-output "${LAUNCH_JSON}"
  "${BUNDLE_ID}"
)
if [[ -n "${LAUNCH_CONSOLE_TIMEOUT}" ]]; then
  LAUNCH_CMD=(
    "${DEVICECTL}" device process
    --timeout "${LAUNCH_CONSOLE_TIMEOUT}"
    --json-output "${LAUNCH_JSON}"
    --log-output "${LAUNCH_LOG}"
    launch
    --terminate-existing
    --device "${DEVICE_ID}"
    --console
    --environment-variables '{"OS_ACTIVITY_DT_MODE":"YES"}'
    "${BUNDLE_ID}"
  )
fi

if [[ "${PREFLIGHT_ONLY}" == "1" ]]; then
  print_command "Device preflight command" "${PREFLIGHT_CMD[@]}"
  if [[ "${DRY_RUN}" == "1" ]]; then
    exit 0
  fi
  mkdir -p "$(dirname "${PREFLIGHT_JSON}")"
  "${PREFLIGHT_CMD[@]}" || {
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
  echo "Resolved app path: ${APP_PATH}"
  if [[ "${FALLBACK_TO_SIGNED_ARTIFACT}" == "1" ]]; then
    echo "Signed artifact fallback path: ${SIGNED_ARTIFACT_PATH}"
  fi
  if [[ "${STRIP_IOS_ENTITLEMENTS}" == "1" ]]; then
    if [[ "${APPLE_DEVICE_ALLOW_ENTITLEMENT_STRIPPING:-}" != "YES" ]]; then
      echo "Refusing to strip iOS entitlements without APPLE_DEVICE_ALLOW_ENTITLEMENT_STRIPPING=YES." >&2
      echo "Use the full-entitlement codesign fallback when validating iCloud, Push, or Sign in with Apple." >&2
      exit 2
    fi
    echo "Local signing patch: temporarily strip iOS app entitlements during build, then restore project file."
  fi
fi

if [[ "${INSTALL}" == "1" ]]; then
  if [[ "${PREFLIGHT_BEFORE_INSTALL}" == "1" ]]; then
    print_command "Device preflight command" "${PREFLIGHT_CMD[@]}"
  fi
  print_command "Install command" "${INSTALL_CMD[@]}"
  if [[ "${VERIFY_AFTER_INSTALL}" == "1" ]]; then
    print_command "Post-install verification command" "${VERIFY_CMD[@]}"
  fi
fi

if [[ "${INSTALL}" == "1" && "${LAUNCH}" == "1" ]]; then
  print_command "Launch command" "${LAUNCH_CMD[@]}"
fi

if [[ "${LAUNCH_ONLY}" == "1" ]]; then
  print_command "Launch command" "${LAUNCH_CMD[@]}"
fi

if [[ "${DRY_RUN}" == "1" ]]; then
  exit 0
fi

if [[ "${LAUNCH_ONLY}" == "1" && "${CONFIRM_PHYSICAL_DEVICE_UPDATE:-}" != "YES" ]]; then
  echo "Refusing to launch on a physical device without CONFIRM_PHYSICAL_DEVICE_UPDATE=YES." >&2
  exit 2
fi

if [[ "${INSTALL}" == "1" && "${CONFIRM_PHYSICAL_DEVICE_UPDATE:-}" != "YES" ]]; then
  echo "Refusing to install to a physical device without CONFIRM_PHYSICAL_DEVICE_UPDATE=YES." >&2
  exit 2
fi

mkdir -p "$(dirname "${INSTALL_JSON}")"

run_launch_command() {
  set +e
  "${LAUNCH_CMD[@]}"
  local launch_status=$?
  set -e
  if [[ -n "${LAUNCH_CONSOLE_TIMEOUT}" && "${launch_status}" == "2" ]]; then
    echo "Launch console timeout reached after ${LAUNCH_CONSOLE_TIMEOUT}s; treating this as app-alive verification."
    echo "Launch console log: ${LAUNCH_LOG}"
  elif [[ "${launch_status}" != "0" && -f "${LAUNCH_JSON}" ]] && json_contains_locked_launch_error "${LAUNCH_JSON}"; then
    echo "Launch was denied because the device is locked; install and metadata verification already completed."
  elif [[ "${launch_status}" != "0" ]]; then
    exit "${launch_status}"
  fi
}

if [[ "${LAUNCH_ONLY}" == "1" ]]; then
  mkdir -p "$(dirname "${LAUNCH_JSON}")"
  run_launch_command
  exit 0
fi

if [[ "${INSTALL}" == "1" && "${SKIP_BUILD}" == "1" && "${FALLBACK_TO_SIGNED_ARTIFACT}" == "1" ]]; then
  verify_signed_artifact_bundle "${APP_PATH}"
fi

if [[ "${INSTALL}" == "1" && "${PREFLIGHT_BEFORE_INSTALL}" == "1" ]]; then
  mkdir -p "$(dirname "${PREFLIGHT_JSON}")"
  "${PREFLIGHT_CMD[@]}" || {
    echo "Device preflight failed. Confirm the device is connected, awake, trusted, and visible to CoreDevice." >&2
    exit 1
  }
fi

if [[ "${SKIP_BUILD}" != "1" ]]; then
  if [[ "${STRIP_IOS_ENTITLEMENTS}" == "1" ]]; then
    strip_ios_entitlements_for_local_signing
  fi
  set +e
  "${BUILD_CMD[@]}"
  build_status=$?
  set -e
  if [[ "${build_status}" != "0" ]]; then
    if [[ "${INSTALL}" == "1" && "${FALLBACK_TO_SIGNED_ARTIFACT}" == "1" ]]; then
      echo "xcodebuild failed with status ${build_status}; verifying signed artifact fallback."
      verify_signed_artifact_bundle "${SIGNED_ARTIFACT_PATH}"
      APP_PATH="${SIGNED_ARTIFACT_PATH}"
      INSTALL_CMD=(
        "${DEVICECTL}" device install app
        --device "${DEVICE_ID}"
        "${APP_PATH}"
        --timeout "${DEVICECTL_TIMEOUT}"
        --json-output "${INSTALL_JSON}"
      )
      print_command "Signed artifact fallback install command" "${INSTALL_CMD[@]}"
    else
      exit "${build_status}"
    fi
  fi
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
  run_launch_command
fi
