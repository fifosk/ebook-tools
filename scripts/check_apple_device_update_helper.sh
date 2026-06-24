#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HELPER="${ROOT_DIR}/scripts/apple_unattended_device_update.sh"
FULL_ENTITLEMENT_PLANNER="${ROOT_DIR}/scripts/apple_full_entitlement_signing_plan.sh"
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

makefile="$(cat "${MAKEFILE}")"
assert_contains "${makefile}" "apple-device-full-entitlement-plan:" "Makefile should expose the full-entitlement signing planner"
assert_contains "${makefile}" "bash scripts/apple_full_entitlement_signing_plan.sh \\" "Makefile planner target should call the planner script"
assert_contains "${makefile}" "--device \"\$(APPLE_DEVICE_ID)\"" "Makefile planner target should pass the selected device id"
assert_contains "${makefile}" "--app-profile \"\$(FULL_CAPABILITY_IOS_PROFILE)\"" "Makefile planner target should pass the app provisioning profile"
assert_contains "${makefile}" "--extension-profile \"\$(WILDCARD_IOS_EXTENSION_PROFILE)\"" "Makefile planner target should pass the extension provisioning profile"
assert_contains "${makefile}" "--signing-identity \"\$(APPLE_DEVELOPMENT_IDENTITY)\"" "Makefile planner target should pass the signing identity"

build_output="$(bash "${HELPER}" --device TEST-DEVICE --dry-run --build-only)"
assert_contains "${build_output}" "Build command:" "build-only dry run should print the build command"
assert_contains "${build_output}" "-configuration  Debug" "build-only dry run should include the default configuration"
assert_contains "${build_output}" "DerivedData-device-TEST-DEVICE" "build-only dry run should use a sanitized device-scoped derived data path"
assert_not_contains "${build_output}" "Install command:" "build-only dry run should not print install command"

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
