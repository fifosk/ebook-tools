#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HELPER="${ROOT_DIR}/scripts/apple_build_macos_ipad_style.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

FAKE_XCBUILD="${TMP_DIR}/xcodebuild"
CALL_LOG="${TMP_DIR}/xcodebuild.calls"

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

cat > "${FAKE_XCBUILD}" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

printf '%q ' "$@" >> "${FAKE_XCBUILD_CALL_LOG}"
printf '\n' >> "${FAKE_XCBUILD_CALL_LOG}"

for arg in "$@"; do
  if [[ "${arg}" == "-showdestinations" ]]; then
    cat <<'EOF'
Available destinations for the "InteractiveReader" scheme:
    { platform:iOS Simulator, id:SIM-IPHONE, OS:26.0, name:iPhone 17 Pro }
    { platform:macOS, arch:arm64, variant:Designed for [iPad,iPhone], id:LOCAL-MAC-123, name:My Mac }
EOF
    exit 0
  fi
  if [[ "${arg}" == "-showBuildSettings" ]]; then
    cat <<'EOF'
    BUILT_PRODUCTS_DIR = /tmp/ebook-tools-products/Debug-iphoneos
    FULL_PRODUCT_NAME = InteractiveReader.app
EOF
    exit 0
  fi
done

if [[ "${*: -1}" == "build" ]]; then
  echo "FAKE_BUILD_OK"
  exit 0
fi

exit 0
SH
chmod +x "${FAKE_XCBUILD}"

bash -n "${HELPER}"

show_output="$(
  FAKE_XCBUILD_CALL_LOG="${CALL_LOG}" XCBUILD="${FAKE_XCBUILD}" \
    bash "${HELPER}" --show-destination
)"
assert_contains "${show_output}" "platform=macOS,id=LOCAL-MAC-123" "destination resolver should pick Designed for iPad/iPhone"
assert_contains "${show_output}" "/tmp/ebook-tools-products/Debug-iphoneos/InteractiveReader.app" "destination resolver should report Xcode-derived app path"

dry_run_output="$(
  FAKE_XCBUILD_CALL_LOG="${CALL_LOG}" XCBUILD="${FAKE_XCBUILD}" CODE_SIGNING_ALLOWED=NO \
    bash "${HELPER}" --dry-run
)"
assert_contains "${dry_run_output}" "Dry run build command:" "dry run should print the build command"
assert_contains "${dry_run_output}" "-destination platform=macOS\\,id=LOCAL-MAC-123" "dry run should target local macOS"
assert_contains "${dry_run_output}" "CODE_SIGNING_ALLOWED=NO" "dry run should preserve unsigned local compile default"
assert_not_contains "${dry_run_output}" "platform=iOS" "macOS helper should not select iOS simulator destinations"

override_output="$(
  FAKE_XCBUILD_CALL_LOG="${CALL_LOG}" XCBUILD="${FAKE_XCBUILD}" \
    MACOS_IPAD_DESTINATION="platform=macOS,id=OVERRIDE-MAC" \
    MACOS_IPAD_DERIVED_DATA="${TMP_DIR}/DerivedData" \
    bash "${HELPER}" --dry-run
)"
assert_contains "${override_output}" "platform=macOS,id=OVERRIDE-MAC" "explicit destination override should be honored"
assert_contains "${override_output}" "${TMP_DIR}/DerivedData" "derived data override should be honored"

build_output="$(
  FAKE_XCBUILD_CALL_LOG="${CALL_LOG}" XCBUILD="${FAKE_XCBUILD}" XCODEBUILD_QUIET=0 \
    bash "${HELPER}"
)"
assert_contains "${build_output}" "FAKE_BUILD_OK" "non-dry-run helper should invoke xcodebuild build"
assert_contains "${build_output}" "Built app: /tmp/ebook-tools-products/Debug-iphoneos/InteractiveReader.app" "build should report the derived app path"

echo "apple macOS iPad-style helper checks passed"
