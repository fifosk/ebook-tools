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
    assert "private func completeSubmission(_ jobId: String?) async" in source
    assert source.count("await completeSubmission(jobId)") == 4
    assert source.count("onJobSubmitted(jobId)") == 1


def test_apple_create_can_load_and_apply_web_creation_templates() -> None:
    view_source = _source(CREATE_VIEW)
    view_model_source = _source(CREATE_VIEW_MODEL)
    status_views_source = _source(CREATE_STATUS_VIEWS)
    api_models_source = _source(PIPELINE_CREATION_API_MODELS)
    api_client_source = _source(API_CLIENT_CREATION)

    assert "struct CreationTemplateListResponse: Decodable, Equatable" in api_models_source
    assert "struct CreationTemplateEntry: Decodable, Equatable, Identifiable" in api_models_source
    assert "case createdAt = \"created_at\"" in api_models_source
    assert "case updatedAt = \"updated_at\"" in api_models_source
    assert "var normalizedMode: String" in api_models_source
    assert "var displayName: String" in api_models_source

    assert "func fetchCreationTemplates(mode: String? = nil)" in api_client_source
    assert "AppleCreateRuntimeContract.templateListPath" in api_client_source
    assert "static func templatePath(_ encodedTemplateId: String)" in api_client_source
    assert "func deleteCreationTemplate(templateId: String) async throws" in api_client_source
    assert "AppleCreateRuntimeContract.templatePath(encoded)" in api_client_source
    assert 'method: "DELETE"' in api_client_source
    assert 'URLQueryItem(name: "mode", value: mode)' in api_client_source

    assert "@Published private(set) var creationTemplates: [CreationTemplateEntry] = []" in view_model_source
    assert "@Published private(set) var isLoadingCreationTemplates = false" in view_model_source
    assert "@Published private(set) var isDeletingCreationTemplate = false" in view_model_source
    assert "@Published private(set) var creationTemplatesErrorMessage: String?" in view_model_source
    assert "@Published var creationTemplateMessage: String?" in view_model_source
    assert "func loadCreationTemplates(" in view_model_source
    assert "client.fetchCreationTemplates()" in view_model_source
    assert "func deleteCreationTemplate(" in view_model_source
    assert "client.deleteCreationTemplate(templateId: trimmedID)" in view_model_source
    assert "creationTemplates.removeAll { $0.id == trimmedID }" in view_model_source

    assert "struct AppleBookCreateTemplateSection: View" in status_views_source
    for identifier in [
        "createBookTemplatePicker",
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
    assert "private func applySelectedCreationTemplate()" in view_source
    assert "private func requestDeleteSelectedCreationTemplate()" in view_source
    assert "private func deleteCreationTemplate(_ template: CreationTemplateEntry) async" in view_source
    assert "creationTemplatePendingDelete = template" in view_source
    assert "await viewModel.deleteCreationTemplate(" in view_source
    assert "private func applyCreationTemplate(_ template: CreationTemplateEntry)" in view_source
    assert 'template.normalizedMode == "subtitle_job"' in view_source
    assert 'template.normalizedMode == "youtube_dub"' in view_source
    assert "private func applySubtitleCreationTemplate(" in view_source
    assert "private func applyYoutubeDubCreationTemplate(" in view_source
    assert "private func templateFormState(from template: CreationTemplateEntry)" in view_source
    assert "private func templateSettings(from template: CreationTemplateEntry)" in view_source
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
        assert web_template_key in view_source


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
    assert "AppleBookCreatePresentationHelpers.swift" in payload_script


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
            rf"private func {function_name}\(force: Bool = false\) async \{{(?P<body>.*?)\n    \}}",
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
    project = _source(XCODE_PROJECT)

    assert "struct AppleBookCreateOutputSection: View" in output_source
    assert 'Section("Output")' in output_source
    assert "AppleBookCreateSubtitleOutputControls(" in output_source
    assert "AppleBookCreateYoutubeOutputControls(" in output_source
    assert "AppleBookCreateGeneratedOutputControls(" in output_source
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
    assert 'accessibilityIdentifier("createBookImagePromptPipelinePicker")' not in generated_output_source
    assert 'accessibilityIdentifier("createBookLookupCacheBatchSizeControl")' in generated_output_source
    assert "struct AppleBookCreateSubtitleOutputControls: View" not in output_source
    assert "struct AppleBookCreateYoutubeOutputControls: View" not in output_source
    assert "struct AppleBookCreateGeneratedOutputControls: View" not in output_source
    assert "struct AppleBookCreateSubtitleOutputControls: View" not in narration_source
    assert "struct AppleBookCreateYoutubeOutputControls: View" not in narration_source
    assert "struct AppleBookCreateGeneratedOutputControls: View" not in narration_source
    assert "AppleBookCreateOutputSection(" in view_source
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
    assert "static func webCreateHandoffURL(apiBaseURL: URL?, mode: AppleCreateMode)" in routing_source
    assert 'return "books:create"' in routing_source
    assert 'return "pipeline:source"' in routing_source
    assert 'return "subtitles:youtube-dub"' in routing_source
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
    assert "static func subtitleSourceDefaults(" in source_selection
    assert "static func preferredYoutubeSelection(from library: YoutubeNasLibraryResponse?)" in source_selection
    assert "sortedYoutubeVideosForDefaultSelection(library?.videos ?? [])" in source_selection
    assert "private static func sortedYoutubeVideosForDefaultSelection(" in source_selection
    assert "static func youtubeSelection(" in source_selection
    assert "static func youtubeSourceDefaults(" in source_selection
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
    assert "AppleBookCreatePresentation.subtitleSourceDefaults(" in view_source
    assert "AppleBookCreatePresentation.youtubeSourceDefaults(" in view_source
    assert "let scopeChanged = youtubeSelectionStorageScope != youtubeLibraryLoadKey" not in view_source


def test_create_storage_keys_are_split_from_view_and_target_wired() -> None:
    storage_source = _source(CREATE_STORAGE_KEYS)
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
    assert "AppleBookCreateStorageKeys.youtubeLibraryLoad(" in view_source
    assert "AppleBookCreateStorageKeys.loadScope(" in view_source
    assert "configuration.apiBaseURL.absoluteString" not in view_source
    assert "AppleBookCreateStorageKeys.swift in Sources" in project
    assert project.count("AppleBookCreateStorageKeys.swift in Sources") == 4
    assert "AppleBookCreateStorageKeys.swift" in payload_script


def test_create_preferences_are_split_from_view_and_target_wired() -> None:
    preferences_source = _source(CREATE_PREFERENCES)
    view_source = _source(CREATE_VIEW)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "enum AppleBookCreatePreferences" in preferences_source
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
    assert "AppleBookCreatePreferences.storedYoutubeSelectionPath(" in view_source
    assert "AppleBookCreatePreferences.persistYoutubeSelectionPath(" in view_source
    assert "AppleBookCreatePreferences.storedYoutubeBaseDir(" in view_source
    assert "AppleBookCreatePreferences.persistYoutubeBaseDir(" in view_source
    assert "AppleBookCreatePreferences.storedSubtitleShowOriginal(" in view_source
    assert "AppleBookCreatePreferences.persistSubtitleShowOriginal(" in view_source
    assert "AppleBookCreatePreferences.storedLanguagePreferences(" in view_source
    assert "AppleBookCreatePreferences.persistLanguagePreferences(" in view_source
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
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "enum AppleBookCreateMetadataSources" in metadata_source
    assert "static func youtubeTvSourceName(subtitlePath: String, videoPath: String)" in metadata_source
    assert "static func youtubeVideoSourceName(videoPath: String)" in metadata_source
    assert "static func subtitleSourceName(" in metadata_source
    assert "sources: [SubtitleSourceEntry]" in metadata_source
    assert "URL(fileURLWithPath: normalizedPath).lastPathComponent" in metadata_source
    assert "AppleBookCreateMetadataSources.youtubeTvSourceName(" in view_source
    assert "AppleBookCreateMetadataSources.youtubeVideoSourceName(" in view_source
    assert "AppleBookCreateMetadataSources.subtitleSourceName(" in view_source
    assert "private var defaultSubtitleMetadataLookupSourceName" not in view_source
    assert "URL(fileURLWithPath: selectedPath).lastPathComponent" not in view_source
    assert "AppleBookCreateMetadataSources.swift in Sources" in project
    assert project.count("AppleBookCreateMetadataSources.swift in Sources") == 4
    assert "AppleBookCreateMetadataSources.swift" in payload_script


def test_create_file_import_is_split_from_view_and_target_wired() -> None:
    import_source = _source(CREATE_FILE_IMPORT)
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
    assert "AppleBookCreateFileImport.narrateImportSelection(" in view_source
    assert "AppleBookCreateFileImport.subtitleImportSelection(from: urls)" in view_source
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
    assert "AppleBookCreateFileImporterModifier.swift in Sources" in project
    assert project.count("AppleBookCreateFileImporterModifier.swift in Sources") == 4
    assert "AppleBookCreateFileImport.swift" in payload_script


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
    basic_source = _source(CREATE_BASIC_SECTIONS)
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
    assert "private var createSetupSections: some View" in source
    assert "private var createSettingsSections: some View" in source
    assert "private var jobTypeSection: some View" in source
    assert "private var jobSettingsSection: some View" in source

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
    assert "jobTypeSection" in settings_sections.group("body")
    assert "promptSection" in settings_sections.group("body")
    assert "metadataSection" in settings_sections.group("body")
    assert "jobSettingsSection" in settings_sections.group("body")
    assert "narrationSection" in settings_sections.group("body")
    assert "outputSection" in settings_sections.group("body")
    assert "submitSection" in settings_sections.group("body")
    assert 'Section("Job Type")' in basic_source
    assert 'Picker("Job type", selection: $creationMode)' in basic_source
    assert '.accessibilityIdentifier("createJobTypePicker")' in basic_source

    assert "AppleBookCreatePromptSection(" in source
    assert "AppleBookCreateJobSettingsSection(" in source
    assert "sentenceCountControl" in basic_source
    assert "narrateChapterSettingsControls" in basic_source
    assert 'accessibilityIdentifier("createNarrateOutputPathField")' in basic_source
    assert 'accessibilityIdentifier("createNarrateStartSentenceField")' in basic_source
    assert 'accessibilityIdentifier("createNarrateEndSentenceField")' in basic_source
    assert "showsNarrateRangeControls: false" in source

    assert "private var narrateChapterSettingsControls: some View" in basic_source
    assert "Button(action: onLoadNarrateChapters)" in basic_source
    assert 'accessibilityIdentifier("createNarrateLoadChaptersButton")' in basic_source
    assert 'accessibilityIdentifier("createNarrateStartChapterPicker")' in basic_source
    assert 'accessibilityIdentifier("createNarrateEndChapterPicker")' in basic_source
    assert "applyNarrateChapterRangeSelection" in source


def test_apple_create_prefers_latest_server_epub_for_narration_source() -> None:
    source = _source(CREATE_SOURCE_SELECTION)
    controls_source = _source(CREATE_SOURCE_CONTROLS)

    assert "static func preferredPipelineEbook(from files: PipelineFileBrowserResponse?) -> PipelineFileEntry?" in source
    assert "static func pipelineEbookPickerLabel(_ entry: PipelineFileEntry) -> String" in source
    assert "pickerMetadataParts(" in source
    assert "formatPickerSize(" in source
    assert "formatPickerModifiedDate(" in source
    assert "AppleBookCreatePresentation.pipelineEbookPickerLabel(entry)" in controls_source
    assert "files?.ebooks.filter({ $0.type == \"file\" })" in source
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
    assert "sourceBookSummary: bookSummary" in source

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

    assert handle_created
    assert open_created
    assert focus_created
    assert navigate_job

    for body in (handle_created.group("body"), open_created.group("body")):
        assert "activeSection = .jobs" in body
        assert "jobsAutoPlay = false" in body
        assert "jobsPlaybackMode = .resume" in body
        assert "focusCreatedJob(jobId)" in body

    assert "await jobsViewModel.load(using: appState)" in focus_created.group("body")
    assert "navigateToJob(job, autoPlay: false)" in focus_created.group("body")
    assert "jobsViewModel.startAutoRefresh(using: appState)" in focus_created.group("body")
    assert "jobsViewModel.activeFilter = jobsViewModel.jobCategory(for: job)" in navigate_job.group("body")


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
