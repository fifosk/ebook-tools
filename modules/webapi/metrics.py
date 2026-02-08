"""Prometheus metrics exporter for the ebook-tools API.

Defines all custom application metrics and wires automatic HTTP
instrumentation via prometheus-fastapi-instrumentator.

Usage:
    from .metrics import setup_metrics
    setup_metrics(app)  # call once in create_app()

Adding new metrics:
    1. Define the metric (Counter/Gauge/Histogram) at module level
    2. Instrument it at the call site via a lazy import
    3. For gauge-style metrics that need periodic refresh, add a collector
       function and register it in ``_periodic_gauge_update``
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import TYPE_CHECKING

from fastapi import FastAPI, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)
from prometheus_fastapi_instrumentator import Instrumentator

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application info
# ---------------------------------------------------------------------------
APP_INFO = Info(
    "ebook_tools",
    "ebook-tools application information",
)

# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------
UP_GAUGE = Gauge(
    "ebook_tools_up",
    "Whether the ebook-tools backend is up (1=up, 0=down)",
)

HEALTH_STATUS = Gauge(
    "ebook_tools_health_status",
    "Health check status (1=ok, 0.5=degraded, 0=unhealthy)",
)

# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
JOBS_TOTAL = Gauge(
    "ebook_tools_jobs_total",
    "Current jobs by status",
    ["status"],
)

JOBS_ACTIVE = Gauge(
    "ebook_tools_jobs_active",
    "Number of currently running jobs",
)

JOBS_QUEUE_DEPTH = Gauge(
    "ebook_tools_jobs_queue_depth",
    "Current job queue depth (pending + running)",
)

JOB_DURATION = Histogram(
    "ebook_tools_job_duration_seconds",
    "Job execution duration in seconds",
    ["job_type", "status"],
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600],
)

BACKPRESSURE_REJECTIONS = Counter(
    "ebook_tools_jobs_backpressure_rejections_total",
    "Total job rejections due to backpressure",
)

BACKPRESSURE_DELAYS = Counter(
    "ebook_tools_jobs_backpressure_delays_total",
    "Total job delays due to backpressure",
)

# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------
LIBRARY_ITEMS = Gauge(
    "ebook_tools_library_items_total",
    "Total library items by type",
    ["item_type"],
)

# ---------------------------------------------------------------------------
# Users & sessions
# ---------------------------------------------------------------------------
USERS_TOTAL = Gauge(
    "ebook_tools_users_total",
    "Total registered users by role",
    ["role"],
)

SESSIONS_ACTIVE = Gauge(
    "ebook_tools_sessions_active",
    "Number of active (non-expired) user sessions",
)

AUTH_ATTEMPTS = Counter(
    "ebook_tools_auth_attempts_total",
    "Authentication attempts by method and result",
    ["method", "result"],
)

# ---------------------------------------------------------------------------
# Pipeline performance
# ---------------------------------------------------------------------------
PIPELINE_STAGE_DURATION = Histogram(
    "ebook_tools_pipeline_stage_duration_seconds",
    "Pipeline stage execution time in seconds",
    ["stage"],
    buckets=[0.1, 0.5, 1, 5, 10, 30, 60, 300],
)

WORKER_POOL_UTILIZATION = Gauge(
    "ebook_tools_worker_pool_utilization",
    "Worker pool utilisation ratio (active / max)",
)

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
ERRORS_TOTAL = Counter(
    "ebook_tools_errors_total",
    "Total errors by type and endpoint",
    ["error_type", "endpoint"],
)

JOB_FAILURES = Counter(
    "ebook_tools_job_failures_total",
    "Total job failures by error type",
    ["error_type"],
)

# ---------------------------------------------------------------------------
# Gauge update interval
# ---------------------------------------------------------------------------
_GAUGE_UPDATE_INTERVAL_SECONDS = 15

# Background task handle — kept so shutdown can cancel it
_gauge_task: asyncio.Task | None = None


# ---------------------------------------------------------------------------
# Periodic gauge collectors
# ---------------------------------------------------------------------------

def _collect_job_gauges() -> None:
    """Snapshot job counts from the PipelineJobManager singleton."""
    try:
        from .dependencies import get_pipeline_job_manager
    except Exception:
        return

    try:
        manager = get_pipeline_job_manager()
    except Exception:
        return

    status_counts: dict[str, int] = {}
    max_workers = 1
    active_count = 0

    with manager._lock:
        for job in manager._jobs.values():
            key = job.status.value
            status_counts[key] = status_counts.get(key, 0) + 1

    # Populate all known statuses (so Prometheus shows 0 rather than absent)
    for s in ("pending", "running", "pausing", "paused", "completed", "failed", "cancelled"):
        JOBS_TOTAL.labels(status=s).set(status_counts.get(s, 0))

    JOBS_ACTIVE.set(status_counts.get("running", 0))

    # Queue depth
    queue_depth = status_counts.get("pending", 0) + status_counts.get("running", 0)
    JOBS_QUEUE_DEPTH.set(queue_depth)

    # Worker pool utilisation
    try:
        executor = manager._executor
        if hasattr(executor, "_max_workers"):
            max_workers = max(1, executor._max_workers)
        elif hasattr(executor, "max_workers"):
            max_workers = max(1, executor.max_workers)
        active_count = status_counts.get("running", 0)
        WORKER_POOL_UTILIZATION.set(active_count / max_workers)
    except Exception:
        pass


def _collect_library_gauges() -> None:
    """Snapshot library item counts."""
    try:
        from .dependencies import get_library_service
        service = get_library_service()
        overview = service.get_library_overview()
    except Exception:
        return

    # Overview object has a .languages dict, but we want by item_type
    # Use the overview total + finished/paused as a simpler approach
    try:
        repo = service.repository
        # Try to get counts by item_type directly from the repository
        if hasattr(repo, "count_by_type"):
            counts = repo.count_by_type()
            for item_type, count in counts.items():
                LIBRARY_ITEMS.labels(item_type=item_type).set(count)
        else:
            # Fallback: use the overview total
            LIBRARY_ITEMS.labels(item_type="all").set(overview.total)
    except Exception:
        LIBRARY_ITEMS.labels(item_type="all").set(getattr(overview, "total", 0))


def _collect_user_gauges() -> None:
    """Snapshot user and session counts."""
    try:
        from .dependencies import get_auth_service
        auth = get_auth_service()
    except Exception:
        return

    # Users by role
    try:
        users = auth.user_store.list_users()
        role_counts: dict[str, int] = {}
        for u in users:
            role = u.roles[0] if u.roles else "viewer"
            role_counts[role] = role_counts.get(role, 0) + 1
        for role, count in role_counts.items():
            USERS_TOTAL.labels(role=role).set(count)
    except Exception:
        pass

    # Active sessions
    try:
        if hasattr(auth.session_manager, "count_active_sessions"):
            SESSIONS_ACTIVE.set(auth.session_manager.count_active_sessions())
    except Exception:
        pass


def _collect_health_gauge() -> None:
    """Mirror the /api/admin/system/health logic for the gauge."""
    try:
        from .. import config_manager as cfg
        config_ok = cfg.get_settings() is not None
    except Exception:
        config_ok = False

    db_ok = False
    if os.environ.get("DATABASE_URL", "").strip():
        try:
            from ..database.engine import get_engine
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(__import__("sqlalchemy").text("SELECT 1"))
                db_ok = True
        except Exception:
            pass
    else:
        db_ok = True  # No DB configured = not a failure

    if config_ok and db_ok:
        HEALTH_STATUS.set(1.0)
    elif config_ok or db_ok:
        HEALTH_STATUS.set(0.5)
    else:
        HEALTH_STATUS.set(0.0)


async def _periodic_gauge_update() -> None:
    """Background loop that refreshes gauge metrics."""
    while True:
        try:
            _collect_job_gauges()
            _collect_library_gauges()
            _collect_user_gauges()
            _collect_health_gauge()
        except Exception:
            pass  # Never crash the collector
        await asyncio.sleep(_GAUGE_UPDATE_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Setup entry point
# ---------------------------------------------------------------------------

_setup_done = False


def setup_metrics(app: FastAPI) -> None:
    """Wire Prometheus metrics into the FastAPI application.

    Call once from ``create_app()`` before routers are registered.
    Idempotent — safe to call multiple times (e.g. in test suites that
    recreate the app).
    """
    global _gauge_task, _setup_done

    # Application info (safe to call repeatedly)
    try:
        APP_INFO.info({
            "version": getattr(app, "version", "unknown"),
            "title": getattr(app, "title", "ebook-tools"),
        })
    except ValueError:
        pass  # Already set
    UP_GAUGE.set(1)

    if not _setup_done:
        # -- Auto-instrument HTTP requests (first call only) --
        # Auto-generates: http_request_duration_seconds, http_requests_total, etc.
        try:
            instrumentator = Instrumentator(
                should_group_status_codes=False,
                should_ignore_untemplated=True,
                should_respect_env_var=False,
                should_instrument_requests_inprogress=True,
                excluded_handlers=["/metrics", "/_health"],
                inprogress_name="ebook_tools_http_requests_inprogress",
                inprogress_labels=True,
            )
            instrumentator.instrument(app)
            instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)
        except ValueError:
            # Metrics already registered in the global Prometheus registry
            # (happens when tests create multiple app instances).
            pass
        _setup_done = True

    # -- Expose /metrics on every app (needed for test clients) --
    if not any(r.path == "/metrics" for r in getattr(app, "routes", [])):
        @app.get("/metrics", include_in_schema=False)
        async def _metrics_fallback() -> Response:
            return Response(
                content=generate_latest(REGISTRY),
                media_type=CONTENT_TYPE_LATEST,
            )

    # -- Start periodic gauge collector --
    @app.on_event("startup")
    async def _start_gauge_collector() -> None:
        global _gauge_task
        _gauge_task = asyncio.create_task(_periodic_gauge_update())
        logger.info("Prometheus gauge collector started (interval=%ds)", _GAUGE_UPDATE_INTERVAL_SECONDS)

    @app.on_event("shutdown")
    async def _stop_gauge_collector() -> None:
        global _gauge_task
        if _gauge_task is not None:
            _gauge_task.cancel()
            _gauge_task = None
