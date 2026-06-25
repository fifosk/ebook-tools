from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException, status

from modules.webapi.dependencies import RequestUserContext
from modules.webapi.routes.media import lookup_cache

pytestmark = pytest.mark.webapi


def test_lookup_cache_resolution_preserves_forbidden(monkeypatch) -> None:
    def _raise_forbidden(**_kwargs: object) -> Path:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not allowed")

    monkeypatch.setattr(lookup_cache, "_resolve_job_root", _raise_forbidden)

    with pytest.raises(HTTPException) as exc_info:
        lookup_cache._load_cache_for_job(
            "job-private",
            locator=object(),
            library_repository=object(),
            request_user=RequestUserContext(user_id="reader", user_role="viewer"),
            job_manager=object(),
        )

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


def test_lookup_cache_resolution_keeps_missing_as_cache_miss(monkeypatch) -> None:
    def _raise_not_found(**_kwargs: object) -> Path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="missing")

    monkeypatch.setattr(lookup_cache, "_resolve_job_root", _raise_not_found)

    assert (
        lookup_cache._load_cache_for_job(
            "job-missing",
            locator=object(),
            library_repository=object(),
            request_user=RequestUserContext(user_id="reader", user_role="viewer"),
            job_manager=object(),
        )
        is None
    )
