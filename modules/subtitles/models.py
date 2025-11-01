"""Typed containers for subtitle processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(slots=True)
class SubtitleCue:
    """Normalized representation of a subtitle cue."""

    index: int
    start: float
    end: float
    lines: List[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def as_text(self) -> str:
        return "\n".join(self.lines).strip()


@dataclass(slots=True)
class SubtitleJobOptions:
    """Runtime configuration for a subtitle processing task."""

    input_language: str
    target_language: str
    enable_transliteration: bool = False
    highlight: bool = True
    batch_size: Optional[int] = None
    worker_count: Optional[int] = None

    @classmethod
    def from_mapping(cls, data: Dict[str, object]) -> "SubtitleJobOptions":
        worker_value = data.get("worker_count")
        worker_count = None
        if isinstance(worker_value, int):
            worker_count = worker_value
        elif isinstance(worker_value, str) and worker_value.strip().isdigit():
            worker_count = int(worker_value.strip())
        return cls(
            input_language=str(data.get("input_language") or "English"),
            target_language=str(data.get("target_language") or "English"),
            enable_transliteration=bool(data.get("enable_transliteration")),
            highlight=bool(data.get("highlight", True)),
            batch_size=int(data["batch_size"]) if data.get("batch_size") else None,
            worker_count=worker_count,
        )

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "input_language": self.input_language,
            "target_language": self.target_language,
            "enable_transliteration": self.enable_transliteration,
            "highlight": self.highlight,
        }
        if self.batch_size is not None:
            payload["batch_size"] = self.batch_size
        if self.worker_count is not None:
            payload["worker_count"] = self.worker_count
        return payload


@dataclass(slots=True)
class SubtitleProcessingResult:
    """Summary artefacts produced after processing subtitles."""

    output_path: Path
    cue_count: int
    translated_count: int
    metadata: Dict[str, object] = field(default_factory=dict)
