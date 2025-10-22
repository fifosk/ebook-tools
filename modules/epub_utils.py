"""Utility helpers for creating synthetic EPUB files for testing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence
from uuid import uuid4
import zipfile

from xml.sax.saxutils import escape


_EPUB_MIMETYPE = "application/epub+zip"
_CONTAINER_XML = """<?xml version='1.0' encoding='utf-8'?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml" />
  </rootfiles>
</container>
"""


def _build_chapter_xhtml(sentences: Sequence[str]) -> str:
    body = "\n".join(f"    <p>{escape(sentence)}</p>" for sentence in sentences)
    return (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        "<html xmlns=\"http://www.w3.org/1999/xhtml\">\n"
        "  <head><title>Sample Chapter</title></head>\n"
        "  <body>\n"
        f"{body}\n"
        "  </body>\n"
        "</html>\n"
    )


def _build_nav_xhtml() -> str:
    return (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        "<html xmlns=\"http://www.w3.org/1999/xhtml\" xmlns:epub=\"http://www.idpf.org/2007/ops\">\n"
        "  <head><title>Table of Contents</title></head>\n"
        "  <body>\n"
        "    <nav epub:type=\"toc\" id=\"toc\">\n"
        "      <h1>Table of Contents</h1>\n"
        "      <ol>\n"
        "        <li><a href=\"chapter1.xhtml\">Chapter 1</a></li>\n"
        "      </ol>\n"
        "    </nav>\n"
        "  </body>\n"
        "</html>\n"
    )


def _build_content_opf(book_id: str) -> str:
    return (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        "<package xmlns=\"http://www.idpf.org/2007/opf\" version=\"3.0\" unique-identifier=\"bookid\">\n"
        "  <metadata xmlns:dc=\"http://purl.org/dc/elements/1.1/\">\n"
        "    <dc:identifier id=\"bookid\">urn:uuid:{} </dc:identifier>\n"
        "    <dc:title>Sample EPUB</dc:title>\n"
        "    <dc:language>en</dc:language>\n"
        "  </metadata>\n"
        "  <manifest>\n"
        "    <item id=\"toc\" href=\"nav.xhtml\" media-type=\"application/xhtml+xml\" properties=\"nav\"/>\n"
        "    <item id=\"chapter1\" href=\"chapter1.xhtml\" media-type=\"application/xhtml+xml\"/>\n"
        "  </manifest>\n"
        "  <spine>\n"
        "    <itemref idref=\"chapter1\"/>\n"
        "  </spine>\n"
        "</package>\n"
    ).format(book_id)


def create_epub_from_sentences(sentences: Iterable[str], output_path: Path | str) -> Path:
    """Create a minimal EPUB file containing ``sentences`` and return its path."""

    sentences = [str(sentence) for sentence in sentences]
    if not sentences:
        raise ValueError("At least one sentence is required to build an EPUB")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    book_id = str(uuid4())
    chapter_content = _build_chapter_xhtml(sentences)
    nav_content = _build_nav_xhtml()
    opf_content = _build_content_opf(book_id)
    sentences_payload = json.dumps({"sentences": sentences}, ensure_ascii=False, indent=2)

    with zipfile.ZipFile(output, "w") as zf:
        zf.writestr("mimetype", _EPUB_MIMETYPE, compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", _CONTAINER_XML, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/content.opf", opf_content, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/nav.xhtml", nav_content, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/chapter1.xhtml", chapter_content, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/sentences.json", sentences_payload, compress_type=zipfile.ZIP_DEFLATED)

    return output
