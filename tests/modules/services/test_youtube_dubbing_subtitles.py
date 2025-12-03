from pathlib import Path

from modules.services.youtube_dubbing import (
    _AssDialogue,
    _language_uses_non_latin,
    _normalize_rtl_word_order,
    _write_webvtt,
)


class _StubTransliterator:
    def transliterate(self, text: str, language: str):
        return type("Result", (), {"text": "salam aleikum"})()


def test_normalize_rtl_word_order_reverses_tokens_for_display() -> None:
    text = "שלום עולם טוב"
    assert _normalize_rtl_word_order(text, "he") == "טוב עולם שלום"
    assert _normalize_rtl_word_order("hello world", "he") == "hello world"


def test_language_uses_non_latin_accepts_language_codes() -> None:
    assert _language_uses_non_latin("he")
    assert _language_uses_non_latin("Hebrew")
    assert not _language_uses_non_latin("en")


def test_write_webvtt_includes_transliteration_with_rtl_order(tmp_path: Path) -> None:
    destination = tmp_path / "sample.vtt"
    dialogue = _AssDialogue(
        start=0.0,
        end=2.5,
        translation="مرحبا بالعالم",
        original="Hello world",
        transliteration=None,
    )
    _write_webvtt(
        [dialogue],
        destination,
        target_language="ar",
        include_transliteration=True,
        transliterator=_StubTransliterator(),
    )
    payload = destination.read_text(encoding="utf-8")
    assert "بالعالم مرحبا" in payload
    assert "aleikum salam" in payload
