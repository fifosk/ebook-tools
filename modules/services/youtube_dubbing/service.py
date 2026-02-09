from __future__ import annotations

import shutil
import threading
from pathlib import Path
from typing import Any, List, Mapping, Optional, Sequence

from modules.progress_tracker import ProgressTracker
from modules.services.file_locator import FileLocator
from modules.services.job_manager import PipelineJob, PipelineJobManager, PipelineJobStatus
from modules.services.job_manager.runtime_context import job_runtime_context
from modules.transliteration import (
    TransliterationService,
    get_transliterator,
    resolve_local_transliteration_module,
)

from .audio_utils import _clamp_original_mix
from .common import (
    _DEFAULT_FLUSH_SENTENCES,
    _DEFAULT_TRANSLATION_BATCH_SIZE,
    _TARGET_DUB_HEIGHT,
    _DubJobCancelled,
    logger,
)
from .dialogues import _clip_dialogues_to_window, _parse_dialogues, _validate_time_window
from .generation import generate_dubbed_video
from .stitching import stitch_dub_batches
from .language import _find_language_token, _language_uses_non_latin, _resolve_language_code
from .video_utils import _classify_video_source
from .webvtt import _ensure_webvtt_for_video, _ensure_webvtt_variant


_GOOGLE_TRANSLATION_PROVIDER_ALIASES = {
    "google",
    "googletrans",
    "googletranslate",
    "google-translate",
    "gtranslate",
    "gtrans",
}
_PYTHON_TRANSLITERATION_ALIASES = {
    "python",
    "python-module",
    "module",
    "local-module",
}


def _normalize_translation_provider(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized in _GOOGLE_TRANSLATION_PROVIDER_ALIASES:
        return "googletrans"
    if normalized in {"llm", "ollama", "default"}:
        return "llm"
    return normalized or None


def _normalize_transliteration_mode(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower().replace("_", "-")
    if normalized in _PYTHON_TRANSLITERATION_ALIASES:
        return "python"
    if normalized.startswith("local-gemma3") or normalized == "gemma3-12b":
        return "default"
    if normalized in {"llm", "ollama", "default"}:
        return "default"
    return normalized or None


def _resolve_partial_video(path: Path) -> Path:
    """Recover or reject partial downloads that still end with .part."""

    resolved = path.expanduser()
    if resolved.suffix.lower() != ".part":
        return resolved
    candidate = resolved.with_suffix("")
    if candidate.exists():
        logger.info("Using completed download for %s (recovered from .part)", candidate)
        return candidate
    try:
        resolved.rename(candidate)
        logger.info("Recovered partial video download as %s", candidate)
        return candidate
    except OSError as exc:
        raise FileNotFoundError(
            f"Video file '{resolved}' appears to be an incomplete download (.part); finish the download first."
        ) from exc


def _serialize_generated_files(output_path: Path, *, relative_prefix: Optional[Path] = None) -> dict:
    return _serialize_generated_files_batch([output_path], relative_prefix=relative_prefix)


def _serialize_generated_files_batch(
    paths: Sequence[Path],
    *,
    relative_prefix: Optional[Path] = None,
    subtitle_paths: Optional[Sequence[Path]] = None,
    subtitle_relative_prefix: Optional[Path] = None,
) -> dict:
    files = []
    for path in paths:
        files.append(
            {
                "type": "video",
                "path": path.as_posix(),
                "name": path.name,
                **(
                    {"relative_path": (relative_prefix / path.name).as_posix()}
                    if relative_prefix is not None
                    else {}
                ),
            }
        )
    subtitle_prefix = subtitle_relative_prefix if subtitle_relative_prefix is not None else relative_prefix
    if subtitle_paths:
        for subtitle_path in subtitle_paths:
            files.append(
                {
                    "type": "text",
                    "path": subtitle_path.as_posix(),
                    "name": subtitle_path.name,
                    **(
                        {"relative_path": (subtitle_prefix / subtitle_path.name).as_posix()}
                        if subtitle_prefix is not None
                        else {}
                    ),
                }
            )
    return {
        "complete": True,
        "chunks": [
            {
                "chunk_id": "youtube_dub",
                "range_fragment": "dub",
                "files": files,
            }
        ],
    }


def _build_job_result(
    *,
    output_path: Path,
    written_paths: List[Path],
    video_path: Path,
    subtitle_path: Path,
    source_subtitle_path: Optional[Path],
    source_kind: str,
    source_language: Optional[str],
    language: str,
    voice: str,
    tempo: float,
    macos_reading_speed: int,
    dialogues: int,
    dubbed_duration_seconds: float,
    start_offset: float,
    end_offset: Optional[float],
    original_mix_percent: float,
    flush_sentences: int,
    llm_model: Optional[str],
    translation_provider: Optional[str],
    translation_batch_size: int,
    transliteration_mode: Optional[str],
    transliteration_model: Optional[str],
    transliteration_module: Optional[str],
    target_height: int,
    preserve_aspect_ratio: bool,
) -> dict:
    return {
        "youtube_dub": {
            "output_path": output_path.as_posix(),
            "video_path": video_path.as_posix(),
            "subtitle_path": subtitle_path.as_posix(),
            "source_subtitle_path": source_subtitle_path.as_posix() if source_subtitle_path else subtitle_path.as_posix(),
            "source_kind": source_kind,
            "source_language": source_language,
            "language": language,
            "voice": voice,
            "tempo": tempo,
            "reading_speed": macos_reading_speed,
            "dialogues": dialogues,
            "dubbed_duration_seconds": round(dubbed_duration_seconds, 3),
            "start_time_offset_seconds": start_offset,
            "end_time_offset_seconds": end_offset,
            "original_mix_percent": original_mix_percent,
            "flush_sentences": flush_sentences,
            "llm_model": llm_model,
            "translation_provider": translation_provider,
            "translation_batch_size": translation_batch_size,
            "transliteration_mode": transliteration_mode,
            "transliteration_model": transliteration_model,
            "transliteration_module": transliteration_module,
            "written_paths": [path.as_posix() for path in written_paths],
            "split_batches": len(written_paths) > 1,
            "target_height": target_height,
            "preserve_aspect_ratio": preserve_aspect_ratio,
        }
    }


def _extract_translation_sentences_from_vtt(subtitle_artifacts: List[Path]) -> List[str]:
    """Extract translation-track text from output VTT files for lookup cache.

    The dub pipeline writes VTT files with ``<c.translation>`` cues containing
    the translated text.  We parse those cues to get the sentences that users
    will actually see (and tap on) in the video player.

    Only dubbed output VTTs (containing ``.dub.`` in the filename) are parsed.
    Source-language VTTs are skipped — their ``<c.translation>`` tags contain
    reversed original text, not real translations.  Among dub VTTs, the
    ``*.full.vtt`` stitched file is preferred to avoid duplicates from
    per-batch files.
    """
    import re as _re

    _VTT_TRANSLATION_RE = _re.compile(r"<c\.translation>(.*?)</c>", _re.DOTALL)
    _TAG_STRIP_RE = _re.compile(r"<[^>]+>")

    sentences: List[str] = []
    seen: set[str] = set()

    # Prefer the stitched "full" VTT; fall back to per-batch VTTs if absent
    dub_vtts = [a for a in subtitle_artifacts if a.suffix.lower() == ".vtt" and ".dub." in a.name]
    full_vtts = [v for v in dub_vtts if ".full." in v.name]
    candidates = full_vtts or dub_vtts

    for artifact in candidates:
        try:
            content = artifact.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in _VTT_TRANSLATION_RE.finditer(content):
            text = _TAG_STRIP_RE.sub("", m.group(1)).strip()
            if text and text not in seen:
                seen.add(text)
                sentences.append(text)

    return sentences


def _run_dub_job(
    job: PipelineJob,
    *,
    video_path: Path,
    subtitle_path: Path,
    language_code: str,
    voice: str,
    tempo: float,
    macos_reading_speed: int,
    output_dir: Optional[Path],
    max_workers: Optional[int] = None,
    start_time_offset: Optional[float] = None,
    end_time_offset: Optional[float] = None,
    original_mix_percent: Optional[float] = None,
    flush_sentences: Optional[int] = None,
    llm_model: Optional[str] = None,
    translation_provider: Optional[str] = None,
    translation_batch_size: Optional[int] = None,
    transliteration_mode: Optional[str] = None,
    transliteration_model: Optional[str] = None,
    split_batches: bool = False,
    stitch_batches: bool = True,
    include_transliteration: Optional[bool] = None,
    target_height: int = _TARGET_DUB_HEIGHT,
    preserve_aspect_ratio: bool = True,
    file_locator: Optional[FileLocator] = None,
    source_subtitle_path: Optional[Path] = None,
    source_kind: str = "youtube",
    source_language: Optional[str] = None,
    enable_lookup_cache: bool = True,
) -> None:
    video_path = _resolve_partial_video(video_path)
    tracker = job.tracker or ProgressTracker()
    stop_event = job.stop_event or threading.Event()
    source_subtitle = source_subtitle_path or subtitle_path
    target_height_resolved = int(target_height)
    tracker.publish_progress(
        {
            "stage": "validation",
            "video": video_path.as_posix(),
            "subtitle": subtitle_path.as_posix(),
            "language": language_code,
            "start_offset": start_time_offset or 0.0,
            "end_offset": end_time_offset,
            "split_batches": split_batches,
            "stitch_batches": stitch_batches,
        }
    )
    try:
        media_root: Optional[Path] = None
        relative_prefix: Optional[Path] = None
        subtitle_storage_path: Path = subtitle_path
        subtitle_artifacts: List[Path] = []
        stitched_generated_files_snapshot: Optional[dict] = None
        resolved_translation_provider = (
            _normalize_translation_provider(translation_provider) or "llm"
        )
        resolved_translation_batch_size = (
            max(1, int(translation_batch_size))
            if translation_batch_size is not None
            else _DEFAULT_TRANSLATION_BATCH_SIZE
        )
        resolved_transliteration_mode = (
            _normalize_transliteration_mode(transliteration_mode) or "default"
        )
        resolved_transliteration_model = (transliteration_model or "").strip() or None
        if resolved_transliteration_mode == "default":
            if not resolved_transliteration_model:
                resolved_transliteration_model = llm_model
        else:
            resolved_transliteration_model = None
        requested_transliteration = (
            _language_uses_non_latin(language_code)
            if include_transliteration is None
            else bool(include_transliteration)
        )
        include_transliteration_resolved = bool(
            requested_transliteration and _language_uses_non_latin(language_code)
        )
        if requested_transliteration and not include_transliteration_resolved:
            logger.info(
                "Transliteration disabled for Latin-script language %s",
                language_code,
                extra={"event": "youtube.dub.transliteration.disabled", "language": language_code},
            )
        # Preserve the original name for nested closures that may still reference it.
        include_transliteration = include_transliteration_resolved
        transliterator: Optional[TransliterationService] = None
        if include_transliteration_resolved:
            try:
                transliterator = get_transliterator()
            except Exception:
                transliterator = None
                include_transliteration_resolved = False

        def _ensure_media_root() -> Optional[Path]:
            nonlocal media_root
            if file_locator is None:
                return None
            if media_root is None:
                media_root = file_locator.media_root(job.job_id)
                media_root.mkdir(parents=True, exist_ok=True)
            return media_root

        def _copy_into_storage(path: Path) -> Path:
            root = _ensure_media_root()
            if root is None:
                return path
            target = root / path.name
            try:
                if path.resolve() == target.resolve():
                    return target
            except Exception:
                pass
            try:
                shutil.copy2(path, target)
                return target
            except Exception:
                logger.warning(
                    "Unable to copy dubbed artifact %s into storage for job %s",
                    path,
                    job.job_id,
                    exc_info=True,
                )
                return path

        try:
            subtitle_storage_path = _copy_into_storage(subtitle_storage_path)
            subtitle_artifacts.append(subtitle_storage_path)
            if media_root and subtitle_storage_path.is_relative_to(media_root):
                relative_prefix = Path("media")
            vtt_variant = _ensure_webvtt_variant(
                subtitle_storage_path,
                media_root,
                target_language=language_code,
                # Skip transliteration when copying the source subtitles into storage;
                # the translated/batch subtitles later in the pipeline will carry the
                # transliteration track to avoid front-loading a long LLM pass here.
                include_transliteration=False,
                transliterator=None,
                transliteration_mode=resolved_transliteration_mode,
                transliteration_model=resolved_transliteration_model,
            )
            if vtt_variant:
                subtitle_artifacts.append(vtt_variant)
        except Exception:
            logger.debug("Unable to prepare subtitle copy for storage", exc_info=True)

        storage_written_paths: List[Path] = []

        def _serialize_files() -> dict:
            return _serialize_generated_files_batch(
                storage_written_paths,
                relative_prefix=relative_prefix,
                subtitle_paths=subtitle_artifacts,
                subtitle_relative_prefix=relative_prefix,
            )

        def _register_written_path(path: Path) -> None:
            nonlocal relative_prefix
            batch_subtitles: list[Path] = []

            def _relative_str(candidate: Path) -> str:
                try:
                    if media_root and candidate.is_relative_to(media_root):
                        return (Path("media") / candidate.relative_to(media_root)).as_posix()
                except Exception:
                    pass
                return candidate.as_posix()

            def _subtitles_map(paths: Sequence[Path]) -> dict[str, str]:
                mapping: dict[str, str] = {}
                for candidate in paths:
                    suffix = candidate.suffix.lower().lstrip(".") or "text"
                    if suffix in mapping:
                        continue
                    if suffix not in {"vtt", "ass", "srt", "text"}:
                        suffix = "text"
                    mapping[suffix] = _relative_str(candidate)
                return mapping

            stored = _copy_into_storage(path)
            root = media_root
            if root and stored.is_relative_to(root):
                relative_prefix = Path("media")
            if stored not in storage_written_paths:
                storage_written_paths.append(stored)
            subtitle_bases = {stored, path}
            for base in subtitle_bases:
                subtitle_candidate = base.with_suffix(".ass")
                alt_subtitle = base.with_suffix(".srt")
                vtt_subtitle = base.with_suffix(".vtt")
                candidates = (vtt_subtitle, subtitle_candidate, alt_subtitle)
                for candidate in candidates:
                    try:
                        if candidate.exists():
                            copied_subtitle = _copy_into_storage(candidate)
                            if copied_subtitle not in subtitle_artifacts:
                                subtitle_artifacts.append(copied_subtitle)
                            if copied_subtitle not in batch_subtitles:
                                batch_subtitles.append(copied_subtitle)
                            # Avoid re-rendering VTT files when they already exist; keep the
                            # authored transliteration/RTL ordering and skip LLM work here.
                            if copied_subtitle.suffix.lower() == ".vtt":
                                continue
                            # If we already have an explicit VTT sibling for this video/subtitle pair,
                            # do not regenerate/realign another VTT from ASS/SRT.
                            if vtt_subtitle.exists():
                                continue
                            vtt_variant = _ensure_webvtt_variant(
                                copied_subtitle,
                                media_root,
                                target_language=language_code,
                                include_transliteration=include_transliteration_resolved,
                                transliterator=transliterator if include_transliteration_resolved else None,
                                transliteration_mode=resolved_transliteration_mode,
                                transliteration_model=resolved_transliteration_model,
                            )
                            if vtt_variant:
                                if vtt_variant not in subtitle_artifacts:
                                    subtitle_artifacts.append(vtt_variant)
                                if vtt_variant not in batch_subtitles:
                                    batch_subtitles.append(vtt_variant)
                            aligned_variant = _ensure_webvtt_for_video(
                                copied_subtitle,
                                stored,
                                media_root,
                                target_language=language_code,
                                include_transliteration=include_transliteration_resolved,
                                transliterator=transliterator if include_transliteration_resolved else None,
                                transliteration_mode=resolved_transliteration_mode,
                                transliteration_model=resolved_transliteration_model,
                            )
                            if aligned_variant:
                                if aligned_variant not in subtitle_artifacts:
                                    subtitle_artifacts.append(aligned_variant)
                                if aligned_variant not in batch_subtitles:
                                    batch_subtitles.append(aligned_variant)
                    except Exception:
                        logger.debug("Unable to register subtitle artifact %s", candidate, exc_info=True)
            job.generated_files = _serialize_files()
            try:
                subtitle_map = _subtitles_map(batch_subtitles or subtitle_artifacts)
                chunk_files: dict[str, str] = {"video": _relative_str(stored)}
                chunk_files.update(subtitle_map)
                chunk_identifier = stored.stem or "youtube_dub"
                tracker.record_generated_chunk(
                    chunk_id=chunk_identifier,
                    start_sentence=0,
                    end_sentence=0,
                    range_fragment=stored.stem,
                    files=chunk_files,
                )
                job.generated_files = tracker.get_generated_files()
            except Exception:
                logger.debug("Unable to publish generated chunk for %s", stored, exc_info=True)
            try:
                tracker.publish_progress(
                    {"stage": "media.update", "generated_files": job.generated_files, "output_path": stored.as_posix()}
                )
            except Exception:
                logger.debug("Unable to publish generated media update for %s", stored, exc_info=True)

        # Persist subtitle reference immediately so active jobs can expose tracks even before videos finish.
        job.generated_files = _serialize_files()
        try:
            subtitle_map = {
                (
                    sub.suffix.lower().lstrip(".") if sub.suffix.lower().lstrip(".") in {"vtt", "ass", "srt"} else "text"
                ): (
                    (Path("media") / sub.relative_to(media_root)).as_posix()
                    if media_root and sub.is_relative_to(media_root)
                    else sub.as_posix()
                )
                for sub in subtitle_artifacts
            }
            chunk_identifier = f"{subtitle_storage_path.stem or 'youtube_dub'}_init"
            tracker.record_generated_chunk(
                chunk_id=chunk_identifier,
                start_sentence=0,
                end_sentence=0,
                range_fragment="dub",
                files=subtitle_map,
            )
            job.generated_files = tracker.get_generated_files()
        except Exception:
            logger.debug("Unable to publish initial generated subtitles snapshot", exc_info=True)
        try:
            tracker.publish_progress({"stage": "media.init", "generated_files": job.generated_files})
        except Exception:
            logger.debug("Unable to publish initial generated media snapshot", exc_info=True)

        final_output, written_paths, dubbed_duration_seconds = generate_dubbed_video(
            video_path,
            subtitle_path,
            target_language=language_code,
            voice=voice,
            tempo=tempo,
            macos_reading_speed=macos_reading_speed,
            output_dir=output_dir,
            tracker=tracker,
            stop_event=stop_event,
            max_workers=max_workers,
            start_time_offset=start_time_offset,
            end_time_offset=end_time_offset,
            original_mix_percent=original_mix_percent,
            flush_sentences=flush_sentences,
            llm_model=llm_model,
            translation_provider=resolved_translation_provider,
            translation_batch_size=resolved_translation_batch_size,
            transliteration_mode=resolved_transliteration_mode,
            transliteration_model=resolved_transliteration_model,
            split_batches=split_batches,
            include_transliteration=include_transliteration_resolved,
            on_batch_written=_register_written_path,
            target_height=target_height,
            preserve_aspect_ratio=preserve_aspect_ratio,
        )
        try:
            for candidate in written_paths:
                expected = (media_root / candidate.name) if media_root is not None else candidate
                if expected not in storage_written_paths:
                    _register_written_path(candidate)
        except Exception:
            logger.debug("Unable to register final written paths for %s", job.job_id, exc_info=True)

        stitched_video_path: Optional[Path] = None
        if bool(split_batches) and bool(stitch_batches) and media_root is not None:
            try:
                batch_candidates = [path for path in storage_written_paths if path.suffix.lower() == ".mp4"]
                batch_candidates.sort(key=lambda p: p.name)
                if len(batch_candidates) >= 2:
                    try:
                        tracker.publish_progress(
                            {
                                "stage": "stitching.start",
                                "batch_count": len(batch_candidates),
                            }
                        )
                    except Exception:
                        logger.debug("Unable to publish stitching start progress for %s", job.job_id, exc_info=True)
                    from re import sub as _re_sub

                    base_name = _re_sub(r"^\\d{2}-\\d{2}-\\d{2}-", "", batch_candidates[0].name)
                    base_output = media_root / base_name
                    stitched = stitch_dub_batches(
                        batch_candidates,
                        base_output=base_output,
                        language_code=language_code,
                        include_transliteration=include_transliteration_resolved,
                        transliterator=transliterator if include_transliteration_resolved else None,
                        transliteration_mode=resolved_transliteration_mode,
                        transliteration_model=resolved_transliteration_model,
                        target_height=target_height_resolved,
                        preserve_aspect_ratio=preserve_aspect_ratio,
                    )
                    if stitched is not None:
                        stitched_video, stitched_vtt, stitched_ass = stitched
                        stitched_video_path = stitched_video
                        try:
                            tracker.publish_progress(
                                {
                                    "stage": "stitching.done",
                                    "output_path": stitched_video_path.as_posix(),
                                }
                            )
                        except Exception:
                            logger.debug("Unable to publish stitching done progress for %s", job.job_id, exc_info=True)
                        # Ensure the stitched artifacts are registered for storage and listing.
                        _register_written_path(stitched_video)
                        if stitched_vtt.exists():
                            _copy_into_storage(stitched_vtt)
                        if stitched_ass.exists():
                            _copy_into_storage(stitched_ass)
            except Exception:
                logger.warning("Unable to stitch YouTube dub batches for job %s", job.job_id, exc_info=True)

        if stitched_video_path is not None and media_root is not None:
            try:
                subtitle_only: List[Path] = []
                for candidate in (
                    stitched_video_path.with_suffix(".vtt"),
                    stitched_video_path.with_suffix(".ass"),
                ):
                    if candidate.exists():
                        subtitle_only.append(candidate)
                relative_prefix = Path("media")
                stitched_generated_files_snapshot = _serialize_generated_files_batch(
                    [stitched_video_path],
                    relative_prefix=relative_prefix,
                    subtitle_paths=subtitle_only,
                    subtitle_relative_prefix=relative_prefix,
                )
                job.generated_files = stitched_generated_files_snapshot
                final_output = stitched_video_path
                try:
                    tracker.publish_progress(
                        {
                            "stage": "media.reset",
                            "media_reset": True,
                            "generated_files": stitched_generated_files_snapshot,
                            "output_path": stitched_video_path.as_posix(),
                        }
                    )
                except Exception:
                    logger.debug("Unable to publish stitched media reset for %s", job.job_id, exc_info=True)

                # Mirror stitched outputs back next to the NAS batch files for convenient playback outside the app.
                # Prefer an explicit output_dir when provided; otherwise use the parent directory of the generated batches.
                try:
                    mirror_dir: Optional[Path] = output_dir
                    if mirror_dir is None:
                        for candidate in written_paths:
                            if candidate.suffix.lower() == ".mp4":
                                mirror_dir = candidate.parent
                                break
                    if mirror_dir is not None:
                        try:
                            tracker.publish_progress(
                                {
                                    "stage": "nas.mirror.start",
                                    "destination": mirror_dir.as_posix(),
                                }
                            )
                        except Exception:
                            logger.debug("Unable to publish NAS mirror start progress for %s", job.job_id, exc_info=True)
                        mirror_dir.mkdir(parents=True, exist_ok=True)
                        for artifact in (
                            stitched_video_path,
                            stitched_video_path.with_suffix(".ass"),
                        ):
                            if not artifact.exists():
                                continue
                            destination = mirror_dir / artifact.name
                            try:
                                if artifact.resolve() == destination.resolve():
                                    continue
                            except Exception:
                                pass
                            shutil.copy2(artifact, destination)
                        try:
                            tracker.publish_progress(
                                {
                                    "stage": "nas.mirror.done",
                                    "destination": mirror_dir.as_posix(),
                                }
                            )
                        except Exception:
                            logger.debug("Unable to publish NAS mirror done progress for %s", job.job_id, exc_info=True)
                except Exception:
                    logger.warning(
                        "Unable to mirror stitched YouTube dub outputs into NAS folder for job %s",
                        job.job_id,
                        exc_info=True,
                    )
            except Exception:
                logger.debug("Unable to replace generated files with stitched output for %s", job.job_id, exc_info=True)
    except _DubJobCancelled:
        job.status = PipelineJobStatus.CANCELLED
        job.error_message = None
        return
    if stop_event.is_set():
        job.status = PipelineJobStatus.CANCELLED
        job.error_message = None
        return
    job.status = PipelineJobStatus.COMPLETED
    job.error_message = None
    if not storage_written_paths:
        for path in written_paths:
            _register_written_path(path)
    try:
        if stitched_generated_files_snapshot is not None:
            job.generated_files = stitched_generated_files_snapshot
        else:
            job.generated_files = tracker.get_generated_files()
    except Exception:
        logger.debug("Unable to snapshot generated files after completion", exc_info=True)
    job.media_completed = True
    dialogues = _clip_dialogues_to_window(
        _parse_dialogues(subtitle_path),
        start_offset=start_time_offset or 0.0,
        end_offset=end_time_offset,
    )
    job.result_payload = _build_job_result(
        output_path=(storage_written_paths[-1] if storage_written_paths else final_output),
        written_paths=written_paths,
        video_path=video_path,
        subtitle_path=subtitle_storage_path,
        source_subtitle_path=source_subtitle,
        source_kind=source_kind,
        source_language=(source_language or "").strip() or None,
        language=language_code,
        voice=voice,
        tempo=tempo,
        macos_reading_speed=macos_reading_speed,
        dialogues=len([entry for entry in dialogues if entry.translation]),
        dubbed_duration_seconds=dubbed_duration_seconds,
        start_offset=start_time_offset or 0.0,
        end_offset=end_time_offset,
        original_mix_percent=_clamp_original_mix(original_mix_percent),
        flush_sentences=flush_sentences if flush_sentences is not None else _DEFAULT_FLUSH_SENTENCES,
        llm_model=llm_model,
        translation_provider=resolved_translation_provider,
        translation_batch_size=resolved_translation_batch_size,
        transliteration_mode=resolved_transliteration_mode,
        transliteration_model=resolved_transliteration_model,
        transliteration_module=resolve_local_transliteration_module(language_code)
        if resolved_transliteration_mode == "python"
        else None,
        target_height=target_height_resolved,
        preserve_aspect_ratio=preserve_aspect_ratio,
    )
    try:
        if stitched_generated_files_snapshot is not None:
            job.generated_files = stitched_generated_files_snapshot
        else:
            job.generated_files = tracker.get_generated_files()
    except Exception:
        logger.debug("Unable to snapshot generated files from tracker on completion; falling back to serialized batch", exc_info=True)
        job.generated_files = _serialize_generated_files_batch(
            storage_written_paths,
            relative_prefix=relative_prefix,
            subtitle_paths=subtitle_artifacts,
            subtitle_relative_prefix=relative_prefix,
        )
    tracker.publish_progress({"stage": "complete", "output_path": final_output.as_posix()})

    # Build lookup cache in background (non-blocking, non-fatal)
    # Extract translation sentences from the output VTT files (not the source subtitle).
    # The source subtitle has the original language text; the output VTT has <c.translation> cues
    # with the actual translated text that users will tap on in the video player.
    if enable_lookup_cache and file_locator is not None and subtitle_artifacts:
        cache_sentences = _extract_translation_sentences_from_vtt(subtitle_artifacts)
        if cache_sentences:

            def _build_video_lookup_cache() -> None:
                try:
                    from modules.lookup_cache import LookupCacheManager
                    from modules.llm_client_manager import client_scope

                    tracker.publish_progress({
                        "stage": "lookup_cache",
                        "message": "Building word lookup cache in background...",
                        "lookup_cache_status": "building",
                    })
                    job_dir = file_locator.job_root(job.job_id)
                    cache_manager = LookupCacheManager(
                        job_id=job.job_id,
                        job_dir=job_dir,
                        input_language=language_code,
                        definition_language="English",
                    )
                    with client_scope(None) as llm_client:
                        cache_manager.build_from_sentences(
                            sentences=cache_sentences,
                            llm_client=llm_client,
                            batch_size=10,
                            skip_stopwords=False,
                            progress_tracker=tracker,
                        )
                    cache_manager.save()
                    tracker.publish_progress({
                        "stage": "lookup_cache",
                        "message": f"Word lookup cache complete: {cache_manager.cache.stats.total_words} words.",
                        "lookup_cache_status": "complete",
                    })
                    logger.info(
                        "Lookup cache built for dub job %s: %d words",
                        job.job_id,
                        cache_manager.cache.stats.total_words,
                    )
                except Exception as exc:
                    logger.warning("Lookup cache build failed for dub job %s: %s", job.job_id, exc)
                    try:
                        tracker.publish_progress({
                            "stage": "lookup_cache",
                            "message": f"Lookup cache failed: {exc}",
                            "lookup_cache_status": "error",
                        })
                    except Exception:
                        pass

            threading.Thread(
                target=_build_video_lookup_cache,
                name=f"lookup-cache-{job.job_id}",
                daemon=True,
            ).start()


class YoutubeDubbingService:
    """Coordinate YouTube dubbing jobs with progress tracking."""

    def __init__(
        self,
        job_manager: PipelineJobManager,
        *,
        max_workers: Optional[int] = None,
    ) -> None:
        self._job_manager = job_manager
        self._max_workers = max_workers

    def enqueue(
        self,
        video_path: Path,
        subtitle_path: Path,
        *,
        source_language: Optional[str] = None,
        target_language: Optional[str],
        voice: str,
        tempo: float,
        macos_reading_speed: int,
        output_dir: Optional[Path],
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        media_metadata: Optional[Mapping[str, Any]] = None,
        start_time_offset: Optional[float] = None,
        end_time_offset: Optional[float] = None,
        original_mix_percent: Optional[float] = None,
        flush_sentences: Optional[int] = None,
        llm_model: Optional[str] = None,
        translation_provider: Optional[str] = None,
        translation_batch_size: Optional[int] = None,
        transliteration_mode: Optional[str] = None,
        transliteration_model: Optional[str] = None,
        split_batches: Optional[bool] = None,
        stitch_batches: Optional[bool] = None,
        include_transliteration: Optional[bool] = None,
        target_height: Optional[int] = None,
        preserve_aspect_ratio: Optional[bool] = None,
        enable_lookup_cache: Optional[bool] = None,
    ) -> PipelineJob:
        resolved_video = _resolve_partial_video(video_path)
        resolved_subtitle = subtitle_path.expanduser()
        if not resolved_video.exists():
            raise FileNotFoundError(f"Video file '{resolved_video}' does not exist")
        if not resolved_subtitle.exists():
            raise FileNotFoundError(f"Subtitle file '{resolved_subtitle}' does not exist")
        if resolved_video.parent != resolved_subtitle.parent:
            raise ValueError("subtitle_path must be in the same directory as the video file")
        if resolved_subtitle.suffix.lower() not in {".ass", ".srt", ".vtt", ".sub"}:
            raise ValueError("subtitle_path must reference an ASS, SRT, SUB, or VTT subtitle file.")

        start_offset, end_offset = _validate_time_window(start_time_offset, end_time_offset)
        resolved_target_height = int(target_height) if target_height is not None else _TARGET_DUB_HEIGHT
        if resolved_target_height < 0:
            resolved_target_height = 0
        allowed_heights = {320, 480, 720}
        if resolved_target_height not in allowed_heights:
            raise ValueError("target_height must be one of 320, 480, or 720")
        preserve_aspect_ratio_resolved = True if preserve_aspect_ratio is None else bool(preserve_aspect_ratio)

        tracker = ProgressTracker()
        stop_event = threading.Event()
        source_kind = _classify_video_source(resolved_video)
        source_language_hint = (source_language or "").strip() or None
        if source_language_hint is None:
            source_language_hint = _find_language_token(resolved_subtitle)
        language_code = _resolve_language_code(
            target_language or _find_language_token(resolved_subtitle) or "en"
        )
        resolved_translation_provider = (
            _normalize_translation_provider(translation_provider) or "llm"
        )
        resolved_translation_batch_size = (
            max(1, int(translation_batch_size))
            if translation_batch_size is not None
            else _DEFAULT_TRANSLATION_BATCH_SIZE
        )
        resolved_transliteration_mode = (
            _normalize_transliteration_mode(transliteration_mode) or "default"
        )
        resolved_transliteration_model = (transliteration_model or "").strip() or None
        payload = {
            "video_path": resolved_video.as_posix(),
            "subtitle_path": resolved_subtitle.as_posix(),
            "source_subtitle_path": resolved_subtitle.as_posix(),
            "source_kind": source_kind,
            "source_language": source_language_hint,
            "target_language": language_code,
            "voice": voice,
            "tempo": tempo,
            "macos_reading_speed": macos_reading_speed,
            "output_dir": output_dir.as_posix() if output_dir else None,
            "start_time_offset": start_offset,
            "end_time_offset": end_offset,
            "original_mix_percent": _clamp_original_mix(original_mix_percent),
            "flush_sentences": flush_sentences if flush_sentences is not None else _DEFAULT_FLUSH_SENTENCES,
            "llm_model": llm_model,
            "translation_provider": resolved_translation_provider,
            "translation_batch_size": resolved_translation_batch_size,
            "transliteration_mode": resolved_transliteration_mode,
            "transliteration_model": resolved_transliteration_model,
            "split_batches": bool(split_batches) if split_batches is not None else False,
            "stitch_batches": True if stitch_batches is None else bool(stitch_batches),
            "include_transliteration": include_transliteration,
            "target_height": resolved_target_height,
            "preserve_aspect_ratio": preserve_aspect_ratio_resolved,
            "enable_lookup_cache": True if enable_lookup_cache is None else bool(enable_lookup_cache),
        }
        if media_metadata:
            payload["media_metadata"] = dict(media_metadata)

        def _worker(job: PipelineJob) -> None:
            with job_runtime_context(self._job_manager.file_locator, job.job_id):
                _run_dub_job(
                    job,
                    video_path=resolved_video,
                    subtitle_path=resolved_subtitle,
                    language_code=language_code,
                    voice=voice,
                    tempo=tempo,
                    macos_reading_speed=macos_reading_speed,
                    output_dir=output_dir,
                    max_workers=self._max_workers,
                    start_time_offset=start_offset,
                    end_time_offset=end_offset,
                    original_mix_percent=original_mix_percent,
                    flush_sentences=flush_sentences,
                    llm_model=llm_model,
                    translation_provider=resolved_translation_provider,
                    translation_batch_size=resolved_translation_batch_size,
                    transliteration_mode=resolved_transliteration_mode,
                    transliteration_model=resolved_transliteration_model,
                    split_batches=bool(split_batches) if split_batches is not None else False,
                    stitch_batches=True if stitch_batches is None else bool(stitch_batches),
                    include_transliteration=include_transliteration,
                    target_height=resolved_target_height,
                    preserve_aspect_ratio=preserve_aspect_ratio_resolved,
                    file_locator=self._job_manager.file_locator,
                    source_subtitle_path=resolved_subtitle,
                    source_kind=source_kind,
                    source_language=source_language_hint,
                    enable_lookup_cache=True if enable_lookup_cache is None else bool(enable_lookup_cache),
                )

        return self._job_manager.submit_background_job(
            job_type="youtube_dub",
            worker=_worker,
            tracker=tracker,
            stop_event=stop_event,
            request_payload=payload,
            user_id=user_id,
            user_role=user_role,
        )


__all__ = [
    "_build_job_result",
    "_run_dub_job",
    "_serialize_generated_files",
    "_serialize_generated_files_batch",
    "YoutubeDubbingService",
]
