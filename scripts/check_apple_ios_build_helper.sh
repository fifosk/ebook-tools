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

assert_contains "${makefile}" "build-apple-iphone-simulator:" "Makefile should expose a quick iPhone simulator build target"
assert_contains "${makefile}" "build-apple-ipad-simulator:" "Makefile should expose a quick iPad simulator build target"
assert_contains "${makefile}" "build-apple-ios-simulators: build-apple-iphone-simulator build-apple-ipad-simulator" "Makefile should expose a combined iOS simulator build target"
assert_contains "${makefile}" "build-apple-ios-uitests:" "Makefile should expose a quick iOS UITest build target"
assert_contains "${makefile}" "IPHONE_DESTINATION ?= 'platform=iOS Simulator,name=iPhone 17 Pro'" "iPhone build should default to an iOS simulator destination"
assert_contains "${makefile}" "IPAD_DESTINATION ?= 'platform=iOS Simulator,name=iPad Pro 13-inch (M5)'" "iPad build should default to an iPad simulator destination"
assert_contains "${makefile}" "-scheme InteractiveReader" "iOS builds should compile the shipping iOS app scheme"
assert_contains "${makefile}" "-scheme InteractiveReaderUITests" "iOS UITest build should compile the app-owned UI test scheme"
assert_contains "${makefile}" "build-for-testing" "iOS UITest build should compile tests without launching the simulator journey"
assert_contains "${makefile}" "-destination \$(IPHONE_DESTINATION)" "iPhone build should reuse the shared iPhone destination"
assert_contains "${makefile}" "-destination \$(IPAD_DESTINATION)" "iPad build should reuse the shared iPad destination"
assert_contains "${makefile}" "-derivedDataPath \$(IPHONE_BUILD_DERIVED_DATA)" "iPhone build should write to a scoped DerivedData path"
assert_contains "${makefile}" "-derivedDataPath \$(IPAD_BUILD_DERIVED_DATA)" "iPad build should write to a scoped DerivedData path"
assert_contains "${makefile}" "-derivedDataPath \$(IOS_UITEST_BUILD_DERIVED_DATA)" "iOS UITest build should write to a scoped DerivedData path"
assert_not_contains "${makefile}" "build-apple-iphone-simulator:"$'\n'$'\t'"bash scripts/apple_unattended_device_update.sh" "iPhone simulator build must not route through physical-device deployment"
assert_not_contains "${makefile}" "build-apple-ipad-simulator:"$'\n'$'\t'"bash scripts/apple_unattended_device_update.sh" "iPad simulator build must not route through physical-device deployment"
assert_not_contains "${makefile}" "build-apple-ios-uitests:"$'\n'$'\t'"bash scripts/apple_unattended_device_update.sh" "iOS UITest build must not route through physical-device deployment"

echo "apple iOS simulator build helper checks passed"
