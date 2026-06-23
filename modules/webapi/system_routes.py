"""System control routes for the FastAPI backend.

Provides endpoints for system status, configuration reload, and graceful restart.
"""

from __future__ import annotations

import asyncio
import os
import signal
import time
from datetime import datetime, timezone
from typing import Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, status

from ..config_manager.config_repository import ConfigRepository
from ..config_manager.pg_config_repository import PgConfigRepository
from ..config_manager.constants import DEFAULT_CONFIG_DB_DIR, DEFAULT_LIBRARY_ROOT
from ..config_manager.loader import (
    get_config_state,
    reload_configuration,
    save_current_config_to_db,
)
from ..config_manager.groups import get_hot_reload_keys
from ..user_management import AuthService
from ..user_management.user_store_base import UserRecord
from .auth_utils import require_admin_user
from .dependencies import get_auth_service, get_pipeline_job_manager
from .schemas.config import (
    HealthCheckResponse,
    QueuePressureStatus,
    ReloadConfigResponse,
    RestartRequestPayload,
    RestartResponse,
    SystemStatusResponse,
)
from ..services.job_manager import PipelineJobManager, PipelineJobStatus

router = APIRouter()

# Module-level state for tracking system status
_START_TIME = time.time()
_RESTART_SCHEDULED = False
_RESTART_AT: str | None = None
_PENDING_RESTART_KEYS: list[str] = []


def _require_admin(
    authorization: str | None,
    auth_service: AuthService,
) -> Tuple[str, UserRecord]:
    """Validate admin authentication and return (token, user)."""
    return require_admin_user(authorization, auth_service)


def _get_config_repository():
    """Get the configuration repository instance (PG or SQLite)."""
    import os
    if os.environ.get("DATABASE_URL", "").strip():
        return PgConfigRepository()
    return ConfigRepository()


def queue_pressure_status(job_manager: PipelineJobManager) -> QueuePressureStatus:
    """Return a token-safe queue/backpressure snapshot for status views."""

    state = job_manager.backpressure_state
    policy = getattr(job_manager, "backpressure_policy", None)
    if state is None:
        return QueuePressureStatus(accepting_jobs=True)

    return QueuePressureStatus(
        accepting_jobs=job_manager.is_accepting_jobs,
        is_under_pressure=state.is_under_pressure,
        queue_depth=state.queue_depth,
        active_count=state.active_count,
        soft_limit=getattr(policy, "soft_limit", None),
        hard_limit=getattr(policy, "hard_limit", None),
        rejection_count=state.rejection_count,
        delay_count=state.delay_count,
    )


def _count_running_jobs(job_manager: PipelineJobManager) -> int:
    """Count currently running pipeline jobs."""
    try:
        jobs = job_manager.list(user_role="admin")
        return sum(1 for job in jobs.values() if job.status == PipelineJobStatus.RUNNING)
    except Exception:
        return 0


# -----------------------------------------------------------------------------
# System Status Endpoints
# -----------------------------------------------------------------------------


@router.get("/system/status", response_model=SystemStatusResponse)
def get_system_status(
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
    job_manager: PipelineJobManager = Depends(get_pipeline_job_manager),
) -> SystemStatusResponse:
    """Get current system status including configuration state."""
    _require_admin(authorization, auth_service)

    config_state = get_config_state()
    uptime = time.time() - _START_TIME

    # Resolve database paths
    config_db_path = str(DEFAULT_CONFIG_DB_DIR / "config.db")
    library_db_path = str(DEFAULT_LIBRARY_ROOT / ".library" / "library.db")

    return SystemStatusResponse(
        uptime_seconds=uptime,
        config_loaded_at=config_state.get("loaded_at"),
        active_snapshot_id=config_state.get("active_snapshot_id"),
        db_enabled=config_state.get("db_enabled", False),
        config_db_path=config_db_path,
        library_db_path=library_db_path,
        pending_changes=False,  # Could track pending changes
        restart_required=_RESTART_SCHEDULED or len(_PENDING_RESTART_KEYS) > 0,
        restart_keys=list(_PENDING_RESTART_KEYS),
        queue_pressure=queue_pressure_status(job_manager),
    )


@router.get("/system/health", response_model=HealthCheckResponse)
def deep_health_check() -> HealthCheckResponse:
    """Comprehensive health check for post-restart verification.

    This endpoint does not require authentication for monitoring purposes.
    """
    uptime = time.time() - _START_TIME
    config_state = get_config_state()

    checks = {
        "config_loaded": config_state.get("loaded_at") is not None,
    }

    # Check database availability
    db_available = False
    try:
        repo = _get_config_repository()
        with repo.connect():
            db_available = True
        checks["database"] = True
    except Exception:
        checks["database"] = False

    # Check tmp workspace
    tmp_workspace = None
    is_ramdisk = False
    try:
        from .application import _STARTUP_RUNTIME_CONTEXT
        if _STARTUP_RUNTIME_CONTEXT:
            tmp_workspace = str(_STARTUP_RUNTIME_CONTEXT.tmp_dir)
            is_ramdisk = _STARTUP_RUNTIME_CONTEXT.is_tmp_ramdisk
    except Exception:
        pass

    # Determine overall status
    if all(checks.values()):
        status_str = "ok"
    elif any(checks.values()):
        status_str = "degraded"
    else:
        status_str = "unhealthy"

    return HealthCheckResponse(
        status=status_str,
        config_loaded=checks.get("config_loaded", False),
        db_available=db_available,
        tmp_workspace=tmp_workspace,
        is_ramdisk=is_ramdisk,
        uptime_seconds=uptime,
        checks=checks,
    )


# -----------------------------------------------------------------------------
# Configuration Reload Endpoint
# -----------------------------------------------------------------------------


@router.post("/system/reload-config", response_model=ReloadConfigResponse)
def reload_config(
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> ReloadConfigResponse:
    """Hot-reload configuration without full restart.

    Only settings that don't require restart will take effect immediately.
    Settings that require restart will be queued for the next restart.
    """
    global _PENDING_RESTART_KEYS

    _token, user = _require_admin(authorization, auth_service)

    # Get current config to compare
    from ..config_manager.loader import load_configuration
    old_config = load_configuration()

    try:
        # Reload configuration
        new_config = reload_configuration(verbose=True)

        # Determine what changed
        hot_reload_keys = set(get_hot_reload_keys())
        changed_keys = []
        restart_needed_keys = []

        for key in set(old_config.keys()) | set(new_config.keys()):
            old_val = old_config.get(key)
            new_val = new_config.get(key)
            if old_val != new_val:
                changed_keys.append(key)
                if key not in hot_reload_keys:
                    restart_needed_keys.append(key)

        # Track keys that need restart
        _PENDING_RESTART_KEYS = list(set(_PENDING_RESTART_KEYS) | set(restart_needed_keys))

        # Log the reload
        repo = _get_config_repository()
        repo.log_change(
            action="reload",
            username=user.username,
            metadata={
                "changed_keys": changed_keys,
                "restart_needed_keys": restart_needed_keys,
            },
        )

        return ReloadConfigResponse(
            success=True,
            reloaded_at=datetime.now(timezone.utc).isoformat(),
            changed_keys=changed_keys,
        )

    except Exception as e:
        return ReloadConfigResponse(
            success=False,
            reloaded_at=datetime.now(timezone.utc).isoformat(),
            error=str(e),
        )


# -----------------------------------------------------------------------------
# Restart Endpoint
# -----------------------------------------------------------------------------


@router.post("/system/restart", response_model=RestartResponse)
async def request_restart(
    payload: RestartRequestPayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
    job_manager: PipelineJobManager = Depends(get_pipeline_job_manager),
) -> RestartResponse:
    """Request graceful API restart.

    Creates a backup before restart and schedules SIGTERM after the delay.
    """
    global _RESTART_SCHEDULED, _RESTART_AT, _PENDING_RESTART_KEYS

    _token, user = _require_admin(authorization, auth_service)

    # Check for running jobs
    running_jobs = _count_running_jobs(job_manager)
    if running_jobs > 0 and not payload.force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot restart: {running_jobs} job(s) currently running. Use force=true to override."
        )

    # Create pre-restart backup
    repo = _get_config_repository()
    restart_id = repo.log_restart_request(
        requested_by=user.username,
        reason=payload.reason,
        delay_seconds=payload.delay_seconds,
    )

    # Save current config as backup
    backup_snapshot_id = save_current_config_to_db(
        label="Pre-restart Backup",
        description=f"Automatic backup before restart. Reason: {payload.reason or 'Manual restart'}",
        created_by=user.username,
    )

    # Calculate restart time
    restart_at = datetime.now(timezone.utc)
    _RESTART_AT = restart_at.isoformat()
    _RESTART_SCHEDULED = True

    # Schedule the restart
    async def delayed_restart():
        await asyncio.sleep(payload.delay_seconds)
        # Clear pending keys since we're restarting
        global _PENDING_RESTART_KEYS
        _PENDING_RESTART_KEYS = []
        # Send SIGTERM for graceful shutdown
        os.kill(os.getpid(), signal.SIGTERM)

    asyncio.create_task(delayed_restart())

    return RestartResponse(
        scheduled=True,
        restart_at=_RESTART_AT,
        delay_seconds=payload.delay_seconds,
        pre_restart_snapshot_id=backup_snapshot_id,
        running_jobs=running_jobs,
    )


@router.get("/system/restart/status")
def get_restart_status(
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Get the current restart status."""
    _require_admin(authorization, auth_service)

    return {
        "restart_scheduled": _RESTART_SCHEDULED,
        "restart_at": _RESTART_AT,
        "pending_restart_keys": _PENDING_RESTART_KEYS,
    }


@router.post("/system/restart/cancel")
def cancel_restart(
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Cancel a scheduled restart.

    Note: This only clears the scheduled flag. If the restart task has already
    sent SIGTERM, the shutdown cannot be stopped.
    """
    global _RESTART_SCHEDULED, _RESTART_AT

    _token, user = _require_admin(authorization, auth_service)

    if not _RESTART_SCHEDULED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No restart is currently scheduled"
        )

    _RESTART_SCHEDULED = False
    _RESTART_AT = None

    repo = _get_config_repository()
    repo.log_change(
        action="restart_cancelled",
        username=user.username,
    )

    return {
        "cancelled": True,
        "message": "Restart cancelled. Note: Cannot stop shutdown if SIGTERM already sent.",
    }


__all__ = ["router"]
