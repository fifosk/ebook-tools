"""Cross-filesystem aware atomic move utilities."""

from __future__ import annotations

import hashlib
import os
import shutil
import unicodedata
from pathlib import Path
from typing import Iterable, Tuple
from uuid import uuid4


class AtomicMoveError(RuntimeError):
    """Raised when a move operation cannot be completed safely."""


class ChecksumMismatchError(AtomicMoveError):
    """Raised when source and destination checksums do not match."""


_IGNORED_NAMES = {
    ".DS_Store",
}


def _iter_files(root: Path) -> Iterable[Tuple[Path, Path]]:
    if root.is_file():
        if root.name not in _IGNORED_NAMES:
            yield Path("."), root
        return

    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name not in _IGNORED_NAMES and not path.name.startswith("._"):
            yield path.relative_to(root), path


def _compute_checksum(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _normalized_rel_path(rel_path: Path) -> str:
    rel_string = rel_path.as_posix()
    if rel_string == "./":
        rel_string = "."
    return unicodedata.normalize("NFC", rel_string)


def _verify_copy(src: Path, dst: Path, algorithm: str) -> None:
    src_index: dict[str, tuple[Path, Path]] = {}
    for rel_path, file_path in _iter_files(src):
        key = _normalized_rel_path(rel_path)
        if key in src_index:
            raise ChecksumMismatchError(f"Duplicate source file path after normalization: {rel_path}")
        src_index[key] = (rel_path, file_path)

    dst_index: dict[str, tuple[Path, Path]] = {}
    for rel_path, file_path in _iter_files(dst):
        key = _normalized_rel_path(rel_path)
        if key in dst_index:
            raise ChecksumMismatchError(
                f"Duplicate destination file path after normalization: {rel_path}"
            )
        dst_index[key] = (rel_path, file_path)

    missing = sorted(set(src_index) - set(dst_index))
    extra = sorted(set(dst_index) - set(src_index))
    if missing or extra:
        summary_parts = []
        if missing:
            summary_parts.append(f"missing={missing[:5]}")
        if extra:
            summary_parts.append(f"extra={extra[:5]}")
        summary = ", ".join(summary_parts) if summary_parts else "unknown"
        raise ChecksumMismatchError(f"Source and destination contain different files ({summary})")

    for key in sorted(src_index):
        src_rel, src_file = src_index[key]
        _, dst_file = dst_index[key]
        if _compute_checksum(src_file, algorithm) != _compute_checksum(dst_file, algorithm):
            raise ChecksumMismatchError(f"Checksum mismatch for {src_rel}")


def _same_filesystem(src: Path, dst_parent: Path) -> bool:
    try:
        return os.stat(src).st_dev == os.stat(dst_parent).st_dev
    except FileNotFoundError as exc:  # pragma: no cover - defensive
        raise AtomicMoveError(f"Cannot stat path during move: {exc}") from exc


def atomic_move(source: Path | str, destination: Path | str, *, checksum: str = "sha256") -> None:
    """Move ``source`` to ``destination`` safely, even across filesystems."""

    src_path = Path(source)
    dst_path = Path(destination)

    if not src_path.exists():
        raise FileNotFoundError(f"Source path {src_path} does not exist")

    dst_parent = dst_path.parent
    dst_parent.mkdir(parents=True, exist_ok=True)

    if dst_path.exists():
        raise AtomicMoveError(f"Destination path {dst_path} already exists")

    if _same_filesystem(src_path, dst_parent):
        src_path.replace(dst_path)
        return

    temp_name = f".tmp-{uuid4().hex}"
    temp_path = dst_parent / f"{dst_path.name}{temp_name}"

    try:
        if src_path.is_dir():
            shutil.copytree(src_path, temp_path)
        else:
            shutil.copy2(src_path, temp_path)

        _verify_copy(src_path, temp_path, checksum)
        temp_path.replace(dst_path)

        if src_path.is_dir():
            shutil.rmtree(src_path)
        else:
            src_path.unlink()
    except Exception:
        if temp_path.exists():
            if temp_path.is_dir():
                shutil.rmtree(temp_path, ignore_errors=True)
            else:
                try:
                    temp_path.unlink()
                except OSError:
                    pass
        raise
