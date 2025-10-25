"""Typed models shared across pipeline phases."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from pydub import AudioSegment

from ..core.config import PipelineConfig


@dataclass(slots=True)
class PipelineMetadata:
    """Container for metadata derived from pipeline inputs and inference."""

    values: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Optional[Mapping[str, Any]]) -> "PipelineMetadata":
        if isinstance(payload, PipelineMetadata):
            return payload.clone()
        return cls(values=dict(payload or {}))

    def update(self, payload: Mapping[str, Any]) -> None:
        self.values.update(payload)

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def clone(self) -> "PipelineMetadata":
        return PipelineMetadata(values=dict(self.values))

    def as_dict(self) -> Dict[str, Any]:
        return dict(self.values)


@dataclass(slots=True)
class PipelineAttributes:
    """Identifiers shared with observability hooks."""

    correlation_id: str
    job_id: Optional[str]
    input_file: str

    def as_dict(self) -> Dict[str, Any]:
        payload = {
            "correlation_id": self.correlation_id,
            "job_id": self.job_id,
            "input_file": self.input_file,
        }
        return payload


@dataclass(slots=True)
class ConfigPhaseResult:
    """Result of preparing runtime configuration for the pipeline."""

    pipeline_config: PipelineConfig
    generate_audio: bool
    audio_mode: str


@dataclass(slots=True)
class IngestionResult:
    """Sentences refined during ingestion."""

    refined_sentences: List[str]
    refined_updated: bool
    total_sentences: int


@dataclass(slots=True)
class RenderResult:
    """Artifacts emitted by the rendering phase."""

    written_blocks: List[str]
    audio_segments: Optional[List[AudioSegment]]
    batch_video_files: List[str]
    base_dir: Optional[str]
    base_output_stem: Optional[str]


@dataclass(slots=True)
class StitchingArtifacts:
    """Outputs generated while stitching full translations."""

    documents: Dict[str, str] = field(default_factory=dict)
    audio_path: Optional[str] = None
    video_path: Optional[str] = None


@dataclass(slots=True)
class MetadataPhaseResult:
    """Combined metadata and ingestion outputs."""

    metadata: PipelineMetadata
    ingestion: IngestionResult


