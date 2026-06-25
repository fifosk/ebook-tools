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
assert_contains "${makefile}" "apple-device-full-entitlement-plan:" "Makefile should expose the full-entitlement signing planner"
assert_contains "${makefile}" "bash scripts/apple_full_entitlement_signing_plan.sh \\" "Makefile planner target should call the planner script"
assert_contains "${makefile}" "--device \"\$(APPLE_DEVICE_ID)\"" "Makefile planner target should pass the selected device id"
assert_contains "${makefile}" "--app-profile \"\$(FULL_CAPABILITY_IOS_PROFILE)\"" "Makefile planner target should pass the app provisioning profile"
assert_contains "${makefile}" "--extension-profile \"\$(WILDCARD_IOS_EXTENSION_PROFILE)\"" "Makefile planner target should pass the extension provisioning profile"
assert_contains "${makefile}" "--signing-identity \"\$(APPLE_DEVELOPMENT_IDENTITY)\"" "Makefile planner target should pass the signing identity"
assert_contains "${makefile}" "apple-device-full-entitlement-fallback-install:" "Makefile should expose the full-entitlement signed-artifact fallback installer"
assert_contains "${makefile}" "--fallback-to-signed-artifact" "Makefile fallback installer should enable the signed-artifact fallback"
assert_contains "${makefile}" "--signed-artifact-path \"\$(APPLE_DEVICE_SIGNED_ARTIFACT_PATH)\"" "Makefile fallback installer should pass the configured signed artifact path"
assert_contains "${makefile}" "--launch-console-timeout \"\$(APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT)\"" "Makefile fallback installer should pass the launch crash-watch timeout"
assert_contains "${makefile}" "apple-device-full-entitlement-stable-install:" "Makefile should expose the direct full-entitlement stable artifact installer"
assert_contains "${makefile}" "--skip-build" "stable artifact installer should avoid rebuilding the cached signed app"
assert_contains "${makefile}" "--app-path \"\$(APPLE_DEVICE_SIGNED_ARTIFACT_PATH)\"" "stable artifact installer should install the configured signed artifact path"

build_output="$(bash "${HELPER}" --device TEST-DEVICE --dry-run --build-only)"
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
args="$*"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --json-output)
      json_output="${2:-}"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
mkdir -p "$(dirname "${json_output}")"
if [[ "${args}" == *"device info apps"* ]]; then
cat > "${json_output}" <<'JSON'
{"result":{"apps":[{"bundleIdentifier":"com.example.InteractiveReader","name":"InteractiveReader","version":"2026.6.25","bundleVersion":"202606259"}]}}
JSON
elif [[ "${args}" == *"device install app"* ]]; then
cat > "${json_output}" <<'JSON'
{"result":{"installed":true}}
JSON
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
  <string>2026.6.25</string>
  <key>CFBundleVersion</key>
  <string>202606259</string>
</dict>
</plist>
PLIST
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
assert_contains "${fallback_install_output}" "Verified installed app: InteractiveReader com.example.InteractiveReader version=2026.6.25 build=202606259" "signed-artifact fallback should still verify installed metadata"

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
assert_contains "${stable_install_output}" "Verified installed app: InteractiveReader com.example.InteractiveReader version=2026.6.25 build=202606259" "stable signed-artifact install should still verify installed metadata"

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

echo "apple unattended device update helper checks passed"
