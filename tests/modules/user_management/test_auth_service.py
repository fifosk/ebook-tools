import pytest

from modules.user_management.auth_service import AuthService
from modules.user_management.local_user_store import LocalUserStore
from modules.user_management.session_manager import SessionManager

pytestmark = pytest.mark.auth


def build_auth(tmp_path):
    store = LocalUserStore(tmp_path / "users.json")
    store.create_user("alice", "password", roles=["admin", "user"])
    store.create_user("bob", "password", roles=["user"])
    manager = SessionManager(tmp_path / "sessions.json")
    return AuthService(store, manager)


def test_successful_login_and_logout(tmp_path):
    auth = build_auth(tmp_path)

    token = auth.login("alice", "password")
    assert auth.session_has_role(token, "admin")

    assert auth.logout(token) is True
    assert not auth.session_has_role(token, "admin")


def test_login_failure(tmp_path):
    auth = build_auth(tmp_path)

    with pytest.raises(ValueError):
        auth.login("alice", "wrong")

    with pytest.raises(ValueError):
        auth.login("unknown", "password")


def test_require_role_decorator(tmp_path):
    auth = build_auth(tmp_path)
    token = auth.login("alice", "password")

    @auth.require_role("admin")
    def protected(*, session_token, user):
        return user.username

    assert protected(session_token=token) == "alice"

    with pytest.raises(PermissionError):
        protected(session_token="invalid")

    token_user = auth.login("bob", "password")
    with pytest.raises(PermissionError):
        protected(session_token=token_user)


def test_require_authenticated_decorator(tmp_path):
    auth = build_auth(tmp_path)
    token = auth.login("bob", "password")

    @auth.require_authenticated()
    def protected(*, session_token, user):
        return user.roles

    assert protected(session_token=token) == ["user"]

    with pytest.raises(PermissionError):
        protected(session_token="invalid")

    with pytest.raises(PermissionError):
        protected()
