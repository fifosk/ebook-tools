#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d /tmp/ebook-tools-apple-audio-mode.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT

swiftc \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/AudioModeManager.swift" \
  "${ROOT_DIR}/scripts/tests/check_audio_mode_manager.swift" \
  -o "${TMP_DIR}/check_audio_mode_manager"

"${TMP_DIR}/check_audio_mode_manager"

echo "apple audio mode manager checks passed"
