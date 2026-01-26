"""Lightweight orchestration layer for high-level library workflows."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

from modules import logging_manager
from modules.services.file_locator import FileLocator
from modules.services.job_manager import PipelineJobManager

from .library_metadata import LibraryMetadataManager
from .library_models import LibraryEntry, LibraryQuery
from .library_repository import LibraryRepository
from .library_sync import (
    LibraryConflictError,
    LibraryError,
    LibraryNotFoundError,
    LibrarySearchResult,
    LibrarySync,
)

LOGGER = logging_manager.get_logger().getChild("library.service")


@dataclass
class LibraryOverview:
    """Aggregated snapshot returned by :meth:`LibraryService.get_library_overview`."""

    total: int
    finished: int
    paused: int
    languages: Dict[str, int]


class LibraryService:
    """Expose high-level entry points backed by the modular library subsystems."""

    def __init__(
        self,
        *,
        library_root: Path,
        file_locator: Optional[FileLocator] = None,
        repository: Optional[LibraryRepository] = None,
        metadata_manager: Optional[LibraryMetadataManager] = None,
        job_manager: Optional[PipelineJobManager] = None,
    ) -> None:
        locator = file_locator or FileLocator()
        repo = repository or LibraryRepository(library_root)
        metadata = metadata_manager or LibraryMetadataManager(library_root)
        self._sync = LibrarySync(
            library_root=library_root,
            file_locator=locator,
            repository=repo,
            metadata_manager=metadata,
            job_manager=job_manager,
        )
        self._repository = repo
        self._metadata_manager = metadata

    @property
    def sync(self) -> LibrarySync:
        """Expose the `LibrarySync` component for lower-level operations."""

        return self._sync

    @property
    def repository(self) -> LibraryRepository:
        return self._repository

    def get_library_overview(self) -> LibraryOverview:
        """Return aggregate counts for the current library."""

        entries = list(self._repository.iter_entries())
        total = len(entries)
        finished = sum(1 for entry in entries if entry.status == "finished")
        paused = sum(1 for entry in entries if entry.status == "paused")
        languages: Dict[str, int] = {}
        for entry in entries:
            languages[entry.language] = languages.get(entry.language, 0) + 1
        return LibraryOverview(
            total=total,
            finished=finished,
            paused=paused,
            languages=dict(sorted(languages.items())),
        )

    def refresh_metadata(self, entry_id: str) -> LibraryEntry:
        """Delegate to :class:`LibrarySync` for metadata refresh."""

        return self._sync.refresh_metadata(entry_id)

    def enrich_metadata(self, entry_id: str, *, force: bool = False) -> LibraryEntry:
        """Delegate to :class:`LibrarySync` for metadata enrichment from external sources."""

        return self._sync.enrich_metadata(entry_id, force=force)

    def rebuild_index(self) -> int:
        """Rebuild the SQLite index from filesystem state."""

        count = self._repository.sync_from_filesystem(self._sync.library_root)
        LOGGER.info("Rebuilt library index with %s entries", count)
        return count

    def import_book(self, source_path: Path) -> LibraryEntry:
        """Import an external directory into the library."""

        resolved_source = Path(source_path).expanduser()
        if not resolved_source.exists():
            raise LibraryNotFoundError(f"Source path {resolved_source} does not exist")

        metadata_path = resolved_source / "metadata" / "job.json"
        if not metadata_path.exists():
            raise LibraryError("Source path does not contain metadata/job.json")

        metadata = self._repository.load_metadata(resolved_source)
        job_id = str(metadata.get("job_id") or "").strip()
        if not job_id:
            raise LibraryError("Source metadata must include a job_id")

        target_root = self._sync.resolve_library_path(metadata, job_id)
        if target_root.exists():
            raise LibraryConflictError(f"Library target {target_root} already exists")

        target_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(resolved_source, target_root)
        entry = self._sync.build_entry(metadata, target_root)
        self._repository.add_entry(entry)
        return entry

    def export_entry(self, entry_id: str, *, destination: Optional[Path] = None) -> Path:
        """Export a library entry into a temporary archive."""

        entry = self._repository.get_entry_by_id(entry_id)
        if entry is None:
            raise LibraryNotFoundError(f"Library entry {entry_id} not found")

        source = Path(entry.library_path)
        if not source.exists():
            raise LibraryNotFoundError(f"Library entry {entry_id} is missing on disk")

        if destination is None:
            temp_dir = Path(tempfile.mkdtemp(prefix=f"library-export-{entry_id}-"))
            destination = temp_dir / f"{entry_id}.zip"
        else:
            destination = Path(destination).expanduser()
            destination.parent.mkdir(parents=True, exist_ok=True)

        shutil.make_archive(str(destination.with_suffix("")), "zip", root_dir=source)
        return destination.with_suffix(".zip")


def get_library_service(
    *,
    library_root: Optional[Path] = None,
    file_locator: Optional[FileLocator] = None,
    job_manager: Optional[PipelineJobManager] = None,
) -> LibraryService:
    """Factory helper mirroring the dependency wiring used by FastAPI routes."""

    if library_root is None:
        from modules import config_manager as cfg  # Local import to avoid cycles

        library_root = cfg.get_library_root(create=True)
    return LibraryService(
        library_root=library_root,
        file_locator=file_locator,
        job_manager=job_manager,
    )


__all__ = [
    "LibraryConflictError",
    "LibraryError",
    "LibraryNotFoundError",
    "LibraryOverview",
    "LibrarySearchResult",
    "LibraryService",
    "get_library_service",
]
