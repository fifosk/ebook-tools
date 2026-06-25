import os
from pathlib import Path

from modules.core import ingestion


class DummyPipelineConfig:
    def __init__(self, tmp_path: Path, *, max_words: int = 10, split_on_comma_semicolon: bool = False):
        self.working_dir = tmp_path / "work"
        self.books_dir = tmp_path / "books"
        self.max_words = max_words
        self.split_on_comma_semicolon = split_on_comma_semicolon
        self.derived_runtime_dirname = "runtime"
        self.derived_refined_filename_template = "{base_name}_refined.json"
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.books_dir.mkdir(parents=True, exist_ok=True)

    def ensure_runtime_dir(self) -> Path:
        runtime_dir = self.working_dir / self.derived_runtime_dirname
        runtime_dir.mkdir(parents=True, exist_ok=True)
        return runtime_dir

    def resolved_books_dir(self) -> Path:
        return self.books_dir


def _book_path(config: DummyPipelineConfig) -> Path:
    path = config.books_dir / "sample.epub"
    path.write_text("placeholder", encoding="utf-8")
    return path


def test_runtime_cache_paths_include_resolved_input_identity(tmp_path):
    config = DummyPipelineConfig(tmp_path)
    first_dir = config.books_dir / "first"
    second_dir = config.books_dir / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first_path = first_dir / "sample.epub"
    second_path = second_dir / "sample.epub"
    first_path.write_text("first", encoding="utf-8")
    second_path.write_text("second", encoding="utf-8")

    first_refined = ingestion.refined_list_output_path(str(first_path), config)
    second_refined = ingestion.refined_list_output_path(str(second_path), config)
    first_index = ingestion.content_index_output_path(str(first_path), config)
    second_index = ingestion.content_index_output_path(str(second_path), config)

    assert first_refined != second_refined
    assert first_index != second_index
    assert first_refined.name.startswith("sample_")
    assert first_index.name.startswith("sample_")


def _patch_sections(monkeypatch, calls: list[str], *, title: str = "Chapter One") -> None:
    def fake_extract_sections(input_file: str, books_dir: Path | None = None):
        calls.append(input_file)
        return [
            {
                "id": "chapter-1",
                "title": title,
                "text": "Alpha. Beta.",
                "href": "chapter.xhtml",
                "toc_label": title,
                "spine_index": 0,
            }
        ]

    monkeypatch.setattr(ingestion, "extract_sections_from_epub", fake_extract_sections)
    monkeypatch.setattr(
        ingestion,
        "split_text_into_sentences",
        lambda text, **_: ["Alpha.", "Beta."] if text == "Alpha. Beta." else [],
    )


def test_get_refined_sentences_reuses_valid_runtime_cache(tmp_path, monkeypatch):
    config = DummyPipelineConfig(tmp_path)
    path = _book_path(config)
    calls: list[str] = []

    monkeypatch.setattr(ingestion, "extract_sections_from_epub", lambda *_, **__: [])

    def fake_extract_text(input_file: str):
        calls.append(input_file)
        return "Alpha. Beta."

    monkeypatch.setattr(ingestion, "extract_text_from_epub", fake_extract_text)
    monkeypatch.setattr(
        ingestion,
        "split_text_into_sentences",
        lambda text, **_: ["Alpha.", "Beta."] if text == "Alpha. Beta." else [],
    )

    first, first_updated = ingestion.get_refined_sentences(str(path), config)
    second, second_updated = ingestion.get_refined_sentences(str(path), config)

    assert first == ["Alpha.", "Beta."]
    assert second == first
    assert first_updated is True
    assert second_updated is False
    assert calls == [str(path)]


def test_get_refined_sentences_invalidates_cache_when_source_mtime_changes(tmp_path, monkeypatch):
    config = DummyPipelineConfig(tmp_path)
    path = _book_path(config)
    calls: list[str] = []

    monkeypatch.setattr(ingestion, "extract_sections_from_epub", lambda *_, **__: [])

    def fake_extract_text(input_file: str):
        calls.append(input_file)
        return "Alpha. Beta."

    monkeypatch.setattr(ingestion, "extract_text_from_epub", fake_extract_text)
    monkeypatch.setattr(
        ingestion,
        "split_text_into_sentences",
        lambda text, **_: ["Alpha.", "Beta."] if text == "Alpha. Beta." else [],
    )

    ingestion.get_refined_sentences(str(path), config)
    original_mtime = path.stat().st_mtime
    os.utime(path, (original_mtime + 20, original_mtime + 20))
    _, refreshed = ingestion.get_refined_sentences(str(path), config)

    assert refreshed is True
    assert calls == [str(path), str(path)]


def test_get_content_index_reuses_valid_runtime_cache(tmp_path, monkeypatch):
    config = DummyPipelineConfig(tmp_path)
    path = _book_path(config)
    calls: list[str] = []
    _patch_sections(monkeypatch, calls)

    first = ingestion.get_content_index(str(path), config, ["Alpha.", "Beta."])
    second = ingestion.get_content_index(str(path), config, ["Alpha.", "Beta."])

    assert first == second
    assert first["chapters"][0]["title"] == "Chapter One"
    assert calls == [str(path)]
    assert ingestion.content_index_output_path(str(path), config).exists()


def test_get_content_index_invalidates_cache_when_source_mtime_changes(tmp_path, monkeypatch):
    config = DummyPipelineConfig(tmp_path)
    path = _book_path(config)
    calls: list[str] = []
    _patch_sections(monkeypatch, calls)

    ingestion.get_content_index(str(path), config, ["Alpha.", "Beta."])
    original_mtime = path.stat().st_mtime
    os.utime(path, (original_mtime + 20, original_mtime + 20))
    ingestion.get_content_index(str(path), config, ["Alpha.", "Beta."])

    assert calls == [str(path), str(path)]


def test_get_content_index_invalidates_cache_when_split_settings_change(tmp_path, monkeypatch):
    config = DummyPipelineConfig(tmp_path)
    path = _book_path(config)
    calls: list[str] = []
    _patch_sections(monkeypatch, calls)

    ingestion.get_content_index(str(path), config, ["Alpha.", "Beta."])
    config.max_words = 4
    ingestion.get_content_index(str(path), config, ["Alpha.", "Beta."])

    assert calls == [str(path), str(path)]


def test_get_content_index_invalidates_cache_when_refined_sentences_change(
    tmp_path,
    monkeypatch,
):
    config = DummyPipelineConfig(tmp_path)
    path = _book_path(config)
    calls: list[str] = []
    _patch_sections(monkeypatch, calls)

    ingestion.get_content_index(str(path), config, ["Alpha.", "Beta."])
    ingestion.get_content_index(str(path), config, ["Alpha.", "Gamma."])

    assert calls == [str(path), str(path)]


def test_get_content_index_force_refresh_bypasses_cache(tmp_path, monkeypatch):
    config = DummyPipelineConfig(tmp_path)
    path = _book_path(config)
    calls: list[str] = []
    _patch_sections(monkeypatch, calls)

    ingestion.get_content_index(str(path), config, ["Alpha.", "Beta."])
    ingestion.get_content_index(str(path), config, ["Alpha.", "Beta."], force_refresh=True)

    assert calls == [str(path), str(path)]


def test_build_content_index_marks_mismatched_refined_sentences_approximate(
    tmp_path,
    monkeypatch,
):
    config = DummyPipelineConfig(tmp_path)
    path = _book_path(config)

    monkeypatch.setattr(
        ingestion,
        "extract_sections_from_epub",
        lambda *_args, **_kwargs: [
            {
                "id": "chapter-1",
                "title": "Chapter One",
                "text": "Alpha. Gamma.",
            }
        ],
    )
    monkeypatch.setattr(
        ingestion,
        "split_text_into_sentences",
        lambda text, **_: ["Alpha.", "Gamma."] if text == "Alpha. Gamma." else [],
    )

    content_index = ingestion.build_content_index(str(path), config, ["Alpha.", "Beta."])

    assert content_index["alignment"]["status"] == "approximate"
    assert content_index["chapters"][0]["start_sentence"] == 1
    assert content_index["chapters"][0]["end_sentence"] == 2


def test_build_content_index_ranges_do_not_exceed_total_sentences_when_sections_overrun(
    tmp_path,
    monkeypatch,
):
    config = DummyPipelineConfig(tmp_path)
    path = _book_path(config)

    monkeypatch.setattr(
        ingestion,
        "extract_sections_from_epub",
        lambda *_args, **_kwargs: [
            {
                "id": "chapter-1",
                "title": "Chapter One",
                "text": "Alpha. Beta. Gamma.",
            }
        ],
    )
    monkeypatch.setattr(
        ingestion,
        "split_text_into_sentences",
        lambda text, **_: (
            ["Alpha.", "Beta.", "Gamma."] if text == "Alpha. Beta. Gamma." else []
        ),
    )

    content_index = ingestion.build_content_index(str(path), config, ["Alpha.", "Beta."])
    chapter = content_index["chapters"][0]

    assert content_index["alignment"]["status"] == "approximate"
    assert chapter["start_sentence"] == 1
    assert chapter["end_sentence"] == 2
    assert chapter["range_truncated"] is True


def test_refined_sentences_and_content_index_keep_adjacent_sections_contiguous(
    tmp_path,
    monkeypatch,
):
    config = DummyPipelineConfig(tmp_path)
    path = _book_path(config)

    sections = [
        {
            "id": "chapter-1",
            "title": "Chapter One",
            "text": "First start. First end.",
            "href": "chapter-1.xhtml",
            "spine_index": 0,
        },
        {
            "id": "chapter-2",
            "title": "Chapter Two",
            "text": "Second start. Second end.",
            "href": "chapter-2.xhtml",
            "spine_index": 1,
        },
    ]
    sentence_map = {
        "First start. First end.": ["First start.", "First end."],
        "Second start. Second end.": ["Second start.", "Second end."],
    }
    monkeypatch.setattr(
        ingestion,
        "extract_sections_from_epub",
        lambda *_args, **_kwargs: sections,
    )
    monkeypatch.setattr(
        ingestion,
        "split_text_into_sentences",
        lambda text, **_: sentence_map.get(text, []),
    )

    refined, refreshed = ingestion.get_refined_sentences(str(path), config)
    content_index = ingestion.build_content_index(str(path), config, refined)

    assert refreshed is True
    assert refined == [
        "First start.",
        "First end.",
        "Second start.",
        "Second end.",
    ]
    assert content_index["alignment"]["status"] == "exact"
    assert content_index["total_sentences"] == 4
    assert content_index["sources"]["order"] == "spine"
    assert [
        (chapter["start_sentence"], chapter["end_sentence"])
        for chapter in content_index["chapters"]
    ] == [(1, 2), (3, 4)]
