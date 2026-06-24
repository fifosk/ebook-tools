#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HELPER="${ROOT_DIR}/scripts/apple_unattended_device_update.sh"

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
