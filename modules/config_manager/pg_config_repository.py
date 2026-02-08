"""PostgreSQL-backed configuration repository with auditing and encryption."""

from __future__ import annotations

import hashlib
import json
import os
from base64 import urlsafe_b64encode
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import and_, delete, func, select, update

from modules import logging_manager

from ..database.engine import get_db_session
from ..database.models.config import (
    ConfigAuditLogModel,
    ConfigRestartLogModel,
    ConfigSecretModel,
    ConfigSensitiveKeyModel,
    ConfigSnapshotModel,
)
from .config_repository import AuditLogEntry, ConfigRepositoryError, SnapshotMetadata

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

CONFIG_SECRET_ENV = "EBOOK_CONFIG_SECRET"


class PgConfigRepository:
    """PostgreSQL-backed configuration persistence with auditing and encryption."""

    def __init__(
        self,
        encryption_key: Optional[str] = None,
    ) -> None:
        self._encryption_key = encryption_key or os.environ.get(CONFIG_SECRET_ENV)
        self._fernet: Optional[Any] = None
        if ENCRYPTION_AVAILABLE and self._encryption_key:
            self._fernet = self._derive_fernet_key(self._encryption_key)

    def _derive_fernet_key(self, secret: str) -> Any:
        if not ENCRYPTION_AVAILABLE:
            return None
        salt = b"ebook_tools_config_v1"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = urlsafe_b64encode(kdf.derive(secret.encode()))
        return Fernet(key)

    @property
    def encryption_available(self) -> bool:
        return self._fernet is not None

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
        snapshot_id = f"snap_{uuid4().hex[:12]}"
        config_json_str = json.dumps(config, sort_keys=True, ensure_ascii=False)
        config_hash = hashlib.sha256(config_json_str.encode()).hexdigest()[:16]
        now = datetime.now(timezone.utc)

        with get_db_session() as session:
            if activate:
                session.execute(
                    update(ConfigSnapshotModel).values(is_active=False)
                )

            model = ConfigSnapshotModel(
                snapshot_id=snapshot_id,
                label=label,
                description=description,
                config_json=config,
                config_hash=config_hash,
                created_by=created_by,
                created_at=now,
                is_active=activate,
                source=source,
            )
            session.add(model)

            self._log_change_internal(
                session,
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

    def get_snapshot(
        self, snapshot_id: str
    ) -> Optional[Tuple[SnapshotMetadata, Dict[str, Any]]]:
        with get_db_session() as session:
            model = session.execute(
                select(ConfigSnapshotModel).where(
                    ConfigSnapshotModel.snapshot_id == snapshot_id
                )
            ).scalar_one_or_none()

            if model is None:
                return None

            meta = SnapshotMetadata(
                snapshot_id=model.snapshot_id,
                label=model.label,
                description=model.description,
                created_by=model.created_by,
                created_at=model.created_at.isoformat() if model.created_at else "",
                is_active=model.is_active,
                source=model.source,
                config_hash=model.config_hash,
            )
            config = dict(model.config_json) if model.config_json else {}
            return meta, config

    def get_active_snapshot(
        self,
    ) -> Optional[Tuple[SnapshotMetadata, Dict[str, Any]]]:
        with get_db_session() as session:
            model = session.execute(
                select(ConfigSnapshotModel)
                .where(ConfigSnapshotModel.is_active == True)
                .order_by(ConfigSnapshotModel.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()

            if model is None:
                return None

            meta = SnapshotMetadata(
                snapshot_id=model.snapshot_id,
                label=model.label,
                description=model.description,
                created_by=model.created_by,
                created_at=model.created_at.isoformat() if model.created_at else "",
                is_active=True,
                source=model.source,
                config_hash=model.config_hash,
            )
            config = dict(model.config_json) if model.config_json else {}
            return meta, config

    def restore_snapshot(
        self,
        snapshot_id: str,
        *,
        restored_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        with get_db_session() as session:
            model = session.execute(
                select(ConfigSnapshotModel).where(
                    ConfigSnapshotModel.snapshot_id == snapshot_id
                )
            ).scalar_one_or_none()

            if model is None:
                raise ConfigRepositoryError(f"Snapshot not found: {snapshot_id}")

            session.execute(
                update(ConfigSnapshotModel).values(is_active=False)
            )
            session.execute(
                update(ConfigSnapshotModel)
                .where(ConfigSnapshotModel.snapshot_id == snapshot_id)
                .values(is_active=True)
            )

            self._log_change_internal(
                session,
                action="restore",
                username=restored_by,
                snapshot_id=snapshot_id,
                metadata={"label": model.label},
            )

            config = dict(model.config_json) if model.config_json else {}

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
        with get_db_session() as session:
            total = session.execute(
                select(func.count()).select_from(ConfigSnapshotModel)
            ).scalar_one()

            models = (
                session.execute(
                    select(ConfigSnapshotModel)
                    .order_by(ConfigSnapshotModel.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
                .scalars()
                .all()
            )

        snapshots = [
            SnapshotMetadata(
                snapshot_id=m.snapshot_id,
                label=m.label,
                description=m.description,
                created_by=m.created_by,
                created_at=m.created_at.isoformat() if m.created_at else "",
                is_active=m.is_active,
                source=m.source,
                config_hash=m.config_hash,
            )
            for m in models
        ]
        return snapshots, total

    def delete_snapshot(
        self, snapshot_id: str, *, deleted_by: Optional[str] = None
    ) -> bool:
        with get_db_session() as session:
            model = session.execute(
                select(ConfigSnapshotModel).where(
                    ConfigSnapshotModel.snapshot_id == snapshot_id
                )
            ).scalar_one_or_none()

            if model is None:
                return False

            if model.is_active:
                raise ConfigRepositoryError("Cannot delete the active snapshot")

            # Clear FK references in restart log
            session.execute(
                update(ConfigRestartLogModel)
                .where(
                    ConfigRestartLogModel.pre_restart_snapshot_id == snapshot_id
                )
                .values(pre_restart_snapshot_id=None)
            )

            session.execute(
                delete(ConfigSnapshotModel).where(
                    ConfigSnapshotModel.snapshot_id == snapshot_id
                )
            )

            self._log_change_internal(
                session,
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
        with get_db_session() as session:
            self._log_change_internal(
                session,
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
        session,
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
        # Mask sensitive values
        if key_name and self._is_sensitive_key(session, key_name):
            if old_value is not None:
                old_value = "[REDACTED]"
            if new_value is not None:
                new_value = "[REDACTED]"

        now = datetime.now(timezone.utc)

        model = ConfigAuditLogModel(
            timestamp=now,
            username=username,
            action=action,
            snapshot_id=snapshot_id,
            group_name=group_name,
            key_name=key_name,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json=metadata,
            success=success,
            error_message=error_message,
        )
        session.add(model)

    @staticmethod
    def _is_sensitive_key(session, key_path: str) -> bool:
        row = session.execute(
            select(ConfigSensitiveKeyModel).where(
                and_(
                    ConfigSensitiveKeyModel.key_path == key_path,
                    ConfigSensitiveKeyModel.mask_in_audit == True,
                )
            )
        ).scalar_one_or_none()
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
        conditions = []
        if username:
            conditions.append(ConfigAuditLogModel.username == username)
        if action:
            conditions.append(ConfigAuditLogModel.action == action)
        if since:
            conditions.append(ConfigAuditLogModel.timestamp >= since)
        if group_name:
            conditions.append(ConfigAuditLogModel.group_name == group_name)

        where = and_(*conditions) if conditions else True

        with get_db_session() as session:
            total = session.execute(
                select(func.count())
                .select_from(ConfigAuditLogModel)
                .where(where)
            ).scalar_one()

            models = (
                session.execute(
                    select(ConfigAuditLogModel)
                    .where(where)
                    .order_by(ConfigAuditLogModel.timestamp.desc())
                    .limit(limit)
                    .offset(offset)
                )
                .scalars()
                .all()
            )

        entries = [
            AuditLogEntry(
                id=m.id,
                timestamp=m.timestamp.isoformat() if m.timestamp else "",
                username=m.username,
                action=m.action,
                snapshot_id=m.snapshot_id,
                group_name=m.group_name,
                key_name=m.key_name,
                old_value=m.old_value,
                new_value=m.new_value,
                ip_address=str(m.ip_address) if m.ip_address else None,
                user_agent=m.user_agent,
                metadata=dict(m.metadata_json) if m.metadata_json else None,
                success=m.success,
                error_message=m.error_message,
            )
            for m in models
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
        if not self._fernet:
            raise ConfigRepositoryError(
                "Encryption not available. Set EBOOK_CONFIG_SECRET environment variable "
                "or install cryptography package."
            )

        encrypted = self._fernet.encrypt(value.encode())
        now = datetime.now(timezone.utc)

        with get_db_session() as session:
            existing = session.execute(
                select(ConfigSecretModel).where(
                    ConfigSecretModel.key_path == key_path
                )
            ).scalar_one_or_none()

            if existing:
                existing.encrypted_value = encrypted
                existing.updated_at = now
                existing.updated_by = updated_by
            else:
                session.add(
                    ConfigSecretModel(
                        key_path=key_path,
                        encrypted_value=encrypted,
                        updated_at=now,
                        updated_by=updated_by,
                    )
                )

            # Ensure key is marked as sensitive
            sens = session.execute(
                select(ConfigSensitiveKeyModel).where(
                    ConfigSensitiveKeyModel.key_path == key_path
                )
            ).scalar_one_or_none()
            if sens is None:
                session.add(ConfigSensitiveKeyModel(key_path=key_path))

            self._log_change_internal(
                session,
                action="update",
                username=updated_by,
                key_name=key_path,
                new_value="[ENCRYPTED]",
            )

    def get_secret(self, key_path: str) -> Optional[str]:
        if not self._fernet:
            return None

        with get_db_session() as session:
            model = session.execute(
                select(ConfigSecretModel).where(
                    ConfigSecretModel.key_path == key_path
                )
            ).scalar_one_or_none()

        if model is None:
            return None

        try:
            return self._fernet.decrypt(model.encrypted_value).decode()
        except InvalidToken as e:
            raise ConfigRepositoryError(
                f"Failed to decrypt secret {key_path}"
            ) from e

    def delete_secret(
        self, key_path: str, *, deleted_by: Optional[str] = None
    ) -> bool:
        with get_db_session() as session:
            result = session.execute(
                delete(ConfigSecretModel).where(
                    ConfigSecretModel.key_path == key_path
                )
            )
            if result.rowcount > 0:
                self._log_change_internal(
                    session,
                    action="delete",
                    username=deleted_by,
                    key_name=key_path,
                    old_value="[ENCRYPTED]",
                )
                return True
        return False

    def list_secrets(self) -> List[str]:
        with get_db_session() as session:
            models = (
                session.execute(
                    select(ConfigSecretModel).order_by(
                        ConfigSecretModel.key_path
                    )
                )
                .scalars()
                .all()
            )
        return [m.key_path for m in models]

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
        result = self.get_snapshot(snapshot_id)
        if not result:
            raise ConfigRepositoryError(f"Snapshot not found: {snapshot_id}")

        metadata, config = result

        if mask_sensitive:
            config = self._mask_sensitive_values(config)
        elif include_secrets:
            for kp in self.list_secrets():
                secret_value = self.get_secret(kp)
                if secret_value:
                    self._set_nested_value(config, kp, secret_value)

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
        result = dict(config)

        with get_db_session() as session:
            models = (
                session.execute(
                    select(ConfigSensitiveKeyModel).where(
                        ConfigSensitiveKeyModel.mask_in_export == True
                    )
                )
                .scalars()
                .all()
            )
            sensitive_keys = {m.key_path for m in models}

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

    @staticmethod
    def _set_nested_value(
        config: Dict[str, Any], key_path: str, value: Any
    ) -> None:
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
        active = self.get_active_snapshot()
        pre_restart_snapshot_id = None
        if active:
            pre_restart_snapshot_id = active[0].snapshot_id
        else:
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

        now = datetime.now(timezone.utc)

        with get_db_session() as session:
            model = ConfigRestartLogModel(
                requested_at=now,
                requested_by=requested_by,
                reason=reason,
                delay_seconds=delay_seconds,
                pre_restart_snapshot_id=pre_restart_snapshot_id,
            )
            session.add(model)
            session.flush()
            restart_id = model.id

            self._log_change_internal(
                session,
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
        now = datetime.now(timezone.utc)

        with get_db_session() as session:
            session.execute(
                update(ConfigRestartLogModel)
                .where(ConfigRestartLogModel.id == restart_id)
                .values(
                    completed_at=now,
                    success=success,
                    error_message=error_message,
                )
            )


__all__ = ["PgConfigRepository"]
