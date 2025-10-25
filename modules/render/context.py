"""Context containers shared across rendering pipelines."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional
from typing import Literal

MediaType = Literal["video", "audio", "text"]


@dataclass(frozen=True, slots=True)
class RenderBatchContext:
    """Combine manifest and per-media context information for a render batch."""

    manifest: Mapping[str, Any] = field(default_factory=dict)
    media: Mapping[MediaType, Mapping[str, Any]] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Return a value from the manifest-level context."""

        return self.manifest.get(key, default)

    def media_context(self, media_type: MediaType) -> Mapping[str, Any]:
        """Return the context mapping for ``media_type`` or an empty mapping."""

        return self.media.get(media_type, {})

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the batch context into plain dictionaries."""

        manifest_payload = dict(self.manifest)
        media_payload: Dict[str, Dict[str, Any]] = {}
        for media_type, context in self.media.items():
            media_payload[media_type] = dict(context)
        return {"manifest": manifest_payload, "media": media_payload}

    @classmethod
    def from_mapping(cls, payload: Optional[Mapping[str, Any]]) -> "RenderBatchContext":
        """Instantiate a context from a serialized representation."""

        if not payload:
            return cls()
        manifest_payload: Mapping[str, Any]
        raw_manifest = payload.get("manifest") if isinstance(payload, Mapping) else None
        if isinstance(raw_manifest, Mapping):
            manifest_payload = dict(raw_manifest)
        else:
            manifest_payload = {}

        media_payload: Dict[MediaType, Mapping[str, Any]] = {}
        raw_media = payload.get("media") if isinstance(payload, Mapping) else None
        if isinstance(raw_media, Mapping):
            for key, value in raw_media.items():
                if key in ("video", "audio", "text") and isinstance(value, Mapping):
                    media_payload[key] = dict(value)  # type: ignore[assignment]
        return cls(manifest=manifest_payload, media=media_payload)

    def merge_manifest(self, payload: Mapping[str, Any]) -> "RenderBatchContext":
        """Return a new context with manifest keys updated from ``payload``."""

        merged = dict(self.manifest)
        merged.update(payload)
        return RenderBatchContext(manifest=merged, media=self.media)

    def merge_media(self, media_type: MediaType, payload: Mapping[str, Any]) -> "RenderBatchContext":
        """Return a context with the ``media_type`` context updated."""

        media_payload: Dict[MediaType, Mapping[str, Any]] = {
            key: dict(value) for key, value in self.media.items()
        }
        existing = dict(media_payload.get(media_type, {}))
        existing.update(payload)
        media_payload[media_type] = existing
        return RenderBatchContext(manifest=self.manifest, media=media_payload)


__all__ = ["MediaType", "RenderBatchContext"]
