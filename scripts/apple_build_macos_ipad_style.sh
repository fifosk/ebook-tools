#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
XCBUILD="${XCBUILD:-/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild}"
XCPROJ="${XCPROJ:-${ROOT_DIR}/ios/InteractiveReader/InteractiveReader.xcodeproj}"
SCHEME="${SCHEME:-InteractiveReader}"
DERIVED_DATA="${MACOS_IPAD_DERIVED_DATA:-${ROOT_DIR}/test-results/DerivedData-macos-ipad-style}"
CODE_SIGNING_ALLOWED="${CODE_SIGNING_ALLOWED:-NO}"
DESTINATION="${MACOS_IPAD_DESTINATION:-}"
QUIET_FLAG=()

if [[ "${XCODEBUILD_QUIET:-1}" != "0" ]]; then
  QUIET_FLAG=(-quiet)
fi

if [[ -z "${DESTINATION}" ]]; then
  DESTINATION_ID="$(
    "${XCBUILD}" -project "${XCPROJ}" -scheme "${SCHEME}" -showdestinations \
      | python3 -c 'import re, sys
text = sys.stdin.read().splitlines()
for line in text:
    if "platform:macOS" in line and "variant:Designed for [iPad,iPhone]" in line:
        match = re.search(r"id:([^,}]+)", line)
        if match:
            print(match.group(1).strip())
            raise SystemExit(0)
raise SystemExit("No local macOS Designed for iPad/iPhone destination was found.")'
  )"
  DESTINATION="platform=macOS,id=${DESTINATION_ID}"
fi

echo "Building ${SCHEME} for ${DESTINATION}"
"${XCBUILD}" \
  -project "${XCPROJ}" \
  -scheme "${SCHEME}" \
  -destination "${DESTINATION}" \
  -derivedDataPath "${DERIVED_DATA}" \
  CODE_SIGNING_ALLOWED="${CODE_SIGNING_ALLOWED}" \
  "${QUIET_FLAG[@]}" \
  build

echo "Built app: ${DERIVED_DATA}/Build/Products/Debug-iphoneos/InteractiveReader.app"
