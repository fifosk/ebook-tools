#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from modules.library.sync import file_ops


@dataclass
class RehydrateStats:
    chunks_seen: int = 0
    chunks_changed: int = 0
    sentences_added: int = 0
    audio_tracks_added: int = 0
    timing_tracks_added: int = 0

    def merge(self, other: "RehydrateStats") -> None:
        self.chunks_seen += other.chunks_seen
        self.chunks_changed += other.chunks_changed
        self.sentences_added += other.sentences_added
        self.audio_tracks_added += other.audio_tracks_added
        self.timing_tracks_added += other.timing_tracks_added


FIELD_GROUPS: Tuple[
    Tuple[str, Tuple[str, ...], Callable[[Any], bool]],
    ...,
] = (
    ("sentences", ("sentences",), lambda value: isinstance(value, list) and len(value) > 0),
    (
        "audio_tracks",
        ("audio_tracks", "audioTracks"),
        lambda value: isinstance(value, Mapping) and len(value) > 0,
    ),
    (
        "timing_tracks",
        ("timing_tracks", "timingTracks"),
        lambda value: isinstance(value, Mapping) and len(value) > 0,
    ),
)


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False


def _load_chunk_payload(job_root: Path, metadata_path: str) -> Optional[Mapping[str, Any]]:
    raw_path = metadata_path.replace("\\", "/")
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        normalized = raw_path.lstrip("/")
        if not normalized:
            return None
        candidate = job_root / normalized
    if not candidate.exists():
        return None
    try:
        with candidate.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, Mapping) else None


def _pick_first(value: Mapping[str, Any], keys: Tuple[str, ...]) -> Tuple[Optional[str], Any]:
    for key in keys:
        if key in value:
            return key, value.get(key)
    return None, None


def _rehydrate_chunk_entry(
    chunk_entry: Dict[str, Any],
    payload: Mapping[str, Any],
    *,
    force: bool,
) -> Tuple[Dict[str, Any], bool, RehydrateStats]:
    updated = dict(chunk_entry)
    changed = False
    stats = RehydrateStats(chunks_seen=1)

    for label, keys, has_payload in FIELD_GROUPS:
        dest_key, dest_value = _pick_first(updated, keys)
        source_key, source_value = _pick_first(payload, keys)
        if not has_payload(source_value):
            continue
        if not force and has_payload(dest_value):
            continue
        if dest_key is None:
            dest_key = source_key or keys[0]
        updated[dest_key] = copy.deepcopy(source_value)
        changed = True
        if label == "sentences":
            stats.sentences_added += 1
        elif label == "audio_tracks":
            stats.audio_tracks_added += 1
        elif label == "timing_tracks":
            stats.timing_tracks_added += 1

    if changed:
        stats.chunks_changed = 1
    return updated, changed, stats


def _rehydrate_chunks(
    chunks_value: Any,
    job_root: Path,
    *,
    force: bool,
) -> Tuple[Any, bool, RehydrateStats]:
    stats = RehydrateStats()
    if isinstance(chunks_value, list):
        updated_chunks = []
        changed_any = False
        for entry in chunks_value:
            if not isinstance(entry, Mapping):
                updated_chunks.append(entry)
                continue
            chunk_entry = dict(entry)
            metadata_path = chunk_entry.get("metadata_path") or chunk_entry.get("metadataPath")
            if isinstance(metadata_path, str) and metadata_path.strip():
                payload = _load_chunk_payload(job_root, metadata_path.strip())
            else:
                payload = None
            if payload:
                updated_entry, changed, chunk_stats = _rehydrate_chunk_entry(
                    chunk_entry, payload, force=force
                )
                stats.merge(chunk_stats)
                if changed:
                    changed_any = True
                updated_chunks.append(updated_entry)
            else:
                updated_chunks.append(chunk_entry)
        return (updated_chunks if changed_any else chunks_value), changed_any, stats
    if isinstance(chunks_value, Mapping):
        updated_map: Dict[str, Any] = {}
        changed_any = False
        for key, entry in chunks_value.items():
            if not isinstance(entry, Mapping):
                updated_map[key] = entry
                continue
            chunk_entry = dict(entry)
            metadata_path = chunk_entry.get("metadata_path") or chunk_entry.get("metadataPath")
            if isinstance(metadata_path, str) and metadata_path.strip():
                payload = _load_chunk_payload(job_root, metadata_path.strip())
            else:
                payload = None
            if payload:
                updated_entry, changed, chunk_stats = _rehydrate_chunk_entry(
                    chunk_entry, payload, force=force
                )
                stats.merge(chunk_stats)
                if changed:
                    changed_any = True
                updated_map[key] = updated_entry
            else:
                updated_map[key] = chunk_entry
        return (updated_map if changed_any else chunks_value), changed_any, stats
    return chunks_value, False, stats


def _rehydrate_generated(
    generated: Any,
    job_root: Path,
    *,
    force: bool,
) -> Tuple[Any, bool, RehydrateStats]:
    if not isinstance(generated, Mapping):
        return generated, False, RehydrateStats()
    updated = dict(generated)
    chunks_value = generated.get("chunks")
    updated_chunks, changed, stats = _rehydrate_chunks(chunks_value, job_root, force=force)
    if changed:
        updated["chunks"] = updated_chunks
    return (updated if changed else generated), changed, stats


def _rehydrate_metadata(
    metadata: Mapping[str, Any],
    job_root: Path,
    *,
    force: bool,
) -> Tuple[Dict[str, Any], bool, RehydrateStats]:
    updated = dict(metadata)
    changed = False
    stats = RehydrateStats()

    generated = metadata.get("generated_files")
    updated_generated, generated_changed, generated_stats = _rehydrate_generated(
        generated, job_root, force=force
    )
    stats.merge(generated_stats)
    if generated_changed:
        updated["generated_files"] = updated_generated
        changed = True

    for nested_key in ("result", "result_payload"):
        section = metadata.get(nested_key)
        if not isinstance(section, Mapping):
            continue
        section_payload = dict(section)
        nested_generated = section_payload.get("generated_files")
        updated_nested, nested_changed, nested_stats = _rehydrate_generated(
            nested_generated, job_root, force=force
        )
        stats.merge(nested_stats)
        if nested_changed:
            section_payload["generated_files"] = updated_nested
            updated[nested_key] = section_payload
            changed = True

    return updated, changed, stats


def _backup_metadata(metadata_path: Path) -> Path:
    backup_path = metadata_path.with_suffix(metadata_path.suffix + ".bak")
    if not backup_path.exists():
        shutil.copy2(metadata_path, backup_path)
        return backup_path
    for index in range(1, 1000):
        candidate = metadata_path.with_suffix(metadata_path.suffix + f".bak{index}")
        if not candidate.exists():
            shutil.copy2(metadata_path, candidate)
            return candidate
    raise RuntimeError("Unable to allocate backup name for metadata")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rehydrate inline chunk payloads in library job metadata."
    )
    parser.add_argument(
        "job_root",
        type=Path,
        help="Path to the library job directory (contains metadata/job.json).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite inline payloads even if they already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing job.json.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip writing a backup job.json.bak file.",
    )
    args = parser.parse_args()

    job_root = args.job_root.expanduser().resolve()
    metadata_path = job_root / "metadata" / "job.json"
    if not metadata_path.exists():
        print(f"Missing metadata file at {metadata_path}")
        return 1

    metadata = file_ops.load_metadata(job_root)
    updated, changed, stats = _rehydrate_metadata(metadata, job_root, force=args.force)

    print(
        "Chunks:",
        stats.chunks_seen,
        "changed:",
        stats.chunks_changed,
        "sentences:",
        stats.sentences_added,
        "audio_tracks:",
        stats.audio_tracks_added,
        "timing_tracks:",
        stats.timing_tracks_added,
    )

    if not changed:
        print("No metadata updates needed.")
        return 0

    if args.dry_run:
        print("Dry run: no changes written.")
        return 0

    if not args.no_backup:
        backup_path = _backup_metadata(metadata_path)
        print(f"Backup written to {backup_path}")

    file_ops.write_metadata(job_root, updated)
    print("job.json updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
