from __future__ import annotations

import os
from pathlib import Path

import pytest

from modules.services.source_discovery import (
    append_bounded_newest_source_file,
    iter_visible_source_files,
    newest_source_file_sort_key,
    walk_visible_source_files,
)


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


def test_iter_visible_source_files_streams_same_visible_entries(tmp_path: Path) -> None:
    nested = tmp_path / "Series"
    hidden = tmp_path / ".hidden"
    nested.mkdir()
    hidden.mkdir()
    visible = nested / "latest.epub"
    hidden_file = hidden / "hidden.epub"
    visible.write_bytes(b"ebook")
    hidden_file.write_bytes(b"hidden")

    iterator = iter_visible_source_files(tmp_path, suffixes={"epub"})

    assert iter(iterator) is iterator
    results = list(iterator)
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


def test_append_bounded_newest_source_file_reuses_cached_stat_and_secondary_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    older = tmp_path / "zeta.epub"
    alpha = tmp_path / "Alpha.epub"
    beta = tmp_path / "beta.epub"
    older.write_bytes(b"older")
    alpha.write_bytes(b"alpha")
    beta.write_bytes(b"beta")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(alpha, (1_700_000_100, 1_700_000_100))
    os.utime(beta, (1_700_000_100, 1_700_000_100))

    entries = list(iter_visible_source_files(tmp_path, suffixes={".epub"}))
    original_stat = Path.stat

    def fake_stat(path: Path, *args, **kwargs):
        if path.suffix == ".epub":
            raise AssertionError("bounded newest helper should reuse discovered stat payloads")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fake_stat)

    matches = []
    for entry in entries:
        append_bounded_newest_source_file(
            matches,
            entry,
            2,
            secondary_key=lambda item: item.path.name,
        )

    assert [entry.path.name for entry in matches] == ["Alpha.epub", "beta.epub"]
    assert [
        entry.path.name
        for entry in sorted(
            matches,
            key=lambda item: newest_source_file_sort_key(
                item,
                secondary_key=lambda found: found.path.name,
            ),
        )
    ] == ["Alpha.epub", "beta.epub"]


def test_append_bounded_newest_source_file_ignores_non_positive_limits(tmp_path: Path) -> None:
    ebook = tmp_path / "latest.epub"
    ebook.write_bytes(b"ebook")
    [entry] = list(iter_visible_source_files(tmp_path, suffixes={".epub"}))
    matches = []

    append_bounded_newest_source_file(matches, entry, 0)
    append_bounded_newest_source_file(matches, entry, -1)

    assert matches == []


def test_append_bounded_newest_source_file_discards_worse_entries_when_full(tmp_path: Path) -> None:
    newest = tmp_path / "newest.epub"
    older = tmp_path / "older.epub"
    newest.write_bytes(b"newest")
    older.write_bytes(b"older")
    os.utime(newest, (1_700_000_100, 1_700_000_100))
    os.utime(older, (1_700_000_000, 1_700_000_000))

    entries = {
        entry.path.name: entry
        for entry in iter_visible_source_files(tmp_path, suffixes={".epub"})
    }
    matches = [entries["newest.epub"]]

    append_bounded_newest_source_file(matches, entries["older.epub"], 1)

    assert [entry.path.name for entry in matches] == ["newest.epub"]


def test_walk_visible_source_files_uses_safe_root_stat_instead_of_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ebook = tmp_path / "latest.epub"
    ebook.write_bytes(b"ebook")
    original_exists = Path.exists

    def fake_exists(path: Path, *args, **kwargs):
        if path == tmp_path:
            raise OSError("transient NAS exists failure")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", fake_exists)

    results = walk_visible_source_files(tmp_path, suffixes={"epub"})

    assert [entry.path for entry in results] == [ebook]
    assert results[0].stat.st_size == len(b"ebook")


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
