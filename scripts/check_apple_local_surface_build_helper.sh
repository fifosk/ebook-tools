#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAKEFILE="${ROOT_DIR}/Makefile"

assert_contains() {
  local haystack="$1"
  local needle="$2"
  local message="$3"
  if [[ "${haystack}" != *"${needle}"* ]]; then
    echo "ERROR: ${message}" >&2
    echo "Expected to find: ${needle}" >&2
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
    exit 1
  fi
}

makefile="$(<"${MAKEFILE}")"
target_line="build-apple-local-surfaces: build-apple-ios-simulators build-apple-tvos-simulator build-apple-macos-ipad-style"
verify_line="verify-apple-local-surfaces: test-apple-contracts build-apple-local-surfaces build-apple-ios-uitests"
checkpoint_line="verify-apple-cross-surface-checkpoint: test-web-create-intake-focused test-web-creation-templates-focused build-web-production verify-apple-local-surfaces"
office_ipad_target_line="build-apple-office-ipad-surfaces: build-apple-ipad-simulator build-apple-macos-ipad-style"
office_ipad_verify_line="verify-apple-office-ipad-surfaces: test-apple-contracts build-apple-office-ipad-surfaces build-apple-ios-uitests"

assert_contains "${makefile}" "${target_line}" "Makefile should expose one local Apple surface build gate"
assert_contains "${makefile}" "${verify_line}" "Makefile should expose one non-physical Apple verification gate"
assert_contains "${makefile}" "${checkpoint_line}" "Makefile should expose one Web plus Apple cross-surface checkpoint gate"
assert_contains "${makefile}" "${office_ipad_target_line}" "Makefile should expose an office-iPad local build gate"
assert_contains "${makefile}" "${office_ipad_verify_line}" "Makefile should expose an office-iPad local verification gate"
assert_contains "${makefile}" "test-web-create-intake-focused:" "cross-surface checkpoint should include the repo-owned Web Create intake focused tests"
assert_contains "${makefile}" "test-web-creation-templates-focused:" "cross-surface checkpoint should include the repo-owned Web creation-template focused tests"
assert_contains "${makefile}" "build-web-production:" "cross-surface checkpoint should include the repo-owned Web production/export build"
assert_contains "${makefile}" "build-apple-ios-simulators: build-apple-iphone-simulator build-apple-ipad-simulator" "local surface build should include iPhone and iPad simulator builds"
assert_contains "${makefile}" "build-apple-ios-uitests:" "local verification should include the iOS UITest build-for-testing lane"
assert_contains "${makefile}" "build-apple-tvos-simulator:" "local surface build should include the tvOS simulator build lane"
assert_contains "${makefile}" "build-apple-macos-ipad-style:" "local surface build should include the local Mac iPad-style build lane"
assert_not_contains "${office_ipad_target_line}" "build-apple-iphone-simulator" "office-iPad build should not depend on the iPhone simulator build"
assert_not_contains "${office_ipad_target_line}" "build-apple-ios-simulators" "office-iPad build should not depend on the combined iOS simulator gate"
assert_not_contains "${office_ipad_target_line}" "apple-device-update" "office-iPad build should not depend on physical-device update targets"
assert_not_contains "${office_ipad_target_line}" "apple_unattended_device_update.sh" "office-iPad build should not route through physical-device deployment"
assert_not_contains "${office_ipad_verify_line}" "build-apple-iphone-simulator" "office-iPad verification should not depend on the iPhone simulator build"
assert_not_contains "${office_ipad_verify_line}" "build-apple-ios-simulators" "office-iPad verification should not depend on the combined iOS simulator gate"
assert_not_contains "${office_ipad_verify_line}" "apple-device-update" "office-iPad verification should not depend on physical-device update targets"
assert_not_contains "${office_ipad_verify_line}" "apple_unattended_device_update.sh" "office-iPad verification should not route through physical-device deployment"
assert_not_contains "${target_line}" "apple-device-update" "local surface build should not depend on physical-device update targets"
assert_not_contains "${target_line}" "apple_unattended_device_update.sh" "local surface build should not route through physical-device deployment"
assert_not_contains "${verify_line}" "apple-device-update" "verification gate should not depend on physical-device update targets"
assert_not_contains "${verify_line}" "apple_unattended_device_update.sh" "verification gate should not route through physical-device deployment"
assert_not_contains "${checkpoint_line}" "apple-device-update" "cross-surface checkpoint should not depend on physical-device update targets"
assert_not_contains "${checkpoint_line}" "apple_unattended_device_update.sh" "cross-surface checkpoint should not route through physical-device deployment"

echo "apple local surface build helper checks passed"
