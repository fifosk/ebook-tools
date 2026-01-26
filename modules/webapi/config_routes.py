"""Configuration management routes for the FastAPI backend."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse

from ..config_manager.config_repository import (
    ConfigRepository,
    ConfigRepositoryError,
)
from ..config_manager.groups import (
    CONFIG_KEY_METADATA,
    GROUP_METADATA,
    ConfigGroup,
    flat_to_grouped,
    get_hot_reload_keys,
    get_sensitive_keys,
    grouped_to_flat,
)
from ..config_manager.loader import (
    get_config_state,
    load_configuration,
    reload_configuration,
    save_current_config_to_db,
)
from ..user_management import AuthService
from ..user_management.user_store_base import UserRecord
from .dependencies import get_auth_service, refresh_runtime_config
from .schemas.config import (
    AuditLogEntry,
    AuditLogResponse,
    ConfigGroupMetadata,
    ConfigGroupResponse,
    ConfigGroupUpdatePayload,
    ConfigGroupUpdateResponse,
    ConfigKeyMetadata,
    ConfigValidationPayload,
    ConfigValidationResponse,
    CreateSnapshotPayload,
    CreateSnapshotResponse,
    ExportSnapshotResponse,
    GroupedConfigResponse,
    ImportConfigResponse,
    RestoreSnapshotResponse,
    SecretKeyInfo,
    SecretListResponse,
    SetSecretPayload,
    SetSecretResponse,
    SnapshotListResponse,
    SnapshotMetadata,
    ValidationError,
)

router = APIRouter()


def _extract_bearer_token(authorization: str | None) -> str | None:
    """Extract bearer token from Authorization header."""
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip() or None
    return authorization.strip() or None


def _require_admin(
    authorization: str | None,
    auth_service: AuthService,
) -> Tuple[str, UserRecord]:
    """Validate admin authentication and return (token, user)."""
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session token"
        )

    user = auth_service.authenticate(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token"
        )

    if "admin" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required"
        )

    return token, user


def _get_config_repository() -> ConfigRepository:
    """Get the configuration repository instance."""
    return ConfigRepository()


def _build_key_metadata(
    key: str,
    current_config: Dict[str, Any],
    env_keys: set,
    *,
    show_secrets: bool = False,
) -> ConfigKeyMetadata:
    """Build metadata for a single configuration key."""
    meta = CONFIG_KEY_METADATA.get(key, {})
    current_value = current_config.get(key)

    # Mask sensitive values unless show_secrets is True
    is_sensitive = meta.get("sensitive", False) or key in get_sensitive_keys()
    display_value = current_value
    if is_sensitive and current_value and not show_secrets:
        display_value = "***REDACTED***"

    validation_rules = {}
    if "min" in meta:
        validation_rules["min"] = meta["min"]
    if "max" in meta:
        validation_rules["max"] = meta["max"]
    if "choices" in meta:
        validation_rules["choices"] = meta["choices"]
    if "dynamic_choices_source" in meta:
        validation_rules["dynamicChoicesSource"] = meta["dynamic_choices_source"]

    return ConfigKeyMetadata(
        key=key,
        display_name=meta.get("display_name", key),
        description=meta.get("description"),
        type=meta.get("type", "string"),
        default_value=None,  # Could load from defaults
        current_value=display_value,
        is_sensitive=is_sensitive,
        is_env_override=key in env_keys,
        requires_restart=meta.get("requires_restart", True),
        validation_rules=validation_rules if validation_rules else None,
    )


def _build_group_response(
    group: ConfigGroup,
    current_config: Dict[str, Any],
    env_keys: set,
    *,
    show_secrets: bool = False,
) -> ConfigGroupResponse:
    """Build response for a single configuration group."""
    group_meta = GROUP_METADATA.get(group, {})

    # Get keys for this group
    group_keys = [
        key for key, meta in CONFIG_KEY_METADATA.items()
        if meta.get("group") == group
    ]

    keys = [
        _build_key_metadata(key, current_config, env_keys, show_secrets=show_secrets)
        for key in sorted(group_keys)
    ]

    has_sensitive = any(k.is_sensitive for k in keys)

    return ConfigGroupResponse(
        group=group.value,
        metadata=ConfigGroupMetadata(
            name=group.value,
            display_name=group_meta.get("display_name", group.value),
            description=group_meta.get("description", ""),
            icon=group_meta.get("icon"),
            key_count=len(keys),
            has_sensitive=has_sensitive,
        ),
        keys=keys,
    )


# -----------------------------------------------------------------------------
# Configuration Endpoints
# -----------------------------------------------------------------------------


@router.get("/config", response_model=GroupedConfigResponse)
def get_current_config(
    show_secrets: bool = Query(False, description="Show actual secret values (admin only)"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> GroupedConfigResponse:
    """Get the current effective configuration grouped by area."""
    _require_admin(authorization, auth_service)

    config = load_configuration()
    config_state = get_config_state()

    # When showing secrets, we need to get them from the settings object
    # since load_configuration() excludes sensitive fields
    if show_secrets:
        from ..config_manager import get_settings
        settings = get_settings()
        # Add secret values back to config dict
        for key in get_sensitive_keys():
            secret_value = getattr(settings, key, None)
            if secret_value is not None:
                if hasattr(secret_value, "get_secret_value"):
                    config[key] = secret_value.get_secret_value()
                else:
                    config[key] = secret_value

    # Determine which keys come from environment
    from ..config_manager.settings import load_environment_overrides
    env_overrides = load_environment_overrides()
    env_keys = set(env_overrides.keys())

    groups = [
        _build_group_response(group, config, env_keys, show_secrets=show_secrets)
        for group in ConfigGroup
    ]

    return GroupedConfigResponse(
        groups=groups,
        effective_sources={},  # Could track per-key sources
        last_modified=config_state.get("loaded_at"),
        active_snapshot_id=config_state.get("active_snapshot_id"),
    )


@router.get("/config/groups/{group_name}", response_model=ConfigGroupResponse)
def get_config_group(
    group_name: str,
    show_secrets: bool = Query(False, description="Show actual secret values (admin only)"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> ConfigGroupResponse:
    """Get configuration for a specific group."""
    _require_admin(authorization, auth_service)

    try:
        group = ConfigGroup(group_name)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown configuration group: {group_name}"
        )

    config = load_configuration()

    # When showing secrets, we need to get them from the settings object
    if show_secrets:
        from ..config_manager import get_settings
        settings = get_settings()
        for key in get_sensitive_keys():
            secret_value = getattr(settings, key, None)
            if secret_value is not None:
                if hasattr(secret_value, "get_secret_value"):
                    config[key] = secret_value.get_secret_value()
                else:
                    config[key] = secret_value

    from ..config_manager.settings import load_environment_overrides
    env_overrides = load_environment_overrides()
    env_keys = set(env_overrides.keys())

    return _build_group_response(group, config, env_keys, show_secrets=show_secrets)


@router.put("/config/groups/{group_name}", response_model=ConfigGroupUpdateResponse)
def update_config_group(
    group_name: str,
    payload: ConfigGroupUpdatePayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> ConfigGroupUpdateResponse:
    """Update configuration for a specific group."""
    _token, user = _require_admin(authorization, auth_service)

    try:
        group = ConfigGroup(group_name)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown configuration group: {group_name}"
        )

    repo = _get_config_repository()

    # Create backup if requested
    backup_snapshot_id = None
    if payload.create_backup:
        backup_snapshot_id = save_current_config_to_db(
            label=f"Pre-update backup ({group_name})",
            description=f"Automatic backup before updating {group_name} group",
            created_by=user.username,
        )

    # Get current config and apply updates
    # Note: load_configuration() excludes sensitive keys, so we need to add them back
    current_config = load_configuration()

    # Add existing secret values back to config so they're preserved when saving
    from ..config_manager import get_settings
    settings = get_settings()
    for key in get_sensitive_keys():
        secret_value = getattr(settings, key, None)
        if secret_value is not None:
            if hasattr(secret_value, "get_secret_value"):
                current_config[key] = secret_value.get_secret_value()
            else:
                current_config[key] = secret_value

    updated_keys = []
    requires_restart = False
    hot_reload_keys = set(get_hot_reload_keys())

    for key, value in payload.values.items():
        meta = CONFIG_KEY_METADATA.get(key, {})
        if meta.get("group") != group:
            continue

        old_value = current_config.get(key)
        if old_value != value:
            updated_keys.append(key)
            current_config[key] = value

            # Check if this key requires restart
            if key not in hot_reload_keys:
                requires_restart = True

            # Log the change
            repo.log_change(
                action="update",
                username=user.username,
                group_name=group_name,
                key_name=key,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(value) if value is not None else None,
            )

    # Save updated config as new active snapshot
    if updated_keys:
        repo.save_snapshot(
            current_config,
            label=f"Updated {group_name}",
            description=f"Updated keys: {', '.join(updated_keys)}",
            created_by=user.username,
            source="update",
            activate=True,
        )
        # Refresh the runtime config provider so subsequent requests use updated config
        refresh_runtime_config()

    return ConfigGroupUpdateResponse(
        group=group_name,
        updated_keys=updated_keys,
        requires_restart=requires_restart,
        backup_snapshot_id=backup_snapshot_id,
    )


@router.post("/config/validate", response_model=ConfigValidationResponse)
def validate_config(
    payload: ConfigValidationPayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> ConfigValidationResponse:
    """Validate configuration changes before applying."""
    _require_admin(authorization, auth_service)

    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []

    for key, value in payload.values.items():
        meta = CONFIG_KEY_METADATA.get(key, {})

        # Type validation
        expected_type = meta.get("type", "string")
        if expected_type == "integer" and not isinstance(value, int):
            errors.append(ValidationError(
                key=key,
                message=f"Expected integer, got {type(value).__name__}",
                error_type="error"
            ))
        elif expected_type == "number" and not isinstance(value, (int, float)):
            errors.append(ValidationError(
                key=key,
                message=f"Expected number, got {type(value).__name__}",
                error_type="error"
            ))
        elif expected_type == "boolean" and not isinstance(value, bool):
            errors.append(ValidationError(
                key=key,
                message=f"Expected boolean, got {type(value).__name__}",
                error_type="error"
            ))

        # Range validation
        if "min" in meta and isinstance(value, (int, float)):
            if value < meta["min"]:
                errors.append(ValidationError(
                    key=key,
                    message=f"Value must be at least {meta['min']}",
                    error_type="error"
                ))
        if "max" in meta and isinstance(value, (int, float)):
            if value > meta["max"]:
                errors.append(ValidationError(
                    key=key,
                    message=f"Value must be at most {meta['max']}",
                    error_type="error"
                ))

        # Choices validation
        if "choices" in meta and value not in meta["choices"]:
            errors.append(ValidationError(
                key=key,
                message=f"Value must be one of: {', '.join(meta['choices'])}",
                error_type="error"
            ))

        # Restart warning
        if meta.get("requires_restart", True):
            warnings.append(ValidationError(
                key=key,
                message="This setting requires a restart to take effect",
                error_type="warning"
            ))

    return ConfigValidationResponse(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


# -----------------------------------------------------------------------------
# Snapshot Endpoints
# -----------------------------------------------------------------------------


@router.get("/config/snapshots", response_model=SnapshotListResponse)
def list_snapshots(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> SnapshotListResponse:
    """List all configuration snapshots."""
    _require_admin(authorization, auth_service)

    repo = _get_config_repository()
    snapshots, total = repo.list_snapshots(limit=limit, offset=offset)

    return SnapshotListResponse(
        snapshots=[
            SnapshotMetadata(
                snapshot_id=s.snapshot_id,
                label=s.label,
                description=s.description,
                created_by=s.created_by,
                created_at=s.created_at,
                is_active=s.is_active,
                source=s.source,
                config_hash=s.config_hash,
            )
            for s in snapshots
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/config/snapshots", response_model=CreateSnapshotResponse, status_code=status.HTTP_201_CREATED)
def create_snapshot(
    payload: CreateSnapshotPayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> CreateSnapshotResponse:
    """Create a backup snapshot of current configuration."""
    _token, user = _require_admin(authorization, auth_service)

    snapshot_id = save_current_config_to_db(
        label=payload.label,
        description=payload.description,
        created_by=user.username,
        activate=payload.activate,
    )

    if not snapshot_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create snapshot"
        )

    return CreateSnapshotResponse(
        snapshot_id=snapshot_id,
        label=payload.label,
        created_at=datetime.now(timezone.utc).isoformat(),
        is_active=payload.activate,
    )


@router.post("/config/snapshots/{snapshot_id}/restore", response_model=RestoreSnapshotResponse)
def restore_snapshot(
    snapshot_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> RestoreSnapshotResponse:
    """Restore a previous configuration snapshot."""
    _token, user = _require_admin(authorization, auth_service)

    repo = _get_config_repository()

    # Get snapshot info before restore
    result = repo.get_snapshot(snapshot_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot not found: {snapshot_id}"
        )

    metadata, snapshot_config = result

    # Determine which keys will change and require restart
    current_config = load_configuration()
    hot_reload_keys = set(get_hot_reload_keys())
    restart_keys = []

    for key in snapshot_config:
        if key not in current_config or current_config[key] != snapshot_config[key]:
            if key not in hot_reload_keys:
                restart_keys.append(key)

    try:
        repo.restore_snapshot(snapshot_id, restored_by=user.username)
    except ConfigRepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Refresh the runtime config provider so subsequent requests use restored config
    refresh_runtime_config()

    return RestoreSnapshotResponse(
        snapshot_id=snapshot_id,
        label=metadata.label,
        restored_at=datetime.now(timezone.utc).isoformat(),
        requires_restart=len(restart_keys) > 0,
        restart_keys=restart_keys,
    )


@router.delete("/config/snapshots/{snapshot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_snapshot(
    snapshot_id: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Delete a configuration snapshot."""
    _token, user = _require_admin(authorization, auth_service)

    repo = _get_config_repository()

    try:
        deleted = repo.delete_snapshot(snapshot_id, deleted_by=user.username)
    except ConfigRepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot not found: {snapshot_id}"
        )


@router.get("/config/snapshots/{snapshot_id}/export", response_model=ExportSnapshotResponse)
def export_snapshot(
    snapshot_id: str,
    mask_sensitive: bool = Query(True),
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> ExportSnapshotResponse:
    """Export snapshot as downloadable JSON."""
    _require_admin(authorization, auth_service)

    repo = _get_config_repository()

    try:
        export_data = repo.export_snapshot(snapshot_id, mask_sensitive=mask_sensitive)
    except ConfigRepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    return ExportSnapshotResponse(
        snapshot_id=export_data["snapshot_id"],
        label=export_data.get("label"),
        description=export_data.get("description"),
        created_at=export_data["created_at"],
        created_by=export_data.get("created_by"),
        source=export_data["source"],
        config=export_data["config"],
    )


@router.post("/config/import", response_model=ImportConfigResponse)
async def import_config(
    file: UploadFile,
    label: Optional[str] = Query(None),
    activate: bool = Query(False),
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> ImportConfigResponse:
    """Import configuration from uploaded JSON file."""
    _token, user = _require_admin(authorization, auth_service)

    # Read and parse the uploaded file
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON: {e}"
        )

    # Extract config from the data (handle both raw config and export format)
    if "config" in data:
        config = data["config"]
        label = label or data.get("label")
    else:
        config = data

    repo = _get_config_repository()
    snapshot_id = repo.import_config(
        config,
        label=label,
        imported_by=user.username,
        activate=activate,
    )

    # Refresh the runtime config provider if config was activated
    if activate:
        refresh_runtime_config()

    return ImportConfigResponse(
        snapshot_id=snapshot_id,
        label=label,
        key_count=len(config),
        is_active=activate,
    )


# -----------------------------------------------------------------------------
# Audit Log Endpoints
# -----------------------------------------------------------------------------


@router.get("/config/audit", response_model=AuditLogResponse)
def get_audit_log(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    username: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    group_name: Optional[str] = Query(None),
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuditLogResponse:
    """Query the configuration audit log."""
    _require_admin(authorization, auth_service)

    repo = _get_config_repository()
    entries, total = repo.get_audit_log(
        limit=limit,
        offset=offset,
        username=username,
        action=action,
        since=since,
        group_name=group_name,
    )

    return AuditLogResponse(
        entries=[
            AuditLogEntry(
                id=e.id,
                timestamp=e.timestamp,
                username=e.username,
                action=e.action,
                snapshot_id=e.snapshot_id,
                group_name=e.group_name,
                key_name=e.key_name,
                old_value=e.old_value,
                new_value=e.new_value,
                ip_address=e.ip_address,
                metadata=e.metadata,
                success=e.success,
                error_message=e.error_message,
            )
            for e in entries
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


# -----------------------------------------------------------------------------
# Secrets Management Endpoints
# -----------------------------------------------------------------------------


@router.get("/config/secrets", response_model=SecretListResponse)
def list_secrets(
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> SecretListResponse:
    """List stored secrets (key paths only, not values)."""
    _require_admin(authorization, auth_service)

    repo = _get_config_repository()
    secret_paths = repo.list_secrets()

    # Get metadata for each secret
    secrets = []
    for key_path in secret_paths:
        secrets.append(SecretKeyInfo(
            key_path=key_path,
            updated_at=None,  # Could query from DB
            updated_by=None,
        ))

    return SecretListResponse(
        secrets=secrets,
        encryption_available=repo.encryption_available,
    )


@router.post("/config/secrets", response_model=SetSecretResponse)
def set_secret(
    payload: SetSecretPayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> SetSecretResponse:
    """Store an encrypted secret value."""
    _token, user = _require_admin(authorization, auth_service)

    repo = _get_config_repository()

    if not repo.encryption_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Encryption not available. Set EBOOK_CONFIG_SECRET environment variable."
        )

    try:
        repo.store_secret(
            payload.key_path,
            payload.value,
            updated_by=user.username,
        )
    except ConfigRepositoryError as e:
        return SetSecretResponse(
            key_path=payload.key_path,
            success=False,
            error=str(e),
        )

    return SetSecretResponse(
        key_path=payload.key_path,
        success=True,
    )


@router.delete("/config/secrets/{key_path:path}", status_code=status.HTTP_204_NO_CONTENT)
def delete_secret(
    key_path: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Delete a stored secret."""
    _token, user = _require_admin(authorization, auth_service)

    repo = _get_config_repository()
    deleted = repo.delete_secret(key_path, deleted_by=user.username)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secret not found: {key_path}"
        )


__all__ = ["router"]
