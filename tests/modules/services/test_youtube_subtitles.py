from datetime import datetime
from pathlib import Path

import pytest

import modules.services.youtube_subtitles as youtube_subtitles
from modules.services.youtube_subtitles import (
    YoutubeSubtitleListing,
    _finalize_partial_download,
    _recent_files,
    download_subtitle,
    download_video,
)

pytestmark = pytest.mark.services


def test_finalize_partial_download_skips_stale_partials(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    stale_partial = tmp_path / "Demo [abc].mp4.part"
    stable_partial = tmp_path / "Demo [abc].webm.part"
    stale_partial.write_bytes(b"stale")
    stable_partial.write_bytes(b"stable")
    original_stat = Path.stat

    def fake_stat(path: Path, *args, **kwargs):
        if path == stale_partial:
            raise FileNotFoundError(path)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fake_stat)

    recovered = _finalize_partial_download(tmp_path, "Demo [abc]")

    assert recovered == tmp_path / "Demo [abc]_yt.webm"
    assert recovered is not None
    assert recovered.read_bytes() == b"stable"
    assert not stable_partial.exists()


def test_finalize_partial_download_uses_safe_stat_for_completed_candidate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    partial = tmp_path / "Demo [abc].mp4.part"
    existing = tmp_path / "Demo [abc]_yt.mp4"
    partial.write_bytes(b"partial")
    existing.write_bytes(b"existing")

    def fail_exists(path: Path) -> bool:
        raise AssertionError("partial recovery should probe completed files via safe_stat")

    monkeypatch.setattr(Path, "exists", fail_exists)

    assert _finalize_partial_download(tmp_path, "Demo [abc]") is None
    assert partial.read_bytes() == b"partial"
    assert existing.read_bytes() == b"existing"


def test_recent_files_stops_on_candidate_scan_failure(tmp_path: Path) -> None:
    stable = tmp_path / "stable.mp4"
    stable.write_bytes(b"video")

    class _BrokenCandidateIterator:
        def __init__(self) -> None:
            self._index = 0

        def __iter__(self):
            return self

        def __next__(self) -> Path:
            self._index += 1
            if self._index == 1:
                return stable
            raise OSError("transient NAS scan failure")

    assert [path for path, _mtime in _recent_files(_BrokenCandidateIterator(), context="test")] == [
        stable
    ]


def test_recent_files_uses_safe_stat_instead_of_is_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    stable = tmp_path / "stable.mp4"
    stable.write_bytes(b"video")

    def fail_is_file(_path: Path) -> bool:
        raise AssertionError("_recent_files should rely on safe_stat instead of is_file")

    monkeypatch.setattr(Path, "is_file", fail_is_file)

    assert [path for path, _mtime in _recent_files([stable], context="test")] == [stable]


def test_download_subtitle_skips_stale_candidates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    stale = tmp_path / "stale-abc.en.srt"
    stable = tmp_path / "stable-abc.en.srt"
    stale.write_text("stale", encoding="utf-8")
    stable.write_text("stable", encoding="utf-8")
    original_stat = Path.stat

    class _FakeYoutubeDL:
        def __init__(self, options):
            self.params = options

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def prepare_filename(self, _info) -> str:
            return str(self.params["outtmpl"]).replace("%(ext)s", "mp4")

    def fake_extract(_ydl, _url: str, *, download: bool):
        assert download
        return {"id": "abc", "title": "Demo"}

    def fake_stat(path: Path, *args, **kwargs):
        if path == stale:
            raise FileNotFoundError(path)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(youtube_subtitles, "YoutubeDL", _FakeYoutubeDL)
    monkeypatch.setattr(youtube_subtitles, "_extract_with_backoff", fake_extract)
    monkeypatch.setattr(Path, "stat", fake_stat)

    downloaded = download_subtitle(
        "https://youtube.example/watch?v=abc",
        language="en",
        kind="manual",
        output_dir=tmp_path,
        video_id="abc",
        video_title="Demo",
    )

    assert downloaded == tmp_path / "Demo [abc]_yt.en.srt"
    assert downloaded.read_text(encoding="utf-8") == "stable"
    assert not stable.exists()


def test_download_video_falls_back_to_prepared_filename_when_output_scan_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    timestamp = datetime(2026, 6, 24, 12, 0, 0)
    download_dir = tmp_path / "Demo - 2026-06-24 12-00-00"

    class _FakeYoutubeDL:
        def __init__(self, options):
            self.params = options

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def prepare_filename(self, _info) -> str:
            return str(self.params["outtmpl"]).replace("%(ext)s", "mp4")

    def fake_extract(ydl, _url: str, *, download: bool):
        assert download
        output_path = Path(ydl.prepare_filename({}))
        output_path.write_bytes(b"video")
        return {"id": "abc", "title": "Demo"}

    original_iterdir = Path.iterdir

    def fake_iterdir(path: Path):
        if path == download_dir:
            raise OSError("transient NAS scan failure")
        return original_iterdir(path)

    monkeypatch.setattr(
        youtube_subtitles,
        "list_available_subtitles",
        lambda _url: YoutubeSubtitleListing("abc", "Demo", [], []),
    )
    monkeypatch.setattr(youtube_subtitles, "YoutubeDL", _FakeYoutubeDL)
    monkeypatch.setattr(youtube_subtitles, "_extract_with_backoff", fake_extract)
    monkeypatch.setattr(Path, "iterdir", fake_iterdir)

    downloaded = download_video("https://youtube.example/watch?v=abc", output_root=tmp_path, timestamp=timestamp)

    assert downloaded == download_dir / "Demo [abc]_yt.mp4"
    assert downloaded.read_bytes() == b"video"


def test_download_video_fallback_uses_safe_stat_for_prepared_filename(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    timestamp = datetime(2026, 6, 24, 12, 0, 0)
    download_dir = tmp_path / "Demo - 2026-06-24 12-00-00"

    class _FakeYoutubeDL:
        def __init__(self, options):
            self.params = options

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def prepare_filename(self, _info) -> str:
            return str(self.params["outtmpl"]).replace("%(ext)s", "mp4")

    def fake_extract(ydl, _url: str, *, download: bool):
        assert download
        output_path = Path(ydl.prepare_filename({}))
        output_path.write_bytes(b"video")
        return {"id": "abc", "title": "Demo"}

    original_iterdir = Path.iterdir

    def fake_iterdir(path: Path):
        if path == download_dir:
            raise OSError("transient NAS scan failure")
        return original_iterdir(path)

    def fail_exists(path: Path) -> bool:
        raise AssertionError("download fallback should probe prepared filename via safe_stat")

    monkeypatch.setattr(
        youtube_subtitles,
        "list_available_subtitles",
        lambda _url: YoutubeSubtitleListing("abc", "Demo", [], []),
    )
    monkeypatch.setattr(youtube_subtitles, "YoutubeDL", _FakeYoutubeDL)
    monkeypatch.setattr(youtube_subtitles, "_extract_with_backoff", fake_extract)
    monkeypatch.setattr(Path, "iterdir", fake_iterdir)
    monkeypatch.setattr(Path, "exists", fail_exists)

    downloaded = download_video("https://youtube.example/watch?v=abc", output_root=tmp_path, timestamp=timestamp)

    assert downloaded == download_dir / "Demo [abc]_yt.mp4"
    assert downloaded.read_bytes() == b"video"
