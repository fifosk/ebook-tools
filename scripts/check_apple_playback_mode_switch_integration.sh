#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d /tmp/ebook-tools-apple-mode-switch.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT

swiftc \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/AudioModeManager.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/SentencePositionProvider.swift" \
  "${ROOT_DIR}/scripts/tests/check_playback_mode_switch_integration.swift" \
  -o "${TMP_DIR}/check_playback_mode_switch_integration"

"${TMP_DIR}/check_playback_mode_switch_integration"

echo "apple playback mode switch integration checks passed"
