"""Base abstractions for user persistence layers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class UserRecord:
    """Representation of an authenticated user.

    Attributes:
        username: Unique identifier for the user.
        password_hash: The hashed password string for credential validation.
        roles: A collection of role identifiers assigned to the user.
        metadata: Arbitrary key/value metadata associated with the user.
    """

    username: str
    password_hash: str
    roles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the record into a JSON-compatible dictionary."""
        return {
            "username": self.username,
            "password_hash": self.password_hash,
            "roles": list(self.roles),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "UserRecord":
        """Rehydrate a :class:`UserRecord` from a persisted dictionary."""
        return cls(
            username=payload["username"],
            password_hash=payload["password_hash"],
            roles=list(payload.get("roles", [])),
            metadata=dict(payload.get("metadata", {})),
        )


class UserStoreBase(ABC):
    """Abstract base class for user store implementations."""

    @abstractmethod
    def create_user(
        self,
        username: str,
        password: str,
        roles: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserRecord:
        """Create a new user in the store."""

    @abstractmethod
    def get_user(self, username: str) -> Optional[UserRecord]:
        """Retrieve a user record by username."""

    @abstractmethod
    def update_user(
        self,
        username: str,
        password: Optional[str] = None,
        roles: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserRecord:
        """Update user attributes and return the updated record."""

    @abstractmethod
    def delete_user(self, username: str) -> bool:
        """Remove a user from the store."""

    @abstractmethod
    def list_users(self) -> List[UserRecord]:
        """Return all user records managed by the store."""

    @abstractmethod
    def verify_credentials(self, username: str, password: str) -> bool:
        """Validate credentials for a user."""
