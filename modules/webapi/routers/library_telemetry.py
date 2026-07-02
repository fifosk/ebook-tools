"""Telemetry helpers for Library API routes."""

from __future__ import annotations

from ..route_telemetry import log_started_route_result
from ... import logging_manager


LOGGER = logging_manager.get_logger().getChild("webapi.library")


def _log_library_route_result(
    *,
    message: str,
    operation: str,
    result: str,
    started_at: float,
    include_operation: bool = False,
    **fields: str | int | bool | None,
) -> None:
    rendered_fields = {
        key: str(value) if isinstance(value, bool) else value
        for key, value in fields.items()
    }
    log_started_route_result(
        LOGGER,
        metric_name="LIBRARY_ROUTE_DURATION",
        message=message,
        operation=operation,
        result=result,
        started_at=started_at,
        include_operation=include_operation,
        duration_first=False,
        **rendered_fields,
    )


def _log_library_source_upload(
    *,
    result: str,
    started_at: float,
    has_filename: bool | None = None,
) -> None:
    _log_library_route_result(
        message="Library source upload",
        operation="source_upload",
        result=result,
        started_at=started_at,
        has_filename=has_filename,
    )


def _log_library_metadata_update(
    *,
    result: str,
    started_at: float,
    edited_fields: int | None = None,
) -> None:
    _log_library_route_result(
        message="Library metadata update",
        operation="metadata_update",
        result=result,
        started_at=started_at,
        edited_fields=edited_fields,
    )


def _log_library_isbn_apply(
    *,
    result: str,
    started_at: float,
    has_isbn: bool | None = None,
) -> None:
    _log_library_route_result(
        message="Library ISBN apply",
        operation="isbn_apply",
        result=result,
        started_at=started_at,
        has_isbn=has_isbn,
    )


def _log_library_metadata_enrich(
    *,
    result: str,
    started_at: float,
    force: bool | None = None,
) -> None:
    _log_library_route_result(
        message="Library metadata enrich",
        operation="metadata_enrich",
        result=result,
        started_at=started_at,
        force=force,
    )


def _log_library_metadata_refresh(
    *,
    result: str,
    started_at: float,
    enrich_requested: bool | None = None,
) -> None:
    _log_library_route_result(
        message="Library metadata refresh",
        operation="metadata_refresh",
        result=result,
        started_at=started_at,
        enrich_requested=enrich_requested,
    )


def _log_library_move_entry(
    *,
    result: str,
    started_at: float,
    status_override_present: bool | None = None,
) -> None:
    _log_library_route_result(
        message="Library entry move",
        operation="move_entry",
        result=result,
        started_at=started_at,
        status_override_present=status_override_present,
    )


def _log_library_media_remove(
    *,
    result: str,
    started_at: float,
    location: str | None = None,
    removed_count: int | None = None,
) -> None:
    _log_library_route_result(
        message="Library media remove",
        operation="remove_media",
        result=result,
        started_at=started_at,
        location=location,
        removed_count=removed_count,
    )


def _log_library_media_file_resolve(
    *,
    result: str,
    started_at: float,
    has_range: bool | None = None,
) -> None:
    _log_library_route_result(
        message="Library media file resolve",
        operation="media_file",
        result=result,
        started_at=started_at,
        has_range=has_range,
    )


def _log_library_access_policy(
    *,
    operation: str,
    result: str,
    started_at: float,
    visibility_present: bool | None = None,
    grant_count: int | None = None,
) -> None:
    _log_library_route_result(
        message="Library access policy",
        operation=operation,
        result=result,
        started_at=started_at,
        include_operation=True,
        visibility_present=visibility_present,
        grant_count=grant_count,
    )


def _log_library_reindex(
    *,
    result: str,
    started_at: float,
    indexed_count: int | None = None,
) -> None:
    _log_library_route_result(
        message="Library reindex",
        operation="reindex",
        result=result,
        started_at=started_at,
        indexed_count=indexed_count,
    )


def _log_library_remove_entry(
    *,
    result: str,
    started_at: float,
) -> None:
    _log_library_route_result(
        message="Library entry remove",
        operation="remove_entry",
        result=result,
        started_at=started_at,
    )


__all__ = [
    "_log_library_access_policy",
    "_log_library_isbn_apply",
    "_log_library_media_file_resolve",
    "_log_library_media_remove",
    "_log_library_metadata_enrich",
    "_log_library_metadata_refresh",
    "_log_library_metadata_update",
    "_log_library_move_entry",
    "_log_library_reindex",
    "_log_library_remove_entry",
    "_log_library_route_result",
    "_log_library_source_upload",
]
