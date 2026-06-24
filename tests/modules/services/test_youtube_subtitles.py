from datetime import datetime
from pathlib import Path

import pytest

import modules.services.youtube_subtitles as youtube_subtitles
from modules.services.youtube_subtitles import (
    YoutubeSubtitleListing,
    _finalize_partial_download,
    _recent_files,
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
