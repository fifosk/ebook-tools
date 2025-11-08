"""Helpers for assembling media job manifests."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping


def finalize_job_manifest(
    manifest: MutableMapping[str, Any],
    *,
    tempo_factor: float,
    generation_mode: str | None = None,
    aligner: str | None = None,
) -> MutableMapping[str, Any]:
    """Record timing metadata on the job manifest."""

    meta_rate = round(float(tempo_factor), 3)
    timing_meta = dict(
        playbackRate=meta_rate,
        generation_mode=generation_mode,
        aligner=aligner,
    )
    cleaned_meta = {
        key: value
        for key, value in timing_meta.items()
        if value is not None and value != ""
    }
    manifest["timing_meta"] = cleaned_meta
    return manifest


def extract_timing_meta(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return timing metadata if present."""

    meta = manifest.get("timing_meta")
    if isinstance(meta, Mapping):
        return dict(meta)
    return {}


__all__ = ["finalize_job_manifest", "extract_timing_meta"]
