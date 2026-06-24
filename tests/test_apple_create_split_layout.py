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
CREATE_SECTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateSections.swift"
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
CREATE_VIEW_MODEL = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateViewModel.swift"
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
CREATE_MODELS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateModels.swift"
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
CREATE_METADATA_VIEWS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateMetadataViews.swift"
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
CREATE_MEDIA_METADATA_SECTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateMediaMetadataSections.swift"
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


def test_create_view_uses_shell_owned_mode_binding() -> None:
    source = _source(CREATE_VIEW)

    assert "@Binding var creationMode: AppleCreateMode" in source
    assert "@State private var creationMode = AppleCreateMode.generatedBook" not in source
    assert "showsInlineJobTypePicker: Bool" in source
    assert "showsJobTypePicker: false" in source
    assert "@Environment(\\.horizontalSizeClass) private var horizontalSizeClass" in source
    assert "private var usesRegularWidthCreateLayout: Bool" in source
    assert "horizontalSizeClass == .regular" in source


def test_create_models_are_split_from_presentation_and_target_wired() -> None:
    models_source = _source(CREATE_MODELS)
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
    assert "enum AppleCreateMode: String" in models_source
    assert "enum AppleBookCreatePresentation" not in models_source
    assert "enum AppleBookCreatePresentation" in support_source
    assert "AppleBookCreateModels.swift in Sources" in project
    assert project.count("AppleBookCreateModels.swift in Sources") == 4


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
    sections_source = _source(CREATE_SECTIONS)
    project = _source(XCODE_PROJECT)

    assert "struct AppleBookCreateAdvancedMetadataJSONEditor: View" in metadata_source
    assert "struct AppleBookCreateMetadataArtworkPreview: View" in metadata_source
    assert "struct AppleBookCreateAdvancedMetadataJSONEditor: View" not in sections_source
    assert "struct AppleBookCreateMetadataArtworkPreview: View" not in sections_source
    assert "AppleBookCreateAdvancedMetadataJSONEditor(" in sections_source
    assert "AppleBookCreateMetadataArtworkPreview(" in sections_source
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


def test_create_basic_sections_are_split_from_create_view_and_target_wired() -> None:
    basic_source = _source(CREATE_BASIC_SECTIONS)
    view_source = _source(CREATE_VIEW)
    project = _source(XCODE_PROJECT)

    assert "struct AppleBookCreatePromptSection: View" in basic_source
    assert "struct AppleBookCreateMetadataSection: View" in basic_source
    assert "struct AppleBookCreateJobTypeSection: View" in basic_source
    assert "struct AppleBookCreateJobSettingsSection: View" in basic_source
    assert 'accessibilityIdentifier("createBookTopicField")' in basic_source
    assert 'accessibilityIdentifier("createNarrateOutputPathField")' in basic_source
    assert "AppleBookCreatePromptSection(" in view_source
    assert "AppleBookCreateMetadataSection(" in view_source
    assert "AppleBookCreateJobTypeSection(" in view_source
    assert "AppleBookCreateJobSettingsSection(" in view_source
    assert "AppleBookCreateBasicSections.swift in Sources" in project
    assert project.count("AppleBookCreateBasicSections.swift in Sources") == 4


def test_create_output_section_is_split_from_create_view_and_target_wired() -> None:
    output_source = _source(CREATE_OUTPUT_SECTION)
    view_source = _source(CREATE_VIEW)
    project = _source(XCODE_PROJECT)

    assert "struct AppleBookCreateOutputSection: View" in output_source
    assert 'Section("Output")' in output_source
    assert "AppleBookCreateSubtitleOutputControls(" in output_source
    assert "AppleBookCreateYoutubeOutputControls(" in output_source
    assert "AppleBookCreateGeneratedOutputControls(" in output_source
    assert "AppleBookCreateOutputSection(" in view_source
    assert "AppleBookCreateSubtitleOutputControls(" not in view_source
    assert "AppleBookCreateYoutubeOutputControls(" not in view_source
    assert "AppleBookCreateGeneratedOutputControls(" not in view_source
    assert "AppleBookCreateOutputSection.swift in Sources" in project
    assert project.count("AppleBookCreateOutputSection.swift in Sources") == 4


def test_create_media_metadata_sections_are_split_from_create_view_and_target_wired() -> None:
    metadata_sections_source = _source(CREATE_MEDIA_METADATA_SECTIONS)
    view_source = _source(CREATE_VIEW)
    project = _source(XCODE_PROJECT)

    assert "struct AppleBookCreateYoutubeMetadataSection: View" in metadata_sections_source
    assert "struct AppleBookCreateSubtitleMetadataSection: View" in metadata_sections_source
    assert "AppleBookCreateYoutubeMetadataControls(" in metadata_sections_source
    assert "AppleBookCreateSubtitleMetadataControls(" in metadata_sections_source
    assert "AppleBookCreateYoutubeMetadataSection(" in view_source
    assert "AppleBookCreateSubtitleMetadataSection(" in view_source
    assert "AppleBookCreateYoutubeMetadataControls(" not in view_source
    assert "AppleBookCreateSubtitleMetadataControls(" not in view_source
    assert "AppleBookCreateMediaMetadataSections.swift in Sources" in project
    assert project.count("AppleBookCreateMediaMetadataSections.swift in Sources") == 4


def test_create_payload_factory_is_split_from_view_model_and_target_wired() -> None:
    factory_source = _source(CREATE_PAYLOAD_FACTORY)
    view_model_source = _source(CREATE_VIEW_MODEL)
    project = _source(XCODE_PROJECT)

    assert "enum AppleBookCreatePayloadFactory" in factory_source
    assert "static func makeSubmission(from draft: AppleBookCreateDraft)" in factory_source
    assert "static func makePipelineSubmission(from draft: AppleNarrateEbookDraft)" in factory_source
    assert "static func makeSubtitlePayload(from draft: AppleSubtitleJobDraft)" in factory_source
    assert "static func makeYoutubeDubPayload(from draft: AppleYoutubeDubDraft)" in factory_source
    assert "AppleBookCreatePayloadFactory.makeSubmission(from: draft)" in view_model_source
    assert "AppleBookCreatePayloadFactory.makePipelineSubmission(from: effectiveDraft)" in view_model_source
    assert "AppleBookCreatePayloadFactory.makeSubtitlePayload(from: draft)" in view_model_source
    assert "AppleBookCreatePayloadFactory.makeYoutubeDubPayload(from: draft)" in view_model_source
    assert "private static func makeSubmission" not in view_model_source
    assert "private static func makePipelineSubmission(from draft: AppleNarrateEbookDraft)" not in view_model_source
    assert "private static func makeSubtitlePayload" not in view_model_source
    assert "private static func makeYoutubeDubPayload" not in view_model_source
    assert "AppleBookCreatePayloadFactory.swift in Sources" in project
    assert project.count("AppleBookCreatePayloadFactory.swift in Sources") == 4


def test_create_routing_is_split_from_support_and_target_wired() -> None:
    routing_source = _source(CREATE_ROUTING)
    support_source = _source(CREATE_SUPPORT)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "extension AppleBookCreatePresentation" in routing_source
    assert "static func availableCreateModes(isTV: Bool)" in routing_source
    assert "static func webCreateViewID(for mode: AppleCreateMode)" in routing_source
    assert "static func webCreateHandoffURL(apiBaseURL: URL?, mode: AppleCreateMode)" in routing_source
    assert 'return "books:create"' in routing_source
    assert 'return "pipeline:source"' in routing_source
    assert 'return "subtitles:youtube-dub"' in routing_source
    assert "static func availableCreateModes" not in support_source
    assert "static func webCreateViewID" not in support_source
    assert "static func webCreateHandoffURL" not in support_source
    assert "AppleBookCreateRouting.swift in Sources" in project
    assert project.count("AppleBookCreateRouting.swift in Sources") == 4
    assert "AppleBookCreateRouting.swift" in payload_script


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
    support_source = _source(CREATE_SUPPORT)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "extension AppleBookCreatePresentation" in language_source
    assert "static func availableInputLanguages(" in language_source
    assert "static func availableTargetLanguages(" in language_source
    assert "static func availableVoices(" in language_source
    assert "static func voiceInventoryOptions(" in language_source
    assert "static func sampleSentence(language: String, fallbackLabel: String)" in language_source
    assert "static func voicePreviewKey(language: String)" in language_source
    assert "AppleBookCreateLanguage.options(from: supported)" in language_source
    assert "static func availableInputLanguages(" not in support_source
    assert "static func availableTargetLanguages(" not in support_source
    assert "static func availableVoices(" not in support_source
    assert "static func voiceInventoryOptions(" not in support_source
    assert "AppleBookCreateLanguageOptions.swift in Sources" in project
    assert project.count("AppleBookCreateLanguageOptions.swift in Sources") == 4
    assert "AppleBookCreateLanguageOptions.swift" in payload_script


def test_create_source_selection_is_split_from_support_and_target_wired() -> None:
    source_selection = _source(CREATE_SOURCE_SELECTION)
    support_source = _source(CREATE_SUPPORT)
    project = _source(XCODE_PROJECT)
    payload_script = _source(APPLE_CREATION_PAYLOADS_SCRIPT)

    assert "extension AppleBookCreatePresentation" in source_selection
    assert "static func preferredPipelineEbook(from files: PipelineFileBrowserResponse?) -> PipelineFileEntry?" in source_selection
    assert "static func preferredSubtitleSource(from response: SubtitleSourceListResponse?)" in source_selection
    assert "static func preferredYoutubeSelection(from library: YoutubeNasLibraryResponse?)" in source_selection
    assert "static func youtubeSelection(" in source_selection
    assert "static func youtubeLibraryCacheKey(baseKey: String, baseDir: String)" in source_selection
    assert "static func subtitleShowOriginalPreferenceKey(baseKey: String)" in source_selection
    assert "private static let subtitleJobSourceFormats" not in support_source
    assert "static func preferredPipelineEbook" not in support_source
    assert "static func preferredSubtitleSource" not in support_source
    assert "AppleBookCreateSourceSelection.swift in Sources" in project
    assert project.count("AppleBookCreateSourceSelection.swift in Sources") == 4
    assert "AppleBookCreateSourceSelection.swift" in payload_script


def test_source_section_can_move_job_type_picker_out_of_detail_form() -> None:
    source = _source(CREATE_SECTIONS)

    assert "let showsJobTypePicker: Bool" in source
    assert "let showsNarrateRangeControls: Bool" in source
    assert "if showsJobTypePicker || creationMode != .generatedBook" in source
    assert 'Picker("Job type", selection: $creationMode)' in source
    assert '.accessibilityIdentifier("createJobTypePicker")' in source
    assert "if showsNarrateRangeControls" in source


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
    basic_source = _source(CREATE_BASIC_SECTIONS)

    assert "regularWidthCreateLayout" in source
    assert 'accessibilityIdentifier: "appleBookCreateSetupPane"' in source
    assert 'accessibilityIdentifier: "appleBookCreateSettingsPane"' in source
    assert "private static let setupPaneMinWidth: CGFloat = 220" in source
    assert "private static let setupPaneIdealWidth: CGFloat = 260" in source
    assert "private static let setupPaneMaxWidth: CGFloat = 280" in source
    assert "private static let settingsPaneMinWidth: CGFloat = 480" in source
    assert "private static let settingsPaneIdealWidth: CGFloat = 680" in source
    assert "minWidth: Self.setupPaneMinWidth" in source
    assert "idealWidth: Self.setupPaneIdealWidth" in source
    assert "maxWidth: Self.setupPaneMaxWidth" in source
    assert ".layoutPriority(0)" in source
    assert 'createSettingsForm(accessibilityIdentifier: "appleBookCreateSettingsPane")' in source
    assert "minWidth: Self.settingsPaneMinWidth" in source
    assert "idealWidth: Self.settingsPaneIdealWidth" in source
    assert ".layoutPriority(2)" in source
    assert "private func createSettingsForm<Content: View>" in source
    assert "Form {\n            content()\n        }" in source
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

    assert "static func preferredPipelineEbook(from files: PipelineFileBrowserResponse?) -> PipelineFileEntry?" in source
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
    source = _source(CREATE_SECTIONS)

    assert "#if os(tvOS)" in source
    assert 'Picker("Input", selection: $inputLanguage)' in source
    assert "AppleBookCreateLanguageSelector(" in source
    assert 'accessibilityIdentifier: "createBookInputLanguagePicker"' in source
    assert 'accessibilityIdentifier: "createBookTargetLanguagePicker"' in source
    assert "#if !os(tvOS)" in source
    assert "private struct AppleBookCreateLanguageSelector: View" in source
    assert "@State private var searchText = \"\"" in source
    assert "private var filteredOptions: [AppleBookCreateLanguage]" in source
    assert '.searchable(text: $searchText, prompt: "Search Languages")' in source
    assert '.sheet(item: $selectedLanguage)' in source
    assert '.accessibilityIdentifier("\\(accessibilityIdentifier).\\(language.id)")' in source
    assert 'Text("\\(options.count) available")' in source
    assert '.accessibilityValue("\\(selection.label), \\(options.count) available")' in source


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
    sections_source = _source(CREATE_SECTIONS)
    view_source = _source(CREATE_VIEW)

    assert "embeddedYoutubeSubtitleControls" in sections_source
    assert 'accessibilityIdentifier("createYoutubeInspectEmbeddedSubtitlesButton")' in sections_source
    assert 'accessibilityIdentifier("createYoutubeEmbeddedSubtitleLanguagesField")' in sections_source
    assert 'accessibilityIdentifier("createYoutubeExtractEmbeddedSubtitlesButton")' in sections_source
    assert 'accessibilityIdentifier("createYoutubeEmbeddedSubtitlesMessage")' in sections_source
    assert 'accessibilityIdentifier("createYoutubeEmbeddedSubtitlesError")' in sections_source
    assert "youtubeInlineSubtitleStreams: viewModel.youtubeInlineSubtitleStreams" in view_source
    assert "onInspectYoutubeSubtitles: inspectYoutubeSubtitles" in view_source
    assert "onExtractYoutubeSubtitles: extractYoutubeSubtitles" in view_source


def test_subtitle_create_exposes_editable_metadata_lookup_name() -> None:
    sections_source = _source(CREATE_SECTIONS)
    view_source = _source(CREATE_VIEW)

    assert "AppleBookCreateSubtitleMetadataControls" in sections_source
    assert "@Binding var lookupSourceName: String" in sections_source
    assert 'TextField("Lookup filename", text: $lookupSourceName)' in sections_source
    assert 'accessibilityIdentifier("createSubtitleMetadataLookupField")' in sections_source
    assert "subtitleMetadataLookupSourceName" in view_source
    assert "sourceName: subtitleMetadataLookupSourceName" in view_source


def test_apple_create_exposes_metadata_cache_clear_controls() -> None:
    sections_source = _source(CREATE_SECTIONS)
    view_source = _source(CREATE_VIEW)

    assert "let isClearingCache: Bool" in sections_source
    assert "let onClearCache: () -> Void" in sections_source
    assert 'accessibilityIdentifier("createSubtitleMetadataClearCacheButton")' in sections_source
    assert "viewModel.isClearingSubtitleTvMetadataCache" in view_source
    assert "clearSubtitleTvMetadataCache(" in view_source
    assert "query: subtitleMetadataLookupSourceName" in view_source

    assert "let isClearingTvMetadataCache: Bool" in sections_source
    assert "let isClearingYoutubeMetadataCache: Bool" in sections_source
    assert "let canClearTvMetadataCache: Bool" in sections_source
    assert "let canClearYoutubeMetadataCache: Bool" in sections_source
    assert "let onClearTvMetadataCache: () -> Void" in sections_source
    assert "let onClearYoutubeMetadataCache: () -> Void" in sections_source
    assert 'accessibilityIdentifier("createYoutubeClearTvMetadataCacheButton")' in sections_source
    assert 'accessibilityIdentifier("createYoutubeClearYoutubeMetadataCacheButton")' in sections_source
    assert "viewModel.isClearingYoutubeTvMetadataCache" in view_source
    assert "viewModel.isClearingYoutubeMetadataCache" in view_source
    assert "canClearTvMetadataCache: !youtubeMetadataTvSourceName.isEmpty" in view_source
    assert "canClearYoutubeMetadataCache: !youtubeMetadataVideoSourceName.isEmpty" in view_source
    assert "clearYoutubeTvMetadataCache(" in view_source
    assert "query: youtubeMetadataTvSourceName" in view_source
    assert "clearYoutubeVideoMetadataCache(" in view_source
    assert "query: youtubeMetadataVideoSourceName" in view_source


def test_apple_create_exposes_tv_metadata_artwork_and_ids() -> None:
    sections_source = _source(CREATE_SECTIONS)
    metadata_source = _source(CREATE_METADATA_VIEWS)
    view_source = _source(CREATE_VIEW)
    view_model_source = _source(CREATE_VIEW_MODEL)

    assert "struct AppleBookCreateMetadataArtworkPreview: View" in metadata_source
    assert "AsyncImage(url: url)" in metadata_source
    assert 'accessibilityIdentifier("createMetadataArtworkPreview")' in metadata_source
    assert 'accessibilityIdentifier(item.accessibilityIdentifier)' in metadata_source
    assert "createMetadataPosterPreview" in metadata_source
    assert "createMetadataStillPreview" in metadata_source
    assert "createMetadataYoutubeThumbnailPreview" in metadata_source

    assert 'DisclosureGroup("Artwork")' in sections_source
    assert "#if os(tvOS)" in sections_source
    assert "subtitleArtworkFields" in sections_source
    assert "youtubeArtworkFields" in sections_source
    assert 'accessibilityIdentifier("createSubtitleMetadataArtworkDisclosure")' in sections_source
    assert 'accessibilityIdentifier("createSubtitleMetadataPosterUrlField")' in sections_source
    assert 'accessibilityIdentifier("createSubtitleMetadataStillUrlField")' in sections_source
    assert "showPosterURL: subtitleMetadataNestedTextBinding(section: \"show\", nestedKey: \"image\", key: \"medium\")" in view_source
    assert "episodeStillURL: subtitleMetadataNestedTextBinding(section: \"episode\", nestedKey: \"image\", key: \"medium\")" in view_source
    assert 'tmdbId: subtitleMetadataNumberBinding(section: "show", key: "tmdb_id")' in view_source
    assert 'imdbId: subtitleMetadataTextBinding(section: "show", key: "imdb_id")' in view_source
    assert 'accessibilityIdentifier("createSubtitleMetadataTmdbIdField")' in sections_source
    assert 'accessibilityIdentifier("createSubtitleMetadataImdbIdField")' in sections_source

    assert 'accessibilityIdentifier("createYoutubeMetadataArtworkDisclosure")' in sections_source
    assert 'accessibilityIdentifier("createYoutubeMetadataPosterUrlField")' in sections_source
    assert 'accessibilityIdentifier("createYoutubeMetadataStillUrlField")' in sections_source
    assert 'accessibilityIdentifier("createYoutubeMetadataThumbnailUrlField")' in sections_source
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
    assert "func updateSubtitleMediaMetadataNestedText(" in view_model_source
    assert "func updateYoutubeMediaMetadataNestedText(" in view_model_source
    assert "private static func updateNestedText(" in view_model_source
    assert "nested.removeValue(forKey: key)" in view_model_source
    assert "sectionDraft.removeValue(forKey: nestedKey)" in view_model_source
    assert "struct AppleBookCreateAdvancedMetadataJSONEditor: View" in metadata_source
    assert 'DisclosureGroup("Advanced Metadata JSON")' in metadata_source
    assert "@Binding var advancedMetadataJSON: String" in sections_source
    assert "let advancedMetadataErrorMessage: String?" in sections_source
    assert "TextEditor(text: $text)" in metadata_source
    assert 'disclosureIdentifier: "createSubtitleAdvancedMetadataDisclosure"' in sections_source
    assert 'textEditorIdentifier: "createSubtitleAdvancedMetadataJSONEditor"' in sections_source
    assert 'applyIdentifier: "createSubtitleAdvancedMetadataApplyButton"' in sections_source
    assert 'syncIdentifier: "createSubtitleAdvancedMetadataSyncButton"' in sections_source
    assert 'disclosureIdentifier: "createYoutubeAdvancedMetadataDisclosure"' in sections_source
    assert 'textEditorIdentifier: "createYoutubeAdvancedMetadataJSONEditor"' in sections_source
    assert 'applyIdentifier: "createYoutubeAdvancedMetadataApplyButton"' in sections_source
    assert 'syncIdentifier: "createYoutubeAdvancedMetadataSyncButton"' in sections_source
    assert "advancedMetadataJSON: $viewModel.subtitleMediaMetadataJSONText" in view_source
    assert "advancedMetadataJSON: $viewModel.youtubeMediaMetadataJSONText" in view_source
    assert "viewModel.applySubtitleMediaMetadataJSONText()" in view_source
    assert "viewModel.applyYoutubeMediaMetadataJSONText()" in view_source
    assert "viewModel.syncSubtitleMediaMetadataJSONText()" in view_source
    assert "viewModel.syncYoutubeMediaMetadataJSONText()" in view_source
    assert "func applySubtitleMediaMetadataJSONText()" in view_model_source
    assert "func applyYoutubeMediaMetadataJSONText()" in view_model_source
    assert "private static func parseMetadataJSONObject" in view_model_source
    assert "JSONDecoder().decode([String: JSONValue].self" in view_model_source
    assert 'accessibilityIdentifier("createYoutubeMetadataTmdbIdField")' in sections_source
    assert 'accessibilityIdentifier("createYoutubeMetadataImdbIdField")' in sections_source
