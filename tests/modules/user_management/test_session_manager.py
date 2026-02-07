from pathlib import Path

from modules.user_management.session_manager import SessionManager

import pytest

pytestmark = pytest.mark.auth


def test_create_and_retrieve_session(tmp_path):
    session_file = tmp_path / "sessions.json"
    manager = SessionManager(session_file)

    token = manager.create_session("alice")
    stored = manager.get_session(token)

    assert stored is not None
    assert stored["username"] == "alice"
    assert manager.get_username(token) == "alice"


def test_delete_and_clear_sessions(tmp_path):
    session_file = tmp_path / "sessions.json"
    manager = SessionManager(session_file)

    token1 = manager.create_session("bob")
    token2 = manager.create_session("bob")
    token3 = manager.create_session("carol")

    assert manager.delete_session(token1) is True
    assert manager.get_session(token1) is None

    cleared = manager.clear_sessions_for_user("bob")
    assert cleared == 1
    assert manager.get_session(token2) is None
    assert manager.get_session(token3) is not None
