"""Routes exposing subtitle job orchestration."""

from __future__ import annotations
import tempfile
from pathlib import Path
from typing import Optional, Union

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from modules import logging_manager as log_mgr
from modules.services import SubtitleService, SubtitleSubmission
from modules.services.llm_models import list_available_llm_models
from modules.services.job_manager import PipelineJobManager
from modules.services.subtitle_service import SUPPORTED_EXTENSIONS
from modules.services.youtube_subtitles import (
    SubtitleKind,
    download_video as perform_youtube_video_download,
    download_subtitle as perform_youtube_subtitle_download,
    list_available_subtitles,
)
from modules.services.youtube_dubbing import (
    DEFAULT_YOUTUBE_VIDEO_ROOT,
    YoutubeDubbingService,
    list_downloaded_videos,
)
from modules.subtitles import SubtitleColorPalette, SubtitleJobOptions

from ..dependencies import (
    RequestUserContext,
    get_pipeline_job_manager,
    get_request_user,
    get_subtitle_service,
    get_youtube_dubbing_service,
)
from ..schemas import (
    PipelineSubmissionResponse,
    SubtitleSourceEntry,
    SubtitleSourceListResponse,
    LLMModelListResponse,
    YoutubeSubtitleDownloadRequest,
    YoutubeSubtitleDownloadResponse,
    YoutubeSubtitleListResponse,
    YoutubeSubtitleTrackPayload,
    YoutubeVideoDownloadRequest,
    YoutubeVideoDownloadResponse,
    YoutubeVideoFormatPayload,
    YoutubeDubRequest,
    YoutubeDubResponse,
    YoutubeNasLibraryResponse,
    YoutubeNasSubtitlePayload,
    YoutubeNasVideoPayload,
)

router = APIRouter(prefix="/api/subtitles", tags=["subtitles"])
logger = log_mgr.get_logger().getChild("webapi.subtitles")


def _as_bool(value: Optional[str | bool], default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _coerce_int(value: Optional[str | int]) -> Optional[int]:
    if isinstance(value, int):
        return value
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(str(value).strip())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid batch_size") from exc


def _parse_ass_font_size(value: Optional[str | int]) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        candidate = value
    else:
        trimmed = str(value).strip()
        if not trimmed:
            return None
        try:
            candidate = int(trimmed)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ass_font_size must be an integer",
            ) from exc
    if candidate <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ass_font_size must be greater than zero",
        )
    if candidate > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ass_font_size must be 200 or smaller",
        )
    return candidate


def _parse_ass_emphasis_scale(value: Optional[str | float]) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        candidate = float(value)
    else:
        trimmed = str(value).strip()
        if not trimmed:
            return None
        try:
            candidate = float(trimmed)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ass_emphasis_scale must be a number",
            ) from exc
    if candidate <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ass_emphasis_scale must be greater than zero",
        )
    if candidate > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ass_emphasis_scale must be 3.0 or smaller",
        )
    return candidate


def _parse_timecode_to_seconds(value: str, *, allow_minutes_only: bool) -> float:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("Empty time value")
    segments = trimmed.split(":")
    hours = 0
    minutes_str: Optional[str] = None
    seconds_str: Optional[str] = None
    if len(segments) == 1:
        if not allow_minutes_only:
            raise ValueError("Time value must include ':' separators")
        try:
            minutes = int(segments[0])
        except ValueError as exc:
            raise ValueError("Relative time must be an integer minute value") from exc
        if minutes < 0:
            raise ValueError("Relative minutes must be non-negative")
        return float(minutes * 60)
    if len(segments) == 2:
        minutes_str, seconds_str = segments
    elif len(segments) == 3:
        hours_str, minutes_str, seconds_str = segments
        try:
            hours = int(hours_str)
        except ValueError as exc:
            raise ValueError("Hours component must be an integer") from exc
        if hours < 0:
            raise ValueError("Hours component cannot be negative")
    else:
        raise ValueError("Time value must be MM:SS or HH:MM:SS")

    if minutes_str is None or seconds_str is None:
        raise ValueError("Minutes and seconds components are required")
    try:
        minutes = int(minutes_str)
        seconds = int(seconds_str)
    except ValueError as exc:
        raise ValueError("Minutes and seconds must be integers") from exc
    if minutes < 0 or seconds < 0:
        raise ValueError("Minutes and seconds must be non-negative")
    if len(segments) == 3 and minutes >= 60:
        raise ValueError("Minutes must be between 00 and 59 when hours are provided")
    if seconds >= 60:
        raise ValueError("Seconds must be between 00 and 59")
    return float(hours * 3600 + minutes * 60 + seconds)


def _parse_time_offset(value: Optional[str]) -> float:
    if value is None:
        return 0.0
    trimmed = str(value).strip()
    if not trimmed:
        return 0.0
    try:
        return _parse_timecode_to_seconds(trimmed, allow_minutes_only=False)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be in MM:SS or HH:MM:SS format.",
        ) from exc


def _parse_end_time(value: Optional[str], start_seconds: float) -> Optional[float]:
    if value is None:
        return None
    trimmed = str(value).strip()
    if not trimmed:
        return None
    if trimmed.startswith("+"):
        relative_expr = trimmed[1:].strip()
        if not relative_expr:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_time offset cannot be empty.",
            )
        try:
            delta = _parse_timecode_to_seconds(relative_expr, allow_minutes_only=True)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Relative end_time must be '+MM:SS', '+HH:MM:SS', or '+<minutes>'.",
            ) from exc
        end_seconds = start_seconds + delta
    else:
        try:
            end_seconds = _parse_timecode_to_seconds(trimmed, allow_minutes_only=False)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_time must be in MM:SS or HH:MM:SS format.",
            ) from exc
    if end_seconds <= start_seconds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be after start_time.",
        )
    return float(end_seconds)


@router.get("/sources", response_model=SubtitleSourceListResponse)
def list_subtitle_sources(
    directory: Optional[str] = None,
    service: SubtitleService = Depends(get_subtitle_service),
) -> SubtitleSourceListResponse:
    """Return discoverable subtitle files."""

    base_path = Path(directory).expanduser() if directory else None
    try:
        entries = service.list_sources(base_path)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    payload = [
        SubtitleSourceEntry(name=path.name, path=path.as_posix())
        for path in entries
    ]
    return SubtitleSourceListResponse(sources=payload)


def _serialize_youtube_tracks(listing) -> YoutubeSubtitleListResponse:
    tracks = [
        YoutubeSubtitleTrackPayload(
            language=track.language,
            kind=track.kind,
            name=track.name,
            formats=track.formats,
        )
        for track in listing.tracks
    ]
    video_formats = [
        YoutubeVideoFormatPayload(
            format_id=entry.format_id,
            ext=entry.ext,
            resolution=entry.resolution,
            fps=entry.fps,
            note=entry.note,
            bitrate_kbps=entry.bitrate_kbps,
            filesize=entry.filesize,
        )
        for entry in getattr(listing, "video_formats", []) or []
    ]
    return YoutubeSubtitleListResponse(
        video_id=listing.video_id,
        title=listing.title,
        tracks=tracks,
        video_formats=video_formats,
    )


@router.get("/youtube/subtitles", response_model=YoutubeSubtitleListResponse)
def list_youtube_subtitles(url: str) -> YoutubeSubtitleListResponse:
    """Return available YouTube subtitle languages for ``url``."""

    try:
        listing = list_available_subtitles(url)
    except Exception as exc:
        logger.warning("Unable to list YouTube subtitles for %s", url, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to list subtitles: {exc}",
        ) from exc
    return _serialize_youtube_tracks(listing)


@router.post("/youtube/download", response_model=YoutubeSubtitleDownloadResponse)
def download_youtube_subtitle(
    payload: YoutubeSubtitleDownloadRequest,
    service: SubtitleService = Depends(get_subtitle_service),
) -> YoutubeSubtitleDownloadResponse:
    """Download a YouTube subtitle track into the subtitle NAS directory."""

    language = payload.language.strip()
    if not language:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="language is required",
        )
    kind: SubtitleKind = payload.kind

    try:
        listing = list_available_subtitles(payload.url)
    except Exception as exc:
        logger.warning("Unable to inspect YouTube subtitles for %s", payload.url, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to inspect subtitles: {exc}",
        ) from exc

    selected = next(
        (track for track in listing.tracks if track.language == language and track.kind == kind),
        None,
    )
    if selected is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {kind} subtitles found for language '{language}'",
        )

    try:
        output_path = perform_youtube_subtitle_download(
            payload.url,
            language=language,
            kind=kind,
            output_dir=service.default_source_dir,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.warning(
            "Failed to download YouTube subtitles for %s (%s, %s)",
            payload.url,
            language,
            kind,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subtitle download failed: {exc}",
        ) from exc

    return YoutubeSubtitleDownloadResponse(
        output_path=output_path.as_posix(),
        filename=output_path.name,
    )


def _looks_like_youtube_subtitle(path: Path) -> bool:
    """Heuristic to detect YouTube-sourced subtitles from the filename."""

    name = path.name.lower()
    stem = path.stem.lower()
    normalized = name.replace("_", "-")
    if normalized.endswith("-yt.srt"):
        return True
    if stem.endswith("_yt") or stem.endswith("-yt"):
        return True
    # Match YouTube video id enclosed in brackets, e.g., [kZ5Jq2Is888]
    return bool(regex.search(r"\[[a-z0-9_-]{8,15}\]", name, flags=regex.IGNORECASE))


def _serialize_nas_video(entry) -> YoutubeNasVideoPayload:
    subtitles = [
        YoutubeNasSubtitlePayload(
            path=sub.path.as_posix(),
            filename=sub.path.name,
            language=sub.language,
            format=sub.format,
        )
        for sub in getattr(entry, "subtitles", []) or []
    ]
    return YoutubeNasVideoPayload(
        path=entry.path.as_posix(),
        filename=entry.path.name,
        folder=entry.path.parent.as_posix(),
        size_bytes=entry.size_bytes,
        modified_at=entry.modified_at,
        subtitles=subtitles,
    )


def _parse_tempo_value(value: Optional[float | str]) -> float:
    if value is None:
        return 1.0
    try:
        tempo = float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tempo must be a number",
        ) from exc
    if tempo <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tempo must be greater than zero",
        )
    if tempo > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tempo must be 5.0 or lower",
        )
    return tempo


@router.post("/youtube/video", response_model=YoutubeVideoDownloadResponse)
def download_youtube_video(
    payload: YoutubeVideoDownloadRequest,
) -> YoutubeVideoDownloadResponse:
    """Download a YouTube video to the NAS directory."""

    target_root = Path(payload.output_dir or "/Volumes/Data/Video/Youtube").expanduser()
    try:
        target_root.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to create output directory: {exc}",
        ) from exc

    format_id = payload.format_id.strip() if isinstance(payload.format_id, str) else None
    if format_id:
        try:
            listing = list_available_subtitles(payload.url)
        except Exception as exc:
            logger.warning("Unable to inspect YouTube video formats for %s", payload.url, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to inspect video formats: {exc}",
            ) from exc
        known_formats = {entry.format_id for entry in getattr(listing, "video_formats", [])}
        if format_id not in known_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requested format is not available for this video.",
            )

    try:
        output_path = perform_youtube_video_download(
            payload.url,
            output_root=target_root,
            format_id=format_id,
        )
    except Exception as exc:
        logger.warning("YouTube video download failed for %s", payload.url, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video download failed: {exc}",
        ) from exc

    return YoutubeVideoDownloadResponse(
        output_path=output_path.as_posix(),
        filename=output_path.name,
        folder=output_path.parent.as_posix(),
    )


@router.get("/youtube/library", response_model=YoutubeNasLibraryResponse)
def list_youtube_library(base_dir: Optional[str] = None) -> YoutubeNasLibraryResponse:
    """Return downloaded YouTube videos discovered in the NAS path."""

    target_root = Path(base_dir or DEFAULT_YOUTUBE_VIDEO_ROOT).expanduser()
    try:
        videos = list_downloaded_videos(target_root)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    payload = [_serialize_nas_video(video) for video in videos]
    return YoutubeNasLibraryResponse(base_dir=target_root.as_posix(), videos=payload)


@router.post("/youtube/dub", response_model=YoutubeDubResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_youtube_dub(
    payload: YoutubeDubRequest,
    youtube_dubbing_service: YoutubeDubbingService = Depends(get_youtube_dubbing_service),
    request_user: RequestUserContext = Depends(get_request_user),
) -> YoutubeDubResponse:
    """Generate a dubbed audio track from an ASS subtitle and mux it into the video."""

    video_path = Path(payload.video_path).expanduser()
    subtitle_path = Path(payload.subtitle_path).expanduser()

    tempo = _parse_tempo_value(payload.tempo)
    macos_speed = payload.macos_reading_speed if payload.macos_reading_speed is not None else 100
    if macos_speed <= 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="macos_reading_speed must be greater than zero",
        )
    mix_percent = payload.original_mix_percent
    if mix_percent is not None and (mix_percent < 0 or mix_percent > 100):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="original_mix_percent must be between 0 and 100",
        )
    flush_sentences = payload.flush_sentences
    if flush_sentences is not None and flush_sentences <= 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="flush_sentences must be greater than zero",
        )
    llm_model = (payload.llm_model or "").strip() or None
    split_batches = bool(payload.split_batches) if payload.split_batches is not None else False
    start_offset = _parse_time_offset(payload.start_time_offset)
    end_offset = _parse_end_time(payload.end_time_offset, start_offset)
    voice = (payload.voice or "gTTS").strip() or "gTTS"
    target_language = (payload.target_language or "").strip() or None
    output_dir = Path(payload.output_dir).expanduser() if payload.output_dir else None

    try:
        job = youtube_dubbing_service.enqueue(
            video_path=video_path,
            subtitle_path=subtitle_path,
            target_language=target_language,
            voice=voice,
            tempo=tempo,
            macos_reading_speed=macos_speed,
            output_dir=output_dir,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
            start_time_offset=start_offset,
            end_time_offset=end_offset,
            original_mix_percent=mix_percent,
            flush_sentences=flush_sentences,
            llm_model=llm_model,
            split_batches=split_batches,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning(
            "Unable to generate dubbed YouTube video",
            exc_info=True,
        )
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to generate dubbed video: {exc}",
        ) from exc

    return YoutubeDubResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
        job_type=job.job_type,
    )


@router.get("/models", response_model=LLMModelListResponse)
def list_subtitle_models() -> LLMModelListResponse:
    """Return available Ollama models for subtitle translations."""

    try:
        models = list_available_llm_models()
    except Exception as exc:
        logger.error("Unable to query Ollama model tags", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to query Ollama model list.",
        ) from exc

    return LLMModelListResponse(models=models)


@router.post(
    "/jobs",
    response_model=PipelineSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_subtitle_job(
    input_language: str = Form(...),
    target_language: str = Form(...),
    original_language: Optional[str] = Form(None),
    llm_model: Optional[str] = Form(None),
    enable_transliteration: Union[str, bool] = Form(False),
    highlight: Union[str, bool] = Form(True),
    show_original: Union[str, bool] = Form(True),
    batch_size: Optional[str] = Form(None),
    worker_count: Optional[str] = Form(None),
    start_time: Optional[str] = Form("00:00"),
    end_time: Optional[str] = Form(None),
    source_path: Optional[str] = Form(None),
    cleanup_source: Union[str, bool] = Form(False),
    mirror_batches_to_source_dir: Union[str, bool] = Form(True),
    output_format: str = Form("srt"),
    subtitle_color_original: Optional[str] = Form(None),
    subtitle_color_translation: Optional[str] = Form(None),
    subtitle_color_transliteration: Optional[str] = Form(None),
    subtitle_color_highlight_current: Optional[str] = Form(None),
    subtitle_color_highlight_prior: Optional[str] = Form(None),
    ass_font_size: Optional[str] = Form(None),
    ass_emphasis_scale: Optional[str] = Form(None),
    file: UploadFile | None = File(None),
    service: SubtitleService = Depends(get_subtitle_service),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Submit a subtitle processing job."""

    if file is None and not source_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either an upload or source_path must be provided.",
        )
    if file is not None and source_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one of upload or source_path may be provided.",
        )

    color_payload = {
        "original": subtitle_color_original,
        "translation": subtitle_color_translation,
        "transliteration": subtitle_color_transliteration,
        "highlight_current": subtitle_color_highlight_current,
        "highlight_prior": subtitle_color_highlight_prior,
    }
    palette_mapping = {
        key: value
        for key, value in color_payload.items()
        if value is not None and str(value).strip()
    }

    try:
        start_offset_seconds = _parse_time_offset(start_time)
        end_offset_seconds = _parse_end_time(end_time, start_offset_seconds)
        palette = SubtitleColorPalette.from_mapping(palette_mapping if palette_mapping else None)
        resolved_input_language = (input_language or "").strip()
        if not resolved_input_language:
            resolved_input_language = "English"
        resolved_target_language = (target_language or "").strip()
        resolved_original_language = (original_language or "").strip()
        if not resolved_original_language:
            resolved_original_language = resolved_input_language
        resolved_llm_model = (llm_model or "").strip() or None
        options_model = SubtitleJobOptions(
            input_language=resolved_input_language,
            target_language=resolved_target_language,
            original_language=resolved_original_language,
            show_original=_as_bool(show_original, True),
            enable_transliteration=_as_bool(enable_transliteration, False),
            highlight=_as_bool(highlight, True),
            batch_size=_coerce_int(batch_size),
            worker_count=_coerce_int(worker_count),
            mirror_batches_to_source_dir=_as_bool(mirror_batches_to_source_dir, True),
            start_time_offset=start_offset_seconds,
            end_time_offset=end_offset_seconds,
            output_format=output_format,
            color_palette=palette,
            llm_model=resolved_llm_model,
            ass_font_size=_parse_ass_font_size(ass_font_size),
            ass_emphasis_scale=_parse_ass_emphasis_scale(ass_emphasis_scale),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    cleanup_flag = _as_bool(cleanup_source, False)
    temp_file: Optional[Path] = None

    try:
        if file is not None:
            filename = file.filename or "subtitle.srt"
            suffix = Path(filename).suffix or ".srt"
            if suffix.lower() not in SUPPORTED_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported subtitle extension '{suffix}'.",
                )
            with tempfile.NamedTemporaryFile("wb", suffix=suffix, delete=False) as handle:
                contents = await file.read()
                if not contents:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Uploaded subtitle file is empty.",
                    )
                handle.write(contents)
                temp_file = Path(handle.name)
            source_path_resolved = temp_file
            original_name = filename
            cleanup_flag = True
        else:
            assert source_path is not None  # for mypy
            source_path_resolved = Path(source_path).expanduser()
            if not source_path_resolved.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Subtitle source '{source_path_resolved}' does not exist.",
                )
            if source_path_resolved.suffix.lower() not in SUPPORTED_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported subtitle extension '{source_path_resolved.suffix}'.",
                )
            original_name = source_path_resolved.name
    except HTTPException:
        if temp_file is not None:
            temp_file.unlink(missing_ok=True)
        raise
    except OSError as exc:
        if temp_file is not None:
            temp_file.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to prepare subtitle upload.",
        ) from exc

    try:
        object.__setattr__(
            options_model,
            "source_is_youtube",
            _looks_like_youtube_subtitle(source_path_resolved),
        )
    except Exception:
        # Defensive: keep options intact if tagging fails.
        pass

    submission = SubtitleSubmission(
        source_path=source_path_resolved,
        original_name=original_name,
        options=options_model,
        cleanup=cleanup_flag,
    )

    try:
        job = service.enqueue(
            submission,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except Exception:
        if temp_file is not None:
            temp_file.unlink(missing_ok=True)
        raise

    return PipelineSubmissionResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
        job_type=job.job_type,
    )


@router.get("/jobs/{job_id}/result")
def get_subtitle_job_result(
    job_id: str,
    job_manager: PipelineJobManager = Depends(get_pipeline_job_manager),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Return the final payload for a subtitle job."""

    job = job_manager.get(
        job_id,
        user_id=request_user.user_id,
        user_role=request_user.user_role,
    )
    if job.job_type != "subtitle":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subtitle job not found")
    return job.result_payload or {}
