"""User management utilities for the ebook-tools CLI."""

from __future__ import annotations

import getpass
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .. import logging_manager as log_mgr
from ..user_management import AuthService, LocalUserStore, SessionManager

USER_STORE_ENV = "EBOOKTOOLS_USER_STORE"
SESSION_FILE_ENV = "EBOOKTOOLS_SESSION_FILE"
ACTIVE_SESSION_ENV = "EBOOKTOOLS_ACTIVE_SESSION_FILE"
SESSION_TOKEN_ENV = "EBOOKTOOLS_SESSION_TOKEN"

logger = log_mgr.get_logger()


class SessionRequirementError(RuntimeError):
    """Raised when a CLI command requires an authenticated session."""


@dataclass
class ActiveSessionStore:
    """Persist the active session token for CLI commands."""

    path: Path

    def __post_init__(self) -> None:  # pragma: no cover - trivial
        self.path = self.path.expanduser()

    def _ensure_parent(self) -> None:
        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def store(self, token: str) -> None:
        self._ensure_parent()
        self.path.write_text(token.strip() + "\n", encoding="utf-8")

    def load(self) -> Optional[str]:
        try:
            data = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        token = data.strip()
        return token or None

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:  # pragma: no cover - already absent
            return


def _resolve_path(value: Optional[str], env_var: str, default: Optional[Path]) -> Optional[Path]:
    if value:
        return Path(value).expanduser()
    env_value = os.environ.get(env_var)
    if env_value:
        return Path(env_value).expanduser()
    return default


def _create_auth_service(
    *, user_store_path: Optional[Path] = None, session_file: Optional[Path] = None
) -> AuthService:
    user_store = LocalUserStore(storage_path=user_store_path)
    session_manager = SessionManager(session_file=session_file)
    return AuthService(user_store, session_manager)


def _active_session_store(path: Optional[Path] = None) -> ActiveSessionStore:
    default_path = Path(os.path.expanduser("~/.ebooktools_active_session"))
    resolved = path or _resolve_path(None, ACTIVE_SESSION_ENV, default_path)
    assert resolved is not None
    return ActiveSessionStore(resolved)


def _roles_display(roles: Iterable[str]) -> str:
    collected = list(roles)
    if not collected:
        return "(no roles)"
    return ", ".join(sorted(collected))


def _prompt_password(username: str) -> str:
    return getpass.getpass(f"Password for {username}: ")


def ensure_active_session(
    *,
    user_store_path: Optional[Path] = None,
    session_file: Optional[Path] = None,
    active_session_path: Optional[Path] = None,
) -> str:
    """Return the active session token, raising if authentication is missing."""

    token = os.environ.get(SESSION_TOKEN_ENV)
    resolved_user_store = user_store_path or _resolve_path(None, USER_STORE_ENV, None)
    resolved_session_file = session_file or _resolve_path(None, SESSION_FILE_ENV, None)
    resolved_active_path = active_session_path or _resolve_path(None, ACTIVE_SESSION_ENV, None)
    auth_service = _create_auth_service(
        user_store_path=resolved_user_store, session_file=resolved_session_file
    )

    if token:
        if auth_service.authenticate(token) is None:
            raise SessionRequirementError(
                "The session token in EBOOKTOOLS_SESSION_TOKEN is invalid. Please log in again."
            )
        return token

    store = _active_session_store(resolved_active_path)
    token = store.load()
    if not token:
        raise SessionRequirementError(
            "No active session found. Please log in using 'ebook-tools user login'."
        )

    if auth_service.authenticate(token) is None:
        raise SessionRequirementError(
            "The active session is invalid or has expired. Please log in again."
        )

    return token


def execute_user_command(args) -> int:
    """Dispatch the ``ebook-tools user`` sub-commands."""

    user_store_path = _resolve_path(getattr(args, "user_store", None), USER_STORE_ENV, None)
    session_file = _resolve_path(getattr(args, "session_file", None), SESSION_FILE_ENV, None)
    active_session_path = _resolve_path(
        getattr(args, "active_session_file", None), ACTIVE_SESSION_ENV, None
    )

    auth_service = _create_auth_service(
        user_store_path=user_store_path, session_file=session_file
    )
    active_store = _active_session_store(active_session_path)

    command = getattr(args, "user_command", None)
    if command == "add":
        password = getattr(args, "password", None) or _prompt_password(args.username)
        roles: Iterable[str] = getattr(args, "roles", []) or []
        try:
            record = auth_service.user_store.create_user(
                args.username, password, roles=roles
            )
        except ValueError as exc:
            log_mgr.console_error(str(exc), logger_obj=logger)
            return 1
        log_mgr.console_info(
            "Created user '%s' with roles: %s", record.username, _roles_display(record.roles), logger_obj=logger
        )
        return 0

    if command == "list":
        users = auth_service.user_store.list_users()
        if not users:
            log_mgr.console_info("No users registered.", logger_obj=logger)
            return 0
        log_mgr.console_info("Registered users:", logger_obj=logger)
        for record in sorted(users, key=lambda item: item.username):
            log_mgr.console_info(
                " - %s (%s)", record.username, _roles_display(record.roles), logger_obj=logger
            )
        return 0

    if command == "login":
        password = getattr(args, "password", None) or _prompt_password(args.username)
        try:
            token = auth_service.login(args.username, password)
        except ValueError as exc:
            log_mgr.console_error(str(exc), logger_obj=logger)
            return 1
        active_store.store(token)
        log_mgr.console_info(
            "Login successful for '%s'.", args.username, logger_obj=logger
        )
        log_mgr.console_info(
            "Session token saved to %s.", active_store.path, logger_obj=logger
        )
        log_mgr.console_info("Token: %s", token, logger_obj=logger)
        return 0

    if command == "logout":
        explicit_token = getattr(args, "token", None) or os.environ.get(SESSION_TOKEN_ENV)
        token = explicit_token or active_store.load()
        if not token:
            log_mgr.console_error(
                "No session token provided and no active session recorded.",
                logger_obj=logger,
            )
            return 1
        if auth_service.logout(token):
            if active_store.load() == token:
                active_store.clear()
            log_mgr.console_info("Session logged out successfully.", logger_obj=logger)
            return 0
        log_mgr.console_warning(
            "Session token not found; it may have already been logged out.",
            logger_obj=logger,
        )
        if explicit_token:
            return 1
        active_store.clear()
        return 0

    log_mgr.console_error("Unknown user command: %s", command, logger_obj=logger)
    return 1


__all__ = [
    "ACTIVE_SESSION_ENV",
    "ActiveSessionStore",
    "SESSION_FILE_ENV",
    "SESSION_TOKEN_ENV",
    "SessionRequirementError",
    "USER_STORE_ENV",
    "ensure_active_session",
    "execute_user_command",
]
