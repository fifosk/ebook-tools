"""Helpers for validating and applying pipeline job lifecycle transitions."""

from __future__ import annotations

import copy
from typing import Any, Dict, Mapping, Optional

from ..pipeline_service import serialize_pipeline_request
from .job import PipelineJob, PipelineJobStatus

_TERMINAL_STATES = {
    PipelineJobStatus.COMPLETED,
    PipelineJobStatus.FAILED,
    PipelineJobStatus.CANCELLED,
}


def _coerce_positive_int(value: Any) -> Optional[int]:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _resolve_base_payload(job: PipelineJob) -> Optional[Dict[str, Any]]:
    if job.request_payload is not None:
        return copy.deepcopy(job.request_payload)
    if job.request is not None:
        return serialize_pipeline_request(job.request)
    return None


def _resolve_inputs(payload: Dict[str, Any]) -> Dict[str, Any]:
    raw_inputs = payload.get("inputs")
    if isinstance(raw_inputs, dict):
        return raw_inputs
    inputs: Dict[str, Any] = {}
    payload["inputs"] = inputs
    return inputs


def _extract_last_sentence(job: PipelineJob) -> Optional[int]:
    event = job.last_event
    if event is None:
        return None
    metadata = event.metadata
    if not isinstance(metadata, Mapping):
        return None
    candidates = (
        metadata.get("sentence_number"),
        metadata.get("sentence"),
        metadata.get("current_sentence"),
    )
    for candidate in candidates:
        value = _coerce_positive_int(candidate)
        if value is not None:
            return value
    return None


def _resolve_block_size(job: PipelineJob, inputs: Mapping[str, Any]) -> int:
    candidate = _coerce_positive_int(inputs.get("sentences_per_output_file"))
    if candidate is not None and candidate > 0:
        return candidate
    if job.request is not None:
        try:
            return max(1, int(job.request.inputs.sentences_per_output_file))
        except Exception:  # pragma: no cover - defensive fallback
            pass
    return 1


def _compute_block_start(sentence_number: int, block_size: int, base_start: int) -> int:
    """Return the first sentence for the block containing ``sentence_number``."""

    if sentence_number <= 0:
        return max(1, base_start)

    size = max(1, block_size)
    origin = max(1, base_start)
    if sentence_number <= origin:
        return origin

    offset = sentence_number - origin
    block_index = offset // size
    return origin + block_index * size


def compute_resume_context(job: PipelineJob) -> Optional[Dict[str, Any]]:
    """Return a payload describing how to resume ``job`` from the last block."""

    payload = _resolve_base_payload(job)
    if payload is None:
        return None

    inputs = _resolve_inputs(payload)
    last_sentence = _extract_last_sentence(job)
    if last_sentence is None and job.last_event is not None:
        completed = _coerce_positive_int(job.last_event.snapshot.completed)
        if completed is not None:
            base_start = _coerce_positive_int(inputs.get("start_sentence")) or 1
            last_sentence = max(base_start, base_start + completed - 1)

    block_size = _resolve_block_size(job, inputs)

    start_sentence = _coerce_positive_int(inputs.get("start_sentence"))
    if start_sentence is None:
        start_sentence = 1

    if last_sentence is not None:
        block_start = _compute_block_start(last_sentence, block_size, start_sentence)
        inputs["start_sentence"] = block_start
        inputs["resume_block_start"] = block_start
        inputs["resume_last_sentence"] = last_sentence
        inputs["resume_next_sentence"] = last_sentence + 1
    else:
        inputs.setdefault("resume_block_start", start_sentence)

    return payload


def apply_resume_context(job: PipelineJob, context: Mapping[str, Any]) -> Dict[str, Any]:
    """Persist ``context`` on ``job`` and update attached request metadata."""

    payload = copy.deepcopy(dict(context))
    inputs = _resolve_inputs(payload)

    start_sentence = _coerce_positive_int(inputs.get("start_sentence"))
    if job.request is not None and start_sentence is not None:
        job.request.inputs.start_sentence = start_sentence
    if job.request is not None and isinstance(inputs.get("book_metadata"), Mapping):
        job.request.inputs.book_metadata = dict(inputs["book_metadata"])

    job.request_payload = copy.deepcopy(payload)
    job.resume_context = payload
    return payload


def apply_pause_transition(job: PipelineJob) -> None:
    """Validate and persist state changes required to pause ``job``."""

    if job.status in _TERMINAL_STATES:
        raise ValueError(
            f"Cannot pause job {job.job_id} in terminal state {job.status.value}"
        )
    if job.status == PipelineJobStatus.PAUSED:
        raise ValueError(f"Job {job.job_id} is already paused")
    if job.status != PipelineJobStatus.RUNNING:
        raise ValueError(
            f"Cannot pause job {job.job_id} from state {job.status.value}"
        )

    context = compute_resume_context(job)
    if context is not None:
        job.resume_context = context
    job.status = PipelineJobStatus.PAUSED


def apply_resume_transition(job: PipelineJob) -> None:
    """Validate and persist state changes required to resume ``job``."""

    if job.status != PipelineJobStatus.PAUSED:
        raise ValueError(
            f"Cannot resume job {job.job_id} from state {job.status.value}"
        )

    context = job.resume_context or compute_resume_context(job)
    if context is not None:
        apply_resume_context(job, context)
    job.status = PipelineJobStatus.PENDING


__all__ = [
    "apply_pause_transition",
    "apply_resume_transition",
    "apply_resume_context",
    "compute_resume_context",
]
