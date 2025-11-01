"""Library metadata management commands for the ebook-tools CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from .. import config_manager as cfg
from .. import logging_manager as log_mgr
from ..library import LibraryError, LibraryIndexer, LibraryNotFoundError, LibraryService
from ..services.file_locator import FileLocator

LOGGER = log_mgr.get_logger().getChild("cli.library")


def _create_library_service() -> LibraryService:
    library_root = cfg.get_library_root(create=True)
    locator = FileLocator()
    indexer = LibraryIndexer(library_root)
    return LibraryService(
        library_root=library_root,
        file_locator=locator,
        indexer=indexer,
        job_manager=None,
    )


def _filter_updates(args) -> Dict[str, Optional[str]]:
    updates: Dict[str, Optional[str]] = {}
    for field in ("title", "author", "genre", "language", "isbn"):
        value = getattr(args, field, None)
        if value is not None:
            updates[field] = value
    return updates


def execute_library_command(args) -> int:
    """Dispatch the ``ebook-tools library`` sub-commands."""

    service = _create_library_service()
    command = getattr(args, "library_command", None)

    if command == "refresh":
        job_id = args.job_id
        try:
            item = service.refresh_metadata(job_id)
        except LibraryNotFoundError:
            log_mgr.console_error(
                f"Library entry '{job_id}' not found.",
                logger_obj=LOGGER,
            )
            return 1
        except LibraryError as exc:
            log_mgr.console_error(str(exc), logger_obj=LOGGER)
            return 1

        log_mgr.console_info(
            "Refreshed metadata for '%s' — title: %s · author: %s",
            job_id,
            item.book_title or "Untitled",
            item.author or "Unknown Author",
            logger_obj=LOGGER,
        )
        return 0

    if command == "edit":
        job_id = args.job_id
        updates = _filter_updates(args)
        if not updates:
            log_mgr.console_error(
                "No metadata fields provided. Use --title/--author/--genre/--language to apply updates.",
                logger_obj=LOGGER,
            )
            return 1
        try:
            item = service.update_metadata(
                job_id,
                title=updates.get("title"),
                author=updates.get("author"),
                genre=updates.get("genre"),
                language=updates.get("language"),
                isbn=updates.get("isbn"),
            )
        except LibraryNotFoundError:
            log_mgr.console_error(
                f"Library entry '{job_id}' not found.",
                logger_obj=LOGGER,
            )
            return 1
        except LibraryError as exc:
            log_mgr.console_error(str(exc), logger_obj=LOGGER)
            return 1

        summary_parts = [
            f"title: {item.book_title or 'Untitled'}",
            f"author: {item.author or 'Unknown'}",
            f"genre: {item.genre or 'Unknown'}",
            f"language: {item.language}",
        ]
        log_mgr.console_info(
            "Updated metadata for '%s' (%s)",
            job_id,
            "; ".join(summary_parts),
            logger_obj=LOGGER,
        )
        return 0

    if command == "reupload":
        job_id = args.job_id
        source_path = Path(args.path)
        try:
            item = service.reupload_source_from_path(job_id, source_path)
        except LibraryNotFoundError:
            log_mgr.console_error(
                f"Library entry '{job_id}' not found.",
                logger_obj=LOGGER,
            )
            return 1
        except LibraryError as exc:
            log_mgr.console_error(str(exc), logger_obj=LOGGER)
            return 1

        log_mgr.console_info(
            "Reuploaded source for '%s' — source path: %s",
            job_id,
            item.source_path or "(unknown)",
            logger_obj=LOGGER,
        )
        return 0

    if command == "fetch-isbn":
        job_id = args.job_id
        isbn = args.isbn
        try:
            item = service.apply_isbn_metadata(job_id, isbn)
        except LibraryNotFoundError:
            log_mgr.console_error(
                f"Library entry '{job_id}' not found.",
                logger_obj=LOGGER,
            )
            return 1
        except LibraryError as exc:
            log_mgr.console_error(str(exc), logger_obj=LOGGER)
            return 1

        log_mgr.console_info(
            "Fetched ISBN metadata for '%s' — title: %s · author: %s",
            job_id,
            item.book_title or "Untitled",
            item.author or "Unknown Author",
            logger_obj=LOGGER,
        )
        return 0

    log_mgr.console_error(
        f"Unknown library command: {command}",
        logger_obj=LOGGER,
    )
    return 1


__all__ = ["execute_library_command"]
