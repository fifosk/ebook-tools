from pathlib import Path

import pytest

from modules.services.youtube_dubbing import (
    _AssDialogue,
    _compute_underlay_gain_db,
    _language_uses_non_latin,
    _normalize_rtl_word_order,
    _subtitle_codec_is_image_based,
    _summarize_ffmpeg_error,
    _write_webvtt,
    _has_video_stream,
    list_inline_subtitle_streams,
    extract_inline_subtitles,
    list_downloaded_videos,
    delete_nas_subtitle,
    delete_downloaded_video,
)
import modules.services.youtube_dubbing.video_utils as _video_utils_mod
import modules.services.youtube_dubbing.nas as _nas_mod
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

    monkeypatch.setattr(_video_utils_mod.subprocess, "run", fake_run)
    assert _has_video_stream(tmp_path / "dummy.mp4")


def test_compute_underlay_gain_respects_mix_percent() -> None:
    gain_db = _compute_underlay_gain_db(reference_rms=100.0, original_rms=200.0, mix_percent=10.0)
    # 10% of dubbed loudness with original twice as loud -> roughly -26 dB.
    assert pytest.approx(gain_db, rel=1e-3) == pytest.approx(-26.0206, rel=1e-3)


def test_subtitle_codec_is_image_based_detects_common_bitmap_streams() -> None:
    assert _subtitle_codec_is_image_based("hdmv_pgs_subtitle")
    assert not _subtitle_codec_is_image_based("subrip")


def test_summarize_ffmpeg_error_trims_banner_and_prefers_error_line() -> None:
    stderr = """
    ffmpeg version 7.1 Copyright (c) 2000-2024 the FFmpeg developers
    Input #0, matroska,webm, from 'video.mkv':
      Metadata:
        TITLE           : Demo
    Error while opening decoder for input stream #0:2 : Invalid data found when processing input
    """

    summary = _summarize_ffmpeg_error(stderr)

    assert summary == "Error while opening decoder for input stream #0:2 : Invalid data found when processing input"


def test_extract_inline_subtitles_skips_image_based_streams(monkeypatch, tmp_path: Path) -> None:
    video_path = tmp_path / "sample.mkv"
    video_path.write_bytes(b"\x00")

    monkeypatch.setattr(
        _nas_mod,
        "_probe_subtitle_streams",
        lambda _path: [
            {
                "index": 2,
                "__position__": 0,
                "codec_name": "hdmv_pgs_subtitle",
                "tags": {},
            }
        ],
    )

    def _unexpected_run(*_args, **_kwargs):
        raise AssertionError("ffmpeg should not be invoked for image-based subtitle streams")

    monkeypatch.setattr(_nas_mod.subprocess, "run", _unexpected_run)

    with pytest.raises(ValueError) as excinfo:
        extract_inline_subtitles(video_path)

    assert "image-based subtitle codec 'hdmv_pgs_subtitle'" in str(excinfo.value)


def test_extract_inline_subtitles_filters_by_language(monkeypatch, tmp_path: Path) -> None:
    video_path = tmp_path / "sample.mkv"
    video_path.write_bytes(b"\x00")
    streams = [
        {"index": 3, "__position__": 0, "tags": {"language": "en"}, "codec_name": "subrip"},
        {"index": 4, "__position__": 1, "tags": {"language": "fr"}, "codec_name": "subrip"},
    ]

    monkeypatch.setattr(_nas_mod, "_probe_subtitle_streams", lambda _path: streams)

    calls = []

    def _fake_run(cmd, **_kwargs):
        calls.append(cmd)
        Path(cmd[-1]).write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
        return type("Result", (), {"returncode": 0, "stdout": b"", "stderr": b""})()

    monkeypatch.setattr(_nas_mod.subprocess, "run", _fake_run)
    monkeypatch.setattr(_nas_mod, "load_subtitle_cues", lambda _path: [])
    monkeypatch.setattr(_nas_mod, "write_srt", lambda _path, _cues: None)

    extracted = extract_inline_subtitles(video_path, languages=["en"])

    assert len(extracted) == 1
    assert extracted[0].language == "en"
    assert len(calls) == 1
    assert f"0:s:{streams[0]['__position__']}" in calls[0]


def test_list_inline_subtitle_streams_reports_extractability(monkeypatch, tmp_path: Path) -> None:
    video_path = tmp_path / "sample.mkv"
    video_path.write_bytes(b"\x00")
    monkeypatch.setattr(
        _nas_mod,
        "_probe_subtitle_streams",
        lambda _path: [
            {"index": 0, "__position__": 0, "tags": {"language": "en"}, "codec_name": "subrip"},
            {"index": 1, "__position__": 1, "tags": {"language": "es"}, "codec_name": "hdmv_pgs_subtitle"},
        ],
    )

    streams = list_inline_subtitle_streams(video_path)

    assert streams[0]["language"] == "en"
    assert streams[0]["can_extract"]
    assert streams[1]["language"] == "es"
    assert not streams[1]["can_extract"]


def test_delete_nas_subtitle_removes_mirrors(monkeypatch, tmp_path: Path) -> None:
    subtitle_path = tmp_path / "movie.en.srt"
    subtitle_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
    html_dir = subtitle_path.parent / "html"
    html_dir.mkdir()
    html_local = html_dir / "movie.en.html"
    html_local.write_text("<p>Hello</p>", encoding="utf-8")

    mirror_root = tmp_path / "mirror"
    mirror_root.mkdir()
    mirror_copy = mirror_root / subtitle_path.name
    mirror_copy.write_text("copy", encoding="utf-8")
    mirror_html_dir = mirror_root / "html"
    mirror_html_dir.mkdir()
    mirror_html = mirror_html_dir / "movie.en.html"
    mirror_html.write_text("<p>Mirror</p>", encoding="utf-8")

    monkeypatch.setattr(_nas_mod, "_SUBTITLE_MIRROR_DIR", mirror_root)

    result = delete_nas_subtitle(subtitle_path)

    assert not subtitle_path.exists()
    assert not mirror_copy.exists()
    assert not mirror_html.exists()
    assert not html_local.exists()
    removed_paths = {path.resolve() for path in result.removed}
    assert subtitle_path.resolve() in removed_paths
    assert mirror_copy.resolve() in removed_paths
    assert mirror_html.resolve() in removed_paths


def test_delete_downloaded_video_removes_folder_and_artifacts(monkeypatch, tmp_path: Path) -> None:
    video_dir = tmp_path / "Sample Video - 2024-01-01 10-00-00"
    video_dir.mkdir()
    video_path = video_dir / "sample_yt.mp4"
    video_path.write_bytes(b"\x00")
    subtitle_path = video_dir / "sample_yt.en.srt"
    subtitle_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
    html_dir = video_dir / "html"
    html_dir.mkdir()
    html_path = html_dir / "sample_yt.en.html"
    html_path.write_text("<p>hello</p>", encoding="utf-8")
    dubbed_dir = video_dir / "dubbed-en"
    dubbed_dir.mkdir()
    (dubbed_dir / "sample_yt.en.dub.mp4").write_bytes(b"\x00")

    mirror_root = tmp_path / "mirror"
    mirror_root.mkdir()
    mirror_copy = mirror_root / subtitle_path.name
    mirror_copy.write_text("copy", encoding="utf-8")
    mirror_html_dir = mirror_root / "html"
    mirror_html_dir.mkdir()
    mirror_html = mirror_html_dir / "sample_yt.en.html"
    mirror_html.write_text("<p>mirror</p>", encoding="utf-8")

    monkeypatch.setattr(_nas_mod, "_SUBTITLE_MIRROR_DIR", mirror_root)

    result = delete_downloaded_video(video_path)

    assert not video_dir.exists()
    assert not mirror_copy.exists()
    assert not mirror_html.exists()
    removed_paths = {path.resolve() for path in result.removed}
    assert video_dir.resolve() in removed_paths
    assert video_path.resolve() in removed_paths
    assert subtitle_path.resolve() in removed_paths
