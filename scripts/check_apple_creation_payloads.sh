#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d /tmp/ebook-tools-apple-contracts.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT

swiftc \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Utilities/String+Extras.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Models/ApiModels.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Utilities/JSONValue+Helpers.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Models/LibraryJobApiModels.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Models/PipelineCreationApiModels.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Utilities/SubtitleTimecodeInput.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Shared/PlayerLanguageFlagResolver.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateModels.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateOptions.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateDefaults.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreatePresentationHelpers.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateNormalization.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateDrafts.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateHistoryParsing.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateHistoryDefaults.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateFileImport.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateLanguageOptions.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateVoicePreviewSamples.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateRouting.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateSupport.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateMetadataSources.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateSourceSelection.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateStorageKeys.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreatePreferences.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateTemplateSettings.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreatePayloadFactory.swift" \
  "${ROOT_DIR}/ios/InteractiveReader/InteractiveReader/Features/Create/AppleBookCreateMediaPayloads.swift" \
  "${ROOT_DIR}/scripts/tests/check_apple_creation_payloads.swift" \
  -o "${TMP_DIR}/check_apple_creation_payloads"

"${TMP_DIR}/check_apple_creation_payloads"
