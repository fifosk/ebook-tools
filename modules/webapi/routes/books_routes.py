"""Routes for managing pipeline book files and covers."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response

from modules.library import LibraryNotFoundError, LibrarySync

from ..dependencies import (
    RequestUserContext,
    RuntimeContextProvider,
    get_file_locator,
    get_library_sync,
    get_pipeline_service,
    get_request_user,
    get_runtime_context_provider,
)
from ..schemas import (
    PipelineFileBrowserResponse,
    PipelineFileDeleteRequest,
    PipelineFileEntry,
)
from ...services.file_locator import FileLocator
from ...services.pipeline_service import PipelineService

router = APIRouter()

def _format_relative_path(path: Path, root: Path) -> str:
    """Return ``path`` relative to ``root`` using POSIX separators when possible."""

    try:
        relative = path.relative_to(root)
    except ValueError:
        return path.as_posix()
    return relative.as_posix() or path.name


def _list_ebook_files(root: Path) -> List[PipelineFileEntry]:
    entries: List[PipelineFileEntry] = []
    if not root.exists():
        return entries
    for path in sorted(root.glob("*.epub")):
        if not path.is_file():
            continue
        entries.append(
            PipelineFileEntry(
                name=path.name,
                path=_format_relative_path(path, root),
                type="file",
            )
        )
    return entries


def _list_output_entries(root: Path) -> List[PipelineFileEntry]:
    entries: List[PipelineFileEntry] = []
    if not root.exists():
        return entries
    for path in sorted(root.iterdir()):
        if path.name.startswith("."):
            continue
        entry_type = "directory" if path.is_dir() else "file"
        entries.append(
            PipelineFileEntry(
                name=path.name,
                path=_format_relative_path(path, root),
                type=entry_type,
            )
        )
    return entries


def _normalise_epub_name(filename: str | None) -> str:
    raw_name = Path(filename or "uploaded.epub").name or "uploaded.epub"
    if raw_name.lower().endswith(".epub"):
        return raw_name
    return f"{raw_name}.epub"


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
):
    """Return available ebook and output paths for client-side file pickers."""

    with context_provider.activation({}, {}) as context:
        ebooks = _list_ebook_files(context.books_dir)
        outputs = _list_output_entries(context.output_dir)

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
):
    """Persist an uploaded EPUB file into the configured books directory."""

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

    return PipelineFileEntry(
        name=destination.name,
        path=_format_relative_path(destination, destination_dir),
        type="file",
    )


@router.delete("/files", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline_ebook(
    payload: PipelineFileDeleteRequest,
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
):
    """Remove an existing EPUB from the configured books directory."""

    with context_provider.activation({}, {}) as context:
        books_dir = context.books_dir
        target = (books_dir / payload.path).resolve()

        try:
            target.relative_to(books_dir)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ebook path",
            ) from exc

        if not target.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ebook not found",
            )

        if not target.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only files can be deleted",
            )

        try:
            target.unlink()
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unable to delete ebook: {exc}",
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
