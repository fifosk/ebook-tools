"""Cross-filesystem aware atomic move utilities."""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from typing import Iterable, Tuple
from uuid import uuid4


class AtomicMoveError(RuntimeError):
    """Raised when a move operation cannot be completed safely."""


class ChecksumMismatchError(AtomicMoveError):
    """Raised when source and destination checksums do not match."""


def _iter_files(root: Path) -> Iterable[Tuple[Path, Path]]:
    if root.is_file():
        yield Path("."), root
        return

    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path.relative_to(root), path


def _compute_checksum(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _verify_copy(src: Path, dst: Path, algorithm: str) -> None:
    src_files = list(_iter_files(src))
    dst_files = list(_iter_files(dst))

    if len(src_files) != len(dst_files):
        raise ChecksumMismatchError("Source and destination contain a different number of files")

    for (src_rel, src_file), (dst_rel, dst_file) in zip(src_files, dst_files):
        if src_rel != dst_rel:
            raise ChecksumMismatchError(
                f"Mismatch in copied file paths: {src_rel} vs {dst_rel}"
            )
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
