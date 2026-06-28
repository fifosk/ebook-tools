#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d /tmp/ebook-tools-apple-sequence-pause.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT

swiftc \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Services/SequencePlaybackController.swift" \
  "${ROOT_DIR}/scripts/tests/check_sequence_pause_cancel.swift" \
  -o "${TMP_DIR}/check_sequence_pause_cancel"

"${TMP_DIR}/check_sequence_pause_cancel"

echo "apple sequence pause cancellation checks passed"
