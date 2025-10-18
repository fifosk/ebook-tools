"""Utilities for ensuring the temporary working directory is backed by RAM."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import Iterable, Optional, Tuple

from . import logging_manager as log_mgr

logger = log_mgr.get_logger()

_RAM_FS_TYPES = {"tmpfs", "ramfs"}
_DEFAULT_RAMDISK_SIZE_BYTES = 1024 ** 3  # 1 GiB


def ensure_ramdisk(path: os.PathLike[str] | str, *, size_bytes: int = _DEFAULT_RAMDISK_SIZE_BYTES) -> bool:
    """Ensure ``path`` is backed by a RAM disk of at least ``size_bytes``.

    Returns ``True`` when the directory is already on a RAM-backed filesystem or
    when mounting succeeds. Returns ``False`` if the current platform does not
    support automatic RAM disk management or if mounting fails.
    """

    target = Path(path).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    if _is_ramdisk(target):
        logger.debug("Temporary directory %s already resides on a RAM-backed filesystem.", target)
        return True

    if _has_required_capacity(target, size_bytes):
        logger.debug(
            "Temporary directory %s already has at least %s capacity; skipping RAM disk creation.",
            target,
            _format_size(size_bytes),
        )
        return True

    system = platform.system()
    if system == "Linux":
        return _mount_ramdisk_linux(target, size_bytes)

    if system == "Darwin":  # pragma: no cover - macOS-specific branch
        return _mount_ramdisk_macos(target, size_bytes)

    logger.info(
        "RAM disk automation is not supported on platform %s. Using directory %s on existing storage.",
        system,
        target,
    )
    return False


def _is_ramdisk(path: Path) -> bool:
    mount = _find_mount_for_path(path)
    if not mount:
        return False
    _device, _mount_point, fs_type = mount
    return fs_type.lower() in _RAM_FS_TYPES


def _find_mount_for_path(path: Path) -> Optional[Tuple[str, str, str]]:
    """Return the mount entry covering ``path`` if available."""

    try:
        mounts = list(_iter_proc_mounts())
    except FileNotFoundError:
        mounts = list(_iter_mount_command())

    if not mounts:
        return None

    target = path.resolve()
    best: Optional[Tuple[str, str, str]] = None
    best_length = -1

    for device, mount_point, fs_type in mounts:
        normalized_mount = Path(mount_point).resolve()
        try:
            target.relative_to(normalized_mount)
            length = len(str(normalized_mount))
            if length > best_length:
                best = (device, str(normalized_mount), fs_type)
                best_length = length
        except ValueError:
            continue

    return best


def _iter_proc_mounts() -> Iterable[Tuple[str, str, str]]:
    """Yield mount entries by reading ``/proc/self/mounts``."""

    with open("/proc/self/mounts", "r", encoding="utf-8") as mount_file:
        for line in mount_file:
            parts = line.strip().split()
            if len(parts) < 3:
                continue
            device, mount_point, fs_type = parts[:3]
            yield _decode_mount_token(device), _decode_mount_token(mount_point), fs_type


def _iter_mount_command() -> Iterable[Tuple[str, str, str]]:  # pragma: no cover - fallback path
    try:
        output = subprocess.check_output(["mount"], text=True)
    except (OSError, subprocess.CalledProcessError):
        return []

    entries = []
    for line in output.splitlines():
        if " on " not in line:
            continue
        head, rest = line.split(" on ", 1)
        if " (" not in rest:
            continue
        mount_point, tail = rest.split(" (", 1)
        fs_type = tail.split(",", 1)[0]
        entries.append((head.strip(), mount_point.strip(), fs_type.strip()))
    return entries


def _decode_mount_token(token: str) -> str:
    """Decode escape sequences found in ``/proc/self/mounts`` entries."""

    return (
        token.replace("\\040", " ")
        .replace("\\011", "\t")
        .replace("\\012", "\n")
        .replace("\\134", "\\")
    )


def _has_required_capacity(path: Path, size_bytes: int) -> bool:
    mount = _find_mount_for_path(path)
    if not mount:
        return False

    _device, mount_point, _fs_type = mount
    if Path(mount_point).resolve() != path.resolve():
        return False

    capacity = _filesystem_capacity_bytes(path)
    if capacity is None:
        return False

    return capacity >= size_bytes


def _filesystem_capacity_bytes(path: Path) -> Optional[int]:
    try:
        output = subprocess.check_output(["df", "-k", str(path)], text=True)
    except (OSError, subprocess.CalledProcessError):
        return None

    lines = output.strip().splitlines()
    if len(lines) < 2:
        return None

    parts = lines[1].split()
    if len(parts) < 2:
        return None

    try:
        blocks_kib = int(parts[1])
    except ValueError:
        return None

    return blocks_kib * 1024


def _mount_ramdisk_linux(target: Path, size_bytes: int) -> bool:
    size_option = f"size={size_bytes}"
    try:
        subprocess.run(
            [
                "mount",
                "-t",
                "tmpfs",
                "-o",
                size_option,
                "tmpfs",
                str(target),
            ],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.warning("Failed to mount tmpfs at %s: %s", target, exc)
        return False
    except FileNotFoundError:
        logger.warning("mount command not available; cannot create RAM disk at %s", target)
        return False

    if _is_ramdisk(target):
        logger.info(
            "Mounted tmpfs RAM disk at %s (%s).",
            target,
            _format_size(size_bytes),
        )
        return True
    logger.warning("tmpfs mount at %s did not appear in mount table.", target)
    return False


def _mount_ramdisk_macos(target: Path, size_bytes: int) -> bool:  # pragma: no cover - macOS specific
    block_count = max(1, size_bytes // 512)
    try:
        device = subprocess.check_output(
            ["hdiutil", "attach", "-nomount", f"ram://{block_count}"],
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.warning("Failed to allocate macOS RAM disk device: %s", exc)
        return False

    try:
        subprocess.run(
            ["diskutil", "eraseVolume", "HFS+", target.name or "RAMDisk", device],
            check=True,
            text=True,
        )
        subprocess.run(
            ["diskutil", "mount", "-mountPoint", str(target), device],
            check=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.warning("Failed to mount RAM disk %s at %s: %s", device, target, exc)
        return False

    if _is_ramdisk(target):
        logger.info(
            "Mounted macOS RAM disk at %s (%s).",
            target,
            _format_size(size_bytes),
        )
        return True

    logger.warning("macOS RAM disk at %s not detected after mount command.", target)
    return False


def _format_size(size_bytes: int) -> str:
    for unit in ("bytes", "KiB", "MiB", "GiB", "TiB"):
        if size_bytes < 1024 or unit == "TiB":
            return f"{size_bytes:.0f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.0f} TiB"


__all__ = ["ensure_ramdisk"]
