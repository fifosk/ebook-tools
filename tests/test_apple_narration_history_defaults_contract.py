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
    support_source = _source(CREATE_SUPPORT)
    struct_block = _named_block(
        model_source,
        r"struct AppleNarrationHistoryDefaults: Equatable \{",
        "struct AppleSubtitleHistoryDefaults",
    )
    function_block = _named_block(
        support_source,
        r"static func narrationHistoryDefaults\(",
        "static func generatedBookHistoryDefaults",
    )

    for field in [
        "let voice: AppleBookCreateVoiceOption?",
        "let generateAudio: Bool?",
        "let audioMode: String?",
        "let audioBitrateKbps: String?",
        "let writtenMode: String?",
        "let tempo: Double?",
        "let sentencesPerOutputFile: Int?",
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
        'narrationBool($0, keys: ["generate_audio", "generateAudio"])',
        'narrationString($0, keys: ["audio_mode", "audioMode"])',
        'narrationInt($0, keys: ["audio_bitrate_kbps", "audioBitrateKbps"])',
        'historyDouble($0, keys: ["tempo"])',
        'narrationInt($0, keys: ["sentences_per_output_file", "sentencesPerOutputFile"])',
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


def test_narrate_epub_history_defaults_preserve_user_edited_fields() -> None:
    source = _source(CREATE_VIEW)
    block = _named_block(
        source,
        r"private func applyNarrationHistoryDefaults\(\) \{",
        "private func applySubtitleHistoryDefaults",
    )

    for token in [
        "if !editedFields.contains(.voice),",
        "if !editedFields.contains(.generateAudio),",
        "if !editedFields.contains(.audioMode),",
        "if !editedFields.contains(.audioBitrateKbps),",
        "if !editedFields.contains(.writtenMode),",
        "if !editedFields.contains(.tempo),",
        "if !editedFields.contains(.bookSentencesPerOutputFile),",
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


def test_parity_plan_mentions_narrate_epub_history_defaults() -> None:
    plan = _source(PLAN_DOC)

    assert "Narrate EPUB history defaults now reuse prior audio, output, translation, transliteration, lookup-cache, and chunking settings" in plan
