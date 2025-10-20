"""Core slide model abstractions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


class SlideType(str, Enum):
    TITLE = "title"
    TEXT = "text"
    IMAGE = "image"
    QUOTE = "quote"
    CODE = "code"
    SENTENCE = "sentence"


@dataclass(slots=True)
class HighlightSpec:
    word_index: Optional[int] = None
    char_range: Optional[Tuple[int, int]] = None


@dataclass(slots=True)
class Slide:
    """Representation of a logical slide to be rendered."""

    slide_type: SlideType
    title: str
    content: Sequence[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    template_name: Optional[str] = None
    highlight_original: HighlightSpec = field(default_factory=HighlightSpec)
    highlight_translation: HighlightSpec = field(default_factory=HighlightSpec)
    highlight_transliteration: HighlightSpec = field(default_factory=HighlightSpec)

    @classmethod
    def from_sentence_block(
        cls,
        block: str,
        *,
        template_name: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> "Slide":
        lines = block.split("\n")
        title = lines[0] if lines else ""
        sections = [line.strip() for line in lines[1:] if line.strip()]
        combined_metadata: Dict[str, Any] = {"raw_block": block}
        if metadata:
            combined_metadata.update(metadata)
        return cls(
            slide_type=SlideType.SENTENCE,
            title=title,
            content=sections,
            metadata=combined_metadata,
            template_name=template_name,
        )

    def with_highlights(
        self,
        *,
        original: Optional[HighlightSpec] = None,
        translation: Optional[HighlightSpec] = None,
        transliteration: Optional[HighlightSpec] = None,
    ) -> "Slide":
        clone = Slide(
            slide_type=self.slide_type,
            title=self.title,
            content=tuple(self.content),
            metadata=dict(self.metadata),
            template_name=self.template_name,
            highlight_original=original or self.highlight_original,
            highlight_translation=translation or self.highlight_translation,
            highlight_transliteration=transliteration or self.highlight_transliteration,
        )
        return clone


__all__ = ["Slide", "SlideType", "HighlightSpec"]
