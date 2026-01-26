"""SQLite-backed configuration repository with auditing and encryption.

This module provides persistent storage for configuration snapshots,
change auditing, and encrypted secrets management.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from base64 import urlsafe_b64decode, urlsafe_b64encode
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Tuple
from uuid import uuid4

from modules import logging_manager

logger = logging_manager.get_logger()

# Optional cryptography dependency for encryption
try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    Fernet = None
    InvalidToken = Exception

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
CONFIG_SECRET_ENV = "EBOOK_CONFIG_SECRET"
DEFAULT_CONFIG_DB_DIR = Path("config/.settings")


@dataclass
class SnapshotMetadata:
    """Metadata for a configuration snapshot."""

    snapshot_id: str
    label: Optional[str]
    description: Optional[str]
    created_by: Optional[str]
    created_at: str
    is_active: bool
    source: str
    config_hash: str


@dataclass
class AuditLogEntry:
    """Entry in the configuration audit log."""

    id: int
    timestamp: str
    username: Optional[str]
    action: str
    snapshot_id: Optional[str]
    group_name: Optional[str]
    key_name: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata: Optional[Dict[str, Any]]
    success: bool
    error_message: Optional[str]


class ConfigRepositoryError(RuntimeError):
    """Raised when configuration repository operations fail."""


class ConfigRepository:
    """SQLite-backed configuration persistence with auditing and encryption."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        encryption_key: Optional[str] = None,
    ) -> None:
        """Initialize the configuration repository.

        Args:
            db_path: Path to the SQLite database. Defaults to config/.settings/config.db
            encryption_key: Secret key for encrypting sensitive values.
                           Falls back to EBOOK_CONFIG_SECRET env var.
        """
        if db_path is None:
            db_path = DEFAULT_CONFIG_DB_DIR / "config.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize encryption
        self._encryption_key = encryption_key or os.environ.get(CONFIG_SECRET_ENV)
        self._fernet: Optional[Any] = None
        if ENCRYPTION_AVAILABLE and self._encryption_key:
            self._fernet = self._derive_fernet_key(self._encryption_key)

    def _derive_fernet_key(self, secret: str) -> Any:
        """Derive a Fernet key from the secret string."""
        if not ENCRYPTION_AVAILABLE:
            return None

        # Use PBKDF2 to derive a key from the secret
        salt = b"ebook_tools_config_v1"  # Static salt - key rotation uses new secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = urlsafe_b64encode(kdf.derive(secret.encode()))
        return Fernet(key)

    @property
    def db_path(self) -> Path:
        """Return the database file path."""
        return self._db_path

    @property
    def encryption_available(self) -> bool:
        """Return whether encryption is available and configured."""
        return self._fernet is not None

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Open a database connection with migrations applied.

        Yields:
            SQLite connection with row factory configured
        """
        connection = sqlite3.connect(
            str(self._db_path),
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        connection.row_factory = sqlite3.Row
        try:
            self._apply_migrations(connection)
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _apply_migrations(self, connection: sqlite3.Connection) -> None:
        """Apply pending database migrations."""
        connection.execute("PRAGMA foreign_keys = ON;")
        try:
            connection.execute("PRAGMA journal_mode = WAL;")
        except sqlite3.OperationalError:
            try:
                connection.execute("PRAGMA journal_mode = DELETE;")
            except sqlite3.OperationalError:
                pass

        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"
        )

        applied = {
            row["version"]
            for row in connection.execute("SELECT version FROM schema_migrations")
        }

        for path in self._sorted_migrations():
            version = int(path.stem.split("_", 1)[0])
            if version in applied:
                continue
            script = path.read_text(encoding="utf-8")
            connection.executescript(script)
            connection.execute(
                "INSERT OR REPLACE INTO schema_migrations (version) VALUES (?)",
                (version,),
            )

        connection.commit()

    def _sorted_migrations(self) -> List[Path]:
        """Return migration files sorted by version number."""
        if not MIGRATIONS_DIR.exists():
            return []
        return sorted(
            (path for path in MIGRATIONS_DIR.iterdir() if path.suffix == ".sql"),
            key=lambda path: path.stem,
        )

    # -------------------------------------------------------------------------
    # Snapshot Management
    # -------------------------------------------------------------------------

    def save_snapshot(
        self,
        config: Dict[str, Any],
        *,
        label: Optional[str] = None,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
        source: str = "manual",
        activate: bool = False,
    ) -> str:
        """Save a configuration snapshot.

        Args:
            config: Configuration dictionary to save
            label: Optional human-readable label
            description: Optional description
            created_by: Username who created the snapshot
            source: Source of the snapshot (manual, import, auto_backup, etc.)
            activate: Whether to mark this snapshot as active

        Returns:
            The snapshot_id of the created snapshot
        """
        snapshot_id = f"snap_{uuid4().hex[:12]}"
        config_json = json.dumps(config, sort_keys=True, ensure_ascii=False)
        config_hash = hashlib.sha256(config_json.encode()).hexdigest()[:16]
        created_at = datetime.now(timezone.utc).isoformat()

        with self.connect() as connection:
            if activate:
                # Deactivate all other snapshots
                connection.execute("UPDATE config_snapshots SET is_active = 0")

            connection.execute(
                """
                INSERT INTO config_snapshots (
                    snapshot_id, label, description, config_json, config_hash,
                    created_by, created_at, is_active, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    label,
                    description,
                    config_json,
                    config_hash,
                    created_by,
                    created_at,
                    1 if activate else 0,
                    source,
                ),
            )

            # Log the snapshot creation
            self._log_change_internal(
                connection,
                action="create",
                username=created_by,
                snapshot_id=snapshot_id,
                metadata={"source": source, "label": label},
            )

        logger.info(
            "Created config snapshot %s",
            snapshot_id,
            extra={"event": "config.snapshot.created", "snapshot_id": snapshot_id},
        )
        return snapshot_id

    def get_snapshot(self, snapshot_id: str) -> Optional[Tuple[SnapshotMetadata, Dict[str, Any]]]:
        """Get a snapshot by ID.

        Args:
            snapshot_id: The snapshot identifier

        Returns:
            Tuple of (metadata, config) or None if not found
        """
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM config_snapshots WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()

        if not row:
            return None

        metadata = SnapshotMetadata(
            snapshot_id=row["snapshot_id"],
            label=row["label"],
            description=row["description"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            is_active=bool(row["is_active"]),
            source=row["source"],
            config_hash=row["config_hash"],
        )
        config = json.loads(row["config_json"])
        return metadata, config

    def get_active_snapshot(self) -> Optional[Tuple[SnapshotMetadata, Dict[str, Any]]]:
        """Get the currently active configuration snapshot.

        Returns:
            Tuple of (metadata, config) or None if no active snapshot
        """
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM config_snapshots WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1"
            ).fetchone()

        if not row:
            return None

        metadata = SnapshotMetadata(
            snapshot_id=row["snapshot_id"],
            label=row["label"],
            description=row["description"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            is_active=True,
            source=row["source"],
            config_hash=row["config_hash"],
        )
        config = json.loads(row["config_json"])
        return metadata, config

    def restore_snapshot(
        self,
        snapshot_id: str,
        *,
        restored_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Restore a previous snapshot and mark it active.

        Args:
            snapshot_id: The snapshot to restore
            restored_by: Username performing the restore

        Returns:
            The restored configuration dictionary

        Raises:
            ConfigRepositoryError: If snapshot not found
        """
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM config_snapshots WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()

            if not row:
                raise ConfigRepositoryError(f"Snapshot not found: {snapshot_id}")

            # Deactivate all snapshots and activate this one
            connection.execute("UPDATE config_snapshots SET is_active = 0")
            connection.execute(
                "UPDATE config_snapshots SET is_active = 1 WHERE snapshot_id = ?",
                (snapshot_id,),
            )

            self._log_change_internal(
                connection,
                action="restore",
                username=restored_by,
                snapshot_id=snapshot_id,
                metadata={"label": row["label"]},
            )

        config = json.loads(row["config_json"])
        logger.info(
            "Restored config snapshot %s",
            snapshot_id,
            extra={"event": "config.snapshot.restored", "snapshot_id": snapshot_id},
        )
        return config

    def list_snapshots(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        include_config: bool = False,
    ) -> Tuple[List[SnapshotMetadata], int]:
        """List available configuration snapshots.

        Args:
            limit: Maximum number of snapshots to return
            offset: Number of snapshots to skip
            include_config: Whether to include full config (not implemented)

        Returns:
            Tuple of (list of metadata, total count)
        """
        with self.connect() as connection:
            # Get total count
            total = connection.execute(
                "SELECT COUNT(*) as total FROM config_snapshots"
            ).fetchone()["total"]

            # Get snapshots
            rows = connection.execute(
                """
                SELECT snapshot_id, label, description, created_by, created_at,
                       is_active, source, config_hash
                FROM config_snapshots
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()

        snapshots = [
            SnapshotMetadata(
                snapshot_id=row["snapshot_id"],
                label=row["label"],
                description=row["description"],
                created_by=row["created_by"],
                created_at=row["created_at"],
                is_active=bool(row["is_active"]),
                source=row["source"],
                config_hash=row["config_hash"],
            )
            for row in rows
        ]
        return snapshots, total

    def delete_snapshot(self, snapshot_id: str, *, deleted_by: Optional[str] = None) -> bool:
        """Delete a configuration snapshot.

        Args:
            snapshot_id: The snapshot to delete
            deleted_by: Username performing the deletion

        Returns:
            True if deleted, False if not found

        Raises:
            ConfigRepositoryError: If attempting to delete the active snapshot
        """
        with self.connect() as connection:
            row = connection.execute(
                "SELECT is_active FROM config_snapshots WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()

            if not row:
                return False

            if row["is_active"]:
                raise ConfigRepositoryError("Cannot delete the active snapshot")

            # Clear foreign key references in restart log before deleting
            connection.execute(
                "UPDATE config_restart_log SET pre_restart_snapshot_id = NULL WHERE pre_restart_snapshot_id = ?",
                (snapshot_id,),
            )

            connection.execute(
                "DELETE FROM config_snapshots WHERE snapshot_id = ?",
                (snapshot_id,),
            )

            self._log_change_internal(
                connection,
                action="delete",
                username=deleted_by,
                snapshot_id=snapshot_id,
            )

        logger.info(
            "Deleted config snapshot %s",
            snapshot_id,
            extra={"event": "config.snapshot.deleted", "snapshot_id": snapshot_id},
        )
        return True

    # -------------------------------------------------------------------------
    # Audit Logging
    # -------------------------------------------------------------------------

    def log_change(
        self,
        action: str,
        *,
        username: Optional[str] = None,
        snapshot_id: Optional[str] = None,
        group_name: Optional[str] = None,
        key_name: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """Record an audit log entry.

        Args:
            action: Type of action (create, update, restore, export, import, etc.)
            username: User performing the action
            snapshot_id: Related snapshot ID
            group_name: Configuration group affected
            key_name: Specific key changed
            old_value: Previous value (masked for sensitive keys)
            new_value: New value (masked for sensitive keys)
            ip_address: Client IP address
            user_agent: Client user agent
            metadata: Additional metadata
            success: Whether the action succeeded
            error_message: Error message if failed
        """
        with self.connect() as connection:
            self._log_change_internal(
                connection,
                action=action,
                username=username,
                snapshot_id=snapshot_id,
                group_name=group_name,
                key_name=key_name,
                old_value=old_value,
                new_value=new_value,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata,
                success=success,
                error_message=error_message,
            )

    def _log_change_internal(
        self,
        connection: sqlite3.Connection,
        action: str,
        *,
        username: Optional[str] = None,
        snapshot_id: Optional[str] = None,
        group_name: Optional[str] = None,
        key_name: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """Internal audit log recording (requires existing connection)."""
        # Mask sensitive values
        if key_name and self._is_sensitive_key(connection, key_name):
            if old_value is not None:
                old_value = "[REDACTED]"
            if new_value is not None:
                new_value = "[REDACTED]"

        timestamp = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(metadata) if metadata else None

        connection.execute(
            """
            INSERT INTO config_audit_log (
                timestamp, username, action, snapshot_id, group_name, key_name,
                old_value, new_value, ip_address, user_agent, metadata_json,
                success, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                username,
                action,
                snapshot_id,
                group_name,
                key_name,
                old_value,
                new_value,
                ip_address,
                user_agent,
                metadata_json,
                1 if success else 0,
                error_message,
            ),
        )

    def _is_sensitive_key(self, connection: sqlite3.Connection, key_path: str) -> bool:
        """Check if a key is marked as sensitive."""
        row = connection.execute(
            "SELECT 1 FROM config_sensitive_keys WHERE key_path = ? AND mask_in_audit = 1",
            (key_path,),
        ).fetchone()
        return row is not None

    def get_audit_log(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        username: Optional[str] = None,
        action: Optional[str] = None,
        since: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> Tuple[List[AuditLogEntry], int]:
        """Query the audit log with filters.

        Args:
            limit: Maximum entries to return
            offset: Number of entries to skip
            username: Filter by username
            action: Filter by action type
            since: Filter entries after this timestamp
            group_name: Filter by configuration group

        Returns:
            Tuple of (list of entries, total count)
        """
        conditions: List[str] = []
        params: List[Any] = []

        if username:
            conditions.append("username = ?")
            params.append(username)
        if action:
            conditions.append("action = ?")
            params.append(action)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)
        if group_name:
            conditions.append("group_name = ?")
            params.append(group_name)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with self.connect() as connection:
            # Get total count
            total = connection.execute(
                f"SELECT COUNT(*) as total FROM config_audit_log {where_clause}",
                params,
            ).fetchone()["total"]

            # Get entries
            rows = connection.execute(
                f"""
                SELECT * FROM config_audit_log
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            ).fetchall()

        entries = [
            AuditLogEntry(
                id=row["id"],
                timestamp=row["timestamp"],
                username=row["username"],
                action=row["action"],
                snapshot_id=row["snapshot_id"],
                group_name=row["group_name"],
                key_name=row["key_name"],
                old_value=row["old_value"],
                new_value=row["new_value"],
                ip_address=row["ip_address"],
                user_agent=row["user_agent"],
                metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else None,
                success=bool(row["success"]),
                error_message=row["error_message"],
            )
            for row in rows
        ]
        return entries, total

    # -------------------------------------------------------------------------
    # Secrets Management
    # -------------------------------------------------------------------------

    def store_secret(
        self,
        key_path: str,
        value: str,
        *,
        updated_by: Optional[str] = None,
    ) -> None:
        """Store an encrypted secret value.

        Args:
            key_path: The configuration key path
            value: The secret value to encrypt and store
            updated_by: Username performing the update

        Raises:
            ConfigRepositoryError: If encryption is not available
        """
        if not self._fernet:
            raise ConfigRepositoryError(
                "Encryption not available. Set EBOOK_CONFIG_SECRET environment variable "
                "or install cryptography package."
            )

        encrypted = self._fernet.encrypt(value.encode())
        updated_at = datetime.now(timezone.utc).isoformat()

        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO config_secrets (key_path, encrypted_value, updated_at, updated_by)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key_path) DO UPDATE SET
                    encrypted_value = excluded.encrypted_value,
                    updated_at = excluded.updated_at,
                    updated_by = excluded.updated_by
                """,
                (key_path, encrypted, updated_at, updated_by),
            )

            # Ensure key is marked as sensitive
            connection.execute(
                "INSERT OR IGNORE INTO config_sensitive_keys (key_path) VALUES (?)",
                (key_path,),
            )

            self._log_change_internal(
                connection,
                action="update",
                username=updated_by,
                key_name=key_path,
                new_value="[ENCRYPTED]",
            )

    def get_secret(self, key_path: str) -> Optional[str]:
        """Retrieve and decrypt a secret value.

        Args:
            key_path: The configuration key path

        Returns:
            The decrypted value or None if not found

        Raises:
            ConfigRepositoryError: If decryption fails
        """
        if not self._fernet:
            return None

        with self.connect() as connection:
            row = connection.execute(
                "SELECT encrypted_value FROM config_secrets WHERE key_path = ?",
                (key_path,),
            ).fetchone()

        if not row:
            return None

        try:
            return self._fernet.decrypt(row["encrypted_value"]).decode()
        except InvalidToken as e:
            raise ConfigRepositoryError(f"Failed to decrypt secret {key_path}") from e

    def delete_secret(self, key_path: str, *, deleted_by: Optional[str] = None) -> bool:
        """Delete a stored secret.

        Args:
            key_path: The configuration key path
            deleted_by: Username performing the deletion

        Returns:
            True if deleted, False if not found
        """
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM config_secrets WHERE key_path = ?",
                (key_path,),
            )

            if cursor.rowcount > 0:
                self._log_change_internal(
                    connection,
                    action="delete",
                    username=deleted_by,
                    key_name=key_path,
                    old_value="[ENCRYPTED]",
                )
                return True

        return False

    def list_secrets(self) -> List[str]:
        """List all stored secret key paths (not values).

        Returns:
            List of key paths that have stored secrets
        """
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT key_path FROM config_secrets ORDER BY key_path"
            ).fetchall()
        return [row["key_path"] for row in rows]

    # -------------------------------------------------------------------------
    # Export / Import
    # -------------------------------------------------------------------------

    def export_snapshot(
        self,
        snapshot_id: str,
        *,
        mask_sensitive: bool = True,
        include_secrets: bool = False,
    ) -> Dict[str, Any]:
        """Export a snapshot as JSON-serializable dictionary.

        Args:
            snapshot_id: The snapshot to export
            mask_sensitive: Whether to mask sensitive values
            include_secrets: Whether to include decrypted secrets (requires mask_sensitive=False)

        Returns:
            Dictionary with snapshot metadata and config

        Raises:
            ConfigRepositoryError: If snapshot not found
        """
        result = self.get_snapshot(snapshot_id)
        if not result:
            raise ConfigRepositoryError(f"Snapshot not found: {snapshot_id}")

        metadata, config = result

        # Mask sensitive values if requested
        if mask_sensitive:
            config = self._mask_sensitive_values(config)
        elif include_secrets:
            # Inject decrypted secrets into config
            for key_path in self.list_secrets():
                secret_value = self.get_secret(key_path)
                if secret_value:
                    self._set_nested_value(config, key_path, secret_value)

        return {
            "snapshot_id": metadata.snapshot_id,
            "label": metadata.label,
            "description": metadata.description,
            "created_at": metadata.created_at,
            "created_by": metadata.created_by,
            "source": metadata.source,
            "config": config,
        }

    def _mask_sensitive_values(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Return a copy of config with sensitive values masked."""
        result = dict(config)

        with self.connect() as connection:
            rows = connection.execute(
                "SELECT key_path FROM config_sensitive_keys WHERE mask_in_export = 1"
            ).fetchall()
            sensitive_keys = {row["key_path"] for row in rows}

        for key_path in sensitive_keys:
            parts = key_path.split(".")
            target = result
            for part in parts[:-1]:
                if isinstance(target, dict) and part in target:
                    target = target[part]
                else:
                    break
            else:
                if isinstance(target, dict) and parts[-1] in target:
                    target[parts[-1]] = "***REDACTED***"

        return result

    def _set_nested_value(self, config: Dict[str, Any], key_path: str, value: Any) -> None:
        """Set a nested value in the config dictionary."""
        parts = key_path.split(".")
        target = config
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value

    def import_config(
        self,
        config: Dict[str, Any],
        *,
        label: Optional[str] = None,
        description: Optional[str] = None,
        imported_by: Optional[str] = None,
        activate: bool = False,
    ) -> str:
        """Import configuration from a dictionary.

        Args:
            config: Configuration dictionary to import
            label: Optional label for the snapshot
            description: Optional description
            imported_by: Username performing the import
            activate: Whether to activate the imported config

        Returns:
            The snapshot_id of the created snapshot
        """
        # Create a snapshot from the imported config
        snapshot_id = self.save_snapshot(
            config,
            label=label or "Imported Configuration",
            description=description,
            created_by=imported_by,
            source="import",
            activate=activate,
        )

        self.log_change(
            action="import",
            username=imported_by,
            snapshot_id=snapshot_id,
            metadata={"label": label},
        )

        return snapshot_id

    # -------------------------------------------------------------------------
    # Restart Tracking
    # -------------------------------------------------------------------------

    def log_restart_request(
        self,
        *,
        requested_by: Optional[str] = None,
        reason: Optional[str] = None,
        delay_seconds: int = 5,
    ) -> int:
        """Log a restart request.

        Args:
            requested_by: Username requesting the restart
            reason: Reason for the restart
            delay_seconds: Delay before restart

        Returns:
            The restart log entry ID
        """
        # Create a pre-restart backup
        active = self.get_active_snapshot()
        pre_restart_snapshot_id = None
        if active:
            pre_restart_snapshot_id = active[0].snapshot_id
        else:
            # Create a new snapshot if none is active
            from .loader import load_configuration
            try:
                config = load_configuration()
                pre_restart_snapshot_id = self.save_snapshot(
                    config,
                    label="Pre-restart Backup",
                    description=f"Automatic backup before restart: {reason or 'No reason provided'}",
                    created_by=requested_by,
                    source="pre_restart",
                )
            except Exception as e:
                logger.warning(
                    "Failed to create pre-restart backup: %s",
                    e,
                    extra={"event": "config.restart.backup_failed"},
                )

        requested_at = datetime.now(timezone.utc).isoformat()

        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO config_restart_log (
                    requested_at, requested_by, reason, delay_seconds, pre_restart_snapshot_id
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (requested_at, requested_by, reason, delay_seconds, pre_restart_snapshot_id),
            )
            restart_id = cursor.lastrowid

            self._log_change_internal(
                connection,
                action="restart",
                username=requested_by,
                metadata={"reason": reason, "delay_seconds": delay_seconds},
            )

        return restart_id

    def complete_restart(
        self,
        restart_id: int,
        *,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """Record restart completion.

        Args:
            restart_id: The restart log entry ID
            success: Whether the restart succeeded
            error_message: Error message if failed
        """
        completed_at = datetime.now(timezone.utc).isoformat()

        with self.connect() as connection:
            connection.execute(
                """
                UPDATE config_restart_log
                SET completed_at = ?, success = ?, error_message = ?
                WHERE id = ?
                """,
                (completed_at, 1 if success else 0, error_message, restart_id),
            )


__all__ = [
    "ConfigRepository",
    "ConfigRepositoryError",
    "SnapshotMetadata",
    "AuditLogEntry",
    "CONFIG_SECRET_ENV",
    "DEFAULT_CONFIG_DB_DIR",
]
