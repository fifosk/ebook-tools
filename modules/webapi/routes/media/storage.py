"""Storage file streaming routes for media outputs."""

from __future__ import annotations

import mimetypes
import re
import urllib.parse
from pathlib import Path
from typing import Iterator, Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse

from .... import config_manager as cfg
from ....services.file_locator import FileLocator
from ...dependencies import get_file_locator

storage_router = APIRouter()


class _RangeParseError(Exception):
    """Raised when the supplied Range header cannot be satisfied."""

def _parse_byte_range(range_value: str, file_size: int) -> Tuple[int, int]:
    """Return the inclusive byte range requested by ``range_value``.

    ``range_value`` must follow the ``bytes=start-end`` syntax. Only a single range is
    supported and the resulting indices are clamped to the available file size. A
    :class:`_RangeParseError` is raised when the header is malformed or does not
    overlap the file contents.
    """

    if file_size <= 0:
        raise _RangeParseError

    header = range_value.strip()
    if not header.lower().startswith("bytes="):
        raise _RangeParseError

    raw_spec = header[len("bytes=") :].strip()
    if "," in raw_spec:
        raise _RangeParseError

    if "-" not in raw_spec:
        raise _RangeParseError

    start_token, end_token = raw_spec.split("-", 1)

    if not start_token:
        # suffix-byte-range-spec: bytes=-N
        if not end_token.isdigit():
            raise _RangeParseError
        length = int(end_token)
        if length <= 0:
            raise _RangeParseError
        start = max(file_size - length, 0)
        end = file_size - 1
    else:
        if not start_token.isdigit():
            raise _RangeParseError
        start = int(start_token)
        if start >= file_size:
            raise _RangeParseError

        if end_token:
            if not end_token.isdigit():
                raise _RangeParseError
            end = int(end_token)
            if end < start:
                raise _RangeParseError
            end = min(end, file_size - 1)
        else:
            end = file_size - 1

    return start, end


def _iter_file_chunks(path: Path, start: int, end: int) -> Iterator[bytes]:
    """Yield chunks from ``path`` between ``start`` and ``end`` (inclusive)."""

    chunk_size = 1 << 16
    total = max(end - start + 1, 0)
    if total <= 0:
        return

    with path.open("rb") as stream:
        stream.seek(start)
        remaining = total
        while remaining > 0:
            chunk = stream.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def _stream_local_file(resolved_path: Path, range_header: str | None = None) -> StreamingResponse:
    try:
        stat_result = resolved_path.stat()
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc

    file_size = int(stat_result.st_size)
    suffix = resolved_path.suffix.lower()
    media_type = mimetypes.guess_type(resolved_path.name)[0]
    if not media_type:
        if suffix == ".vtt":
            media_type = "text/vtt"
        elif suffix == ".srt":
            media_type = "text/x-srt"
        elif suffix == ".ass":
            media_type = "text/plain"
        elif suffix in {".m4v", ".mp4"}:
            media_type = "video/mp4"

    def _should_inline(content_type: str | None) -> bool:
        if not content_type:
            return False
        if content_type.startswith(("video/", "audio/", "image/")):
            return True
        if content_type in {"text/vtt"}:
            return True
        return False

    if range_header and "," in range_header:
        # Some clients (notably iOS) may request multiple ranges. We only support a single
        # contiguous range, so fall back to streaming the full payload instead of failing.
        range_header = None

    if range_header:
        try:
            start, end = _parse_byte_range(range_header, file_size)
        except _RangeParseError as exc:
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                detail="Requested range not satisfiable",
                headers={"Content-Range": f"bytes */{file_size}"},
            ) from exc
        status_code = status.HTTP_206_PARTIAL_CONTENT
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
        }
    else:
        start = 0
        end = file_size - 1 if file_size > 0 else -1
        status_code = status.HTTP_200_OK
        headers = {"Accept-Ranges": "bytes"}

    content_length = max(end - start + 1, 0)
    headers["Content-Length"] = str(content_length)
    # Latin-1 header encoding will fail on filenames with accents; provide a
    # safe ASCII fallback while still advertising the UTF-8 name via RFC 5987.
    original_name = resolved_path.name
    safe_ascii = re.sub(r"[^0-9A-Za-z._-]", "_", original_name) or "download"
    quoted_utf8 = urllib.parse.quote(original_name)
    disposition = "inline" if _should_inline(media_type) else "attachment"
    headers["Content-Disposition"] = (
        f'{disposition}; filename="{safe_ascii}"; filename*=UTF-8\'\'{quoted_utf8}'
    )

    body_iterator = _iter_file_chunks(resolved_path, start, end)
    return StreamingResponse(
        body_iterator,
        status_code=status_code,
        media_type=media_type or "application/octet-stream",
        headers=headers,
    )


async def _download_job_file(
    job_id: str,
    filename: str,
    file_locator: FileLocator,
    range_header: str | None,
):
    """Return a streaming response for the requested job file."""

    try:
        resolved_path = file_locator.resolve_path(job_id, filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc

    if not resolved_path.exists() or not resolved_path.is_file():
        resolved_path = _resolve_alternate_job_path(job_id, filename) or resolved_path
        if not resolved_path.exists() or not resolved_path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return _stream_local_file(resolved_path, range_header)


def _resolve_alternate_job_path(job_id: str, filename: str) -> Optional[Path]:
    """Try a repo-root storage directory when the primary locator misses."""

    try:
        repo_root = cfg.SCRIPT_DIR.parent
        candidate_root = repo_root / "storage"
        if not candidate_root.exists():
            return None
        alternate_locator = FileLocator(storage_dir=candidate_root)
        return alternate_locator.resolve_path(job_id, filename)
    except Exception:
        return None


def _resolve_cover_download_path(filename: str) -> Path:
    root = cfg.resolve_directory(None, cfg.DEFAULT_COVERS_RELATIVE)
    candidate = (root / filename).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return candidate


@storage_router.get("/jobs/{job_id}/files/{filename:path}")
async def download_job_file(
    job_id: str,
    filename: str,
    file_locator: FileLocator = Depends(get_file_locator),
    range_header: str | None = Header(default=None, alias="Range"),
):
    """Stream the requested job file supporting optional byte ranges."""

    return await _download_job_file(job_id, filename, file_locator, range_header)


@storage_router.get("/jobs/{job_id}/{filename:path}")
async def download_job_file_without_prefix(
    job_id: str,
    filename: str,
    file_locator: FileLocator = Depends(get_file_locator),
    range_header: str | None = Header(default=None, alias="Range"),
):
    """Stream job files that were referenced without the legacy ``/files`` prefix."""

    return await _download_job_file(job_id, filename, file_locator, range_header)


@storage_router.get("/covers/{filename:path}")
async def download_cover_file(
    filename: str,
    range_header: str | None = Header(default=None, alias="Range"),
):
    """Serve cover images stored in the shared covers directory."""

    resolved_path = _resolve_cover_download_path(filename)
    return _stream_local_file(resolved_path, range_header)
