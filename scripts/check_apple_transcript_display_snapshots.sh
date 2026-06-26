#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d /tmp/ebook-tools-apple-transcript-snapshots.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT

swiftc \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/TextPlayerTimelineTypes.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/TextPlayerTimeline.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/TextPlayerTimeline+Helpers.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/TextPlayerTimeline+DisplayBuilders.swift" \
  "${ROOT_DIR}/scripts/tests/check_transcript_display_snapshots.swift" \
  -o "${TMP_DIR}/check_transcript_display_snapshots"

"${TMP_DIR}/check_transcript_display_snapshots"

echo "apple transcript display snapshot checks passed"
