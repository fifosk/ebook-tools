#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d /tmp/ebook-tools-apple-position.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT

swiftc \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/SentencePositionProvider.swift" \
  "${ROOT_DIR}/scripts/tests/check_sentence_position_provider.swift" \
  -o "${TMP_DIR}/check_sentence_position_provider"

"${TMP_DIR}/check_sentence_position_provider"

echo "apple sentence position provider checks passed"
