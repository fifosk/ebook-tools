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
    assert "showsJobTypePicker: showsInlineJobTypePicker" in source
    assert "@Environment(\\.horizontalSizeClass) private var horizontalSizeClass" in source
    assert "private var usesRegularWidthCreateLayout: Bool" in source
    assert "horizontalSizeClass == .regular" in source


def test_source_section_can_move_job_type_picker_out_of_detail_form() -> None:
    source = _source(CREATE_SECTIONS)

    assert "let showsJobTypePicker: Bool" in source
    assert "if showsJobTypePicker || creationMode != .generatedBook" in source
    assert 'Picker("Job type", selection: $creationMode)' in source
    assert '.accessibilityIdentifier("createJobTypePicker")' in source


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
    assert 'createList(accessibilityIdentifier: "appleBookCreateSettingsPane")' in source
    assert "minWidth: Self.settingsPaneMinWidth" in source
    assert "idealWidth: Self.settingsPaneIdealWidth" in source
    assert ".layoutPriority(2)" in source
    assert "private var createSetupSections: some View" in source
    assert "private var createSettingsSections: some View" in source
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
    assert "promptSection" in setup_sections.group("body")
    assert "metadataSection" in setup_sections.group("body")
    assert "jobSettingsSection" not in setup_sections.group("body")
    assert "jobSettingsSection" in settings_sections.group("body")
    assert "narrationSection" in settings_sections.group("body")
    assert "outputSection" in settings_sections.group("body")
    assert "submitSection" in settings_sections.group("body")

    prompt_section = re.search(
        r"private var promptSection: some View \{(?P<body>.*?)\n    \}",
        source,
        re.DOTALL,
    )
    job_settings_section = re.search(
        r"private var jobSettingsSection: some View \{(?P<body>.*?)\n    \}",
        source,
        re.DOTALL,
    )

    assert prompt_section
    assert job_settings_section
    assert "sentenceCountControl" not in prompt_section.group("body")
    assert "sentenceCountControl" in job_settings_section.group("body")
    assert 'accessibilityIdentifier("createNarrateOutputPathField")' in job_settings_section.group("body")
    assert 'accessibilityIdentifier("createNarrateStartSentenceField")' in job_settings_section.group("body")
    assert 'accessibilityIdentifier("createNarrateEndSentenceField")' in job_settings_section.group("body")


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
    view_source = _source(CREATE_VIEW)
    view_model_source = _source(CREATE_VIEW_MODEL)

    assert "private struct AppleBookCreateMetadataArtworkPreview: View" in sections_source
    assert "AsyncImage(url: url)" in sections_source
    assert 'accessibilityIdentifier("createMetadataArtworkPreview")' in sections_source
    assert 'accessibilityIdentifier(item.accessibilityIdentifier)' in sections_source
    assert "createMetadataPosterPreview" in sections_source
    assert "createMetadataStillPreview" in sections_source
    assert "createMetadataYoutubeThumbnailPreview" in sections_source

    assert 'DisclosureGroup("Artwork")' in sections_source
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
    assert 'accessibilityIdentifier("createYoutubeMetadataTmdbIdField")' in sections_source
    assert 'accessibilityIdentifier("createYoutubeMetadataImdbIdField")' in sections_source
