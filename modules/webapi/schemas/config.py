"""Pydantic schemas for configuration management API endpoints."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase for JSON serialization."""
    components = string.split("_")
    return components[0] + "".join(word.capitalize() for word in components[1:])


class CamelModel(BaseModel):
    """Base model that serializes to camelCase for frontend compatibility."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


# -----------------------------------------------------------------------------
# Configuration Key and Group Schemas
# -----------------------------------------------------------------------------


class ConfigKeyMetadata(CamelModel):
    """Metadata describing a single configuration key."""

    key: str = Field(..., description="The configuration key name")
    display_name: str = Field(..., description="Human-readable display name")
    description: Optional[str] = Field(None, description="Description of the setting")
    type: str = Field(..., description="Value type: string, number, integer, boolean, array, object, secret")
    default_value: Any = Field(None, description="Default value for this key")
    current_value: Any = Field(None, description="Current effective value")
    is_sensitive: bool = Field(False, description="Whether this key contains sensitive data")
    is_env_override: bool = Field(False, description="Whether current value comes from environment variable")
    requires_restart: bool = Field(True, description="Whether changes require a restart")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Validation rules (min, max, choices, etc.)")


class ConfigGroupMetadata(CamelModel):
    """Metadata describing a configuration group."""

    name: str = Field(..., description="Group identifier")
    display_name: str = Field(..., description="Human-readable display name")
    description: str = Field(..., description="Description of settings in this group")
    icon: Optional[str] = Field(None, description="Icon identifier for UI")
    key_count: int = Field(..., description="Number of keys in this group")
    has_sensitive: bool = Field(False, description="Whether group contains sensitive keys")


class ConfigGroupResponse(CamelModel):
    """Response containing a single configuration group."""

    group: str = Field(..., description="Group identifier")
    metadata: ConfigGroupMetadata
    keys: List[ConfigKeyMetadata]


class GroupedConfigResponse(CamelModel):
    """Response containing all configuration groups."""

    groups: List[ConfigGroupResponse]
    effective_sources: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of key -> source (default, file, env, db)"
    )
    last_modified: Optional[str] = Field(None, description="When config was last modified")
    active_snapshot_id: Optional[str] = Field(None, description="Active DB snapshot ID if any")


class ConfigGroupUpdatePayload(CamelModel):
    """Payload for updating a configuration group."""

    values: Dict[str, Any] = Field(..., description="Key-value pairs to update")
    create_backup: bool = Field(True, description="Create a backup before applying changes")


class ConfigGroupUpdateResponse(CamelModel):
    """Response after updating a configuration group."""

    group: str
    updated_keys: List[str]
    requires_restart: bool
    backup_snapshot_id: Optional[str] = None


# -----------------------------------------------------------------------------
# Snapshot Schemas
# -----------------------------------------------------------------------------


class SnapshotMetadata(CamelModel):
    """Metadata for a configuration snapshot."""

    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    label: Optional[str] = Field(None, description="Human-readable label")
    description: Optional[str] = Field(None, description="Description of the snapshot")
    created_by: Optional[str] = Field(None, description="Username who created the snapshot")
    created_at: str = Field(..., description="ISO timestamp when created")
    is_active: bool = Field(False, description="Whether this is the active snapshot")
    source: str = Field(..., description="Source: manual, import, auto_backup, migration, pre_restart")
    config_hash: str = Field(..., description="Hash of the configuration content")


class SnapshotListResponse(CamelModel):
    """Response containing a list of snapshots."""

    snapshots: List[SnapshotMetadata]
    total: int = Field(..., description="Total number of snapshots")
    limit: int
    offset: int


class CreateSnapshotPayload(CamelModel):
    """Payload for creating a new snapshot."""

    label: Optional[str] = Field(None, description="Human-readable label")
    description: Optional[str] = Field(None, description="Description of the snapshot")
    activate: bool = Field(False, description="Whether to activate this snapshot immediately")


class CreateSnapshotResponse(CamelModel):
    """Response after creating a snapshot."""

    snapshot_id: str
    label: Optional[str]
    created_at: str
    is_active: bool


class RestoreSnapshotResponse(CamelModel):
    """Response after restoring a snapshot."""

    snapshot_id: str
    label: Optional[str]
    restored_at: str
    requires_restart: bool
    restart_keys: List[str] = Field(
        default_factory=list,
        description="Keys that changed and require restart"
    )


class ExportSnapshotResponse(CamelModel):
    """Response containing exported snapshot data."""

    snapshot_id: str
    label: Optional[str]
    description: Optional[str]
    created_at: str
    created_by: Optional[str]
    source: str
    config: Dict[str, Any]


class ImportConfigPayload(CamelModel):
    """Payload for importing configuration (used with file upload)."""

    label: Optional[str] = Field(None, description="Label for the imported config")
    description: Optional[str] = Field(None, description="Description")
    activate: bool = Field(False, description="Whether to activate after import")


class ImportConfigResponse(CamelModel):
    """Response after importing configuration."""

    snapshot_id: str
    label: Optional[str]
    key_count: int
    is_active: bool


# -----------------------------------------------------------------------------
# Audit Log Schemas
# -----------------------------------------------------------------------------


class AuditLogEntry(CamelModel):
    """Entry in the configuration audit log."""

    id: int
    timestamp: str
    username: Optional[str]
    action: str = Field(..., description="Action: create, update, restore, export, import, delete, reload, restart")
    snapshot_id: Optional[str]
    group_name: Optional[str]
    key_name: Optional[str]
    old_value: Optional[str] = Field(None, description="Previous value (redacted for sensitive keys)")
    new_value: Optional[str] = Field(None, description="New value (redacted for sensitive keys)")
    ip_address: Optional[str]
    metadata: Optional[Dict[str, Any]]
    success: bool
    error_message: Optional[str]


class AuditLogResponse(CamelModel):
    """Response containing audit log entries."""

    entries: List[AuditLogEntry]
    total: int
    limit: int
    offset: int


class AuditLogQueryParams(CamelModel):
    """Query parameters for audit log."""

    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)
    username: Optional[str] = None
    action: Optional[str] = None
    since: Optional[str] = None
    group_name: Optional[str] = None


# -----------------------------------------------------------------------------
# Validation Schemas
# -----------------------------------------------------------------------------


class ValidationError(CamelModel):
    """A single validation error."""

    key: str
    message: str
    error_type: str = Field("error", description="error or warning")


class ConfigValidationPayload(CamelModel):
    """Payload for validating configuration changes."""

    group: Optional[str] = Field(None, description="Group to validate (or all if None)")
    values: Dict[str, Any] = Field(..., description="Values to validate")


class ConfigValidationResponse(CamelModel):
    """Response from configuration validation."""

    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]


# -----------------------------------------------------------------------------
# System Control Schemas
# -----------------------------------------------------------------------------


class SystemStatusResponse(CamelModel):
    """Response containing system status information."""

    uptime_seconds: float
    config_loaded_at: Optional[str]
    active_snapshot_id: Optional[str]
    db_enabled: bool
    config_db_path: Optional[str] = Field(None, description="Path to the configuration database")
    library_db_path: Optional[str] = Field(None, description="Path to the library database")
    pending_changes: bool = Field(False, description="Whether there are unapplied changes")
    restart_required: bool = Field(False, description="Whether a restart is required")
    restart_keys: List[str] = Field(
        default_factory=list,
        description="Keys that have changed and require restart"
    )


class ReloadConfigResponse(CamelModel):
    """Response after reloading configuration."""

    success: bool
    reloaded_at: str
    changed_keys: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class RestartRequestPayload(CamelModel):
    """Payload for requesting a server restart."""

    reason: Optional[str] = Field(None, description="Reason for the restart")
    delay_seconds: int = Field(5, ge=1, le=60, description="Delay before restart")
    force: bool = Field(False, description="Force restart even if jobs are running")


class RestartResponse(CamelModel):
    """Response after scheduling a restart."""

    scheduled: bool
    restart_at: str
    delay_seconds: int
    pre_restart_snapshot_id: Optional[str]
    running_jobs: int = Field(0, description="Number of running jobs that will be affected")


class HealthCheckResponse(CamelModel):
    """Deep health check response."""

    status: str = Field(..., description="ok, degraded, or unhealthy")
    config_loaded: bool
    db_available: bool
    tmp_workspace: Optional[str]
    is_ramdisk: bool
    uptime_seconds: float
    checks: Dict[str, bool] = Field(default_factory=dict)


# -----------------------------------------------------------------------------
# Secret Management Schemas
# -----------------------------------------------------------------------------


class SecretKeyInfo(CamelModel):
    """Information about a stored secret (not the value)."""

    key_path: str
    updated_at: Optional[str]
    updated_by: Optional[str]


class SecretListResponse(CamelModel):
    """Response listing stored secrets."""

    secrets: List[SecretKeyInfo]
    encryption_available: bool


class SetSecretPayload(CamelModel):
    """Payload for setting a secret value."""

    key_path: str = Field(..., description="Configuration key path")
    value: str = Field(..., description="Secret value to store")


class SetSecretResponse(CamelModel):
    """Response after setting a secret."""

    key_path: str
    success: bool
    error: Optional[str] = None
