#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d /tmp/ebook-tools-apple-context-builder.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT

swiftc \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Utilities/String+Extras.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Models/PipelineTimingApiModels.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Models/PipelineSentenceApiModels.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Models/PipelineMediaApiModels.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerModels.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/TextPlayerTimelineTypes.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/TextPlayerTimeline.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/TextPlayerTimeline+Helpers.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/TextPlayerTimeline+ActiveDisplay.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerContextBuilder.swift" \
  "${ROOT_DIR}/scripts/tests/check_interactive_context_builder.swift" \
  -o "${TMP_DIR}/check_interactive_context_builder"

"${TMP_DIR}/check_interactive_context_builder"

echo "apple interactive context builder checks passed"
