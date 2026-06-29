#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d /tmp/ebook-tools-apple-jump-lock.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT

swiftc \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/SentencePositionProvider.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractiveSentenceJumpRenderLock.swift" \
  "${ROOT_DIR}/scripts/tests/check_sentence_jump_render_lock.swift" \
  -o "${TMP_DIR}/check_sentence_jump_render_lock"

"${TMP_DIR}/check_sentence_jump_render_lock"

echo "apple sentence jump render lock checks passed"
