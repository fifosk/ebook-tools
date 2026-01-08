"""Shared helpers for image generation in the rendering pipeline."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional


def _job_relative_path(candidate: Path, *, base_dir: Path) -> str:
    """Best-effort conversion of an absolute path to a job-relative storage path."""

    base_dir_path = Path(base_dir)
    path_obj = Path(candidate)
    for parent in base_dir_path.parents:
        if parent.name.lower() == "media" and parent.parent != parent:
            try:
                relative = path_obj.relative_to(parent.parent)
            except ValueError:
                continue
            if relative.as_posix():
                return relative.as_posix()
    job_root_candidates = list(base_dir_path.parents[:4])
    job_root_candidates.append(base_dir_path)
    for root_candidate in job_root_candidates:
        try:
            relative = path_obj.relative_to(root_candidate)
        except ValueError:
            continue
        if relative.as_posix():
            return relative.as_posix()
    return path_obj.name


def _resolve_media_root(base_dir: Path) -> Path:
    """Return the job's media root directory based on ``base_dir``."""

    candidate = Path(base_dir)
    if candidate.name.lower() == "media":
        return candidate
    for parent in candidate.parents:
        if parent.name.lower() == "media":
            return parent
    return candidate


def _resolve_job_root(media_root: Path) -> Optional[Path]:
    candidate = Path(media_root)
    if candidate.name.lower() != "media":
        return None
    if candidate.parent == candidate:
        return None
    return candidate.parent


def _atomic_write_json(path: Path, payload: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


@dataclass(frozen=True, slots=True)
class _SentenceImageResult:
    chunk_id: str
    range_fragment: str
    start_sentence: int
    end_sentence: int
    sentence_number: int
    relative_path: str
    prompt: str
    negative_prompt: str
    extra: dict[str, Any] = field(default_factory=dict)


class _ImageGenerationState:
    """Shared state used to merge async image results into chunk metadata."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._chunks: dict[str, dict[str, Any]] = {}
        self._pending: dict[str, list[_SentenceImageResult]] = {}

    def register_chunk(self, result) -> bool:
        """Store ``result`` and apply any pending image updates. Returns True if updated."""

        if result is None:
            return False

        sentence_map: dict[int, dict[str, Any]] = {}
        for entry in result.sentences or []:
            if not isinstance(entry, Mapping):
                continue
            raw_number = entry.get("sentence_number") or entry.get("sentenceNumber")
            try:
                number = int(raw_number)
            except (TypeError, ValueError):
                continue
            sentence_map[number] = entry  # type: ignore[assignment]

        with self._lock:
            chunk_payload = {
                "chunk_id": result.chunk_id,
                "range_fragment": result.range_fragment,
                "start_sentence": result.start_sentence,
                "end_sentence": result.end_sentence,
                "files": dict(result.artifacts),
                "sentences": list(result.sentences or []),
                "audio_tracks": dict(result.audio_tracks or {}),
                "timing_tracks": dict(result.timing_tracks or {}),
                "extra_files": [],
                "sentence_map": sentence_map,
            }
            policy = getattr(result, "highlighting_policy", None)
            if isinstance(policy, str) and policy.strip():
                chunk_payload["highlighting_policy"] = policy.strip()
            self._chunks[result.chunk_id] = chunk_payload
            pending = self._pending.pop(result.chunk_id, [])

        updated = False
        for item in pending:
            if self.apply(item):
                updated = True
        return updated

    def apply(self, image: _SentenceImageResult) -> bool:
        """Apply ``image`` into the cached chunk state. Returns True if changed."""

        if image is None:
            return False

        with self._lock:
            chunk = self._chunks.get(image.chunk_id)
            if chunk is None:
                self._pending.setdefault(image.chunk_id, []).append(image)
                return False

            sentence_entry = chunk.get("sentence_map", {}).get(image.sentence_number)
            if isinstance(sentence_entry, dict):
                preserved: dict[str, Any] = {}
                previous = sentence_entry.get("image")
                if isinstance(previous, Mapping):
                    for key, value in previous.items():
                        if key in {"path", "prompt", "negative_prompt", "negativePrompt"}:
                            continue
                        preserved[key] = value

                extra_payload = image.extra if isinstance(image.extra, dict) else {}
                image_payload: dict[str, Any] = {
                    **preserved,
                    **extra_payload,
                    "path": image.relative_path,
                    "prompt": image.prompt,
                }
                if image.negative_prompt:
                    image_payload["negative_prompt"] = image.negative_prompt
                if previous != image_payload:
                    sentence_entry["image"] = image_payload
                    sentence_entry["image_path"] = image.relative_path
                    sentence_entry["imagePath"] = image.relative_path
                    updated = True
                else:
                    updated = False
            else:
                updated = False

            extra_files: list[dict[str, Any]] = chunk.get("extra_files") or []
            signature = ("image", image.relative_path)
            seen = chunk.setdefault("_image_seen", set())
            if signature not in seen:
                seen.add(signature)
                extra_files.append(
                    {
                        "type": "image",
                        "path": image.relative_path,
                        "sentence_number": image.sentence_number,
                        "start_sentence": image.start_sentence,
                        "end_sentence": image.end_sentence,
                        "range_fragment": image.range_fragment,
                        "chunk_id": image.chunk_id,
                    }
                )
                chunk["extra_files"] = extra_files
                updated = True or updated

        return updated

    def snapshot_chunk(self, chunk_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            chunk = self._chunks.get(chunk_id)
            return dict(chunk) if isinstance(chunk, dict) else None


__all__ = [
    "_SentenceImageResult",
    "_ImageGenerationState",
    "_atomic_write_json",
    "_job_relative_path",
    "_resolve_job_root",
    "_resolve_media_root",
]
