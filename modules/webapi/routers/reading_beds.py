"""Reading bed (background music) catalog and administration routes."""

from __future__ import annotations

import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse, Response

from modules import logging_manager as log_mgr
from modules.services.file_locator import FileLocator
from modules.user_management import AuthService

from ..auth_utils import require_admin_user
from ..dependencies import get_auth_service
from ..route_telemetry import log_started_route_result
from ..schemas.reading_beds import (
    ReadingBedDeleteResponse,
    ReadingBedEntry,
    ReadingBedListResponse,
    ReadingBedUpdateRequest,
)


router = APIRouter(prefix="/api/reading-beds", tags=["reading-beds"])
admin_router = APIRouter(prefix="/api/admin/reading-beds", tags=["admin", "reading-beds"])

logger = log_mgr.logger


DEFAULT_BUNDLED_BED_ID = "lost-in-the-pages"
DEFAULT_BUNDLED_BED_LABEL = "Lost in the Pages"
DEFAULT_BUNDLED_BED_URL = "/assets/reading-beds/lost-in-the-pages.mp3"
READING_BED_UNAVAILABLE_MESSAGE = "Unable to sync reading beds."


def _require_admin(authorization: str | None, auth_service: AuthService) -> None:
    require_admin_user(authorization, auth_service)


def _reading_bed_result_from_http_error(exc: HTTPException) -> str:
    if exc.status_code == status.HTTP_400_BAD_REQUEST:
        return "invalid"
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return "unauthorized"
    if exc.status_code == status.HTTP_403_FORBIDDEN:
        return "forbidden"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        return "not_found"
    return "error"


def _log_reading_bed_route_result(
    *,
    operation: str,
    result: str,
    started_at: float,
    beds: int | None = None,
    bytes_written: int | None = None,
    deleted: bool | None = None,
    default_changed: bool | None = None,
    bundled: bool | None = None,
    uploaded: bool | None = None,
) -> None:
    log_started_route_result(
        logger,
        metric_name="READING_BED_ROUTE_DURATION",
        message="Reading bed route",
        operation=operation,
        result=result,
        started_at=started_at,
        success_results=frozenset(),
        duration_precision=2,
        log_extra={
            "event": "reading_beds.route",
            "operation": operation,
            "result": result,
        },
        beds=max(0, beds) if beds is not None else None,
        bytes=max(0, bytes_written) if bytes_written is not None else None,
        deleted=deleted,
        default_changed=default_changed,
        bundled=bundled,
        uploaded=uploaded,
    )


def _raise_reading_bed_unavailable(
    *,
    operation: str,
    started_at: float,
) -> None:
    _log_reading_bed_route_result(
        operation=operation,
        result="error",
        started_at=started_at,
    )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=READING_BED_UNAVAILABLE_MESSAGE,
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_identifier(value: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    raw = (value or "").strip().lower()
    if not raw:
        return "bed"
    normalized = []
    last_was_dash = False
    for ch in raw:
        if ch in allowed:
            normalized.append(ch)
            last_was_dash = False
        elif ch.isspace() or ch in {".", ",", ":", ";", "/", "\\", "|"}:
            if not last_was_dash and normalized:
                normalized.append("-")
                last_was_dash = True
        else:
            if not last_was_dash and normalized:
                normalized.append("-")
                last_was_dash = True
    result = "".join(normalized).strip("-_")
    return result or "bed"

def _looks_like_mp3(filename: str | None, content_type: str | None) -> bool:
    name = (filename or "").strip().lower()
    ctype = (content_type or "").strip().lower()
    if name.endswith(".mp3"):
        return True
    if ctype in {"audio/mpeg", "audio/mp3", "audio/mpeg3"}:
        return True
    if ctype.startswith("audio/") and ("mpeg" in ctype or "mp3" in ctype):
        return True
    if ctype in {"application/octet-stream", ""}:
        return True
    return False


def _reading_beds_root(file_locator: FileLocator) -> Path:
    return file_locator.storage_root / "reading_beds"


def _manifest_path(root: Path) -> Path:
    return root / "manifest.json"


def _files_root(root: Path) -> Path:
    return root / "files"


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def _ensure_manifest(file_locator: FileLocator) -> Tuple[Path, Dict[str, Any]]:
    root = _reading_beds_root(file_locator)
    root.mkdir(parents=True, exist_ok=True)
    _files_root(root).mkdir(parents=True, exist_ok=True)

    manifest_path = _manifest_path(root)
    if manifest_path.exists():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
    else:
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    beds = payload.get("beds")
    if not isinstance(beds, list):
        beds = []

    if not beds:
        beds.insert(
            0,
            {
                "id": DEFAULT_BUNDLED_BED_ID,
                "label": DEFAULT_BUNDLED_BED_LABEL,
                "kind": "bundled",
                "bundled_url": DEFAULT_BUNDLED_BED_URL,
                "content_type": "audio/mpeg",
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
            },
        )

    payload["version"] = 1
    payload["beds"] = beds

    default_id = payload.get("default_id")
    if not isinstance(default_id, str) or not default_id.strip():
        payload["default_id"] = DEFAULT_BUNDLED_BED_ID

    _atomic_write_json(manifest_path, payload)
    return manifest_path, payload


def _iter_beds(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    beds = payload.get("beds")
    if not isinstance(beds, list):
        return []
    return [entry for entry in beds if isinstance(entry, dict)]


def _find_bed(payload: Dict[str, Any], bed_id: str) -> Dict[str, Any] | None:
    bed_id = (bed_id or "").strip()
    if not bed_id:
        return None
    for entry in _iter_beds(payload):
        if entry.get("id") == bed_id:
            return entry
    return None


def _resolve_bundled_file(entry: Dict[str, Any], bed_id: str) -> Path | None:
    """Resolve a bundled reading bed to a local file path.

    Searches multiple locations to handle both local dev and Docker deployments.
    """
    bundled_url = entry.get("bundled_url")
    if not isinstance(bundled_url, str) or not bundled_url.strip():
        bundled_url = DEFAULT_BUNDLED_BED_URL
    # Extract filename from the URL path (e.g., "/assets/reading-beds/foo.mp3" -> "foo.mp3")
    filename = Path(bundled_url.strip()).name
    if not filename:
        return None
    project_root = Path(__file__).resolve().parents[3]
    search_dirs = [
        # Local dev: web/public and web/dist
        project_root / "web" / "public" / "assets" / "reading-beds",
        project_root / "web" / "dist" / "assets" / "reading-beds",
        # Docker / storage: bundled beds copied to storage
        FileLocator().storage_root / "reading_beds" / "bundled",
    ]
    for assets_dir in search_dirs:
        candidate = (assets_dir / filename).resolve()
        if candidate.exists():
            return candidate
    return None


def _bed_url(entry: Dict[str, Any], bed_id: str) -> str:
    kind = entry.get("kind")
    if kind == "bundled":
        url = entry.get("bundled_url")
        if isinstance(url, str) and url.strip():
            return url.strip()
        return DEFAULT_BUNDLED_BED_URL
    return f"/api/reading-beds/{bed_id}/file"


def _serialize_catalog(payload: Dict[str, Any]) -> ReadingBedListResponse:
    default_id = payload.get("default_id")
    if not isinstance(default_id, str):
        default_id = None
    default_id = default_id.strip() if default_id else None
    entries: list[ReadingBedEntry] = []
    for entry in _iter_beds(payload):
        bed_id = entry.get("id")
        if not isinstance(bed_id, str) or not bed_id.strip():
            continue
        label = entry.get("label")
        label_value = label.strip() if isinstance(label, str) and label.strip() else bed_id
        kind_value = entry.get("kind") if entry.get("kind") in {"bundled", "uploaded"} else "uploaded"
        content_type = entry.get("content_type")
        content_type_value = content_type.strip() if isinstance(content_type, str) and content_type.strip() else None
        entries.append(
            ReadingBedEntry(
                id=bed_id,
                label=label_value,
                url=_bed_url(entry, bed_id),
                kind=kind_value,  # type: ignore[arg-type]
                content_type=content_type_value,
                is_default=bool(default_id and bed_id == default_id),
            )
        )
    if default_id and not any(entry.id == default_id for entry in entries):
        default_id = entries[0].id if entries else None
    return ReadingBedListResponse(default_id=default_id, beds=entries)


@router.get("", response_model=ReadingBedListResponse)
def list_reading_beds() -> ReadingBedListResponse:
    started_at = time.perf_counter()
    try:
        _, payload = _ensure_manifest(FileLocator())
        catalog = _serialize_catalog(payload)
    except Exception:
        _raise_reading_bed_unavailable(operation="list", started_at=started_at)
    _log_reading_bed_route_result(
        operation="list",
        result="success",
        started_at=started_at,
        beds=len(catalog.beds),
    )
    return catalog


@router.get("/{bed_id}/file")
def fetch_reading_bed_file(bed_id: str) -> Response:
    started_at = time.perf_counter()
    try:
        file_locator = FileLocator()
        _, payload = _ensure_manifest(file_locator)
        entry = _find_bed(payload, bed_id)
        if entry is None:
            logger.info(
                "Reading bed fetch result=not_found",
                extra={"event": "reading_beds.fetch.not_found"},
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading bed not found")

        kind = entry.get("kind")
        if kind == "bundled":
            # Serve bundled reading bed files directly instead of redirecting to
            # /assets/ which is only available through the frontend Nginx container.
            bundled_file = _resolve_bundled_file(entry, bed_id)
            if bundled_file and bundled_file.exists():
                content_type = entry.get("content_type")
                media_type = (
                    content_type.strip()
                    if isinstance(content_type, str) and content_type.strip()
                    else "audio/mpeg"
                )
                _log_reading_bed_route_result(
                    operation="fetch",
                    result="success",
                    started_at=started_at,
                    bundled=True,
                )
                return FileResponse(path=bundled_file, media_type=media_type, filename=bundled_file.name)
            # Fallback to redirect (works when frontend serves static assets on same origin)
            url = _bed_url(entry, bed_id)
            _log_reading_bed_route_result(
                operation="fetch",
                result="success",
                started_at=started_at,
                bundled=True,
            )
            return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

        filename = entry.get("filename")
        if not isinstance(filename, str) or not filename.strip():
            logger.warning(
                "Reading bed fetch result=missing_file",
                extra={"event": "reading_beds.fetch.missing_file"},
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading bed file missing")

        root = _reading_beds_root(file_locator)
        candidate = (root / filename).resolve()
        if root.resolve() not in candidate.parents and candidate != root.resolve():
            logger.warning(
                "Reading bed fetch result=invalid_path",
                extra={"event": "reading_beds.fetch.invalid_path"},
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reading bed file path")
        if not candidate.exists():
            logger.warning(
                "Reading bed fetch result=file_not_found",
                extra={"event": "reading_beds.fetch.file_not_found"},
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading bed file missing")

        content_type = entry.get("content_type")
        media_type = content_type.strip() if isinstance(content_type, str) and content_type.strip() else "audio/mpeg"
        _log_reading_bed_route_result(
            operation="fetch",
            result="success",
            started_at=started_at,
            uploaded=True,
        )
        return FileResponse(path=candidate, media_type=media_type, filename=candidate.name)
    except HTTPException as exc:
        result = _reading_bed_result_from_http_error(exc)
        _log_reading_bed_route_result(
            operation="fetch",
            result=result,
            started_at=started_at,
        )
        raise
    except Exception:
        _raise_reading_bed_unavailable(operation="fetch", started_at=started_at)


@admin_router.post("", response_model=ReadingBedEntry, status_code=status.HTTP_201_CREATED)
def upload_reading_bed(
    file: UploadFile = File(...),
    label: str | None = Form(default=None),
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> ReadingBedEntry:
    started_at = time.perf_counter()
    size_bytes = 0
    try:
        _require_admin(authorization, auth_service)

        file_locator = FileLocator()
        manifest_path, payload = _ensure_manifest(file_locator)

        original_name = (file.filename or "").strip()
        requested_label = (label or "").strip()
        display_label = requested_label or (Path(original_name).stem.strip() if original_name else "") or "Reading bed"

        if not _looks_like_mp3(file.filename, file.content_type):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only MP3 uploads are supported")

        base_id = _sanitize_identifier(display_label)
        existing_ids = {entry.get("id") for entry in _iter_beds(payload) if isinstance(entry.get("id"), str)}
        bed_id = base_id
        suffix = 2
        while bed_id in existing_ids:
            bed_id = f"{base_id}-{suffix}"
            suffix += 1

        root = _reading_beds_root(file_locator)
        files_root = _files_root(root)
        files_root.mkdir(parents=True, exist_ok=True)

        dest = (files_root / f"{bed_id}.mp3").resolve()
        if files_root.resolve() not in dest.parents and dest != files_root.resolve():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file destination")

        try:
            try:
                file.file.seek(0)
            except Exception:
                pass
            with dest.open("wb") as handle:
                shutil.copyfileobj(file.file, handle)
            size_bytes = dest.stat().st_size
            if size_bytes <= 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file was empty")
        finally:
            try:
                file.file.close()
            except Exception:
                pass

        size_bytes = dest.stat().st_size if dest.exists() else 0

        beds = list(_iter_beds(payload))
        beds.append(
            {
                "id": bed_id,
                "label": display_label,
                "kind": "uploaded",
                "filename": f"files/{dest.name}",
                "content_type": "audio/mpeg",
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
            }
        )
        payload["beds"] = beds

        default_id = payload.get("default_id")
        if not isinstance(default_id, str) or not default_id.strip():
            payload["default_id"] = bed_id

        _atomic_write_json(manifest_path, payload)
        refreshed = _ensure_manifest(file_locator)[1]
        catalog = _serialize_catalog(refreshed)
        entry = next((item for item in catalog.beds if item.id == bed_id), None)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to register reading bed")
    except HTTPException as exc:
        result = _reading_bed_result_from_http_error(exc)
        _log_reading_bed_route_result(
            operation="upload",
            result=result,
            started_at=started_at,
        )
        raise
    except Exception:
        _raise_reading_bed_unavailable(operation="upload", started_at=started_at)
    _log_reading_bed_route_result(
        operation="upload",
        result="success",
        started_at=started_at,
        beds=len(catalog.beds),
        bytes_written=size_bytes,
    )
    return entry


@admin_router.patch("/{bed_id}", response_model=ReadingBedEntry)
def update_reading_bed(
    bed_id: str,
    payload_update: ReadingBedUpdateRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> ReadingBedEntry:
    started_at = time.perf_counter()
    default_changed = False
    try:
        _require_admin(authorization, auth_service)

        file_locator = FileLocator()
        manifest_path, payload = _ensure_manifest(file_locator)
        entry = _find_bed(payload, bed_id)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading bed not found")

        updated = False
        if payload_update.label is not None:
            label_value = payload_update.label.strip()
            entry["label"] = label_value or bed_id
            updated = True

        if payload_update.set_default is True:
            payload["default_id"] = bed_id
            updated = True
            default_changed = True

        if updated:
            entry["updated_at"] = _now_iso()
            _atomic_write_json(manifest_path, payload)

        refreshed = _ensure_manifest(file_locator)[1]
        catalog = _serialize_catalog(refreshed)
        resolved = next((item for item in catalog.beds if item.id == bed_id), None)
        if resolved is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to update reading bed")
    except HTTPException as exc:
        result = _reading_bed_result_from_http_error(exc)
        _log_reading_bed_route_result(
            operation="update",
            result=result,
            started_at=started_at,
        )
        raise
    except Exception:
        _raise_reading_bed_unavailable(operation="update", started_at=started_at)
    _log_reading_bed_route_result(
        operation="update",
        result="success",
        started_at=started_at,
        default_changed=default_changed,
    )
    return resolved


@admin_router.delete("/{bed_id}", response_model=ReadingBedDeleteResponse)
def delete_reading_bed(
    bed_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> ReadingBedDeleteResponse:
    started_at = time.perf_counter()
    try:
        _require_admin(authorization, auth_service)

        file_locator = FileLocator()
        manifest_path, payload = _ensure_manifest(file_locator)
        beds = list(_iter_beds(payload))
        remaining: list[Dict[str, Any]] = []
        deleted_entry: Dict[str, Any] | None = None
        for entry in beds:
            if entry.get("id") == bed_id:
                deleted_entry = entry
                continue
            remaining.append(entry)

        if deleted_entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading bed not found")

        if not remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one reading bed must remain available",
            )

        payload["beds"] = remaining
        default_id = payload.get("default_id")
        if isinstance(default_id, str) and default_id == bed_id:
            payload["default_id"] = remaining[0].get("id") or DEFAULT_BUNDLED_BED_ID

        _atomic_write_json(manifest_path, payload)

        if deleted_entry.get("kind") == "uploaded":
            filename = deleted_entry.get("filename")
            if isinstance(filename, str) and filename.strip():
                root = _reading_beds_root(file_locator)
                candidate = (root / filename).resolve()
                try:
                    if candidate.exists():
                        candidate.unlink()
                except Exception:
                    pass

        refreshed = _ensure_manifest(file_locator)[1]
        catalog = _serialize_catalog(refreshed)
        response = ReadingBedDeleteResponse(deleted=True, default_id=catalog.default_id)
    except HTTPException as exc:
        result = _reading_bed_result_from_http_error(exc)
        _log_reading_bed_route_result(
            operation="delete",
            result=result,
            started_at=started_at,
        )
        raise
    except Exception:
        _raise_reading_bed_unavailable(operation="delete", started_at=started_at)
    _log_reading_bed_route_result(
        operation="delete",
        result="success",
        started_at=started_at,
        beds=len(catalog.beds),
        deleted=response.deleted,
    )
    return response
