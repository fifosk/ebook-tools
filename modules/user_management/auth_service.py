"""Authentication utilities built on top of the user store."""
from __future__ import annotations

from functools import wraps
from typing import Callable, Optional

from .session_manager import SessionManager
from .user_store_base import UserRecord, UserStoreBase


class AuthService:
    """Coordinate authentication, sessions, and authorisation checks."""

    def __init__(self, user_store: UserStoreBase, session_manager: Optional[SessionManager] = None) -> None:
        self._user_store = user_store
        self._session_manager = session_manager or SessionManager()

    # ------------------------------------------------------------------
    # Authentication helpers
    # ------------------------------------------------------------------
    def login(self, username: str, password: str) -> str:
        """Validate user credentials and create a session token."""
        if not self._user_store.verify_credentials(username, password):
            raise ValueError("Invalid username or password")
        return self._session_manager.create_session(username)

    def logout(self, session_token: str) -> bool:
        """Terminate a session token if present."""
        return self._session_manager.delete_session(session_token)

    def authenticate(self, session_token: str) -> Optional[UserRecord]:
        """Resolve a session token into the associated user record."""
        username = self._session_manager.get_username(session_token)
        if not username:
            return None
        return self._user_store.get_user(username)

    # ------------------------------------------------------------------
    # Authorisation helpers
    # ------------------------------------------------------------------
    def user_has_role(self, username: str, role: str) -> bool:
        user = self._user_store.get_user(username)
        return bool(user and role in user.roles)

    def session_has_role(self, session_token: str, role: str) -> bool:
        user = self.authenticate(session_token)
        return bool(user and role in user.roles)

    def require_role(self, *roles: str) -> Callable:
        """Decorator enforcing that the caller has at least one of the roles."""
        if not roles:
            raise ValueError("At least one role must be specified")

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                token = kwargs.get("session_token")
                if token is None:
                    raise PermissionError("A session_token keyword argument is required")
                user = self.authenticate(token)
                if user is None:
                    raise PermissionError("Invalid session token")
                if not any(role in user.roles for role in roles):
                    raise PermissionError("Insufficient permissions")
                kwargs.setdefault("user", user)
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def require_authenticated(self) -> Callable:
        """Decorator ensuring that a valid session token is supplied."""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                token = kwargs.get("session_token")
                if token is None:
                    raise PermissionError("A session_token keyword argument is required")
                user = self.authenticate(token)
                if user is None:
                    raise PermissionError("Invalid session token")
                kwargs.setdefault("user", user)
                return func(*args, **kwargs)

            return wrapper

        return decorator

    @property
    def session_manager(self) -> SessionManager:
        return self._session_manager

    @property
    def user_store(self) -> UserStoreBase:
        return self._user_store
