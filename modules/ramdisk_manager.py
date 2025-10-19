"""Utilities for ensuring the temporary working directory is backed by RAM."""

from __future__ import annotations

import os
import platform
import plistlib
import shutil
import subprocess
import time
from pathlib import Path
from typing import Iterable, Optional, Tuple

from . import logging_manager as log_mgr

logger = log_mgr.get_logger()

_RAM_FS_TYPES = {"tmpfs", "ramfs"}
_DEFAULT_RAMDISK_SIZE_BYTES = 1024 ** 3  # 1 GiB
_MACOS_DEFAULT_MOUNT_POINT = Path("/Volumes/tmp")


def ensure_ramdisk(
    path: os.PathLike[str] | str,
    *,
    size_bytes: int = _DEFAULT_RAMDISK_SIZE_BYTES,
) -> bool:
    """Ensure ``path`` is backed by a RAM disk of at least ``size_bytes``.

    Returns ``True`` when the directory is already on a RAM-backed filesystem or
    when mounting succeeds. Returns ``False`` if the current platform does not
    support automatic RAM disk management or if mounting fails.
    """

    target = Path(path).expanduser()
    if not target.is_absolute():
        target = target.resolve()

    if target.is_symlink():
        if not target.exists():
            try:
                target.unlink()
            except OSError as exc:  # pragma: no cover - defensive logging
                logger.warning("Failed to remove broken symlink %s: %s", target, exc)
                return False
            target.parent.mkdir(parents=True, exist_ok=True)
            target.mkdir(parents=True, exist_ok=True)
    elif target.exists():
        if not target.is_dir():
            if target.is_file():
                target.unlink()
            else:
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
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
        desired_mount_point = _MACOS_DEFAULT_MOUNT_POINT
        mount_target = desired_mount_point if _prepare_macos_mount_point(desired_mount_point) else None

        actual_mount = _mount_ramdisk_macos(mount_target, size_bytes)
        if actual_mount is None:
            return False

        if target.resolve() != actual_mount.resolve():
            if not _replace_with_symlink(target, actual_mount):
                return False

        if _wait_for_ramdisk(actual_mount):
            return True

        if _wait_for_ramdisk(target):
            return True

        return False

    logger.info(
        "RAM disk automation is not supported on platform %s. Using directory %s on existing storage.",
        system,
        target,
    )
    return False


def ensure_standard_directory(path: os.PathLike[str] | str) -> Path:
    """Ensure ``path`` refers to a regular directory on persistent storage."""

    target = Path(path).expanduser()
    if not target.is_absolute():
        target = target.resolve()

    resolved_symlink_target: Optional[Path] = None
    if target.is_symlink():
        try:
            resolved_symlink_target = target.resolve(strict=True)
        except FileNotFoundError:
            resolved_symlink_target = None
        try:
            target.unlink()
        except OSError as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to remove symlink %s: %s", target, exc)
            return target
        if resolved_symlink_target is not None:
            _teardown_ramdisk_mount(resolved_symlink_target)

    if target.exists() and target.is_dir() and _is_ramdisk(target):
        _teardown_ramdisk_mount(target)
        if target.exists() and target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)

    if target.exists() and not target.is_dir():
        if target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
        _teardown_ramdisk_mount(target)

    target.mkdir(parents=True, exist_ok=True)
    return target


def _is_ramdisk(path: Path) -> bool:
    mount = _find_mount_for_path(path)
    if not mount:
        return False
    device, mount_point, fs_type = mount
    if fs_type.lower() in _RAM_FS_TYPES:
        return True

    if platform.system() == "Darwin":  # pragma: no cover - macOS specific detection
        info_by_device = _get_diskutil_info(device)
        if _info_indicates_ramdisk(info_by_device):
            return True

        info_by_mount = _get_diskutil_info(mount_point)
        if _info_indicates_ramdisk(info_by_mount):
            return True

    return False


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


def _mount_ramdisk_macos(target: Optional[Path], size_bytes: int) -> Optional[Path]:  # pragma: no cover - macOS specific
    existing_device = _find_existing_macos_ramdisk_identifier(size_bytes)
    mount_path: Optional[Path] = None

    if existing_device:
        mount_path = _ensure_macos_mount(existing_device, target)
        if mount_path is not None:
            logger.info(
                "Mounted existing macOS RAM disk %s at %s (%s).",
                existing_device,
                mount_path,
                _format_size(size_bytes),
            )
            return mount_path

    block_count = max(1, size_bytes // 512)
    try:
        device_path = subprocess.check_output(
            ["hdiutil", "attach", "-nomount", f"ram://{block_count}"],
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.warning("Failed to allocate macOS RAM disk device: %s", exc)
        return None

    device_identifier = Path(device_path).name
    device_node = Path("/dev") / device_identifier
    if not device_node.exists():
        logger.warning("Allocated RAM disk device %s not found at %s.", device_identifier, device_node)
        return None

    volume_name = (target.name if target else "RAMDisk") or "RAMDisk"
    try:
        subprocess.run(
            ["diskutil", "eraseVolume", "HFS+", volume_name, device_identifier],
            check=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.warning("Failed to format RAM disk %s: %s", device_identifier, exc)
        return None

    mount_path = _ensure_macos_mount(device_identifier, target)
    if mount_path is not None:
        logger.info(
            "Mounted macOS RAM disk at %s (%s).",
            mount_path,
            _format_size(size_bytes),
        )
        return mount_path

    fallback_mount = target or _MACOS_DEFAULT_MOUNT_POINT
    logger.warning("macOS RAM disk at %s not detected after mount attempts.", fallback_mount)
    return None


def _ensure_macos_mount(device_identifier: str, target: Optional[Path]) -> Optional[Path]:
    mount_candidate = _find_mountable_identifier(device_identifier)
    if not mount_candidate:
        return None

    attempted_mount_path: Optional[Path] = None
    if target is not None and _prepare_macos_mount_point(target):
        if _attempt_diskutil_mount(mount_candidate, target):
            attempted_mount_path = target
            if _is_ramdisk(target):
                return target

    mount_point = _get_diskutil_mount_point(mount_candidate)
    if mount_point:
        mount_path = Path(mount_point)
        if target is not None and target != mount_path:
            if _replace_with_symlink(target, mount_path):
                logger.info("Linked %s to existing RAM disk mount %s.", target, mount_path)
                if _is_ramdisk(target):
                    return target
        return mount_path

    if attempted_mount_path is not None:
        return attempted_mount_path if _is_ramdisk(attempted_mount_path) else None

    return None


def _attempt_diskutil_mount(device_identifier: str, target: Path) -> bool:
    try:
        subprocess.run(
            ["diskutil", "mount", "-mountPoint", str(target), device_identifier],
            check=True,
            text=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _find_mountable_identifier(device_identifier: str) -> Optional[str]:
    info = _get_diskutil_info(device_identifier)
    if _info_represents_mountable(info):
        return info.get("DeviceIdentifier", device_identifier)

    listing = _get_diskutil_listing(device_identifier)
    if not listing:
        return None if not info else device_identifier

    for partition in listing.get("Partitions", []):
        part_identifier = partition.get("DeviceIdentifier")
        if not part_identifier:
            continue
        part_info = _get_diskutil_info(part_identifier)
        if _info_represents_mountable(part_info):
            return part_identifier

    return device_identifier if info else None


def _info_represents_mountable(info: Optional[dict]) -> bool:
    if not info:
        return False

    if info.get("MountPoint") or info.get("FilesystemName"):
        return True

    content = info.get("Content")
    if content in {"Apple_HFS", "APFS", "Case-sensitive APFS", "ExFAT", "MS-DOS FAT32"}:
        return True

    return False


def _get_diskutil_info(identifier: str) -> Optional[dict]:
    try:
        output = subprocess.check_output(["diskutil", "info", "-plist", identifier], text=False)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None

    try:
        return plistlib.loads(output)
    except Exception:
        return None


def _get_diskutil_listing(identifier: str) -> Optional[dict]:
    try:
        output = subprocess.check_output(["diskutil", "list", "-plist", identifier], text=False)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None

    try:
        return plistlib.loads(output)
    except Exception:
        return None


def _get_diskutil_mount_point(identifier: str) -> Optional[str]:
    info = _get_diskutil_info(identifier)
    if not info:
        return None
    mount_point = info.get("MountPoint")
    return mount_point if mount_point else None


def _replace_with_symlink(target: Path, source: Path) -> bool:
    try:
        if target == source:
            return True
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source)
        return target.is_symlink()
    except OSError as exc:
        logger.warning("Failed to link %s to %s: %s", target, source, exc)
        return False


def _prepare_macos_mount_point(path: Path) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.debug("Insufficient permissions to create mount point %s; using default diskutil mount location.", path)
        return False
    except OSError as exc:
        logger.debug("Failed to prepare mount point %s: %s", path, exc)
        return False
    return True


def _teardown_ramdisk_mount(mount_path: Path) -> None:
    if not mount_path.exists():
        return

    if platform.system() == "Darwin":  # pragma: no cover - macOS specific cleanup
        info = _get_diskutil_info(str(mount_path))
        if not info:
            return
        device_identifier = info.get("DeviceIdentifier")
        if not device_identifier:
            return
        _diskutil_unmount(str(mount_path))
        _diskutil_eject(device_identifier)
        return

    if platform.system() == "Linux" and _is_ramdisk(mount_path):
        _umount_path(mount_path)


def _diskutil_unmount(mount_point: str) -> None:
    try:
        subprocess.run(["diskutil", "unmount", mount_point], check=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:  # pragma: no cover - best effort cleanup
        logger.debug("Failed to unmount %s: %s", mount_point, exc)


def _diskutil_eject(device_identifier: str) -> None:
    try:
        subprocess.run(["diskutil", "eject", device_identifier], check=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:  # pragma: no cover - best effort cleanup
        logger.debug("Failed to eject %s: %s", device_identifier, exc)


def _umount_path(path: Path) -> None:
    try:
        subprocess.run(["umount", str(path)], check=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:  # pragma: no cover - best effort cleanup
        logger.debug("Failed to unmount %s: %s", path, exc)


def _find_existing_macos_ramdisk_identifier(size_bytes: int) -> Optional[str]:
    try:
        output = subprocess.check_output(["diskutil", "list", "-plist"], text=False)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None

    try:
        listing = plistlib.loads(output)
    except Exception:
        return None

    tolerance = max(4096, size_bytes // 50)
    for entry in listing.get("AllDisksAndPartitions", []):
        for identifier, size in _iter_disk_entries(entry):
            if not identifier or size is None:
                continue
            if abs(int(size) - size_bytes) > tolerance:
                continue
            info = _get_diskutil_info(identifier)
            if _info_indicates_ramdisk(info):
                return identifier
    return None


def _iter_disk_entries(entry: dict) -> Iterable[Tuple[Optional[str], Optional[int]]]:
    yield entry.get("DeviceIdentifier"), entry.get("Size")
    for partition in entry.get("Partitions", []) or []:
        yield partition.get("DeviceIdentifier"), partition.get("Size")


def _info_indicates_ramdisk(info: Optional[dict]) -> bool:
    if not info:
        return False

    if info.get("VirtualOrPhysical") == "Virtual":
        return True

    media_name = (info.get("MediaName") or "").lower()
    if "ram" in media_name:
        return True

    device_location = (info.get("DeviceLocation") or "").lower()
    if "virtual" in device_location:
        return True

    return False


def _format_size(size_bytes: int) -> str:
    for unit in ("bytes", "KiB", "MiB", "GiB", "TiB"):
        if size_bytes < 1024 or unit == "TiB":
            return f"{size_bytes:.0f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.0f} TiB"


def _wait_for_ramdisk(path: Path, attempts: int = 5, delay: float = 0.2) -> bool:
    for _ in range(max(1, attempts)):
        if _is_ramdisk(path):
            return True
        time.sleep(max(0.0, delay))
    return False


def is_ramdisk(path: os.PathLike[str] | str) -> bool:
    """Return ``True`` when ``path`` resides on a RAM-backed filesystem."""

    target = Path(path).expanduser()
    try:
        resolved = target.resolve(strict=True)
    except FileNotFoundError:
        if target.is_symlink():
            try:
                resolved = target.resolve(strict=False)
            except (RuntimeError, OSError):
                resolved = None
        else:
            resolved = None

    candidate = resolved if resolved is not None else target
    return _is_ramdisk(candidate)


def teardown_ramdisk(path: os.PathLike[str] | str) -> None:
    """Unmount the RAM disk backing ``path`` and restore a regular directory."""

    target = Path(path).expanduser()
    candidates = []

    try:
        resolved = target.resolve(strict=True)
    except FileNotFoundError:
        try:
            resolved = target.resolve(strict=False)
        except (RuntimeError, OSError):
            resolved = None

    if resolved is not None:
        candidates.append(resolved)
    candidates.append(target)

    seen: set[str] = set()
    for candidate in candidates:
        candidate_path = Path(candidate)
        try:
            key = str(candidate_path.resolve())
        except FileNotFoundError:
            key = str(candidate_path)
        if key in seen:
            continue
        seen.add(key)
        if _is_ramdisk(candidate_path):
            _teardown_ramdisk_mount(candidate_path)

    if target.is_symlink():
        try:
            target.unlink()
        except OSError as exc:  # pragma: no cover - best effort cleanup
            logger.debug("Failed to remove tmp symlink %s: %s", target, exc)

    if not target.exists():
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as exc:  # pragma: no cover - best effort cleanup
            logger.debug("Failed to recreate tmp directory %s: %s", target, exc)


__all__ = [
    "ensure_ramdisk",
    "ensure_standard_directory",
    "is_ramdisk",
    "teardown_ramdisk",
]
