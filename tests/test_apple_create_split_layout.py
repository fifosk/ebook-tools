from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import get_args

from modules.webapi.schemas.creation_templates import CreationTemplateMode


ROOT = Path(__file__).resolve().parents[1]
CREATE_VIEW = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateView.swift"
)
CREATE_PRESENTATION_STATE = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreatePresentationState.swift"
)
CREATE_SUBMISSION_ACTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateSubmissionActions.swift"
)
CREATE_LIFECYCLE = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateLifecycle.swift"
)
CREATE_LAYOUT = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateLayout.swift"
)
CREATE_SETTINGS_CONTENT = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateSettingsContent.swift"
)
CREATE_NARRATION_SECTION = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateNarrationSection.swift"
)
LIBRARY_SHELL = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Library"
    / "LibraryShellView.swift"
)
LIBRARY_BROWSE_CHROME = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Library"
    / "LibraryBrowseChrome.swift"
)
CREATE_VIEW_MODEL = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateViewModel.swift"
)
CREATE_VIEW_MODEL_SUBMISSION = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateViewModel+Submission.swift"
)
CREATE_VIEW_MODEL_METADATA = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateViewModel+Metadata.swift"
)
CREATE_VIEW_MODEL_TEMPLATES = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateViewModel+Templates.swift"
)
CREATE_VIEW_MODEL_SOURCES = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateViewModel+Sources.swift"
)
CREATE_SUPPORT = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateSupport.swift"
)
CREATE_PAYLOAD_FACTORY = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreatePayloadFactory.swift"
)
CREATE_MEDIA_PAYLOADS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateMediaPayloads.swift"
)
CREATE_ROUTING = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateRouting.swift"
)
CREATE_SOURCE_SELECTION = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateSourceSelection.swift"
)
CREATE_SOURCE_ACTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateSourceActions.swift"
)
CREATE_METADATA_ACTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateMetadataActions.swift"
)
CREATE_DERIVED_STATE = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateDerivedState.swift"
)
CREATE_STORAGE_KEYS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateStorageKeys.swift"
)
CREATE_PREFERENCES = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreatePreferences.swift"
)
CREATE_MODELS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateModels.swift"
)
PIPELINE_CREATION_API_MODELS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Models"
    / "PipelineCreationApiModels.swift"
)
API_CLIENT_CREATION = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Services"
    / "APIClient+Creation.swift"
)
API_CLIENT = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Services"
    / "APIClient.swift"
)
CREATE_OPTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateOptions.swift"
)
CREATE_DEFAULTS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateDefaults.swift"
)
CREATE_CREATION_OPTIONS_ACTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateCreationOptionsActions.swift"
)
CREATE_PRESENTATION_HELPERS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreatePresentationHelpers.swift"
)
CREATE_DISCOVERY_PRESENTATION = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateDiscoveryPresentation.swift"
)
CREATE_DOWNLOAD_STATION_PRESENTATION = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateDownloadStationPresentation.swift"
)
CREATE_VIDEO_DISCOVERY_PRESENTATION = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateVideoDiscoveryPresentation.swift"
)
CREATE_NORMALIZATION = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateNormalization.swift"
)
CREATE_DRAFTS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateDrafts.swift"
)
CREATE_DRAFT_ACTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateDraftActions.swift"
)
CREATE_LANGUAGE_OPTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateLanguageOptions.swift"
)
CREATE_VOICE_PREVIEW_SAMPLES = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateVoicePreviewSamples.swift"
)
CREATE_LANGUAGE_SELECTOR = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateLanguageSelector.swift"
)
CREATE_FILE_IMPORT = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateFileImport.swift"
)
CREATE_FILE_IMPORT_ACTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateFileImportActions.swift"
)
CREATE_FILE_IMPORTER_MODIFIER = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateFileImporterModifier.swift"
)
CREATE_METADATA_VIEWS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateMetadataViews.swift"
)
CREATE_METADATA_SOURCES = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateMetadataSources.swift"
)
CREATE_METADATA_JSON = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateMetadataJSON.swift"
)
CREATE_METADATA_BINDINGS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateMetadataBindings.swift"
)
CREATE_CONTROL_BINDINGS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateControlBindings.swift"
)
CREATE_SOURCE_CONTROLS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateSourceControls.swift"
)
CREATE_TEMPLATE_SETTINGS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateTemplateSettings.swift"
)
CREATE_TEMPLATE_ACTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateTemplateActions.swift"
)
CREATE_TEMPLATE_APPLICATION_ACTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateTemplateApplicationActions.swift"
)
CREATE_TEMPLATE_SAVE_PAYLOAD_FACTORY = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateTemplateSavePayloadFactory.swift"
)
CREATE_HISTORY_DEFAULTS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateHistoryDefaults.swift"
)
CREATE_HISTORY_DEFAULT_ACTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateHistoryDefaultActions.swift"
)
CREATE_HISTORY_PARSING = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateHistoryParsing.swift"
)
CREATE_SOURCE_SECTION = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateSourceSection.swift"
)
CREATE_SOURCE_SECTION_FACTORY = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateSourceSectionFactory.swift"
)
CREATE_SOURCE_CONTROLS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateSourceControls.swift"
)
CREATE_SOURCE_SUPPORT_CONTROLS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateSourceSupportControls.swift"
)
CREATE_YOUTUBE_SOURCE_CONTROLS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateYoutubeSourceControls.swift"
)
CREATE_YOUTUBE_DISCOVERY_CONTROLS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateYoutubeDiscoveryControls.swift"
)
CREATE_YOUTUBE_SOURCE_SUPPORT_CONTROLS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateYoutubeSourceSupportControls.swift"
)
CREATE_BASIC_SECTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateBasicSections.swift"
)
CREATE_OUTPUT_SECTION = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateOutputSection.swift"
)
CREATE_OUTPUT_CONTROLS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateOutputControls.swift"
)
CREATE_GENERATED_OUTPUT_CONTROLS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateGeneratedOutputControls.swift"
)
CREATE_GENERATED_IMAGE_CONTROLS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateGeneratedImageControls.swift"
)
INTERACTIVE_PLAYER_VIEW = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "InteractivePlayer"
    / "InteractivePlayerView.swift"
)
INTERACTIVE_PLAYER_INTERACTIVE_CONTENT = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "InteractivePlayer"
    / "InteractivePlayerView+InteractiveContent.swift"
)
INTERACTIVE_PLAYER_INPUT_HANDLERS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "InteractivePlayer"
    / "InteractivePlayerView+InputHandlers.swift"
)
INTERACTIVE_PLAYER_TRANSCRIPT = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "InteractivePlayer"
    / "InteractivePlayerView+Transcript.swift"
)
INTERACTIVE_PLAYER_PLAYBACK_MODEL = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "InteractivePlayer"
    / "InteractivePlayerViewModel+Playback.swift"
)
INTERACTIVE_PLAYER_SELECTION_MODEL = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "InteractivePlayer"
    / "InteractivePlayerViewModel+Selection.swift"
)
SENTENCE_POSITION_PROVIDER = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "InteractivePlayer"
    / "SentencePositionProvider.swift"
)
CREATE_VALUE_CONTROLS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateValueControls.swift"
)
CREATE_MEDIA_METADATA_SECTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateMediaMetadataSections.swift"
)
CREATE_MEDIA_METADATA_CONTROLS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateMediaMetadataControls.swift"
)
CREATE_STATUS_VIEWS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateStatusViews.swift"
)
XCODE_PROJECT = ROOT / "ios" / "InteractiveReader" / "InteractiveReader.xcodeproj" / "project.pbxproj"
APPLE_CREATION_PAYLOADS_SCRIPT = ROOT / "scripts" / "check_apple_creation_payloads.sh"
APPLE_CREATE_READINESS_SCRIPT = ROOT / "scripts" / "check_apple_create_readiness.py"
WEB_APP_VIEWS = ROOT / "web" / "src" / "utils" / "appViewDeepLink.ts"
BACKEND_URL_SAFETY = ROOT / "modules" / "services" / "acquisition" / "url_safety.py"
WEB_TEMPLATE_SANITIZER = ROOT / "web" / "src" / "utils" / "creationTemplateSanitizer.ts"
WEB_API_DTOS = ROOT / "web" / "src" / "api" / "dtos.ts"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _python_literal_assignment(path: Path, name: str) -> set[str]:
    tree = ast.parse(_source(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        value = ast.literal_eval(node.value)
        return {str(item) for item in value}
    raise AssertionError(f"Could not find Python literal assignment {name}")


def _typescript_string_array(source: str, name: str) -> set[str]:
    match = re.search(
        rf"const {re.escape(name)} = (?:new Set\()?\[(?P<body>.*?)\](?:\))?;",
        source,
        flags=re.S,
    )
    assert match is not None, f"Could not find TypeScript string array {name}"
    return set(re.findall(r"['\"]([^'\"]+)['\"]", match.group("body")))


def _typescript_string_union(source: str, name: str) -> set[str]:
    match = re.search(
        rf"export type {re.escape(name)}\s*=\s*(?P<body>.*?);",
        source,
        flags=re.S,
    )
    assert match is not None, f"Could not find TypeScript string union {name}"
    return set(re.findall(r"['\"]([^'\"]+)['\"]", match.group("body")))


def _swift_returned_string_array(source: str, signature: str) -> set[str]:
    body = _swift_function_body(source, signature)
    match = re.search(r"return\s+\[(?P<body>.*?)\]\.contains", body, flags=re.S)
    assert match is not None, f"Could not find returned Swift string array for {signature}"
    return set(re.findall(r'"([^"]+)"', match.group("body")))


def _swift_inline_string_array(source: str, signature: str, suffix: str) -> set[str]:
    body = _swift_function_body(source, signature)
    match = re.search(rf"\[(?P<body>.*?)\]\.{re.escape(suffix)}", body, flags=re.S)
    assert match is not None, f"Could not find Swift string array before .{suffix}"
    return set(re.findall(r'"([^"]+)"', match.group("body")))


def _normalized_sensitive_markers(markers: set[str]) -> set[str]:
    return {re.sub(r"[-_]", "", marker).casefold() for marker in markers}


def test_url_safety_markers_stay_aligned_across_backend_web_and_apple() -> None:
    backend_markers = _python_literal_assignment(BACKEND_URL_SAFETY, "SENSITIVE_KEY_MARKERS")
    backend_schemes = _python_literal_assignment(BACKEND_URL_SAFETY, "PUBLIC_URL_SCHEMES")
    web_source = _source(WEB_TEMPLATE_SANITIZER)
    swift_source = _source(CREATE_DRAFTS)

    web_markers = _typescript_string_array(web_source, "SENSITIVE_KEY_MARKERS")
    web_schemes = {scheme.removesuffix(":") for scheme in _typescript_string_array(web_source, "PUBLIC_URL_SCHEMES")}
    swift_markers = _swift_returned_string_array(
        swift_source,
        "private static func isSensitiveBookMetadataExtraKey(_ key: String) -> Bool",
    )
    swift_schemes = _swift_inline_string_array(
        swift_source,
        "private static func stripSensitiveURLParts(_ value: String) -> String",
        "contains(scheme)",
    )

    expected_markers = _normalized_sensitive_markers(backend_markers)
    assert _normalized_sensitive_markers(web_markers) == expected_markers
    assert _normalized_sensitive_markers(swift_markers) == expected_markers
    assert web_schemes == backend_schemes
    assert swift_schemes == backend_schemes


def test_interactive_player_uses_explicit_sentence_skip_and_gate_seeks() -> None:
    transcript_source = _source(INTERACTIVE_PLAYER_TRANSCRIPT)
    view_source = _source(INTERACTIVE_PLAYER_VIEW)
    content_source = _source(INTERACTIVE_PLAYER_INTERACTIVE_CONTENT)
    input_source = _source(INTERACTIVE_PLAYER_INPUT_HANDLERS)
    playback_model_source = _source(INTERACTIVE_PLAYER_PLAYBACK_MODEL)
    selection_model_source = _source(INTERACTIVE_PLAYER_SELECTION_MODEL)
    sentence_position_source = _source(SENTENCE_POSITION_PROVIDER)

    assert "func handleSentenceSkip(_ delta: Int, in chunk: InteractiveChunk)" in transcript_source
    assert "prepareExplicitSentenceJump(to: targetNumber)" in transcript_source
    assert "viewModel.jumpToSentence(targetNumber, autoPlay: audioCoordinator.isPlaybackRequested)" in transcript_source
    explicit_anchor_body = transcript_source.split("private func jumpByOneSentenceFromExplicitAnchor(", 1)[1].split(
        "\n    func stableSentenceIndexForNavigation",
        1,
    )[0]
    assert "SentencePositionProvider.sentenceIndex(" in explicit_anchor_body
    assert "let targetIndex = anchorIndex + step" in explicit_anchor_body
    assert "anchorSentenceNumber + step" not in explicit_anchor_body
    assert "func stableSentenceIndexForNavigation(in chunk: InteractiveChunk) -> Int?" in transcript_source
    assert "if audioCoordinator.isPlaying," in transcript_source
    assert "requestKeyboardShortcutFocus()" in transcript_source

    for source in (view_source, content_source, input_source):
        assert "handleSentenceSkip(" in source
        assert "viewModel.skipSentence(forward:" not in source

    assert "func gateStartTimeForSentence(" in selection_model_source
    assert "SentencePositionProvider.gateStartTime(" in selection_model_source
    assert "static func gateStartTime(" in sentence_position_source
    assert "case .translation:\n            candidate = sentence.startGate" in sentence_position_source
    assert "case .original:\n            candidate = sentence.originalStartGate" in sentence_position_source
    assert "let gate = gateStartTimeForSentence" in selection_model_source
    assert "let gate = gateStartTimeForSentence" in playback_model_source


def _call_arguments(source: str, start: int) -> str:
    depth = 0
    for index in range(start, len(source)):
        character = source[index]
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError("Could not parse AppleBookCreateView call arguments")


def _swift_struct_body(source: str, name: str) -> str:
    match = re.search(rf"\bstruct {re.escape(name)}\b[^\{{]*\{{", source)
    assert match is not None, f"Could not find Swift struct {name}"
    start = match.end() - 1
    depth = 0
    for index in range(start, len(source)):
        character = source[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1 : index]
    raise AssertionError(f"Could not parse Swift struct {name}")


def _swift_function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        character = source[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : index]
    raise AssertionError(f"Could not parse Swift function {signature}")


def _web_apple_create_views(source: str) -> dict[str, str]:
    constant_values = {
        name: value
        for name, value in re.findall(
            r"export const ([A-Z0-9_]+) = '([^']+)' as const;",
            _source(ROOT / "web" / "src" / "constants" / "appViews.ts"),
        )
    }
    object_match = re.search(
        r"export const APPLE_CREATE_WEB_VIEW_BY_MODE = \{(?P<body>.*?)\} as const;",
        source,
        flags=re.S,
    )
    assert object_match is not None

    modes: dict[str, str] = {}
    for mode, raw_value in re.findall(r"(\w+):\s*([^,\n]+)", object_match.group("body")):
        value = raw_value.strip().strip("'\"")
        modes[mode] = constant_values.get(value, value)
    return modes


def _swift_apple_create_views(source: str) -> dict[str, str]:
    return {
        mode: view
        for mode, view in re.findall(
            r"case \.(\w+):\s*return \"([^\"]+)\"",
            source,
        )
    }


def test_create_view_uses_shell_owned_mode_binding() -> None:
    source = _source(CREATE_VIEW)
    source_factory_source = _source(CREATE_SOURCE_SECTION_FACTORY)
    source_actions = _source(CREATE_SOURCE_ACTIONS)
    metadata_actions = _source(CREATE_METADATA_ACTIONS)
    lifecycle_source = _source(CREATE_LIFECYCLE)
    submission_actions_source = _source(CREATE_SUBMISSION_ACTIONS)
    project = _source(XCODE_PROJECT)

    assert "@Binding var creationMode: AppleCreateMode" in source
    assert "@State private var creationMode = AppleCreateMode.generatedBook" not in source
    assert "showsInlineJobTypePicker: Bool" in source
    assert "showsJobTypePicker: false" in source_factory_source
    assert "@Environment(\\.horizontalSizeClass) private var horizontalSizeClass" in source
    assert "private var usesRegularWidthCreateLayout: Bool" in source
    assert "horizontalSizeClass == .regular" in source
    assert "onLoadCreateDependencies: loadCreateDependencies" in source
    assert "await onLoadCreateDependencies()" in lifecycle_source
    assert "private func loadCreateDependencies() async" in source
    assert "handleSubtitleSourcePathChange()" in source_actions
    assert "func handleSubtitleSourcePathChange()" in source_actions
    assert "onYoutubeVideoPathChange(newValue)" in lifecycle_source
    assert "func handleYoutubeVideoPathChange(_ path: String)" in source_actions
    assert "handleLanguagePreferenceChange()" in source_actions
    assert "func handleLanguagePreferenceChange()" in source_actions
    assert "func completeSubmission(_ jobId: String?) async" in submission_actions_source
    assert submission_actions_source.count("await completeSubmission(jobId)") == 4
    assert submission_actions_source.count("onJobSubmitted(jobId)") == 1
    assert "private func completeSubmission(_ jobId: String?) async" not in source
    for helper in [
        "refreshVoiceInventory",
        "checkImageNodes",
        "previewVoice",
        "loadYoutubeTvMetadata",
        "loadYoutubeVideoMetadata",
        "clearYoutubeTvMetadataCache",
        "clearYoutubeVideoMetadataCache",
        "applyYoutubeAdvancedMetadataJSON",
        "syncYoutubeAdvancedMetadataJSON",
        "lookupSubtitleMetadata",
        "refreshSubtitleMetadata",
        "clearSubtitleMetadata",
        "clearSubtitleMetadataCache",
        "applySubtitleAdvancedMetadataJSON",
        "syncSubtitleAdvancedMetadataJSON",
        "retryCreationOptions",
    ]:
        assert f"func {helper}(" in metadata_actions
        assert f"private func {helper}(" not in source
    assert "AppleBookCreateMetadataActions.swift in Sources" in project
    assert project.count("AppleBookCreateMetadataActions.swift in Sources") == 4


def test_apple_create_can_load_and_apply_web_creation_templates() -> None:
    view_source = _source(CREATE_VIEW)
    presentation_state_source = _source(CREATE_PRESENTATION_STATE)
    submission_actions_source = _source(CREATE_SUBMISSION_ACTIONS)
    source_actions = _source(CREATE_SOURCE_ACTIONS)
    view_model_source = _source(CREATE_VIEW_MODEL)
    view_model_templates = _source(CREATE_VIEW_MODEL_TEMPLATES)
    status_views_source = _source(CREATE_STATUS_VIEWS)
    source_section_source = _source(CREATE_SOURCE_SECTION)
    template_settings_source = _source(CREATE_TEMPLATE_SETTINGS)
    template_actions_source = _source(CREATE_TEMPLATE_ACTIONS)
    template_application_source = _source(CREATE_TEMPLATE_APPLICATION_ACTIONS)
    template_save_factory_source = _source(CREATE_TEMPLATE_SAVE_PAYLOAD_FACTORY)
    source_controls_source = _source(CREATE_SOURCE_CONTROLS)
    draft_actions_source = _source(CREATE_DRAFT_ACTIONS)
    api_models_source = _source(PIPELINE_CREATION_API_MODELS)
    api_client_source = _source(API_CLIENT_CREATION)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "struct CreationTemplateListResponse: Decodable, Equatable" in api_models_source
    assert "struct CreationTemplateEntry: Decodable, Equatable, Identifiable" in api_models_source
    assert "struct CreationTemplateSaveRequest: Encodable, Equatable" in api_models_source
    assert "struct CreationTemplateDeleteResponse: Decodable, Equatable" in api_models_source
    assert "case templateId = \"template_id\"" in api_models_source
    assert "let createdAt: Double" in api_models_source
    assert "let updatedAt: Double" in api_models_source
    assert "case createdAt = \"created_at\"" not in api_models_source
    assert "case updatedAt = \"updated_at\"" not in api_models_source
    assert "var normalizedMode: String" in api_models_source
    assert "var displayName: String" in api_models_source

    assert "func fetchCreationTemplates(mode: String? = nil)" in api_client_source
    assert "AppleCreateRuntimeContract.templateListPath" in api_client_source
    assert "static func templatePath(_ encodedTemplateId: String)" in api_client_source
    assert "static func encodedTemplateID(_ templateId: String) -> String" in api_client_source
    assert "private static func encodedRouteID(_ value: String) -> String" in api_client_source
    assert "AppleAPIPathComponentEncoding.encode(trimmed)" in api_client_source
    assert "func fetchCreationTemplate(templateId: String) async throws -> CreationTemplateEntry" in api_client_source
    assert "AppleCreateRuntimeContract.encodedTemplateID(templateId)" in api_client_source
    assert "try decode(CreationTemplateEntry.self, from: data)" in api_client_source
    assert "func saveCreationTemplate(_ payload: CreationTemplateSaveRequest) async throws -> CreationTemplateEntry" in api_client_source
    assert 'method: "POST"' in api_client_source
    assert "client.saveCreationTemplate(request)" in view_model_templates
    assert "func deleteCreationTemplate(templateId: String) async throws -> CreationTemplateDeleteResponse" in api_client_source
    assert "AppleCreateRuntimeContract.templatePath(encoded)" in api_client_source
    assert 'method: "DELETE"' in api_client_source
    assert "try decode(CreationTemplateDeleteResponse.self, from: data)" in api_client_source
    assert 'URLQueryItem(name: "mode", value: mode)' in api_client_source

    assert "@Published var creationTemplates: [CreationTemplateEntry] = []" in view_model_source
    assert "@Published var isLoadingCreationTemplates = false" in view_model_source
    assert "@Published var isSavingCreationTemplate = false" in view_model_source
    assert "@Published var isDeletingCreationTemplate = false" in view_model_source
    assert "@Published var creationTemplatesErrorMessage: String?" in view_model_source
    assert "@Published var creationTemplateMessage: String?" in view_model_source
    assert "func loadCreationTemplates(" in view_model_templates
    assert "mode: String? = nil" in view_model_templates
    assert "client.fetchCreationTemplates(mode: mode)" in view_model_templates
    assert "func saveCreationTemplate(" in view_model_templates
    assert "creationTemplates.insert(saved, at: 0)" in view_model_templates
    assert "func deleteCreationTemplate(" in view_model_templates
    assert "let response = try await client.deleteCreationTemplate(templateId: trimmedID)" in view_model_templates
    assert "let deletedID = response.templateId.trimmingCharacters(in: .whitespacesAndNewlines)" in view_model_templates
    assert "let idsToRemove = Set([trimmedID, deletedID].filter { !$0.isEmpty })" in view_model_templates
    assert "guard !idsToRemove.isEmpty else" in view_model_templates
    assert "creationTemplates.removeAll { idsToRemove.contains($0.id) }" in view_model_templates
    assert "let didRemoveLocalTemplate = creationTemplates.count != templateCountBeforeRemoval" in view_model_templates
    assert "if response.deleted {" in view_model_templates
    assert 'creationTemplateMessage = "Removed stale saved template."' in view_model_templates

    assert "struct AppleBookCreateTemplateSection: View" in status_views_source
    for identifier in [
        "createBookTemplatePicker",
        "createBookSaveTemplateButton",
        "createBookApplyTemplateButton",
        "createBookDeleteTemplateButton",
        "createBookRefreshTemplatesButton",
        "createBookTemplateDetailSummary",
        "createBookTemplateStatusLabel",
        "createBookTemplateErrorLabel",
    ]:
        assert identifier in status_views_source
    assert "private struct AppleBookCreateTemplateDetailView: View" in status_views_source
    assert 'Label("Template Details", systemImage: "doc.text.magnifyingglass")' in status_views_source
    assert '"Type: \\(templateTypeLabel)"' in status_views_source
    assert '"Handoff source: \\(Self.displayLabel(source))"' in status_views_source
    assert "AppleBookCreateTemplateSettings.handoffSource(from: template)" in status_views_source
    assert "static func handoffSource(from template: CreationTemplateEntry) -> String?" in template_settings_source
    assert 'let nestedPayload = template.payload["payload"]?.objectValue ?? [:]' in template_settings_source
    assert 'string(template.payload, "handoff_source")' in template_settings_source
    assert 'string(template.payload, "handoffSource")' in template_settings_source
    assert 'string(nestedPayload, "handoff_source")' in template_settings_source
    assert 'string(nestedPayload, "handoffSource")' in template_settings_source
    assert '"Updated: \\(Self.updatedDateLabel(for: template.updatedAt))"' in status_views_source
    assert '"Saved fields: \\(formState.count)"' in status_views_source
    assert '"Discovery source: \\(Self.discoverySourceLabel(from: discoveryState))"' in status_views_source
    for discovery_key in [
        '"selected_provider"',
        '"source_provider"',
        '"acquisition_provider"',
        '"provider"',
        '"source_kind"',
    ]:
        assert discovery_key in status_views_source
    for forbidden_summary_key in [
        '"source_url"',
        '"cover_url"',
        '"candidate_id"',
        '"acquisition_candidate_id"',
        '"source_path"',
        '"video_path"',
    ]:
        assert forbidden_summary_key not in status_views_source
    assert "AppleBookCreateTemplateSettings.formState(from: template) ?? [:]" in status_views_source
    assert "AppleBookCreateTemplateSettings.discoveryState(from: template) ?? [:]" in status_views_source

    assert "private var templateSection: some View" in view_source
    assert "AppleBookCreateTemplateSection(" in view_source
    assert "extension AppleBookCreateView" in template_actions_source
    assert "func refreshCreationTemplatesFromSection()" in template_actions_source
    assert "await refreshCreationTemplates()" in view_source
    assert "func refreshCreationTemplates(force: Bool = false) async" in template_actions_source
    assert "func saveCurrentCreationTemplate()" in template_actions_source
    assert "func currentCreationTemplateSaveRequest() -> CreationTemplateSaveRequest?" in template_actions_source
    assert "AppleBookCreateTemplateSavePayloadFactory.makeGeneratedBookRequest(" in template_actions_source
    assert "cacheKey: creationTemplateLoadKey" in template_actions_source
    assert "mode: creationMode.creationTemplateMode" in template_actions_source
    assert "selectedTemplateID = template.id" in template_actions_source
    assert "func applySelectedCreationTemplate()" in template_actions_source
    assert "func requestDeleteSelectedCreationTemplate()" in template_actions_source
    assert "func deleteCreationTemplate(_ template: CreationTemplateEntry) async" in template_actions_source
    assert "creationTemplatePendingDelete = template" in template_actions_source
    assert "await viewModel.deleteCreationTemplate(" in template_actions_source
    assert "func applyCreationTemplate(_ template: CreationTemplateEntry)" in template_application_source
    assert "func applyCreationTemplate(_ template: CreationTemplateEntry)" not in view_source
    assert "extension AppleBookCreateView" in template_application_source
    assert "private func saveCurrentCreationTemplate()" not in view_source
    assert "private func currentCreationTemplateSaveRequest()" not in view_source
    assert "private func applySelectedCreationTemplate()" not in view_source
    assert "private func requestDeleteSelectedCreationTemplate()" not in view_source
    assert "private func deleteCreationTemplate(_ template: CreationTemplateEntry) async" not in view_source
    assert "AppleBookCreateTemplateSettings.compatibleTemplates(" in presentation_state_source
    assert "AppleBookCreateTemplateSettings.compatibleTemplates(" not in view_source
    assert "AppleBookCreateTemplateSettings.mode(for: template)" in template_application_source
    assert 'template.normalizedMode == "subtitle_job"' not in view_source
    assert 'template.normalizedMode == "youtube_dub"' not in view_source
    assert "private func applySubtitleCreationTemplate(" in template_application_source
    assert "private func applyYoutubeDubCreationTemplate(" in template_application_source
    assert "AppleBookCreateTemplateSettings.settings(from: template)" in template_application_source
    assert '@State var bookDiscoveryQuery = ""' in view_source
    assert "@State var bookDiscoveryProvider = AppleBookCreatePresentation.defaultBookDiscoveryProviderID" in view_source
    assert "discoveryQuery: $bookDiscoveryQuery" in source_section_source
    assert "discoveryProvider: $bookDiscoveryProvider" in source_section_source
    assert "@Binding var discoveryQuery: String" in source_controls_source
    assert "@Binding var discoveryProvider: String" in source_controls_source
    assert 'TextField("Search title or filename", text: $discoveryQuery)' in source_controls_source
    assert "onSearchAcquisitionDiscovery(discoveryQuery, acquisitionDiscoveryProvider)" in source_controls_source
    assert "private var acquisitionDiscoveryProvider: String" in source_controls_source
    assert "bookDiscoveryQuery: bookDiscoveryQuery" in draft_actions_source
    assert "bookDiscoveryProvider: bookDiscoveryProvider" in draft_actions_source
    assert "let bookDiscoveryQuery: String?" in _source(
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Features"
        / "Create"
        / "AppleBookCreateModels.swift"
    )
    assert "bookDiscoveryQuery: String? = nil" in _source(
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Features"
        / "Create"
        / "AppleBookCreateDrafts.swift"
    )
    assert "selectedProvider: draft.bookDiscoveryProvider" in template_save_factory_source
    assert "query: draft.bookDiscoveryQuery" in template_save_factory_source
    assert 'add(selectedProvider, named: "selected_provider", to: &state)' in template_save_factory_source
    assert 'add(query, named: "query", to: &state)' in template_save_factory_source
    assert "let selectedProvider: String?" in template_settings_source
    assert 'string(discoveryState, "selected_provider") ?? provider' in template_settings_source
    assert 'let query = string(discoveryState, "query")' in template_settings_source
    assert "bookDiscoveryProvider = provider" in template_application_source
    assert "bookDiscoveryQuery = query" in template_application_source
    subtitle_template_body = template_application_source.split("private func applySubtitleCreationTemplate(", 1)[1].split(
        "\n    private func applyYoutubeDubCreationTemplate",
        1,
    )[0]
    assert 'string(formState, "source_path") ?? AppleBookCreateTemplateSettings.string(formState, "subtitle_path")' not in subtitle_template_body
    assert "static func subtitleSourcePath(" in template_settings_source
    assert 'string(formState, "source_path") ?? string(formState, "subtitle_path")' in template_settings_source
    assert "sourcePath: subtitleSourcePath(formState: formState)" in template_settings_source
    assert "struct AppleSubtitleTemplateApplication" in template_settings_source
    assert "static func subtitleApplication(" in template_settings_source
    for subtitle_key in [
        '"input_language"',
        '"target_language"',
        '"output_format"',
        '"start_time"',
        '"end_time"',
        '"enable_transliteration"',
        '"highlight"',
        '"show_original"',
        '"generate_audio_book"',
        '"mirror_batches_to_source_dir"',
        '"translation_provider"',
        '"llm_model"',
        '"transliteration_mode"',
        '"transliteration_model"',
        '"worker_count"',
        '"batch_size"',
        '"translation_batch_size"',
        '"ass_font_size"',
        '"ass_emphasis_scale"',
    ]:
        assert subtitle_key in template_settings_source
    assert "AppleBookCreateTemplateSettings.subtitleApplication(from: formState)" in subtitle_template_body
    for subtitle_field in [
        "sourcePath",
        "inputLanguage",
        "targetLanguage",
        "outputFormat",
        "startTime",
        "endTime",
        "enableTransliteration",
        "highlight",
        "showOriginal",
        "generateAudioBook",
        "mirrorBatchesToSourceDir",
        "translationProvider",
        "llmModel",
        "transliterationMode",
        "transliterationModel",
        "workerCount",
        "batchSize",
        "translationBatchSize",
        "assFontSize",
        "assEmphasisScale",
    ]:
        assert f"subtitleApplication.{subtitle_field}" in subtitle_template_body
    for direct_parse in [
        'string(formState, "input_language")',
        'string(formState, "target_language")',
        'string(formState, "output_format")',
        'string(formState, "start_time")',
        'string(formState, "end_time")',
        'bool(formState, "enable_transliteration")',
        'bool(formState, "highlight")',
        'bool(formState, "show_original")',
        'bool(formState, "generate_audio_book")',
        'bool(formState, "mirror_batches_to_source_dir")',
        'string(formState, "translation_provider")',
        'string(formState, "llm_model")',
        'string(formState, "transliteration_mode")',
        'string(formState, "transliteration_model")',
        'int(formState, "worker_count")',
        'int(formState, "batch_size")',
        'int(formState, "translation_batch_size")',
        'int(formState, "ass_font_size")',
        'double(formState, "ass_emphasis_scale")',
    ]:
        assert direct_parse not in subtitle_template_body
    assert "AppleBookCreateLanguage.init(backendValue:)" in template_settings_source
    assert "AppleSubtitleOutputFormat(rawValue: $0.lowercased())" in template_settings_source
    assert "AppleSubtitleTranslationProvider.init(backendValue:)" in template_settings_source
    assert "AppleSubtitleTransliterationMode.init(backendValue:)" in template_settings_source
    assert "struct AppleBookCreateTemplateLanguageApplication" in template_settings_source
    assert "static func languageApplication(" in template_settings_source
    assert 'string(formState, "input_language")' in template_settings_source
    assert 'stringArray(formState, "target_languages")' in template_settings_source
    assert ".flatMap(AppleBookCreateLanguage.init(backendValue:))" in template_settings_source
    assert ".compactMap(AppleBookCreateLanguage.init(backendValue:))" in template_settings_source
    assert "AppleBookCreateTemplateSettings.languageApplication(from: formState)" in template_application_source
    language_body = template_application_source.split("private func applyTemplateLanguages(", 1)[1].split(
        "\n    private func applyTemplateNarrationSettings",
        1,
    )[0]
    assert "languageApplication.inputLanguage" in language_body
    assert "languageApplication.targetLanguages.first" in language_body
    assert "languageApplication.targetLanguages\n                .dropFirst()" in language_body
    assert ".map(\\.backendValue)" in language_body
    assert 'string(formState, "input_language")' not in language_body
    assert 'stringArray(formState, "target_languages")' not in language_body
    assert "struct AppleBookCreateTemplateVoiceApplication" in template_settings_source
    assert "static func voiceApplication(" in template_settings_source
    assert 'string(formState, "selected_voice")' in template_settings_source
    assert ".flatMap(AppleBookCreateVoiceOption.init(backendValue:))" in template_settings_source
    assert 'stringDictionary(from: formState["voice_overrides"])' in template_settings_source
    assert "AppleBookCreateTemplateSettings.voiceApplication(from: formState)" in template_application_source
    narration_body = template_application_source.split("private func applyTemplateNarrationSettings(", 1)[1].split(
        "\n    private func applyTemplateOutputSettings",
        1,
    )[0]
    assert "voiceApplication.voice" in narration_body
    assert "voiceApplication.overrides" in narration_body
    assert 'string(formState, "selected_voice")' not in narration_body
    assert 'stringDictionary(from: formState["voice_overrides"])' not in narration_body
    assert "struct AppleBookCreateTemplateAudioApplication" in template_settings_source
    assert "static func audioApplication(" in template_settings_source
    for audio_key in [
        '"generate_audio"',
        '"audio_mode"',
        '"audio_bitrate_kbps"',
        '"written_mode"',
        '"tempo"',
        '"stitch_full"',
        '"include_transliteration"',
    ]:
        assert audio_key in template_settings_source
    assert "AppleBookCreateTemplateSettings.audioApplication(from: formState)" in template_application_source
    assert "audioApplication.generateAudio" in narration_body
    assert "audioApplication.audioMode" in narration_body
    assert "audioApplication.audioBitrateKbps" in narration_body
    assert "audioApplication.writtenMode" in narration_body
    assert "audioApplication.tempo" in narration_body
    assert "audioApplication.stitchFull" in narration_body
    assert "audioApplication.includeTransliteration" in narration_body
    assert 'bool(formState, "generate_audio")' not in narration_body
    assert 'string(formState, "audio_mode")' not in narration_body
    assert 'string(formState, "audio_bitrate_kbps")' not in narration_body
    assert 'string(formState, "written_mode")' not in narration_body
    assert 'double(formState, "tempo")' not in narration_body
    assert 'bool(formState, "stitch_full")' not in narration_body
    assert 'bool(formState, "include_transliteration")' not in narration_body
    assert "struct AppleBookCreateTemplateBookTranslationApplication" in template_settings_source
    assert "static func bookTranslationApplication(" in template_settings_source
    for translation_key in [
        '"translation_provider"',
        '"ollama_model"',
        '"translation_batch_size"',
        '"transliteration_mode"',
        '"transliteration_model"',
        '"enable_lookup_cache"',
        '"lookup_cache_batch_size"',
    ]:
        assert translation_key in template_settings_source
    assert ".flatMap(AppleSubtitleTranslationProvider.init(backendValue:))" in template_settings_source
    assert ".flatMap(AppleSubtitleTransliterationMode.init(backendValue:))" in template_settings_source
    assert "AppleBookCreateTemplateSettings.bookTranslationApplication(from: formState)" in template_application_source
    assert "translationApplication.provider" in narration_body
    assert "translationApplication.llmModel" in narration_body
    assert "translationApplication.translationBatchSize" in narration_body
    assert "translationApplication.transliterationMode" in narration_body
    assert "translationApplication.transliterationModel" in narration_body
    assert "translationApplication.enableLookupCache" in narration_body
    assert "translationApplication.lookupCacheBatchSize" in narration_body
    assert 'string(formState, "translation_provider")' not in narration_body
    assert 'string(formState, "ollama_model")' not in narration_body
    assert 'int(formState, "translation_batch_size")' not in narration_body
    assert 'string(formState, "transliteration_mode")' not in narration_body
    assert 'string(formState, "transliteration_model")' not in narration_body
    assert 'bool(formState, "enable_lookup_cache")' not in narration_body
    assert 'int(formState, "lookup_cache_batch_size")' not in narration_body
    assert "struct AppleBookCreateTemplateOutputApplication" in template_settings_source
    assert "static func outputApplication(" in template_settings_source
    assert '"output_html"' in template_settings_source
    assert '"output_pdf"' in template_settings_source
    assert "AppleBookCreateTemplateSettings.outputApplication(from: formState)" in template_application_source
    output_body = template_application_source.split("private func applyTemplateOutputSettings(", 1)[1].split(
        "\n    private func applyTemplateImageSettings",
        1,
    )[0]
    assert "outputApplication.outputHtml" in output_body
    assert "outputApplication.outputPdf" in output_body
    assert 'bool(formState, "output_html")' not in output_body
    assert 'bool(formState, "output_pdf")' not in output_body
    assert "struct AppleBookCreateTemplateImageApplication" in template_settings_source
    assert "static func imageApplication(" in template_settings_source
    for image_key in [
        '"add_images"',
        '"image_prompt_pipeline"',
        '"image_style_template"',
        '"image_prompt_batching_enabled"',
        '"image_prompt_batch_size"',
        '"image_prompt_plan_batch_size"',
        '"image_prompt_context_sentences"',
        '"image_width"',
        '"image_height"',
        '"image_steps"',
        '"image_cfg_scale"',
        '"image_sampler_name"',
        '"image_seed_with_previous_image"',
        '"image_blank_detection_enabled"',
        '"image_api_base_urls"',
        '"image_api_timeout_seconds"',
    ]:
        assert image_key in template_settings_source
    assert ".flatMap(AppleGeneratedBookImagePromptPipeline.init(backendValue:))" in template_settings_source
    assert ".flatMap(AppleGeneratedBookImageStyleTemplate.init(backendValue:))" in template_settings_source
    assert "AppleBookCreateTemplateSettings.imageApplication(from: formState)" in template_application_source
    image_body = template_application_source.split("private func applyTemplateImageSettings(", 1)[1].split(
        "\n    private func applyTemplateWorkerSettings",
        1,
    )[0]
    for image_field in [
        "includeImages",
        "promptPipeline",
        "styleTemplate",
        "promptBatchingEnabled",
        "promptBatchSize",
        "promptPlanBatchSize",
        "promptContextSentences",
        "width",
        "height",
        "steps",
        "cfgScale",
        "samplerName",
        "seedWithPreviousImage",
        "blankDetectionEnabled",
        "apiBaseURLs",
        "apiTimeoutSeconds",
    ]:
        assert f"imageApplication.{image_field}" in image_body
    for direct_parse in [
        'bool(formState, "add_images")',
        'string(formState, "image_prompt_pipeline")',
        'string(formState, "image_style_template")',
        'bool(formState, "image_prompt_batching_enabled")',
        'int(formState, "image_prompt_batch_size")',
        'int(formState, "image_prompt_plan_batch_size")',
        'int(formState, "image_prompt_context_sentences")',
        'string(formState, "image_width")',
        'string(formState, "image_height")',
        'string(formState, "image_steps")',
        'string(formState, "image_cfg_scale")',
        'string(formState, "image_sampler_name")',
        'bool(formState, "image_seed_with_previous_image")',
        'bool(formState, "image_blank_detection_enabled")',
        'stringArray(formState, "image_api_base_urls")',
        'string(formState, "image_api_timeout_seconds")',
    ]:
        assert direct_parse not in image_body
    assert "struct AppleBookCreateTemplateWorkerApplication" in template_settings_source
    assert "static func workerApplication(" in template_settings_source
    for worker_key in [
        '"thread_count"',
        '"queue_size"',
        '"job_max_workers"',
        '"image_concurrency"',
    ]:
        assert worker_key in template_settings_source
    assert "AppleBookCreateTemplateSettings.workerApplication(from: formState)" in template_application_source
    worker_body = template_application_source.split("private func applyTemplateWorkerSettings(", 1)[1].split(
        "\n    private func applyTemplateMetadata",
        1,
    )[0]
    assert "workerApplication.threadCount" in worker_body
    assert "workerApplication.queueSize" in worker_body
    assert "workerApplication.jobMaxWorkers" in worker_body
    assert "workerApplication.imageConcurrency" in worker_body
    assert 'string(formState, "thread_count")' not in worker_body
    assert 'string(formState, "queue_size")' not in worker_body
    assert 'string(formState, "job_max_workers")' not in worker_body
    assert 'string(formState, "image_concurrency")' not in worker_body
    assert "AppleBookCreateTemplateSettings.metadataObject(from: formState)" in template_application_source
    assert "applyTemplateDiscoveryState(template, formState: formState)" in template_application_source
    assert "private func applyTemplateDiscoveryState(" in template_application_source
    assert "AppleBookCreateTemplateSettings.discoveryApplication(" in template_application_source
    assert 'extras["acquisition_provider"] = .string(provider)' not in view_source
    assert 'extras["acquisition_candidate_id"] = .string(value)' not in view_source
    assert "private func templateFormState(from template: CreationTemplateEntry)" not in view_source
    assert "private func templateSettings(from template: CreationTemplateEntry)" not in view_source
    assert "enum AppleBookCreateTemplateSettings" in template_settings_source
    assert "struct AppleBookCreateTemplateDiscoveryApplication" in template_settings_source
    assert "let shouldUseDiscoverySourcePanel: Bool?" in template_settings_source
    assert "static func mode(for template: CreationTemplateEntry) -> AppleCreateMode?" in template_settings_source
    assert "static func compatibleTemplates(" in template_settings_source
    assert 'case "subtitle_job"' in template_settings_source
    assert 'case "youtube_dub"' in template_settings_source
    assert "static func formState(from template: CreationTemplateEntry)" in template_settings_source
    assert "static func settings(from template: CreationTemplateEntry)" in template_settings_source
    assert "static func selectedCompatibleTemplateID(" in template_settings_source
    assert "static func selectedTemplatePickerValue(" in template_settings_source
    assert "static func resolvedTemplateSelection(" in template_settings_source
    assert "compatibleTemplates(from: templates, for: mode)" in template_settings_source
    assert "AppleBookCreateTemplateSettings.selectedTemplatePickerValue(" in presentation_state_source
    assert "AppleBookCreateTemplateSettings.resolvedTemplateSelection(" in template_actions_source
    assert "compatibleCreationTemplates.contains(where: { $0.id == selectedTemplateID })" not in view_source
    assert "static func metadataObject(from formState: [String: JSONValue])" in template_settings_source
    assert 'object(from: formState["book_metadata"])' in template_settings_source
    assert "struct AppleBookCreateTemplateBookMetadataApplication" in template_settings_source
    assert "static func bookMetadataApplication(" in template_settings_source
    assert 'title: string(metadata, "book_title") ?? string(metadata, "title")' in template_settings_source
    assert 'author: string(metadata, "book_author") ?? string(metadata, "author")' in template_settings_source
    assert 'genre: string(metadata, "book_genre") ?? string(metadata, "genre")' in template_settings_source
    assert 'summary: string(metadata, "book_summary") ?? string(metadata, "summary")' in template_settings_source
    assert 'coverFile: string(metadata, "book_cover_file") ?? string(metadata, "cover_file")' in template_settings_source
    assert "AppleBookCreateTemplateSettings.bookMetadataApplication(from: formState)" in template_application_source
    metadata_body = template_application_source.split("private func applyTemplateMetadata(", 1)[1].split(
        "\n    private func applyTemplateSourceBookContext",
        1,
    )[0]
    assert "metadataApplication.title" in metadata_body
    assert "metadataApplication.author" in metadata_body
    assert "metadataApplication.genre" in metadata_body
    assert "metadataApplication.summary" in metadata_body
    assert "metadataApplication.year" in metadata_body
    assert "metadataApplication.isbn" in metadata_body
    assert "metadataApplication.coverFile" in metadata_body
    assert 'object(from: formState["book_metadata"])' not in metadata_body
    assert 'string(metadata, "book_title")' not in metadata_body
    assert "struct AppleBookCreateTemplateSourceBookContextApplication" in template_settings_source
    assert "static func sourceBookContextApplication(" in template_settings_source
    assert 'title: string(formState, "source_book_title")' in template_settings_source
    assert 'author: string(formState, "source_book_author")' in template_settings_source
    assert 'genre: string(formState, "source_book_genre")' in template_settings_source
    assert 'summary: string(formState, "source_book_summary")' in template_settings_source
    assert "AppleBookCreateTemplateSettings.sourceBookContextApplication(from: formState)" in template_application_source
    source_context_body = template_application_source.split("private func applyTemplateSourceBookContext(", 1)[1].split(
        "\n    private func applyTemplateDiscoveryState",
        1,
    )[0]
    assert "guard creationMode == .generatedBook else" in source_context_body
    assert "contextApplication.title" in source_context_body
    assert "contextApplication.author" in source_context_body
    assert "contextApplication.genre" in source_context_body
    assert "contextApplication.summary" in source_context_body
    assert 'string(formState, "source_book_title")' not in source_context_body
    assert 'string(formState, "source_book_author")' not in source_context_body
    assert 'string(formState, "source_book_genre")' not in source_context_body
    assert 'string(formState, "source_book_summary")' not in source_context_body
    assert "static func discoveryApplication(" in template_settings_source
    assert "static func discoveryState(from template: CreationTemplateEntry)" in template_settings_source
    assert 'extras["acquisition_provider"] = .string(string(discoveryState, "acquisition_provider") ?? provider)' in template_settings_source
    assert 'extras["acquisition_candidate_id"] = .string(value)' in template_settings_source
    assert 'extras["book_title"] = .string(value)' in template_settings_source
    assert 'extras["rights"] = .string(value)' in template_settings_source
    assert 'extras["book_language"] = .string(value)' in template_settings_source
    assert 'extras["book_year"] = value' in template_settings_source
    assert 'extras["capabilities"] = value' in template_settings_source
    assert "AppleBookCreatePresentation.normalizedBookMetadataExtras(extras)" in template_settings_source
    assert "static func stringArray(_ object: [String: JSONValue], _ key: String)" in template_settings_source
    assert "static func stringDictionary(from value: JSONValue?)" in template_settings_source
    assert "static func endSentenceText(from value: JSONValue?)" in template_settings_source
    assert "static func discoveryState(from template: CreationTemplateEntry)" in template_settings_source
    assert 'template.payload["discovery_state"]' in template_settings_source
    assert "enum AppleBookCreateTemplateSavePayloadFactory" not in template_settings_source
    youtube_template_body = template_application_source.split("private func applyYoutubeDubCreationTemplate(", 1)[1].split(
        "\n    private func applyTemplateLanguages",
        1,
    )[0]
    assert "struct AppleYoutubeDubTemplateApplication" in template_settings_source
    assert "static func youtubeDubApplication(" in template_settings_source
    assert "AppleBookCreateTemplateSettings.youtubeDubApplication(" in youtube_template_body
    for youtube_field in [
        "videoPath",
        "subtitlePath",
        "sourceLanguage",
        "targetLanguage",
        "voice",
        "startTimeOffset",
        "endTimeOffset",
        "originalMixPercent",
        "flushSentences",
        "translationProvider",
        "llmModel",
        "translationBatchSize",
        "transliterationMode",
        "transliterationModel",
        "splitBatches",
        "stitchBatches",
        "includeTransliteration",
        "targetHeight",
        "preserveAspectRatio",
        "enableLookupCache",
    ]:
        assert f"youtubeApplication.{youtube_field}" in youtube_template_body
    for direct_parse in [
        'string(formState, "source_language")',
        'string(formState, "target_language")',
        'string(formState, "voice")',
        'string(formState, "start_time_offset")',
        'string(formState, "end_time_offset")',
        'double(formState, "original_mix_percent")',
        'int(formState, "flush_sentences")',
        'string(formState, "translation_provider")',
        'string(formState, "llm_model")',
        'int(formState, "translation_batch_size")',
        'string(formState, "transliteration_mode")',
        'string(formState, "transliteration_model")',
        'bool(formState, "split_batches")',
        'bool(formState, "stitch_batches")',
        'bool(formState, "include_transliteration")',
        'int(formState, "target_height")',
        'bool(formState, "preserve_aspect_ratio")',
        'bool(formState, "enable_lookup_cache")',
    ]:
        assert direct_parse not in youtube_template_body
    assert "AppleYoutubeDubTargetHeight.init(rawValue:)" in template_settings_source

    assert "enum AppleBookCreateTemplateSavePayloadFactory" in template_save_factory_source
    assert "static func makeGeneratedBookRequest(from draft: AppleBookCreateDraft)" in template_save_factory_source
    assert "static func makeNarrateEbookRequest(from draft: AppleNarrateEbookDraft)" in template_save_factory_source
    assert "static func makeSubtitleJobRequest(from draft: AppleSubtitleJobDraft)" in template_save_factory_source
    assert "static func makeYoutubeDubRequest(from draft: AppleYoutubeDubDraft)" in template_save_factory_source
    assert '"kind": .string("book_narration_form")' in template_save_factory_source
    assert '"source": .string("apple")' in template_save_factory_source
    assert '"form_state": .object(formState)' in template_save_factory_source
    subtitle_save_body = template_save_factory_source.split(
        "static func makeSubtitleJobRequest(from draft: AppleSubtitleJobDraft)",
        1,
    )[1].split("\n    static func makeYoutubeDubRequest", 1)[0]
    assert '"source_mode": .string(draft.sourcePath?.nonEmptyValue == nil ? "upload" : "existing")' in subtitle_save_body
    assert '"source_mode": .string(draft.sourcePath?.nonEmptyValue == nil ? "upload" : "server")' not in subtitle_save_body
    assert 'language: draft.inputLanguage' in template_save_factory_source
    assert "let normalizedTitle = title.trimmingCharacters(in: .whitespacesAndNewlines)" in template_save_factory_source
    assert '"title": .string(normalizedTitle)' in template_save_factory_source
    assert '"book_title": .string(normalizedTitle)' in template_save_factory_source
    assert '"job_label": .string(normalizedTitle)' in template_save_factory_source
    assert 'add(language, named: "book_language", to: &metadata)' in template_save_factory_source
    assert "AppleBookCreatePresentation.normalizedBookGenres(genre)" in template_save_factory_source
    assert 'metadata["book_genres"] = .array(genres.map { .string($0) })' in template_save_factory_source
    assert "private static func addBookCover(_ value: String?, to object: inout [String: JSONValue])" in template_save_factory_source
    assert 'object["cover_url"] = .string(trimmed)' in template_save_factory_source
    assert 'object["book_cover_file"] = .string(trimmed)' in template_save_factory_source
    assert "let videoDiscoveryState: [String: JSONValue]?" in _source(CREATE_MODELS)
    assert "let draft = currentGeneratedBookDraft()" in submission_actions_source
    assert "let draft = currentNarrateEbookDraft()" in submission_actions_source
    assert "guard let draft = currentSubtitleJobDraft() else { return }" in submission_actions_source
    assert "guard let draft = currentYoutubeDubDraft() else { return }" in submission_actions_source
    assert draft_actions_source.count("AppleBookCreatePresentation.generatedBookDraft(") == 1
    assert draft_actions_source.count("AppleBookCreatePresentation.narrateEbookDraft(") == 1
    assert draft_actions_source.count("AppleBookCreatePresentation.subtitleJobDraft(") == 1
    assert draft_actions_source.count("AppleBookCreatePresentation.youtubeDubDraft(") == 1
    assert "videoDiscoveryState: youtubeDiscoveryState" in draft_actions_source
    assert draft_actions_source.count("videoDiscoveryState: youtubeDiscoveryState") == 1
    assert "AppleBookCreatePresentation.generatedBookDraft(" not in view_source
    assert "AppleBookCreatePresentation.narrateEbookDraft(" not in view_source
    assert "AppleBookCreatePresentation.subtitleJobDraft(" not in view_source
    assert "AppleBookCreatePresentation.youtubeDubDraft(" not in view_source
    assert "@State var youtubeDiscoveryState: [String: JSONValue]?" in view_source
    assert "private func youtubeDiscoveryStatePayload(" not in view_source
    discovery_source = _source(CREATE_DISCOVERY_PRESENTATION)
    video_discovery_source = _source(CREATE_VIDEO_DISCOVERY_PRESENTATION)
    assert "static func videoDiscoveryStatePayload(" in video_discovery_source
    assert "static func videoDiscoveryState(" in video_discovery_source
    assert 'state["selected_subtitle_path"] = .string(trimmed)' in video_discovery_source
    assert 'state.removeValue(forKey: "selected_subtitle_path")' in video_discovery_source
    assert "static func videoDiscoveryStatePayload(" not in discovery_source
    assert "static func videoDiscoveryState(" not in discovery_source
    assert "AppleBookCreatePresentation.videoDiscoveryStatePayload(" in source_actions
    assert "AppleBookCreatePresentation.videoDiscoveryState(" in source_actions
    assert 'youtubeDiscoveryState?["selected_subtitle_path"]' not in view_source
    assert "let discoveryState = AppleBookCreatePresentation.normalizedVideoDiscoveryState(" in template_application_source
    assert "youtubeDiscoveryState = discoveryState" in template_application_source
    assert "static func youtubeVideoPath(" in template_settings_source
    assert "static func youtubeSubtitlePath(" in template_settings_source
    assert 'string(discoveryState ?? [:], "selected_video_path")' in template_settings_source
    assert 'string(discoveryState ?? [:], "local_path")' in template_settings_source
    assert 'string(discoveryState ?? [:], "selected_subtitle_path")' in template_settings_source
    assert "videoPath: youtubeVideoPath(formState: formState, discoveryState: discoveryState)" in template_settings_source
    assert "subtitlePath: youtubeSubtitlePath(formState: formState, discoveryState: discoveryState)" in template_settings_source
    assert "AppleBookCreateTemplateSettings.discoveryState(from: template)" in template_application_source
    assert '"media_kind": .string("video")' in video_discovery_source
    assert '"candidate_id": .string(candidate.candidateId)' in video_discovery_source
    assert "selectedProvider: String? = nil" in video_discovery_source
    assert "query: String? = nil" in video_discovery_source
    assert 'state["selected_provider"] = .string(selectedProvider)' in video_discovery_source
    assert 'state["query"] = .string(query)' in video_discovery_source
    assert "payload[\"discovery_state\"] = .object(discoveryState)" in template_save_factory_source
    assert "private static func makeVideoDiscoveryState(" in template_save_factory_source
    assert 'trimmedKey.lowercased().contains("token")' in template_save_factory_source
    for web_template_key in [
        '"input_file"',
        '"base_output_file"',
        '"target_languages"',
        '"selected_voice"',
        '"voice_overrides"',
        '"translation_provider"',
        '"enable_lookup_cache"',
        '"add_images"',
        '"image_api_base_urls"',
        '"book_metadata"',
        '"source_path"',
        '"output_format"',
        '"generate_audio_book"',
        '"mirror_batches_to_source_dir"',
        '"ass_font_size"',
        '"ass_emphasis_scale"',
        '"video_path"',
        '"subtitle_path"',
        '"source_language"',
        '"original_mix_percent"',
        '"flush_sentences"',
        '"target_height"',
        '"media_metadata"',
    ]:
        assert web_template_key in view_source + template_save_factory_source
    assert "AppleBookCreateTemplateSettings.swift in Sources" in project
    assert project.count("AppleBookCreateTemplateSettings.swift in Sources") == 4
    assert "AppleBookCreateTemplateActions.swift in Sources" in project
    assert project.count("AppleBookCreateTemplateActions.swift in Sources") == 4
    assert "AppleBookCreateTemplateApplicationActions.swift in Sources" in project
    assert project.count("AppleBookCreateTemplateApplicationActions.swift in Sources") == 4
    assert "AppleBookCreateTemplateSavePayloadFactory.swift in Sources" in project
    assert project.count("AppleBookCreateTemplateSavePayloadFactory.swift in Sources") == 4
    assert "AppleBookCreateTemplateSettings.swift" in payload_script
    assert "AppleBookCreateTemplateSavePayloadFactory.swift" in payload_script


def test_apple_create_response_models_match_api_client_decoder_strategy() -> None:
    api_models_source = _source(PIPELINE_CREATION_API_MODELS)

    response_models = [
        "CreationTemplateEntry",
        "PipelineFileEntry",
        "PipelineFileBrowserResponse",
        "BookContentIndexResponse",
        "SubtitleSourceEntry",
        "SubtitleSourceDeleteResponse",
        "YoutubeInlineSubtitleStream",
        "YoutubeInlineSubtitleListResponse",
        "YoutubeSubtitleExtractionResponse",
        "BookCreationDefaults",
        "BookCreationPipelineDefaults",
        "BookCreationSentenceSplitterMode",
        "BookCreationSentenceSplitterCapabilities",
        "BookCreationGeneratedSourceDefaults",
        "BookCreationSubtitleDefaults",
        "BookCreationYoutubeDubDefaults",
        "BookCreationOptionsResponse",
    ]
    for model_name in response_models:
        body = _swift_struct_body(api_models_source, model_name)
        assert not re.search(r'case\s+\w+\s*=\s*"[^"]*_[^"]*"', body), model_name
    assert "let type: String?" in _swift_struct_body(api_models_source, "PipelineFileEntry")
    assert "let sentenceSplitterMode: String?" in _swift_struct_body(
        api_models_source,
        "BookCreationPipelineDefaults",
    )
    assert "let cacheVersion: String" in _swift_struct_body(
        api_models_source,
        "BookCreationSentenceSplitterMode",
    )
    assert "let supportedModes: [BookCreationSentenceSplitterMode]" in _swift_struct_body(
        api_models_source,
        "BookCreationSentenceSplitterCapabilities",
    )
    assert "let comparisonMetricFields: [String]" in _swift_struct_body(
        api_models_source,
        "BookCreationSentenceSplitterCapabilities",
    )
    assert "let sentenceSplitterCapabilities: BookCreationSentenceSplitterCapabilities?" in _swift_struct_body(
        api_models_source,
        "BookCreationOptionsResponse",
    )

    assert "decoder.keyDecodingStrategy = .convertFromSnakeCase" in _source(API_CLIENT)
    assert 'case inputFile = "input_file"' in api_models_source
    assert 'case videoPath = "video_path"' in api_models_source


def test_api_client_extracts_fastapi_error_details_for_create_messages() -> None:
    source = _source(API_CLIENT)

    assert "static func responseMessage(from data: Data) -> String?" in source
    assert 'for key in ["detail", "message", "error"]' in source
    assert 'value["msg"] as? String' in source
    assert 'messages.joined(separator: "; ")' in source
    assert "let message = APIClientError.responseMessage(from: data)" in source
    assert "String(data: data, encoding: .utf8)" in source


def test_create_lifecycle_modifier_owns_view_side_effect_wiring() -> None:
    source = _source(CREATE_VIEW)
    lifecycle_source = _source(CREATE_LIFECYCLE)
    project = _source(XCODE_PROJECT)

    assert "AppleBookCreateLifecycleModifier(" in source
    assert "onLoadCreateDependencies: loadCreateDependencies" in source
    assert "onRefreshHistoryDefaults: refreshHistoryDefaults" in source
    assert "onCreationModeChange: refreshCreationTemplatesFromSection" in source
    assert "onDeleteEbook: deletePipelineEbook" in source
    assert "onDeleteSubtitleSource: deleteSubtitleSource" in source
    assert "onDeleteCreationTemplate: deleteCreationTemplate" in source
    assert "AppleBookCreateEbookDeleteConfirmationModifier" not in source
    assert "AppleBookCreateSubtitleDeleteConfirmationModifier" not in source
    assert "AppleBookCreateTemplateDeleteConfirmationModifier" not in source
    assert ".task(id: creationOptionsLoadKey)" not in source
    assert ".onChange(of: recentJobs)" not in source
    assert ".onChange(of: youtubeBaseDir)" not in source

    assert "struct AppleBookCreateLifecycleModifier: ViewModifier" in lifecycle_source
    assert ".task(id: creationOptionsLoadKey)" in lifecycle_source
    assert ".onChange(of: recentJobs)" in lifecycle_source
    assert ".onChange(of: creationMode)" in lifecycle_source
    assert "onCreationModeChange()" in lifecycle_source
    assert ".onChange(of: youtubeBaseDir)" in lifecycle_source
    assert "AppleBookCreateEbookDeleteConfirmationModifier" in lifecycle_source
    assert "AppleBookCreateSubtitleDeleteConfirmationModifier" in lifecycle_source
    assert "AppleBookCreateTemplateDeleteConfirmationModifier" in lifecycle_source
    assert "confirmDeletePipelineEbookButton" in lifecycle_source
    assert "confirmDeleteSubtitleSourceButton" in lifecycle_source
    assert "confirmDeleteCreationTemplateButton" in lifecycle_source
    assert "AppleBookCreateLifecycle.swift in Sources" in project
    assert project.count("AppleBookCreateLifecycle.swift in Sources") == 4


def test_create_submission_actions_are_split_from_create_view_and_target_wired() -> None:
    view_source = _source(CREATE_VIEW)
    submission_actions_source = _source(CREATE_SUBMISSION_ACTIONS)
    project = _source(XCODE_PROJECT)

    assert "extension AppleBookCreateView" in submission_actions_source
    assert "func submit()" in submission_actions_source
    assert "func submitGeneratedBook()" in submission_actions_source
    assert "func submitNarrateEbook()" in submission_actions_source
    assert "func submitSubtitleJob()" in submission_actions_source
    assert "func submitYoutubeDub()" in submission_actions_source
    assert "func completeSubmission(_ jobId: String?) async" in submission_actions_source
    assert "viewModel.submitGeneratedBook(draft, using: appState)" in submission_actions_source
    assert "viewModel.submitNarrateEbook(" in submission_actions_source
    assert "viewModel.submitSubtitleJob(" in submission_actions_source
    assert "viewModel.submitYoutubeDub(draft, using: appState)" in submission_actions_source
    assert "await refreshIntakeStatus(force: true)" in submission_actions_source
    assert "onJobSubmitted(jobId)" in submission_actions_source

    for moved_definition in [
        "private func submit()",
        "private func submitGeneratedBook()",
        "private func submitNarrateEbook()",
        "private func submitSubtitleJob()",
        "private func submitYoutubeDub()",
        "private func completeSubmission(_ jobId: String?) async",
    ]:
        assert moved_definition not in view_source

    assert "AppleBookCreateSubmissionActions.swift in Sources" in project
    assert project.count("AppleBookCreateSubmissionActions.swift in Sources") == 4


def test_create_view_model_uses_shared_submission_wrapper() -> None:
    source = _source(CREATE_VIEW_MODEL)
    submission_source = _source(CREATE_VIEW_MODEL_SUBMISSION)
    project = _source(XCODE_PROJECT)

    assert "extension AppleBookCreateViewModel" in submission_source
    assert "func submitGeneratedBook(_ draft: AppleBookCreateDraft, using appState: AppState)" in submission_source
    assert "func submitNarrateEbook(" in submission_source
    assert "func submitSubtitleJob(" in submission_source
    assert "func submitYoutubeDub(" in submission_source
    assert "private func submitJob(" in submission_source
    assert "operation: (APIClient) async throws -> String" in submission_source
    assert "let jobId = try await operation(client)" in submission_source
    assert "submittedJobId = jobId" in submission_source
    assert submission_source.count("await submitJob(using: appState)") == 4
    assert submission_source.count("isSubmitting = true") == 1
    assert submission_source.count("defer { isSubmitting = false }") == 1
    assert submission_source.count('errorMessage = "API configuration is unavailable."') == 1
    assert "func submitGeneratedBook(_ draft: AppleBookCreateDraft, using appState: AppState)" not in source
    assert "private func submitJob(" not in source
    assert "AppleBookCreateViewModel+Submission.swift in Sources" in project
    assert project.count("AppleBookCreateViewModel+Submission.swift in Sources") == 4


def test_create_view_model_ignores_stale_intake_status_refreshes() -> None:
    source = _source(CREATE_VIEW_MODEL)
    load_body = _swift_function_body(
        source,
        "func loadIntakeStatus(\n        using appState: AppState,\n        cacheKey: String,\n        force: Bool = false\n    ) async",
    )

    assert "private var intakeStatusRequestSequence = 0" in source
    assert "intakeStatusRequestSequence += 1" in load_body
    assert "let requestSequence = intakeStatusRequestSequence" in load_body
    assert "if requestSequence == intakeStatusRequestSequence" in load_body
    assert "let status = try await client.fetchPipelineIntakeStatus()" in load_body
    assert "guard requestSequence == intakeStatusRequestSequence else { return }" in load_body
    assert load_body.index("guard requestSequence == intakeStatusRequestSequence else { return }") < load_body.index(
        "intakeStatus = status"
    )
    assert load_body.count("guard requestSequence == intakeStatusRequestSequence else { return }") == 2


def test_create_view_model_ignores_stale_creation_template_refreshes() -> None:
    source = _source(CREATE_VIEW_MODEL)
    template_source = _source(CREATE_VIEW_MODEL_TEMPLATES)
    load_body = _swift_function_body(
        template_source,
        "func loadCreationTemplates(\n        using appState: AppState,\n        cacheKey: String,\n        mode: String? = nil,\n        force: Bool = false\n    ) async -> [CreationTemplateEntry]",
    )

    assert "var creationTemplatesRequestSequence = 0" in source
    assert "creationTemplatesRequestSequence += 1" in load_body
    assert "let requestSequence = creationTemplatesRequestSequence" in load_body
    assert "if requestSequence == creationTemplatesRequestSequence" in load_body
    assert "let response = try await client.fetchCreationTemplates(mode: mode)" in load_body
    assert "guard requestSequence == creationTemplatesRequestSequence else" in load_body
    assert load_body.index("guard requestSequence == creationTemplatesRequestSequence else") < load_body.index(
        "creationTemplates = response.templates"
    )
    assert "return creationTemplates" in load_body
    assert load_body.count("guard requestSequence == creationTemplatesRequestSequence else") == 3


def test_create_view_model_metadata_actions_are_split_and_target_wired() -> None:
    source = _source(CREATE_VIEW_MODEL)
    metadata_source = _source(CREATE_VIEW_MODEL_METADATA)
    project = _source(XCODE_PROJECT)

    assert "extension AppleBookCreateViewModel" in metadata_source
    for helper in [
        "lookupSubtitleTvMetadata",
        "clearSubtitleTvMetadataCache",
        "updateSubtitleMediaMetadata",
        "applySubtitleMediaMetadataJSONText",
        "lookupYoutubeTvMetadata",
        "lookupYoutubeVideoMetadata",
        "clearYoutubeVideoMetadataCache",
        "updateYoutubeMediaMetadata",
        "applyYoutubeMediaMetadataJSONText",
        "resetYoutubeMetadataState",
    ]:
        assert f"func {helper}(" in metadata_source
        assert f"func {helper}(" not in source

    assert "private func updateSubtitleMetadataSection(" in metadata_source
    assert "private func updateYoutubeMetadataSection(" in metadata_source
    assert "private func mergeYoutubeTvMetadata(" in metadata_source
    assert "AppleBookCreateMetadataJSON.parseObject(" in metadata_source
    assert "AppleBookCreateMetadataJSON.updateNestedText(" in metadata_source
    assert "AppleBookCreateViewModel+Metadata.swift in Sources" in project
    assert project.count("AppleBookCreateViewModel+Metadata.swift in Sources") == 4


def test_create_view_model_ignores_stale_metadata_lookup_refreshes() -> None:
    source = _source(CREATE_VIEW_MODEL)
    metadata_source = _source(CREATE_VIEW_MODEL_METADATA)
    subtitle_body = _swift_function_body(
        metadata_source,
        "func lookupSubtitleTvMetadata(\n        sourceName: String,\n        force: Bool = false,\n        using appState: AppState\n    ) async",
    )
    clear_subtitle_body = _swift_function_body(metadata_source, "func clearSubtitleMetadata()")
    youtube_tv_body = _swift_function_body(
        metadata_source,
        "func lookupYoutubeTvMetadata(\n        sourceName: String,\n        force: Bool = false,\n        using appState: AppState\n    ) async",
    )
    youtube_video_body = _swift_function_body(
        metadata_source,
        "func lookupYoutubeVideoMetadata(\n        sourceName: String,\n        force: Bool = false,\n        using appState: AppState\n    ) async",
    )
    reset_youtube_body = _swift_function_body(metadata_source, "func resetYoutubeMetadataState()")

    assert "var subtitleTvMetadataRequestSequence = 0" in source
    assert "subtitleTvMetadataRequestSequence += 1" in subtitle_body
    assert "let requestSequence = subtitleTvMetadataRequestSequence" in subtitle_body
    assert "if requestSequence == subtitleTvMetadataRequestSequence" in subtitle_body
    assert "guard requestSequence == subtitleTvMetadataRequestSequence else { return }" in subtitle_body
    assert subtitle_body.index("guard requestSequence == subtitleTvMetadataRequestSequence else { return }") < subtitle_body.index(
        "subtitleTvMetadataPreview = response"
    )
    assert subtitle_body.count("guard requestSequence == subtitleTvMetadataRequestSequence else { return }") == 2
    assert "subtitleTvMetadataRequestSequence += 1" in clear_subtitle_body

    assert "var youtubeTvMetadataRequestSequence = 0" in source
    assert "youtubeTvMetadataRequestSequence += 1" in youtube_tv_body
    assert "let requestSequence = youtubeTvMetadataRequestSequence" in youtube_tv_body
    assert "if requestSequence == youtubeTvMetadataRequestSequence" in youtube_tv_body
    assert "guard requestSequence == youtubeTvMetadataRequestSequence else { return }" in youtube_tv_body
    assert youtube_tv_body.index("guard requestSequence == youtubeTvMetadataRequestSequence else { return }") < youtube_tv_body.index(
        "youtubeTvMetadataPreview = response"
    )
    assert youtube_tv_body.count("guard requestSequence == youtubeTvMetadataRequestSequence else { return }") == 2

    assert "var youtubeVideoMetadataRequestSequence = 0" in source
    assert "youtubeVideoMetadataRequestSequence += 1" in youtube_video_body
    assert "let requestSequence = youtubeVideoMetadataRequestSequence" in youtube_video_body
    assert "if requestSequence == youtubeVideoMetadataRequestSequence" in youtube_video_body
    assert "guard requestSequence == youtubeVideoMetadataRequestSequence else { return }" in youtube_video_body
    assert youtube_video_body.index("guard requestSequence == youtubeVideoMetadataRequestSequence else { return }") < youtube_video_body.index(
        "youtubeVideoMetadataPreview = response"
    )
    assert youtube_video_body.count("guard requestSequence == youtubeVideoMetadataRequestSequence else { return }") == 2
    assert "youtubeTvMetadataRequestSequence += 1" in reset_youtube_body
    assert "youtubeVideoMetadataRequestSequence += 1" in reset_youtube_body


def test_create_view_model_source_actions_are_split_and_target_wired() -> None:
    source = _source(CREATE_VIEW_MODEL)
    source_actions = _source(CREATE_VIEW_MODEL_SOURCES)
    project = _source(XCODE_PROJECT)

    assert "extension AppleBookCreateViewModel" in source_actions
    for helper in [
        "loadAcquisitionProviders",
        "loadPipelineFiles",
        "loadEbookDiscovery",
        "acquireEbookDiscoveryCandidate",
        "prepareEbookDiscoveryCandidate",
        "loadVideoDiscovery",
        "prepareVideoDiscoveryCandidate",
        "submitDownloadStationTask",
        "pollDownloadStationTask",
        "deletePipelineEbook",
        "uploadPipelineEbook",
        "loadSubtitleSources",
        "deleteSubtitleSource",
        "loadYoutubeLibrary",
        "resetYoutubeSubtitleExtractionState",
        "loadYoutubeSubtitleStreams",
        "extractYoutubeSubtitles",
        "loadNarrateChapters",
        "clearNarrateChapters",
    ]:
        assert f"func {helper}(" in source_actions
        assert f"func {helper}(" not in source

    assert "private func mergePipelineEbook(" in source_actions
    assert "private static func shouldSkipNarrateChapterLookup(for inputFile: String) -> Bool" in source_actions
    assert "private func mergePipelineEbook(" not in source
    assert "private static func shouldSkipNarrateChapterLookup(for inputFile: String) -> Bool" not in source
    assert "AppleBookCreateViewModel+Sources.swift in Sources" in project
    assert project.count("AppleBookCreateViewModel+Sources.swift in Sources") == 4


def test_create_view_model_ignores_stale_source_list_refreshes() -> None:
    source = _source(CREATE_VIEW_MODEL)
    source_actions = _source(CREATE_VIEW_MODEL_SOURCES)
    providers_body = _swift_function_body(
        source_actions,
        "func loadAcquisitionProviders(\n        using appState: AppState,\n        cacheKey: String,\n        force: Bool = false\n    ) async -> [AcquisitionProviderEntry]",
    )
    pipeline_body = _swift_function_body(
        source_actions,
        "func loadPipelineFiles(\n        using appState: AppState,\n        cacheKey: String,\n        force: Bool = false\n    ) async -> PipelineFileBrowserResponse?",
    )
    delete_pipeline_body = _swift_function_body(
        source_actions,
        "func deletePipelineEbook(\n        path: String,\n        using appState: AppState\n    ) async -> Bool",
    )
    upload_pipeline_body = _swift_function_body(
        source_actions,
        "func uploadPipelineEbook(\n        fileURL: URL,\n        filename: String?,\n        using appState: AppState\n    ) async -> PipelineFileEntry?",
    )
    subtitle_sources_body = _swift_function_body(
        source_actions,
        "func loadSubtitleSources(\n        using appState: AppState,\n        cacheKey: String,\n        force: Bool = false\n    ) async -> SubtitleSourceListResponse?",
    )
    delete_subtitle_body = _swift_function_body(
        source_actions,
        "func deleteSubtitleSource(\n        path: String,\n        using appState: AppState\n    ) async -> Bool",
    )
    youtube_library_body = _swift_function_body(
        source_actions,
        "func loadYoutubeLibrary(\n        using appState: AppState,\n        cacheKey: String,\n        baseDir: String? = nil,\n        force: Bool = false\n    ) async -> YoutubeNasLibraryResponse?",
    )

    assert "var acquisitionProvidersRequestSequence = 0" in source
    assert "acquisitionProvidersRequestSequence += 1" in providers_body
    assert "let requestSequence = acquisitionProvidersRequestSequence" in providers_body
    assert "guard requestSequence == acquisitionProvidersRequestSequence else" in providers_body
    assert providers_body.index("guard requestSequence == acquisitionProvidersRequestSequence else") < providers_body.index(
        "acquisitionProviders = response.providers"
    )
    assert providers_body.count("guard requestSequence == acquisitionProvidersRequestSequence else") == 2

    assert "var pipelineFilesRequestSequence = 0" in source
    assert "pipelineFilesRequestSequence += 1" in pipeline_body
    assert "let requestSequence = pipelineFilesRequestSequence" in pipeline_body
    assert "if requestSequence == pipelineFilesRequestSequence" in pipeline_body
    assert "guard requestSequence == pipelineFilesRequestSequence else" in pipeline_body
    assert pipeline_body.index("guard requestSequence == pipelineFilesRequestSequence else") < pipeline_body.index(
        "pipelineFiles = response"
    )
    assert pipeline_body.count("guard requestSequence == pipelineFilesRequestSequence else") == 2
    assert "pipelineFilesRequestSequence += 1" in delete_pipeline_body
    assert "pipelineFilesRequestSequence += 1" in upload_pipeline_body

    assert "var subtitleSourcesRequestSequence = 0" in source
    assert "subtitleSourcesRequestSequence += 1" in subtitle_sources_body
    assert "let requestSequence = subtitleSourcesRequestSequence" in subtitle_sources_body
    assert "if requestSequence == subtitleSourcesRequestSequence" in subtitle_sources_body
    assert "guard requestSequence == subtitleSourcesRequestSequence else" in subtitle_sources_body
    assert subtitle_sources_body.index("guard requestSequence == subtitleSourcesRequestSequence else") < subtitle_sources_body.index(
        "subtitleSources = response"
    )
    assert subtitle_sources_body.count("guard requestSequence == subtitleSourcesRequestSequence else") == 2
    assert "subtitleSourcesRequestSequence += 1" in delete_subtitle_body

    assert "var youtubeLibraryRequestSequence = 0" in source
    assert "youtubeLibraryRequestSequence += 1" in youtube_library_body
    assert "let requestSequence = youtubeLibraryRequestSequence" in youtube_library_body
    assert "if requestSequence == youtubeLibraryRequestSequence" in youtube_library_body
    assert "guard requestSequence == youtubeLibraryRequestSequence else" in youtube_library_body
    assert youtube_library_body.index("guard requestSequence == youtubeLibraryRequestSequence else") < youtube_library_body.index(
        "youtubeLibrary = response"
    )
    assert youtube_library_body.count("guard requestSequence == youtubeLibraryRequestSequence else") == 2


def test_create_view_model_ignores_stale_acquisition_discovery_refreshes() -> None:
    source = _source(CREATE_VIEW_MODEL)
    source_actions = _source(CREATE_VIEW_MODEL_SOURCES)
    ebook_body = _swift_function_body(
        source_actions,
        "func loadEbookDiscovery(\n        using appState: AppState,\n        cacheKey: String,\n        query: String? = nil,\n        provider: String = AppleBookCreatePresentation.defaultBookDiscoveryProviderID,\n        sourceIds: [String] = [],\n        force: Bool = false\n    ) async -> AcquisitionDiscoveryResponse?",
    )
    video_body = _swift_function_body(
        source_actions,
        "func loadVideoDiscovery(\n        using appState: AppState,\n        cacheKey: String,\n        query: String? = nil,\n        provider: String = AppleBookCreatePresentation.defaultVideoDiscoveryProviderID,\n        force: Bool = false\n    ) async -> AcquisitionDiscoveryResponse?",
    )

    assert "var ebookAcquisitionDiscoveryRequestSequence = 0" in source
    assert "ebookAcquisitionDiscoveryRequestSequence += 1" in ebook_body
    assert "let requestSequence = ebookAcquisitionDiscoveryRequestSequence" in ebook_body
    assert "if requestSequence == ebookAcquisitionDiscoveryRequestSequence" in ebook_body
    assert "guard requestSequence == ebookAcquisitionDiscoveryRequestSequence else" in ebook_body
    assert ebook_body.index("guard requestSequence == ebookAcquisitionDiscoveryRequestSequence else") < ebook_body.index(
        "ebookAcquisitionDiscovery = response"
    )
    assert "return ebookAcquisitionDiscovery" in ebook_body
    assert ebook_body.count("guard requestSequence == ebookAcquisitionDiscoveryRequestSequence else") == 3

    assert "var youtubeAcquisitionDiscoveryRequestSequence = 0" in source
    assert "youtubeAcquisitionDiscoveryRequestSequence += 1" in video_body
    assert "let requestSequence = youtubeAcquisitionDiscoveryRequestSequence" in video_body
    assert "if requestSequence == youtubeAcquisitionDiscoveryRequestSequence" in video_body
    assert "guard requestSequence == youtubeAcquisitionDiscoveryRequestSequence else" in video_body
    assert video_body.index("guard requestSequence == youtubeAcquisitionDiscoveryRequestSequence else") < video_body.index(
        "youtubeAcquisitionDiscovery = response"
    )
    assert "return youtubeAcquisitionDiscovery" in video_body
    assert video_body.count("guard requestSequence == youtubeAcquisitionDiscoveryRequestSequence else") == 3


def test_create_view_model_ignores_stale_selected_source_detail_refreshes() -> None:
    source = _source(CREATE_VIEW_MODEL)
    source_actions = _source(CREATE_VIEW_MODEL_SOURCES)
    subtitle_streams_body = _swift_function_body(
        source_actions,
        "func loadYoutubeSubtitleStreams(\n        videoPath: String,\n        using appState: AppState\n    ) async -> YoutubeInlineSubtitleListResponse?",
    )
    reset_streams_body = _swift_function_body(source_actions, "func resetYoutubeSubtitleExtractionState()")
    chapters_body = _swift_function_body(
        source_actions,
        "func loadNarrateChapters(inputFile: String, using appState: AppState) async",
    )
    clear_chapters_body = _swift_function_body(source_actions, "func clearNarrateChapters()")

    assert "var youtubeSubtitleStreamsRequestSequence = 0" in source
    assert "youtubeSubtitleStreamsRequestSequence += 1" in subtitle_streams_body
    assert "let requestSequence = youtubeSubtitleStreamsRequestSequence" in subtitle_streams_body
    assert "if requestSequence == youtubeSubtitleStreamsRequestSequence" in subtitle_streams_body
    assert "guard requestSequence == youtubeSubtitleStreamsRequestSequence else" in subtitle_streams_body
    assert subtitle_streams_body.index("guard requestSequence == youtubeSubtitleStreamsRequestSequence else") < subtitle_streams_body.index(
        "youtubeInlineSubtitleStreams = response.streams"
    )
    assert subtitle_streams_body.count("guard requestSequence == youtubeSubtitleStreamsRequestSequence else") == 2
    assert "youtubeSubtitleStreamsRequestSequence += 1" in reset_streams_body

    assert "var narrateChaptersRequestSequence = 0" in source
    assert "narrateChaptersRequestSequence += 1" in chapters_body
    assert "let requestSequence = narrateChaptersRequestSequence" in chapters_body
    assert "if requestSequence == narrateChaptersRequestSequence" in chapters_body
    assert "guard requestSequence == narrateChaptersRequestSequence else { return }" in chapters_body
    assert chapters_body.index("guard requestSequence == narrateChaptersRequestSequence else { return }") < chapters_body.index(
        "narrateChapterOptions = chapters"
    )
    assert chapters_body.count("guard requestSequence == narrateChaptersRequestSequence else { return }") == 2
    assert "narrateChaptersRequestSequence += 1" in clear_chapters_body


def test_create_view_model_template_actions_are_split_and_target_wired() -> None:
    source = _source(CREATE_VIEW_MODEL)
    template_source = _source(CREATE_VIEW_MODEL_TEMPLATES)
    project = _source(XCODE_PROJECT)

    assert "extension AppleBookCreateViewModel" in template_source
    for helper in [
        "loadCreationTemplates",
        "deleteCreationTemplate",
        "saveCreationTemplate",
    ]:
        assert f"func {helper}(" in template_source
        assert f"func {helper}(" not in source

    assert "client.fetchCreationTemplates(mode: mode)" in template_source
    assert "client.saveCreationTemplate(request)" in template_source
    assert "let response = try await client.deleteCreationTemplate(templateId: trimmedID)" in template_source
    assert "response.templateId" in template_source
    assert "response.deleted" in template_source
    assert "AppleBookCreateViewModel+Templates.swift in Sources" in project
    assert project.count("AppleBookCreateViewModel+Templates.swift in Sources") == 4


def test_create_models_are_split_from_presentation_and_target_wired() -> None:
    models_source = _source(CREATE_MODELS)
    options_source = _source(CREATE_OPTIONS)
    support_source = _source(
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Features"
        / "Create"
        / "AppleBookCreateSupport.swift"
    )
    project = _source(XCODE_PROJECT)

    assert "struct AppleBookCreateDraft: Equatable" in models_source
    assert models_source.count("let bookMetadataExtras: [String: JSONValue]") == 2
    assert "struct AppleNarrationHistoryDefaults: Equatable" in models_source
    assert "struct AppleNarrateSourceDefaults: Equatable" in models_source
    assert "struct AppleSubtitleSourceDefaults: Equatable" in models_source
    assert "struct AppleYoutubeSourceDefaults: Equatable" in models_source
    assert "enum AppleCreateMode: String" not in models_source
    assert "struct AppleCreateSubmitState: Equatable" not in models_source
    assert "enum AppleSubtitleTranslationProvider: String" not in models_source
    assert "enum AppleCreateMode: String" in options_source
    assert "var creationTemplateMode: String" in options_source
    for mode_name in ["generated_book", "narrate_ebook", "subtitle_job", "youtube_dub"]:
        assert f'return "{mode_name}"' in options_source
    assert "struct AppleCreateSubmitState: Equatable" in options_source
    assert "enum AppleYoutubeDubTargetHeight: Int" in options_source
    assert "enum AppleSubtitleOutputFormat: String" in options_source
    assert "enum AppleSubtitleTranslationProvider: String" in options_source
    assert "enum AppleSubtitleTransliterationMode: String" in options_source
    assert "enum AppleSubtitleTuning" in options_source
    assert "enum AppleBookOutputChunking" in options_source
    assert "enum AppleBookSentenceSplitterMode: String, CaseIterable, Identifiable" in options_source
    assert 'return "Regex (stable)"' in options_source
    assert 'return "Modern (opt-in)"' in options_source
    assert "struct AppleBookSentenceSplitterOption: Identifiable, Equatable" in options_source
    assert "from capabilities: BookCreationSentenceSplitterCapabilities?" in options_source
    assert "capabilities?.supportedModes.compactMap" in options_source
    assert "guard let mode = recognizedMode(for: backendMode.id) else { return nil }" in options_source
    assert "return result.isEmpty ? fallbackOptions : result" in options_source
    assert "enum AppleBookCreatePresentation" not in models_source
    assert "enum AppleBookCreatePresentation" in support_source
    assert "AppleBookCreateModels.swift in Sources" in project
    assert project.count("AppleBookCreateModels.swift in Sources") == 4
    assert "AppleBookCreateOptions.swift in Sources" in project
    assert project.count("AppleBookCreateOptions.swift in Sources") == 4
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)
    assert "AppleBookCreateOptions.swift" in payload_script


def test_apple_create_template_modes_match_backend_and_readiness_probe() -> None:
    backend_modes = {str(mode) for mode in get_args(CreationTemplateMode)}
    readiness_modes = _python_literal_assignment(
        APPLE_CREATE_READINESS_SCRIPT,
        "CREATION_TEMPLATE_MODE_PROBES",
    )
    web_modes = _typescript_string_union(
        _source(WEB_API_DTOS),
        "CreationTemplateMode",
    )
    options_source = _source(CREATE_OPTIONS)
    creation_template_mode_body = options_source.split("var creationTemplateMode: String", 1)[
        1
    ].split("struct AppleCreateTargetLanguageDefaults", 1)[0]
    swift_modes = set(re.findall(r'return "([^"]+)"', creation_template_mode_body))

    assert backend_modes == {
        "generated_book",
        "narrate_ebook",
        "subtitle_job",
        "youtube_dub",
    }
    assert readiness_modes == backend_modes
    assert web_modes == backend_modes
    assert swift_modes == backend_modes


def test_create_defaults_are_split_from_support_and_target_wired() -> None:
    defaults_source = _source(CREATE_DEFAULTS)
    actions_source = _source(CREATE_CREATION_OPTIONS_ACTIONS)
    view_source = _source(CREATE_VIEW)
    support_source = _source(CREATE_SUPPORT)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "extension AppleBookCreatePresentation" in defaults_source
    assert "static func resolvedDefaults(" in defaults_source
    assert "bookSentenceSplitterMode: editedFields.contains(.bookSentenceSplitterMode)" in defaults_source
    assert "options.pipelineDefaults.sentenceSplitterMode" in defaults_source
    assert "static func targetLanguageDefaults(" in defaults_source
    assert "static func languagePreferences(" in defaults_source
    assert "static func resolvedLanguagePreferences(" in defaults_source
    assert "static func voiceOverrides(" in defaults_source
    assert "static func voiceOverridePipelineValue(" in defaults_source
    assert "static func normalizedTargetLanguages(" in defaults_source
    assert "static func normalizedLanguageList(" in defaults_source
    assert "static func normalizedBookGenres(" in defaults_source
    assert "private static func normalizedDefaultText(" in defaults_source
    assert "static func resolvedDefaults(" not in support_source
    assert "static func targetLanguageDefaults(" not in support_source
    assert "static func languagePreferences(" not in support_source
    assert "static func resolvedLanguagePreferences(" not in support_source
    assert "static func voiceOverrides(" not in support_source
    assert "static func voiceOverridePipelineValue(" not in support_source
    assert "static func normalizedTargetLanguages(" not in support_source
    assert "static func normalizedLanguageList(" not in support_source
    assert "static func normalizedBookGenres(" not in support_source
    assert "func refreshCreationOptions(force: Bool = false) async" in actions_source
    assert "private func applyCreationOptions(_ options: BookCreationOptionsResponse)" in actions_source
    assert "private func applyStoredLanguagePreferences()" in actions_source
    assert "func persistLanguagePreferences()" in actions_source
    assert "func clampSentenceCount(_ value: Int)" in actions_source
    assert "var sentenceBounds: BookCreationSentenceBounds" in actions_source
    assert "func refreshCreationOptions(force: Bool = false) async" not in view_source
    assert "private func applyCreationOptions(_ options: BookCreationOptionsResponse)" not in view_source
    assert "private func applyStoredLanguagePreferences()" not in view_source
    assert "AppleBookCreateDefaults.swift in Sources" in project
    assert project.count("AppleBookCreateDefaults.swift in Sources") == 4
    assert "AppleBookCreateCreationOptionsActions.swift in Sources" in project
    assert project.count("AppleBookCreateCreationOptionsActions.swift in Sources") == 4
    assert "AppleBookCreateDefaults.swift" in payload_script


def test_create_presentation_helpers_are_split_from_support_and_target_wired() -> None:
    presentation_source = _source(CREATE_PRESENTATION_HELPERS)
    support_source = _source(CREATE_SUPPORT)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "extension AppleBookCreatePresentation" in presentation_source
    assert "static func contentIndexChapters(" in presentation_source
    assert "guard let start, start >= 0 else { continue }" in presentation_source
    assert "let normalizedStart = max(start, 1)" in presentation_source
    assert "static func chapterRangeSelection(" in presentation_source
    assert "static func submitButtonPresentation(" in presentation_source
    assert "static func intakeStatusPresentation(" in presentation_source
    assert "static func canSubmit(" in presentation_source
    assert "static func derivedBaseOutput(" in presentation_source
    assert "static func subtitleModelLabel(" in presentation_source
    assert "static func subtitleTransliterationModelLabel(" in presentation_source
    assert "static func availableSubtitleLlmModels(" in presentation_source
    assert "static func availableSubtitleTransliterationModels(" in presentation_source
    assert "static func formattedAssEmphasisScale(" in presentation_source
    assert "static func formattedYoutubeOriginalMixPercent(" in presentation_source
    assert "static func formatDurationLabel(" in presentation_source
    assert "static func estimatedAudioDurationLabel(" in presentation_source
    assert "static func estimatedNarrateSentenceCount(" in presentation_source
    assert "private static func normalizedPresentationText(" in presentation_source
    assert "static func contentIndexChapters(" not in support_source
    assert "static func chapterRangeSelection(" not in support_source
    assert "static func submitButtonPresentation(" not in support_source
    assert "static func intakeStatusPresentation(" not in support_source
    assert "static func canSubmit(" not in support_source
    assert "static func derivedBaseOutput(" not in support_source
    assert "static func subtitleModelLabel(" not in support_source
    assert "static func subtitleTransliterationModelLabel(" not in support_source
    assert "static func availableSubtitleLlmModels(" not in support_source
    assert "static func availableSubtitleTransliterationModels(" not in support_source
    assert "static func formattedAssEmphasisScale(" not in support_source
    assert "static func formattedYoutubeOriginalMixPercent(" not in support_source
    assert "static func formatDurationLabel(" not in support_source
    assert "static func estimatedAudioDurationLabel(" not in support_source
    assert "static func estimatedNarrateSentenceCount(" not in support_source
    assert "AppleBookCreatePresentationHelpers.swift in Sources" in project
    assert project.count("AppleBookCreatePresentationHelpers.swift in Sources") == 4
    assert "AppleBookCreateDiscoveryPresentation.swift in Sources" in project
    assert project.count("AppleBookCreateDiscoveryPresentation.swift in Sources") == 4
    assert "AppleBookCreateDownloadStationPresentation.swift in Sources" in project
    assert project.count("AppleBookCreateDownloadStationPresentation.swift in Sources") == 4
    assert "AppleBookCreateVideoDiscoveryPresentation.swift in Sources" in project
    assert project.count("AppleBookCreateVideoDiscoveryPresentation.swift in Sources") == 4
    assert "AppleBookCreatePresentationHelpers.swift" in payload_script
    assert "AppleBookCreateDiscoveryPresentation.swift" in payload_script
    assert "AppleBookCreateDownloadStationPresentation.swift" in payload_script
    assert "AppleBookCreateVideoDiscoveryPresentation.swift" in payload_script


def test_create_normalization_helpers_are_split_from_support_and_target_wired() -> None:
    normalization_source = _source(CREATE_NORMALIZATION)
    support_source = _source(CREATE_SUPPORT)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "extension AppleBookCreatePresentation" in normalization_source
    for helper in [
        "clampSentenceCount",
        "clampImagePromptContextSentences",
        "clampImagePromptBatchSize",
        "clampBookSentencesPerOutputFile",
        "normalizedImageDimension",
        "normalizedImageSteps",
        "normalizedImageCfgScale",
        "normalizedPositiveInteger",
        "normalizedImageApiBaseURLs",
        "normalizedEndSentence",
        "normalizedPositiveNumber",
        "normalizedMode",
        "normalizedAudioBitrate",
        "clampTempo",
        "clampAssFontSize",
        "clampAssEmphasisScale",
        "clampSubtitleTranslationBatchSize",
        "clampSubtitleWorkerCount",
        "clampSubtitleBatchSize",
        "clampYoutubeOriginalMixPercent",
        "clampYoutubeFlushSentences",
        "normalizeYoutubeOffset",
        "normalizedSubtitleTimeRange",
        "normalizedYoutubeOffsetRange",
    ]:
        assert f"static func {helper}(" in normalization_source
        assert f"static func {helper}(" not in support_source

    assert "private static func normalizedNormalizationText(" in normalization_source
    assert "private static func bounded<T: Comparable>(" in normalization_source
    assert "private static func clamp<T: Comparable>(" not in support_source
    assert "AppleBookCreateNormalization.swift in Sources" in project
    assert project.count("AppleBookCreateNormalization.swift in Sources") == 4
    assert "AppleBookCreateNormalization.swift" in payload_script


def test_create_draft_helpers_are_split_from_support_and_target_wired() -> None:
    draft_source = _source(CREATE_DRAFTS)
    draft_actions_source = _source(CREATE_DRAFT_ACTIONS)
    view_source = _source(CREATE_VIEW)
    support_source = _source(CREATE_SUPPORT)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "extension AppleBookCreatePresentation" in draft_source
    for helper in [
        "generatedBookDraft",
        "narrateEbookDraft",
        "subtitleJobDraft",
        "normalizedSubtitleMediaMetadata",
        "youtubeDubDraft",
        "normalizedYoutubeMediaMetadata",
        "deriveBaseOutputName",
    ]:
        assert f"static func {helper}(" in draft_source
        assert f"static func {helper}(" not in support_source

    assert "private static func normalizedDraftText(" in draft_source
    assert "static func normalizedBookMetadataExtras(" in draft_source
    assert "private static func normalizedBookMetadataExtraValue(" in draft_source
    assert "static func normalizedSubtitleMediaMetadata(_ value: [String: JSONValue]?)" in draft_source
    assert "static func normalizedYoutubeMediaMetadata(_ value: [String: JSONValue])" in draft_source
    assert draft_source.count("var metadata = normalizedBookMetadataExtras(value)") >= 2
    assert "func currentGeneratedBookDraft() -> AppleBookCreateDraft" in draft_actions_source
    assert "func currentNarrateEbookDraft() -> AppleNarrateEbookDraft" in draft_actions_source
    assert "func currentSubtitleJobDraft() -> AppleSubtitleJobDraft?" in draft_actions_source
    assert "func currentYoutubeDubDraft() -> AppleYoutubeDubDraft?" in draft_actions_source
    assert "AppleBookCreatePresentation.generatedBookDraft(" in draft_actions_source
    assert "AppleBookCreatePresentation.narrateEbookDraft(" in draft_actions_source
    assert "AppleBookCreatePresentation.subtitleJobDraft(" in draft_actions_source
    assert "AppleBookCreatePresentation.youtubeDubDraft(" in draft_actions_source
    assert "func currentGeneratedBookDraft() -> AppleBookCreateDraft" not in view_source
    assert "func currentNarrateEbookDraft() -> AppleNarrateEbookDraft" not in view_source
    assert "func currentSubtitleJobDraft() -> AppleSubtitleJobDraft?" not in view_source
    assert "func currentYoutubeDubDraft() -> AppleYoutubeDubDraft?" not in view_source
    assert "AppleBookCreateDrafts.swift in Sources" in project
    assert project.count("AppleBookCreateDrafts.swift in Sources") == 4
    assert "AppleBookCreateDraftActions.swift in Sources" in project
    assert project.count("AppleBookCreateDraftActions.swift in Sources") == 4
    assert "AppleBookCreateDrafts.swift" in payload_script


def test_create_metadata_views_are_split_from_sections_and_target_wired() -> None:
    metadata_source = _source(CREATE_METADATA_VIEWS)
    metadata_controls_source = _source(CREATE_MEDIA_METADATA_CONTROLS)
    narration_source = _source(CREATE_NARRATION_SECTION)
    project = _source(XCODE_PROJECT)

    assert "struct AppleBookCreateAdvancedMetadataJSONEditor: View" in metadata_source
    assert "struct AppleBookCreateMetadataArtworkPreview: View" in metadata_source
    assert "struct AppleBookCreateMetadataStatusMessages: View" in metadata_source
    assert "struct AppleBookCreateMetadataActionButton: View" in metadata_source
    assert "struct AppleBookCreateBusyActionButton: View" in metadata_source
    assert "AppleBookCreateBusyActionButton(" in metadata_source
    assert "struct AppleBookCreateAdvancedMetadataJSONEditor: View" not in narration_source
    assert "struct AppleBookCreateMetadataArtworkPreview: View" not in narration_source
    assert "AppleBookCreateAdvancedMetadataJSONEditor(" in metadata_controls_source
    assert "AppleBookCreateMetadataArtworkPreview(" in metadata_controls_source
    assert metadata_controls_source.count("AppleBookCreateMetadataStatusMessages(") == 2
    assert metadata_controls_source.count("AppleBookCreateMetadataActionButton(") == 8
    assert "createSubtitleMetadataStatus" in metadata_controls_source
    assert "createYoutubeMetadataStatus" in metadata_controls_source
    assert "AppleBookCreateMetadataViews.swift in Sources" in project
    assert project.count("AppleBookCreateMetadataViews.swift in Sources") == 4


def test_create_status_views_are_split_from_create_view_and_target_wired() -> None:
    status_source = _source(CREATE_STATUS_VIEWS)
    view_source = _source(CREATE_VIEW)
    project = _source(XCODE_PROJECT)

    assert "struct AppleBookCreateStatusSection: View" in status_source
    assert "struct AppleBookCreateSubmitSection: View" in status_source
    assert 'accessibilityIdentifier("createBookOptionsLoadingLabel")' in status_source
    assert 'accessibilityIdentifier("createBookSubmitButton")' in status_source
    assert "AppleBookCreateStatusSection(" in view_source
    assert "AppleBookCreateSubmitSection(" in view_source
    assert "private func intakeStatusSystemImage" not in view_source
    assert "AppleBookCreateStatusViews.swift in Sources" in project
    assert project.count("AppleBookCreateStatusViews.swift in Sources") == 4


def test_create_presentation_state_is_split_from_create_view_and_target_wired() -> None:
    presentation_state_source = _source(CREATE_PRESENTATION_STATE)
    view_source = _source(CREATE_VIEW)
    project = _source(XCODE_PROJECT)

    assert "extension AppleBookCreateView" in presentation_state_source
    assert "var canSubmit: Bool" in presentation_state_source
    assert "var submitState: AppleCreateSubmitState" in presentation_state_source
    assert "var selectedCompatibleTemplateIDBinding: Binding<String>" in presentation_state_source
    assert "var webCreateHandoffURL: URL?" in presentation_state_source
    assert "var derivedBaseOutput: String" in presentation_state_source
    assert "var videoDiscoveryAvailability: AppleBookCreateVideoDiscoveryAvailability" in presentation_state_source
    assert "static var isTVPlatform: Bool" in presentation_state_source
    assert "AppleBookCreatePresentation.availableCreateModes(isTV: Self.isTVPlatform)" in presentation_state_source
    assert "AppleBookCreateTemplateSettings.selectedTemplatePickerValue(" in presentation_state_source
    assert "AppleBookCreateMetadataSources.subtitleSourceName(" in presentation_state_source

    for moved_definition in [
        "private var canSubmit: Bool",
        "private var submitState: AppleCreateSubmitState",
        "private var selectedCompatibleTemplateIDBinding: Binding<String>",
        "private var webCreateHandoffURL: URL?",
        "private var derivedBaseOutput: String",
        "private var videoDiscoveryAvailability: AppleBookCreateVideoDiscoveryAvailability",
        "private static var isTVPlatform: Bool",
    ]:
        assert moved_definition not in view_source

    assert "AppleBookCreatePresentationState.swift in Sources" in project
    assert project.count("AppleBookCreatePresentationState.swift in Sources") == 4


def test_create_view_section_callbacks_route_through_named_actions() -> None:
    view_source = _source(CREATE_VIEW)
    source_factory_source = _source(CREATE_SOURCE_SECTION_FACTORY)

    for callback in [
        "onRefreshPipelineFiles: refreshPipelineFilesFromSourceSection",
        "onRefreshSubtitleSources: refreshSubtitleSourcesFromSourceSection",
        "onRefreshYoutubeLibrary: refreshYoutubeLibraryFromSourceSection",
        "onChooseNarrateFile: chooseNarrateFile",
        "onChooseSubtitleFile: chooseSubtitleFile",
    ]:
        assert callback in source_factory_source

    for callback in [
        "onRefreshVoiceInventory: refreshVoiceInventory",
        "onPreviewVoice: previewVoice",
        "onLoadTvMetadata: loadYoutubeTvMetadata",
        "onLoadYoutubeMetadata: loadYoutubeVideoMetadata",
        "onClearTvMetadataCache: clearYoutubeTvMetadataCache",
        "onClearYoutubeMetadataCache: clearYoutubeVideoMetadataCache",
        "onLookup: lookupSubtitleMetadata",
        "onRefresh: refreshSubtitleMetadata",
        "onClear: clearSubtitleMetadata",
        "onClearCache: clearSubtitleMetadataCache",
        "onRetryDefaults: retryCreationOptions",
    ]:
        assert callback in view_source

    assert "onRefreshPipelineFiles: {\n                Task" not in source_factory_source
    assert "onRefreshVoiceInventory: {\n                Task" not in view_source
    assert "onLoadTvMetadata: {\n                Task" not in view_source
    assert "onLookup: {\n                Task" not in view_source
    assert "onRetryDefaults: {\n                Task" not in view_source


def test_tvos_create_loads_server_backed_source_defaults() -> None:
    source_actions = _source(CREATE_SOURCE_ACTIONS)

    for function_name, loader in [
        ("refreshPipelineFiles", "viewModel.loadPipelineFiles"),
        ("refreshSubtitleSources", "viewModel.loadSubtitleSources"),
        ("refreshYoutubeLibrary", "viewModel.loadYoutubeLibrary"),
    ]:
        match = re.search(
            rf"(?:private )?func {function_name}\(force: Bool = false\) async \{{(?P<body>.*?)\n    \}}",
            source_actions,
            re.DOTALL,
        )
        assert match, f"Missing {function_name}"
        body = match.group("body")
        assert loader in body
        assert "Self.isTVPlatform else { return }" not in body
        assert "guard !Self.isTVPlatform" not in body


def test_create_basic_sections_are_split_from_create_view_and_target_wired() -> None:
    basic_source = _source(CREATE_BASIC_SECTIONS)
    value_controls_source = _source(CREATE_VALUE_CONTROLS)
    view_source = _source(CREATE_VIEW)
    project = _source(XCODE_PROJECT)

    assert "struct AppleBookCreatePromptSection: View" in basic_source
    assert "struct AppleBookCreateMetadataSection: View" in basic_source
    assert "struct AppleBookCreateJobTypeSection: View" in basic_source
    assert "struct AppleBookCreateJobSettingsSection: View" in basic_source
    assert "struct AppleBookCreateDiscreteValueControl: View" in value_controls_source
    assert 'accessibilityIdentifier("createBookTopicField")' in basic_source
    assert 'accessibilityIdentifier("createNarrateOutputPathField")' in basic_source
    assert "AppleBookCreateDiscreteValueControl(" in basic_source
    assert "step: 5" in basic_source
    assert "LabeledContent(\"Sentences\")" not in basic_source
    assert "AppleBookCreatePromptSection(" in view_source
    assert "AppleBookCreateMetadataSection(" in view_source
    assert "AppleBookCreateJobTypeSection(" in view_source
    assert "AppleBookCreateJobSettingsSection(" in view_source
    assert "AppleBookCreateBasicSections.swift in Sources" in project
    assert project.count("AppleBookCreateBasicSections.swift in Sources") == 4


def test_create_output_section_is_split_from_create_view_and_target_wired() -> None:
    output_source = _source(CREATE_OUTPUT_SECTION)
    output_controls_source = _source(CREATE_OUTPUT_CONTROLS)
    generated_output_source = _source(CREATE_GENERATED_OUTPUT_CONTROLS)
    generated_image_source = _source(CREATE_GENERATED_IMAGE_CONTROLS)
    value_controls_source = _source(CREATE_VALUE_CONTROLS)
    control_bindings_source = _source(CREATE_CONTROL_BINDINGS)
    narration_source = _source(CREATE_NARRATION_SECTION)
    view_source = _source(CREATE_VIEW)
    metadata_actions_source = _source(CREATE_METADATA_ACTIONS)
    derived_state_source = _source(CREATE_DERIVED_STATE)
    presentation_state_source = _source(CREATE_PRESENTATION_STATE)
    project = _source(XCODE_PROJECT)

    assert "struct AppleBookCreateOutputSection: View" in output_source
    assert 'Section("Output")' in output_source
    assert "AppleBookCreateSubtitleOutputControls(" in output_source
    assert "AppleBookCreateYoutubeOutputControls(" in output_source
    assert "AppleBookCreateGeneratedOutputControls(" in output_source
    assert "sentenceSplitterMode: $sentenceSplitterMode" in output_source
    assert "struct AppleBookCreateSubtitleOutputControls: View" in output_controls_source
    assert "struct AppleBookCreateYoutubeOutputControls: View" in output_controls_source
    assert "struct AppleBookCreateGeneratedOutputControls: View" not in output_controls_source
    assert "struct AppleBookCreateGeneratedOutputControls: View" in generated_output_source
    assert "struct AppleBookCreateGeneratedImageControls: View" in generated_image_source
    assert "struct AppleBookCreateDiscreteValueControl: View" in value_controls_source
    assert "struct AppleBookCreateDiscreteDoubleValueControl: View" in value_controls_source
    assert "step: Int = 1" in value_controls_source
    assert "AppleBookCreateGeneratedImageControls(" in generated_output_source
    assert generated_output_source.count("AppleBookCreateDiscreteValueControl(") == 3
    assert "let sentenceSplitterOptions: [AppleBookSentenceSplitterOption]" in output_source
    assert "let sentenceSplitterOptions: [AppleBookSentenceSplitterOption]" in generated_output_source
    assert "sentenceSplitterOptions: sentenceSplitterOptions" in output_source
    assert "sentenceSplitterOptions: sentenceSplitterOptions" in view_source
    assert "var availableSubtitleLlmModels: [String]" in derived_state_source
    assert "var availableSubtitleTransliterationModels: [String]" in derived_state_source
    assert "var availableBookTransliterationModels: [String]" in derived_state_source
    assert "var formattedAssEmphasisScale: String" in derived_state_source
    assert "var formattedYoutubeOriginalMixPercent: String" in derived_state_source
    assert "var formattedTempo: String" in derived_state_source
    assert "var estimatedAudioDurationLabel: String?" in derived_state_source
    assert "private var availableSubtitleLlmModels: [String]" not in view_source
    assert "private var formattedTempo: String" not in view_source
    assert 'Picker("Sentence splitter", selection: $sentenceSplitterMode)' in generated_output_source
    assert 'accessibilityIdentifier("createBookSentenceSplitterModePicker")' in generated_output_source
    assert "ForEach(sentenceSplitterOptions)" in generated_output_source
    assert "ForEach(AppleBookSentenceSplitterMode.allCases)" not in generated_output_source
    assert "LabeledContent(\"Translation batch\")" not in generated_output_source
    assert "LabeledContent(\"Lookup batch\")" not in generated_output_source
    assert 'accessibilityIdentifier("createSubtitleAssFontSizeControl")' in output_controls_source
    assert 'accessibilityIdentifier("createSubtitleAssEmphasisControl")' in output_controls_source
    assert 'accessibilityIdentifier("createSubtitleMirrorBatchesToggle")' in output_controls_source
    assert 'accessibilityIdentifier("createSubtitleWorkerCountControl")' in output_controls_source
    assert 'accessibilityIdentifier("createSubtitleBatchSizeControl")' in output_controls_source
    assert 'accessibilityIdentifier("createSubtitleTranslationBatchSizeControl")' in output_controls_source
    assert 'accessibilityIdentifier("createYoutubeOriginalMixControl")' in output_controls_source
    assert 'accessibilityIdentifier("createYoutubeFlushSentencesControl")' in output_controls_source
    assert 'accessibilityIdentifier("createYoutubeTranslationBatchSizeControl")' in output_controls_source
    assert 'accessibilityIdentifier("createBookImagePromptPipelinePicker")' in generated_image_source
    assert 'accessibilityIdentifier("createBookImageNodeAvailabilityButton")' in generated_image_source
    assert 'accessibilityIdentifier("createBookImageNodeAvailabilityMessage")' in generated_image_source
    assert 'accessibilityIdentifier("createBookImageNodeAvailabilityError")' in generated_image_source
    assert "AppleBookCreatePresentation.normalizedImageApiBaseURLs(imageApiBaseURLs)" in generated_image_source
    assert "let onCheckImageNodes: () -> Void" in generated_image_source
    assert "isCheckingImageNodes: viewModel.isCheckingImageNodes" in view_source
    assert "imageNodeAvailabilityMessage: viewModel.imageNodeAvailabilityMessage" in view_source
    assert "imageNodeAvailabilityErrorMessage: viewModel.imageNodeAvailabilityErrorMessage" in view_source
    assert "onCheckImageNodes: checkImageNodes" in view_source
    assert "viewModel.checkImageNodeAvailability(" in metadata_actions_source
    assert "func checkImageNodeAvailability(" in _source(CREATE_VIEW_MODEL)
    assert "client.checkImageNodeAvailability(baseURLs: baseURLs)" in _source(CREATE_VIEW_MODEL)
    assert "Unable to check image nodes. Verify the image API URLs and backend connectivity." in _source(CREATE_VIEW_MODEL)
    assert 'accessibilityIdentifier("createBookImagePromptPipelinePicker")' not in generated_output_source
    assert 'accessibilityIdentifier("createBookLookupCacheBatchSizeControl")' in generated_output_source
    assert "struct AppleBookCreateSubtitleOutputControls: View" not in output_source
    assert "struct AppleBookCreateYoutubeOutputControls: View" not in output_source
    assert "struct AppleBookCreateGeneratedOutputControls: View" not in output_source
    assert "struct AppleBookCreateSubtitleOutputControls: View" not in narration_source
    assert "struct AppleBookCreateYoutubeOutputControls: View" not in narration_source
    assert "struct AppleBookCreateGeneratedOutputControls: View" not in narration_source
    assert "AppleBookCreateOutputSection(" in view_source
    assert "var sentenceSplitterOptions: [AppleBookSentenceSplitterOption]" in presentation_state_source
    assert "private var sentenceSplitterOptions: [AppleBookSentenceSplitterOption]" not in view_source
    assert "from: viewModel.creationOptions?.sentenceSplitterCapabilities" in presentation_state_source
    assert "from: viewModel.creationOptions?.sentenceSplitterCapabilities" not in view_source
    assert "AppleBookCreateSubtitleOutputControls(" not in view_source
    assert "AppleBookCreateYoutubeOutputControls(" not in view_source
    assert "AppleBookCreateGeneratedOutputControls(" not in view_source
    assert "var clampedAssFontSize: Int" in control_bindings_source
    assert "var clampedYoutubeFlushSentences: Int" in control_bindings_source
    assert "var clampedImagePromptPlanBatchSize: Int" in control_bindings_source
    assert "var sentenceCountBinding: Binding<Int>" in control_bindings_source
    assert "var subtitleOutputFormatBinding: Binding<AppleSubtitleOutputFormat>" in control_bindings_source
    assert "var youtubeOriginalMixPercentBinding: Binding<Double>" in control_bindings_source
    assert "func textBinding(for field: AppleBookCreateEditedField, value: Binding<String>)" in control_bindings_source
    assert "var narrateSourcePathBinding: Binding<String>" in control_bindings_source
    assert "func boolBinding(for field: AppleBookCreateEditedField, value: Binding<Bool>)" in control_bindings_source
    assert "func markEdited(_ field: AppleBookCreateEditedField)" in control_bindings_source
    assert "private var clampedAssFontSize: Int" not in view_source
    assert "private var sentenceCountBinding: Binding<Int>" not in view_source
    assert "private func textBinding(for field: AppleBookCreateEditedField, value: Binding<String>)" not in view_source
    assert "private var narrateSourcePathBinding: Binding<String>" not in view_source
    assert "func markEdited(_ field: AppleBookCreateEditedField)" not in view_source
    assert "AppleBookCreateOutputSection.swift in Sources" in project
    assert project.count("AppleBookCreateOutputSection.swift in Sources") == 4
    assert "AppleBookCreateControlBindings.swift in Sources" in project
    assert project.count("AppleBookCreateControlBindings.swift in Sources") == 4
    assert "AppleBookCreateOutputControls.swift in Sources" in project
    assert project.count("AppleBookCreateOutputControls.swift in Sources") == 4
    assert "AppleBookCreateGeneratedOutputControls.swift in Sources" in project
    assert project.count("AppleBookCreateGeneratedOutputControls.swift in Sources") == 4
    assert "AppleBookCreateGeneratedImageControls.swift in Sources" in project
    assert project.count("AppleBookCreateGeneratedImageControls.swift in Sources") == 4
    assert "AppleBookCreateValueControls.swift in Sources" in project
    assert project.count("AppleBookCreateValueControls.swift in Sources") == 4


def test_create_media_metadata_sections_are_split_from_create_view_and_target_wired() -> None:
    metadata_sections_source = _source(CREATE_MEDIA_METADATA_SECTIONS)
    metadata_controls_source = _source(CREATE_MEDIA_METADATA_CONTROLS)
    narration_source = _source(CREATE_NARRATION_SECTION)
    view_source = _source(CREATE_VIEW)
    project = _source(XCODE_PROJECT)

    assert "struct AppleBookCreateYoutubeMetadataSection: View" in metadata_sections_source
    assert "struct AppleBookCreateSubtitleMetadataSection: View" in metadata_sections_source
    assert "AppleBookCreateYoutubeMetadataControls(" in metadata_sections_source
    assert "AppleBookCreateSubtitleMetadataControls(" in metadata_sections_source
    assert "struct AppleBookCreateYoutubeMetadataControls: View" in metadata_controls_source
    assert "struct AppleBookCreateSubtitleMetadataControls: View" in metadata_controls_source
    assert "struct AppleBookCreateYoutubeMetadataControls: View" not in metadata_sections_source
    assert "struct AppleBookCreateSubtitleMetadataControls: View" not in metadata_sections_source
    assert "struct AppleBookCreateYoutubeMetadataControls: View" not in narration_source
    assert "struct AppleBookCreateSubtitleMetadataControls: View" not in narration_source
    assert "AppleBookCreateYoutubeMetadataSection(" in view_source
    assert "AppleBookCreateSubtitleMetadataSection(" in view_source
    assert "AppleBookCreateYoutubeMetadataControls(" not in view_source
    assert "AppleBookCreateSubtitleMetadataControls(" not in view_source
    assert "AppleBookCreateMediaMetadataSections.swift in Sources" in project
    assert project.count("AppleBookCreateMediaMetadataSections.swift in Sources") == 4
    assert "AppleBookCreateMediaMetadataControls.swift in Sources" in project
    assert project.count("AppleBookCreateMediaMetadataControls.swift in Sources") == 4


def test_create_payload_factory_is_split_from_view_model_and_target_wired() -> None:
    factory_source = _source(CREATE_PAYLOAD_FACTORY)
    media_payloads_source = _source(CREATE_MEDIA_PAYLOADS)
    view_model_source = _source(CREATE_VIEW_MODEL)
    submission_source = _source(CREATE_VIEW_MODEL_SUBMISSION)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "enum AppleBookCreatePayloadFactory" in factory_source
    assert "static func makeSubmission(from draft: AppleBookCreateDraft)" in factory_source
    assert "static func makePipelineSubmission(from draft: AppleNarrateEbookDraft)" in factory_source
    assert "static func makeSubtitlePayload(from draft: AppleSubtitleJobDraft)" not in factory_source
    assert "static func makeYoutubeDubPayload(from draft: AppleYoutubeDubDraft)" not in factory_source
    assert "extension AppleBookCreatePayloadFactory" in media_payloads_source
    assert "static func makeSubtitlePayload(from draft: AppleSubtitleJobDraft)" in media_payloads_source
    assert "static func makeYoutubeDubPayload(from draft: AppleYoutubeDubDraft)" in media_payloads_source
    assert "AppleBookCreatePayloadFactory.makeSubmission(from: draft)" in submission_source
    assert "AppleBookCreatePayloadFactory.makePipelineSubmission(from: effectiveDraft)" in submission_source
    assert "AppleBookCreatePayloadFactory.makeSubtitlePayload(from: draft)" in submission_source
    assert "AppleBookCreatePayloadFactory.makeYoutubeDubPayload(from: draft)" in submission_source
    assert "AppleBookCreatePayloadFactory.makeSubmission(from: draft)" not in view_model_source
    assert "private static func makeSubmission" not in view_model_source
    assert "private static func makePipelineSubmission(from draft: AppleNarrateEbookDraft)" not in view_model_source
    assert "private static func makeSubtitlePayload" not in view_model_source
    assert "private static func makeYoutubeDubPayload" not in view_model_source
    assert "AppleBookCreatePayloadFactory.swift in Sources" in project
    assert project.count("AppleBookCreatePayloadFactory.swift in Sources") == 4
    assert "AppleBookCreateMediaPayloads.swift in Sources" in project
    assert project.count("AppleBookCreateMediaPayloads.swift in Sources") == 4
    assert "mergeExtraBookMetadata(" in factory_source
    assert 'resolvedPipelineOverrides["sentence_splitter_mode"]' in factory_source
    assert "AppleBookSentenceSplitterMode(backendValue: sentenceSplitterMode).backendValue" in factory_source
    assert "extraMetadata: draft.bookMetadataExtras" in factory_source
    assert '"openlibrary_work_key"' in factory_source
    assert '"media_metadata_lookup"' in factory_source
    assert "AppleBookCreatePayloadFactory.swift" in payload_script
    assert "AppleBookCreateMediaPayloads.swift" in payload_script


def test_create_routing_is_split_from_support_and_target_wired() -> None:
    routing_source = _source(CREATE_ROUTING)
    support_source = _source(CREATE_SUPPORT)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)
    web_app_views = _source(WEB_APP_VIEWS)

    assert "extension AppleBookCreatePresentation" in routing_source
    assert "static func availableCreateModes(isTV: Bool)" in routing_source
    assert "AppleCreateMode.allCases" in routing_source
    assert "isTV ? []" not in routing_source
    assert "static func webCreateViewID(for mode: AppleCreateMode)" in routing_source
    assert "static func webCreateHandoffURL(" in routing_source
    assert "templateID: String? = nil" in routing_source
    assert 'return "books:create"' in routing_source
    assert 'return "pipeline:source"' in routing_source
    assert 'return "subtitles:youtube-dub"' in routing_source
    assert 'URLQueryItem(name: "source", value: "apple")' in routing_source
    assert 'URLQueryItem(name: "template_id", value: templateID)' in routing_source
    assert "templateID: webCreateHandoffTemplateID" in _source(CREATE_PRESENTATION_STATE)
    assert "var webCreateHandoffTemplateID: String?" in _source(CREATE_PRESENTATION_STATE)
    assert "private var webCreateHandoffTemplateID: String?" not in _source(CREATE_VIEW)
    assert "AppleBookCreateTemplateSettings.selectedCompatibleTemplateID(" in _source(CREATE_PRESENTATION_STATE)
    assert "compatibleCreationTemplates.first { $0.id == selectedTemplateID }?.id" not in _source(CREATE_VIEW)
    assert _swift_apple_create_views(routing_source) == _web_apple_create_views(web_app_views)
    assert "static func availableCreateModes" not in support_source
    assert "static func webCreateViewID" not in support_source
    assert "static func webCreateHandoffURL" not in support_source
    assert "AppleBookCreateRouting.swift in Sources" in project
    assert project.count("AppleBookCreateRouting.swift in Sources") == 4
    assert "AppleBookCreateRouting.swift" in payload_script


def test_tvos_browse_picker_includes_native_create() -> None:
    source = _source(LIBRARY_BROWSE_CHROME)

    tvos_block = re.search(
        r"#if os\(tvOS\)(?P<body>.*?)#else",
        source,
        flags=re.S,
    )
    assert tvos_block is not None
    assert "[.jobs, .create, .library, .settings, .search]" in tvos_block.group("body")
    assert 'case create = "Create"' in source
    assert '"browseSection\\(rawValue)Button"' in source

    non_tvos_block = re.search(
        r"#else(?P<body>.*?)#endif",
        source,
        flags=re.S,
    )
    assert non_tvos_block is not None
    assert "[.jobs, .create, .library, .settings, .search]" in non_tvos_block.group("body")


def test_create_history_defaults_are_split_from_support_and_target_wired() -> None:
    history_source = _source(CREATE_HISTORY_DEFAULTS)
    parsing_source = _source(CREATE_HISTORY_PARSING)
    support_source = _source(CREATE_SUPPORT)
    view_source = _source(CREATE_VIEW)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "extension AppleBookCreatePresentation" in history_source
    assert "static func narrationHistoryDefaults(" in history_source
    assert "static func generatedBookHistoryDefaults" in history_source
    assert 'narrationString($0, keys: ["sentence_splitter_mode", "sentenceSplitterMode"])' in history_source
    assert 'bookSentenceSplitterMode: historyString(in: sources, keys: ["sentence_splitter_mode", "sentenceSplitterMode"])' in history_source
    assert "static func subtitleHistoryDefaults" in history_source
    assert "static func youtubeHistoryDefaults" in history_source
    assert "static func narrationStartSentence" not in history_source
    assert "static func latestNarrationJob" not in history_source
    assert "static func narrationString(" not in history_source
    assert "static func historyOffset(" not in history_source
    assert "static func parseJobDate(" not in history_source
    assert "extension AppleBookCreatePresentation" in parsing_source
    assert "static func narrationStartSentence" in parsing_source
    assert "static func latestNarrationJob" in parsing_source
    assert "static func narrationString(" in parsing_source
    assert "static func historyOffset(" in parsing_source
    assert "static func parseJobDate(" in parsing_source
    assert "static func narrationHistoryDefaults(" not in support_source
    assert "static func generatedBookHistoryDefaults" not in support_source
    assert "static func subtitleHistoryDefaults" not in support_source
    assert "static func youtubeHistoryDefaults" not in support_source
    assert "static func latestNarrationJob" not in support_source
    assert "static func narrationString(" not in support_source
    assert "static func historyOffset(" not in support_source
    assert "static func parseJobDate(" not in support_source
    history_actions_source = _source(CREATE_HISTORY_DEFAULT_ACTIONS)
    assert "func applyHistoryDefaultsForCurrentMode()" in history_actions_source
    assert "private func applyGeneratedBookHistoryDefaults()" in history_actions_source
    assert "func applyHistoryDefaultsForCurrentMode()" not in view_source
    assert "AppleBookCreateHistoryDefaults.swift in Sources" in project
    assert project.count("AppleBookCreateHistoryDefaults.swift in Sources") == 4
    assert "AppleBookCreateHistoryDefaultActions.swift in Sources" in project
    assert project.count("AppleBookCreateHistoryDefaultActions.swift in Sources") == 4
    assert "AppleBookCreateHistoryParsing.swift in Sources" in project
    assert project.count("AppleBookCreateHistoryParsing.swift in Sources") == 4
    assert "AppleBookCreateHistoryDefaults.swift" in payload_script
    assert "AppleBookCreateHistoryParsing.swift" in payload_script


def test_create_language_options_are_split_from_support_and_target_wired() -> None:
    language_source = _source(CREATE_LANGUAGE_OPTIONS)
    sample_source = _source(CREATE_VOICE_PREVIEW_SAMPLES)
    selector_source = _source(CREATE_LANGUAGE_SELECTOR)
    view_source = _source(CREATE_VIEW)
    derived_state_source = _source(CREATE_DERIVED_STATE)
    support_source = _source(CREATE_SUPPORT)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "extension AppleBookCreatePresentation" in language_source
    assert "static func availableInputLanguages(" in language_source
    assert "static func availableTargetLanguages(" in language_source
    assert "static func availableVoices(" in language_source
    assert "static func languageVoiceOptions(" in language_source
    assert "static func targetLanguagesForVoiceOverrides(" in language_source
    assert "static func voiceInventoryOptions(" in language_source
    assert "static func sampleSentence(language: String, fallbackLabel: String)" in language_source
    assert "static func voicePreviewKey(language: String)" in language_source
    assert "AppleBookCreateVoicePreviewSamples.sentences[code]" in language_source
    assert "enum AppleBookCreateVoicePreviewSamples" in sample_source
    assert "AppleBookCreateLanguage.options(from: supported)" in language_source
    assert "static func availableInputLanguages(" not in support_source
    assert "static func availableTargetLanguages(" not in support_source
    assert "static func availableVoices(" not in support_source
    assert "static func languageVoiceOptions(" not in support_source
    assert "static func targetLanguagesForVoiceOverrides(" not in support_source
    assert "static func voiceInventoryOptions(" not in support_source
    assert "AppleBookCreatePresentation.languageVoiceOptions(" in derived_state_source
    assert "AppleBookCreatePresentation.targetLanguagesForVoiceOverrides(" in derived_state_source
    assert "AppleBookCreatePresentation.languageVoiceOptions(" not in view_source
    assert "AppleBookCreatePresentation.targetLanguagesForVoiceOverrides(" not in view_source
    assert "var result = [String: [AppleBookCreateVoiceOption]]()" not in view_source
    assert "AppleBookCreateLanguageOptions.swift in Sources" in project
    assert project.count("AppleBookCreateLanguageOptions.swift in Sources") == 4
    assert "AppleBookCreateDerivedState.swift in Sources" in project
    assert project.count("AppleBookCreateDerivedState.swift in Sources") == 4
    assert "AppleBookCreateVoicePreviewSamples.swift in Sources" in project
    assert project.count("AppleBookCreateVoicePreviewSamples.swift in Sources") == 4
    assert "struct AppleBookCreateLanguageSelector: View" in selector_source
    assert "AppleBookCreateLanguageSelector.swift in Sources" in project
    assert project.count("AppleBookCreateLanguageSelector.swift in Sources") == 4
    assert "AppleBookCreateLanguageOptions.swift" in payload_script
    assert "AppleBookCreateVoicePreviewSamples.swift" in payload_script


def test_create_source_selection_is_split_from_support_and_target_wired() -> None:
    source_selection = _source(CREATE_SOURCE_SELECTION)
    source_actions = _source(CREATE_SOURCE_ACTIONS)
    support_source = _source(CREATE_SUPPORT)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "extension AppleBookCreatePresentation" in source_selection
    assert "static func preferredPipelineEbook(from files: PipelineFileBrowserResponse?) -> PipelineFileEntry?" in source_selection
    assert "static func preferredSubtitleSource(from response: SubtitleSourceListResponse?)" in source_selection
    assert "static func narrateSourceDefaults(" in source_selection
    assert "normalizedSourceText(sourceBaseOutput).isEmpty && !didEditBaseOutput" in source_selection
    assert "static func subtitleSourceDefaults(" in source_selection
    assert "static func preferredYoutubeSelection(from library: YoutubeNasLibraryResponse?)" in source_selection
    assert "sortedYoutubeVideosForDefaultSelection(library?.videos ?? [])" in source_selection
    assert "private static func sortedYoutubeVideosForDefaultSelection(" in source_selection
    assert "let video = videos.first { !playableYoutubeSubtitles(for: $0).isEmpty } ?? videos[0]" in source_selection
    assert "static func youtubeSelection(" in source_selection
    assert "let storedSubtitle = requestedVideoPath == selectedVideo.path" in source_selection
    assert "static func youtubeSourceDefaults(" in source_selection
    assert "let scopeChanged = currentStorageScope != nextStorageScope" in source_selection
    assert "static func youtubeLibraryCacheKey(baseKey: String, baseDir: String)" in source_selection
    assert "static func subtitleShowOriginalPreferenceKey(baseKey: String)" in source_selection
    assert "private static let subtitleJobSourceFormats" not in support_source
    assert "static func preferredPipelineEbook" not in support_source
    assert "static func preferredSubtitleSource" not in support_source
    assert "AppleBookCreateSourceSelection.swift in Sources" in project
    assert project.count("AppleBookCreateSourceSelection.swift in Sources") == 4
    assert "AppleBookCreateSourceSelection.swift" in payload_script
    view_source = _source(CREATE_VIEW)
    control_bindings_source = _source(CREATE_CONTROL_BINDINGS)
    assert "extension AppleBookCreateView" in source_actions
    for source_handler in [
        "handleYoutubeBaseDirChange",
        "handleSubtitleSourcePathChange",
        "requestDeleteSubtitleSource",
        "deleteSubtitleSource",
        "handleYoutubeVideoPathChange",
        "handleYoutubeSubtitlePathChange",
        "refreshPipelineFilesFromSourceSection",
        "searchAcquisitionDiscovery",
        "applyAcquisitionDiscoveryCandidate",
        "searchYoutubeAcquisitionDiscovery",
        "applyYoutubeAcquisitionDiscoveryCandidate",
        "submitDownloadStation",
        "pollDownloadStation",
        "requestDeletePipelineEbook",
        "deletePipelineEbook",
        "refreshSubtitleSources",
        "refreshYoutubeLibrary",
        "inspectYoutubeSubtitles",
        "extractYoutubeSubtitles",
        "clearNarrateChapterSelection",
    ]:
        assert f"func {source_handler}(" in source_actions
    assert "AppleBookCreatePresentation.narrateSourceDefaults(" in source_actions
    assert "trimmed(sourceBaseOutput).isEmpty && !editedFields.contains(.sourceBaseOutput)" not in view_source
    assert "func refreshNarrateBaseOutputIfNeeded(" in source_actions
    assert "private func shouldRefreshNarrateBaseOutput(" in source_actions
    assert "currentBaseOutput == derivedNarrateBaseOutputName(for: previousSourcePath)" in source_actions
    assert "private func derivedNarrateBaseOutputName(for sourcePath: String)" in source_actions
    assert "AppleBookCreatePresentation.selectedPipelineEbook(" in source_actions
    assert "refreshNarrateBaseOutputIfNeeded(for: newValue, replacing: previousSourcePath)" in control_bindings_source
    assert "AppleBookCreatePresentation.subtitleSourceDefaults(" in source_actions
    assert "AppleBookCreatePresentation.youtubeSourceDefaults(" in source_actions
    assert "AppleBookCreatePresentation.narrateSourceDefaults(" not in view_source
    assert "AppleBookCreatePresentation.subtitleSourceDefaults(" not in view_source
    assert "AppleBookCreatePresentation.youtubeSourceDefaults(" not in view_source
    assert "AppleBookCreateSourceActions.swift in Sources" in project
    assert project.count("AppleBookCreateSourceActions.swift in Sources") == 4
    assert "let scopeChanged = youtubeSelectionStorageScope != youtubeLibraryLoadKey" not in view_source


def test_create_storage_keys_are_split_from_view_and_target_wired() -> None:
    storage_source = _source(CREATE_STORAGE_KEYS)
    preferences_source = _source(CREATE_PREFERENCES)
    view_source = _source(CREATE_VIEW)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "enum AppleBookCreateStorageKeys" in storage_source
    assert "static func loadScope(apiBaseURL: URL?, userID: String?, userRole: String?)" in storage_source
    assert "static func youtubeSelection(baseKey: String, baseDir: String, field: String)" in storage_source
    assert "static func subtitleShowOriginal(baseKey: String)" in storage_source
    assert "static func youtubeBaseDir(baseKey: String)" in storage_source
    assert "static func youtubeLibraryLoad(baseKey: String, baseDir: String)" in storage_source
    assert "static func languagePreferences(baseKey: String)" in storage_source
    assert "AppleBookCreatePresentation.youtubeLibraryCacheKey" in storage_source
    assert "AppleBookCreatePresentation.subtitleShowOriginalPreferenceKey" in storage_source
    assert "ebookTools.appleCreate.youtubeDub.\\(field).\\(baseKey)" in storage_source
    assert "ebookTools.appleCreate.youtubeDub.baseDir.\\(baseKey)" in storage_source
    assert "ebookTools.appleCreate.bookJobDefaults.v1.\\(baseKey)" in storage_source
    assert "ebookTools.appleCreate.youtubeDub.\\(field)" not in view_source
    assert "ebookTools.appleCreate.youtubeDub.baseDir" not in view_source
    assert "ebookTools.appleCreate.bookJobDefaults.v1" not in view_source
    assert "AppleBookCreateStorageKeys.youtubeLibraryLoad(" in preferences_source
    assert "AppleBookCreateStorageKeys.youtubeLibraryLoad(" not in view_source
    assert "AppleBookCreateStorageKeys.loadScope(" not in preferences_source
    assert "configuration.apiBaseURL.absoluteString" not in view_source
    assert "AppleBookCreateStorageKeys.swift in Sources" in project
    assert project.count("AppleBookCreateStorageKeys.swift in Sources") == 4
    assert "AppleBookCreateStorageKeys.swift" in payload_script


def test_create_preferences_are_split_from_view_and_target_wired() -> None:
    preferences_source = _source(CREATE_PREFERENCES)
    lifecycle_source = _source(CREATE_LIFECYCLE)
    actions_source = _source(CREATE_CREATION_OPTIONS_ACTIONS)
    view_source = _source(CREATE_VIEW)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "enum AppleBookCreatePreferences" in preferences_source
    assert "struct AppleBookCreatePreferenceScope" in preferences_source
    assert "let baseKey: String" in preferences_source
    assert "let youtubeBaseDir: String" in preferences_source
    assert "var youtubeLibraryLoadKey: String" in preferences_source
    assert "static func storedYoutubeSelectionPath(" in preferences_source
    assert "static func persistYoutubeSelectionPath(" in preferences_source
    assert "static func storedYoutubeBaseDir(" in preferences_source
    assert "static func persistYoutubeBaseDir(" in preferences_source
    assert "static func storedSubtitleShowOriginal(" in preferences_source
    assert "static func persistSubtitleShowOriginal(" in preferences_source
    assert "static func storedLanguagePreferences(" in preferences_source
    assert "static func persistLanguagePreferences(" in preferences_source
    assert "defaults: UserDefaults = .standard" in preferences_source
    assert "decoder: JSONDecoder = JSONDecoder()" in preferences_source
    assert "encoder: JSONEncoder = JSONEncoder()" in preferences_source
    assert "AppleBookCreateStorageKeys.youtubeSelection(" in preferences_source
    assert "AppleBookCreateStorageKeys.youtubeBaseDir(" in preferences_source
    assert "AppleBookCreateStorageKeys.subtitleShowOriginal(" in preferences_source
    assert "AppleBookCreateStorageKeys.languagePreferences(" in preferences_source
    assert "private static func setOrRemove(" in preferences_source
    assert "extension AppleBookCreateView" not in preferences_source
    assert "extension AppleBookCreateView" in lifecycle_source
    assert "var creationOptionsLoadKey: String" in lifecycle_source
    assert "var creationTemplateLoadKey: String" in lifecycle_source
    assert '"\\(creationOptionsLoadKey)|templateMode=\\(creationMode.creationTemplateMode)"' in lifecycle_source
    assert "AppleBookCreateStorageKeys.loadScope(" in lifecycle_source
    assert "var preferenceScope: AppleBookCreatePreferenceScope" in lifecycle_source
    assert "baseKey: creationOptionsLoadKey" in lifecycle_source
    assert "youtubeBaseDir: youtubeBaseDir" in lifecycle_source
    assert "func storedYoutubeSelectionPath(field: String)" in lifecycle_source
    assert "preferenceScope.storedYoutubeSelectionPath(field: field)" in lifecycle_source
    assert "func persistYoutubeSelectionPath(_ path: String, field: String)" in lifecycle_source
    assert "preferenceScope.persistYoutubeSelectionPath(path, field: field)" in lifecycle_source
    assert "func applyStoredYoutubeBaseDir()" in lifecycle_source
    assert "preferenceScope.storedYoutubeBaseDir()" in lifecycle_source
    assert "func persistYoutubeBaseDir(_ baseDir: String)" in lifecycle_source
    assert "preferenceScope.persistYoutubeBaseDir(baseDir)" in lifecycle_source
    assert "func applyStoredSubtitleShowOriginal()" in lifecycle_source
    assert "preferenceScope.storedSubtitleShowOriginal()" in lifecycle_source
    assert "func persistSubtitleShowOriginal(_ value: Bool)" in lifecycle_source
    assert "preferenceScope.persistSubtitleShowOriginal(value)" in lifecycle_source
    assert "preferenceScope.storedLanguagePreferences()" in actions_source
    assert "preferenceScope.persistLanguagePreferences(preferences)" in actions_source
    assert "var youtubeLibraryLoadKey: String" in lifecycle_source
    assert "preferenceScope.youtubeLibraryLoadKey" in lifecycle_source
    assert "var preferenceScope: AppleBookCreatePreferenceScope" not in view_source
    assert "func storedYoutubeSelectionPath(field: String)" not in view_source
    assert "func persistYoutubeSelectionPath(_ path: String, field: String)" not in view_source
    assert "func applyStoredYoutubeBaseDir()" not in view_source
    assert "func persistYoutubeBaseDir(_ baseDir: String)" not in view_source
    assert "func applyStoredSubtitleShowOriginal()" not in view_source
    assert "func persistSubtitleShowOriginal(_ value: Bool)" not in view_source
    assert "preferenceScope.storedLanguagePreferences()" not in view_source
    assert "preferenceScope.persistLanguagePreferences(preferences)" not in view_source
    assert "AppleBookCreatePreferences.storedYoutubeSelectionPath(" not in view_source
    assert "AppleBookCreatePreferences.persistYoutubeSelectionPath(" not in view_source
    assert "AppleBookCreatePreferences.storedYoutubeBaseDir(" not in view_source
    assert "AppleBookCreatePreferences.persistYoutubeBaseDir(" not in view_source
    assert "AppleBookCreatePreferences.storedSubtitleShowOriginal(" not in view_source
    assert "AppleBookCreatePreferences.persistSubtitleShowOriginal(" not in view_source
    assert "AppleBookCreatePreferences.storedLanguagePreferences(" not in view_source
    assert "AppleBookCreatePreferences.persistLanguagePreferences(" not in view_source
    assert "UserDefaults.standard.string(forKey: youtubeBaseDirStorageKey)" not in view_source
    assert "UserDefaults.standard.object(forKey: subtitleShowOriginalStorageKey)" not in view_source
    assert "UserDefaults.standard.data(forKey: languagePreferencesStorageKey)" not in view_source
    assert "UserDefaults.standard.set(data, forKey: languagePreferencesStorageKey)" not in view_source
    assert "private var languagePreferencesStorageKey" not in view_source
    assert "AppleBookCreatePreferences.swift in Sources" in project
    assert project.count("AppleBookCreatePreferences.swift in Sources") == 4
    assert "AppleBookCreatePreferences.swift" in payload_script


def test_create_metadata_sources_are_split_from_view_and_target_wired() -> None:
    metadata_source = _source(CREATE_METADATA_SOURCES)
    view_source = _source(CREATE_VIEW)
    presentation_state_source = _source(CREATE_PRESENTATION_STATE)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "enum AppleBookCreateMetadataSources" in metadata_source
    assert "static func youtubeTvSourceName(subtitlePath: String, videoPath: String)" in metadata_source
    assert "static func youtubeVideoSourceName(videoPath: String)" in metadata_source
    assert "static func subtitleSourceName(" in metadata_source
    assert "sources: [SubtitleSourceEntry]" in metadata_source
    assert "URL(fileURLWithPath: normalizedPath).lastPathComponent" in metadata_source
    assert "AppleBookCreateMetadataSources.youtubeTvSourceName(" in presentation_state_source
    assert "AppleBookCreateMetadataSources.youtubeVideoSourceName(" in presentation_state_source
    assert "AppleBookCreateMetadataSources.subtitleSourceName(" in presentation_state_source
    assert "AppleBookCreateMetadataSources.youtubeTvSourceName(" not in view_source
    assert "AppleBookCreateMetadataSources.youtubeVideoSourceName(" not in view_source
    assert "AppleBookCreateMetadataSources.subtitleSourceName(" not in view_source
    assert "private var defaultSubtitleMetadataLookupSourceName" not in view_source
    assert "URL(fileURLWithPath: selectedPath).lastPathComponent" not in view_source
    assert "AppleBookCreateMetadataSources.swift in Sources" in project
    assert project.count("AppleBookCreateMetadataSources.swift in Sources") == 4
    assert "AppleBookCreateMetadataSources.swift" in payload_script


def test_create_file_import_is_split_from_view_and_target_wired() -> None:
    import_source = _source(CREATE_FILE_IMPORT)
    import_actions_source = _source(CREATE_FILE_IMPORT_ACTIONS)
    modifier_source = _source(CREATE_FILE_IMPORTER_MODIFIER)
    view_source = _source(CREATE_VIEW)
    source_factory_source = _source(CREATE_SOURCE_SECTION_FACTORY)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "struct AppleBookCreateImportedFile: Equatable" in import_source
    assert "struct AppleBookCreateNarrateImportSelection: Equatable" in import_source
    assert "struct AppleBookCreateSubtitleImportSelection: Equatable" in import_source
    assert "enum AppleBookCreateFileImport" in import_source
    assert "static var epubContentType: UTType" in import_source
    assert "static var subtitleContentTypes: [UTType]" in import_source
    assert "static func importedFile(from urls: [URL])" in import_source
    assert "static func derivedNarrateBaseOutput(" in import_source
    assert "static func narrateImportSelection(" in import_source
    assert "static func subtitleImportSelection(from urls: [URL])" in import_source
    assert "UTType(filenameExtension: \"epub\")" in import_source
    assert "UTType(filenameExtension: \"srt\")" in import_source
    assert "UTType(filenameExtension: \"vtt\")" in import_source
    assert "extension AppleBookCreateView" in import_actions_source
    assert "func handleNarrateEbookImport(_ result: Result<[URL], Error>)" in import_actions_source
    assert "func handleSubtitleFileImport(_ result: Result<[URL], Error>)" in import_actions_source
    assert "func importNarrateEbookToServer(_ selection: AppleBookCreateNarrateImportSelection)" in import_actions_source
    assert "AppleBookCreateFileImport.narrateImportSelection(" in import_actions_source
    assert "AppleBookCreateFileImport.subtitleImportSelection(from: urls)" in import_actions_source
    assert "AppleBookCreateFileImport.narrateImportSelection(" not in view_source
    assert "AppleBookCreateFileImport.subtitleImportSelection(from: urls)" not in view_source
    assert "struct AppleBookCreateFileImporterModifier: ViewModifier" in modifier_source
    assert "AppleBookCreateFileImport.epubContentType" in modifier_source
    assert "AppleBookCreateFileImport.subtitleContentTypes" in modifier_source
    assert "AppleBookCreateFileImporterModifier(" in view_source
    assert "AppleBookCreateFileImport.epubContentType" not in view_source
    assert "AppleBookCreateFileImport.subtitleContentTypes" not in view_source
    assert "url.lastPathComponent" not in view_source
    assert "url.deletingPathExtension().lastPathComponent" not in view_source
    assert "AppleBookCreateFileImport.swift in Sources" in project
    assert project.count("AppleBookCreateFileImport.swift in Sources") == 4
    assert "AppleBookCreateFileImportActions.swift in Sources" in project
    assert project.count("AppleBookCreateFileImportActions.swift in Sources") == 4
    assert "AppleBookCreateFileImporterModifier.swift in Sources" in project
    assert project.count("AppleBookCreateFileImporterModifier.swift in Sources") == 4
    assert "AppleBookCreateFileImport.swift" in payload_script
    assert "guard !didEditBaseOutput else" in import_source
    assert "currentBaseOutput.trimmingCharacters" not in import_source
    assert "@Published var isUploadingPipelineEbook = false" in _source(CREATE_VIEW_MODEL)
    assert "func uploadPipelineEbook(" in _source(CREATE_VIEW_MODEL_SOURCES)
    assert "client.uploadPipelineEbook(fileURL: fileURL, filename: filename)" in _source(CREATE_VIEW_MODEL_SOURCES)
    assert "mergePipelineEbook(uploaded)" in _source(CREATE_VIEW_MODEL_SOURCES)
    assert "isUploadingPipelineEbook: viewModel.isUploadingPipelineEbook" in source_factory_source
    assert "importNarrateEbookToServer(selection)" in import_actions_source
    assert "viewModel.uploadPipelineEbook(" in import_actions_source
    assert "sourcePath = uploaded.path" in import_actions_source
    assert "selectedNarrateFileURL = nil" in import_actions_source
    assert "private func importNarrateEbookToServer(_ selection: AppleBookCreateNarrateImportSelection)" not in view_source
    assert "isUploadingPipelineEbook ? \"Importing EPUB\"" in _source(CREATE_SOURCE_CONTROLS)
    assert ".disabled(isBusy)" in _source(CREATE_SOURCE_SUPPORT_CONTROLS)
    assert 'accessibilityIdentifier("\\(buttonIdentifier).progress")' in _source(CREATE_SOURCE_SUPPORT_CONTROLS)


def test_source_section_can_move_job_type_picker_out_of_detail_form() -> None:
    source = _source(CREATE_SOURCE_SECTION)
    controls_source = _source(CREATE_SOURCE_CONTROLS)
    support_controls_source = _source(CREATE_SOURCE_SUPPORT_CONTROLS)
    youtube_source = _source(CREATE_YOUTUBE_SOURCE_CONTROLS)
    youtube_discovery_source = _source(CREATE_YOUTUBE_DISCOVERY_CONTROLS)
    youtube_support_source = _source(CREATE_YOUTUBE_SOURCE_SUPPORT_CONTROLS)
    narration_source = _source(CREATE_NARRATION_SECTION)
    project = _source(XCODE_PROJECT)

    assert "struct AppleBookCreateSourceSection: View" in source
    assert "struct AppleBookCreateNarrateSourceControls: View" in controls_source
    assert "struct AppleBookCreateSubtitleSourceControls: View" in support_controls_source
    assert "struct AppleBookCreateYoutubeSourceControls: View" in youtube_source
    assert "struct AppleBookCreateYoutubeDiscoveryControls: View" in youtube_discovery_source
    assert "struct AppleBookCreateYoutubeDownloadStationControls: View" in youtube_support_source
    assert "struct AppleBookCreateYoutubeEmbeddedSubtitleControls: View" in youtube_support_source
    assert "struct AppleBookCreateFileImportControl: View" in support_controls_source
    assert "struct AppleBookCreateSourceActionRow: View" in support_controls_source
    assert "AppleBookCreateBusyActionButton(" in support_controls_source
    assert "let showsJobTypePicker: Bool" in source
    assert "let showsNarrateRangeControls: Bool" in source
    assert "if showsJobTypePicker || creationMode != .generatedBook" in source
    assert 'Picker("Job type", selection: $creationMode)' in source
    assert '.accessibilityIdentifier("createJobTypePicker")' in source
    assert "AppleBookCreateNarrateSourceControls(" in source
    assert "AppleBookCreateSubtitleSourceControls(" in source
    assert "AppleBookCreateYoutubeSourceControls(" in source
    assert "private var narrateRangeControls: some View" not in source
    assert "private func subtitleEntryLabel(" not in source
    assert "private var embeddedYoutubeSubtitleControls: some View" not in source
    assert "private func youtubeVideoLabel(" not in source
    assert "if showsNarrateRangeControls" in controls_source
    assert 'Picker("Server EPUB", selection: $sourcePath)' in controls_source
    assert "shouldShowNoServerEbooksMessage" in controls_source
    assert "noServerEbooksMessage" in controls_source
    assert "pipelineFiles?.booksRoot" in controls_source
    assert "No server EPUBs found." in controls_source
    assert 'Picker("Server subtitle", selection: $subtitleSourcePath)' in support_controls_source
    assert "AppleBookCreatePresentation.chapterRangeSelection(" in support_controls_source
    assert "AppleBookCreatePresentation.subtitleJobSources(from: subtitleSources)" in support_controls_source
    assert 'Picker("NAS video", selection: $youtubeVideoPath)' in youtube_source
    assert "AppleBookCreatePresentation.playableYoutubeSubtitles(for:" in youtube_source
    assert controls_source.count("AppleBookCreateSourceActionRow(") == 1
    assert support_controls_source.count("AppleBookCreateSourceActionRow(") == 1
    assert youtube_source.count("AppleBookCreateSourceActionRow(") == 1
    assert youtube_support_source.count("AppleBookCreateSourceActionRow(") == 2
    assert 'buttonIdentifier: "createYoutubeInspectEmbeddedSubtitlesButton"' in youtube_support_source
    assert "struct AppleBookCreateSourceSection: View" not in narration_source
    assert "AppleBookCreateSourceSection.swift in Sources" in project
    assert project.count("AppleBookCreateSourceSection.swift in Sources") == 4
    assert "AppleBookCreateSourceSectionFactory.swift in Sources" in project
    assert project.count("AppleBookCreateSourceSectionFactory.swift in Sources") == 4
    assert "AppleBookCreateSourceControls.swift in Sources" in project
    assert project.count("AppleBookCreateSourceControls.swift in Sources") == 4
    assert "AppleBookCreateSourceSupportControls.swift in Sources" in project
    assert project.count("AppleBookCreateSourceSupportControls.swift in Sources") == 4
    assert "AppleBookCreateYoutubeSourceControls.swift in Sources" in project
    assert project.count("AppleBookCreateYoutubeSourceControls.swift in Sources") == 4
    assert "AppleBookCreateYoutubeDiscoveryControls.swift in Sources" in project
    assert project.count("AppleBookCreateYoutubeDiscoveryControls.swift in Sources") == 4
    assert "AppleBookCreateYoutubeSourceSupportControls.swift in Sources" in project
    assert project.count("AppleBookCreateYoutubeSourceSupportControls.swift in Sources") == 4
    assert "AppleBookCreateNarrationSection.swift in Sources" in project
    assert project.count("AppleBookCreateNarrationSection.swift in Sources") == 4
    assert "AppleBookCreateSections.swift" not in project


def test_subtitle_source_delete_is_wired_through_apple_create() -> None:
    view_source = _source(CREATE_VIEW)
    lifecycle_source = _source(CREATE_LIFECYCLE)
    source_factory_source = _source(CREATE_SOURCE_SECTION_FACTORY)
    source = _source(CREATE_SOURCE_SECTION)
    controls_source = _source(CREATE_SOURCE_CONTROLS)
    support_controls_source = _source(CREATE_SOURCE_SUPPORT_CONTROLS)
    view_model_source = _source(CREATE_VIEW_MODEL)
    view_model_sources = _source(CREATE_VIEW_MODEL_SOURCES)
    api_models_source = _source(PIPELINE_CREATION_API_MODELS)
    api_client_source = _source(API_CLIENT_CREATION)

    assert 'static let subtitleDeleteSourcePath = "/api/subtitles/delete-source"' in api_client_source
    assert "func deleteSubtitleSource(" in api_client_source
    assert "path: AppleCreateRuntimeContract.subtitleDeleteSourcePath" in api_client_source
    assert "struct SubtitleSourceDeleteRequest: Encodable, Equatable" in api_models_source
    assert "struct SubtitleSourceDeleteResponse: Decodable, Equatable" in api_models_source
    assert "func deleteSubtitleSource(" in view_model_sources
    assert "isDeletingSubtitleSource = true" in view_model_sources
    assert "client.deleteSubtitleSource(subtitlePath: trimmedPath)" in view_model_sources
    assert "subtitleSources = SubtitleSourceListResponse(" in view_model_sources
    assert "let isDeletingSubtitleSource: Bool" in source
    assert "let onDeleteSubtitleSource: (SubtitleSourceEntry) -> Void" in source
    assert "isDeletingSubtitleSource: isDeletingSubtitleSource" in source
    assert "onDeleteSubtitleSource: onDeleteSubtitleSource" in source
    assert "AppleBookCreateSubtitleSourceControls(" in source
    assert "let isDeletingSubtitleSource: Bool" in support_controls_source
    assert "let onDeleteSubtitleSource: (SubtitleSourceEntry) -> Void" in support_controls_source
    assert 'accessibilityIdentifier("createSubtitleDeleteServerSourceButton")' in support_controls_source
    assert 'accessibilityIdentifier("createSubtitleDeleteServerSourceProgress")' in support_controls_source
    assert "private var selectedSubtitleSourceEntry: SubtitleSourceEntry?" in support_controls_source
    assert "subtitleSourcePendingDelete" in view_source
    assert "confirmationDialog(" in lifecycle_source
    assert 'accessibilityIdentifier("confirmDeleteSubtitleSourceButton")' in lifecycle_source
    assert "onDeleteSubtitleSource: requestDeleteSubtitleSource" in source_factory_source


def test_narrate_epub_source_delete_is_wired_through_apple_create() -> None:
    view_source = _source(CREATE_VIEW)
    lifecycle_source = _source(CREATE_LIFECYCLE)
    source_factory_source = _source(CREATE_SOURCE_SECTION_FACTORY)
    source = _source(CREATE_SOURCE_SECTION)
    controls_source = _source(CREATE_SOURCE_CONTROLS)
    view_model_source = _source(CREATE_VIEW_MODEL)
    view_model_sources = _source(CREATE_VIEW_MODEL_SOURCES)
    api_models_source = _source(PIPELINE_CREATION_API_MODELS)
    api_client_source = _source(API_CLIENT_CREATION)

    assert "struct PipelineFileDeleteRequest: Encodable, Equatable" in api_models_source
    assert "func deletePipelineEbook(" in api_client_source
    assert 'method: "DELETE"' in api_client_source
    assert "payload: PipelineFileDeleteRequest(path: path)" in api_client_source
    assert "func deletePipelineEbook(" in view_model_sources
    assert "isDeletingPipelineEbook = true" in view_model_sources
    assert "client.deletePipelineEbook(path: trimmedPath)" in view_model_sources
    assert "pipelineFiles = PipelineFileBrowserResponse(" in view_model_sources
    assert "let isDeletingPipelineEbook: Bool" in source
    assert "let onDeletePipelineEbook: (PipelineFileEntry) -> Void" in source
    assert "isDeletingPipelineEbook: isDeletingPipelineEbook" in source
    assert "onDeletePipelineEbook: onDeletePipelineEbook" in source
    assert "let isDeletingPipelineEbook: Bool" in controls_source
    assert "let onDeletePipelineEbook: (PipelineFileEntry) -> Void" in controls_source
    assert 'accessibilityIdentifier("createNarrateDeleteServerEbookButton")' in controls_source
    assert 'accessibilityIdentifier("createNarrateDeleteServerEbookProgress")' in controls_source
    assert "private var selectedNarrateServerEbook: PipelineFileEntry?" in controls_source
    assert "pipelineEbookPendingDelete" in view_source
    assert "AppleBookCreateEbookDeleteConfirmationModifier" in lifecycle_source
    assert 'accessibilityIdentifier("confirmDeletePipelineEbookButton")' in lifecycle_source
    assert "onDeletePipelineEbook: requestDeletePipelineEbook" in source_factory_source


def test_narrate_epub_acquisition_discovery_is_wired_through_apple_create() -> None:
    view_source = _source(CREATE_VIEW)
    source_factory_source = _source(CREATE_SOURCE_SECTION_FACTORY)
    source_actions = _source(CREATE_SOURCE_ACTIONS)
    source = _source(CREATE_SOURCE_SECTION)
    source_section_source = source
    controls_source = _source(CREATE_SOURCE_CONTROLS)
    view_model_source = _source(CREATE_VIEW_MODEL)
    view_model_sources = _source(CREATE_VIEW_MODEL_SOURCES)
    api_models_source = _source(PIPELINE_CREATION_API_MODELS)
    api_client_source = _source(API_CLIENT_CREATION)
    template_factory_source = _source(CREATE_TEMPLATE_SAVE_PAYLOAD_FACTORY)
    drafts_source = _source(CREATE_DRAFTS)
    draft_actions_source = _source(CREATE_DRAFT_ACTIONS)

    assert 'static let acquisitionDiscoverPath = "/api/acquisition/discover"' in api_client_source
    assert "func discoverAcquisitionCandidates(" in api_client_source
    assert 'URLQueryItem(name: "media_kind", value: mediaKind)' in api_client_source
    assert 'URLQueryItem(name: "provider", value: provider)' in api_client_source
    assert 'provider.localizedCaseInsensitiveCompare("backend_defaults") != .orderedSame' in api_client_source
    assert 'URLQueryItem(name: "source_id", value: normalizedSourceId)' in api_client_source
    assert "try decode(AcquisitionDiscoveryResponse.self, from: data)" in api_client_source
    assert "struct AcquisitionCandidate: Decodable, Equatable, Identifiable" in api_models_source
    assert "let candidateToken: String" in api_models_source
    assert "let localPath: String?" in api_models_source
    assert "struct AcquisitionDiscoveryResponse: Decodable, Equatable" in api_models_source
    assert "let defaultProviderIds: [String: [String]]" in api_models_source
    assert "struct AcquisitionJobCreateRequest: Encodable, Equatable" in api_models_source
    assert "let candidateToken: String?" in api_models_source
    assert "let metadata: [String: JSONValue]?" in api_models_source
    assert 'case candidateToken = "candidate_token"' in api_models_source
    assert "candidateToken: String? = nil" in api_client_source
    assert "candidateToken: candidateToken?.nonEmptyValue" in api_client_source
    assert 'static let acquisitionAcquirePath = "/api/acquisition/acquire"' in api_client_source
    assert "func acquireAcquisitionCandidate(" in api_client_source
    assert "func prepareAcquisitionArtifact(" in api_client_source
    assert "static func encodedAcquisitionID(_ acquisitionId: String) -> String" in api_client_source
    assert "AppleCreateRuntimeContract.encodedAcquisitionID(artifactId)" in api_client_source
    assert "AppleCreateRuntimeContract.encodedAcquisitionID(taskId)" in api_client_source
    assert "try decode(AcquisitionArtifactResponse.self, from: data)" in api_client_source
    assert "try decode(AcquisitionPreparedArtifactResponse.self, from: data)" in api_client_source
    assert "struct AcquisitionArtifactResponse: Decodable, Equatable" in api_models_source
    assert "struct AcquisitionPreparedArtifactResponse: Decodable, Equatable" in api_models_source
    assert "@Published var ebookAcquisitionDiscovery: AcquisitionDiscoveryResponse?" in view_model_source
    assert "@Published var isLoadingEbookAcquisitionDiscovery = false" in view_model_source
    assert "@Published var isAcquiringEbookDiscoveryCandidate = false" in view_model_source
    assert "func loadEbookDiscovery(" in view_model_sources
    assert 'mediaKind: "book"' in view_model_sources
    assert "provider: String = AppleBookCreatePresentation.defaultBookDiscoveryProviderID" in view_model_sources
    assert "? AppleBookCreatePresentation.defaultBookDiscoveryProviderID" in view_model_sources
    assert "AppleBookCreatePresentation.discoveryRequestProviderID(\n            for: normalizedProvider,\n            mediaKind: \"book\"\n        )" in view_model_sources
    assert 'provider: requestProvider' in view_model_sources
    assert "sourceIds: normalizedSourceIds" in view_model_sources
    assert "func acquireEbookDiscoveryCandidate(" in view_model_sources
    assert "func prepareEbookDiscoveryCandidate(" in view_model_sources
    assert "client.acquireAcquisitionCandidate(" in view_model_sources
    assert "client.prepareAcquisitionArtifact(" in view_model_sources
    assert "AppleBookCreatePresentation.internetArchiveSourceIDs(candidate)" in source_actions
    assert 'provider: "internet_archive"' in source_actions
    assert "sourceIds: sourceIds" in source_actions

    assert "let ebookAcquisitionDiscovery: AcquisitionDiscoveryResponse?" in source
    assert "let acquisitionProviders: [AcquisitionProviderEntry]" in source
    assert "let acquisitionDefaultProviderIds: [String: [String]]" in source
    assert "let isAcquiringEbookAcquisitionCandidate: Bool" in source
    assert "let acquisitionProvidersErrorMessage: String?" in controls_source
    assert "acquisitionProviders: viewModel.acquisitionProviders" in source_factory_source
    assert "acquisitionDefaultProviderIds: viewModel.acquisitionDefaultProviderIds" in source_factory_source
    assert "acquisitionProviders: acquisitionProviders" in source
    assert "acquisitionDefaultProviderIds: acquisitionDefaultProviderIds" in source
    assert "let onSearchAcquisitionDiscovery: (String, String) -> Void" in source
    assert "let onSelectAcquisitionCandidate: (AcquisitionCandidate) -> Void" in source
    assert "ebookAcquisitionDiscovery: viewModel.ebookAcquisitionDiscovery" in source_factory_source
    assert "isAcquiringEbookAcquisitionCandidate: viewModel.isAcquiringEbookDiscoveryCandidate" in source_factory_source
    assert "onSearchAcquisitionDiscovery: searchAcquisitionDiscovery" in source_factory_source
    assert "onSelectAcquisitionCandidate: applyAcquisitionDiscoveryCandidate" in source_factory_source
    assert "func applyAcquisitionDiscoveryCandidate(_ candidate: AcquisitionCandidate)" in source_actions
    assert "viewModel.acquireEbookDiscoveryCandidate(" in source_actions
    assert "viewModel.prepareEbookDiscoveryCandidate(" in source_actions
    assert "func applyAcquisitionDiscoveryPath(_ localPath: String)" in source_actions
    assert "refreshNarrateBaseOutputIfNeeded(for: localPath, replacing: previousSourcePath)" in source_actions
    assert "clearNarrateChapterSelection()" in source_actions
    assert "func clearNarrateSourceMetadata()" in source_actions
    assert "bookMetadataExtras = [:]" in source_actions
    assert "clearNarrateSourceMetadata()" in source_actions
    presentation_source = _source(CREATE_PRESENTATION_HELPERS)
    discovery_source = _source(CREATE_DISCOVERY_PRESENTATION)
    assert "struct AppleBookCreateDiscoveryProviderOption" in discovery_source
    assert "static func bookDiscoveryProviderOptions(" in discovery_source
    assert "static func bookDiscoveryProviderOptions(" not in presentation_source
    download_station_source = _source(CREATE_DOWNLOAD_STATION_PRESENTATION)
    assert "extension AppleBookCreatePresentation" in download_station_source
    assert "static func downloadStationCompletedFiles(from job: AcquisitionJobStatusResponse?) -> [String]" in download_station_source
    assert "static func downloadStationCompletedCandidate(" in download_station_source
    assert "static func isDownloadStationHandoffCandidate(_ candidate: AcquisitionCandidate) -> Bool" in download_station_source
    assert "static func downloadStationCompletedFiles(" not in discovery_source
    assert "static func downloadStationCompletedCandidate(" not in discovery_source
    assert "static func isDownloadStationHandoffCandidate(" not in discovery_source
    assert "private static let fallbackBookDiscoveryProviders" in discovery_source
    assert 'let available: Bool' in discovery_source
    assert 'static let defaultBookDiscoveryProviderID = "backend_defaults"' in discovery_source
    assert "static func isDefaultBookDiscoveryProviderID" in discovery_source
    assert "static func discoveryRequestProviderID(for providerID: String, mediaKind: String) -> String?" in discovery_source
    assert "let normalizedMediaKind = mediaKind" in discovery_source
    assert ".trimmingCharacters(in: .whitespacesAndNewlines)\n            .lowercased()" in discovery_source
    assert 'if normalizedMediaKind == "book", isDefaultBookDiscoveryProviderID(normalizedProvider)' in discovery_source
    assert 'if normalizedMediaKind == "video", isDefaultVideoDiscoveryProviderID(normalizedProvider)' in discovery_source
    assert "return nil" in discovery_source
    assert "return normalizedProvider" in discovery_source
    assert "private static let defaultBookDiscoveryProvider = AppleBookCreateDiscoveryProviderOption(" in discovery_source
    assert 'AppleBookCreateDiscoveryProviderOption(id: "manual_downloads", label: "Manual downloads", available: true)' in discovery_source
    assert 'AppleBookCreateDiscoveryProviderOption(id: "gutenberg", label: "Gutenberg", available: true)' in discovery_source
    assert 'AppleBookCreateDiscoveryProviderOption(id: "internet_archive", label: "Internet Archive", available: true)' in discovery_source
    assert 'AppleBookCreateDiscoveryProviderOption(id: "openlibrary", label: "Open Library", available: true)' in discovery_source
    assert 'AppleBookCreateDiscoveryProviderOption(id: "zlibrary_attended", label: "Z-Library import", available: false)' in discovery_source
    book_default_body = _swift_function_body(
        discovery_source,
        "private static func defaultBookDiscoveryProviderOption(",
    )
    assert 'for: "book"' in book_default_body
    assert 'providerIDs: defaultProviderIds["book"] ?? []' in book_default_body
    assert "let availableDefaults = backendDefaults.filter { availableOptionIds.contains($0) }" in book_default_body
    assert "availableDefaults.count >= 2" in book_default_body
    assert "return defaultBookDiscoveryProvider" in book_default_body
    defaultable_body = _swift_function_body(discovery_source, "static func defaultableProviderIDs(")
    assert "let hasProviderInventory = !providers.isEmpty" in defaultable_body
    assert "guard let provider = providersByID[$0]" in defaultable_body
    assert "if hasProviderInventory" in defaultable_body
    assert "return provider.defaultEligibleMediaKinds.contains(mediaKind)" in defaultable_body
    assert 'guard mediaKind == "video" else' in defaultable_body
    assert "ForEach(discoveryProviderOptions)" in controls_source
    assert "Text(option.label).tag(option.id)" in controls_source
    assert "AppleBookCreatePresentation.bookDiscoveryProviderOptions(" in controls_source
    assert "from: acquisitionProviders,\n            defaultProviderIds: acquisitionDefaultProviderIds" in controls_source
    assert "AppleBookCreatePresentation.defaultDiscoveryProviderID(" in controls_source
    assert "defaultProviderIds: acquisitionDefaultProviderIds" in controls_source
    assert "optionIds: discoveryProviderOptions.map(\\.id)" in controls_source
    assert "availableOptionIds: discoveryProviderOptions.filter(\\.available).map(\\.id)" in controls_source
    assert "@State private var hasUserSelectedDiscoveryProvider = false" in controls_source
    assert "@State private var didApplyBackendDiscoveryDefault = false" in controls_source
    assert "@State private var lastAutomaticDiscoverySearchSignature: String?" in controls_source
    assert "private var acquisitionDiscoveryProviderBinding: Binding<String>" in controls_source
    assert "hasUserSelectedDiscoveryProvider = true" in controls_source
    assert "triggerAutomaticDiscoverySearchIfReady(providerID: providerID, force: true)" in controls_source
    assert "private func triggerAutomaticDiscoverySearchIfReady(" in controls_source
    assert "guard sourcePanel == .discovery else" in controls_source
    assert "lastAutomaticDiscoverySearchSignature != signature" in controls_source
    assert "onSearchAcquisitionDiscovery(discoveryQuery, providerID)" in controls_source
    assert "private func isDiscoveryProviderAvailable(_ providerID: String) -> Bool" in controls_source
    assert ".onChange(of: sourcePanel)" in controls_source
    assert "private func applyPreferredDiscoveryProviderIfNeeded(_ providerID: String?)" in controls_source
    assert ".onChange(of: discoveryProviderOptionsSignature)" in controls_source
    assert "private var discoveryProviderOptionsSignature: String" in controls_source
    assert "currentProviderIsKnown" in controls_source
    discovery_default_body = controls_source.split("private func applyPreferredDiscoveryProviderIfNeeded", 1)[1].split(
        "\n    }\n}",
        1,
    )[0]
    assert "!didApplyBackendDiscoveryDefault" not in discovery_default_body
    assert "acquisitionDiscoveryProvider != providerID || !currentProviderIsKnown" in discovery_default_body
    assert "let discoveryMediaKinds: [String]" in api_models_source
    assert "let defaultEligibleMediaKinds: [String]" in api_models_source
    assert "enum AppleBookCreateNarrateSourcePanel" in controls_source
    assert "case discovery" in controls_source
    assert "@Binding var sourcePanel: AppleBookCreateNarrateSourcePanel" in controls_source
    assert "@State var narrateSourcePanel = AppleBookCreateNarrateSourcePanel.server" in view_source
    assert "narrateSourcePanel: $narrateSourcePanel" in source_factory_source
    assert "@Binding var narrateSourcePanel: AppleBookCreateNarrateSourcePanel" in source_section_source
    assert "sourcePanel: $narrateSourcePanel" in source_section_source
    template_application_source = _source(CREATE_TEMPLATE_APPLICATION_ACTIONS)
    assert "narrateSourcePanel = shouldUseDiscoverySourcePanel ? .discovery : .server" in template_application_source
    assert 'accessibilityIdentifier("createNarrateSourceModePicker")' in controls_source
    assert "discoverySourceControls" in controls_source
    assert 'accessibilityIdentifier("createNarrateDiscoveryPanel")' in controls_source
    assert 'return provider.discoveryMediaKinds.contains("book")' in discovery_source
    assert 'provider.mediaKinds.contains("book")' not in discovery_source
    assert "if let discoveryMediaKinds = provider.discoveryMediaKinds" not in discovery_source
    assert "bookDiscoveryCapabilities.contains($0)" not in discovery_source
    assert "private static func bookDiscoveryProviderRank(" in discovery_source
    assert "private static func bookDiscoveryProviderLabel(" in discovery_source
    assert "private func discoveryProviderRank(" not in controls_source
    assert "private func discoveryProviderLabel(" not in controls_source
    assert ".pickerStyle(.menu)" in controls_source
    assert "createNarrateDiscoveryProviderPicker" in controls_source
    assert "private var selectedDiscoveryProvider: AcquisitionProviderEntry?" in controls_source
    assert "private var selectedDiscoveryProviderOption: AppleBookCreateDiscoveryProviderOption?" in controls_source
    assert "private var isSelectedDiscoveryProviderAvailable: Bool" in controls_source
    assert "selectedDiscoveryProviderOption?.available != false" in controls_source
    assert "selectedDiscoveryProvider?.available != false" in controls_source
    assert "selectedDiscoveryProviderUnavailableMessage" in controls_source
    assert "AppleBookCreatePresentation.bookDiscoveryProviderUnavailableMessage(" in controls_source
    assert "selectedOption: selectedDiscoveryProviderOption" in controls_source
    assert "provider.policyNotes.first" not in controls_source
    assert "provider.status.replacingOccurrences" not in controls_source
    assert "static func bookDiscoveryProviderUnavailableMessage(" in discovery_source
    assert "Direct Z-Library automation is intentionally disabled" in discovery_source
    assert "static func discoveryProviderUnavailableMessage(" in discovery_source
    assert "static func sourceFallbackAction(for provider: AcquisitionProviderEntry) -> String" in discovery_source
    assert "provider.sourceLabel?" in discovery_source
    assert 'sourceName = "the backend source root"' in discovery_source
    assert 'return "Configure \\(sourceName) or choose another discovery source."' in discovery_source
    assert "fallbackAction: sourceFallbackAction(for: provider)" in discovery_source
    assert "provider.policyNotes.first" in discovery_source
    assert "let sourceLabel: String?" in api_models_source
    assert "|| !isSelectedDiscoveryProviderAvailable" in controls_source
    assert "AppleBookCreatePresentation.bookDiscoveryCandidates(" in controls_source
    assert "providerID: acquisitionDiscoveryProvider" in controls_source
    assert "providers: acquisitionProviders" in controls_source
    assert "AppleBookCreatePresentation.discoveryPolicyNotes(from: acquisitionDiscovery)" in controls_source
    assert 'accessibilityIdentifier("createNarrateDiscoveryPolicyNote")' in controls_source
    assert "providerID: String" in discovery_source
    assert "let queriedProviders = Set(discovery?.providersQueried ?? [])" in discovery_source
    assert "isDefaultBookDiscoveryProviderID(providerID)" in discovery_source
    assert "defaultableProviderIDs(\n                   for: \"book\"" in discovery_source
    assert "AppleBookCreatePresentation.bookDiscoveryCandidateDetail(candidate)" in controls_source
    assert "AppleBookCreatePresentation.bookDiscoveryCandidateAction(candidate)" in controls_source
    assert "AppleBookCreatePresentation.canSelectBookDiscoveryCandidate(candidate)" in controls_source
    assert '$0.capabilities.contains("acquire")' in discovery_source
    assert "|| $0.capabilities.contains(\"metadata\")" in discovery_source
    assert '$0.provider == "openlibrary"' not in discovery_source.split("static func bookDiscoveryCandidates(", 1)[1].split("static func bookDiscoveryCandidateDetail", 1)[0]
    assert 'return candidate.capabilities.contains("metadata") ? "Apply metadata" : "Review"' in discovery_source
    assert "static func canSelectBookDiscoveryCandidate(_ candidate: AcquisitionCandidate)" in discovery_source
    assert "private func canSelectDiscoveryCandidate(" not in controls_source
    assert "private func discoveryCandidateDetail(" not in controls_source
    assert "private func discoveryCandidateAction(" not in controls_source
    assert "guard candidate.capabilities.contains(\"acquire\") else" in view_model_sources
    assert "applyAcquisitionDiscoveryMetadata(candidate, preparedMetadata: prepared.metadata)" in source_actions
    assert "applyAcquisitionDiscoveryMetadata(candidate, preparedMetadata: acquired.metadata)" in source_actions
    assert "preparedMetadata: [String: JSONValue]? = nil" in source_actions
    assert "AppleBookCreatePresentation.bookDiscoveryMetadataApplication(" in source_actions
    assert "@State var bookMetadataExtras = [String: JSONValue]()" in view_source
    assert "bookMetadataExtras: bookMetadataExtras" in draft_actions_source
    assert "bookMetadataExtras = metadataApplication.bookMetadataExtras" in source_actions
    assert "private func acquisitionBookMetadataExtras(" not in view_source
    assert "struct AppleBookCreateBookDiscoveryMetadataApplication: Equatable" in discovery_source
    assert "static func bookDiscoveryMetadataApplication(" in discovery_source
    assert "private static func bookDiscoveryMetadataExtras(" in discovery_source
    assert 'extras["source_provider"] = .string(candidate.provider)' in discovery_source
    assert 'extras["acquisition_provider"] = .string(candidate.provider)' in discovery_source
    assert 'extras["acquisition_candidate_id"] = .string(candidate.candidateId)' in discovery_source
    assert 'extras["rights"] = .string(candidate.rights)' in discovery_source
    assert 'extras["capabilities"] = .array(candidate.capabilities.map { .string($0) })' in discovery_source
    assert 'extras["book_title"] = .string(candidate.title)' in discovery_source
    assert 'extras["language"] = .string(language)' in discovery_source
    assert 'extras["year"] = .number(Double(year))' in discovery_source
    assert "discoveryState: makeBookDiscoveryState(" in template_factory_source
    assert 'payload["discovery_state"] = .object(discoveryState)' in template_factory_source
    assert 'state: [String: JSONValue] = [' in template_factory_source
    assert '"media_kind": .string("book")' in template_factory_source
    assert '"provider": .string(provider)' in template_factory_source
    assert 'named: "title"' in template_factory_source
    assert 'named: "rights"' in template_factory_source
    assert 'named: "language"' in template_factory_source
    assert 'named: "year"' in template_factory_source
    assert 'named: "capabilities"' in template_factory_source
    assert 'named: "candidate_id"' in template_factory_source
    assert 'named: "selected_path"' in template_factory_source
    assert "private static func firstJSONValue(" in template_factory_source
    assert "static func normalizedBookMetadataExtras(_ extras: [String: JSONValue])" in drafts_source
    assert "!isSensitiveBookMetadataExtraKey(trimmedKey)" in drafts_source
    assert "private static func isSensitiveBookMetadataExtraKey(_ key: String) -> Bool" in drafts_source
    assert "private static func stripSensitiveURLParts(_ value: String) -> String" in drafts_source
    assert "stripSensitiveURLParts(trimmed)" in drafts_source
    for marker in [
        '"apikey"',
        '"authkey"',
        '"authheader"',
        '"password"',
        '"authorization"',
        '"bearer"',
        '"cookie"',
        '"credential"',
        '"csrf"',
        '"jwt"',
        '"passkey"',
        '"privatekey"',
        '"rsskey"',
        '"secret"',
        '"sessioncookie"',
        '"sid"',
        '"token"',
    ]:
        assert marker in drafts_source
    assert 'bookDiscoveryMetadataText(metadata, keys: "book_title", "title")' in discovery_source
    assert 'bookDiscoveryMetadataText(metadata, keys: "book_cover_file", "cover_file", "cover_url")' in discovery_source
    assert "private func metadataText(" not in view_source
    assert 'metadata["cover_url"] = .string(coverFile)' in _source(CREATE_PAYLOAD_FACTORY)
    assert '"cover_url"' in _source(CREATE_PAYLOAD_FACTORY)

    for identifier in [
        "createNarrateSourceModePicker",
        "createNarrateDiscoveryPanel",
        "createNarrateDiscoveryProviderPicker",
        "createNarrateDiscoveryQueryField",
        "createNarrateDiscoverySearchButton",
        "createNarrateDiscoveryProgress",
        "createNarrateDiscoveryAcquireProgress",
        "createNarrateDiscoveryMessage",
        "createNarrateDiscoveryCandidate.",
    ]:
        assert identifier in controls_source


def test_youtube_dub_acquisition_discovery_is_wired_through_apple_create() -> None:
    view_source = _source(CREATE_VIEW)
    source_factory_source = _source(CREATE_SOURCE_SECTION_FACTORY)
    presentation_state_source = _source(CREATE_PRESENTATION_STATE)
    source_actions = _source(CREATE_SOURCE_ACTIONS)
    source = _source(CREATE_SOURCE_SECTION)
    youtube_source = _source(CREATE_YOUTUBE_SOURCE_CONTROLS)
    youtube_discovery_source = _source(CREATE_YOUTUBE_DISCOVERY_CONTROLS)
    youtube_support_source = _source(CREATE_YOUTUBE_SOURCE_SUPPORT_CONTROLS)
    view_model_source = _source(CREATE_VIEW_MODEL)
    view_model_sources = _source(CREATE_VIEW_MODEL_SOURCES)

    assert "func loadVideoDiscovery(" in view_model_sources
    assert "func loadAcquisitionProviders(" in view_model_sources
    assert "@Published var acquisitionProviders: [AcquisitionProviderEntry] = []" in view_model_source
    assert "@Published var acquisitionDefaultProviderIds: [String: [String]] = [:]" in view_model_source
    assert "acquisitionDefaultProviderIds = response.defaultProviderIds" in view_model_sources
    assert "response.defaultProviderIds ?? [:]" not in view_model_sources
    assert 'mediaKind: "video"' in view_model_sources
    assert "provider: String = AppleBookCreatePresentation.defaultVideoDiscoveryProviderID" in view_model_sources
    assert "?? AppleBookCreatePresentation.defaultVideoDiscoveryProviderID" in view_model_sources
    assert "AppleBookCreatePresentation.discoveryRequestProviderID(\n            for: normalizedProvider,\n            mediaKind: \"video\"\n        )" in view_model_sources
    assert "provider: requestProvider" in view_model_sources
    assert "@Published var youtubeAcquisitionDiscovery: AcquisitionDiscoveryResponse?" in view_model_source
    assert "@Published var isLoadingYoutubeAcquisitionDiscovery = false" in view_model_source
    assert "@Published var isPreparingYoutubeAcquisitionCandidate = false" in view_model_source
    assert "let acquisitionProviders: [AcquisitionProviderEntry]" in source
    assert "let acquisitionDefaultProviderIds: [String: [String]]" in source
    assert "let youtubeAcquisitionDiscovery: AcquisitionDiscoveryResponse?" in source
    assert "let youtubeDiscoveryState: [String: JSONValue]?" in source
    assert "let isPreparingYoutubeAcquisitionCandidate: Bool" in source
    assert "let acquisitionProvidersErrorMessage: String?" in source
    assert "let youtubeSearchUnavailableMessage: String?" in source
    assert "let isYoutubeSearchAvailable: Bool" in source
    assert "let onSearchYoutubeAcquisitionDiscovery: (String, String) -> Void" in source
    assert "let onSelectYoutubeAcquisitionCandidate: (AcquisitionCandidate, String, String) -> Void" in source
    discovery_source = _source(CREATE_DISCOVERY_PRESENTATION)
    download_station_source = _source(CREATE_DOWNLOAD_STATION_PRESENTATION)
    video_discovery_source = _source(CREATE_VIDEO_DISCOVERY_PRESENTATION)
    assert "struct AppleBookCreateVideoDiscoveryAvailability" in video_discovery_source
    assert "static func youtubeVideoDiscoveryAvailability(" in video_discovery_source
    assert 'providers.first { $0.id == "youtube_search" }' in video_discovery_source
    assert 'providers.first { $0.id == "download_station" }' in video_discovery_source
    assert "let hasProviderInventory = !providers.isEmpty" in video_discovery_source
    assert "isYoutubeSearchAvailable: youtubeSearchProvider?.available ?? !hasProviderInventory" in video_discovery_source
    assert "struct AppleBookCreateVideoDiscoveryAvailability" not in discovery_source
    assert "static func youtubeVideoDiscoveryAvailability(" not in discovery_source
    assert "youtubeAcquisitionDiscovery: viewModel.youtubeAcquisitionDiscovery" in source_factory_source
    assert "youtubeDiscoveryState: youtubeDiscoveryState" in source_factory_source
    assert "acquisitionProviders: viewModel.acquisitionProviders" in source_factory_source
    assert "acquisitionDefaultProviderIds: viewModel.acquisitionDefaultProviderIds" in source_factory_source
    assert "isPreparingYoutubeAcquisitionCandidate: viewModel.isPreparingYoutubeAcquisitionCandidate" in source_factory_source
    assert "youtubeSearchUnavailableMessage: videoDiscoveryAvailability.youtubeSearchUnavailableMessage" in source_factory_source
    assert "isYoutubeSearchAvailable: videoDiscoveryAvailability.isYoutubeSearchAvailable" in source_factory_source
    assert "downloadStationUnavailableMessage: videoDiscoveryAvailability.downloadStationUnavailableMessage" in source_factory_source
    assert "isDownloadStationAvailable: videoDiscoveryAvailability.isDownloadStationAvailable" in source_factory_source
    assert "var videoDiscoveryAvailability: AppleBookCreateVideoDiscoveryAvailability" in presentation_state_source
    assert "private var videoDiscoveryAvailability: AppleBookCreateVideoDiscoveryAvailability" not in view_source
    assert "candidateToken: candidateToken" in source_actions
    assert "candidateToken: trimmedCandidateToken" in view_model_sources
    assert "func prepareVideoDiscoveryCandidate(" in view_model_sources
    assert "isPreparingYoutubeAcquisitionCandidate = true" in view_model_sources
    assert "client.prepareAcquisitionArtifact(" in view_model_sources
    assert "downloadStationCandidate?.candidateToken" in youtube_support_source
    assert 'accessibilityIdentifier("createYoutubeDownloadStationCandidate")' in youtube_support_source
    assert "AppleBookCreatePresentation.isDownloadStationHandoffCandidate(candidate)" in youtube_discovery_source
    assert "let discovery = await viewModel.loadVideoDiscovery(" in source_actions
    assert "static func downloadStationCompletedFiles(from job: AcquisitionJobStatusResponse?) -> [String]" in download_station_source
    assert "static func downloadStationCompletedCandidate(" in download_station_source
    assert "private static func downloadStationCompletedFileHints(" in download_station_source
    assert "var hints = normalizedDownloadStationMetadataStrings(job.completedFiles)" in download_station_source
    assert 'for key in ["completed_file", "completed_path", "local_path", "filename"]' in download_station_source
    assert 'for key in ["completed_files", "completed_paths", "files"]' in download_station_source
    assert 'metadata["completed_file"] ?? metadata["completed_path"] ?? metadata["local_path"]' in download_station_source
    assert "static func downloadStationCompletedFiles(" not in discovery_source
    assert "static func downloadStationCompletedCandidate(" not in discovery_source
    assert "AppleBookCreatePresentation.downloadStationCompletedFiles(from: job)" in view_model_sources
    assert "Completed: \\(completedFiles.joined(separator: \", \"))." in view_model_sources
    assert "AppleBookCreatePresentation.downloadStationCompletedFiles(from: downloadStationJob)" in youtube_support_source
    assert "AppleBookCreatePresentation.downloadStationCompletedCandidate(" in source_actions
    assert "private func downloadStationCompletedCandidate(" not in view_source
    assert "private static func downloadStationCandidateNameSet(_ candidate: AcquisitionCandidate) -> Set<String>" in download_station_source
    assert "private static func downloadStationNameKeys(for value: String) -> [String]" in download_station_source
    assert "private static func downloadStationLastPathComponent(_ value: String) -> String" in download_station_source
    assert "private static func downloadStationFileStem(_ filename: String) -> String" in download_station_source
    assert "onSelectYoutubeAcquisitionCandidate(candidate, videoDiscoveryQuery, videoDiscoveryProvider)" in youtube_discovery_source
    assert "private var youtubeSearchProvider" not in view_source
    assert "private var downloadStationProvider" not in view_source
    assert "loadAcquisitionProviders(using: appState" in view_source
    assert "onSearchYoutubeAcquisitionDiscovery: searchYoutubeAcquisitionDiscovery" in source_factory_source
    assert "onSelectYoutubeAcquisitionCandidate: applyYoutubeAcquisitionDiscoveryCandidate" in source_factory_source
    assert "func applyYoutubeAcquisitionDiscoveryCandidate(" in source_actions
    assert "_ candidate: AcquisitionCandidate," in source_actions
    assert "query: String? = nil," in source_actions
    assert "provider: String? = nil" in source_actions
    assert "AppleBookCreatePresentation.isYoutubeMetadataVideoDiscoveryProviderID(candidate.provider)" in source_actions
    assert "AppleBookCreatePresentation.youtubeMetadataSourceURL(for: candidate)" in source_actions
    assert "lookupYoutubeVideoMetadata(" in source_actions
    assert "viewModel.prepareVideoDiscoveryCandidate(" in source_actions
    assert "applyPreparedVideoDiscoveryCandidate(prepared, source: candidate, query: query, provider: provider)" in source_actions
    assert "private func applyPreparedVideoDiscoveryCandidate(" in source_actions
    assert "selectedProvider: provider" in source_actions
    assert "query: query" in source_actions
    assert "preparedMetadata: prepared.metadata" in source_actions
    assert "preparedMetadata: [String: JSONValue]? = nil" in video_discovery_source
    assert '?? candidate.metadata?["source_provider"]?.stringValue?' in video_discovery_source
    assert 'state["acquisition_provider"] = .string(acquisitionProvider)' in video_discovery_source
    assert '?? candidate.metadata?["acquisition_provider"]?.stringValue?' in video_discovery_source
    assert 'state["acquisition_candidate_id"] = .string(acquisitionCandidateID)' in video_discovery_source
    assert '?? candidate.metadata?["acquisition_candidate_id"]?.stringValue?' in video_discovery_source
    assert "prepared.videoPath?.trimmingCharacters" in source_actions
    assert "prepared.subtitlePath?.trimmingCharacters" in source_actions
    assert "prepared.subtitles.first?.path.trimmingCharacters" in source_actions
    assert "handleYoutubeVideoPathChange(videoPath)" in source_actions

    assert "let acquisitionDiscovery: AcquisitionDiscoveryResponse?" in youtube_source
    assert "let videoDiscoveryState: [String: JSONValue]?" in youtube_source
    assert "let acquisitionProviders: [AcquisitionProviderEntry]" in youtube_source
    assert "let acquisitionDefaultProviderIds: [String: [String]]" in youtube_source
    assert "let isLoadingAcquisitionDiscovery: Bool" in youtube_source
    assert "let isPreparingAcquisitionCandidate: Bool" in youtube_source
    assert "let isYoutubeSearchAvailable: Bool" in youtube_source
    assert "let youtubeSearchUnavailableMessage: String?" in youtube_source
    assert "let onSearchYoutubeAcquisitionDiscovery: (String, String) -> Void" in youtube_source
    assert "let onSelectYoutubeAcquisitionCandidate: (AcquisitionCandidate, String, String) -> Void" in youtube_source
    assert "videoDiscoveryProvider" in youtube_source
    assert "@State private var videoDiscoveryProvider = AppleBookCreatePresentation.defaultVideoDiscoveryProviderID" in youtube_source
    presentation_source = _source(CREATE_PRESENTATION_HELPERS)
    assert "struct AppleBookCreateVideoDiscoveryProviderOption" in video_discovery_source
    assert "struct AppleBookCreateVideoDiscoveryProviderOption" not in discovery_source
    assert "let defaultEligibleMediaKinds: [String]" in _source(PIPELINE_CREATION_API_MODELS)
    assert "static func videoDiscoveryProviderOptions(" in video_discovery_source
    assert "defaultProviderIds: [String: [String]] = [:]" in video_discovery_source
    assert "defaultVideoDiscoveryProviderID" in video_discovery_source
    assert "isDefaultVideoDiscoveryProviderID" in video_discovery_source
    assert "static func defaultDiscoveryProviderID(" in discovery_source
    assert "availableOptionIds: [String]? = nil" in discovery_source
    assert "let availableOptionIdSet = Set(availableOptionIds ?? optionIds)" in discovery_source
    assert 'if mediaKind == "video", optionIdSet.contains(defaultVideoDiscoveryProviderID)' in discovery_source
    assert "let preferredOptionIdSet = availableOptionIdSet.isEmpty ? optionIdSet : availableOptionIdSet" in discovery_source
    assert "defaultableProviderIDs(" in discovery_source
    assert "explicitOnlyDefaultVideoDiscoveryProviderIDs" in discovery_source
    assert '"youtube_url"' in discovery_source
    assert "static func videoDiscoveryProviderOptions(" not in presentation_source
    assert "private static let fallbackVideoDiscoveryProviders" in video_discovery_source
    assert 'AppleBookCreateVideoDiscoveryProviderOption(id: "nas_video", label: "NAS videos", available: true)' in video_discovery_source
    assert 'AppleBookCreateVideoDiscoveryProviderOption(id: "manual_downloads", label: "Manual downloads", available: true)' in video_discovery_source
    assert 'AppleBookCreateVideoDiscoveryProviderOption(id: "youtube_url", label: "YouTube URL", available: true)' in video_discovery_source
    assert 'AppleBookCreateVideoDiscoveryProviderOption(id: "youtube_search", label: "YouTube search", available: true)' in video_discovery_source
    assert 'AppleBookCreateVideoDiscoveryProviderOption(id: "newznab_torznab", label: "Indexers", available: true)' in video_discovery_source
    assert 'label: "Default sources"' in video_discovery_source
    assert "ForEach(videoDiscoveryProviderOptions)" in youtube_discovery_source
    assert "AppleBookCreatePresentation.videoDiscoveryProviderOptions(" in youtube_source
    assert "from: acquisitionProviders" in youtube_source
    assert "defaultProviderIds: acquisitionDefaultProviderIds" in youtube_source
    assert "AppleBookCreatePresentation.defaultDiscoveryProviderID(" in youtube_source
    assert "defaultProviderIds: acquisitionDefaultProviderIds" in youtube_source
    assert "optionIds: videoDiscoveryProviderOptions.map(\\.id)" in youtube_source
    assert "availableOptionIds: videoDiscoveryProviderOptions.filter(\\.available).map(\\.id)" in youtube_source
    assert "providers: acquisitionProviders" in youtube_source
    assert "@State private var hasUserSelectedVideoDiscoveryProvider = false" in youtube_source
    assert "@State private var didApplyBackendVideoDiscoveryDefault = false" in youtube_source
    assert "@State private var appliedVideoDiscoveryStateSignature = \"\"" in youtube_source
    assert "applyVideoDiscoveryStateIfNeeded()" in youtube_source
    assert ".onChange(of: videoDiscoveryStateSignature)" in youtube_source
    assert "private var videoDiscoveryStateSignature: String" in youtube_source
    assert 'videoDiscoveryStateText("selected_provider")' in youtube_source
    assert 'videoDiscoveryStateText("query")' in youtube_source
    assert "private func applyVideoDiscoveryStateIfNeeded()" in youtube_source
    assert "videoDiscoveryProvider = provider" in youtube_source
    assert "videoDiscoveryQuery = query" in youtube_source
    assert "private func videoDiscoveryStateText(_ key: String) -> String?" in youtube_source
    assert "private var videoDiscoveryProviderBinding: Binding<String>" in youtube_source
    assert "hasUserSelectedVideoDiscoveryProvider = true" in youtube_source
    assert "private func applyPreferredVideoDiscoveryProviderIfNeeded(_ providerID: String?)" in youtube_source
    assert ".onChange(of: videoDiscoveryProviderOptionsSignature)" in youtube_source
    assert "private var videoDiscoveryProviderOptionsSignature: String" in youtube_source
    assert "currentProviderIsKnown" in youtube_source
    video_default_body = youtube_source.split("private func applyPreferredVideoDiscoveryProviderIfNeeded", 1)[1].split(
        "\n    private var selectedYoutubeVideo",
        1,
    )[0]
    assert "!didApplyBackendVideoDiscoveryDefault" not in video_default_body
    assert "videoDiscoveryProvider != providerID || !currentProviderIsKnown" in video_default_body
    assert "provider.mediaKinds.contains(\"video\")" not in video_discovery_source
    assert 'return provider.discoveryMediaKinds.contains("video")' in video_discovery_source
    assert "if let discoveryMediaKinds = provider.discoveryMediaKinds" not in video_discovery_source
    assert "videoDiscoveryCapabilities.contains($0)" not in video_discovery_source
    assert "private static func videoDiscoveryProviderRank(" in video_discovery_source
    assert "private static func videoDiscoveryProviderLabel(" in video_discovery_source
    assert "static func videoDiscoveryProviderFallbackLabel(for providerID: String)" in video_discovery_source
    assert "private func videoDiscoveryProviderRank(" not in youtube_source
    assert "private func videoDiscoveryProviderLabel(" not in youtube_source
    assert "private func fallbackVideoDiscoveryProviderLabel(" not in youtube_source
    assert "selectedVideoDiscoveryProvider" in youtube_source
    assert "isSelectedVideoDiscoveryProviderAvailable" in youtube_source
    assert "selectedVideoDiscoveryProviderUnavailableMessage" in youtube_source
    assert "!AppleBookCreatePresentation.isDefaultVideoDiscoveryProviderID(videoDiscoveryProvider)" in youtube_source
    assert "if !acquisitionProviders.isEmpty, selectedVideoDiscoveryProvider == nil" in youtube_source
    assert "selectedVideoDiscoveryProviderLabel" in youtube_source
    assert "AppleBookCreatePresentation.videoDiscoveryProviderFallbackLabel(for: videoDiscoveryProvider)" in youtube_source
    assert "is unavailable on this backend. Choose another discovery source." in youtube_source
    assert "AppleBookCreatePresentation.videoDiscoveryProviderUnavailableMessage(" in youtube_source
    assert "provider.policyNotes.first" not in youtube_source
    assert "provider.status.replacingOccurrences" not in youtube_source
    assert "static func videoDiscoveryProviderUnavailableMessage(" in video_discovery_source
    assert 'if provider.id == "youtube_search"' in video_discovery_source
    assert 'if provider.id == "newznab_torznab"' in video_discovery_source
    assert "|| !isSelectedVideoDiscoveryProviderAvailable" in youtube_discovery_source
    assert "AppleBookCreatePresentation.videoDiscoveryCandidates(" in youtube_source
    assert "providers: acquisitionProviders" in youtube_source
    assert "AppleBookCreatePresentation.discoveryPolicyNotes(from: acquisitionDiscovery)" in youtube_source
    assert 'accessibilityIdentifier("createYoutubeDiscoveryPolicyNote")' in youtube_discovery_source
    assert "AppleBookCreatePresentation.videoDiscoveryQueryPlaceholder(providerID: videoDiscoveryProvider)" in youtube_source
    assert "AppleBookCreatePresentation.noVideoDiscoveryCandidatesMessage(providerID: videoDiscoveryProvider)" in youtube_source
    assert "AppleBookCreatePresentation.youtubeVideoLabel(video)" in youtube_source
    assert "AppleBookCreatePresentation.youtubeSubtitleLabel(subtitle)" in youtube_source
    assert "AppleBookCreatePresentation.filenameFromPath" in youtube_support_source
    assert "AppleBookCreatePresentation.videoDiscoveryCandidateDetail(candidate)" in youtube_discovery_source
    assert 'accessibilityIdentifier("createYoutubeDiscoveryPrepareProgress")' in youtube_discovery_source
    assert ".disabled(isPreparingAcquisitionCandidate)" in youtube_discovery_source
    assert "static func videoDiscoveryCandidates(" in video_discovery_source
    assert "static func videoDiscoveryCandidates(" not in discovery_source
    video_candidates_body = video_discovery_source.split("static func videoDiscoveryCandidates(", 1)[1].split(
        "\n    static func videoDiscoveryStatePayload",
        1,
    )[0]
    assert "defaultableProviderIDs(" in video_candidates_body
    assert "providers: providers" in video_candidates_body
    assert "isDefaultVideoDiscoveryProviderID(providerID)" in video_candidates_body
    assert "static func isYoutubeMetadataVideoDiscoveryProviderID(" in video_discovery_source
    assert "static func youtubeMetadataSourceURL(for candidate: AcquisitionCandidate)" in video_discovery_source
    assert 'normalized == "youtube_search" || normalized == "youtube_url"' in video_discovery_source
    assert "static func videoDiscoveryQueryPlaceholder(" in video_discovery_source
    assert "static func noVideoDiscoveryCandidatesMessage(" in video_discovery_source
    assert "No default video sources matched this discovery search." in video_discovery_source
    assert "No YouTube URL metadata matched this discovery search." in video_discovery_source
    assert "static func youtubeVideoLabel(" in video_discovery_source
    assert "static func youtubeSubtitleLabel(" in video_discovery_source
    assert "static func filenameFromPath(" in video_discovery_source
    assert "static func videoDiscoveryCandidateDetail(" in video_discovery_source
    assert "static func isDownloadStationHandoffCandidate(_ candidate: AcquisitionCandidate) -> Bool" in download_station_source
    assert 'candidate.metadata?["handoff_provider"]?.stringValue?' in download_station_source
    assert '.localizedCaseInsensitiveCompare("download_station") == .orderedSame' in download_station_source
    assert 'candidate.metadata?["has_download_url"]?.stringValue?' in download_station_source
    assert '.localizedCaseInsensitiveCompare("true") == .orderedSame' in download_station_source
    assert "Download Station handoff" in video_discovery_source
    assert "static func videoDiscoveryCandidateDetail(" not in discovery_source
    assert "private func youtubeVideoLabel(" not in youtube_source
    assert "private func youtubeSubtitleLabel(" not in youtube_source
    assert "private func filenameFromPath(" not in youtube_source
    assert "private func videoDiscoveryCandidateDetail(" not in youtube_source
    for identifier in [
        "createYoutubeDiscoveryControls",
        "createYoutubeDiscoveryProviderPicker",
        "createYoutubeDiscoveryQueryField",
        "createYoutubeDiscoverySearchButton",
        "createYoutubeDiscoveryProgress",
        "createYoutubeDiscoveryMessage",
        "createYoutubeDiscoveryCandidate.",
    ]:
        assert identifier in youtube_discovery_source


def test_ipad_split_view_keeps_create_picker_in_detail_panel() -> None:
    source = _source(LIBRARY_SHELL)

    assert "@State private var createMode = AppleCreateMode.generatedBook" in source
    assert "createModeSidebarList" not in source
    assert 'Label("Create", systemImage: "square.and.pencil")' in source

    call_positions = [
        match.start()
        for match in re.finditer(r"AppleBookCreateView\(", source)
    ]
    assert len(call_positions) == 2
    calls = [_call_arguments(source, position) for position in call_positions]

    detail_call = next(call for call in calls if "sectionPicker: nil" in call)
    compact_call = next(call for call in calls if "sectionPicker: sectionPickerForHeader" in call)

    assert "creationMode: $createMode" in detail_call
    assert "showsInlineJobTypePicker: true" in detail_call
    assert "creationMode: $createMode" in compact_call
    assert "showsInlineJobTypePicker: true" in compact_call


def test_ipad_create_detail_uses_two_column_job_settings_layout() -> None:
    source = _source(CREATE_VIEW)
    source_factory_source = _source(CREATE_SOURCE_SECTION_FACTORY)
    layout_source = _source(CREATE_LAYOUT)
    settings_content_source = _source(CREATE_SETTINGS_CONTENT)
    basic_source = _source(CREATE_BASIC_SECTIONS)
    controls_source = _source(CREATE_SOURCE_CONTROLS)
    support_controls_source = _source(CREATE_SOURCE_SUPPORT_CONTROLS)
    view_model_source = _source(CREATE_VIEW_MODEL)
    view_model_sources = _source(CREATE_VIEW_MODEL_SOURCES)
    project = _source(XCODE_PROJECT)

    assert "usesRegularWidthCreateLayout" in source
    assert "AppleBookCreateContainer(" in source
    assert "AppleBookCreateRegularWidthLayout(" not in source
    assert "AppleBookCreateList(" not in source
    assert 'accessibilityIdentifier: "appleBookCreateSingleColumnList"' not in source
    assert "private static let setupPaneMinWidth: CGFloat = 220" not in source
    assert "private func createSettingsForm<Content: View>" not in source
    assert "struct AppleBookCreateContainer" in layout_source
    assert "struct AppleBookCreateRegularWidthLayout" in layout_source
    assert "struct AppleBookCreateList" in layout_source
    assert "struct AppleBookCreateSettingsForm" in layout_source
    assert "AppleBookCreateRegularWidthLayout(" in layout_source
    assert "AppleBookCreateList(" in layout_source
    assert 'accessibilityIdentifier: "appleBookCreateSingleColumnList"' in layout_source
    assert "private enum AppleBookCreateLayoutMetrics" in layout_source
    assert 'accessibilityIdentifier: "appleBookCreateSetupPane"' in layout_source
    assert 'accessibilityIdentifier: "appleBookCreateSettingsPane"' in layout_source
    assert "static let setupPaneMinWidth: CGFloat = 220" in layout_source
    assert "static let setupPaneIdealWidth: CGFloat = 260" in layout_source
    assert "static let setupPaneMaxWidth: CGFloat = 280" in layout_source
    assert "static let settingsPaneMinWidth: CGFloat = 480" in layout_source
    assert "static let settingsPaneIdealWidth: CGFloat = 680" in layout_source
    assert "minWidth: AppleBookCreateLayoutMetrics.setupPaneMinWidth" in layout_source
    assert "idealWidth: AppleBookCreateLayoutMetrics.setupPaneIdealWidth" in layout_source
    assert "maxWidth: AppleBookCreateLayoutMetrics.setupPaneMaxWidth" in layout_source
    assert ".layoutPriority(0)" in layout_source
    assert "minWidth: AppleBookCreateLayoutMetrics.settingsPaneMinWidth" in layout_source
    assert "idealWidth: AppleBookCreateLayoutMetrics.settingsPaneIdealWidth" in layout_source
    assert ".layoutPriority(2)" in layout_source
    assert "Form {\n            content()\n        }" in layout_source
    assert "AppleBookCreateLayout.swift in Sources" in project
    assert project.count("AppleBookCreateLayout.swift in Sources") == 4
    assert "AppleBookCreateSettingsContent.swift in Sources" in project
    assert project.count("AppleBookCreateSettingsContent.swift in Sources") == 4
    assert "private var createSetupSections: some View" in source
    assert "private var createSettingsSections: some View" in source
    assert "private var jobTypeSection: some View" in source
    assert "private var jobSettingsSection: some View" in source
    assert "AppleBookCreateSettingsContent(" in source
    assert "struct AppleBookCreateSettingsContent<" in settings_content_source
    assert "let creationMode: AppleCreateMode" in settings_content_source

    setup_sections = re.search(
        r"private var createSetupSections: some View \{(?P<body>.*?)\n    \}",
        source,
        re.DOTALL,
    )
    settings_sections = re.search(
        r"private var createSettingsSections: some View \{(?P<body>.*?)\n    \}",
        source,
        re.DOTALL,
    )

    assert setup_sections
    assert settings_sections
    assert "sourceSection" in setup_sections.group("body")
    assert "AppleBookCreateSourceSection(" in source_factory_source
    assert "AppleBookCreateSourceSection(" not in source
    assert "promptSection" not in setup_sections.group("body")
    assert "metadataSection" not in setup_sections.group("body")
    assert "jobTypeSection" not in setup_sections.group("body")
    assert "jobSettingsSection" not in setup_sections.group("body")
    assert "AppleBookCreateSettingsContent(" in settings_sections.group("body")
    assert "jobTypeSection: { jobTypeSection }" in settings_sections.group("body")
    assert "promptSection: { promptSection }" in settings_sections.group("body")
    assert "metadataSection: { metadataSection }" in settings_sections.group("body")
    assert "jobSettingsSection: { jobSettingsSection }" in settings_sections.group("body")
    assert "narrationSection: { narrationSection }" in settings_sections.group("body")
    assert "outputSection: { outputSection }" in settings_sections.group("body")
    assert "submitSection: { submitSection }" in settings_sections.group("body")

    settings_content_body = _swift_struct_body(settings_content_source, "AppleBookCreateSettingsContent")
    assert "jobTypeSection()" in settings_content_body
    assert "templateSection()" in settings_content_body
    assert "if creationMode == .generatedBook" in settings_content_body
    assert "promptSection()" in settings_content_body
    assert "if creationMode == .generatedBook || creationMode == .narrateEbook" in settings_content_body
    assert "metadataSection()" in settings_content_body
    assert "jobSettingsSection()" in settings_content_body
    assert "narrationSection()" in settings_content_body
    assert "if creationMode == .subtitleJob" in settings_content_body
    assert "subtitleMetadataSection()" in settings_content_body
    assert "if creationMode == .youtubeDub" in settings_content_body
    assert "youtubeMetadataSection()" in settings_content_body
    assert "outputSection()" in settings_content_body
    assert "statusSection()" in settings_content_body
    assert "submitSection()" in settings_content_body
    assert 'Section("Job Type")' in basic_source
    assert 'Picker("Job type", selection: $creationMode)' in basic_source
    assert '.accessibilityIdentifier("createJobTypePicker")' in basic_source

    assert "AppleBookCreatePromptSection(" in source
    assert "AppleBookCreateJobSettingsSection(" in source
    assert "sentenceCountControl" in basic_source
    assert "narrateChapterSettingsControls" in basic_source
    assert "AppleBookCreateNarrateChapterRangeControls(" in basic_source
    assert 'accessibilityIdentifier("createNarrateOutputPathField")' in basic_source
    assert 'accessibilityIdentifier("createNarrateStartSentenceField")' in basic_source
    assert 'accessibilityIdentifier("createNarrateEndSentenceField")' in basic_source
    assert "showsNarrateRangeControls: false" in source_factory_source

    assert "private var narrateChapterSettingsControls: some View" in basic_source
    assert "AppleBookCreateNarrateChapterRangeControls(" in controls_source
    assert "struct AppleBookCreateNarrateChapterRangeControls: View" in support_controls_source
    assert "Button(action: onLoadNarrateChapters)" in support_controls_source
    assert 'accessibilityIdentifier("createNarrateLoadChaptersButton")' in support_controls_source
    assert "private var hasNarrateSource: Bool" in support_controls_source
    assert "private var isLoadChaptersDisabled: Bool" in support_controls_source
    assert 'Text("Choose an EPUB source before loading chapters.")' in support_controls_source
    assert 'Text("No chapter data loaded.")' in support_controls_source
    assert 'accessibilityIdentifier("createNarrateChaptersMessage")' in support_controls_source
    assert 'accessibilityIdentifier("createNarrateStartChapterPicker")' in support_controls_source
    assert 'accessibilityIdentifier("createNarrateEndChapterPicker")' in support_controls_source
    assert 'Text("Same as start").tag("")' in support_controls_source
    assert ".disabled(selectedNarrateStartChapterID.isEmpty)" in support_controls_source
    assert 'accessibilityIdentifier("createNarrateChapterRangeSummary")' in support_controls_source
    assert "applyNarrateChapterRangeSelection" in support_controls_source
    assert "private static func shouldSkipNarrateChapterLookup(for inputFile: String) -> Bool" in view_model_sources
    assert "Generated sources use manual sentence ranges; chapter loading is skipped." in view_model_sources
    assert 'normalized.hasPrefix("runtime/generated/")' in view_model_sources
    assert "client.fetchBookContentIndex(inputFile: trimmedInput)" in view_model_sources


def test_apple_create_prefers_latest_server_epub_for_narration_source() -> None:
    source = _source(CREATE_SOURCE_SELECTION)
    source_factory_source = _source(CREATE_SOURCE_SECTION_FACTORY)
    controls_source = _source(CREATE_SOURCE_CONTROLS)
    support_controls_source = _source(CREATE_SOURCE_SUPPORT_CONTROLS)
    basic_source = _source(CREATE_BASIC_SECTIONS)
    view_source = _source(CREATE_VIEW)

    assert "static func pipelineEbookEntries(from files: PipelineFileBrowserResponse?) -> [PipelineFileEntry]" in source
    assert "static func preferredPipelineEbook(from files: PipelineFileBrowserResponse?) -> PipelineFileEntry?" in source
    assert "static func selectedPipelineEbook(" in source
    assert "static func pipelineEbookPickerLabel(_ entry: PipelineFileEntry) -> String" in source
    assert "static func pipelineEbookDetailLabel(_ entry: PipelineFileEntry) -> String" in source
    assert "private static func pickerPathContext(path: String, title: String) -> String?" in source
    assert "pickerMetadataParts(" in source
    assert "formatPickerSize(" in source
    assert "formatPickerModifiedDate(" in source
    assert 'joined(separator: " · ")' in source
    assert "AppleBookCreatePresentation.pipelineEbookPickerLabel(entry)" in controls_source
    assert "AppleBookCreatePresentation.pipelineEbookDetailLabel(selectedSourceEntry)" in support_controls_source
    assert "AppleBookCreatePresentation.pipelineEbookEntries(from: pipelineFiles)" in controls_source
    assert "private var serverEbookPicker: some View" in controls_source
    assert ".disabled(isLoadingPipelineFiles)" in controls_source
    assert ".disabled(narrateServerEbooks.isEmpty || isLoadingPipelineFiles)" not in controls_source
    assert "private var shouldShowServerEbooksSummary: Bool" in controls_source
    assert "private var serverEbooksSummaryMessage: String" in controls_source
    assert 'accessibilityIdentifier("createNarrateServerEbooksSummary")' in controls_source
    assert 'accessibilityIdentifier("createNarrateSelectedEbookDetail")' in support_controls_source
    assert "let selectedSourceEntry: PipelineFileEntry?" in support_controls_source
    assert "selectedSourceEntry: selectedNarrateServerEbook" in controls_source
    assert "AppleBookCreatePresentation.selectedPipelineEbook(" in controls_source
    assert "let selectedNarrateSourceEntry: PipelineFileEntry?" in basic_source
    assert "selectedSourceEntry: selectedNarrateSourceEntry" in basic_source
    assert "selectedNarrateSourceEntry: selectedNarrateServerEbook" in view_source
    assert "private var selectedNarrateServerEbook: PipelineFileEntry?" in view_source
    assert "AppleBookCreatePresentation.selectedPipelineEbook(" in view_source
    assert "sortedPipelineEbookEntries(files?.ebooks.filter { isPipelineEbookEntry($0) } ?? [])" in source
    assert "let ebooks = pipelineEbookEntries(from: files)" in source
    assert "normalizedSourceText(entry.type ?? \"\").lowercased()" in source
    assert 'guard type != "directory" else' in source
    assert "guard !path.isEmpty else" in source
    assert "private static func isEpubCandidate(name: String, path: String) -> Bool" in source
    assert "name.hasSuffix(\".epub\") || path.hasSuffix(\".epub\")" in source
    assert "return type.isEmpty" in source
    assert "private static func sortedPipelineEbookEntries(_ entries: [PipelineFileEntry]) -> [PipelineFileEntry]" in source
    assert "files?.ebooks.filter({ $0.type == \"file\" })" not in source
    assert "pipelineFiles?.ebooks.filter { $0.type == \"file\" }" not in controls_source
    assert "parseSourceModifiedDate(left.modifiedAt)" in source
    assert "parseSourceModifiedDate(right.modifiedAt)" in source
    assert "return leftDate > rightDate" in source
    assert "left.path.localizedStandardCompare(right.path)" in source
    assert "test-agatha-poirot-30sentences.epub" not in source


def test_apple_create_subtitle_server_sources_match_web_ass_behavior() -> None:
    source = _source(CREATE_SOURCE_SELECTION)

    assert '["ass", "srt", "vtt"]' in source
    assert '["srt", "vtt"]' in source
    assert "subtitleJobSources(from: response)" in source
    assert "let preferred = candidates.filter" in source
    assert "AppleBookCreateSourceSelectionConstants.subtitleJobPreferredDefaultFormats" in source
    assert ".contains(normalizedSourceText($0.format).lowercased())" in source
    assert "let pool = preferred.isEmpty ? candidates : preferred" in source
    assert "return pool.sorted" in source
    assert "parseSourceModifiedDate(left.modifiedAt)" in source
    assert "parseSourceModifiedDate(right.modifiedAt)" in source
    assert "return leftDate > rightDate" in source


def test_apple_create_youtube_default_selection_matches_readiness_preflight() -> None:
    source = _source(CREATE_SOURCE_SELECTION)

    assert '["ass", "srt", "vtt", "sub"]' in source
    assert "static func playableYoutubeSubtitles(for video: YoutubeNasVideoEntry?)" in source
    assert "normalizedSourceText($0.format).lowercased()" in source
    assert "static func preferredYoutubeSubtitle(for video: YoutubeNasVideoEntry?)" in source
    assert "guard !candidates.isEmpty else" in source
    assert "normalizedSourceText(subtitle.language ?? \"\").lowercased().hasPrefix(\"en\")" in source
    assert "} ?? candidates[0]" in source
    assert "static func preferredYoutubeSelection(from library: YoutubeNasLibraryResponse?)" in source
    assert "let videos = sortedYoutubeVideosForDefaultSelection(library?.videos ?? [])" in source
    assert "let video = videos.first { !playableYoutubeSubtitles(for: $0).isEmpty } ?? videos[0]" in source
    assert "return AppleYoutubeSourceSelection(video: video, subtitle: preferredYoutubeSubtitle(for: video))" in source
    assert "private static func sortedYoutubeVideosForDefaultSelection(" in source
    assert "parseSourceModifiedDate(left.modifiedAt)" in source
    assert "parseSourceModifiedDate(right.modifiedAt)" in source
    assert "return leftDate > rightDate" in source
    assert "left.path.localizedStandardCompare(right.path)" in source


def test_generated_book_create_exposes_source_context_fields() -> None:
    source = _source(CREATE_VIEW)
    basic_source = _source(CREATE_BASIC_SECTIONS)
    payload_factory_source = _source(CREATE_PAYLOAD_FACTORY)
    draft_source = _source(CREATE_MODELS)
    draft_actions_source = _source(CREATE_DRAFT_ACTIONS)

    assert "creationMode == .generatedBook || creationMode == .narrateEbook" in basic_source
    assert 'Section(creationMode == .generatedBook ? "Source Book" : "Metadata")' in basic_source
    assert 'creationMode == .generatedBook ? "Source title" : "Title"' in basic_source
    assert 'creationMode == .generatedBook ? "Source author" : "Author"' in basic_source
    assert 'creationMode == .generatedBook ? "Source genre" : "Genre"' in basic_source
    assert 'creationMode == .generatedBook ? "Source summary" : "Summary"' in basic_source
    assert '"createGeneratedSourceBookTitleField"' in basic_source
    assert '"createGeneratedSourceBookAuthorField"' in basic_source
    assert '"createGeneratedSourceBookGenreField"' in basic_source
    assert "sourceBookTitle: sourceBookTitle" in draft_actions_source
    assert "sourceBookAuthor: sourceBookAuthor" in draft_actions_source
    assert "sourceBookGenre: sourceBookGenre" in draft_actions_source
    assert "sourceBookSummary: sourceBookSummary" in draft_actions_source

    assert "let sourceBookTitle: String?" in draft_source
    assert "let sourceBookAuthor: String?" in draft_source
    assert "let sourceBookGenre: String?" in draft_source
    assert "let sourceBookSummary: String?" in draft_source

    assert "sourceBookTitle: draft.sourceBookTitle" in payload_factory_source
    assert "sourceBookAuthor: draft.sourceBookAuthor" in payload_factory_source
    assert "sourceBookGenre: draft.sourceBookGenre" in payload_factory_source
    assert "sourceBookSummary: draft.sourceBookSummary" in payload_factory_source


def test_ipad_split_view_keeps_settings_in_detail_panel() -> None:
    source = _source(LIBRARY_SHELL)

    assert "private static let sidebarColumnMinWidth: CGFloat = 240" in source
    assert "private static let sidebarColumnIdealWidth: CGFloat = 280" in source
    assert "private static let sidebarColumnMaxWidth: CGFloat = 320" in source
    assert "private static let createDetailColumnMinWidth: CGFloat = 760" in source
    assert "private static let createDetailColumnIdealWidth: CGFloat = 940" in source
    assert ".navigationSplitViewColumnWidth(" in source
    assert "min: Self.sidebarColumnMinWidth" in source
    assert "ideal: Self.sidebarColumnIdealWidth" in source
    assert "max: Self.sidebarColumnMaxWidth" in source
    assert "min: Self.createDetailColumnMinWidth" in source
    assert "ideal: Self.createDetailColumnIdealWidth" in source
    assert "private var detailView: some View" in source
    assert "private func browseList() -> some View" in source

    detail_settings = re.search(
        r"case \.settings:\s+PlaybackSettingsView\(",
        source,
    )
    browse_placeholder = re.search(
        r"case \.settings:\s+if isSplitLayout \{\s+placeholderView\(\s+title: \"Settings\",\s+systemImage: \"gearshape\",\s+subtitle: \"Adjust playback options in the detail panel\.\"",
        source,
    )
    browse_compact_settings = re.search(
        r"case \.settings:\s+if isSplitLayout \{.*?\} else \{\s+PlaybackSettingsView\(\s+sectionPicker: sectionPickerForHeader",
        source,
        re.DOTALL,
    )

    assert detail_settings
    assert browse_placeholder
    assert browse_compact_settings


def test_create_submission_routes_to_created_job_with_matching_jobs_filter() -> None:
    source = _source(LIBRARY_SHELL)

    handle_created = re.search(
        r"private func handleCreatedJob\(_ jobId: String\) \{(?P<body>.*?)\n    \}",
        source,
        re.DOTALL,
    )
    open_created = re.search(
        r"private func openCreatedJob\(_ jobId: String\) \{(?P<body>.*?)\n    \}",
        source,
        re.DOTALL,
    )
    focus_created = re.search(
        r"@MainActor\s+private func focusCreatedJob\(_ jobId: String\) async \{(?P<body>.*?)\n    \}",
        source,
        re.DOTALL,
    )
    navigate_job = re.search(
        r"private func navigateToJob\(_ job: PipelineStatusResponse, autoPlay: Bool\) \{(?P<body>.*?)\n    \}",
        source,
        re.DOTALL,
    )
    select_job = re.search(
        r"private func selectJob\(_ job: PipelineStatusResponse, mode: PlaybackStartMode\) \{(?P<body>.*?)\n    \}",
        source,
        re.DOTALL,
    )

    assert handle_created
    assert open_created
    assert focus_created
    assert navigate_job
    assert select_job

    for body in (handle_created.group("body"), open_created.group("body")):
        assert "activeSection = .jobs" in body
        assert "jobsAutoPlay = true" in body
        assert "jobsPlaybackMode = .resume" in body
        assert "focusCreatedJob(jobId)" in body

    assert "await jobsViewModel.load(using: appState)" in focus_created.group("body")
    assert "navigateToJob(job, autoPlay: true)" in focus_created.group("body")
    assert "jobsViewModel.startAutoRefresh(using: appState)" in focus_created.group("body")
    assert "jobsViewModel.activeFilter = jobsViewModel.jobCategory(for: job)" in navigate_job.group("body")
    assert navigate_job.group("body").index("jobsAutoPlay = autoPlay") < navigate_job.group("body").index("selectedJob = job")
    assert navigate_job.group("body").index("jobsPlaybackMode = .resume") < navigate_job.group("body").index("selectedJob = job")
    assert select_job.group("body").index("jobsAutoPlay = true") < select_job.group("body").index("selectedJob = job")
    assert select_job.group("body").index("jobsPlaybackMode = mode") < select_job.group("body").index("selectedJob = job")


def test_ios_create_languages_use_reachable_list_selector() -> None:
    source = _source(CREATE_NARRATION_SECTION)
    selector_source = _source(CREATE_LANGUAGE_SELECTOR)

    assert "struct AppleBookCreateNarrationSection: View" in source
    assert "#if os(tvOS)" in source
    assert 'Picker("Input", selection: $inputLanguage)' in source
    assert "AppleBookCreateLanguageSelector(" in source
    assert 'accessibilityIdentifier: "createBookInputLanguagePicker"' in source
    assert 'accessibilityIdentifier: "createBookTargetLanguagePicker"' in source
    assert "#if !os(tvOS)" in selector_source
    assert "struct AppleBookCreateLanguageSelector: View" in selector_source
    assert "@State private var searchText = \"\"" in selector_source
    assert "private var filteredOptions: [AppleBookCreateLanguage]" in selector_source
    assert '.searchable(text: $searchText, prompt: "Search Languages")' in selector_source
    assert '.sheet(item: $selectedLanguage)' in selector_source
    assert '.accessibilityIdentifier("\\(accessibilityIdentifier).\\(language.id)")' in selector_source
    assert 'Text("\\(options.count) available")' in selector_source
    assert '.accessibilityValue("\\(selection.label), \\(options.count) available")' in selector_source


def test_tvos_create_metadata_json_editor_avoids_text_editor() -> None:
    source = _source(CREATE_METADATA_VIEWS)
    control = re.search(
        r"private var jsonEditorControl: some View \{(?P<body>.*?)\n    \}",
        source,
        re.DOTALL,
    )

    assert control
    assert "#if os(tvOS)" in control.group("body")
    assert 'TextField("Advanced Metadata JSON", text: $text, axis: .vertical)' in control.group("body")
    assert "#else" in control.group("body")
    assert "TextEditor(text: $text)" in control.group("body")


def test_youtube_create_exposes_inline_subtitle_extraction_controls() -> None:
    youtube_source = _source(CREATE_YOUTUBE_SOURCE_CONTROLS)
    youtube_support_source = _source(CREATE_YOUTUBE_SOURCE_SUPPORT_CONTROLS)
    source_factory_source = _source(CREATE_SOURCE_SECTION_FACTORY)

    assert "AppleBookCreateYoutubeEmbeddedSubtitleControls(" in youtube_source
    assert 'buttonIdentifier: "createYoutubeInspectEmbeddedSubtitlesButton"' in youtube_support_source
    assert 'accessibilityIdentifier("createYoutubeEmbeddedSubtitleLanguagesField")' in youtube_support_source
    assert 'buttonIdentifier: "createYoutubeExtractEmbeddedSubtitlesButton"' in youtube_support_source
    assert 'accessibilityIdentifier("createYoutubeEmbeddedSubtitlesMessage")' in youtube_support_source
    assert 'accessibilityIdentifier("createYoutubeEmbeddedSubtitlesError")' in youtube_support_source
    assert "youtubeInlineSubtitleStreams: viewModel.youtubeInlineSubtitleStreams" in source_factory_source
    assert "onInspectYoutubeSubtitles: inspectYoutubeSubtitles" in source_factory_source
    assert "onExtractYoutubeSubtitles: extractYoutubeSubtitles" in source_factory_source


def test_subtitle_create_exposes_editable_metadata_lookup_name() -> None:
    metadata_sections_source = _source(CREATE_MEDIA_METADATA_SECTIONS)
    metadata_controls_source = _source(CREATE_MEDIA_METADATA_CONTROLS)
    view_source = _source(CREATE_VIEW)
    metadata_actions_source = _source(CREATE_METADATA_ACTIONS)

    assert "AppleBookCreateSubtitleMetadataControls" in metadata_sections_source
    assert "@Binding var lookupSourceName: String" in metadata_controls_source
    assert 'TextField("Lookup filename", text: $lookupSourceName)' in metadata_controls_source
    assert 'accessibilityIdentifier("createSubtitleMetadataLookupField")' in metadata_controls_source
    assert "subtitleMetadataLookupSourceName" in view_source
    assert "sourceName: subtitleMetadataLookupSourceName" in metadata_actions_source


def test_apple_create_exposes_metadata_cache_clear_controls() -> None:
    metadata_controls_source = _source(CREATE_MEDIA_METADATA_CONTROLS)
    view_source = _source(CREATE_VIEW)
    metadata_actions_source = _source(CREATE_METADATA_ACTIONS)

    assert "let isClearingCache: Bool" in metadata_controls_source
    assert "let onClearCache: () -> Void" in metadata_controls_source
    assert 'accessibilityIdentifier: "createSubtitleMetadataClearCacheButton"' in metadata_controls_source
    assert "viewModel.isClearingSubtitleTvMetadataCache" in view_source
    assert "clearSubtitleMetadataCache" in view_source
    assert "clearSubtitleTvMetadataCache(" in metadata_actions_source
    assert "query: subtitleMetadataLookupSourceName" in metadata_actions_source

    assert "let isClearingTvMetadataCache: Bool" in metadata_controls_source
    assert "let isClearingYoutubeMetadataCache: Bool" in metadata_controls_source
    assert "let canClearTvMetadataCache: Bool" in metadata_controls_source
    assert "let canClearYoutubeMetadataCache: Bool" in metadata_controls_source
    assert "let onClearTvMetadataCache: () -> Void" in metadata_controls_source
    assert "let onClearYoutubeMetadataCache: () -> Void" in metadata_controls_source
    assert 'accessibilityIdentifier: "createYoutubeClearTvMetadataCacheButton"' in metadata_controls_source
    assert 'accessibilityIdentifier: "createYoutubeClearYoutubeMetadataCacheButton"' in metadata_controls_source
    assert "viewModel.isClearingYoutubeTvMetadataCache" in view_source
    assert "viewModel.isClearingYoutubeMetadataCache" in view_source
    assert "canClearTvMetadataCache: !youtubeMetadataTvSourceName.isEmpty" in view_source
    assert "canClearYoutubeMetadataCache: !youtubeMetadataVideoSourceName.isEmpty" in view_source
    assert "clearYoutubeTvMetadataCache" in view_source
    assert "clearYoutubeVideoMetadataCache" in view_source
    assert "clearYoutubeTvMetadataCache(" in metadata_actions_source
    assert "query: youtubeMetadataTvSourceName" in metadata_actions_source
    assert "clearYoutubeVideoMetadataCache(" in metadata_actions_source
    assert "query: youtubeMetadataVideoSourceName" in metadata_actions_source


def test_apple_create_exposes_tv_metadata_artwork_and_ids() -> None:
    metadata_controls_source = _source(CREATE_MEDIA_METADATA_CONTROLS)
    metadata_source = _source(CREATE_METADATA_VIEWS)
    metadata_bindings_source = _source(CREATE_METADATA_BINDINGS)
    metadata_actions_source = _source(CREATE_METADATA_ACTIONS)
    view_source = _source(CREATE_VIEW)
    view_model_source = _source(CREATE_VIEW_MODEL)
    view_model_metadata_source = _source(CREATE_VIEW_MODEL_METADATA)
    project = _source(XCODE_PROJECT)

    assert "struct AppleBookCreateMetadataArtworkPreview: View" in metadata_source
    assert "AsyncImage(url: url)" in metadata_source
    assert 'accessibilityIdentifier("createMetadataArtworkPreview")' in metadata_source
    assert 'accessibilityIdentifier(item.accessibilityIdentifier)' in metadata_source
    assert "createMetadataPosterPreview" in metadata_source
    assert "createMetadataStillPreview" in metadata_source
    assert "createMetadataYoutubeThumbnailPreview" in metadata_source

    assert 'DisclosureGroup("Artwork")' in metadata_controls_source
    assert "#if os(tvOS)" in metadata_controls_source
    assert "subtitleArtworkFields" in metadata_controls_source
    assert "youtubeArtworkFields" in metadata_controls_source
    assert 'accessibilityIdentifier("createSubtitleMetadataArtworkDisclosure")' in metadata_controls_source
    assert 'accessibilityIdentifier("createSubtitleMetadataPosterUrlField")' in metadata_controls_source
    assert 'accessibilityIdentifier("createSubtitleMetadataStillUrlField")' in metadata_controls_source
    assert "showPosterURL: subtitleMetadataNestedTextBinding(section: \"show\", nestedKey: \"image\", key: \"medium\")" in view_source
    assert "episodeStillURL: subtitleMetadataNestedTextBinding(section: \"episode\", nestedKey: \"image\", key: \"medium\")" in view_source
    assert 'tmdbId: subtitleMetadataNumberBinding(section: "show", key: "tmdb_id")' in view_source
    assert 'imdbId: subtitleMetadataTextBinding(section: "show", key: "imdb_id")' in view_source
    assert 'accessibilityIdentifier("createSubtitleMetadataTmdbIdField")' in metadata_controls_source
    assert 'accessibilityIdentifier("createSubtitleMetadataImdbIdField")' in metadata_controls_source

    assert 'accessibilityIdentifier("createYoutubeMetadataArtworkDisclosure")' in metadata_controls_source
    assert 'accessibilityIdentifier("createYoutubeMetadataPosterUrlField")' in metadata_controls_source
    assert 'accessibilityIdentifier("createYoutubeMetadataStillUrlField")' in metadata_controls_source
    assert 'accessibilityIdentifier("createYoutubeMetadataThumbnailUrlField")' in metadata_controls_source
    assert "tvPosterURL: youtubeMetadataNestedTextBinding(section: \"show\", nestedKey: \"image\", key: \"medium\")" in view_source
    assert "tvEpisodeStillURL: youtubeMetadataNestedTextBinding(section: \"episode\", nestedKey: \"image\", key: \"medium\")" in view_source
    assert 'youtubeThumbnailURL: youtubeMetadataTextBinding(section: "youtube", key: "thumbnail")' in view_source
    assert 'tmdbId: youtubeMetadataNumberBinding(section: "show", key: "tmdb_id")' in view_source
    assert 'imdbId: youtubeMetadataTextBinding(section: "show", key: "imdb_id")' in view_source
    assert "func youtubeMetadataTextBinding(section: String?, key: String)" in metadata_bindings_source
    assert "func youtubeMetadataNumberBinding(section: String, key: String)" in metadata_bindings_source
    assert "func youtubeMetadataNestedTextBinding(section: String, nestedKey: String, key: String)" in metadata_bindings_source
    assert "func subtitleMetadataTextBinding(section: String?, key: String)" in metadata_bindings_source
    assert "func subtitleMetadataNumberBinding(section: String, key: String)" in metadata_bindings_source
    assert "func subtitleMetadataNestedTextBinding(section: String, nestedKey: String, key: String)" in metadata_bindings_source
    assert "viewModel.updateYoutubeMediaMetadata(" in metadata_bindings_source
    assert "viewModel.updateYoutubeMediaMetadataNumber(" in metadata_bindings_source
    assert "viewModel.updateYoutubeMediaMetadataNestedText(" in metadata_bindings_source
    assert "viewModel.updateSubtitleMediaMetadata(" in metadata_bindings_source
    assert "viewModel.updateSubtitleMediaMetadataNumber(" in metadata_bindings_source
    assert "viewModel.updateSubtitleMediaMetadataNestedText(" in metadata_bindings_source
    assert "private func youtubeMetadataNumberBinding(section: String, key: String)" not in view_source
    assert "private func youtubeMetadataNestedTextBinding(section: String, nestedKey: String, key: String)" not in view_source
    assert "private func subtitleMetadataNestedTextBinding(section: String, nestedKey: String, key: String)" not in view_source
    assert "updateYoutubeMediaMetadataNestedText(" not in view_source
    assert "updateSubtitleMediaMetadataNestedText(" not in view_source
    assert "AppleBookCreateMetadataBindings.swift in Sources" in project
    assert project.count("AppleBookCreateMetadataBindings.swift in Sources") == 4
    assert "func updateSubtitleMediaMetadataNestedText(" in view_model_metadata_source
    assert "func updateYoutubeMediaMetadataNestedText(" in view_model_metadata_source
    metadata_json_source = _source(CREATE_METADATA_JSON)
    assert "enum AppleBookCreateMetadataJSON" in metadata_json_source
    assert "static func prettyString(from metadata: [String: JSONValue]?)" in metadata_json_source
    assert "static func parseObject(_ value: String)" in metadata_json_source
    assert "static func cacheClearMessage(cleared: Int, kind: String, query: String)" in metadata_json_source
    assert "static func updateNestedText(" in metadata_json_source
    assert "nested.removeValue(forKey: key)" in metadata_json_source
    assert "sectionDraft.removeValue(forKey: nestedKey)" in metadata_json_source
    assert "AppleBookCreateMetadataJSON.updateNestedText(" in view_model_metadata_source
    assert "private static func updateNestedText(" not in view_model_source
    assert "struct AppleBookCreateAdvancedMetadataJSONEditor: View" in metadata_source
    assert 'DisclosureGroup("Advanced Metadata JSON")' in metadata_source
    assert "@Binding var advancedMetadataJSON: String" in metadata_controls_source
    assert "let advancedMetadataErrorMessage: String?" in metadata_controls_source
    assert "TextEditor(text: $text)" in metadata_source
    assert 'disclosureIdentifier: "createSubtitleAdvancedMetadataDisclosure"' in metadata_controls_source
    assert 'textEditorIdentifier: "createSubtitleAdvancedMetadataJSONEditor"' in metadata_controls_source
    assert 'applyIdentifier: "createSubtitleAdvancedMetadataApplyButton"' in metadata_controls_source
    assert 'syncIdentifier: "createSubtitleAdvancedMetadataSyncButton"' in metadata_controls_source
    assert 'disclosureIdentifier: "createYoutubeAdvancedMetadataDisclosure"' in metadata_controls_source
    assert 'textEditorIdentifier: "createYoutubeAdvancedMetadataJSONEditor"' in metadata_controls_source
    assert 'applyIdentifier: "createYoutubeAdvancedMetadataApplyButton"' in metadata_controls_source
    assert 'syncIdentifier: "createYoutubeAdvancedMetadataSyncButton"' in metadata_controls_source
    assert "advancedMetadataJSON: $viewModel.subtitleMediaMetadataJSONText" in view_source
    assert "advancedMetadataJSON: $viewModel.youtubeMediaMetadataJSONText" in view_source
    assert "viewModel.applySubtitleMediaMetadataJSONText()" in metadata_actions_source
    assert "viewModel.applyYoutubeMediaMetadataJSONText()" in metadata_actions_source
    assert "viewModel.syncSubtitleMediaMetadataJSONText()" in metadata_actions_source
    assert "viewModel.syncYoutubeMediaMetadataJSONText()" in metadata_actions_source
    assert "func applySubtitleMediaMetadataJSONText()" in view_model_metadata_source
    assert "func applyYoutubeMediaMetadataJSONText()" in view_model_metadata_source
    assert "AppleBookCreateMetadataJSON.parseObject(" in view_model_metadata_source
    assert "private static func parseMetadataJSONObject" not in view_model_source
    assert "JSONDecoder().decode([String: JSONValue].self" in metadata_json_source
    assert "AppleBookCreateMetadataJSON.swift in Sources" in project
    assert project.count("AppleBookCreateMetadataJSON.swift in Sources") == 4
    assert 'accessibilityIdentifier("createYoutubeMetadataTmdbIdField")' in metadata_controls_source
    assert 'accessibilityIdentifier("createYoutubeMetadataImdbIdField")' in metadata_controls_source
