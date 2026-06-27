from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_SUPPORT = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateSupport.swift"
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
CREATE_MODELS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateModels.swift"
)
CREATE_VIEW = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateView.swift"
)
PLAN_DOC = ROOT / "docs" / "plans" / "cross-surface-parity-and-optimization.md"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _named_block(source: str, start_pattern: str, end_pattern: str) -> str:
    match = re.search(start_pattern, source, re.DOTALL)
    assert match, f"Missing block start: {start_pattern}"
    start = match.start()
    end = source.find(end_pattern, match.end())
    assert end != -1, f"Missing block end: {end_pattern}"
    return source[start:end]


def test_narrate_epub_history_defaults_include_web_style_output_settings() -> None:
    model_source = _source(CREATE_MODELS)
    history_source = _source(CREATE_HISTORY_DEFAULTS)
    struct_block = _named_block(
        model_source,
        r"struct AppleNarrationHistoryDefaults: Equatable \{",
        "struct AppleSubtitleHistoryDefaults",
    )
    function_block = _named_block(
        history_source,
        r"static func narrationHistoryDefaults\(",
        "static func generatedBookHistoryDefaults",
    )

    for field in [
        "let voice: AppleBookCreateVoiceOption?",
        "let voiceOverrides: [String: String]?",
        "let generateAudio: Bool?",
        "let audioMode: String?",
        "let audioBitrateKbps: String?",
        "let writtenMode: String?",
        "let tempo: Double?",
        "let sentencesPerOutputFile: Int?",
        "let sentenceSplitterMode: AppleBookSentenceSplitterMode?",
        "let stitchFull: Bool?",
        "let includeTransliteration: Bool?",
        "let translationProvider: AppleSubtitleTranslationProvider?",
        "let llmModel: String?",
        "let translationBatchSize: Int?",
        "let transliterationMode: AppleSubtitleTransliterationMode?",
        "let transliterationModel: String?",
        "let lookupCacheBatchSize: Int?",
        "let outputHtml: Bool?",
        "let outputPdf: Bool?",
    ]:
        assert field in struct_block

    for token in [
        'narrationString($0, keys: ["voice", "selected_voice", "selectedVoice"])',
        'historyStringMap(in: narrationParameterSources($0), keys: ["voice_overrides", "voiceOverrides"])',
        'narrationBool($0, keys: ["generate_audio", "generateAudio"])',
        'narrationString($0, keys: ["audio_mode", "audioMode"])',
        'narrationInt($0, keys: ["audio_bitrate_kbps", "audioBitrateKbps"])',
        'historyDouble($0, keys: ["tempo"])',
        'narrationInt($0, keys: ["sentences_per_output_file", "sentencesPerOutputFile"])',
        'narrationString($0, keys: ["sentence_splitter_mode", "sentenceSplitterMode"])',
        'narrationBool($0, keys: ["stitch_full", "stitchFull"])',
        'narrationBool($0, keys: ["include_transliteration", "includeTransliteration"])',
        'narrationString($0, keys: ["translation_provider", "translationProvider"])',
        'narrationString($0, keys: ["llm_model", "llmModel"])',
        'narrationInt($0, keys: ["translation_batch_size", "translationBatchSize"])',
        'narrationString($0, keys: ["transliteration_mode", "transliterationMode"])',
        'narrationString($0, keys: ["transliteration_model", "transliterationModel"])',
        'narrationInt($0, keys: ["lookup_cache_batch_size", "lookupCacheBatchSize"])',
        'narrationBool($0, keys: ["output_html", "outputHtml"])',
        'narrationBool($0, keys: ["output_pdf", "outputPdf"])',
    ]:
        assert token in function_block

    support_source = _source(CREATE_SUPPORT)
    parsing_source = _source(CREATE_HISTORY_PARSING)
    assert "static func narrationHistoryDefaults(" not in support_source
    assert "static func generatedBookHistoryDefaults" not in support_source
    assert "static func subtitleHistoryDefaults" not in support_source
    assert "static func youtubeHistoryDefaults" not in support_source
    assert "static func latestNarrationJob" not in support_source
    assert "static func narrationString(" not in support_source
    assert "static func historyOffset(" not in support_source
    assert "static func parseJobDate(" not in support_source
    assert "static func latestNarrationJob" not in history_source
    assert "static func narrationString(" not in history_source
    assert "static func historyOffset(" not in history_source
    assert "static func parseJobDate(" not in history_source
    assert "static func latestNarrationJob" in parsing_source
    assert "static func narrationString(" in parsing_source
    assert "static func historyOffset(" in parsing_source
    assert "static func parseJobDate(" in parsing_source


def test_narrate_epub_history_defaults_preserve_user_edited_fields() -> None:
    source = _source(CREATE_VIEW)
    block = _named_block(
        source,
        r"private func applyNarrationHistoryDefaults\(\) \{",
        "private func applySubtitleHistoryDefaults",
    )

    for token in [
        "if !editedFields.contains(.voice),",
        "if !editedFields.contains(.languageVoiceOverrides),",
        "if !editedFields.contains(.generateAudio),",
        "if !editedFields.contains(.audioMode),",
        "if !editedFields.contains(.audioBitrateKbps),",
        "if !editedFields.contains(.writtenMode),",
        "if !editedFields.contains(.tempo),",
        "if !editedFields.contains(.bookSentencesPerOutputFile),",
        "if !editedFields.contains(.bookSentenceSplitterMode),",
        "if !editedFields.contains(.stitchFull),",
        "if !editedFields.contains(.includeTransliteration),",
        "if !editedFields.contains(.bookTranslationProvider),",
        "if !editedFields.contains(.bookLlmModel),",
        "if !editedFields.contains(.bookTranslationBatchSize),",
        "if !editedFields.contains(.bookTransliterationMode),",
        "if !editedFields.contains(.bookTransliterationModel),",
        "if !editedFields.contains(.bookLookupCacheBatchSize),",
        "if !editedFields.contains(.outputHtml),",
        "if !editedFields.contains(.outputPdf),",
    ]:
        assert token in block


def test_generated_book_history_defaults_restore_continuation_context_and_voice_overrides() -> None:
    model_source = _source(CREATE_MODELS)
    history_source = _source(CREATE_HISTORY_DEFAULTS)
    view_source = _source(CREATE_VIEW)
    struct_block = _named_block(
        model_source,
        r"struct AppleGeneratedBookHistoryDefaults: Equatable \{",
        "struct AppleCreateResolvedDefaults",
    )
    function_block = _named_block(
        history_source,
        r"static func generatedBookHistoryDefaults",
        "static func subtitleHistoryDefaults",
    )
    view_block = _named_block(
        view_source,
        r"private func applyGeneratedBookHistoryDefaults\(\) \{",
        "private func applyNarrationHistoryDefaults",
    )

    for field in [
        "let sourceBookTitle: String?",
        "let sourceBookAuthor: String?",
        "let sourceBookGenre: String?",
        "let sourceBookSummary: String?",
        "let voiceOverrides: [String: String]?",
        "let bookSentenceSplitterMode: AppleBookSentenceSplitterMode?",
    ]:
        assert field in struct_block

    for token in [
        'sourceBookTitle: historyString(in: sources, keys: ["source_book_title", "sourceBookTitle"])',
        'sourceBookAuthor: historyString(in: sources, keys: ["source_book_author", "sourceBookAuthor"])',
        'sourceBookGenre: historyString(in: sources, keys: ["source_book_genre", "sourceBookGenre"])',
        'sourceBookSummary: historyString(in: sources, keys: ["source_book_summary", "sourceBookSummary"])',
        'voiceOverrides: historyStringMap(in: sources, keys: ["voice_overrides", "voiceOverrides"])',
        'bookSentenceSplitterMode: historyString(in: sources, keys: ["sentence_splitter_mode", "sentenceSplitterMode"])',
        "|| defaults.sourceBookTitle != nil",
        "|| defaults.voiceOverrides != nil",
        "|| defaults.bookSentenceSplitterMode != nil",
    ]:
        assert token in function_block

    for token in [
        "if !editedFields.contains(.sourceBookTitle),",
        "if !editedFields.contains(.sourceBookAuthor),",
        "if !editedFields.contains(.sourceBookGenre),",
        "if !editedFields.contains(.sourceBookSummary),",
        "if !editedFields.contains(.languageVoiceOverrides),",
        "if !editedFields.contains(.bookSentenceSplitterMode),",
    ]:
        assert token in view_block


def test_history_parsing_supports_string_maps_for_voice_overrides() -> None:
    parsing_source = _source(CREATE_HISTORY_PARSING)

    assert "static func historyStringMap(" in parsing_source
    assert "guard let object = source[key]?.objectValue else { continue }" in parsing_source
    assert "result[normalizedKey] = normalizedValue" in parsing_source


def test_create_history_defaults_do_not_replace_loaded_nas_sources() -> None:
    history_source = _source(CREATE_HISTORY_DEFAULTS)
    view_source = _source(CREATE_VIEW)
    function_block = _named_block(
        history_source,
        r"static func narrationHistoryDefaults\(",
        "static func generatedBookHistoryDefaults",
    )
    subtitle_block = _named_block(
        view_source,
        r"private func applySubtitleHistoryDefaults\(\) \{",
        "private func applyYoutubeHistoryDefaults",
    )
    youtube_block = _named_block(
        view_source,
        r"private func applyYoutubeHistoryDefaults\(\) \{",
        "func clearNarrateChapterSelection",
    )

    assert "let currentInput = currentInputFile.trimmingCharacters(in: .whitespacesAndNewlines)" in function_block
    assert 'let latestInputFile = latest.flatMap { narrationString($0, keys: ["input_file", "inputFile"]) }' in function_block
    assert "let inputFile = currentInput.isEmpty ? latestInputFile : nil" in function_block
    assert "let baseOutput = currentInput.isEmpty" in function_block
    assert 'let startInput = currentInput.nonEmptyValue ?? latestInputFile ?? ""' in function_block
    assert "trimmed(subtitleSourcePath).isEmpty" in subtitle_block
    assert "trimmed(youtubeVideoPath).isEmpty" in youtube_block
    assert "trimmed(youtubeSubtitlePath).isEmpty" in youtube_block


def test_parity_plan_mentions_narrate_epub_history_defaults() -> None:
    plan = re.sub(r"\s+", " ", _source(PLAN_DOC))

    assert "Narrate EPUB history defaults now reuse prior audio, output, translation, transliteration, lookup-cache, voice overrides, chunking, and sentence-splitter settings" in plan
    assert "generated-book history also restores source-book continuation context, voice overrides, and sentence-splitter mode" in plan
