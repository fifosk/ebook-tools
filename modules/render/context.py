"""Context containers shared across rendering pipelines."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
from typing import Literal
from uuid import uuid4

from modules import config_manager as cfg

MediaType = Literal["video", "audio", "text"]


@dataclass(frozen=True, slots=True)
class RenderBatchContext:
    """Combine manifest and per-media context information for a render batch."""

    manifest: Mapping[str, Any] = field(default_factory=dict)
    media: Mapping[MediaType, Mapping[str, Any]] = field(default_factory=dict)
    _batch_id: str = field(init=False, repr=False)
    _ramdisk_root: Optional[Path] = field(init=False, repr=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Return a value from the manifest-level context."""

        return self.manifest.get(key, default)

    def __post_init__(self) -> None:
        batch_id = self._derive_batch_id(self.manifest)
        object.__setattr__(self, "_batch_id", batch_id)
        object.__setattr__(self, "_ramdisk_root", self._derive_ramdisk_root(self.manifest, batch_id))

    @staticmethod
    def _derive_batch_id(manifest: Mapping[str, Any]) -> str:
        candidate = manifest.get("batch_id")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        return uuid4().hex

    @staticmethod
    def _derive_ramdisk_root(manifest: Mapping[str, Any], batch_id: str) -> Optional[Path]:
        enabled = manifest.get("ramdisk_enabled", False)
        if isinstance(enabled, str):
            enabled = enabled.lower() in {"true", "1", "yes", "on"}
        if not enabled:
            return None
        base_path = manifest.get("ramdisk_path")
        if isinstance(base_path, str) and base_path.strip():
            candidate = Path(base_path.strip())
            if not candidate.is_absolute():
                runtime_context = cfg.get_runtime_context(None)
                if runtime_context is not None:
                    candidate = runtime_context.tmp_dir / candidate
                else:
                    candidate = (cfg.SCRIPT_DIR / candidate).resolve()
            return candidate / batch_id
        return None

    @property
    def batch_id(self) -> str:
        """Return the identifier associated with this batch."""

        return self._batch_id

    @property
    def temp_dir(self) -> Optional[Path]:
        """Return the temporary directory for this batch, if configured."""

        return self._ramdisk_root

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
