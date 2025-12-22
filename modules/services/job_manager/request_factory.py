"""Helpers for constructing :class:`PipelineRequest` instances."""

from __future__ import annotations

import threading
from typing import Any, Callable, Mapping, Optional

from ...progress_tracker import ProgressEvent, ProgressTracker
from ..pipeline_service import PipelineInput, PipelineRequest
from ..pipeline_types import PipelineMetadata
from .job import PipelineJob


def _coerce_bool(value: Any, default: bool = False) -> bool:
    """Return ``value`` coerced to :class:`bool` with ``default`` fallback."""

    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False
    return bool(value)


def _coerce_int(value: Any, default: int = 0) -> int:
    """Return ``value`` coerced to :class:`int` with ``default`` fallback."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    """Return ``value`` coerced to :class:`float` with ``default`` fallback."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_pipeline_input(payload: Mapping[str, Any]) -> PipelineInput:
    """Construct a :class:`PipelineInput` from ``payload``."""

    data = dict(payload or {})
    raw_targets = data.get("target_languages") or []
    if isinstance(raw_targets, list):
        target_languages = [str(item) for item in raw_targets]
    elif isinstance(raw_targets, (tuple, set)):
        target_languages = [str(item) for item in raw_targets]
    elif raw_targets is None:
        target_languages = []
    else:
        target_languages = [str(raw_targets)]

    end_sentence_value = data.get("end_sentence")
    end_sentence = None
    if end_sentence_value is not None:
        try:
            end_sentence = int(end_sentence_value)
        except (TypeError, ValueError):
            end_sentence = None

    book_metadata = data.get("book_metadata")
    if not isinstance(book_metadata, Mapping):
        book_metadata = {}

    return PipelineInput(
        input_file=str(data.get("input_file") or ""),
        base_output_file=str(data.get("base_output_file") or ""),
        input_language=str(data.get("input_language") or ""),
        target_languages=target_languages,
        sentences_per_output_file=_coerce_int(data.get("sentences_per_output_file"), 1),
        start_sentence=_coerce_int(data.get("start_sentence"), 1),
        end_sentence=end_sentence,
        stitch_full=_coerce_bool(data.get("stitch_full")),
        generate_audio=_coerce_bool(data.get("generate_audio")),
        audio_mode=str(data.get("audio_mode") or ""),
        audio_bitrate_kbps=_coerce_int(data.get("audio_bitrate_kbps"), 0) or None,
        written_mode=str(data.get("written_mode") or ""),
        selected_voice=str(data.get("selected_voice") or ""),
        output_html=_coerce_bool(data.get("output_html")),
        output_pdf=_coerce_bool(data.get("output_pdf")),
        generate_video=_coerce_bool(data.get("generate_video")),
        add_images=_coerce_bool(data.get("add_images"), False),
        include_transliteration=_coerce_bool(data.get("include_transliteration"), True),
        tempo=_coerce_float(data.get("tempo"), 1.0),
        book_metadata=PipelineMetadata.from_mapping(book_metadata),
    )


def _hydrate_request_from_payload(
    job: PipelineJob,
    payload: Mapping[str, Any],
    *,
    tracker_factory: Callable[[], ProgressTracker],
    stop_event_factory: Callable[[], threading.Event],
    observer_factory: Optional[Callable[[PipelineJob], Callable[[ProgressEvent], None]]] = None,
    pipeline_input_builder: Callable[[Mapping[str, Any]], PipelineInput] = _build_pipeline_input,
    stop_event: Optional[threading.Event] = None,
) -> PipelineRequest:
    """Reconstruct a :class:`PipelineRequest` from persisted ``payload``."""

    data = dict(payload or {})
    config = dict(data.get("config") or {})
    environment_overrides = dict(data.get("environment_overrides") or {})
    pipeline_overrides = dict(data.get("pipeline_overrides") or {})

    inputs_payload = data.get("inputs")
    if not isinstance(inputs_payload, Mapping):
        inputs_payload = {}

    tracker = job.tracker
    if tracker is None:
        tracker = tracker_factory()
        if observer_factory is not None:
            tracker.register_observer(observer_factory(job))
        job.tracker = tracker

    resolved_stop_event = (
        stop_event
        or job.stop_event
        or (job.request.stop_event if job.request is not None else None)
    )
    if resolved_stop_event is None:
        resolved_stop_event = stop_event_factory()

    correlation_id = data.get("correlation_id")
    if correlation_id is None and job.request is not None:
        correlation_id = job.request.correlation_id

    resolved_audio_mode = inputs_payload.get("audio_mode")
    if (
        isinstance(resolved_audio_mode, str)
        and resolved_audio_mode.strip()
        and "audio_mode" not in pipeline_overrides
    ):
        pipeline_overrides["audio_mode"] = resolved_audio_mode.strip()
    resolved_audio_bitrate = inputs_payload.get("audio_bitrate_kbps")
    if "audio_bitrate_kbps" not in pipeline_overrides:
        try:
            bitrate_value = int(resolved_audio_bitrate)
        except (TypeError, ValueError):
            bitrate_value = None
        if bitrate_value and bitrate_value > 0:
            pipeline_overrides["audio_bitrate_kbps"] = bitrate_value

    request = PipelineRequest(
        config=config,
        context=job.request.context if job.request is not None else None,
        environment_overrides=environment_overrides,
        pipeline_overrides=pipeline_overrides,
        inputs=pipeline_input_builder(inputs_payload),
        progress_tracker=tracker,
        stop_event=resolved_stop_event,
        translation_pool=None,
        correlation_id=correlation_id,
        job_id=job.job_id,
    )

    return request


class PipelineRequestFactory:
    """Factory for creating :class:`PipelineRequest` objects for jobs."""

    def __init__(
        self,
        *,
        tracker_factory: Callable[[], ProgressTracker],
        stop_event_factory: Callable[[], threading.Event],
        observer_factory: Optional[Callable[[PipelineJob], Callable[[ProgressEvent], None]]] = None,
        pipeline_input_builder: Callable[[Mapping[str, Any]], PipelineInput] = _build_pipeline_input,
    ) -> None:
        self._tracker_factory = tracker_factory
        self._stop_event_factory = stop_event_factory
        self._observer_factory = observer_factory
        self._pipeline_input_builder = pipeline_input_builder

    def hydrate_request(
        self,
        job: PipelineJob,
        payload: Mapping[str, Any],
        *,
        stop_event: Optional[threading.Event] = None,
    ) -> PipelineRequest:
        """Hydrate a :class:`PipelineRequest` for ``job`` from ``payload``."""

        return _hydrate_request_from_payload(
            job,
            payload,
            tracker_factory=self._tracker_factory,
            stop_event_factory=self._stop_event_factory,
            observer_factory=self._observer_factory,
            pipeline_input_builder=self._pipeline_input_builder,
            stop_event=stop_event,
        )


__all__ = [
    "PipelineRequestFactory",
    "_build_pipeline_input",
    "_coerce_bool",
    "_coerce_float",
    "_coerce_int",
    "_hydrate_request_from_payload",
]
