"""Cue merging and normalization helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Optional, Sequence, TYPE_CHECKING

from .models import SubtitleCue
from .text import _normalize_rendered_lines, _normalize_text

if TYPE_CHECKING:  # pragma: no cover
    from .models import SubtitleJobOptions


def _normalize_cue_timeline(
    cues: Sequence[SubtitleCue],
    *,
    min_gap_seconds: float,
    min_duration_seconds: float,
) -> List[SubtitleCue]:
    """Return cues ordered by start with enforced gaps/durations while preserving starts."""

    normalized: List[SubtitleCue] = []
    for cue in sorted(cues, key=lambda c: (c.start, c.end)):
        start = cue.start
        end = cue.end

        if normalized:
            prev = normalized[-1]
            allowed_start = prev.end + min_gap_seconds
            if start < allowed_start:
                # First, try shrinking the previous cue to make room.
                trimmed_prev_end = max(prev.start + min_duration_seconds, start - min_gap_seconds)
                if trimmed_prev_end < prev.end:
                    normalized[-1] = SubtitleCue(
                        index=prev.index,
                        start=prev.start,
                        end=trimmed_prev_end,
                        lines=list(prev.lines),
                    )
                    prev = normalized[-1]
                    allowed_start = prev.end + min_gap_seconds

                # If overlap persists, shift the current cue minimally forward.
                if start < allowed_start:
                    shift = allowed_start - start
                    start += shift
                    end += shift

        end = max(end, start + min_duration_seconds)
        normalized.append(
            SubtitleCue(
                index=cue.index,
                start=start,
                end=end,
                lines=list(cue.lines),
            )
        )

    return normalized


def _count_overlapping_cues(cues: Sequence[SubtitleCue]) -> int:
    """Return how many cues overlap with their immediate predecessor."""

    if not cues:
        return 0

    count = 0
    ordered = sorted(cues, key=lambda c: (c.start, c.end))
    previous_end: Optional[float] = None
    for cue in ordered:
        if previous_end is not None and cue.start < previous_end:
            count += 1
        previous_end = max(previous_end or cue.end, cue.end)
    return count


def _should_merge_youtube_cues(
    cues: Sequence[SubtitleCue],
    options: "SubtitleJobOptions",
    source_path,
) -> bool:
    """Heuristic to decide if YouTube-style merging should be applied."""

    if options.source_is_youtube:
        return True

    name = source_path.name.lower()
    filename_hint = "_yt" in name or ".yt" in name or "youtube" in name

    overlap_ratio = 0.0
    if len(cues) > 1:
        overlap_ratio = _count_overlapping_cues(cues) / max(len(cues) - 1, 1)
    dense_overlap = overlap_ratio >= 0.15

    short_cues = sum(1 for cue in cues if cue.duration <= 1.2)
    short_ratio = short_cues / max(len(cues), 1)

    return filename_hint or (dense_overlap and short_ratio >= 0.25)


def _split_long_cues(
    cues: Sequence[SubtitleCue],
    *,
    target_seconds: float,
    max_seconds: float,
) -> List[SubtitleCue]:
    """Split overly long cues into smaller windows by word count."""

    if not cues:
        return []

    split: List[SubtitleCue] = []
    for cue in cues:
        duration = max(0.0, cue.end - cue.start)
        if duration <= max_seconds:
            split.append(cue)
            continue

        words = cue.as_text().split()
        segments = max(1, int(math.ceil(duration / max(target_seconds, 0.1))))
        if segments <= 1:
            split.append(cue)
            continue

        segment_duration = duration / segments
        words_per_segment = max(1, int(math.ceil(len(words) / segments)))
        for idx in range(segments):
            start = cue.start + segment_duration * idx
            end = min(cue.end, start + segment_duration)
            word_slice = words[idx * words_per_segment : (idx + 1) * words_per_segment]
            text = " ".join(word_slice) if word_slice else cue.as_text()
            split.append(
                SubtitleCue(
                    index=cue.index,
                    start=start,
                    end=end,
                    lines=[text],
                )
            )
    return split


@dataclass(slots=True)
class _NormalizedCueWindow:
    cue: SubtitleCue
    normalized_text: str


def _collapse_redundant_windows(
    cues: Sequence[SubtitleCue],
    *,
    max_gap_seconds: float = 1.0,
    min_containment_ratio: float = 0.45,
    min_similarity: float = 0.82,
) -> List[SubtitleCue]:
    """Merge consecutive cues that repeat the same text to reduce flicker."""

    merged: List[SubtitleCue] = []
    active: Optional[_NormalizedCueWindow] = None

    for cue in cues:
        normalized = _normalize_text(cue.as_text())
        if not normalized:
            continue

        if active is None:
            active = _NormalizedCueWindow(cue=cue, normalized_text=normalized)
            continue

        gap = max(0.0, cue.start - active.cue.end)
        prefix_match = normalized.startswith(active.normalized_text) or active.normalized_text.startswith(
            normalized
        )
        if gap <= max_gap_seconds and (
            _texts_overlap(
                normalized,
                active.normalized_text,
                min_containment_ratio=min_containment_ratio,
                min_similarity=min_similarity,
            )
            or (prefix_match and gap <= 0.35 and min(len(normalized), len(active.normalized_text)) >= 8)
        ):
            keep_current = len(normalized) > len(active.normalized_text)
            base_cue = cue if keep_current else active.cue
            base_text = normalized if keep_current else active.normalized_text
            active = _NormalizedCueWindow(
                cue=SubtitleCue(
                    index=base_cue.index,
                    start=min(active.cue.start, cue.start),
                    end=max(active.cue.end, cue.end),
                    lines=list(base_cue.lines),
                ),
                normalized_text=base_text,
            )
            continue

        merged.append(active.cue)
        active = _NormalizedCueWindow(cue=cue, normalized_text=normalized)

    if active is not None:
        merged.append(active.cue)

    return merged


def _deduplicate_cues_by_text(
    cues: Sequence[SubtitleCue],
    *,
    max_gap_seconds: float = 2.0,
    min_containment_ratio: float = 0.4,
    min_similarity: float = 0.8,
) -> List[SubtitleCue]:
    """Collapse consecutive cues when their text substantially overlaps."""

    if not cues:
        return []

    result: List[SubtitleCue] = []
    previous: Optional[_NormalizedCueWindow] = None

    for cue in cues:
        normalized = _normalize_text(cue.as_text())
        if not normalized:
            continue

        if previous is not None:
            gap = max(0.0, cue.start - previous.cue.end)
            if gap <= max_gap_seconds and _texts_overlap(
                normalized,
                previous.normalized_text,
                min_containment_ratio=min_containment_ratio,
                min_similarity=min_similarity,
            ):
                keep_current = len(normalized) >= len(previous.normalized_text)
                base_lines = cue.lines if keep_current else previous.cue.lines
                merged_cue = SubtitleCue(
                    index=previous.cue.index,
                    start=previous.cue.start,
                    end=max(previous.cue.end, cue.end),
                    lines=list(base_lines),
                )
                result[-1] = merged_cue
                previous = _NormalizedCueWindow(cue=merged_cue, normalized_text=_normalize_text(" ".join(base_lines)))
                continue

        container = _NormalizedCueWindow(cue=cue, normalized_text=normalized)
        result.append(cue)
        previous = container

    return result


def _merge_overlapping_lines(
    cues: Sequence[SubtitleCue],
    *,
    max_gap_seconds: float = 0.55,
    max_window_seconds: float = 5.5,
) -> List[SubtitleCue]:
    """Merge cues whose trailing line repeats as the leading line of the next."""

    if not cues:
        return []

    merged: List[SubtitleCue] = []
    active = cues[0]

    def _normalize_lines(lines: Sequence[str]) -> List[str]:
        return [_normalize_text(line) for line in lines if _normalize_text(line)]

    for cue in cues[1:]:
        gap = max(0.0, cue.start - active.end)
        active_norm = _normalize_lines(active.lines)
        cue_norm = _normalize_lines(cue.lines)

        overlap_len = 0
        max_overlap = min(len(active_norm), len(cue_norm))
        for size in range(max_overlap, 0, -1):
            if active_norm[-size:] == cue_norm[:size]:
                overlap_len = size
                break

        trimmed_lines = list(cue.lines)
        if overlap_len > 0 and overlap_len <= len(cue.lines):
            trimmed_lines = cue.lines[overlap_len:]

        if overlap_len > 0:
            # If the next cue is fully redundant, just extend the window.
            if not trimmed_lines and gap <= max_gap_seconds:
                active = SubtitleCue(
                    index=active.index,
                    start=active.start,
                    end=max(active.end, cue.end),
                    lines=list(active.lines),
                )
                continue

            # Merge when the overlap dominates the next cue and the window stays bounded.
            should_merge = (
                gap <= max_gap_seconds
                and (overlap_len >= len(cue_norm) * 0.85 or len(cue_norm) <= 2)
                and (cue.end - active.start + gap) <= max_window_seconds
            )
            if should_merge:
                preserved_lines = list(active.lines)
                if trimmed_lines:
                    preserved_lines.extend(trimmed_lines)
                active = SubtitleCue(
                    index=active.index,
                    start=active.start,
                    end=max(active.end, cue.end),
                    lines=preserved_lines,
                )
                continue
            # Otherwise, keep the next cue but drop the duplicated lead lines.
            if trimmed_lines != list(cue.lines):
                cue = SubtitleCue(
                    index=cue.index,
                    start=cue.start,
                    end=cue.end,
                    lines=trimmed_lines,
                )

        merged.append(active)
        active = cue

    merged.append(active)
    return merged


def _merge_youtube_windows(
    cues: Sequence[SubtitleCue],
    *,
    target_window_seconds: float = 5.5,
    max_window_seconds: float = 7.0,
    max_gap_seconds: float = 0.75,
    min_gap_seconds: float = 0.0,
    min_duration_seconds: float = 0.35,
) -> List[SubtitleCue]:
    """Merge overlapping/adjacent YouTube cues into ~5s windows without duplicate lines."""

    if not cues:
        return []

    def _merge_lines(existing: Sequence[str], incoming: Sequence[str]) -> List[str]:
        merged = list(existing)
        incoming_lines = list(incoming)

        if merged and incoming_lines:
            trailing = _normalize_text(merged[-1])
            leading = _normalize_text(incoming_lines[0])
            if trailing and leading:
                trailing_tokens = trailing.split()
                leading_tokens = leading.split()
                max_overlap = min(len(trailing_tokens), len(leading_tokens))
                overlap_tokens = 0
                for size in range(max_overlap, 0, -1):
                    if trailing_tokens[-size:] == leading_tokens[:size]:
                        overlap_tokens = size
                        break
                if overlap_tokens > 0:
                    raw_leading_tokens = incoming_lines[0].split()
                    if len(raw_leading_tokens) >= overlap_tokens:
                        trimmed = " ".join(raw_leading_tokens[overlap_tokens:]).strip()
                        incoming_lines[0] = trimmed

        seen = {_normalize_text(line) for line in merged if _normalize_text(line)}
        for line in incoming_lines:
            normalized = _normalize_text(line)
            if not normalized or normalized in seen:
                continue
            merged.append(line)
            seen.add(normalized)
        return merged

    sorted_cues = sorted(cues, key=lambda cue: (cue.start, cue.end))
    window_start = sorted_cues[0].start
    window_end = sorted_cues[0].end
    window_lines = list(sorted_cues[0].lines)
    merged: List[SubtitleCue] = []

    for cue in sorted_cues[1:]:
        gap = max(0.0, cue.start - window_end)
        candidate_end = max(window_end, cue.end)
        candidate_duration = candidate_end - window_start

        should_merge = (
            gap <= max_gap_seconds
            or candidate_duration < target_window_seconds
        )

        if should_merge and candidate_duration <= max_window_seconds:
            window_end = candidate_end
            window_lines = _merge_lines(window_lines, cue.lines)
            continue

        merged.append(
            SubtitleCue(
                index=len(merged) + 1,
                start=window_start,
                end=window_end,
                lines=list(window_lines),
            )
        )
        window_start = cue.start
        window_end = cue.end
        window_lines = list(cue.lines)

    merged.append(
        SubtitleCue(
            index=len(merged) + 1,
            start=window_start,
            end=window_end,
            lines=list(window_lines),
        )
    )

    # Enforce non-overlapping windows with a small guard gap.
    normalized = _normalize_cue_timeline(
        merged,
        min_gap_seconds=min_gap_seconds,
        min_duration_seconds=min_duration_seconds,
    )
    return normalized


def merge_youtube_subtitle_cues(
    cues: Sequence[SubtitleCue],
    *,
    target_window_seconds: float = 5.5,
    max_window_seconds: float = 7.0,
    max_gap_seconds: float = 0.75,
    min_gap_seconds: float = 0.0,
) -> List[SubtitleCue]:
    """Normalize YouTube cues into ~5s non-overlapping windows ready for rendering."""

    merged = _merge_youtube_windows(
        cues,
        target_window_seconds=target_window_seconds,
        max_window_seconds=max_window_seconds,
        max_gap_seconds=max_gap_seconds,
        min_gap_seconds=min_gap_seconds,
        min_duration_seconds=0.35,
    )
    merged = _collapse_redundant_windows(
        merged,
        max_gap_seconds=max_gap_seconds,
    )
    merged = _deduplicate_cues_by_text(
        merged,
        max_gap_seconds=max_gap_seconds + 0.25,
        min_containment_ratio=0.45,
        min_similarity=0.82,
    )
    merged = _merge_overlapping_lines(
        merged,
        max_gap_seconds=max_gap_seconds,
        max_window_seconds=max_window_seconds,
    )
    return _normalize_cue_timeline(
        merged,
        min_gap_seconds=min_gap_seconds,
        min_duration_seconds=0.35,
    )


def _texts_overlap(
    current: str,
    previous: str,
    *,
    min_containment_ratio: float,
    min_similarity: float,
) -> bool:
    if not current or not previous:
        return False
    if current == previous:
        return True
    shorter, longer = (current, previous) if len(current) <= len(previous) else (previous, current)
    ratio = len(shorter) / max(len(longer), 1)
    if longer.startswith(shorter) and ratio >= min_containment_ratio:
        return True
    if shorter in longer and ratio >= min_containment_ratio:
        return True
    similarity = SequenceMatcher(None, current, previous).ratio()
    return similarity >= min_similarity


def _merge_redundant_rendered_cues(
    cues: Sequence[SubtitleCue],
    *,
    max_gap_seconds: float = 0.25,
) -> List[SubtitleCue]:
    if not cues:
        return []

    merged: List[SubtitleCue] = []
    previous: Optional[SubtitleCue] = None
    previous_normalized = ""

    for cue in cues:
        normalized = _normalize_rendered_lines(cue.lines)
        if (
            previous is not None
            and normalized
            and normalized == previous_normalized
            and (cue.start - previous.end) <= max_gap_seconds
        ):
            previous = SubtitleCue(
                index=previous.index,
                start=min(previous.start, cue.start),
                end=max(previous.end, cue.end),
                lines=list(cue.lines),
            )
            merged[-1] = previous
            continue

        merged.append(cue)
        previous = cue
        previous_normalized = normalized

    return merged


def _merge_adjacent_rendered_cues(
    cues: Sequence[SubtitleCue],
    *,
    max_gap_seconds: float = 2.0,
) -> List[SubtitleCue]:
    if not cues:
        return []

    merged: List[SubtitleCue] = []
    for cue in cues:
        if not merged:
            merged.append(cue)
            continue

        previous = merged[-1]
        gap = cue.start - previous.end
        if gap < 0:
            gap = 0.0

        prev_text = _normalize_rendered_lines(previous.lines)
        current_text = _normalize_rendered_lines(cue.lines)
        similar = False
        if prev_text and current_text:
            if prev_text == current_text:
                similar = True
            else:
                similar = _texts_overlap(
                    prev_text,
                    current_text,
                    min_containment_ratio=0.5,
                    min_similarity=0.85,
                )
        if similar and gap <= max_gap_seconds:
            keep_current = len(current_text) >= len(prev_text)
            base_lines = cue.lines if keep_current else previous.lines
            merged[-1] = SubtitleCue(
                index=previous.index,
                start=min(previous.start, cue.start),
                end=max(previous.end, cue.end),
                lines=list(base_lines),
            )
            continue

        merged.append(cue)

    return merged


def _merge_rendered_timeline(
    cues: Sequence[SubtitleCue],
    *,
    max_gap_seconds: float = 2.0,
    preserve_states: bool = False,
) -> List[SubtitleCue]:
    if not cues:
        return []
    if preserve_states:
        # Keep highlight progression intact; preserve original state order.
        return list(cues)

    sorted_cues = sorted(cues, key=lambda c: (c.start, c.end))
    merged: List[SubtitleCue] = []
    normalized_cache: List[str] = []

    for cue in _merge_adjacent_rendered_cues(sorted_cues, max_gap_seconds=max_gap_seconds):
        current_text = _normalize_rendered_lines(cue.lines)
        start_time = cue.start
        if merged:
            previous = merged[-1]
            prev_text = normalized_cache[-1]
            gap = max(0.0, start_time - previous.end)
            similar = False
            if prev_text and current_text:
                if prev_text == current_text:
                    similar = True
                else:
                    similar = _texts_overlap(
                        prev_text,
                        current_text,
                        min_containment_ratio=0.4,
                        min_similarity=0.8,
                    )
            if similar and gap <= max_gap_seconds:
                keep_current = len(current_text) >= len(prev_text)
                base_lines = cue.lines if keep_current else previous.lines
                merged[-1] = SubtitleCue(
                    index=previous.index,
                    start=min(previous.start, cue.start),
                    end=max(previous.end, cue.end),
                    lines=list(base_lines),
                )
                normalized_cache[-1] = _normalize_rendered_lines(base_lines)
                continue
            if start_time < previous.end:
                # Avoid overlapping windows by snapping to the prior end.
                cue = SubtitleCue(
                    index=cue.index,
                    start=previous.end,
                    end=max(previous.end, cue.end),
                    lines=list(cue.lines),
                )
        merged.append(cue)
        normalized_cache.append(current_text)

    return merged


__all__ = [
    "_collapse_redundant_windows",
    "_count_overlapping_cues",
    "_deduplicate_cues_by_text",
    "_merge_adjacent_rendered_cues",
    "_merge_overlapping_lines",
    "_merge_redundant_rendered_cues",
    "_merge_rendered_timeline",
    "_merge_youtube_windows",
    "_normalize_cue_timeline",
    "_should_merge_youtube_cues",
    "_split_long_cues",
    "_texts_overlap",
    "merge_youtube_subtitle_cues",
]
