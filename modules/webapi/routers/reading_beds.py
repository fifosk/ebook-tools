"""Reading bed (background music) catalog and administration routes."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse, Response

from modules import logging_manager as log_mgr
from modules.services.file_locator import FileLocator
from modules.user_management import AuthService

from ..dependencies import get_auth_service
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


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token.strip() or None
    return authorization.strip() or None


def _require_admin(authorization: str | None, auth_service: AuthService) -> None:
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session token")
    record = auth_service.authenticate(token)
    if record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")
    if "admin" not in (record.roles or []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")


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
    _, payload = _ensure_manifest(FileLocator())
    return _serialize_catalog(payload)


@router.get("/{bed_id}/file")
def fetch_reading_bed_file(bed_id: str) -> Response:
    file_locator = FileLocator()
    _, payload = _ensure_manifest(file_locator)
    entry = _find_bed(payload, bed_id)
    if entry is None:
        logger.info(
            "Reading bed not found: %s",
            bed_id,
            extra={"event": "reading_beds.fetch.not_found", "bed_id": bed_id},
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading bed not found")

    kind = entry.get("kind")
    if kind == "bundled":
        url = _bed_url(entry, bed_id)
        return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    filename = entry.get("filename")
    if not isinstance(filename, str) or not filename.strip():
        logger.warning(
            "Reading bed file missing for %s",
            bed_id,
            extra={"event": "reading_beds.fetch.missing_file", "bed_id": bed_id},
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading bed file missing")

    root = _reading_beds_root(file_locator)
    candidate = (root / filename).resolve()
    if root.resolve() not in candidate.parents and candidate != root.resolve():
        logger.warning(
            "Invalid reading bed file path for %s: %s",
            bed_id,
            candidate,
            extra={"event": "reading_beds.fetch.invalid_path", "bed_id": bed_id},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reading bed file path")
    if not candidate.exists():
        logger.warning(
            "Reading bed file not found for %s: %s",
            bed_id,
            candidate,
            extra={"event": "reading_beds.fetch.file_not_found", "bed_id": bed_id},
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading bed file missing")

    content_type = entry.get("content_type")
    media_type = content_type.strip() if isinstance(content_type, str) and content_type.strip() else "audio/mpeg"
    return FileResponse(path=candidate, media_type=media_type, filename=candidate.name)


@admin_router.post("", response_model=ReadingBedEntry, status_code=status.HTTP_201_CREATED)
def upload_reading_bed(
    file: UploadFile = File(...),
    label: str | None = Form(default=None),
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> ReadingBedEntry:
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
    logger.info(
        "Uploaded reading bed %s (%s bytes) to %s",
        bed_id,
        size_bytes,
        dest,
        extra={
            "event": "reading_beds.upload.success",
            "bed_id": bed_id,
            "bytes": size_bytes,
            "path": os.fspath(dest),
        },
    )

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
    return entry


@admin_router.patch("/{bed_id}", response_model=ReadingBedEntry)
def update_reading_bed(
    bed_id: str,
    payload_update: ReadingBedUpdateRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> ReadingBedEntry:
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

    if updated:
        entry["updated_at"] = _now_iso()
        _atomic_write_json(manifest_path, payload)

    refreshed = _ensure_manifest(file_locator)[1]
    catalog = _serialize_catalog(refreshed)
    resolved = next((item for item in catalog.beds if item.id == bed_id), None)
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to update reading bed")
    return resolved


@admin_router.delete("/{bed_id}", response_model=ReadingBedDeleteResponse)
def delete_reading_bed(
    bed_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> ReadingBedDeleteResponse:
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
    return ReadingBedDeleteResponse(deleted=True, default_id=catalog.default_id)
