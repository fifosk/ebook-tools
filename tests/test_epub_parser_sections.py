from pathlib import Path

import ebooklib
import pytest
from ebooklib import epub

from modules import epub_parser

pytestmark = pytest.mark.pipeline


class FakeHtml(epub.EpubHtml):
    def __init__(
        self,
        *,
        uid: str,
        file_name: str,
        content: str,
        title: str = "",
        item_type: int = ebooklib.ITEM_DOCUMENT,
        properties: tuple[str, ...] = (),
    ) -> None:
        self._uid = uid
        self.file_name = file_name
        self.title = title
        self._content = content.encode("utf-8")
        self._item_type = item_type
        self.properties = list(properties)

    def get_id(self) -> str:
        return self._uid

    def get_content(self) -> bytes:
        return self._content

    def get_type(self) -> int:
        return self._item_type


class FakeBook:
    def __init__(self, *, items: list[FakeHtml], spine: list[object], toc: object = ()) -> None:
        self._items = items
        self.spine = spine
        self.toc = toc

    def get_items(self) -> list[FakeHtml]:
        return self._items


def _content(title: str, body: str) -> str:
    return f"<html><body><h1>{title}</h1><p>{body}</p></body></html>"


def _nav() -> str:
    return (
        "<html xmlns:epub=\"http://www.idpf.org/2007/ops\"><body>"
        "<nav epub:type=\"toc\"><h1>Table of Contents</h1></nav>"
        "</body></html>"
    )


def test_extract_sections_uses_spine_order_and_skips_navigation(tmp_path, monkeypatch):
    epub_path = tmp_path / "sample.epub"
    epub_path.write_text("placeholder", encoding="utf-8")
    nav = FakeHtml(
        uid="nav",
        file_name="nav.xhtml",
        content=_nav(),
        item_type=ebooklib.ITEM_NAVIGATION,
        properties=("nav",),
    )
    chapter_two = FakeHtml(
        uid="chapter-two",
        file_name="chapter2.xhtml",
        title="Chapter Two",
        content=_content("Chapter Two", "Second content."),
    )
    chapter_one = FakeHtml(
        uid="chapter-one",
        file_name="chapter1.xhtml",
        title="Chapter One",
        content=_content("Chapter One", "First content."),
    )
    appendix = FakeHtml(
        uid="appendix",
        file_name="appendix.xhtml",
        title="Appendix",
        content=_content("Appendix", "Extra content."),
    )
    book = FakeBook(
        items=[nav, appendix, chapter_two, chapter_one],
        spine=["nav", ("chapter-one", "yes"), ("chapter-two", "yes")],
    )
    monkeypatch.setattr(epub_parser.epub, "read_epub", lambda *_args, **_kwargs: book)

    sections = epub_parser.extract_sections_from_epub(str(epub_path), books_dir=str(tmp_path))

    assert [section["title"] for section in sections] == [
        "Chapter One",
        "Chapter Two",
        "Appendix",
    ]
    assert [section["text"] for section in sections] == [
        "Chapter One First content.",
        "Chapter Two Second content.",
        "Appendix Extra content.",
    ]
    assert [section.get("spine_index") for section in sections] == [1, 2, None]
    assert all("Table of Contents" not in str(section["text"]) for section in sections)
