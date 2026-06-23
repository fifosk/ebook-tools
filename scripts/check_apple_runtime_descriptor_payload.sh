#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d /tmp/ebook-tools-apple-runtime.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT

swiftc \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Models/AuthApiModels.swift" \
  "${ROOT_DIR}/scripts/tests/check_apple_runtime_descriptor_payload.swift" \
  -o "${TMP_DIR}/check_apple_runtime_descriptor_payload"

"${TMP_DIR}/check_apple_runtime_descriptor_payload"
