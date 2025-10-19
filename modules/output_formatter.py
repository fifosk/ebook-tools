"""Utilities for formatting and exporting translation output files."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Iterable, Sequence

from ebooklib import epub
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from modules import config_manager as cfg
from modules import logging_manager as log_mgr

logger = log_mgr.logger


def prepare_output_directory(
    input_file: str,
    book_author: str | None,
    book_title: str | None,
    source_language_code: str,
    target_language_code: str,
    *,
    context: cfg.RuntimeContext | None = None,
) -> tuple[str, str, str]:
    """Create and return the directory and base filenames for batch exports."""
    author = (book_author or "Unknown_Author").strip() or "Unknown_Author"
    title = (book_title or "Unknown_Book").strip() or "Unknown_Book"

    safe_author = re.sub(r"\s+", "_", author)
    safe_title = re.sub(r"\s+", "_", title)

    folder_name = f"{safe_author}_{safe_title}_{source_language_code}_{target_language_code}"
    folder_name = re.sub(r"_+", "_", folder_name).strip("_")

    context = context or cfg.get_runtime_context(None)
    if context is not None:
        ebooks_root = context.output_dir
    else:
        ebooks_root = cfg.resolve_directory(None, cfg.DEFAULT_OUTPUT_RELATIVE)

    base_dir = ebooks_root / folder_name
    base_dir.mkdir(parents=True, exist_ok=True)

    base_output = base_dir / f"{folder_name}.html"
    return str(base_dir), folder_name, str(base_output)


def write_html_file(filename: str | os.PathLike[str], content_list: Iterable[str]) -> None:
    """Persist the provided blocks into a simple HTML document."""
    try:
        path = Path(filename)
        with path.open("w", encoding="utf-8") as handle:
            handle.write("<html>\n<head>\n<meta charset='utf-8'>\n<title>Translation Output</title>\n</head>\n<body>\n")
            for block in content_list:
                handle.write(f"<p>{str(block).replace(chr(10), '<br>')}</p>\n")
            handle.write("</body>\n</html>")
    except Exception as exc:  # pragma: no cover - log for debugging only
        logger.debug("Error writing HTML file '%s': %s", filename, exc)


def write_pdf_file(
    filename: str | os.PathLike[str],
    content_list: Iterable[str],
    target_language: str,
) -> None:
    """Persist the provided blocks into a PDF document with unicode font support."""
    try:
        font_path = None
        if sys.platform == "darwin":
            font_path = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
        else:
            for candidate in [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "C:/Windows/Fonts/arialuni.ttf",
            ]:
                if os.path.exists(candidate):
                    font_path = candidate
                    break

        if font_path and os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont("UnicodeFont", font_path))
            pdfmetrics.registerFontFamily("UnicodeFont", normal="UnicodeFont")
        else:
            logger.debug(
                "Unicode font file not found; PDF output may not render non-Latin characters correctly."
            )
            pdfmetrics.registerFont(TTFont("UnicodeFont", "Helvetica"))
            pdfmetrics.registerFontFamily("UnicodeFont", normal="UnicodeFont")

        styles = getSampleStyleSheet()
        styles["Normal"].fontName = "UnicodeFont"
        document = SimpleDocTemplate(str(filename), pagesize=letter)
        story: list = []
        for block in content_list:
            story.append(Paragraph(str(block).replace(chr(10), "<br>"), styles["Normal"]))
            story.append(Spacer(1, 12))
        document.build(story)
    except Exception as exc:  # pragma: no cover - log for debugging only
        logger.debug("Error writing PDF file '%s': %s", filename, exc)


def write_epub_file(
    filename: str | os.PathLike[str],
    content_list: Iterable[str],
    book_title: str,
) -> None:
    """Create a minimal EPUB document containing the provided blocks."""
    try:
        book = epub.EpubBook()
        book.set_identifier("id123456")
        book.set_title(book_title)
        book.set_language("en")
        book.add_author("Translation Bot")

        chapter = epub.EpubHtml(title="Full Translation", file_name="full.xhtml", lang="en")
        chapter_content = "<html><head><meta charset='utf-8'/></head><body>\n"
        for block in content_list:
            chapter_content += f"<p>{str(block).replace(chr(10), '<br>')}</p>\n"
        chapter_content += "</body></html>"
        chapter.content = chapter_content

        book.add_item(chapter)
        book.toc = (epub.Link("full.xhtml", "Full Translation", "full"),)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav", chapter]

        epub.write_epub(str(filename), book)
    except Exception as exc:  # pragma: no cover - log for debugging only
        logger.debug("Error writing EPUB file '%s': %s", filename, exc)


def format_sentence_range(start: int, end: int, total_sentences: int) -> str:
    """Return a zero-padded range string based on the total sentence count."""

    max_value = max(total_sentences, start, end, 1)
    width = len(str(max_value))
    return f"{start:0{width}d}-{end:0{width}d}"


def export_batch_documents(
    base_dir: str,
    base_name: str,
    batch_start: int,
    batch_end: int,
    written_blocks: Sequence[str],
    target_language: str,
    total_sentences: int,
    *,
    output_html: bool = True,
    output_pdf: bool = False,
) -> dict[str, str]:
    """Write per-batch HTML/PDF documents and return their paths."""
    created: dict[str, str] = {}
    if not written_blocks:
        return created

    base_path = Path(base_dir)
    range_fragment = format_sentence_range(batch_start, batch_end, total_sentences)

    if output_html:
        html_path = base_path / f"{range_fragment}_{base_name}.html"
        write_html_file(html_path, written_blocks)
        created["html"] = str(html_path)
    if output_pdf:
        pdf_path = base_path / f"{range_fragment}_{base_name}.pdf"
        write_pdf_file(pdf_path, written_blocks, target_language)
        created["pdf"] = str(pdf_path)
    return created


def compute_stitched_basename(input_file: str, target_languages: Sequence[str]) -> str:
    """Return the base filename used for stitched outputs."""
    base = Path(input_file).stem
    target_lang_str = "_".join(target_languages)
    return f"{target_lang_str}_{base}" if target_lang_str else base


def stitch_full_output(
    base_dir: str,
    start_sentence: int,
    final_sentence: int,
    stitched_basename: str,
    written_blocks: Sequence[str],
    target_language: str,
    total_sentences: int,
    *,
    output_html: bool = True,
    output_pdf: bool = False,
    epub_title: str | None = None,
) -> dict[str, str]:
    """Generate stitched HTML, PDF, and EPUB documents from collected blocks."""
    created: dict[str, str] = {}
    if not written_blocks:
        logger.debug("No written blocks available to stitch final documents.")
        return created

    base_path = Path(base_dir)
    range_fragment = format_sentence_range(start_sentence, final_sentence, total_sentences)
    epub_title = epub_title or f"Stitched Translation: {range_fragment} {stitched_basename}"

    if output_html:
        html_path = base_path / f"{range_fragment}_{stitched_basename}.html"
        write_html_file(html_path, written_blocks)
        created["html"] = str(html_path)
    if output_pdf:
        pdf_path = base_path / f"{range_fragment}_{stitched_basename}.pdf"
        write_pdf_file(pdf_path, written_blocks, target_language)
        created["pdf"] = str(pdf_path)

    epub_path = base_path / f"{range_fragment}_{stitched_basename}.epub"
    write_epub_file(epub_path, written_blocks, epub_title)
    created["epub"] = str(epub_path)
    return created
