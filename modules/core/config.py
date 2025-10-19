from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PipelineConfig:
    """Configuration values required by the core processing helpers."""

    working_dir: Optional[str]
    books_dir: Optional[str]
    default_working_relative: Path
    derived_runtime_dirname: str
    derived_refined_filename_template: str
    max_words: int
    extend_split_with_comma_semicolon: bool
    selected_voice: str
    tempo: float
    macos_reading_speed: int
    sync_ratio: float
    word_highlighting: bool
    pipeline_enabled: bool
    queue_size: int
    thread_count: int
