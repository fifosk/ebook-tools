"""Background service coordinating subtitle processing jobs."""

from __future__ import annotations

import copy
import os
import queue
import re
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from modules import config_manager as cfg
from modules import logging_manager as log_mgr
from modules.core.rendering.constants import LANGUAGE_CODES
from modules.core.rendering.exporters import BatchExportRequest, build_exporter
from modules.render.backends import get_audio_synthesizer
from modules.retry_annotations import is_failure_annotation
from modules.services.file_locator import FileLocator
from modules.services.job_manager import PipelineJobManager, PipelineJobStatus
from modules.services.youtube_dubbing import delete_nas_subtitle
from modules.subtitles import SubtitleCue, SubtitleJobOptions
from modules.subtitles.common import ASS_EXTENSION, DEFAULT_OUTPUT_SUFFIX, SRT_EXTENSION
from modules.subtitles.models import SubtitleHtmlEntry
from modules.subtitles.processing import (
    SubtitleJobCancelled,
    SubtitleProcessingError,
    load_subtitle_cues,
    merge_youtube_subtitle_cues,
    process_subtitle_file,
)
from pydub import AudioSegment

logger = log_mgr.get_logger().getChild("services.subtitles")

SUPPORTED_EXTENSIONS = {".srt", ".vtt"}
DISCOVERABLE_EXTENSIONS = SUPPORTED_EXTENSIONS | {".ass"}

_FILENAME_SAFE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename_fragment(value: str, fallback: str = "subtitle") -> str:
    """Return a filesystem-friendly identifier derived from ``value``."""

    if not isinstance(value, str):
        return fallback
    trimmed = value.strip()
    if not trimmed:
        return fallback
    candidate = _FILENAME_SAFE_PATTERN.sub("_", trimmed).strip("._-")
    return candidate or fallback


def _format_episode_code(season: int, episode: int) -> str:
    return f"S{season:02d}E{episode:02d}"


@dataclass(frozen=True)
class SubtitleSubmission:
    """Description of a subtitle submission request."""

    source_path: Path
    original_name: str
    options: SubtitleJobOptions
    cleanup: bool = False
    media_metadata: Optional[Dict[str, Any]] = None


class SubtitleService:
    """Coordinate ingestion and processing of subtitle jobs."""

    def __init__(
        self,
        job_manager: PipelineJobManager,
        *,
        locator: Optional[FileLocator] = None,
        default_source_dir: Optional[Path] = None,
    ) -> None:
        self._job_manager = job_manager
        self._locator = locator or job_manager.file_locator
        self._default_source_dir = Path(
            default_source_dir
        ).expanduser() if default_source_dir is not None else Path(
            "/Volumes/Data/Download/Subtitles"
        ).expanduser()
        self._mirror_warning_logged = False

    @property
    def default_source_dir(self) -> Path:
        """Return the configured subtitle source directory used for mirroring."""

        return self._default_source_dir

    def _probe_directory(self, path: Path, *, require_write: bool) -> Optional[Path]:
        candidate = path.expanduser()
        try:
            resolved = candidate.resolve(strict=False)
        except OSError:
            logger.debug(
                "Unable to resolve subtitle directory %s",
                candidate,
                exc_info=True,
            )
            return None
        if not resolved.exists() or not resolved.is_dir():
            return None
        if not os.access(resolved, os.R_OK):
            return None
        if require_write and not os.access(resolved, os.W_OK):
            return None
        return resolved

    def _copy_html_companion(self, source_subtitle: Path, destination_dir: Path) -> None:
        """Best-effort copy of the generated HTML transcript to ``destination_dir``."""

        html_source = source_subtitle.parent / "html" / f"{source_subtitle.stem}.html"
        if not html_source.exists():
            return
        try:
            html_target_dir = destination_dir / "html"
            html_target_dir.mkdir(parents=True, exist_ok=True)
            html_target = html_target_dir / html_source.name
            if html_target == html_source:
                return
            shutil.copy2(html_source, html_target)
        except Exception:  # pragma: no cover - best effort mirror
            logger.warning(
                "Unable to mirror HTML transcript %s to %s",
                html_source,
                destination_dir,
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def enqueue(
        self,
        submission: SubtitleSubmission,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ):
        """Register ``submission`` for processing and return the job handle."""

        resolved_source = submission.source_path.expanduser().resolve()
        if not resolved_source.exists():
            raise FileNotFoundError(f"Subtitle source '{resolved_source}' does not exist")
        if resolved_source.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported subtitle extension '{resolved_source.suffix}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        options = submission.options
        source_name = submission.original_name or resolved_source.name
        def _setup(job):
            data_root = self._locator.data_root(job.job_id)
            data_root.mkdir(parents=True, exist_ok=True)
            target_path = data_root / source_name
            shutil.copy2(resolved_source, target_path)
            if submission.cleanup:
                try:
                    resolved_source.unlink(missing_ok=True)  # type: ignore[arg-type]
                except Exception:  # pragma: no cover - best effort
                    logger.debug(
                        "Unable to delete temporary subtitle source %s",
                        resolved_source,
                        exc_info=True,
                    )
            job.request_payload = {
                "source_file": target_path.name,
                "options": options.to_dict(),
                "submitted_source": str(resolved_source),
                "original_name": source_name,
                "cleanup": submission.cleanup,
            }
            if submission.media_metadata:
                job.request_payload["media_metadata"] = copy.deepcopy(submission.media_metadata)
            tracker_local = job.tracker
            if tracker_local is not None:
                try:
                    cues = load_subtitle_cues(target_path)
                except Exception as exc:
                    raise SubtitleProcessingError(
                        f"Failed to parse {target_path.name}: {exc}"
                    ) from exc
                total_steps = len(cues)
                if options.generate_audio_book:
                    total_steps *= 2
                tracker_local.set_total(total_steps)

        def _worker(job):
            tracker_local = job.tracker
            stop_event = job.stop_event or threading.Event()
            data_root = self._locator.data_root(job.job_id)
            source_file = (job.request_payload or {}).get("source_file") if job.request_payload else None
            if not source_file:
                job.status = PipelineJobStatus.FAILED
                job.error_message = "Missing source file for subtitle job"
                return
            input_path = data_root / str(source_file)
            subtitles_root = self._locator.subtitles_root(job.job_id)
            subtitles_root.mkdir(parents=True, exist_ok=True)
            target_fragment = options.target_language.lower().replace(" ", "-")
            source_stem = Path(source_file).stem
            extension = ASS_EXTENSION if options.output_format == "ass" else SRT_EXTENSION
            output_name = f"{source_stem}.{target_fragment}.{DEFAULT_OUTPUT_SUFFIX}{extension}"
            output_path = subtitles_root / output_name
            try:
                output_path.unlink(missing_ok=True)
            except Exception:  # pragma: no cover - defensive cleanup
                logger.debug("Unable to remove existing subtitle output %s", output_path, exc_info=True)
            mirror_dir: Optional[Path] = None
            mirror_path: Optional[Path] = None
            if options.mirror_batches_to_source_dir:
                mirror_dir = self._probe_directory(
                    self._default_source_dir,
                    require_write=True,
                )
                if mirror_dir is None:
                    if not self._mirror_warning_logged:
                        logger.info(
                            "Subtitle mirror directory %s is unavailable; continuing without live mirroring.",
                            self._default_source_dir,
                        )
                        self._mirror_warning_logged = True
                else:
                    self._mirror_warning_logged = False
                    candidate = mirror_dir / output_name
                    if candidate != output_path:
                        mirror_path = candidate

            display_title = Path(source_name or str(source_file)).stem
            safe_title = _sanitize_filename_fragment(display_title, fallback="Subtitle Job")

            audio_queue: Optional[queue.Queue[Optional[Tuple[int, SubtitleHtmlEntry]]]] = None
            audio_thread: Optional[threading.Thread] = None
            audio_shutdown = threading.Event()
            audio_errors: List[BaseException] = []
            audio_error_event = threading.Event()
            on_transcript_batch: Optional[
                Callable[[Sequence[Tuple[int, SubtitleHtmlEntry]]], None]
            ] = None

            if options.generate_audio_book:

                def _estimate_sentence_count() -> int:
                    cues = load_subtitle_cues(input_path)
                    start_offset = max(0.0, options.start_time_offset or 0.0)
                    end_offset = options.end_time_offset
                    if end_offset is not None:
                        end_offset = max(0.0, float(end_offset))
                        if end_offset <= start_offset:
                            return 0

                    if start_offset > 0 or end_offset is not None:
                        trimmed: List[SubtitleCue] = []
                        for cue in cues:
                            if cue.start < start_offset:
                                continue
                            if end_offset is not None and cue.start >= end_offset:
                                continue
                            clipped_end = cue.end
                            if end_offset is not None and cue.end > end_offset:
                                clipped_end = float(end_offset)
                            if clipped_end <= cue.start:
                                continue
                            trimmed.append(
                                SubtitleCue(
                                    index=cue.index,
                                    start=cue.start,
                                    end=clipped_end,
                                    lines=list(cue.lines),
                                )
                            )
                        cues = trimmed

                    return len(merge_youtube_subtitle_cues(cues))

                estimated_total_sentences = max(_estimate_sentence_count(), 1)
                settings = cfg.get_settings()
                media_root = self._locator.media_root(job.job_id)
                media_root.mkdir(parents=True, exist_ok=True)
                synthesizer = get_audio_synthesizer()
                input_lang = options.original_language or options.input_language
                selected_voice = getattr(settings, "selected_voice", "gTTS") or "gTTS"
                tempo = float(getattr(settings, "tempo", 1.0) or 1.0)
                macos_speed = int(getattr(settings, "macos_reading_speed", 100) or 100)
                tts_backend = str(getattr(settings, "tts_backend", "") or "").strip() or "auto"
                tts_executable = getattr(settings, "tts_executable_path", None)
                sync_ratio = float(getattr(settings, "sync_ratio", 1.0) or 1.0)
                word_highlighting = bool(getattr(settings, "word_highlighting", True)) and bool(
                    options.highlight
                )
                highlight_granularity = str(
                    getattr(settings, "highlight_granularity", "word") or "word"
                )
                video_backend = str(getattr(settings, "video_backend", "ffmpeg") or "ffmpeg")
                raw_video_backend_settings = getattr(settings, "video_backend_settings", {}) or {}
                video_backend_settings: Dict[str, Dict[str, object]] = {}
                if isinstance(raw_video_backend_settings, Mapping):
                    for key, value in raw_video_backend_settings.items():
                        if isinstance(key, str) and isinstance(value, Mapping):
                            video_backend_settings[key] = dict(value)

                base_name = _sanitize_filename_fragment(
                    f"{safe_title}_{input_lang}_{options.target_language}",
                    fallback=safe_title,
                )
                exporter = build_exporter(
                    base_dir=str(media_root),
                    base_name=base_name,
                    cover_img=None,
                    book_author="Subtitles",
                    book_title=display_title,
                    global_cumulative_word_counts=[],
                    total_book_words=0,
                    macos_reading_speed=float(macos_speed),
                    input_language=input_lang,
                    total_sentences=estimated_total_sentences,
                    tempo=tempo,
                    sync_ratio=sync_ratio,
                    word_highlighting=word_highlighting,
                    highlight_granularity=highlight_granularity,
                    selected_voice=selected_voice,
                    primary_target_language=options.target_language,
                    audio_bitrate_kbps=getattr(settings, "audio_bitrate_kbps", None),
                    slide_render_options=None,
                    template_name=None,
                    video_backend=video_backend,
                    video_backend_settings=video_backend_settings,
                )

                audio_queue = queue.Queue()

                def _audio_worker() -> None:
                    try:
                        while True:
                            if audio_shutdown.is_set():
                                break
                            item = audio_queue.get()
                            if item is None:
                                break
                            sentence_number, entry = item
                            if audio_shutdown.is_set():
                                break
                            if stop_event is not None and stop_event.is_set():
                                break

                            original_text = (entry.original_text or "").strip()
                            translation_text = (entry.translation_text or "").strip()
                            transliteration_text = (entry.transliteration_text or "").strip()
                            if translation_text and is_failure_annotation(translation_text):
                                translation_text = ""

                            lines = [
                                line
                                for line in (original_text, translation_text, transliteration_text)
                                if line
                            ]
                            block_body = "\n".join(lines)
                            block = f"Subtitle {sentence_number}\n{block_body}".strip()

                            audio_mode = "4"
                            if not translation_text and original_text:
                                audio_mode = "5"
                            elif translation_text and not original_text:
                                audio_mode = "1"
                            elif not translation_text and not original_text:
                                audio_mode = "1"

                            try:
                                synthesis = synthesizer.synthesize_sentence(
                                    sentence_number=sentence_number,
                                    input_sentence=original_text,
                                    fluent_translation=translation_text,
                                    input_language=input_lang,
                                    target_language=options.target_language,
                                    audio_mode=audio_mode,
                                    total_sentences=estimated_total_sentences,
                                    language_codes=LANGUAGE_CODES,
                                    selected_voice=selected_voice,
                                    voice_overrides=None,
                                    tempo=tempo,
                                    macos_reading_speed=macos_speed,
                                    tts_backend=tts_backend,
                                    tts_executable_path=tts_executable,
                                )
                                audio_segments: List[AudioSegment] = []
                                audio_track_segments: Dict[str, List[AudioSegment]] = {}
                                raw_tracks = getattr(synthesis, "audio_tracks", None)
                                has_track_payload = isinstance(raw_tracks, Mapping)
                                if has_track_payload:
                                    translation_track = raw_tracks.get("translation") or raw_tracks.get("trans")
                                    original_track = raw_tracks.get("orig") or raw_tracks.get("original")
                                    if isinstance(translation_track, AudioSegment):
                                        audio_segments = [translation_track]
                                        audio_track_segments["translation"] = [translation_track]
                                    if isinstance(original_track, AudioSegment):
                                        audio_track_segments["orig"] = [original_track]
                                if not audio_segments and not has_track_payload:
                                    audio_segments = [synthesis.audio]
                            except Exception:  # pragma: no cover - defensive fallback
                                logger.warning(
                                    "Unable to generate TTS audio for subtitle sentence %s",
                                    sentence_number,
                                    exc_info=True,
                                )
                                audio_segments = [AudioSegment.silent(duration=0)]
                                audio_track_segments = {}

                            if tracker_local is not None:
                                tracker_local.record_step_completion(
                                    stage="subtitle_audio",
                                    index=sentence_number,
                                )

                            request = BatchExportRequest(
                                start_sentence=sentence_number,
                                end_sentence=sentence_number,
                                written_blocks=[block],
                                target_language=options.target_language,
                                output_html=False,
                                output_pdf=False,
                                generate_audio=True,
                                audio_segments=audio_segments,
                                audio_tracks=audio_track_segments,
                                generate_video=False,
                                video_blocks=[block],
                            )
                            export_result = exporter.export(request)
                            if tracker_local is not None and export_result is not None:
                                tracker_local.record_generated_chunk(
                                    chunk_id=export_result.chunk_id,
                                    range_fragment=export_result.range_fragment,
                                    start_sentence=export_result.start_sentence,
                                    end_sentence=export_result.end_sentence,
                                    files=export_result.artifacts,
                                    sentences=export_result.sentences,
                                    audio_tracks=export_result.audio_tracks,
                                    timing_tracks=export_result.timing_tracks,
                                )
                    except BaseException as exc:  # pragma: no cover - surface failures
                        audio_errors.append(exc)
                        audio_error_event.set()

                audio_thread = threading.Thread(
                    target=_audio_worker,
                    name=f"subtitle-audio-{job.job_id}",
                )
                audio_thread.start()

                def _enqueue_transcript_batch(
                    batch: Sequence[Tuple[int, SubtitleHtmlEntry]],
                ) -> None:
                    if audio_error_event.is_set() and audio_errors:
                        raise audio_errors[0]
                    if audio_queue is None:
                        return
                    for sentence_number, entry in batch:
                        if stop_event is not None and stop_event.is_set():
                            raise SubtitleJobCancelled(
                                "Subtitle job interrupted by cancellation request"
                            )
                        if audio_error_event.is_set() and audio_errors:
                            raise audio_errors[0]
                        audio_queue.put((sentence_number, entry))

                on_transcript_batch = _enqueue_transcript_batch

            try:
                result = process_subtitle_file(
                    input_path,
                    output_path,
                    options,
                    mirror_output_path=mirror_path,
                    tracker=tracker_local,
                    stop_event=stop_event,
                    collect_transcript_entries=False,
                    on_transcript_batch=on_transcript_batch,
                )
            except SubtitleJobCancelled:
                if audio_queue is not None:
                    audio_shutdown.set()
                    audio_queue.put(None)
                    if audio_thread is not None:
                        audio_thread.join()
                job.status = PipelineJobStatus.CANCELLED
                job.error_message = None
                return
            except Exception as exc:
                if audio_queue is not None:
                    audio_shutdown.set()
                    audio_queue.put(None)
                    if audio_thread is not None:
                        audio_thread.join()
                job.status = PipelineJobStatus.FAILED
                job.error_message = str(exc)
                raise
            else:
                if audio_queue is not None:
                    audio_queue.put(None)
                    if audio_thread is not None:
                        audio_thread.join()
                if audio_errors:
                    exc = audio_errors[0]
                    job.status = PipelineJobStatus.FAILED
                    job.error_message = str(exc)
                    raise exc

            relative_path = output_path.relative_to(self._locator.job_root(job.job_id)).as_posix()
            export_path: Optional[Path] = None
            if mirror_path is not None:
                try:
                    if mirror_path.exists():
                        export_path = mirror_path
                except OSError:
                    logger.info(
                        "Unable to access mirrored subtitle output at %s; will attempt copy fallback.",
                        mirror_path,
                    )
            elif mirror_dir is not None:
                try:
                    export_candidate = mirror_dir / output_name
                    if export_candidate != output_path:
                        shutil.copy2(output_path, export_candidate)
                    self._copy_html_companion(output_path, mirror_dir)
                    export_path = export_candidate
                except Exception:  # pragma: no cover - best effort mirror
                    logger.warning(
                        "Unable to mirror subtitle output %s to %s",
                        output_path,
                        mirror_dir,
                        exc_info=True,
                    )
            subtitle_metadata = {
                **result.metadata,
                "download_url": self._locator.resolve_url(job.job_id, relative_path),
                "generate_audio_book": bool(options.generate_audio_book),
            }
            request_payload = job.request_payload if isinstance(job.request_payload, Mapping) else {}
            media_metadata = request_payload.get("media_metadata") if isinstance(request_payload, Mapping) else None
            if isinstance(media_metadata, Mapping) and media_metadata:
                subtitle_metadata["media_metadata"] = copy.deepcopy(dict(media_metadata))
                job_label = media_metadata.get("job_label")
                if isinstance(job_label, str) and job_label.strip():
                    subtitle_metadata["job_label"] = job_label.strip()
            if export_path is not None:
                subtitle_metadata["export_path"] = export_path.as_posix()

            book_metadata: Dict[str, object] = {
                "book_title": display_title,
                "book_author": "Subtitles",
                "book_genre": "Subtitles",
                "book_language": options.target_language,
                "source_file": (input_path.relative_to(self._locator.job_root(job.job_id))).as_posix(),
                "source_path": (input_path.relative_to(self._locator.job_root(job.job_id))).as_posix(),
            }
            if isinstance(media_metadata, Mapping) and str(media_metadata.get("kind", "")).strip().lower() == "tv_episode":
                show = media_metadata.get("show")
                episode = media_metadata.get("episode")
                show_name = show.get("name") if isinstance(show, Mapping) else None
                episode_name = episode.get("name") if isinstance(episode, Mapping) else None
                season_number = episode.get("season") if isinstance(episode, Mapping) else None
                episode_number = episode.get("number") if isinstance(episode, Mapping) else None
                airdate = episode.get("airdate") if isinstance(episode, Mapping) else None
                genres = show.get("genres") if isinstance(show, Mapping) else None

                if isinstance(show_name, str) and show_name.strip():
                    book_metadata["book_author"] = show_name.strip()
                    book_metadata["series_title"] = show_name.strip()
                if isinstance(season_number, int) and isinstance(episode_number, int) and season_number > 0 and episode_number > 0:
                    book_metadata["season_number"] = season_number
                    book_metadata["episode_number"] = episode_number
                    book_metadata["episode_code"] = _format_episode_code(season_number, episode_number)
                if isinstance(episode_name, str) and episode_name.strip():
                    book_metadata["episode_title"] = episode_name.strip()
                if isinstance(airdate, str) and airdate.strip():
                    book_metadata["airdate"] = airdate.strip()
                if isinstance(genres, list) and genres:
                    filtered = [entry.strip() for entry in genres if isinstance(entry, str) and entry.strip()]
                    if filtered:
                        book_metadata["book_genre"] = "TV"
                        book_metadata["series_genres"] = filtered
                provider = media_metadata.get("provider")
                if isinstance(provider, str) and provider.strip():
                    book_metadata["tv_metadata_provider"] = provider.strip()
                tvmaze = media_metadata.get("tvmaze")
                if isinstance(tvmaze, Mapping):
                    show_id = tvmaze.get("show_id")
                    episode_id = tvmaze.get("episode_id")
                    if isinstance(show_id, int):
                        book_metadata["tvmaze_show_id"] = show_id
                    if isinstance(episode_id, int):
                        book_metadata["tvmaze_episode_id"] = episode_id
                job_label = media_metadata.get("job_label")
                if isinstance(job_label, str) and job_label.strip():
                    book_metadata["job_label"] = job_label.strip()
                    code = book_metadata.get("episode_code")
                    if isinstance(code, str) and code.strip() and isinstance(episode_name, str) and episode_name.strip():
                        book_metadata["book_title"] = f"{code.strip()} - {episode_name.strip()}"
                    elif isinstance(code, str) and code.strip():
                        book_metadata["book_title"] = code.strip()

            result_payload: Dict[str, object] = {
                "subtitle": {
                    "output_path": output_path.as_posix(),
                    "relative_path": relative_path,
                    "metadata": subtitle_metadata,
                    "cues": result.cue_count,
                    "translated": result.translated_count,
                },
                "book_metadata": book_metadata,
            }
            job.result_payload = result_payload

            if tracker_local is not None and not options.generate_audio_book:
                tracker_local.record_generated_chunk(
                    chunk_id="subtitle",
                    range_fragment="subtitle",
                    start_sentence=1,
                    end_sentence=max(int(result.translated_count), 1),
                    files={
                            "subtitle": relative_path,
                        },
                    )

            if tracker_local is not None:
                job.generated_files = tracker_local.get_generated_files()

            job.status = PipelineJobStatus.COMPLETED
            job.error_message = None

        return self._job_manager.submit_background_job(
            job_type="subtitle",
            worker=_worker,
            request_payload={
                "source_path": str(resolved_source),
                "original_name": source_name,
                "options": options.to_dict(),
                "media_metadata": copy.deepcopy(submission.media_metadata)
                if submission.media_metadata
                else None,
            },
            user_id=user_id,
            user_role=user_role,
            setup=_setup,
        )

    def delete_source(self, subtitle_path: Path, *, base_dir: Optional[Path] = None):
        """Delete a subtitle source plus any mirrored HTML companions."""

        try:
            resolved_path = subtitle_path.expanduser().resolve()
        except Exception as exc:
            raise FileNotFoundError(f"Subtitle path '{subtitle_path}' is invalid") from exc

        if not resolved_path.exists():
            raise FileNotFoundError(f"Subtitle file '{resolved_path}' does not exist")

        target_base = base_dir.expanduser() if base_dir is not None else self._default_source_dir
        resolved_base = self._probe_directory(target_base, require_write=True)
        if resolved_base is None:
            raise FileNotFoundError(f"Subtitle directory '{target_base}' is not accessible")
        try:
            resolved_path.relative_to(resolved_base)
        except ValueError as exc:
            raise PermissionError(
                f"Subtitle '{resolved_path}' is outside allowed directory '{resolved_base}'"
            ) from exc

        return delete_nas_subtitle(resolved_path)

    def list_sources(self, directory: Optional[Path] = None) -> List[Path]:
        """Return discovered subtitle files under ``directory``."""

        base_candidate = directory or self._default_source_dir
        resolved = self._probe_directory(base_candidate, require_write=False)
        if resolved is None:
            if directory is not None:
                raise FileNotFoundError(f"Subtitle directory '{base_candidate}' is not accessible")
            return []
        entries: List[Path] = []
        for candidate in resolved.iterdir():
            if candidate.is_file() and candidate.suffix.lower() in DISCOVERABLE_EXTENSIONS:
                entries.append(candidate.resolve())
        entries.sort()
        return entries

    def default_source_directory(self) -> Path:
        """Return the configured directory for local subtitle discovery."""

        return self._default_source_dir
