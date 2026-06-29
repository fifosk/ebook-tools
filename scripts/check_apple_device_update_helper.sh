#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HELPER="${ROOT_DIR}/scripts/apple_unattended_device_update.sh"
FULL_ENTITLEMENT_PLANNER="${ROOT_DIR}/scripts/apple_full_entitlement_signing_plan.sh"
MERGE_ENTITLEMENTS="${ROOT_DIR}/scripts/apple_merge_entitlements.py"
MAKEFILE="${ROOT_DIR}/Makefile"

assert_contains() {
  local haystack="$1"
  local needle="$2"
  local message="$3"
  if [[ "${haystack}" != *"${needle}"* ]]; then
    echo "ERROR: ${message}" >&2
    echo "Expected to find: ${needle}" >&2
    echo "Output was:" >&2
    echo "${haystack}" >&2
    exit 1
  fi
}

assert_not_contains() {
  local haystack="$1"
  local needle="$2"
  local message="$3"
  if [[ "${haystack}" == *"${needle}"* ]]; then
    echo "ERROR: ${message}" >&2
    echo "Unexpectedly found: ${needle}" >&2
    echo "Output was:" >&2
    echo "${haystack}" >&2
    exit 1
  fi
}

bash -n "${HELPER}"
bash -n "${FULL_ENTITLEMENT_PLANNER}"
python3 -m py_compile "${MERGE_ENTITLEMENTS}"

makefile="$(cat "${MAKEFILE}")"
source_info="${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Supporting/Info.plist"
current_short_version="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "${source_info}")"
current_build_version="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "${source_info}")"
export FAKE_INSTALLED_SHORT_VERSION="${current_short_version}"
export FAKE_INSTALLED_BUILD="${current_build_version}"
assert_contains "${makefile}" "apple-device-full-entitlement-plan:" "Makefile should expose the full-entitlement signing planner"
assert_contains "${makefile}" 'bash scripts/apple_full_entitlement_signing_plan.sh --device "$(APPLE_DEVICE_ID)"' "Makefile planner target should call the planner script"
assert_contains "${makefile}" "--device \"\$(APPLE_DEVICE_ID)\"" "Makefile planner target should pass the selected device id"
assert_contains "${makefile}" "\$(if \$(strip \$(FULL_CAPABILITY_IOS_PROFILE)),--app-profile \"\$(FULL_CAPABILITY_IOS_PROFILE)\")" "Makefile planner target should pass the app provisioning profile only when overridden"
assert_contains "${makefile}" "\$(if \$(strip \$(WILDCARD_IOS_EXTENSION_PROFILE)),--extension-profile \"\$(WILDCARD_IOS_EXTENSION_PROFILE)\")" "Makefile planner target should pass the extension provisioning profile only when overridden"
assert_contains "${makefile}" "\$(if \$(strip \$(APPLE_DEVELOPMENT_IDENTITY)),--signing-identity \"\$(APPLE_DEVELOPMENT_IDENTITY)\")" "Makefile planner target should pass the signing identity only when overridden"
assert_contains "${makefile}" "apple-device-full-entitlement-fallback-install:" "Makefile should expose the full-entitlement signed-artifact fallback installer"
assert_contains "${makefile}" "--fallback-to-signed-artifact" "Makefile fallback installer should enable the signed-artifact fallback"
assert_contains "${makefile}" "--signed-artifact-path \"\$(APPLE_DEVICE_SIGNED_ARTIFACT_PATH)\"" "Makefile fallback installer should pass the configured signed artifact path"
assert_contains "${makefile}" "--launch-console-timeout \"\$(APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT)\"" "Makefile fallback installer should pass the launch crash-watch timeout"
assert_contains "${makefile}" "apple-device-full-entitlement-stable-install:" "Makefile should expose the direct full-entitlement stable artifact installer"
assert_contains "${makefile}" "--skip-build" "stable artifact installer should avoid rebuilding the cached signed app"
assert_contains "${makefile}" "--app-path \"\$(APPLE_DEVICE_SIGNED_ARTIFACT_PATH)\"" "stable artifact installer should install the configured signed artifact path"
assert_contains "${makefile}" "apple-device-launch-console:" "Makefile should expose a launch-only console helper"
assert_contains "${makefile}" "--launch-only" "launch-console helper should avoid build/install and only relaunch the app"

build_output="$(
  APPLE_DEVICE_SOURCE_SYNC_MODE=skip \
    bash "${HELPER}" --device TEST-DEVICE --dry-run --build-only
)"
assert_contains "${build_output}" "Build command:" "build-only dry run should print the build command"
assert_contains "${build_output}" "-configuration  Debug" "build-only dry run should include the default configuration"
assert_contains "${build_output}" "DerivedData-device-TEST-DEVICE" "build-only dry run should use a sanitized device-scoped derived data path"
assert_not_contains "${build_output}" "Install command:" "build-only dry run should not print install command"

fake_tools_dir="$(mktemp -d)"
trap 'rm -rf "${fake_tools_dir}"' EXIT
cat > "${fake_tools_dir}/devicectl" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
json_output=""
log_output=""
args="$*"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --json-output)
      json_output="${2:-}"
      shift 2
      ;;
    --log-output)
      log_output="${2:-}"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
mkdir -p "$(dirname "${json_output}")"
if [[ "${FAKE_COREDEVICE_INIT_FAILURE:-}" == "1" ]]; then
  echo 'Failed to load provisioning parameter list due to error: XPCError(errorCode: 1001, errorUserInfo: ["XPCConnectionDescription": "<SystemXPCPeerConnection> { name = com.apple.CoreDevice.CoreDeviceService }", "NSLocalizedDescription": "The connection was invalidated."]).' >&2
  echo 'ERROR: Timed out waiting for CoreDeviceService to fully initialize. This is likely a bug in CoreDevice.' >&2
  exit 1
fi
if [[ "${args}" == *"device info apps"* ]]; then
cat > "${json_output}" <<JSON
{"result":{"apps":[{"bundleIdentifier":"com.example.InteractiveReader","name":"InteractiveReader","version":"${FAKE_INSTALLED_SHORT_VERSION:-2026.6.26}","bundleVersion":"${FAKE_INSTALLED_BUILD:-20260626175}"}]}}
JSON
elif [[ "${args}" == *"device install app"* ]]; then
cat > "${json_output}" <<'JSON'
{"result":{"installed":true}}
JSON
elif [[ "${args}" == *"device process"* && "${args}" == *"launch"* && "${FAKE_LOCKED_LAUNCH:-}" == "1" ]]; then
cat > "${json_output}" <<'JSON'
{"error":{"code":10002,"domain":"com.apple.dt.CoreDeviceError","userInfo":{"NSUnderlyingError":{"error":{"domain":"FBSOpenApplicationServiceErrorDomain","userInfo":{"BSErrorCodeDescription":{"string":"RequestDenied"},"NSLocalizedFailureReason":{"string":"The request was denied by service delegate (SBMainWorkspace) for reason: Locked (\"Unable to launch com.example.InteractiveReader because the device was not, or could not be, unlocked\")."},"NSUnderlyingError":{"error":{"domain":"FBSOpenApplicationErrorDomain","userInfo":{"BSErrorCodeDescription":{"string":"Locked"},"NSLocalizedFailureReason":{"string":"Unable to launch com.example.InteractiveReader because the device was not, or could not be, unlocked."}}}}}}}}},"info":{"outcome":"failed"}}
JSON
exit 1
elif [[ "${args}" == *"device process"* && "${args}" == *"launch"* && "${args}" == *"--console"* ]]; then
cat > "${json_output}" <<'JSON'
{"info":{"outcome":"timeout","details":"Exceeded command timeout"}}
JSON
echo "InteractiveReaderTV fake streamed console line"
if [[ -n "${log_output}" ]]; then
  mkdir -p "$(dirname "${log_output}")"
  cat > "${log_output}" <<'LOG'
InteractiveReaderTV fake console line
LOG
fi
exit 2
else
cat > "${json_output}" <<'JSON'
{"result":{"device":{"hardwareProperties":{"udid":"FAKE-UDID-123"}}}}
JSON
fi
echo "fake device details"
SH
chmod +x "${fake_tools_dir}/devicectl"
cat > "${fake_tools_dir}/xcodebuild" <<'SH'
#!/usr/bin/env bash
printf 'fake xcodebuild'
printf ' %q' "$@"
printf '\n'
SH
chmod +x "${fake_tools_dir}/xcodebuild"
cat > "${fake_tools_dir}/failing-xcodebuild" <<'SH'
#!/usr/bin/env bash
echo "fake xcodebuild signing failure" >&2
exit 65
SH
chmod +x "${fake_tools_dir}/failing-xcodebuild"
cat > "${fake_tools_dir}/codesign" <<'SH'
#!/usr/bin/env bash
echo "fake codesign $*"
SH
chmod +x "${fake_tools_dir}/codesign"
cat > "${fake_tools_dir}/git" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
while [[ $# -gt 0 && "$1" == "-C" ]]; do
  shift 2
done
case "${1:-} ${2:-} ${3:-}" in
  "rev-parse --is-inside-work-tree "*)
    exit 0
    ;;
  "rev-parse --abbrev-ref HEAD")
    echo "main"
    ;;
  "rev-parse HEAD ")
    echo "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    ;;
  "fetch --prune origin"|"fetch --prune origin main")
    exit 0
    ;;
  "rev-parse refs/remotes/origin/main ")
    echo "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    ;;
  *)
    echo "fake git unexpected args: $*" >&2
    exit 2
    ;;
esac
SH
chmod +x "${fake_tools_dir}/git"
export PATH="${fake_tools_dir}:${PATH}"

set +e
stale_source_output="$(
  CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  DEVICECTL="${fake_tools_dir}/devicectl" \
  XCBUILD="${fake_tools_dir}/xcodebuild" \
  PATH="${fake_tools_dir}:${PATH}" \
  APPLE_DEVICE_SOURCE_SYNC_MODE=require \
    bash "${HELPER}" \
      --device TEST-DEVICE \
      --install \
      --skip-build \
      --app-path /tmp/InteractiveReader.app 2>&1
)"
stale_source_status=$?
set -e
if [[ "${stale_source_status}" == "0" ]]; then
  echo "ERROR: stale deploy source should fail before CoreDevice preflight" >&2
  echo "${stale_source_output}" >&2
  exit 1
fi
assert_contains "${stale_source_output}" "Deploy source checkout is not at origin/main: local aaaaaaaa, origin bbbbbbbb." "confirmed installs should refuse stale deploy source before build/install"
assert_contains "${stale_source_output}" "git pull --ff-only origin main" "stale deploy source failure should explain the fast-forward fix"
assert_not_contains "${stale_source_output}" "fake device details" "stale deploy source failure should happen before CoreDevice preflight"

set +e
source_skip_output="$(
  CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  DEVICECTL="${fake_tools_dir}/devicectl" \
  XCBUILD="${fake_tools_dir}/xcodebuild" \
  APPLE_DEVICE_SOURCE_SYNC_MODE=skip \
    bash "${HELPER}" \
      --device TEST-DEVICE \
      --install \
      --skip-build \
      --no-preflight \
      --no-verify \
      --app-path /tmp/InteractiveReader.app 2>&1
)"
source_skip_status=$?
set -e
if [[ "${source_skip_status}" == "0" ]]; then
  echo "ERROR: missing app path should still fail after explicit source-sync skip" >&2
  echo "${source_skip_output}" >&2
  exit 1
fi
assert_contains "${source_skip_output}" "Deploy source freshness check skipped by APPLE_DEVICE_SOURCE_SYNC_MODE=skip." "emergency source-sync override should be explicit in deploy output"
assert_contains "${source_skip_output}" "App bundle not found: /tmp/InteractiveReader.app" "source-sync skip should continue into the ordinary install path"
export APPLE_DEVICE_SOURCE_SYNC_MODE=skip

resolved_destination_output="$(
  DEVICECTL="${fake_tools_dir}/devicectl" \
  XCBUILD="${fake_tools_dir}/xcodebuild" \
    bash "${HELPER}" --device "Friendly iPad" --build-only
)"
assert_contains "${resolved_destination_output}" "Resolved xcodebuild destination id: FAKE-UDID-123" "real build path should resolve friendly device selectors to hardware UDIDs"
assert_contains "${resolved_destination_output}" "-destination id=FAKE-UDID-123" "xcodebuild should receive the resolved hardware UDID"
assert_not_contains "${resolved_destination_output}" "-destination id=Friendly\\ iPad" "xcodebuild should not receive the friendly device name as an id"

preflight_output="$(bash "${HELPER}" --device TEST-DEVICE --dry-run --device-preflight-only)"
assert_contains "${preflight_output}" "Device preflight command:" "preflight dry run should print the preflight command"
assert_contains "${preflight_output}" "device  info  details" "preflight should query device health without mutation"
assert_contains "${preflight_output}" "apple-device-preflight-TEST-DEVICE.json" "preflight should write a script-readable JSON path"
assert_not_contains "${preflight_output}" "--bundle-id" "preflight should not require the app to already be installed"

verify_output="$(bash "${HELPER}" --device TEST-DEVICE --dry-run --verify-installed)"
assert_contains "${verify_output}" "Installed app verification command:" "verify dry run should print app metadata verification"
assert_contains "${verify_output}" "apple-device-installed-app-TEST-DEVICE.json" "verify dry run should write a script-readable JSON path"

set +e
coredevice_failure_output="$(
  DEVICECTL="${fake_tools_dir}/devicectl" \
  FAKE_COREDEVICE_INIT_FAILURE=1 \
    bash "${HELPER}" \
      --device TEST-DEVICE \
      --device-preflight-only 2>&1
)"
coredevice_failure_status=$?
set -e
if [[ "${coredevice_failure_status}" == "0" ]]; then
  echo "ERROR: CoreDevice initialization failure should fail preflight" >&2
  echo "${coredevice_failure_output}" >&2
  exit 1
fi
assert_contains "${coredevice_failure_output}" "CoreDeviceService failed during apple-device-preflight" "CoreDevice XPC failures should get a concrete diagnostic"
assert_contains "${coredevice_failure_output}" "launchctl kickstart -k user/" "CoreDevice diagnostic should include the local service restart command"
assert_contains "${coredevice_failure_output}" "Captured CoreDevice stderr:" "CoreDevice diagnostic should preserve the captured stderr path"
assert_contains "${coredevice_failure_output}" "Device preflight failed." "preflight should still fail after printing CoreDevice diagnostics"

install_output="$(
  CONFIRM_PHYSICAL_DEVICE_UPDATE=YES bash "${HELPER}" \
    --device TEST-DEVICE \
    --dry-run \
    --install \
    --skip-build \
    --app-path /tmp/InteractiveReader.app \
    --launch
)"
assert_not_contains "${install_output}" "Build command:" "skip-build install dry run should not print a build command"
assert_contains "${install_output}" "Device preflight command:" "install dry run should print the pre-install device preflight"
assert_contains "${install_output}" "device  info  details" "install dry run should preflight CoreDevice before install"
assert_contains "${install_output}" "Install command:" "install dry run should print install command"
assert_contains "${install_output}" "Post-install verification command:" "install dry run should verify installed metadata by default"
assert_contains "${install_output}" "Launch command:" "install --launch dry run should print launch command"
assert_contains "${install_output}" "--json-output  ${ROOT_DIR}/test-results/apple-device-launch-TEST-DEVICE.json  com.example.InteractiveReader" "launch output options should appear before the bundle id"

launch_only_dry_run_output="$(
  bash "${HELPER}" \
    --device TEST-DEVICE \
    --dry-run \
    --launch-only \
    --launch-console-timeout 45
)"
assert_contains "${launch_only_dry_run_output}" "Launch command:" "launch-only dry run should print the launch command"
assert_contains "${launch_only_dry_run_output}" "device  process  --timeout  45" "launch-only dry run should attach console with the requested timeout"
assert_contains "${launch_only_dry_run_output}" "--console" "launch-only dry run should attach to app output"
assert_contains "${launch_only_dry_run_output}" "--log-output  ${ROOT_DIR}/test-results/apple-device-launch-console-TEST-DEVICE.coredevice.log" "launch-only dry run should persist CoreDevice output to a predictable raw log file"
assert_not_contains "${launch_only_dry_run_output}" "Build command:" "launch-only dry run should not build"
assert_not_contains "${launch_only_dry_run_output}" "Install command:" "launch-only dry run should not install"

no_preflight_output="$(
  CONFIRM_PHYSICAL_DEVICE_UPDATE=YES bash "${HELPER}" \
    --device TEST-DEVICE \
    --dry-run \
    --install \
    --skip-build \
    --no-preflight \
    --app-path /tmp/InteractiveReader.app
)"
assert_not_contains "${no_preflight_output}" "Device preflight command:" "install --no-preflight dry run should omit the pre-install preflight"
assert_contains "${no_preflight_output}" "Install command:" "install --no-preflight should still show the install command"

provisioning_output="$(
  bash "${HELPER}" \
    --device TEST-DEVICE \
    --dry-run \
    --build-only \
    --allow-provisioning-updates \
    --team-id ABC123XYZ \
    --configuration Release
)"
assert_contains "${provisioning_output}" "-allowProvisioningUpdates" "provisioning dry run should expose Xcode account refresh option"
assert_contains "${provisioning_output}" "DEVELOPMENT_TEAM=ABC123XYZ" "provisioning dry run should pass the requested development team"
assert_contains "${provisioning_output}" "-configuration  Release" "provisioning dry run should honor custom configuration"

fallback_dry_run_output="$(
  CONFIRM_PHYSICAL_DEVICE_UPDATE=YES bash "${HELPER}" \
    --device TEST-DEVICE \
    --dry-run \
    --install \
    --fallback-to-signed-artifact \
    --signed-artifact-path /tmp/InteractiveReader-signed.app
)"
assert_contains "${fallback_dry_run_output}" "Signed artifact fallback path: /tmp/InteractiveReader-signed.app" "signed-artifact fallback dry run should print the fallback app path"
assert_contains "${fallback_dry_run_output}" "Install command:" "signed-artifact fallback dry run should still show the primary install command"

signed_artifact_dir="$(mktemp -d)"
signed_artifact="${signed_artifact_dir}/InteractiveReader.app"
mkdir -p "${signed_artifact}"
cat > "${signed_artifact}/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleIdentifier</key>
  <string>com.example.InteractiveReader</string>
  <key>CFBundleShortVersionString</key>
  <string>CURRENT_SHORT_VERSION</string>
  <key>CFBundleVersion</key>
  <string>CURRENT_BUILD_VERSION</string>
</dict>
</plist>
PLIST
perl -pi -e "s/CURRENT_SHORT_VERSION/${current_short_version}/g; s/CURRENT_BUILD_VERSION/${current_build_version}/g" "${signed_artifact}/Info.plist"
fallback_install_output="$(
  CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  DEVICECTL="${fake_tools_dir}/devicectl" \
  XCBUILD="${fake_tools_dir}/failing-xcodebuild" \
  CODESIGN="${fake_tools_dir}/codesign" \
    bash "${HELPER}" \
      --device TEST-DEVICE \
      --install \
      --fallback-to-signed-artifact \
      --signed-artifact-path "${signed_artifact}"
)"
assert_contains "${fallback_install_output}" "xcodebuild failed with status 65; verifying signed artifact fallback." "signed-artifact fallback should run after xcodebuild failure"
assert_contains "${fallback_install_output}" "Signed artifact fallback install command:" "signed-artifact fallback should print the swapped install command"
assert_contains "${fallback_install_output}" "${signed_artifact}" "signed-artifact fallback should install the verified artifact path"
assert_contains "${fallback_install_output}" "Verified installed app: InteractiveReader com.example.InteractiveReader version=${current_short_version} build=${current_build_version}" "signed-artifact fallback should still verify installed metadata"

stable_install_output="$(
  CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  DEVICECTL="${fake_tools_dir}/devicectl" \
  CODESIGN="${fake_tools_dir}/codesign" \
    bash "${HELPER}" \
      --device TEST-DEVICE \
      --install \
      --skip-build \
      --app-path "${signed_artifact}" \
      --fallback-to-signed-artifact
)"
assert_not_contains "${stable_install_output}" "Build command:" "stable signed-artifact install should not drive Xcode"
assert_contains "${stable_install_output}" "fake codesign --verify --deep --strict --verbose=4 ${signed_artifact}" "stable signed-artifact install should verify the app bundle before install"
assert_contains "${stable_install_output}" "${signed_artifact}" "stable signed-artifact install should use the verified artifact path"
assert_contains "${stable_install_output}" "Verified installed app: InteractiveReader com.example.InteractiveReader version=${current_short_version} build=${current_build_version}" "stable signed-artifact install should still verify installed metadata"

stale_artifact="${signed_artifact_dir}/InteractiveReader-stale.app"
mkdir -p "${stale_artifact}"
cat > "${stale_artifact}/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleIdentifier</key>
  <string>com.example.InteractiveReader</string>
  <key>CFBundleShortVersionString</key>
  <string>${current_short_version}</string>
  <key>CFBundleVersion</key>
  <string>20260626121</string>
</dict>
</plist>
PLIST
set +e
stale_install_output="$(
  CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  DEVICECTL="${fake_tools_dir}/devicectl" \
  CODESIGN="${fake_tools_dir}/codesign" \
    bash "${HELPER}" \
      --device TEST-DEVICE \
      --install \
      --skip-build \
      --app-path "${stale_artifact}" \
      --fallback-to-signed-artifact 2>&1
)"
stale_install_status=$?
set -e
if [[ "${stale_install_status}" == "0" ]]; then
  echo "ERROR: stale signed-artifact install should fail before install" >&2
  echo "${stale_install_output}" >&2
  exit 1
fi
assert_contains "${stale_install_output}" "fake codesign --verify --deep --strict --verbose=4 ${stale_artifact}" "stale stable install should verify the app bundle before touching the device"
assert_contains "${stale_install_output}" "Signed artifact build 20260626121 does not match current ${current_build_version}." "stale stable install should fail on current build mismatch"
assert_not_contains "${stale_install_output}" "fake device details" "stale stable install should fail before executing CoreDevice preflight"
assert_not_contains "${stale_install_output}" "App installed:" "stale stable install should not install stale artifacts"

locked_launch_output="$(
  CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  DEVICECTL="${fake_tools_dir}/devicectl" \
  CODESIGN="${fake_tools_dir}/codesign" \
  FAKE_LOCKED_LAUNCH=1 \
    bash "${HELPER}" \
      --device TEST-DEVICE \
      --install \
      --skip-build \
      --app-path "${signed_artifact}" \
      --fallback-to-signed-artifact \
      --launch
)"
assert_contains "${locked_launch_output}" "Verified installed app: InteractiveReader com.example.InteractiveReader version=${current_short_version} build=${current_build_version}" "locked launch path should still verify installed metadata"
assert_contains "${locked_launch_output}" "Launch was denied because the device is locked; install and metadata verification already completed." "locked launch should be reported without failing the deploy"

launch_only_output="$(
  CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  DEVICECTL="${fake_tools_dir}/devicectl" \
    bash "${HELPER}" \
      --device TEST-DEVICE \
      --launch-only \
      --launch-console-timeout 12
)"
assert_contains "${launch_only_output}" "Launch command:" "launch-only should print the CoreDevice launch command"
assert_contains "${launch_only_output}" "Launch console timeout reached after 12s; treating this as app-alive verification." "launch-only should reuse the console timeout success semantics"
assert_contains "${launch_only_output}" "Launch console log: ${ROOT_DIR}/test-results/apple-device-launch-console-TEST-DEVICE.log" "launch-only should report the persisted console log path"
assert_contains "$(cat "${ROOT_DIR}/test-results/apple-device-launch-console-TEST-DEVICE.log")" "InteractiveReaderTV fake console line" "launch-only should write console output to the persisted log path"
assert_contains "$(cat "${ROOT_DIR}/test-results/apple-device-launch-console-TEST-DEVICE.log")" "InteractiveReaderTV fake streamed console line" "launch-only should tee streamed app console output to the persisted log path"
assert_contains "$(cat "${ROOT_DIR}/test-results/apple-device-launch-console-TEST-DEVICE.log")" "--- CoreDevice --log-output ---" "launch-only should merge CoreDevice raw log output into the persisted log path"
assert_not_contains "${launch_only_output}" "Build command:" "launch-only should not build"
assert_not_contains "${launch_only_output}" "App installed:" "launch-only should not install"

appletv_output="$(
  bash "${HELPER}" \
    --device TEST-APPLE-TV \
    --dry-run \
    --build-only \
    --profile appletv
)"
assert_contains "${appletv_output}" "-scheme  InteractiveReaderTV" "Apple TV profile should select the tvOS app scheme"
assert_contains "${appletv_output}" "Debug-appletvos/InteractiveReaderTV.app" "Apple TV profile should derive the tvOS app bundle path"

appletv_install_output="$(
  CONFIRM_PHYSICAL_DEVICE_UPDATE=YES bash "${HELPER}" \
    --device TEST-APPLE-TV \
    --dry-run \
    --install \
    --skip-build \
    --profile appletv
)"
assert_contains "${appletv_install_output}" "Debug-appletvos/InteractiveReaderTV.app" "Apple TV skip-build dry run should use the tvOS default app path"
assert_contains "${appletv_install_output}" "--bundle-id  com.example.InteractiveReader.tvos" "Apple TV profile should verify the tvOS bundle id"

profile_override_output="$(
  SCHEME=CustomScheme \
  PRODUCT_NAME=CustomApp \
  BUNDLE_ID=com.example.Custom \
  APPLE_DEVICE_PLATFORM_PRODUCT_DIR=customos \
    bash "${HELPER}" \
      --device TEST-DEVICE \
      --dry-run \
      --build-only \
      --profile appletv
)"
assert_contains "${profile_override_output}" "-scheme  CustomScheme" "explicit SCHEME should override profile defaults"
assert_contains "${profile_override_output}" "Debug-customos/CustomApp.app" "explicit product output settings should override profile defaults"

set +e
bad_profile_output="$(
  bash "${HELPER}" \
    --device TEST-DEVICE \
    --dry-run \
    --build-only \
    --profile watch 2>&1
)"
bad_profile_status=$?
set -e
if [[ "${bad_profile_status}" -eq 0 ]]; then
  echo "ERROR: unknown profile should fail before building" >&2
  exit 1
fi
assert_contains "${bad_profile_output}" "Unknown device profile: watch" "unknown profile should explain the bad profile name"

set +e
strip_refusal_output="$(
  CONFIRM_PHYSICAL_DEVICE_UPDATE=YES bash "${HELPER}" \
    --device TEST-DEVICE \
    --dry-run \
    --install \
    --configuration Release \
    --strip-ios-entitlements-for-local-signing 2>&1
)"
strip_refusal_status=$?
set -e
if [[ "${strip_refusal_status}" -eq 0 ]]; then
  echo "ERROR: entitlement-stripping fallback should require an explicit unlock" >&2
  exit 1
fi
assert_contains "${strip_refusal_output}" "APPLE_DEVICE_ALLOW_ENTITLEMENT_STRIPPING=YES" "entitlement stripping should require an explicit unlock"
assert_contains "${strip_refusal_output}" "full-entitlement codesign fallback" "entitlement stripping refusal should point to the safer iCloud-preserving fallback"

local_signing_output="$(
  APPLE_DEVICE_ALLOW_ENTITLEMENT_STRIPPING=YES \
  CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
    bash "${HELPER}" \
    --device TEST-DEVICE \
    --dry-run \
    --install \
    --configuration Release \
    --strip-ios-entitlements-for-local-signing \
    --launch \
    --launch-console-timeout 12
)"
assert_contains "${local_signing_output}" "Local signing patch: temporarily strip iOS app entitlements during build, then restore project file." "local signing dry run should explain the transient entitlement patch"
assert_contains "${local_signing_output}" "device  process  --timeout  12" "console launch should put process-level timeout before launch"
assert_contains "${local_signing_output}" "--console" "console launch dry run should attach to app output"
assert_contains "${local_signing_output}" "--log-output" "console launch dry run should persist CoreDevice console output"
assert_contains "${local_signing_output}" "--environment-variables  \\{\\\"OS_ACTIVITY_DT_MODE\\\":\\\"YES\\\"\\}" "console launch should enable app activity logs"

set +e
refusal_output="$(
  bash "${HELPER}" \
    --device TEST-DEVICE \
    --install \
    --skip-build \
    --app-path /tmp/InteractiveReader.app \
    2>&1
)"
refusal_status=$?
set -e
if [[ "${refusal_status}" -eq 0 ]]; then
  echo "ERROR: install without confirmation should fail before touching a device" >&2
  exit 1
fi
assert_contains "${refusal_output}" "CONFIRM_PHYSICAL_DEVICE_UPDATE=YES" "install without confirmation should explain the physical-device guard"

set +e
launch_refusal_output="$(
  bash "${HELPER}" \
    --device TEST-DEVICE \
    --launch-only \
    --launch-console-timeout 12 \
    2>&1
)"
launch_refusal_status=$?
set -e
if [[ "${launch_refusal_status}" -eq 0 ]]; then
  echo "ERROR: launch-only without confirmation should fail before touching a device" >&2
  exit 1
fi
assert_contains "${launch_refusal_output}" "Refusing to launch on a physical device without CONFIRM_PHYSICAL_DEVICE_UPDATE=YES" "launch-only without confirmation should explain the physical-device guard"
assert_not_contains "${launch_refusal_output}" "Install command:" "launch-only refusal should not print install command"

echo "apple unattended device update helper checks passed"
