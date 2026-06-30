"""Routes for managing pipeline book files and covers."""

from __future__ import annotations

import mimetypes
import io
import logging
import re
import stat as stat_module
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response
from PIL import Image, ImageOps

from modules.library import LibraryNotFoundError, LibrarySync
from modules.permissions import can_access, normalize_role, resolve_access_policy

from ... import config_manager as cfg
from ...core import ingestion
from ...core.config import build_pipeline_config
from ..dependencies import (
    RequestUserContext,
    RuntimeContextProvider,
    get_file_locator,
    get_library_sync,
    get_pipeline_service,
    get_request_user,
    get_runtime_context_provider,
)
from ..route_telemetry import log_started_route_result
from ..schemas import (
    BookContentIndexResponse,
    PipelineFileBrowserResponse,
    PipelineFileDeleteRequest,
    PipelineFileEntry,
)
from ...services.file_locator import FileLocator
from ...services.pipeline_service import PipelineService
from ...services.source_discovery import safe_iterdir, safe_stat, walk_visible_source_files

router = APIRouter()
logger = logging.getLogger(__name__)


_COVER_TARGET_SIZE = (600, 900)
_COVER_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
_COVER_ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
_ALLOWED_ROLES = {"admin", "editor"}


def _log_pipeline_file_picker(
    started_at: float,
    *,
    result: str,
    ebook_count: int = 0,
    output_count: int = 0,
    books_root_present: bool | None = None,
    output_root_present: bool | None = None,
) -> None:
    log_started_route_result(
        logger,
        metric_name="SOURCE_PICKER_ROUTE_DURATION",
        message="Pipeline source picker",
        operation="pipeline_files",
        result=result,
        started_at=started_at,
        include_operation=False,
        duration_first=False,
        ebooks=ebook_count,
        outputs=output_count,
        books_root_present=books_root_present,
        output_root_present=output_root_present,
    )


def _content_index_counts(content_index: object) -> tuple[int, int]:
    if not isinstance(content_index, dict):
        return 0, 0
    chapters = content_index.get("chapters")
    chapter_count = len(chapters) if isinstance(chapters, list) else 0
    total_sentences = content_index.get("total_sentences")
    sentence_count = total_sentences if isinstance(total_sentences, int) else 0
    return chapter_count, sentence_count


def _log_pipeline_content_index(
    started_at: float,
    *,
    result: str,
    chapter_count: int = 0,
    sentence_count: int = 0,
) -> None:
    log_started_route_result(
        logger,
        metric_name="SOURCE_PICKER_ROUTE_DURATION",
        message="Pipeline content index",
        operation="pipeline_content_index",
        result=result,
        started_at=started_at,
        include_operation=False,
        duration_first=False,
        chapters=max(0, chapter_count),
        sentences=max(0, sentence_count),
    )


def _ensure_editor(request_user: RequestUserContext) -> None:
    role = normalize_role(request_user.user_role) or ""
    if role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("/files/content-index", response_model=BookContentIndexResponse)
async def get_book_content_index(
    input_file: str,
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Return chapter metadata for a selected EPUB file."""

    started_at = time.perf_counter()
    _ensure_editor(request_user)
    trimmed = (input_file or "").strip()
    if not trimmed:
        _log_pipeline_content_index(started_at, result="bad_request")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="input_file is required")

    resolved_config = context_provider.resolve_config({})
    with context_provider.activation({}, {}) as context:
        resolved_input = cfg.resolve_file_path(trimmed, context.books_dir)
        if not resolved_input or not resolved_input.exists():
            _log_pipeline_content_index(started_at, result="not_found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EPUB file not found")

        pipeline_config = build_pipeline_config(context, resolved_config, overrides={})
        try:
            refined_sentences, _ = ingestion.get_refined_sentences(
                str(resolved_input),
                pipeline_config,
                force_refresh=False,
                metadata={
                    "mode": "api",
                    "max_words": pipeline_config.max_words,
                },
            )
            content_index = ingestion.get_content_index(
                str(resolved_input),
                pipeline_config,
                refined_sentences,
                force_refresh=False,
                metadata={
                    "mode": "api",
                    "max_words": pipeline_config.max_words,
                },
            )
        except Exception as exc:
            _log_pipeline_content_index(started_at, result="error")
            raise HTTPException(
                status_code=422,
                detail="Unable to load chapters for this EPUB. The file may be corrupt or unsupported.",
            ) from exc

    chapter_count, sentence_count = _content_index_counts(content_index)
    _log_pipeline_content_index(
        started_at,
        result="success",
        chapter_count=chapter_count,
        sentence_count=sentence_count,
    )
    return BookContentIndexResponse(input_file=trimmed, content_index=content_index)


def _format_relative_path(path: Path, root: Path) -> str:
    """Return ``path`` relative to ``root`` using POSIX separators when possible."""

    try:
        relative = path.relative_to(root)
    except ValueError:
        return path.as_posix()
    return relative.as_posix() or path.name


def _is_present_directory(path: Path) -> bool:
    path_stat = safe_stat(path)
    return path_stat is not None and stat_module.S_ISDIR(path_stat.st_mode)


def _list_ebook_files(root: Path) -> List[PipelineFileEntry]:
    entries: List[PipelineFileEntry] = []
    for candidate in walk_visible_source_files(root, suffixes={".epub"}):
        path = candidate.path
        entries.append(
            PipelineFileEntry(
                name=path.name,
                path=_format_relative_path(path, root),
                type="file",
                size_bytes=candidate.stat.st_size,
                modified_at=datetime.fromtimestamp(candidate.stat.st_mtime),
            )
        )
    return sorted(
        entries,
        key=lambda entry: (
            -entry.modified_at.timestamp() if entry.modified_at else 0,
            entry.path.lower(),
        ),
    )


def _list_output_entries(root: Path) -> List[PipelineFileEntry]:
    entries: List[PipelineFileEntry] = []
    if not _is_present_directory(root):
        return entries
    for path in sorted(safe_iterdir(root)):
        if path.name.startswith("."):
            continue
        stat = safe_stat(path)
        if stat is None:
            continue
        if stat_module.S_ISDIR(stat.st_mode):
            entry_type = "directory"
            size_bytes = None
        elif stat_module.S_ISREG(stat.st_mode):
            entry_type = "file"
            size_bytes = stat.st_size
        else:
            continue
        entries.append(
            PipelineFileEntry(
                name=path.name,
                path=_format_relative_path(path, root),
                type=entry_type,
                size_bytes=size_bytes,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
            )
        )
    return entries


def _normalise_epub_name(filename: str | None) -> str:
    raw_name = Path(filename or "uploaded.epub").name or "uploaded.epub"
    if raw_name.lower().endswith(".epub"):
        return raw_name
    return f"{raw_name}.epub"


def _normalise_cover_name(filename: str | None) -> str:
    raw_name = Path(filename or "cover.jpg").name or "cover.jpg"
    stem = Path(raw_name).stem
    safe_stem = re.sub(r"[^0-9A-Za-z._-]", "_", stem) or "cover"
    return f"{safe_stem}.jpg"


def _reserve_destination_path(directory: Path, filename: str) -> Path:
    stem = Path(filename).stem
    suffix = Path(filename).suffix or ".epub"
    candidate = directory / f"{stem}{suffix}"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def _find_job_cover_path(metadata_root: Path) -> Optional[Path]:
    if not metadata_root.exists():
        return None
    for candidate in sorted(metadata_root.glob("cover.*")):
        if candidate.is_file():
            return candidate
    return None


def _guess_cover_media_type(path: Path) -> str:
    media_type, _ = mimetypes.guess_type(path.name)
    return media_type or "image/jpeg"


@router.get("/files", response_model=PipelineFileBrowserResponse)
async def list_pipeline_files(
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Return available ebook and output paths for client-side file pickers."""

    _ensure_editor(request_user)
    started_at = time.perf_counter()
    try:
        with context_provider.activation({}, {}) as context:
            books_root_present = _is_present_directory(context.books_dir)
            output_root_present = _is_present_directory(context.output_dir)
            ebooks = _list_ebook_files(context.books_dir)
            outputs = _list_output_entries(context.output_dir)
    except Exception:
        _log_pipeline_file_picker(started_at, result="error")
        raise

    _log_pipeline_file_picker(
        started_at,
        result="success",
        ebook_count=len(ebooks),
        output_count=len(outputs),
        books_root_present=books_root_present,
        output_root_present=output_root_present,
    )

    return PipelineFileBrowserResponse(
        ebooks=ebooks,
        outputs=outputs,
        books_root=context.books_dir.as_posix(),
        output_root=context.output_dir.as_posix(),
    )


@router.post("/files/upload", response_model=PipelineFileEntry, status_code=status.HTTP_201_CREATED)
async def upload_pipeline_ebook(
    file: UploadFile = File(...),
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Persist an uploaded EPUB file into the configured books directory."""

    _ensure_editor(request_user)
    content_type = (file.content_type or "").lower()
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename required")

    if content_type and content_type not in {
        "application/epub+zip",
        "application/zip",
        "application/octet-stream",
    }:
        if not file.filename.lower().endswith(".epub"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only EPUB files can be uploaded",
            )

    normalised_name = _normalise_epub_name(file.filename)

    with context_provider.activation({}, {}) as context:
        destination_dir = context.books_dir
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = _reserve_destination_path(destination_dir, normalised_name)

        try:
            with destination.open("wb") as buffer:
                while True:
                    chunk = await file.read(1 << 20)
                    if not chunk:
                        break
                    buffer.write(chunk)
        finally:
            await file.close()

    stat = destination.stat()
    return PipelineFileEntry(
        name=destination.name,
        path=_format_relative_path(destination, destination_dir),
        type="file",
        size_bytes=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime),
    )


@router.post("/covers/upload", response_model=PipelineFileEntry, status_code=status.HTTP_201_CREATED)
async def upload_cover_file(
    file: UploadFile = File(...),
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
):
    """Persist an uploaded cover image into the configured covers directory."""

    content_type = (file.content_type or "").lower()
    raw_suffix = Path(file.filename or "").suffix.lower()
    if raw_suffix == ".jpeg":
        raw_suffix = ".jpg"

    if content_type not in _COVER_ALLOWED_CONTENT_TYPES and raw_suffix not in _COVER_ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, or WebP cover images are supported",
        )

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename required")

    normalised_name = _normalise_cover_name(file.filename)

    with context_provider.activation({}, {}):
        destination_dir = cfg.resolve_directory(None, cfg.DEFAULT_COVERS_RELATIVE)
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = _reserve_destination_path(destination_dir, normalised_name)

        try:
            raw = await file.read()
            try:
                with Image.open(io.BytesIO(raw)) as img:
                    normalized = ImageOps.exif_transpose(img)
                    if normalized.mode in ("RGBA", "LA") or (
                        normalized.mode == "P" and "transparency" in normalized.info
                    ):
                        rgba = normalized.convert("RGBA")
                        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                        background.alpha_composite(rgba)
                        normalized_rgb = background.convert("RGB")
                    else:
                        normalized_rgb = normalized.convert("RGB")

                    target_width, target_height = _COVER_TARGET_SIZE
                    width, height = normalized_rgb.size
                    if width <= 0 or height <= 0:
                        raise ValueError("Invalid image size")
                    scale = min(target_width / width, target_height / height)
                    next_width = max(1, round(width * scale))
                    next_height = max(1, round(height * scale))
                    resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS)
                    resized = normalized_rgb.resize((next_width, next_height), resample=resample)

                    canvas = Image.new("RGB", (target_width, target_height), (255, 255, 255))
                    offset = ((target_width - next_width) // 2, (target_height - next_height) // 2)
                    canvas.paste(resized, offset)
                    canvas.save(destination, format="JPEG", quality=88, optimize=True, progressive=True)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Unable to process cover image.",
                ) from exc
        finally:
            await file.close()

    stat = destination.stat()
    return PipelineFileEntry(
        name=destination.name,
        path=f"storage/covers/{destination.name}",
        type="file",
        size_bytes=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime),
    )


@router.delete("/files", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline_ebook(
    payload: PipelineFileDeleteRequest,
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Remove an existing EPUB from the configured books directory."""

    _ensure_editor(request_user)
    with context_provider.activation({}, {}) as context:
        books_dir = context.books_dir
        target = (books_dir / payload.path).resolve(strict=False)

        try:
            target.relative_to(books_dir)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ebook path",
            ) from exc

        if not target.exists():
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        if not target.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only files can be deleted",
            )

        try:
            target.unlink()
        except FileNotFoundError:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to delete ebook.",
            ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{job_id}/cover")
async def fetch_job_cover(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    file_locator: FileLocator = Depends(get_file_locator),
    library_sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Return the stored cover image for ``job_id`` if available."""

    permission_denied = False
    job_missing = False
    try:
        pipeline_service.get_job(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except PermissionError:
        permission_denied = True
    except KeyError:
        job_missing = True

    metadata_root = file_locator.metadata_root(job_id)
    cover_path = _find_job_cover_path(metadata_root)

    if (cover_path is None or not cover_path.is_file()) and library_sync is not None:
        item = library_sync.get_item(job_id)
        if item is not None:
            metadata_payload = item.metadata.data if hasattr(item.metadata, "data") else {}
            owner_id = item.owner_id or metadata_payload.get("user_id") or metadata_payload.get("owner_id")
            if isinstance(owner_id, str):
                owner_id = owner_id.strip() or None
            policy = resolve_access_policy(metadata_payload.get("access"), default_visibility="public")
            if not can_access(
                policy,
                owner_id=owner_id,
                user_id=request_user.user_id,
                user_role=request_user.user_role,
                permission="view",
            ):
                permission_denied = True
                library_cover = None
            else:
                try:
                    library_cover = library_sync.find_cover_asset(job_id)
                except LibraryNotFoundError:
                    library_cover = None
        else:
            try:
                library_cover = library_sync.find_cover_asset(job_id)
            except LibraryNotFoundError:
                library_cover = None
        if library_cover is not None and library_cover.is_file():
            cover_path = library_cover

    if cover_path is None or not cover_path.is_file():
        if job_missing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover not found")
        if permission_denied:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access cover")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover not found")

    media_type = _guess_cover_media_type(cover_path)
    response = FileResponse(
        cover_path,
        media_type=media_type,
        filename=cover_path.name,
    )
    response.headers["Content-Disposition"] = f'inline; filename="{cover_path.name}"'
    return response


__all__ = ["router"]
