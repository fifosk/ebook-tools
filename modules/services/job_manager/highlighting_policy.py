"""Utilities for extracting and resolving highlighting policy from chunk metadata."""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from ... import logging_manager

_LOGGER = logging_manager.get_logger().getChild("job_manager.highlighting_policy")


def _iterate_sentence_entries(payload: Any) -> list[Mapping[str, Any]]:
    """Return flattened sentence entries from a chunk payload."""

    entries: list[Mapping[str, Any]] = []
    if isinstance(payload, list):
        for item in payload:
            entries.extend(_iterate_sentence_entries(item))
    elif isinstance(payload, Mapping):
        sentences = payload.get("sentences")
        if isinstance(sentences, list):
            for sentence in sentences:
                entries.extend(_iterate_sentence_entries(sentence))
        else:
            entries.append(payload)  # Treat mapping as a sentence-level entry
        chunks = payload.get("chunks")
        if isinstance(chunks, list):
            for chunk in chunks:
                entries.extend(_iterate_sentence_entries(chunk))
    return entries


def _extract_highlighting_policy(entry: Mapping[str, Any]) -> Optional[str]:
    """Return the highlighting policy encoded on a sentence entry."""

    summary = entry.get("highlighting_summary")
    if isinstance(summary, Mapping):
        policy = summary.get("policy")
        if isinstance(policy, str) and policy.strip():
            return policy.strip()
    policy = entry.get("highlighting_policy") or entry.get("alignment_policy")
    if isinstance(policy, str) and policy.strip():
        return policy.strip()
    return None


def _is_estimated_policy(policy: Optional[str]) -> bool:
    if not isinstance(policy, str):
        return False
    normalized = policy.strip().lower()
    return normalized.startswith("estimated")


def _extract_policy_from_timing_tracks(payload: Mapping[str, Any]) -> Optional[str]:
    tracks = payload.get("timingTracks") or payload.get("timing_tracks")
    if not isinstance(tracks, Mapping):
        return None
    fallback: Optional[str] = None
    for entries in tracks.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            policy = entry.get("policy")
            if not isinstance(policy, str):
                continue
            normalized = policy.strip()
            if not normalized:
                continue
            if _is_estimated_policy(normalized):
                return normalized
            if fallback is None:
                fallback = normalized
    return fallback


def resolve_highlighting_policy(job_dir: str | os.PathLike[str]) -> Optional[str]:
    """Inspect chunk metadata files to determine the active highlighting policy."""

    job_path = Path(job_dir)
    metadata_dir = job_path / "metadata"
    if not metadata_dir.exists():
        return None

    fallback_policy: Optional[str] = None
    pattern = metadata_dir / "chunk_*.json"
    for chunk_path in sorted(glob.glob(os.fspath(pattern))):
        try:
            with open(chunk_path, "r", encoding="utf-8") as handle:
                chunk_payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue

        if isinstance(chunk_payload, Mapping):
            top_level_policy = chunk_payload.get("highlighting_policy")
            if isinstance(top_level_policy, str) and top_level_policy.strip():
                normalized = top_level_policy.strip()
                if _is_estimated_policy(normalized):
                    return normalized
                if fallback_policy is None:
                    fallback_policy = normalized
            policy = _extract_policy_from_timing_tracks(chunk_payload)
            if policy:
                if _is_estimated_policy(policy):
                    return policy
                if fallback_policy is None:
                    fallback_policy = policy

        for entry in _iterate_sentence_entries(chunk_payload):
            if isinstance(entry, Mapping):
                policy = _extract_highlighting_policy(entry)
                if policy:
                    if _is_estimated_policy(policy):
                        return policy
                    if fallback_policy is None:
                        fallback_policy = policy

    return fallback_policy


def ensure_timing_manifest(
    manifest: Mapping[str, Any] | None,
    job_dir: str | os.PathLike[str],
) -> Dict[str, Any]:
    """
    Attach highlighting metadata to ``manifest`` without persisting timing indexes.
    """

    manifest_payload = dict(manifest or {})
    manifest_payload.pop("timing_tracks", None)

    job_path = Path(job_dir)
    policy = resolve_highlighting_policy(job_path)
    if policy:
        manifest_payload["highlighting_policy"] = policy
    return manifest_payload


__all__ = [
    "resolve_highlighting_policy",
    "ensure_timing_manifest",
    "_iterate_sentence_entries",
    "_extract_highlighting_policy",
    "_is_estimated_policy",
    "_extract_policy_from_timing_tracks",
]
