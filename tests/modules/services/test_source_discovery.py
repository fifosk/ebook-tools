from __future__ import annotations

import os
from pathlib import Path

import pytest

from modules.services.source_discovery import walk_visible_source_files


def test_walk_visible_source_files_prunes_hidden_folders_and_reuses_stats(tmp_path: Path) -> None:
    nested = tmp_path / "Series"
    hidden = tmp_path / ".hidden"
    nested.mkdir()
    hidden.mkdir()
    visible = nested / "latest.EPUB"
    hidden_file = hidden / "hidden.epub"
    ignored = nested / "notes.txt"
    visible.write_bytes(b"ebook")
    hidden_file.write_bytes(b"hidden")
    ignored.write_text("notes", encoding="utf-8")

    results = walk_visible_source_files(tmp_path, suffixes={".epub"})

    assert [entry.path for entry in results] == [visible]
    assert results[0].stat.st_size == len(b"ebook")


def test_walk_visible_source_files_follows_visible_symlinked_folders(tmp_path: Path) -> None:
    external = tmp_path / "Mounted NAS" / "Dan Brown"
    external.mkdir(parents=True)
    visible = external / "latest.epub"
    visible.write_bytes(b"ebook")
    root = tmp_path / "books"
    root.mkdir()
    linked = root / "Dan Brown"
    try:
        linked.symlink_to(external, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")

    results = walk_visible_source_files(root, suffixes={".epub"})

    assert [entry.path for entry in results] == [linked / "latest.epub"]
    assert results[0].stat.st_size == len(b"ebook")


def test_walk_visible_source_files_accepts_bare_suffix_filters(tmp_path: Path) -> None:
    ebook = tmp_path / "latest.EPUB"
    subtitle = tmp_path / "episode.srt"
    ignored = tmp_path / "notes.txt"
    ebook.write_bytes(b"ebook")
    subtitle.write_text("WEBVTT", encoding="utf-8")
    ignored.write_text("notes", encoding="utf-8")

    results = walk_visible_source_files(tmp_path, suffixes={" epub ", "srt", ""})

    assert [entry.path for entry in results] == [subtitle, ebook]


def test_walk_visible_source_files_prunes_symlink_cycles(tmp_path: Path) -> None:
    root = tmp_path / "books"
    root.mkdir()
    visible = root / "latest.epub"
    visible.write_bytes(b"ebook")
    loop = root / "Loop"
    try:
        loop.symlink_to(root, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")

    results = walk_visible_source_files(root, suffixes={".epub"})

    assert [entry.path for entry in results] == [visible]


def test_walk_visible_source_files_skips_stale_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stable = tmp_path / "stable.srt"
    vanished = tmp_path / "vanished.srt"
    stable.write_text("1\n00:00:00,000 --> 00:00:01,000\nStable\n", encoding="utf-8")
    vanished.write_text("1\n00:00:00,000 --> 00:00:01,000\nGone\n", encoding="utf-8")
    original_stat = Path.stat

    def fake_stat(path: Path, *args, **kwargs):
        if path.name == "vanished.srt":
            raise FileNotFoundError(path)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fake_stat)

    results = walk_visible_source_files(tmp_path, suffixes={".srt"})

    assert [entry.path for entry in results] == [stable]


def test_walk_visible_source_files_tolerates_root_scan_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved = tmp_path.resolve()
    original_walk = os.walk

    def fake_walk(path: Path, *args, **kwargs):
        if Path(path) == resolved:
            if False:
                yield None
            return
        yield from original_walk(path, *args, **kwargs)

    monkeypatch.setattr("modules.services.source_discovery.os.walk", fake_walk)

    assert walk_visible_source_files(resolved, suffixes={".epub"}) == []


def test_walk_visible_source_files_skips_hidden_walked_descendants(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    visible_dir = tmp_path / "visible"
    hidden_dir = tmp_path / ".hidden"
    visible_dir.mkdir()
    hidden_dir.mkdir()
    visible = visible_dir / "visible.epub"
    hidden = hidden_dir / "hidden.epub"
    visible.write_bytes(b"visible")
    hidden.write_bytes(b"hidden")

    def fake_walk(path: Path, *args, **kwargs):
        yield str(path), [".hidden", "visible"], []
        yield str(hidden_dir), [], [hidden.name]
        yield str(visible_dir), [], [visible.name]

    monkeypatch.setattr("modules.services.source_discovery.os.walk", fake_walk)

    results = walk_visible_source_files(tmp_path, suffixes={".epub"})

    assert [entry.path for entry in results] == [visible]
