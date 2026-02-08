"""Configuration management models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class ConfigSnapshotModel(Base):
    __tablename__ = "config_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=func.now(), server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")

    __table_args__ = (
        Index("idx_config_snap_active", "is_active", postgresql_where="is_active = TRUE"),
        Index("idx_config_snap_created", "created_at"),
        Index("idx_config_snap_source", "source"),
    )


class ConfigAuditLogModel(Base):
    __tablename__ = "config_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        nullable=False, default=func.now(), server_default=func.now()
    )
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    snapshot_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    group_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    key_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_username", "username"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_group", "group_name"),
    )


class ConfigSensitiveKeyModel(Base):
    __tablename__ = "config_sensitive_keys"

    key_path: Mapped[str] = mapped_column(String(255), primary_key=True)
    mask_in_ui: Mapped[bool] = mapped_column(Boolean, default=True)
    mask_in_export: Mapped[bool] = mapped_column(Boolean, default=True)
    mask_in_audit: Mapped[bool] = mapped_column(Boolean, default=True)


class ConfigSecretModel(Base):
    __tablename__ = "config_secrets"

    key_path: Mapped[str] = mapped_column(String(255), primary_key=True)
    encrypted_value: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encryption_version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=func.now(), server_default=func.now()
    )
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class ConfigGroupSettingModel(Base):
    __tablename__ = "config_group_settings"

    group_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    is_collapsed: Mapped[bool] = mapped_column(Boolean, default=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    custom_icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


class ConfigValidationRuleModel(Base):
    __tablename__ = "config_validation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key_path: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_value: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_warning: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (Index("idx_validation_key", "key_path"),)


class ConfigRestartLogModel(Base):
    __tablename__ = "config_restart_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requested_at: Mapped[datetime] = mapped_column(
        nullable=False, default=func.now(), server_default=func.now()
    )
    requested_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delay_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pre_restart_snapshot_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("config_snapshots.snapshot_id"),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    success: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("idx_restart_requested", "requested_at"),)
