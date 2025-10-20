"""Audio media generation pipeline utilities."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, replace
from queue import Empty, Full, Queue
from typing import Callable, List, Mapping, Optional, Tuple, TYPE_CHECKING

from pydub import AudioSegment

from modules import config_manager as cfg
from modules import logging_manager as log_mgr
from modules.translation_engine import TranslationTask

if TYPE_CHECKING:  # pragma: no cover - imported for type checking only
    from modules.progress_tracker import ProgressTracker

logger = log_mgr.logger


@dataclass(slots=True)
class MediaPipelineResult:
    """Result produced by the media generation workers."""

    index: int
    sentence_number: int
    sentence: str
    target_language: str
    translation: str
    audio_segment: Optional[AudioSegment]


@dataclass(frozen=True)
class PipelineDependencies:
    """Collection of callables required by the media pipeline."""

    generate_audio_for_sentence: Optional[
        Callable[
            [
                int,
                str,
                str,
                str,
                str,
                str,
                int,
                Mapping[str, str],
                str,
                float,
                int,
            ],
            AudioSegment,
        ]
    ] = None
    get_thread_count: Callable[[], int] = cfg.get_thread_count
    get_runtime_context: Callable[[Optional[cfg.RuntimeContext]], Optional[cfg.RuntimeContext]] = cfg.get_runtime_context
    set_runtime_context: Callable[[cfg.RuntimeContext], None] = cfg.set_runtime_context
    clear_runtime_context: Callable[[], None] = cfg.clear_runtime_context


_dependencies = PipelineDependencies()


def configure_pipeline_dependencies(**overrides: object) -> None:
    """Update the callables used by the media pipeline."""

    global _dependencies
    _dependencies = replace(_dependencies, **overrides)


def _require_dependency(name: str) -> object:
    value = getattr(_dependencies, name)
    if value is None:
        raise RuntimeError(f"Pipeline dependency '{name}' has not been configured.")
    return value


def _media_worker(
    name: str,
    task_queue: Queue[Optional[TranslationTask]],
    result_queue: Queue[Optional[MediaPipelineResult]],
    *,
    total_sentences: int,
    input_language: str,
    audio_mode: str,
    language_codes: Mapping[str, str],
    selected_voice: str,
    tempo: float,
    macos_reading_speed: int,
    generate_audio: bool,
    stop_event: Optional[threading.Event] = None,
    progress_tracker: Optional["ProgressTracker"] = None,
) -> None:
    """Consume translation results and emit completed media payloads."""

    generate_audio_for_sentence = _require_dependency("generate_audio_for_sentence")

    while True:
        if stop_event and stop_event.is_set():
            break
        try:
            task = task_queue.get(timeout=0.1)
        except Empty:
            continue
        if task is None:
            task_queue.task_done()
            break
        start_time = time.perf_counter()
        audio_segment: Optional[AudioSegment] = None
        try:
            if generate_audio:
                audio_segment = generate_audio_for_sentence(
                    task.sentence_number,
                    task.sentence,
                    task.translation,
                    input_language,
                    task.target_language,
                    audio_mode,
                    total_sentences,
                    language_codes,
                    selected_voice,
                    tempo,
                    macos_reading_speed,
                )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Consumer %s failed for sentence %s: %s", name, task.sentence_number, exc
            )
            if generate_audio:
                audio_segment = AudioSegment.silent(duration=0)
        finally:
            task_queue.task_done()
        elapsed = time.perf_counter() - start_time
        logger.debug(
            "Consumer %s processed sentence %s in %.3fs",
            name,
            task.sentence_number,
            elapsed,
        )
        payload = MediaPipelineResult(
            index=task.index,
            sentence_number=task.sentence_number,
            sentence=task.sentence,
            target_language=task.target_language,
            translation=task.translation,
            audio_segment=audio_segment,
        )
        while True:
            if stop_event and stop_event.is_set():
                break
            try:
                result_queue.put(payload, timeout=0.1)
                if progress_tracker:
                    progress_tracker.record_media_completion(
                        payload.index, payload.sentence_number
                    )
                break
            except Full:
                continue


def start_media_pipeline(
    task_queue: Queue[Optional[TranslationTask]],
    *,
    worker_count: Optional[int] = None,
    total_sentences: int,
    input_language: str,
    audio_mode: str,
    language_codes: Mapping[str, str],
    selected_voice: str,
    tempo: float,
    macos_reading_speed: int,
    generate_audio: bool,
    queue_size: Optional[int] = None,
    stop_event: Optional[threading.Event] = None,
    progress_tracker: Optional["ProgressTracker"] = None,
) -> Tuple[Queue[Optional[MediaPipelineResult]], List[threading.Thread]]:
    """Start consumer threads that transform translations into media artifacts."""

    get_thread_count = _dependencies.get_thread_count
    get_runtime_context = _dependencies.get_runtime_context
    set_runtime_context = _dependencies.set_runtime_context
    clear_runtime_context = _dependencies.clear_runtime_context

    worker_total = worker_count or get_thread_count()
    worker_total = max(1, worker_total)
    result_queue: Queue[Optional[MediaPipelineResult]] = Queue(maxsize=queue_size or 0)
    stop_event = stop_event or threading.Event()
    workers: List[threading.Thread] = []
    active_context = get_runtime_context(None)

    def _thread_target(*args, **kwargs) -> None:
        if active_context is not None:
            set_runtime_context(active_context)
        try:
            _media_worker(*args, **kwargs)
        finally:
            if active_context is not None:
                clear_runtime_context()

    for idx in range(worker_total):
        thread_name = f"Consumer-{idx + 1}"
        thread = threading.Thread(
            target=_thread_target,
            name=thread_name,
            args=(
                thread_name,
                task_queue,
                result_queue,
            ),
            kwargs={
                "total_sentences": total_sentences,
                "input_language": input_language,
                "audio_mode": audio_mode,
                "language_codes": language_codes,
                "selected_voice": selected_voice,
                "tempo": tempo,
                "macos_reading_speed": macos_reading_speed,
                "generate_audio": generate_audio,
                "stop_event": stop_event,
                "progress_tracker": progress_tracker,
            },
            daemon=True,
        )
        thread.start()
        workers.append(thread)
    return result_queue, workers

