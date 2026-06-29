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
SOURCE_SYNC_MODE="${APPLE_DEVICE_SOURCE_SYNC_MODE:-auto}"
SOURCE_SYNC_BRANCH="${APPLE_DEVICE_SOURCE_SYNC_BRANCH:-}"
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
HOST_READINESS_ONLY=0
HOST_USER_CACHE_VALIDATED=0

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/apple_unattended_device_update.sh --list
  bash scripts/apple_unattended_device_update.sh --host-readiness-only
  APPLE_DEVICE_ID=<udid-or-coredevice-id> bash scripts/apple_unattended_device_update.sh --device-preflight-only
  APPLE_DEVICE_ID=<udid-or-coredevice-id> bash scripts/apple_unattended_device_update.sh --verify-installed
  APPLE_DEVICE_ID=<udid-or-coredevice-id> bash scripts/apple_unattended_device_update.sh --build-only
  APPLE_DEVICE_ID=<udid-or-coredevice-id> CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
    bash scripts/apple_unattended_device_update.sh --launch-only --launch-console-timeout 60
  APPLE_DEVICE_ID=<udid-or-coredevice-id> CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
    bash scripts/apple_unattended_device_update.sh --install [--launch]

Options:
  --list                         List devices known to devicectl and exit.
  --host-readiness-only          Check local macOS passwd/cache readiness for
                                 Xcode/CoreDevice and exit without a device.
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
  --profile PROFILE              Device profile: ios, iphone, ipad, tvos, appletv, or cinema.
                                 tvos/appletv/cinema selects InteractiveReaderTV,
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
  APPLE_DEVICE_SKIP_HOST_USER_CACHE_CHECK=1 skips the local macOS passwd/cache
  readiness guard for fake-tool tests only.
  APPLE_DEVICE_SOURCE_SYNC_MODE controls deploy source freshness checks:
  auto (default) requires confirmed installs to match origin/<branch>,
  warn prints mismatches without failing, require always fails stale checkouts,
  and skip disables the check.
  APPLE_DEVICE_SOURCE_SYNC_BRANCH overrides the branch checked by the source
  freshness guard. Defaults to the current Git branch.
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

coredevice_failure_log_path() {
  local name="$1"
  local path
  path="$(json_scratch_path "${name}-coredevice-error")"
  echo "${path%.json}.log"
}

explain_coredevice_failure_if_known() {
  local phase="$1"
  local stderr_path="$2"
  [[ -f "${stderr_path}" ]] || return 0
  if ! grep -Eqi 'CoreDeviceService to fully initialize|Failed to load provisioning parameter list|XPCConnectionDescription.*CoreDeviceService|connection was invalidated' "${stderr_path}"; then
    return 0
  fi
  echo "CoreDeviceService failed during ${phase}; the device may still appear in devicectl --list while info/install/launch commands are wedged." >&2
  echo "Try: wake/unlock/reconnect the device, quit Xcode, then retry. If the local Mac allows it, restart the user CoreDevice service with:" >&2
  echo "  launchctl kickstart -k user/$(id -u)/com.apple.CoreDevice.CoreDeviceService" >&2
  echo "If launchctl reports Operation not permitted, use Xcode's Devices window to reconnect the device or reboot the Mac before retrying." >&2
  echo "Captured CoreDevice stderr: ${stderr_path}" >&2
}

run_coredevice_command() {
  local phase="$1"
  shift
  local stderr_path
  local restore_errexit=0
  stderr_path="$(coredevice_failure_log_path "${phase}")"
  mkdir -p "$(dirname "${stderr_path}")"
  case "$-" in
    *e*) restore_errexit=1 ;;
  esac
  set +e
  "$@" 2> "${stderr_path}"
  local status=$?
  if [[ "${restore_errexit}" == "1" ]]; then
    set -e
  else
    set +e
  fi
  if [[ -s "${stderr_path}" ]]; then
    cat "${stderr_path}" >&2
  fi
  if [[ "${status}" != "0" ]]; then
    explain_coredevice_failure_if_known "${phase}" "${stderr_path}"
  fi
  return "${status}"
}

host_readiness_report_path() {
  echo "${APPLE_DEVICE_HOST_READINESS_REPORT:-${ROOT_DIR}/test-results/apple-device-host-readiness.json}"
}

write_host_readiness_report() {
  local status="$1"
  local detail="${2:-}"
  local path
  path="$(host_readiness_report_path)"
  mkdir -p "$(dirname "${path}")"
  python3 - "$path" "$status" "$detail" <<'PY'
import datetime as _dt
import json
import sys

path, status, detail = sys.argv[1:4]
payload = {
    "check": "apple-device-host-readiness",
    "status": status,
    "detail": detail,
    "remediation": (
        "Restart the affected user session or repair Directory Services, then rerun "
        "make apple-runtime-xcode-readiness and make apple-device-host-readiness "
        "before simulator or physical-device deploys."
    ),
    "generated_at": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
}

validate_host_user_cache() {
  if [[ "${HOST_USER_CACHE_VALIDATED}" == "1" ]]; then
    return 0
  fi
  if [[ "$(uname -s)" != "Darwin" ]]; then
    HOST_USER_CACHE_VALIDATED=1
    write_host_readiness_report "passed" "host platform is not Darwin"
    return 0
  fi
  if [[ "${APPLE_DEVICE_SKIP_HOST_USER_CACHE_CHECK:-}" == "1" ]]; then
    HOST_USER_CACHE_VALIDATED=1
    write_host_readiness_report "passed" "macOS account/cache lookup is healthy"
    return 0
  fi

  local detail status
  if [[ -n "${APPLE_DEVICE_FORCE_HOST_USER_CACHE_FAILURE:-}" ]]; then
    detail="${APPLE_DEVICE_FORCE_HOST_USER_CACHE_FAILURE}"
    status=1
  else
    set +e
    detail="$(
      python3 - <<'PY'
import os
import pwd
import subprocess
import sys

try:
    pwd.getpwuid(os.getuid())
except KeyError:
    print(f"uid {os.getuid()} has no passwd entry")
    raise SystemExit(1)

try:
    result = subprocess.run(
        ["getconf", "DARWIN_USER_CACHE_DIR"],
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
except FileNotFoundError:
    print("getconf not found")
    raise SystemExit(1)
except subprocess.TimeoutExpired:
    print("DARWIN_USER_CACHE_DIR lookup timed out")
    raise SystemExit(1)

if result.returncode != 0 or not result.stdout.strip():
    print("DARWIN_USER_CACHE_DIR lookup failed")
    raise SystemExit(1)
PY
    )"
    status=$?
    set -e
  fi

  if [[ "${status}" == "0" ]]; then
    HOST_USER_CACHE_VALIDATED=1
    write_host_readiness_report "passed" "macOS account/cache lookup is healthy"
    return 0
  fi

  write_host_readiness_report "failed" "${detail:-unknown}"
  echo "Apple device host readiness failed: macOS account/cache lookup is unhealthy for Xcode/CoreDevice (${detail:-unknown}); restart the user session or repair Directory Services, then retry the Apple device update." >&2
  echo "Wrote host readiness report: $(host_readiness_report_path)" >&2
  echo "For the ebook-tools golden pipeline, rerun 'make apple-runtime-xcode-readiness' from a healthy checkout before simulator or physical-device deploys." >&2
  return 69
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

effective_source_sync_mode() {
  case "${SOURCE_SYNC_MODE}" in
    auto)
      if [[ "${INSTALL}" == "1" ]]; then
        echo "require"
      else
        echo "warn"
      fi
      ;;
    require|warn|skip)
      echo "${SOURCE_SYNC_MODE}"
      ;;
    *)
      echo "Unknown APPLE_DEVICE_SOURCE_SYNC_MODE: ${SOURCE_SYNC_MODE}" >&2
      echo "Expected one of: auto, require, warn, skip." >&2
      exit 2
      ;;
  esac
}

verify_deploy_source_freshness() {
  local mode="$1"
  if [[ "${mode}" == "skip" ]]; then
    echo "Deploy source freshness check skipped by APPLE_DEVICE_SOURCE_SYNC_MODE=skip."
    return 0
  fi
  if ! command -v git >/dev/null 2>&1; then
    echo "Deploy source freshness check skipped; git is not available." >&2
    return 0
  fi
  if ! git -C "${ROOT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Deploy source freshness check skipped; ${ROOT_DIR} is not a Git checkout." >&2
    return 0
  fi

  local branch="${SOURCE_SYNC_BRANCH}"
  if [[ -z "${branch}" ]]; then
    branch="$(git -C "${ROOT_DIR}" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  fi
  if [[ -z "${branch}" || "${branch}" == "HEAD" ]]; then
    echo "Deploy source freshness check skipped; current Git branch is detached." >&2
    return 0
  fi

  local local_head remote_head
  local_head="$(git -C "${ROOT_DIR}" rev-parse HEAD)"
  if ! git -C "${ROOT_DIR}" fetch --prune origin "${branch}" >/dev/null 2>&1; then
    echo "Deploy source freshness check could not fetch origin/${branch}." >&2
    if [[ "${mode}" == "require" ]]; then
      return 1
    fi
    return 0
  fi
  remote_head="$(git -C "${ROOT_DIR}" rev-parse "refs/remotes/origin/${branch}" 2>/dev/null || true)"
  if [[ -z "${remote_head}" ]]; then
    echo "Deploy source freshness check could not resolve origin/${branch}." >&2
    if [[ "${mode}" == "require" ]]; then
      return 1
    fi
    return 0
  fi
  if [[ "${local_head}" == "${remote_head}" ]]; then
    echo "Deploy source freshness check passed: ${branch} ${local_head:0:8} matches origin/${branch}."
    return 0
  fi

  local message="Deploy source checkout is not at origin/${branch}: local ${local_head:0:8}, origin ${remote_head:0:8}."
  if [[ "${mode}" == "require" ]]; then
    echo "${message}" >&2
    echo "Run git pull --ff-only origin ${branch}, or set APPLE_DEVICE_SOURCE_SYNC_MODE=skip for an explicit emergency override." >&2
    return 1
  fi
  echo "WARNING: ${message}" >&2
}

source_info_plist() {
  case "${DEVICE_PROFILE}" in
    tvos|appletv|cinema)
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
  local details_stderr list_json resolved_from_list
  mkdir -p "$(dirname "${json_path}")"
  details_stderr="$(coredevice_failure_log_path apple-device-build-destination)"
  if "${DEVICECTL}" device info details \
      --device "${selector}" \
      --timeout "${DEVICECTL_TIMEOUT}" \
      --json-output "${json_path}" >/dev/null 2> "${details_stderr}"; then
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
    return 0
  fi

  if [[ -s "${details_stderr}" ]]; then
    cat "${details_stderr}" >&2
    echo "Device detail lookup failed while resolving xcodebuild destination; trying devicectl list fallback." >&2
    explain_coredevice_failure_if_known "apple-device-build-destination" "${details_stderr}"
  fi

  list_json="${json_path%.json}-list.json"
  if resolved_from_list="$(resolve_xcodebuild_destination_id_from_list "${selector}" "${list_json}")" && [[ -n "${resolved_from_list}" ]]; then
    echo "${resolved_from_list}"
    return 0
  fi

  echo "${selector}"
}

resolve_xcodebuild_destination_id_from_list() {
  local selector="$1"
  local json_path="$2"
  mkdir -p "$(dirname "${json_path}")"
  "${DEVICECTL}" list devices \
    --timeout "${DEVICECTL_TIMEOUT}" \
    --json-output "${json_path}" >/dev/null 2>/dev/null || return 1
  python3 - "${json_path}" "${selector}" <<'PY'
import json
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
selector = sys.argv[2].strip()

try:
    payload = json.loads(path.read_text())
except Exception:
    raise SystemExit(1)

if not isinstance(payload, dict):
    raise SystemExit(1)

info = payload.get("info")
if payload.get("error") or (isinstance(info, dict) and info.get("outcome") == "failed"):
    raise SystemExit(1)

result = payload.get("result")
if isinstance(result, dict) and isinstance(result.get("devices"), list):
    payload = result["devices"]
elif isinstance(payload.get("devices"), list):
    payload = payload["devices"]

MATCH_KEYS = {
    "name",
    "hostname",
    "identifier",
    "id",
    "udid",
    "ecid",
    "serialNumber",
    "serial_number",
}
DESTINATION_KEYS = ("udid", "identifier", "id")
TRAILING_PLATFORM_WORDS = {
    ("tv",),
    ("television",),
    ("appletv",),
    ("apple", "tv"),
    ("ipad",),
    ("iphone",),
}


def normalized_label(value):
    text = re.sub(r"[^0-9a-z]+", " ", str(value).lower()).strip()
    return " ".join(text.split())


def selector_aliases(value):
    normalized = normalized_label(value)
    aliases = {normalized} if normalized else set()
    tokens = normalized.split()
    for suffix in TRAILING_PLATFORM_WORDS:
        if len(tokens) > len(suffix) and tuple(tokens[-len(suffix):]) == suffix:
            aliases.add(" ".join(tokens[: -len(suffix)]))
    return {alias for alias in aliases if alias}


def iter_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def scalar_values_by_key(value, target_keys):
    values = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in target_keys and isinstance(child, (str, int)) and str(child).strip():
                values.append(str(child).strip())
            values.extend(scalar_values_by_key(child, target_keys))
    elif isinstance(value, list):
        for child in value:
            values.extend(scalar_values_by_key(child, target_keys))
    return values


selector_matches = selector_aliases(selector)

for candidate in iter_dicts(payload):
    searchable = scalar_values_by_key(candidate, MATCH_KEYS)
    if selector_matches.isdisjoint({normalized_label(value) for value in searchable}):
        continue
    for destination_key in DESTINATION_KEYS:
        destinations = scalar_values_by_key(candidate, {destination_key})
        for destination in destinations:
            if destination.strip():
                print(destination.strip())
                raise SystemExit(0)
    for destination in scalar_values_by_key(candidate, DESTINATION_KEYS):
        if destination.strip():
            print(destination.strip())
            raise SystemExit(0)

raise SystemExit(1)
PY
}

resolve_coredevice_device_id_from_list() {
  local selector="$1"
  local json_path="$2"
  mkdir -p "$(dirname "${json_path}")"
  "${DEVICECTL}" list devices \
    --timeout "${DEVICECTL_TIMEOUT}" \
    --json-output "${json_path}" >/dev/null 2>/dev/null || return 1
  python3 - "${json_path}" "${selector}" <<'PY'
import json
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
selector = sys.argv[2].strip()

try:
    payload = json.loads(path.read_text())
except Exception:
    raise SystemExit(1)

if not isinstance(payload, dict):
    raise SystemExit(1)

info = payload.get("info")
if payload.get("error") or (isinstance(info, dict) and info.get("outcome") == "failed"):
    raise SystemExit(1)

result = payload.get("result")
if isinstance(result, dict) and isinstance(result.get("devices"), list):
    payload = result["devices"]
elif isinstance(payload.get("devices"), list):
    payload = payload["devices"]

MATCH_KEYS = {
    "name",
    "hostname",
    "identifier",
    "id",
    "udid",
    "ecid",
    "serialNumber",
    "serial_number",
}
DESTINATION_KEYS = ("identifier", "id", "udid")
TRAILING_PLATFORM_WORDS = {
    ("tv",),
    ("television",),
    ("appletv",),
    ("apple", "tv"),
    ("ipad",),
    ("iphone",),
}


def normalized_label(value):
    text = re.sub(r"[^0-9a-z]+", " ", str(value).lower()).strip()
    return " ".join(text.split())


def selector_aliases(value):
    normalized = normalized_label(value)
    aliases = {normalized} if normalized else set()
    tokens = normalized.split()
    for suffix in TRAILING_PLATFORM_WORDS:
        if len(tokens) > len(suffix) and tuple(tokens[-len(suffix):]) == suffix:
            aliases.add(" ".join(tokens[: -len(suffix)]))
    return {alias for alias in aliases if alias}


def iter_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def scalar_values_by_key(value, target_keys):
    values = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in target_keys and isinstance(child, (str, int)) and str(child).strip():
                values.append(str(child).strip())
            values.extend(scalar_values_by_key(child, target_keys))
    elif isinstance(value, list):
        for child in value:
            values.extend(scalar_values_by_key(child, target_keys))
    return values


selector_matches = selector_aliases(selector)

for candidate in iter_dicts(payload):
    searchable = scalar_values_by_key(candidate, MATCH_KEYS)
    if selector_matches.isdisjoint({normalized_label(value) for value in searchable}):
        continue
    for destination_key in DESTINATION_KEYS:
        destinations = scalar_values_by_key(candidate, {destination_key})
        for destination in destinations:
            if destination.strip():
                print(destination.strip())
                raise SystemExit(0)

raise SystemExit(1)
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
    --host-readiness-only)
      HOST_READINESS_ONLY=1
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
  tvos|appletv|cinema)
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

if [[ "${HOST_READINESS_ONLY}" == "1" ]]; then
  validate_host_user_cache
  echo "Apple device host readiness passed."
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
COREDEVICE_DESTINATION_JSON="$(json_scratch_path apple-device-coredevice-destination)"
INSTALL_JSON="$(json_scratch_path apple-device-install)"
LAUNCH_JSON="$(json_scratch_path apple-device-launch)"
if [[ -z "${LAUNCH_LOG}" ]]; then
  LAUNCH_LOG="$(json_scratch_path apple-device-launch-console)"
  LAUNCH_LOG="${LAUNCH_LOG%.json}.log"
fi
LAUNCH_COREDEVICE_LOG="${LAUNCH_LOG%.log}.coredevice.log"
XCODEBUILD_DESTINATION_ID="${DEVICE_ID}"
DEVICECTL_DEVICE_ID="${DEVICE_ID}"
if [[ "${DRY_RUN}" != "1" && "${INSTALL}" == "1" && "${SKIP_BUILD}" != "1" && "${CONFIRM_PHYSICAL_DEVICE_UPDATE:-}" != "YES" ]]; then
  echo "Refusing to install to a physical device without CONFIRM_PHYSICAL_DEVICE_UPDATE=YES." >&2
  exit 2
fi
if [[ "${SKIP_BUILD}" != "1" && "${DRY_RUN}" != "1" && "${PREFLIGHT_ONLY}" != "1" && "${VERIFY_ONLY}" != "1" && "${LAUNCH_ONLY}" != "1" ]]; then
  validate_host_user_cache
fi
if [[ "${SKIP_BUILD}" != "1" && "${DRY_RUN}" != "1" && "${PREFLIGHT_ONLY}" != "1" && "${VERIFY_ONLY}" != "1" && "${LAUNCH_ONLY}" != "1" ]]; then
  XCODEBUILD_DESTINATION_ID="$(resolve_xcodebuild_destination_id "${DEVICE_ID}" "${BUILD_DESTINATION_JSON}")"
  if [[ "${XCODEBUILD_DESTINATION_ID}" != "${DEVICE_ID}" ]]; then
    echo "Resolved xcodebuild destination id: ${XCODEBUILD_DESTINATION_ID}"
  fi
fi
if [[ "${DRY_RUN}" != "1" && ( "${INSTALL}" == "1" || "${PREFLIGHT_ONLY}" == "1" || "${VERIFY_ONLY}" == "1" || "${LAUNCH_ONLY}" == "1" ) ]]; then
  if DEVICECTL_DEVICE_ID="$(resolve_coredevice_device_id_from_list "${DEVICE_ID}" "${COREDEVICE_DESTINATION_JSON}")" && [[ -n "${DEVICECTL_DEVICE_ID}" ]]; then
    if [[ "${DEVICECTL_DEVICE_ID}" != "${DEVICE_ID}" ]]; then
      echo "Resolved CoreDevice device id: ${DEVICECTL_DEVICE_ID}"
    fi
  else
    DEVICECTL_DEVICE_ID="${DEVICE_ID}"
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
  --device "${DEVICECTL_DEVICE_ID}"
  "${APP_PATH}"
  --timeout "${DEVICECTL_TIMEOUT}"
  --json-output "${INSTALL_JSON}"
)
VERIFY_CMD=(
  "${DEVICECTL}" device info apps
  --device "${DEVICECTL_DEVICE_ID}"
  --bundle-id "${BUNDLE_ID}"
  --timeout "${DEVICECTL_TIMEOUT}"
  --json-output "${VERIFY_JSON}"
)
PREFLIGHT_CMD=(
  "${DEVICECTL}" device info details
  --device "${DEVICECTL_DEVICE_ID}"
  --timeout "${DEVICECTL_TIMEOUT}"
  --json-output "${PREFLIGHT_JSON}"
)
LAUNCH_CMD=(
  "${DEVICECTL}" device process launch
  --terminate-existing
  --device "${DEVICECTL_DEVICE_ID}"
  --timeout "${DEVICECTL_TIMEOUT}"
  --json-output "${LAUNCH_JSON}"
  "${BUNDLE_ID}"
)
if [[ -n "${LAUNCH_CONSOLE_TIMEOUT}" ]]; then
  LAUNCH_CMD=(
    "${DEVICECTL}" device process
    --timeout "${LAUNCH_CONSOLE_TIMEOUT}"
    --json-output "${LAUNCH_JSON}"
    --log-output "${LAUNCH_COREDEVICE_LOG}"
    launch
    --terminate-existing
    --device "${DEVICECTL_DEVICE_ID}"
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
  validate_host_user_cache
  mkdir -p "$(dirname "${PREFLIGHT_JSON}")"
  run_coredevice_command "apple-device-preflight" "${PREFLIGHT_CMD[@]}" || {
    echo "Device preflight failed. Confirm the device is connected, awake, trusted, and visible to CoreDevice." >&2
    exit 1
  }
  echo "Device preflight passed for ${DEVICE_ID}."
  if [[ "${DEVICECTL_DEVICE_ID}" != "${DEVICE_ID}" ]]; then
    echo "Device selector ${DEVICE_ID} resolved to ${DEVICECTL_DEVICE_ID}."
  fi
  exit 0
fi

if [[ "${VERIFY_ONLY}" == "1" ]]; then
  print_command "Installed app verification command" "${VERIFY_CMD[@]}"
  if [[ "${DRY_RUN}" == "1" ]]; then
    exit 0
  fi
  validate_host_user_cache
  mkdir -p "$(dirname "${VERIFY_JSON}")"
  run_coredevice_command "apple-device-installed-app" "${VERIFY_CMD[@]}"
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

validate_host_user_cache

SOURCE_SYNC_EFFECTIVE_MODE="$(effective_source_sync_mode)"
if [[ "${LAUNCH_ONLY}" != "1" && "${PREFLIGHT_ONLY}" != "1" && "${VERIFY_ONLY}" != "1" && "${LIST}" != "1" ]]; then
  verify_deploy_source_freshness "${SOURCE_SYNC_EFFECTIVE_MODE}"
fi

mkdir -p "$(dirname "${INSTALL_JSON}")"

run_launch_command() {
  set +e
  local launch_status
  if [[ -n "${LAUNCH_CONSOLE_TIMEOUT}" ]]; then
    mkdir -p "$(dirname "${LAUNCH_LOG}")"
    : > "${LAUNCH_LOG}"
    rm -f "${LAUNCH_COREDEVICE_LOG}"
    local launch_stderr
    launch_stderr="$(coredevice_failure_log_path apple-device-launch)"
    mkdir -p "$(dirname "${launch_stderr}")"
    "${LAUNCH_CMD[@]}" 2> "${launch_stderr}" | tee -a "${LAUNCH_LOG}"
    launch_status=${PIPESTATUS[0]}
    if [[ -s "${launch_stderr}" ]]; then
      cat "${launch_stderr}" >&2
      {
        echo
        echo "--- CoreDevice stderr ---"
        cat "${launch_stderr}"
      } >> "${LAUNCH_LOG}"
    fi
    if [[ "${launch_status}" != "0" ]]; then
      explain_coredevice_failure_if_known "apple-device-launch" "${launch_stderr}"
    fi
    if [[ -s "${LAUNCH_COREDEVICE_LOG}" ]]; then
      {
        echo
        echo "--- CoreDevice --log-output ---"
        cat "${LAUNCH_COREDEVICE_LOG}"
      } >> "${LAUNCH_LOG}"
    fi
  else
    run_coredevice_command "apple-device-launch" "${LAUNCH_CMD[@]}"
    launch_status=$?
  fi
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
  run_coredevice_command "apple-device-preflight" "${PREFLIGHT_CMD[@]}" || {
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
        --device "${DEVICECTL_DEVICE_ID}"
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

run_coredevice_command "apple-device-install" "${INSTALL_CMD[@]}"

if [[ "${VERIFY_AFTER_INSTALL}" == "1" ]]; then
  run_coredevice_command "apple-device-installed-app" "${VERIFY_CMD[@]}"
  summarize_installed_app_json "${VERIFY_JSON}"
fi

if [[ "${LAUNCH}" == "1" ]]; then
  run_launch_command
fi
