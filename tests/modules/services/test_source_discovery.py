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
