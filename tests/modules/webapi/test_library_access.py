from __future__ import annotations

import pytest
from fastapi import HTTPException

from modules.library import LibraryEntry, MetadataSnapshot
from modules.webapi.dependencies import RequestUserContext
from modules.webapi.routers.library_access import (
    ensure_library_access,
    library_owner_id,
    resolve_library_access,
)

pytestmark = pytest.mark.webapi


def _entry(
    *,
    owner_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> LibraryEntry:
    return LibraryEntry(
        id="library-job",
        author="Author",
        book_title="Book",
        genre=None,
        language="English",
        status="finished",
        created_at="2026-07-03T00:00:00Z",
        updated_at="2026-07-03T00:00:00Z",
        library_path="/tmp/library-job",
        owner_id=owner_id,
        metadata=MetadataSnapshot(metadata=metadata or {}),
    )


def test_library_owner_id_prefers_entry_owner_before_metadata() -> None:
    item = _entry(
        owner_id="entry-owner",
        metadata={"owner_id": "metadata-owner", "user_id": "metadata-user"},
    )

    assert library_owner_id(item) == "entry-owner"


def test_library_owner_id_falls_back_to_metadata_owner() -> None:
    assert library_owner_id(_entry(metadata={"user_id": "  metadata-user  "})) == "metadata-user"
    assert library_owner_id(_entry(metadata={"owner_id": "metadata-owner"})) == "metadata-owner"
    assert library_owner_id(_entry(metadata={"owner_id": "   "})) is None


def test_default_library_access_policy_is_public_for_viewing() -> None:
    item = _entry()
    policy = resolve_library_access(item)

    assert policy.visibility == "public"
    ensure_library_access(
        item,
        RequestUserContext(user_id=None, user_role=None),
        permission="view",
    )


def test_library_owner_can_edit_when_owner_is_stored_in_metadata() -> None:
    ensure_library_access(
        _entry(metadata={"owner_id": "owner-1", "access": {"visibility": "private"}}),
        RequestUserContext(user_id="owner-1", user_role=None),
        permission="edit",
    )


def test_library_access_denial_messages_match_route_contract() -> None:
    item = _entry(metadata={"access": {"visibility": "private"}})

    with pytest.raises(HTTPException) as view_exc:
        ensure_library_access(
            item,
            RequestUserContext(user_id="user-2", user_role="viewer"),
            permission="view",
        )
    assert view_exc.value.status_code == 403
    assert view_exc.value.detail == "Not authorized to access library item"

    with pytest.raises(HTTPException) as edit_exc:
        ensure_library_access(
            item,
            RequestUserContext(user_id="user-2", user_role="viewer"),
            permission="edit",
        )
    assert edit_exc.value.status_code == 403
    assert edit_exc.value.detail == "Not authorized to modify library item"
