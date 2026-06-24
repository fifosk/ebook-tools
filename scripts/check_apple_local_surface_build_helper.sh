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
verify_line="verify-apple-local-surfaces: test-apple-contracts build-apple-local-surfaces"

assert_contains "${makefile}" "${target_line}" "Makefile should expose one local Apple surface build gate"
assert_contains "${makefile}" "${verify_line}" "Makefile should expose one non-physical Apple verification gate"
assert_contains "${makefile}" "build-apple-ios-simulators: build-apple-iphone-simulator build-apple-ipad-simulator" "local surface build should include iPhone and iPad simulator builds"
assert_contains "${makefile}" "build-apple-tvos-simulator:" "local surface build should include the tvOS simulator build lane"
assert_contains "${makefile}" "build-apple-macos-ipad-style:" "local surface build should include the local Mac iPad-style build lane"
assert_not_contains "${target_line}" "apple-device-update" "local surface build should not depend on physical-device update targets"
assert_not_contains "${target_line}" "apple_unattended_device_update.sh" "local surface build should not route through physical-device deployment"
assert_not_contains "${verify_line}" "apple-device-update" "verification gate should not depend on physical-device update targets"
assert_not_contains "${verify_line}" "apple_unattended_device_update.sh" "verification gate should not route through physical-device deployment"

echo "apple local surface build helper checks passed"
