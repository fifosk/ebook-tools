from __future__ import annotations

import re
from pathlib import Path


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
CREATE_TEMPLATE_SETTINGS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateTemplateSettings.swift"
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
CREATE_SOURCE_CONTROLS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateSourceControls.swift"
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
WEB_APP_VIEWS = ROOT / "web" / "src" / "utils" / "appViewDeepLink.ts"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
    lifecycle_source = _source(CREATE_LIFECYCLE)
    submission_actions_source = _source(CREATE_SUBMISSION_ACTIONS)

    assert "@Binding var creationMode: AppleCreateMode" in source
    assert "@State private var creationMode = AppleCreateMode.generatedBook" not in source
    assert "showsInlineJobTypePicker: Bool" in source
    assert "showsJobTypePicker: false" in source
    assert "@Environment(\\.horizontalSizeClass) private var horizontalSizeClass" in source
    assert "private var usesRegularWidthCreateLayout: Bool" in source
    assert "horizontalSizeClass == .regular" in source
    assert "onLoadCreateDependencies: loadCreateDependencies" in source
    assert "await onLoadCreateDependencies()" in lifecycle_source
    assert "private func loadCreateDependencies() async" in source
    assert "handleSubtitleSourcePathChange()" in source
    assert "private func handleSubtitleSourcePathChange()" in source
    assert "onYoutubeVideoPathChange(newValue)" in lifecycle_source
    assert "private func handleYoutubeVideoPathChange(_ path: String)" in source
    assert "handleLanguagePreferenceChange()" in source
    assert "private func handleLanguagePreferenceChange()" in source
    assert "func completeSubmission(_ jobId: String?) async" in submission_actions_source
    assert submission_actions_source.count("await completeSubmission(jobId)") == 4
    assert submission_actions_source.count("onJobSubmitted(jobId)") == 1
    assert "private func completeSubmission(_ jobId: String?) async" not in source


def test_apple_create_can_load_and_apply_web_creation_templates() -> None:
    view_source = _source(CREATE_VIEW)
    presentation_state_source = _source(CREATE_PRESENTATION_STATE)
    submission_actions_source = _source(CREATE_SUBMISSION_ACTIONS)
    view_model_source = _source(CREATE_VIEW_MODEL)
    status_views_source = _source(CREATE_STATUS_VIEWS)
    source_section_source = _source(CREATE_SOURCE_SECTION)
    template_settings_source = _source(CREATE_TEMPLATE_SETTINGS)
    template_save_factory_source = _source(CREATE_TEMPLATE_SAVE_PAYLOAD_FACTORY)
    api_models_source = _source(PIPELINE_CREATION_API_MODELS)
    api_client_source = _source(API_CLIENT_CREATION)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "struct CreationTemplateListResponse: Decodable, Equatable" in api_models_source
    assert "struct CreationTemplateEntry: Decodable, Equatable, Identifiable" in api_models_source
    assert "struct CreationTemplateSaveRequest: Encodable, Equatable" in api_models_source
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
    assert "client.saveCreationTemplate(request)" in view_model_source
    assert "func deleteCreationTemplate(templateId: String) async throws" in api_client_source
    assert "AppleCreateRuntimeContract.templatePath(encoded)" in api_client_source
    assert 'method: "DELETE"' in api_client_source
    assert 'URLQueryItem(name: "mode", value: mode)' in api_client_source

    assert "@Published private(set) var creationTemplates: [CreationTemplateEntry] = []" in view_model_source
    assert "@Published private(set) var isLoadingCreationTemplates = false" in view_model_source
    assert "@Published private(set) var isSavingCreationTemplate = false" in view_model_source
    assert "@Published private(set) var isDeletingCreationTemplate = false" in view_model_source
    assert "@Published private(set) var creationTemplatesErrorMessage: String?" in view_model_source
    assert "@Published var creationTemplateMessage: String?" in view_model_source
    assert "func loadCreationTemplates(" in view_model_source
    assert "client.fetchCreationTemplates()" in view_model_source
    assert "func saveCreationTemplate(" in view_model_source
    assert "creationTemplates.insert(saved, at: 0)" in view_model_source
    assert "func deleteCreationTemplate(" in view_model_source
    assert "client.deleteCreationTemplate(templateId: trimmedID)" in view_model_source
    assert "creationTemplates.removeAll { $0.id == trimmedID }" in view_model_source

    assert "struct AppleBookCreateTemplateSection: View" in status_views_source
    for identifier in [
        "createBookTemplatePicker",
        "createBookSaveTemplateButton",
        "createBookApplyTemplateButton",
        "createBookDeleteTemplateButton",
        "createBookRefreshTemplatesButton",
        "createBookTemplateStatusLabel",
        "createBookTemplateErrorLabel",
    ]:
        assert identifier in status_views_source

    assert "private var templateSection: some View" in view_source
    assert "AppleBookCreateTemplateSection(" in view_source
    assert "await refreshCreationTemplates()" in view_source
    assert "private func saveCurrentCreationTemplate()" in view_source
    assert "private func currentCreationTemplateSaveRequest() -> CreationTemplateSaveRequest?" in view_source
    assert "AppleBookCreateTemplateSavePayloadFactory.makeGeneratedBookRequest(" in view_source
    assert "selectedTemplateID = template.id" in view_source
    assert "private func applySelectedCreationTemplate()" in view_source
    assert "private func requestDeleteSelectedCreationTemplate()" in view_source
    assert "private func deleteCreationTemplate(_ template: CreationTemplateEntry) async" in view_source
    assert "creationTemplatePendingDelete = template" in view_source
    assert "await viewModel.deleteCreationTemplate(" in view_source
    assert "private func applyCreationTemplate(_ template: CreationTemplateEntry)" in view_source
    assert "AppleBookCreateTemplateSettings.compatibleTemplates(" in presentation_state_source
    assert "AppleBookCreateTemplateSettings.compatibleTemplates(" not in view_source
    assert "AppleBookCreateTemplateSettings.mode(for: template)" in view_source
    assert 'template.normalizedMode == "subtitle_job"' not in view_source
    assert 'template.normalizedMode == "youtube_dub"' not in view_source
    assert "private func applySubtitleCreationTemplate(" in view_source
    assert "private func applyYoutubeDubCreationTemplate(" in view_source
    assert "AppleBookCreateTemplateSettings.settings(from: template)" in view_source
    subtitle_template_body = view_source.split("private func applySubtitleCreationTemplate(", 1)[1].split(
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
    assert "AppleBookCreateTemplateSettings.languageApplication(from: formState)" in view_source
    language_body = view_source.split("private func applyTemplateLanguages(", 1)[1].split(
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
    assert "AppleBookCreateTemplateSettings.voiceApplication(from: formState)" in view_source
    narration_body = view_source.split("private func applyTemplateNarrationSettings(", 1)[1].split(
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
    assert "AppleBookCreateTemplateSettings.audioApplication(from: formState)" in view_source
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
    assert "AppleBookCreateTemplateSettings.bookTranslationApplication(from: formState)" in view_source
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
    assert "AppleBookCreateTemplateSettings.outputApplication(from: formState)" in view_source
    output_body = view_source.split("private func applyTemplateOutputSettings(", 1)[1].split(
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
    assert "AppleBookCreateTemplateSettings.imageApplication(from: formState)" in view_source
    image_body = view_source.split("private func applyTemplateImageSettings(", 1)[1].split(
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
    assert "AppleBookCreateTemplateSettings.workerApplication(from: formState)" in view_source
    worker_body = view_source.split("private func applyTemplateWorkerSettings(", 1)[1].split(
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
    assert "AppleBookCreateTemplateSettings.metadataObject(from: formState)" in view_source
    assert "applyTemplateDiscoveryState(template, formState: formState)" in view_source
    assert "private func applyTemplateDiscoveryState(" in view_source
    assert "AppleBookCreateTemplateSettings.discoveryApplication(" in view_source
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
    assert "AppleBookCreateTemplateSettings.resolvedTemplateSelection(" in view_source
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
    assert "AppleBookCreateTemplateSettings.bookMetadataApplication(from: formState)" in view_source
    metadata_body = view_source.split("private func applyTemplateMetadata(", 1)[1].split(
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
    assert "AppleBookCreateTemplateSettings.sourceBookContextApplication(from: formState)" in view_source
    source_context_body = view_source.split("private func applyTemplateSourceBookContext(", 1)[1].split(
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
    assert 'extras["acquisition_provider"] = .string(provider)' in template_settings_source
    assert 'extras["acquisition_candidate_id"] = .string(value)' in template_settings_source
    assert "AppleBookCreatePresentation.normalizedBookMetadataExtras(extras)" in template_settings_source
    assert "static func stringArray(_ object: [String: JSONValue], _ key: String)" in template_settings_source
    assert "static func stringDictionary(from value: JSONValue?)" in template_settings_source
    assert "static func endSentenceText(from value: JSONValue?)" in template_settings_source
    assert "static func discoveryState(from template: CreationTemplateEntry)" in template_settings_source
    assert 'template.payload["discovery_state"]' in template_settings_source
    assert "enum AppleBookCreateTemplateSavePayloadFactory" not in template_settings_source
    youtube_template_body = view_source.split("private func applyYoutubeDubCreationTemplate(", 1)[1].split(
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
    assert view_source.count("AppleBookCreatePresentation.generatedBookDraft(") == 1
    assert view_source.count("AppleBookCreatePresentation.narrateEbookDraft(") == 1
    assert view_source.count("AppleBookCreatePresentation.subtitleJobDraft(") == 1
    assert view_source.count("AppleBookCreatePresentation.youtubeDubDraft(") == 1
    assert "videoDiscoveryState: youtubeDiscoveryState" in view_source
    assert view_source.count("videoDiscoveryState: youtubeDiscoveryState") == 1
    assert "private var youtubeDiscoveryState: [String: JSONValue]?" in view_source
    assert "private func youtubeDiscoveryStatePayload(" not in view_source
    discovery_source = _source(CREATE_DISCOVERY_PRESENTATION)
    assert "static func videoDiscoveryStatePayload(" in discovery_source
    assert "static func videoDiscoveryState(" in discovery_source
    assert 'state["selected_subtitle_path"] = .string(trimmed)' in discovery_source
    assert 'state.removeValue(forKey: "selected_subtitle_path")' in discovery_source
    assert "AppleBookCreatePresentation.videoDiscoveryStatePayload(" in view_source
    assert "AppleBookCreatePresentation.videoDiscoveryState(" in view_source
    assert 'youtubeDiscoveryState?["selected_subtitle_path"]' not in view_source
    assert "let discoveryState = AppleBookCreatePresentation.normalizedVideoDiscoveryState(" in view_source
    assert "youtubeDiscoveryState = discoveryState" in view_source
    assert "static func youtubeVideoPath(" in template_settings_source
    assert "static func youtubeSubtitlePath(" in template_settings_source
    assert 'string(discoveryState ?? [:], "selected_video_path")' in template_settings_source
    assert 'string(discoveryState ?? [:], "local_path")' in template_settings_source
    assert 'string(discoveryState ?? [:], "selected_subtitle_path")' in template_settings_source
    assert "videoPath: youtubeVideoPath(formState: formState, discoveryState: discoveryState)" in template_settings_source
    assert "subtitlePath: youtubeSubtitlePath(formState: formState, discoveryState: discoveryState)" in template_settings_source
    assert "AppleBookCreateTemplateSettings.discoveryState(from: template)" in view_source
    assert '"media_kind": .string("video")' in discovery_source
    assert '"candidate_id": .string(candidate.candidateId)' in discovery_source
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


def test_create_defaults_are_split_from_support_and_target_wired() -> None:
    defaults_source = _source(CREATE_DEFAULTS)
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
    assert "AppleBookCreateDefaults.swift in Sources" in project
    assert project.count("AppleBookCreateDefaults.swift in Sources") == 4
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
    assert "AppleBookCreatePresentationHelpers.swift" in payload_script
    assert "AppleBookCreateDiscoveryPresentation.swift" in payload_script


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
    assert "AppleBookCreateDrafts.swift in Sources" in project
    assert project.count("AppleBookCreateDrafts.swift in Sources") == 4
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

    for callback in [
        "onRefreshPipelineFiles: refreshPipelineFilesFromSourceSection",
        "onRefreshSubtitleSources: refreshSubtitleSourcesFromSourceSection",
        "onRefreshYoutubeLibrary: refreshYoutubeLibraryFromSourceSection",
        "onChooseNarrateFile: chooseNarrateFile",
        "onChooseSubtitleFile: chooseSubtitleFile",
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

    assert "onRefreshPipelineFiles: {\n                Task" not in view_source
    assert "onRefreshVoiceInventory: {\n                Task" not in view_source
    assert "onLoadTvMetadata: {\n                Task" not in view_source
    assert "onLookup: {\n                Task" not in view_source
    assert "onRetryDefaults: {\n                Task" not in view_source


def test_tvos_create_loads_server_backed_source_defaults() -> None:
    view_source = _source(CREATE_VIEW)

    for function_name, loader in [
        ("refreshPipelineFiles", "viewModel.loadPipelineFiles"),
        ("refreshSubtitleSources", "viewModel.loadSubtitleSources"),
        ("refreshYoutubeLibrary", "viewModel.loadYoutubeLibrary"),
    ]:
        match = re.search(
            rf"(?:private )?func {function_name}\(force: Bool = false\) async \{{(?P<body>.*?)\n    \}}",
            view_source,
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
    narration_source = _source(CREATE_NARRATION_SECTION)
    view_source = _source(CREATE_VIEW)
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
    assert "viewModel.checkImageNodeAvailability(" in view_source
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
    assert "AppleBookCreateOutputSection.swift in Sources" in project
    assert project.count("AppleBookCreateOutputSection.swift in Sources") == 4
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
    assert "AppleBookCreateHistoryDefaults.swift in Sources" in project
    assert project.count("AppleBookCreateHistoryDefaults.swift in Sources") == 4
    assert "AppleBookCreateHistoryParsing.swift in Sources" in project
    assert project.count("AppleBookCreateHistoryParsing.swift in Sources") == 4
    assert "AppleBookCreateHistoryDefaults.swift" in payload_script
    assert "AppleBookCreateHistoryParsing.swift" in payload_script


def test_create_language_options_are_split_from_support_and_target_wired() -> None:
    language_source = _source(CREATE_LANGUAGE_OPTIONS)
    sample_source = _source(CREATE_VOICE_PREVIEW_SAMPLES)
    selector_source = _source(CREATE_LANGUAGE_SELECTOR)
    view_source = _source(CREATE_VIEW)
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
    assert "AppleBookCreatePresentation.languageVoiceOptions(" in view_source
    assert "AppleBookCreatePresentation.targetLanguagesForVoiceOverrides(" in view_source
    assert "var result = [String: [AppleBookCreateVoiceOption]]()" not in view_source
    assert "AppleBookCreateLanguageOptions.swift in Sources" in project
    assert project.count("AppleBookCreateLanguageOptions.swift in Sources") == 4
    assert "AppleBookCreateVoicePreviewSamples.swift in Sources" in project
    assert project.count("AppleBookCreateVoicePreviewSamples.swift in Sources") == 4
    assert "struct AppleBookCreateLanguageSelector: View" in selector_source
    assert "AppleBookCreateLanguageSelector.swift in Sources" in project
    assert project.count("AppleBookCreateLanguageSelector.swift in Sources") == 4
    assert "AppleBookCreateLanguageOptions.swift" in payload_script
    assert "AppleBookCreateVoicePreviewSamples.swift" in payload_script


def test_create_source_selection_is_split_from_support_and_target_wired() -> None:
    source_selection = _source(CREATE_SOURCE_SELECTION)
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
    assert "AppleBookCreatePresentation.narrateSourceDefaults(" in view_source
    assert "trimmed(sourceBaseOutput).isEmpty && !editedFields.contains(.sourceBaseOutput)" not in view_source
    assert "private func refreshNarrateBaseOutputIfNeeded(" in view_source
    assert "private func shouldRefreshNarrateBaseOutput(" in view_source
    assert "currentBaseOutput == derivedNarrateBaseOutputName(for: previousSourcePath)" in view_source
    assert "private func derivedNarrateBaseOutputName(for sourcePath: String)" in view_source
    assert "AppleBookCreatePresentation.selectedPipelineEbook(" in view_source
    assert "refreshNarrateBaseOutputIfNeeded(for: newValue, replacing: previousSourcePath)" in view_source
    assert "AppleBookCreatePresentation.subtitleSourceDefaults(" in view_source
    assert "AppleBookCreatePresentation.youtubeSourceDefaults(" in view_source
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
    assert "preferenceScope.storedLanguagePreferences()" in view_source
    assert "preferenceScope.persistLanguagePreferences(preferences)" in view_source
    assert "var youtubeLibraryLoadKey: String" in lifecycle_source
    assert "preferenceScope.youtubeLibraryLoadKey" in lifecycle_source
    assert "var preferenceScope: AppleBookCreatePreferenceScope" not in view_source
    assert "func storedYoutubeSelectionPath(field: String)" not in view_source
    assert "func persistYoutubeSelectionPath(_ path: String, field: String)" not in view_source
    assert "func applyStoredYoutubeBaseDir()" not in view_source
    assert "func persistYoutubeBaseDir(_ baseDir: String)" not in view_source
    assert "func applyStoredSubtitleShowOriginal()" not in view_source
    assert "func persistSubtitleShowOriginal(_ value: Bool)" not in view_source
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
    assert "@Published private(set) var isUploadingPipelineEbook = false" in _source(CREATE_VIEW_MODEL)
    assert "func uploadPipelineEbook(" in _source(CREATE_VIEW_MODEL)
    assert "client.uploadPipelineEbook(fileURL: fileURL, filename: filename)" in _source(CREATE_VIEW_MODEL)
    assert "mergePipelineEbook(uploaded)" in _source(CREATE_VIEW_MODEL)
    assert "isUploadingPipelineEbook: viewModel.isUploadingPipelineEbook" in view_source
    assert "importNarrateEbookToServer(selection)" in import_actions_source
    assert "viewModel.uploadPipelineEbook(" in import_actions_source
    assert "sourcePath = uploaded.path" in import_actions_source
    assert "selectedNarrateFileURL = nil" in import_actions_source
    assert "private func importNarrateEbookToServer(_ selection: AppleBookCreateNarrateImportSelection)" not in view_source
    assert "isUploadingPipelineEbook ? \"Importing EPUB\"" in _source(CREATE_SOURCE_CONTROLS)
    assert ".disabled(isBusy)" in _source(CREATE_SOURCE_CONTROLS)
    assert 'accessibilityIdentifier("\\(buttonIdentifier).progress")' in _source(CREATE_SOURCE_CONTROLS)


def test_source_section_can_move_job_type_picker_out_of_detail_form() -> None:
    source = _source(CREATE_SOURCE_SECTION)
    controls_source = _source(CREATE_SOURCE_CONTROLS)
    youtube_source = _source(CREATE_YOUTUBE_SOURCE_CONTROLS)
    narration_source = _source(CREATE_NARRATION_SECTION)
    project = _source(XCODE_PROJECT)

    assert "struct AppleBookCreateSourceSection: View" in source
    assert "struct AppleBookCreateNarrateSourceControls: View" in controls_source
    assert "struct AppleBookCreateSubtitleSourceControls: View" in controls_source
    assert "struct AppleBookCreateYoutubeSourceControls: View" in youtube_source
    assert "struct AppleBookCreateFileImportControl: View" in controls_source
    assert "struct AppleBookCreateSourceActionRow: View" in controls_source
    assert "AppleBookCreateBusyActionButton(" in controls_source
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
    assert 'Picker("Server subtitle", selection: $subtitleSourcePath)' in controls_source
    assert "AppleBookCreatePresentation.chapterRangeSelection(" in controls_source
    assert "AppleBookCreatePresentation.subtitleJobSources(from: subtitleSources)" in controls_source
    assert 'Picker("NAS video", selection: $youtubeVideoPath)' in youtube_source
    assert "AppleBookCreatePresentation.playableYoutubeSubtitles(for:" in youtube_source
    assert controls_source.count("AppleBookCreateSourceActionRow(") == 2
    assert youtube_source.count("AppleBookCreateSourceActionRow(") == 3
    assert 'buttonIdentifier: "createYoutubeInspectEmbeddedSubtitlesButton"' in youtube_source
    assert "struct AppleBookCreateSourceSection: View" not in narration_source
    assert "AppleBookCreateSourceSection.swift in Sources" in project
    assert project.count("AppleBookCreateSourceSection.swift in Sources") == 4
    assert "AppleBookCreateSourceControls.swift in Sources" in project
    assert project.count("AppleBookCreateSourceControls.swift in Sources") == 4
    assert "AppleBookCreateYoutubeSourceControls.swift in Sources" in project
    assert project.count("AppleBookCreateYoutubeSourceControls.swift in Sources") == 4
    assert "AppleBookCreateNarrationSection.swift in Sources" in project
    assert project.count("AppleBookCreateNarrationSection.swift in Sources") == 4
    assert "AppleBookCreateSections.swift" not in project


def test_subtitle_source_delete_is_wired_through_apple_create() -> None:
    view_source = _source(CREATE_VIEW)
    lifecycle_source = _source(CREATE_LIFECYCLE)
    source = _source(CREATE_SOURCE_SECTION)
    controls_source = _source(CREATE_SOURCE_CONTROLS)
    view_model_source = _source(CREATE_VIEW_MODEL)
    api_models_source = _source(PIPELINE_CREATION_API_MODELS)
    api_client_source = _source(API_CLIENT_CREATION)

    assert 'static let subtitleDeleteSourcePath = "/api/subtitles/delete-source"' in api_client_source
    assert "func deleteSubtitleSource(" in api_client_source
    assert "path: AppleCreateRuntimeContract.subtitleDeleteSourcePath" in api_client_source
    assert "struct SubtitleSourceDeleteRequest: Encodable, Equatable" in api_models_source
    assert "struct SubtitleSourceDeleteResponse: Decodable, Equatable" in api_models_source
    assert "func deleteSubtitleSource(" in view_model_source
    assert "isDeletingSubtitleSource = true" in view_model_source
    assert "client.deleteSubtitleSource(subtitlePath: trimmedPath)" in view_model_source
    assert "subtitleSources = SubtitleSourceListResponse(" in view_model_source
    assert "let isDeletingSubtitleSource: Bool" in source
    assert "let onDeleteSubtitleSource: (SubtitleSourceEntry) -> Void" in source
    assert "isDeletingSubtitleSource: isDeletingSubtitleSource" in source
    assert "onDeleteSubtitleSource: onDeleteSubtitleSource" in source
    assert "let isDeletingSubtitleSource: Bool" in controls_source
    assert "let onDeleteSubtitleSource: (SubtitleSourceEntry) -> Void" in controls_source
    assert 'accessibilityIdentifier("createSubtitleDeleteServerSourceButton")' in controls_source
    assert 'accessibilityIdentifier("createSubtitleDeleteServerSourceProgress")' in controls_source
    assert "private var selectedSubtitleSourceEntry: SubtitleSourceEntry?" in controls_source
    assert "subtitleSourcePendingDelete" in view_source
    assert "confirmationDialog(" in lifecycle_source
    assert 'accessibilityIdentifier("confirmDeleteSubtitleSourceButton")' in lifecycle_source
    assert "onDeleteSubtitleSource: requestDeleteSubtitleSource" in view_source


def test_narrate_epub_source_delete_is_wired_through_apple_create() -> None:
    view_source = _source(CREATE_VIEW)
    lifecycle_source = _source(CREATE_LIFECYCLE)
    source = _source(CREATE_SOURCE_SECTION)
    controls_source = _source(CREATE_SOURCE_CONTROLS)
    view_model_source = _source(CREATE_VIEW_MODEL)
    api_models_source = _source(PIPELINE_CREATION_API_MODELS)
    api_client_source = _source(API_CLIENT_CREATION)

    assert "struct PipelineFileDeleteRequest: Encodable, Equatable" in api_models_source
    assert "func deletePipelineEbook(" in api_client_source
    assert 'method: "DELETE"' in api_client_source
    assert "payload: PipelineFileDeleteRequest(path: path)" in api_client_source
    assert "func deletePipelineEbook(" in view_model_source
    assert "isDeletingPipelineEbook = true" in view_model_source
    assert "client.deletePipelineEbook(path: trimmedPath)" in view_model_source
    assert "pipelineFiles = PipelineFileBrowserResponse(" in view_model_source
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
    assert "onDeletePipelineEbook: requestDeletePipelineEbook" in view_source


def test_narrate_epub_acquisition_discovery_is_wired_through_apple_create() -> None:
    view_source = _source(CREATE_VIEW)
    source = _source(CREATE_SOURCE_SECTION)
    source_section_source = source
    controls_source = _source(CREATE_SOURCE_CONTROLS)
    view_model_source = _source(CREATE_VIEW_MODEL)
    api_models_source = _source(PIPELINE_CREATION_API_MODELS)
    api_client_source = _source(API_CLIENT_CREATION)
    template_factory_source = _source(CREATE_TEMPLATE_SAVE_PAYLOAD_FACTORY)
    drafts_source = _source(CREATE_DRAFTS)

    assert 'static let acquisitionDiscoverPath = "/api/acquisition/discover"' in api_client_source
    assert "func discoverAcquisitionCandidates(" in api_client_source
    assert 'URLQueryItem(name: "media_kind", value: mediaKind)' in api_client_source
    assert 'URLQueryItem(name: "provider", value: provider)' in api_client_source
    assert 'URLQueryItem(name: "source_id", value: normalizedSourceId)' in api_client_source
    assert "try decode(AcquisitionDiscoveryResponse.self, from: data)" in api_client_source
    assert "struct AcquisitionCandidate: Decodable, Equatable, Identifiable" in api_models_source
    assert "let candidateToken: String" in api_models_source
    assert "let localPath: String?" in api_models_source
    assert "struct AcquisitionDiscoveryResponse: Decodable, Equatable" in api_models_source
    assert "let defaultProviderIds: [String: [String]]?" in api_models_source
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
    assert "@Published private(set) var ebookAcquisitionDiscovery: AcquisitionDiscoveryResponse?" in view_model_source
    assert "@Published private(set) var isLoadingEbookAcquisitionDiscovery = false" in view_model_source
    assert "@Published private(set) var isAcquiringEbookDiscoveryCandidate = false" in view_model_source
    assert "func loadEbookDiscovery(" in view_model_source
    assert 'mediaKind: "book"' in view_model_source
    assert "AppleBookCreatePresentation.isDefaultBookDiscoveryProviderID(normalizedProvider)" in view_model_source
    assert 'provider: requestProvider' in view_model_source
    assert "sourceIds: normalizedSourceIds" in view_model_source
    assert "func acquireEbookDiscoveryCandidate(" in view_model_source
    assert "func prepareEbookDiscoveryCandidate(" in view_model_source
    assert "client.acquireAcquisitionCandidate(" in view_model_source
    assert "client.prepareAcquisitionArtifact(" in view_model_source
    assert "AppleBookCreatePresentation.internetArchiveSourceIDs(candidate)" in view_source
    assert 'provider: "internet_archive"' in view_source
    assert "sourceIds: sourceIds" in view_source

    assert "let ebookAcquisitionDiscovery: AcquisitionDiscoveryResponse?" in source
    assert "let acquisitionProviders: [AcquisitionProviderEntry]" in source
    assert "let acquisitionDefaultProviderIds: [String: [String]]" in source
    assert "let isAcquiringEbookAcquisitionCandidate: Bool" in source
    assert "let acquisitionProvidersErrorMessage: String?" in controls_source
    assert "acquisitionProviders: viewModel.acquisitionProviders" in view_source
    assert "acquisitionDefaultProviderIds: viewModel.acquisitionDefaultProviderIds" in view_source
    assert "acquisitionProviders: acquisitionProviders" in source
    assert "acquisitionDefaultProviderIds: acquisitionDefaultProviderIds" in source
    assert "let onSearchAcquisitionDiscovery: (String, String) -> Void" in source
    assert "let onSelectAcquisitionCandidate: (AcquisitionCandidate) -> Void" in source
    assert "ebookAcquisitionDiscovery: viewModel.ebookAcquisitionDiscovery" in view_source
    assert "isAcquiringEbookAcquisitionCandidate: viewModel.isAcquiringEbookDiscoveryCandidate" in view_source
    assert "onSearchAcquisitionDiscovery: searchAcquisitionDiscovery" in view_source
    assert "onSelectAcquisitionCandidate: applyAcquisitionDiscoveryCandidate" in view_source
    assert "private func applyAcquisitionDiscoveryCandidate(_ candidate: AcquisitionCandidate)" in view_source
    assert "viewModel.acquireEbookDiscoveryCandidate(" in view_source
    assert "viewModel.prepareEbookDiscoveryCandidate(" in view_source
    assert "private func applyAcquisitionDiscoveryPath(_ localPath: String)" in view_source
    assert "refreshNarrateBaseOutputIfNeeded(for: localPath, replacing: previousSourcePath)" in view_source
    assert "clearNarrateChapterSelection()" in view_source
    assert "func clearNarrateSourceMetadata()" in view_source
    assert "bookMetadataExtras = [:]" in view_source
    assert "clearNarrateSourceMetadata()" in view_source
    presentation_source = _source(CREATE_PRESENTATION_HELPERS)
    discovery_source = _source(CREATE_DISCOVERY_PRESENTATION)
    assert "struct AppleBookCreateDiscoveryProviderOption" in discovery_source
    assert "static func bookDiscoveryProviderOptions(" in discovery_source
    assert "static func bookDiscoveryProviderOptions(" not in presentation_source
    assert "private static let fallbackBookDiscoveryProviders" in discovery_source
    assert 'let available: Bool' in discovery_source
    assert 'static let defaultBookDiscoveryProviderID = "backend_defaults"' in discovery_source
    assert "static func isDefaultBookDiscoveryProviderID" in discovery_source
    assert "private static let defaultBookDiscoveryProvider = AppleBookCreateDiscoveryProviderOption(" in discovery_source
    assert 'AppleBookCreateDiscoveryProviderOption(id: "manual_downloads", label: "Manual downloads", available: true)' in discovery_source
    assert 'AppleBookCreateDiscoveryProviderOption(id: "gutenberg", label: "Gutenberg", available: true)' in discovery_source
    assert 'AppleBookCreateDiscoveryProviderOption(id: "internet_archive", label: "Internet Archive", available: true)' in discovery_source
    assert 'AppleBookCreateDiscoveryProviderOption(id: "openlibrary", label: "Open Library", available: true)' in discovery_source
    assert 'AppleBookCreateDiscoveryProviderOption(id: "zlibrary_attended", label: "Z-Library import", available: false)' in discovery_source
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
    assert "private var acquisitionDiscoveryProviderBinding: Binding<String>" in controls_source
    assert "hasUserSelectedDiscoveryProvider = true" in controls_source
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
    assert "let discoveryMediaKinds: [String]?" in api_models_source
    assert "enum AppleBookCreateNarrateSourcePanel" in controls_source
    assert "case discovery" in controls_source
    assert "@Binding var sourcePanel: AppleBookCreateNarrateSourcePanel" in controls_source
    assert "@State private var narrateSourcePanel = AppleBookCreateNarrateSourcePanel.server" in view_source
    assert "narrateSourcePanel: $narrateSourcePanel" in view_source
    assert "@Binding var narrateSourcePanel: AppleBookCreateNarrateSourcePanel" in source_section_source
    assert "sourcePanel: $narrateSourcePanel" in source_section_source
    assert "narrateSourcePanel = shouldUseDiscoverySourcePanel ? .discovery : .server" in view_source
    assert 'accessibilityIdentifier("createNarrateSourceModePicker")' in controls_source
    assert "discoverySourceControls" in controls_source
    assert 'accessibilityIdentifier("createNarrateDiscoveryPanel")' in controls_source
    assert 'provider.mediaKinds.contains("book")' in discovery_source
    assert "if let discoveryMediaKinds = provider.discoveryMediaKinds" in discovery_source
    assert 'return discoveryMediaKinds.contains("book")' in discovery_source
    assert "bookDiscoveryCapabilities.contains($0)" in discovery_source
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
    assert "private static func discoveryProviderUnavailableMessage(" in discovery_source
    assert "provider.policyNotes.first" in discovery_source
    assert "|| !isSelectedDiscoveryProviderAvailable" in controls_source
    assert "AppleBookCreatePresentation.bookDiscoveryCandidates(from: acquisitionDiscovery)" in controls_source
    assert "AppleBookCreatePresentation.bookDiscoveryCandidateDetail(candidate)" in controls_source
    assert "AppleBookCreatePresentation.bookDiscoveryCandidateAction(candidate)" in controls_source
    assert "AppleBookCreatePresentation.canSelectBookDiscoveryCandidate(candidate)" in controls_source
    assert '$0.capabilities.contains("acquire")' in discovery_source
    assert '$0.provider == "openlibrary"' in discovery_source
    assert 'return candidate.capabilities.contains("metadata") ? "Apply metadata" : "Review"' in discovery_source
    assert "static func canSelectBookDiscoveryCandidate(_ candidate: AcquisitionCandidate)" in discovery_source
    assert "private func canSelectDiscoveryCandidate(" not in controls_source
    assert "private func discoveryCandidateDetail(" not in controls_source
    assert "private func discoveryCandidateAction(" not in controls_source
    assert "guard candidate.capabilities.contains(\"acquire\") else" in view_model_source
    assert "applyAcquisitionDiscoveryMetadata(candidate)" in view_source
    assert "private func applyAcquisitionDiscoveryMetadata(_ candidate: AcquisitionCandidate) -> Bool" in view_source
    assert "AppleBookCreatePresentation.bookDiscoveryMetadataApplication(candidate)" in view_source
    assert "@State private var bookMetadataExtras = [String: JSONValue]()" in view_source
    assert "bookMetadataExtras: bookMetadataExtras" in view_source
    assert "bookMetadataExtras = metadataApplication.bookMetadataExtras" in view_source
    assert "private func acquisitionBookMetadataExtras(" not in view_source
    assert "struct AppleBookCreateBookDiscoveryMetadataApplication: Equatable" in discovery_source
    assert "static func bookDiscoveryMetadataApplication(" in discovery_source
    assert "private static func bookDiscoveryMetadataExtras(" in discovery_source
    assert 'extras["acquisition_provider"] = .string(candidate.provider)' in discovery_source
    assert 'extras["acquisition_candidate_id"] = .string(candidate.candidateId)' in discovery_source
    assert "discoveryState: makeBookDiscoveryState(" in template_factory_source
    assert 'payload["discovery_state"] = .object(discoveryState)' in template_factory_source
    assert 'state: [String: JSONValue] = [' in template_factory_source
    assert '"media_kind": .string("book")' in template_factory_source
    assert '"provider": .string(provider)' in template_factory_source
    assert 'named: "candidate_id"' in template_factory_source
    assert 'named: "selected_path"' in template_factory_source
    assert "static func normalizedBookMetadataExtras(_ extras: [String: JSONValue])" in drafts_source
    assert "!isSensitiveBookMetadataExtraKey(trimmedKey)" in drafts_source
    assert "private static func isSensitiveBookMetadataExtraKey(_ key: String) -> Bool" in drafts_source
    for marker in [
        '"password"',
        '"secret"',
        '"token"',
        '"authorization"',
        '"authheader"',
        '"apikey"',
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
    presentation_state_source = _source(CREATE_PRESENTATION_STATE)
    source = _source(CREATE_SOURCE_SECTION)
    youtube_source = _source(CREATE_YOUTUBE_SOURCE_CONTROLS)
    view_model_source = _source(CREATE_VIEW_MODEL)

    assert "func loadVideoDiscovery(" in view_model_source
    assert "func loadAcquisitionProviders(" in view_model_source
    assert "@Published private(set) var acquisitionProviders: [AcquisitionProviderEntry] = []" in view_model_source
    assert "@Published private(set) var acquisitionDefaultProviderIds: [String: [String]] = [:]" in view_model_source
    assert "acquisitionDefaultProviderIds = response.defaultProviderIds ?? [:]" in view_model_source
    assert 'mediaKind: "video"' in view_model_source
    assert 'provider: String = "nas_video"' in view_model_source
    assert "AppleBookCreatePresentation.isDefaultVideoDiscoveryProviderID(normalizedProvider)" in view_model_source
    assert "provider: requestProvider" in view_model_source
    assert "@Published private(set) var youtubeAcquisitionDiscovery: AcquisitionDiscoveryResponse?" in view_model_source
    assert "@Published private(set) var isLoadingYoutubeAcquisitionDiscovery = false" in view_model_source
    assert "@Published private(set) var isPreparingYoutubeAcquisitionCandidate = false" in view_model_source
    assert "let acquisitionProviders: [AcquisitionProviderEntry]" in source
    assert "let acquisitionDefaultProviderIds: [String: [String]]" in source
    assert "let youtubeAcquisitionDiscovery: AcquisitionDiscoveryResponse?" in source
    assert "let isPreparingYoutubeAcquisitionCandidate: Bool" in source
    assert "let acquisitionProvidersErrorMessage: String?" in source
    assert "let youtubeSearchUnavailableMessage: String?" in source
    assert "let isYoutubeSearchAvailable: Bool" in source
    assert "let onSearchYoutubeAcquisitionDiscovery: (String, String) -> Void" in source
    assert "let onSelectYoutubeAcquisitionCandidate: (AcquisitionCandidate) -> Void" in source
    discovery_source = _source(CREATE_DISCOVERY_PRESENTATION)
    assert "struct AppleBookCreateVideoDiscoveryAvailability" in discovery_source
    assert "static func youtubeVideoDiscoveryAvailability(" in discovery_source
    assert 'providers.first { $0.id == "youtube_search" }' in discovery_source
    assert 'providers.first { $0.id == "download_station" }' in discovery_source
    assert "let hasProviderInventory = !providers.isEmpty" in discovery_source
    assert "isYoutubeSearchAvailable: youtubeSearchProvider?.available ?? !hasProviderInventory" in discovery_source
    assert "youtubeAcquisitionDiscovery: viewModel.youtubeAcquisitionDiscovery" in view_source
    assert "acquisitionProviders: viewModel.acquisitionProviders" in view_source
    assert "acquisitionDefaultProviderIds: viewModel.acquisitionDefaultProviderIds" in view_source
    assert "isPreparingYoutubeAcquisitionCandidate: viewModel.isPreparingYoutubeAcquisitionCandidate" in view_source
    assert "youtubeSearchUnavailableMessage: videoDiscoveryAvailability.youtubeSearchUnavailableMessage" in view_source
    assert "isYoutubeSearchAvailable: videoDiscoveryAvailability.isYoutubeSearchAvailable" in view_source
    assert "downloadStationUnavailableMessage: videoDiscoveryAvailability.downloadStationUnavailableMessage" in view_source
    assert "isDownloadStationAvailable: videoDiscoveryAvailability.isDownloadStationAvailable" in view_source
    assert "var videoDiscoveryAvailability: AppleBookCreateVideoDiscoveryAvailability" in presentation_state_source
    assert "private var videoDiscoveryAvailability: AppleBookCreateVideoDiscoveryAvailability" not in view_source
    assert "candidateToken: candidateToken" in view_source
    assert "candidateToken: trimmedCandidateToken" in view_model_source
    assert "func prepareVideoDiscoveryCandidate(" in view_model_source
    assert "isPreparingYoutubeAcquisitionCandidate = true" in view_model_source
    assert "client.prepareAcquisitionArtifact(" in view_model_source
    assert "downloadStationCandidate?.candidateToken" in youtube_source
    assert 'accessibilityIdentifier("createYoutubeDownloadStationCandidate")' in youtube_source
    assert "AppleBookCreatePresentation.isDownloadStationHandoffCandidate(candidate)" in youtube_source
    assert "let discovery = await viewModel.loadVideoDiscovery(" in view_source
    assert "static func downloadStationCompletedFiles(from job: AcquisitionJobStatusResponse?) -> [String]" in discovery_source
    assert "static func downloadStationCompletedCandidate(" in discovery_source
    assert "private static func downloadStationCompletedFileHints(" in discovery_source
    assert "var hints = normalizedMetadataStrings(job.completedFiles)" in discovery_source
    assert 'for key in ["completed_file", "completed_path", "local_path", "filename"]' in discovery_source
    assert 'for key in ["completed_files", "completed_paths", "files"]' in discovery_source
    assert 'metadata["completed_file"] ?? metadata["completed_path"] ?? metadata["local_path"]' in discovery_source
    assert "AppleBookCreatePresentation.downloadStationCompletedFiles(from: job)" in view_model_source
    assert "Completed: \\(completedFiles.joined(separator: \", \"))." in view_model_source
    assert "AppleBookCreatePresentation.downloadStationCompletedFiles(from: downloadStationJob)" in youtube_source
    assert "AppleBookCreatePresentation.downloadStationCompletedCandidate(" in view_source
    assert "private func downloadStationCompletedCandidate(" not in view_source
    assert "private static func downloadStationCandidateNameSet(_ candidate: AcquisitionCandidate) -> Set<String>" in discovery_source
    assert "private static func downloadStationNameKeys(for value: String) -> [String]" in discovery_source
    assert "private static func downloadStationLastPathComponent(_ value: String) -> String" in discovery_source
    assert "private static func downloadStationFileStem(_ filename: String) -> String" in discovery_source
    assert "applyYoutubeAcquisitionDiscoveryCandidate(candidate)" in view_source
    assert "private var youtubeSearchProvider" not in view_source
    assert "private var downloadStationProvider" not in view_source
    assert "loadAcquisitionProviders(using: appState" in view_source
    assert "onSearchYoutubeAcquisitionDiscovery: searchYoutubeAcquisitionDiscovery" in view_source
    assert "onSelectYoutubeAcquisitionCandidate: applyYoutubeAcquisitionDiscoveryCandidate" in view_source
    assert "private func applyYoutubeAcquisitionDiscoveryCandidate(_ candidate: AcquisitionCandidate)" in view_source
    assert "AppleBookCreatePresentation.isYoutubeMetadataVideoDiscoveryProviderID(candidate.provider)" in view_source
    assert "AppleBookCreatePresentation.youtubeMetadataSourceURL(for: candidate)" in view_source
    assert "lookupYoutubeVideoMetadata(" in view_source
    assert "viewModel.prepareVideoDiscoveryCandidate(" in view_source
    assert "applyPreparedVideoDiscoveryCandidate(prepared, source: candidate)" in view_source
    assert "private func applyPreparedVideoDiscoveryCandidate(" in view_source
    assert "prepared.videoPath?.trimmingCharacters" in view_source
    assert "prepared.subtitlePath?.trimmingCharacters" in view_source
    assert "prepared.subtitles.first?.path.trimmingCharacters" in view_source
    assert "handleYoutubeVideoPathChange(videoPath)" in view_source

    assert "let acquisitionDiscovery: AcquisitionDiscoveryResponse?" in youtube_source
    assert "let acquisitionProviders: [AcquisitionProviderEntry]" in youtube_source
    assert "let acquisitionDefaultProviderIds: [String: [String]]" in youtube_source
    assert "let isLoadingAcquisitionDiscovery: Bool" in youtube_source
    assert "let isPreparingAcquisitionCandidate: Bool" in youtube_source
    assert "let isYoutubeSearchAvailable: Bool" in youtube_source
    assert "let youtubeSearchUnavailableMessage: String?" in youtube_source
    assert "let onSearchYoutubeAcquisitionDiscovery: (String, String) -> Void" in youtube_source
    assert "let onSelectYoutubeAcquisitionCandidate: (AcquisitionCandidate) -> Void" in youtube_source
    assert "videoDiscoveryProvider" in youtube_source
    presentation_source = _source(CREATE_PRESENTATION_HELPERS)
    assert "struct AppleBookCreateVideoDiscoveryProviderOption" in discovery_source
    assert "static func videoDiscoveryProviderOptions(" in discovery_source
    assert "defaultProviderIds: [String: [String]] = [:]" in discovery_source
    assert "defaultVideoDiscoveryProviderID" in discovery_source
    assert "isDefaultVideoDiscoveryProviderID" in discovery_source
    assert "static func defaultDiscoveryProviderID(" in discovery_source
    assert "availableOptionIds: [String]? = nil" in discovery_source
    assert "let availableOptionIdSet = Set(availableOptionIds ?? optionIds)" in discovery_source
    assert 'if mediaKind == "video", optionIdSet.contains(defaultVideoDiscoveryProviderID)' in discovery_source
    assert "let preferredOptionIdSet = availableOptionIdSet.isEmpty ? optionIdSet : availableOptionIdSet" in discovery_source
    assert "defaultableProviderIDs(" in discovery_source
    assert "explicitOnlyDefaultVideoDiscoveryProviderIDs" in discovery_source
    assert '"youtube_url"' in discovery_source
    assert "static func videoDiscoveryProviderOptions(" not in presentation_source
    assert "private static let fallbackVideoDiscoveryProviders" in discovery_source
    assert 'AppleBookCreateVideoDiscoveryProviderOption(id: "nas_video", label: "NAS videos", available: true)' in discovery_source
    assert 'AppleBookCreateVideoDiscoveryProviderOption(id: "manual_downloads", label: "Manual downloads", available: true)' in discovery_source
    assert 'AppleBookCreateVideoDiscoveryProviderOption(id: "youtube_url", label: "YouTube URL", available: true)' in discovery_source
    assert 'AppleBookCreateVideoDiscoveryProviderOption(id: "youtube_search", label: "YouTube search", available: true)' in discovery_source
    assert 'AppleBookCreateVideoDiscoveryProviderOption(id: "newznab_torznab", label: "Indexers", available: true)' in discovery_source
    assert 'label: "Default sources"' in discovery_source
    assert "ForEach(videoDiscoveryProviderOptions)" in youtube_source
    assert "AppleBookCreatePresentation.videoDiscoveryProviderOptions(" in youtube_source
    assert "from: acquisitionProviders" in youtube_source
    assert "defaultProviderIds: acquisitionDefaultProviderIds" in youtube_source
    assert "AppleBookCreatePresentation.defaultDiscoveryProviderID(" in youtube_source
    assert "defaultProviderIds: acquisitionDefaultProviderIds" in youtube_source
    assert "optionIds: videoDiscoveryProviderOptions.map(\\.id)" in youtube_source
    assert "availableOptionIds: videoDiscoveryProviderOptions.filter(\\.available).map(\\.id)" in youtube_source
    assert "@State private var hasUserSelectedVideoDiscoveryProvider = false" in youtube_source
    assert "@State private var didApplyBackendVideoDiscoveryDefault = false" in youtube_source
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
    assert "provider.mediaKinds.contains(\"video\")" in discovery_source
    assert 'return discoveryMediaKinds.contains("video")' in discovery_source
    assert "videoDiscoveryCapabilities.contains($0)" in discovery_source
    assert "private static func videoDiscoveryProviderRank(" in discovery_source
    assert "private static func videoDiscoveryProviderLabel(" in discovery_source
    assert "static func videoDiscoveryProviderFallbackLabel(for providerID: String)" in discovery_source
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
    assert "static func videoDiscoveryProviderUnavailableMessage(" in discovery_source
    assert 'if provider.id == "youtube_search"' in discovery_source
    assert 'if provider.id == "newznab_torznab"' in discovery_source
    assert "|| !isSelectedVideoDiscoveryProviderAvailable" in youtube_source
    assert "AppleBookCreatePresentation.videoDiscoveryCandidates(" in youtube_source
    assert "AppleBookCreatePresentation.videoDiscoveryQueryPlaceholder(providerID: videoDiscoveryProvider)" in youtube_source
    assert "AppleBookCreatePresentation.noVideoDiscoveryCandidatesMessage(providerID: videoDiscoveryProvider)" in youtube_source
    assert "AppleBookCreatePresentation.youtubeVideoLabel(video)" in youtube_source
    assert "AppleBookCreatePresentation.youtubeSubtitleLabel(subtitle)" in youtube_source
    assert "AppleBookCreatePresentation.filenameFromPath" in youtube_source
    assert "AppleBookCreatePresentation.videoDiscoveryCandidateDetail(candidate)" in youtube_source
    assert 'accessibilityIdentifier("createYoutubeDiscoveryPrepareProgress")' in youtube_source
    assert ".disabled(isPreparingAcquisitionCandidate)" in youtube_source
    assert "static func videoDiscoveryCandidates(" in discovery_source
    assert "static func isYoutubeMetadataVideoDiscoveryProviderID(" in discovery_source
    assert "static func youtubeMetadataSourceURL(for candidate: AcquisitionCandidate)" in discovery_source
    assert 'normalized == "youtube_search" || normalized == "youtube_url"' in discovery_source
    assert "static func videoDiscoveryQueryPlaceholder(" in discovery_source
    assert "static func noVideoDiscoveryCandidatesMessage(" in discovery_source
    assert "No default video sources matched this discovery search." in discovery_source
    assert "No YouTube URL metadata matched this discovery search." in discovery_source
    assert "static func youtubeVideoLabel(" in discovery_source
    assert "static func youtubeSubtitleLabel(" in discovery_source
    assert "static func filenameFromPath(" in discovery_source
    assert "static func videoDiscoveryCandidateDetail(" in discovery_source
    assert "static func isDownloadStationHandoffCandidate(_ candidate: AcquisitionCandidate) -> Bool" in discovery_source
    assert 'candidate.metadata?["handoff_provider"]?.stringValue?' in discovery_source
    assert '.localizedCaseInsensitiveCompare("download_station") == .orderedSame' in discovery_source
    assert 'candidate.metadata?["has_download_url"]?.stringValue?' in discovery_source
    assert '.localizedCaseInsensitiveCompare("true") == .orderedSame' in discovery_source
    assert "Download Station handoff" in discovery_source
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
        assert identifier in youtube_source


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
    layout_source = _source(CREATE_LAYOUT)
    settings_content_source = _source(CREATE_SETTINGS_CONTENT)
    basic_source = _source(CREATE_BASIC_SECTIONS)
    controls_source = _source(CREATE_SOURCE_CONTROLS)
    view_model_source = _source(CREATE_VIEW_MODEL)
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
    assert "showsNarrateRangeControls: false" in source

    assert "private var narrateChapterSettingsControls: some View" in basic_source
    assert "struct AppleBookCreateNarrateChapterRangeControls: View" in controls_source
    assert "Button(action: onLoadNarrateChapters)" in controls_source
    assert 'accessibilityIdentifier("createNarrateLoadChaptersButton")' in controls_source
    assert "private var hasNarrateSource: Bool" in controls_source
    assert "private var isLoadChaptersDisabled: Bool" in controls_source
    assert 'Text("Choose an EPUB source before loading chapters.")' in controls_source
    assert 'Text("No chapter data loaded.")' in controls_source
    assert 'accessibilityIdentifier("createNarrateChaptersMessage")' in controls_source
    assert 'accessibilityIdentifier("createNarrateStartChapterPicker")' in controls_source
    assert 'accessibilityIdentifier("createNarrateEndChapterPicker")' in controls_source
    assert 'Text("Same as start").tag("")' in controls_source
    assert ".disabled(selectedNarrateStartChapterID.isEmpty)" in controls_source
    assert 'accessibilityIdentifier("createNarrateChapterRangeSummary")' in controls_source
    assert "applyNarrateChapterRangeSelection" in controls_source
    assert "private static func shouldSkipNarrateChapterLookup(for inputFile: String) -> Bool" in view_model_source
    assert "Generated sources use manual sentence ranges; chapter loading is skipped." in view_model_source
    assert 'normalized.hasPrefix("runtime/generated/")' in view_model_source
    assert "client.fetchBookContentIndex(inputFile: trimmedInput)" in view_model_source


def test_apple_create_prefers_latest_server_epub_for_narration_source() -> None:
    source = _source(CREATE_SOURCE_SELECTION)
    controls_source = _source(CREATE_SOURCE_CONTROLS)
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
    assert "AppleBookCreatePresentation.pipelineEbookDetailLabel(selectedSourceEntry)" in controls_source
    assert "AppleBookCreatePresentation.pipelineEbookEntries(from: pipelineFiles)" in controls_source
    assert "private var serverEbookPicker: some View" in controls_source
    assert ".disabled(isLoadingPipelineFiles)" in controls_source
    assert ".disabled(narrateServerEbooks.isEmpty || isLoadingPipelineFiles)" not in controls_source
    assert "private var shouldShowServerEbooksSummary: Bool" in controls_source
    assert "private var serverEbooksSummaryMessage: String" in controls_source
    assert 'accessibilityIdentifier("createNarrateServerEbooksSummary")' in controls_source
    assert 'accessibilityIdentifier("createNarrateSelectedEbookDetail")' in controls_source
    assert "let selectedSourceEntry: PipelineFileEntry?" in controls_source
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

    assert "creationMode == .generatedBook || creationMode == .narrateEbook" in basic_source
    assert 'Section(creationMode == .generatedBook ? "Source Book" : "Metadata")' in basic_source
    assert 'creationMode == .generatedBook ? "Source title" : "Title"' in basic_source
    assert 'creationMode == .generatedBook ? "Source author" : "Author"' in basic_source
    assert 'creationMode == .generatedBook ? "Source genre" : "Genre"' in basic_source
    assert 'creationMode == .generatedBook ? "Source summary" : "Summary"' in basic_source
    assert '"createGeneratedSourceBookTitleField"' in basic_source
    assert '"createGeneratedSourceBookAuthorField"' in basic_source
    assert '"createGeneratedSourceBookGenreField"' in basic_source
    assert "sourceBookTitle: sourceBookTitle" in source
    assert "sourceBookAuthor: sourceBookAuthor" in source
    assert "sourceBookGenre: sourceBookGenre" in source
    assert "sourceBookSummary: sourceBookSummary" in source

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
    view_source = _source(CREATE_VIEW)

    assert "embeddedYoutubeSubtitleControls" in youtube_source
    assert 'buttonIdentifier: "createYoutubeInspectEmbeddedSubtitlesButton"' in youtube_source
    assert 'accessibilityIdentifier("createYoutubeEmbeddedSubtitleLanguagesField")' in youtube_source
    assert 'buttonIdentifier: "createYoutubeExtractEmbeddedSubtitlesButton"' in youtube_source
    assert 'accessibilityIdentifier("createYoutubeEmbeddedSubtitlesMessage")' in youtube_source
    assert 'accessibilityIdentifier("createYoutubeEmbeddedSubtitlesError")' in youtube_source
    assert "youtubeInlineSubtitleStreams: viewModel.youtubeInlineSubtitleStreams" in view_source
    assert "onInspectYoutubeSubtitles: inspectYoutubeSubtitles" in view_source
    assert "onExtractYoutubeSubtitles: extractYoutubeSubtitles" in view_source


def test_subtitle_create_exposes_editable_metadata_lookup_name() -> None:
    metadata_sections_source = _source(CREATE_MEDIA_METADATA_SECTIONS)
    metadata_controls_source = _source(CREATE_MEDIA_METADATA_CONTROLS)
    view_source = _source(CREATE_VIEW)

    assert "AppleBookCreateSubtitleMetadataControls" in metadata_sections_source
    assert "@Binding var lookupSourceName: String" in metadata_controls_source
    assert 'TextField("Lookup filename", text: $lookupSourceName)' in metadata_controls_source
    assert 'accessibilityIdentifier("createSubtitleMetadataLookupField")' in metadata_controls_source
    assert "subtitleMetadataLookupSourceName" in view_source
    assert "sourceName: subtitleMetadataLookupSourceName" in view_source


def test_apple_create_exposes_metadata_cache_clear_controls() -> None:
    metadata_controls_source = _source(CREATE_MEDIA_METADATA_CONTROLS)
    view_source = _source(CREATE_VIEW)

    assert "let isClearingCache: Bool" in metadata_controls_source
    assert "let onClearCache: () -> Void" in metadata_controls_source
    assert 'accessibilityIdentifier: "createSubtitleMetadataClearCacheButton"' in metadata_controls_source
    assert "viewModel.isClearingSubtitleTvMetadataCache" in view_source
    assert "clearSubtitleTvMetadataCache(" in view_source
    assert "query: subtitleMetadataLookupSourceName" in view_source

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
    assert "clearYoutubeTvMetadataCache(" in view_source
    assert "query: youtubeMetadataTvSourceName" in view_source
    assert "clearYoutubeVideoMetadataCache(" in view_source
    assert "query: youtubeMetadataVideoSourceName" in view_source


def test_apple_create_exposes_tv_metadata_artwork_and_ids() -> None:
    metadata_controls_source = _source(CREATE_MEDIA_METADATA_CONTROLS)
    metadata_source = _source(CREATE_METADATA_VIEWS)
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
    assert "private func youtubeMetadataNumberBinding(section: String, key: String)" in view_source
    assert "private func youtubeMetadataNestedTextBinding(section: String, nestedKey: String, key: String)" in view_source
    assert "private func subtitleMetadataNestedTextBinding(section: String, nestedKey: String, key: String)" in view_source
    assert "updateYoutubeMediaMetadataNestedText(" in view_source
    assert "updateSubtitleMediaMetadataNestedText(" in view_source
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
    assert "viewModel.applySubtitleMediaMetadataJSONText()" in view_source
    assert "viewModel.applyYoutubeMediaMetadataJSONText()" in view_source
    assert "viewModel.syncSubtitleMediaMetadataJSONText()" in view_source
    assert "viewModel.syncYoutubeMediaMetadataJSONText()" in view_source
    assert "func applySubtitleMediaMetadataJSONText()" in view_model_metadata_source
    assert "func applyYoutubeMediaMetadataJSONText()" in view_model_metadata_source
    assert "AppleBookCreateMetadataJSON.parseObject(" in view_model_metadata_source
    assert "private static func parseMetadataJSONObject" not in view_model_source
    assert "JSONDecoder().decode([String: JSONValue].self" in metadata_json_source
    assert "AppleBookCreateMetadataJSON.swift in Sources" in project
    assert project.count("AppleBookCreateMetadataJSON.swift in Sources") == 4
    assert 'accessibilityIdentifier("createYoutubeMetadataTmdbIdField")' in metadata_controls_source
    assert 'accessibilityIdentifier("createYoutubeMetadataImdbIdField")' in metadata_controls_source
