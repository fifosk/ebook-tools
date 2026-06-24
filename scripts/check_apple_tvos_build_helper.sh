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

assert_contains "${makefile}" "build-apple-tvos-simulator:" "Makefile should expose a quick tvOS simulator build target"
assert_contains "${makefile}" "TVOS_DESTINATION ?= 'platform=tvOS Simulator,name=Apple TV 4K (3rd generation)'" "tvOS build should default to a simulator destination"
assert_contains "${makefile}" "-scheme InteractiveReaderTV" "tvOS build should compile the shipping tvOS app scheme"
assert_contains "${makefile}" "-destination \$(TVOS_DESTINATION)" "tvOS build should reuse the shared tvOS destination"
assert_contains "${makefile}" "-derivedDataPath \$(TVOS_BUILD_DERIVED_DATA)" "tvOS build should write to a scoped DerivedData path"
assert_not_contains "${makefile}" "build-apple-tvos-simulator:"$'\n'$'\t'"bash scripts/apple_unattended_device_update.sh" "tvOS simulator build must not route through physical-device deployment"

echo "apple tvOS simulator build helper checks passed"
