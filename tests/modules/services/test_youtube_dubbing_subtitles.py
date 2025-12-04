from pathlib import Path

import pytest

from modules.services.youtube_dubbing import (
    _AssDialogue,
    _compute_underlay_gain_db,
    _language_uses_non_latin,
    _normalize_rtl_word_order,
    _write_webvtt,
    _has_video_stream,
    list_downloaded_videos,
)
from modules.subtitles.processing import load_subtitle_cues


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
        rtl_normalized=False,
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
    assert "salam aleikum" in payload


def test_load_subtitle_cues_rejects_binary_sub(tmp_path: Path) -> None:
    vobsub_path = tmp_path / "sample.sub"
    vobsub_path.write_bytes(b"\x00\x00\x01\xba" + b"\x00" * 32)

    with pytest.raises(ValueError, match="Binary .sub"):
        load_subtitle_cues(vobsub_path)


def test_list_downloaded_videos_includes_generic_mkv_and_subtitles(tmp_path: Path) -> None:
    video_path = tmp_path / "generic-video.mkv"
    video_path.write_bytes(b"\x00" * 10)
    subtitle_path = tmp_path / "generic-video.en.sub"
    subtitle_path.write_text("1\n00:00:00,000 --> 00:00:02,000\nHello world\n", encoding="utf-8")

    videos = list_downloaded_videos(tmp_path)

    assert len(videos) == 1
    entry = videos[0]
    assert entry.source == "nas_video"
    subtitle_suffixes = {sub.path.suffix for sub in entry.subtitles}
    assert ".sub" in subtitle_suffixes
    assert any(sub.path == subtitle_path.resolve() for sub in entry.subtitles)


def test_has_video_stream_handles_out_of_order_ffprobe_fields(monkeypatch, tmp_path: Path) -> None:
    # ffprobe may emit width/height before pix_fmt; we parse JSON to avoid order issues.
    payload = b'{"streams": [{"pix_fmt": "yuv420p", "width": 612, "height": 480}]}'

    def fake_run(_cmd, **_kwargs):
        return type(
            "Result",
            (),
            {"returncode": 0, "stdout": payload, "stderr": b""},
        )()

    monkeypatch.setattr("modules.services.youtube_dubbing.subprocess.run", fake_run)
    assert _has_video_stream(tmp_path / "dummy.mp4")


def test_compute_underlay_gain_respects_mix_percent() -> None:
    gain_db = _compute_underlay_gain_db(reference_rms=100.0, original_rms=200.0, mix_percent=10.0)
    # 10% of dubbed loudness with original twice as loud -> roughly -26 dB.
    assert pytest.approx(gain_db, rel=1e-3) == pytest.approx(-26.0206, rel=1e-3)
