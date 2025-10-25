from pathlib import Path

import bcrypt
import pytest

from modules.user_management.local_user_store import LocalUserStore


def test_create_and_retrieve_user(tmp_path: Path):
    store_path = tmp_path / "users.json"
    store = LocalUserStore(store_path)

    store.create_user("alice", "password123", roles=["admin"], metadata={"team": "A"})
    user = store.get_user("alice")

    assert user is not None
    assert user.username == "alice"
    assert user.roles == ["admin"]
    assert user.metadata == {"team": "A"}
    assert bcrypt.checkpw(b"password123", user.password_hash.encode("utf-8"))


def test_update_user_password_and_roles(tmp_path: Path):
    store = LocalUserStore(tmp_path / "users.json")
    store.create_user("bob", "oldpass", roles=["user"])

    store.update_user("bob", password="newpass", roles=["editor"])
    user = store.get_user("bob")

    assert user is not None
    assert user.roles == ["editor"]
    assert bcrypt.checkpw(b"newpass", user.password_hash.encode("utf-8"))


def test_verify_credentials(tmp_path: Path):
    store = LocalUserStore(tmp_path / "users.json")
    store.create_user("carol", "secret")

    assert store.verify_credentials("carol", "secret")
    assert not store.verify_credentials("carol", "wrong")
    assert not store.verify_credentials("unknown", "secret")


def test_delete_and_list_users(tmp_path: Path):
    store = LocalUserStore(tmp_path / "users.json")
    store.create_user("dave", "pass1")
    store.create_user("eve", "pass2")

    users = store.list_users()
    assert sorted(u.username for u in users) == ["dave", "eve"]

    removed = store.delete_user("dave")
    assert removed is True
    assert store.get_user("dave") is None

    users = store.list_users()
    assert [u.username for u in users] == ["eve"]


def test_create_existing_user_raises(tmp_path: Path):
    store = LocalUserStore(tmp_path / "users.json")
    store.create_user("frank", "pass")

    with pytest.raises(ValueError):
        store.create_user("frank", "pass")


def test_update_missing_user_raises(tmp_path: Path):
    store = LocalUserStore(tmp_path / "users.json")

    with pytest.raises(KeyError):
        store.update_user("missing")
