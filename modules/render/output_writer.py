"""Utilities for staging render outputs on RAM-backed storage."""
from __future__ import annotations

import errno
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

from .context import RenderBatchContext


@dataclass(slots=True)
class DeferredBatchWriter:
    """Stage rendered batch artifacts in temporary storage before syncing."""

    final_dir: Path
    batch_context: RenderBatchContext
    cleanup: bool = True
    _work_dir: Path = field(init=False, repr=False)
    _staged: Dict[Path, Path] = field(init=False, repr=False, default_factory=dict)
    _using_temp: bool = field(init=False, repr=False)

    def __post_init__(self) -> None:
        temp_dir = self.batch_context.temp_dir
        self.final_dir = Path(self.final_dir)
        self.final_dir.mkdir(parents=True, exist_ok=True)
        if temp_dir is not None:
            self._work_dir = temp_dir
            self._using_temp = True
        else:
            self._work_dir = self.final_dir
            self._using_temp = False
        self._work_dir.mkdir(parents=True, exist_ok=True)

    @property
    def work_dir(self) -> Path:
        """Return the directory where intermediate files should be written."""

        return self._work_dir

    @property
    def using_temp_storage(self) -> bool:
        """Return ``True`` if a RAM-disk is being used for staging."""

        return self._using_temp

    def stage(self, path: Path | str) -> Path:
        """Register ``path`` for synchronization and return its final destination."""

        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self._work_dir / candidate

        if self._using_temp:
            try:
                relative = candidate.relative_to(self._work_dir)
            except ValueError as exc:  # pragma: no cover - defensive guard
                raise ValueError("Staged path must be located within the work directory") from exc
            destination = self.final_dir / relative
            self._staged[candidate] = destination
        else:
            destination = candidate
        return destination

    def commit(self) -> None:
        """Sync staged files to the final directory and cleanup temporary data."""

        if not self._using_temp:
            return
        try:
            for source, destination in list(self._staged.items()):
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(destination))
        except OSError as exc:
            if exc.errno == errno.ENOSPC:
                raise
            raise
        finally:
            self._cleanup_work_dir()
            self._staged.clear()

    def rollback(self) -> None:
        """Remove any staged artifacts without syncing them to the final directory."""

        if self._using_temp:
            self._cleanup_work_dir()
        self._staged.clear()

    def _cleanup_work_dir(self) -> None:
        if not self.cleanup:
            return
        if not self._work_dir.exists():
            return
        if self._using_temp:
            shutil.rmtree(self._work_dir, ignore_errors=True)


__all__ = ["DeferredBatchWriter"]
